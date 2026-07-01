from __future__ import annotations

from panda3d.core import LineSegs, TextNode

from library.core.constants import (
    AMBER,
    AUDIO,
    DIM,
    DYNO_GAUGES,
    DYNO_GRID,
    DYNO_PULL_SECONDS,
    DYNO_TILE,
    DYNO_TRACE,
    DYNO_TRACE_TQ,
    DYNO_ZONE_GREEN,
    DYNO_ZONE_RED,
    ED_BLOWN,
    GREEN,
    GREEN_2,
    LINE,
    TEXT,
    WHITE,
)
from library.core.utils import clamp
from library.stages.task_base import TaskBase

CENTER = TextNode.ACenter


def _faint(color, factor=0.42):
    """Dim a trace colour for the stock reference curves (darker = fainter on the dark
    graph; avoids needing per-line transparency)."""
    return (color[0] * factor, color[1] * factor, color[2] * factor, color[3])


class DynoTask(TaskBase):
    """SimosTools-style dyno: a pull sweeps RPM idle->redline while gauge tiles and a
    live power-vs-RPM graph animate, then the peak + grade are shown."""

    title = "DYNO"
    key = "dyno"
    live = False

    def build_scene(self):
        car = self.game.car
        self.car_np = self.add_garage_scene()
        self.wheels = self.prepare_wheels(self.car_np)
        self.spin = 0.0
        self.running = False
        self.pull_t = 1.0  # show the current curve fully at rest; a pull re-animates it
        self.result = None
        # Current (built) curve previewed full at rest; stock base curve as a faint
        # reference so you can see what the tune + mods added.
        self.points = self._points_from_curve(car.build_whp())
        self.stock_points = self._points_from_curve(car.stock_curve())
        self.rpm_lo = self.points[0]["rpm"] if self.points else car.idle
        self.rpm_hi = self.points[-1]["rpm"] if self.points else car.redline
        self.graph = None
        self.values = self._idle_values()
        self.vmin = {}
        self.vmax = {}

    def _idle_values(self):
        car = self.game.car
        result = car.compute()
        return {"boost": car.tune["boost"] * 0.3, "rpm": 950, "kr": 0.0, "lambda": car.tune["lambda"], "egt": result["egt"] * 0.55, "whp": 0.0}

    # -- pull --------------------------------------------------------------
    def start_pull(self):
        if self.running or not self.game.car.flashed:
            return
        car = self.game.car
        self.result = car.compute()
        self.points = self._points_from_curve(car.build_whp())  # the car's real composed curve
        # Grade off the actual built peak (curve), not the tune-only compute() figure.
        self.result["whp"] = max((p["pw"] for p in self.points), default=self.result["whp"])
        self.rpm_lo = self.points[0]["rpm"] if self.points else car.idle
        self.rpm_hi = self.points[-1]["rpm"] if self.points else car.redline
        self.running = True
        self.pull_t = 0.0
        self.vmin, self.vmax = {}, {}
        self.game.log("dyno pull started", "info")
        self.dirty = True

    @staticmethod
    def _points_from_curve(curve):
        """``[(rpm, whp)] -> [{rpm, pw, tq}]`` for the gauge/graph code (``pw`` = wheel
        power; torque derived for completeness)."""
        return [{"rpm": rpm, "pw": whp, "tq": (whp * 5252 / rpm if rpm else 0.0)} for rpm, whp in curve]

    def tick(self, dt):
        if not self.running:
            self.app.audio.idle()
            return
        self.pull_t += dt / DYNO_PULL_SECONDS
        finished = self.pull_t >= 1.0
        if finished:
            self.pull_t = 1.0
            self.running = False
            self._finish_dyno(self.result)
            self.dirty = True
        self._sample()
        self.spin -= dt * 1700
        for wheel in self.wheels:
            wheel.setP(self.spin)
        self.app.audio.set_engine(self.values["rpm"], AUDIO["pull_load"])
        if finished:  # lift off at redline -> overrun crackle
            self.app.audio.bov()
            self.app.audio.overrun(self.game.car.active_pop(), 1.1)
        self._update_gauges()
        self._controls()
        self._draw_graph()

    def _sample(self):
        lo, hi = self.rpm_lo, self.rpm_hi
        rpm = lo + (hi - lo) * self.pull_t
        spool = clamp((rpm - 2100) / 1300, 0, 1)
        car = self.game.car
        self.values = {
            "boost": car.tune["boost"] * (0.3 + 0.7 * spool),
            "rpm": rpm,
            "kr": self.result["KR"] * (0.4 + 0.6 * spool),
            "lambda": car.tune["lambda"],
            "egt": self.result["egt"] * (0.65 + 0.35 * spool),
            "whp": self._power_at(rpm),
        }
        for key, value in self.values.items():
            self.vmin[key] = min(self.vmin.get(key, value), value)
            self.vmax[key] = max(self.vmax.get(key, value), value)

    def _power_at(self, rpm):
        if not self.points:
            return 0.0
        prev = self.points[0]
        for point in self.points:
            if point["rpm"] >= rpm:
                span = point["rpm"] - prev["rpm"] or 1
                frac = (rpm - prev["rpm"]) / span
                return prev["pw"] + (point["pw"] - prev["pw"]) * frac
            prev = point
        return self.points[-1]["pw"]

    def _finish_dyno(self, result: dict):
        """Record the pull, log the grade, and fire grade-based achievements/quips."""
        game = self.game
        self._log_result(game.car.record_dyno(result))
        # The money_shift / tuner_of_year / cat_delete trophies are polled off the car's
        # recorded dyno result + grade; here we just apply the gameplay sting + Dave's quip.
        if result["blown"]:
            game.hurt_bro(ED_BLOWN)
            game.dave(game.car.blow_dave_pool())  # Vortex makes Dave deny it; others "blown"
        elif game.car.grade.startswith("Grade S"):
            game.dave("sgrade")
        else:
            game.dave("dyno")

    # -- UI ----------------------------------------------------------------
    # The gauge cluster gets the left ~38% of the width; the graph gets the rest.
    SPLIT_FRAC = 0.38

    def _split_x(self):
        left, right = self.bounds()
        return left + (right - left) * self.SPLIT_FRAC

    def _gauge_layout(self):
        """Per-gauge tile rects: (x, z, w, h, gauge_tuple), a compact 2x3 grid on the
        left (kept narrow so the dyno graph can be large)."""
        left, _ = self.bounds()
        cols, rows = 2, 3
        gx_lo, gx_hi, gz_lo, gz_hi = left, self._split_x() - 0.03, -0.50, 0.52
        tile_w, tile_h = (gx_hi - gx_lo) / cols, (gz_hi - gz_lo) / rows
        out = []
        for index, gauge in enumerate(DYNO_GAUGES):
            row, col = divmod(index, cols)
            x = gx_lo + tile_w * col
            z = gz_hi - tile_h * (row + 1)
            out.append((x + 0.010, z + 0.010, tile_w - 0.020, tile_h - 0.020, gauge))
        return out

    def build_ui(self):
        left, right = self.bounds()
        gx0, gx1, gz0, gz1 = self._split_x() + 0.04, right, -0.30, 0.52  # the (large) graph rect
        graph_cx = (gx0 + gx1) / 2
        # Gauge frames and labels are persistent; values/fill sizes are edited live.
        for index, (x, z, w, h, gauge) in enumerate(self._gauge_layout()):
            label, _key, lo, hi, _danger, unit, _dec = gauge
            cx = x + w / 2
            xr, zt = x + w, z + h
            self.ui.add_frame(f"g{index}-tile", frame_size=(x, xr, z, zt), color=DYNO_TILE, border=LINE)
            self.ui.add_frame(f"g{index}-green", frame_size=(x, xr, z, z), color=DYNO_ZONE_GREEN, border=None)
            self.ui.add_frame(f"g{index}-red", frame_size=(x, xr, z, z), color=DYNO_ZONE_RED, border=None, is_visible=False)
            self.ui.add_text(f"g{index}-title", label, (cx, 0, z + h - 0.038), 0.021, TEXT, CENTER)
            for i in range(3):
                self.ui.add_text(f"g{index}-s{i}", f"{lo + (hi - lo) * i / 2:.0f}", (x + 0.018, 0, z + h * i / 2 - 0.007), 0.017, DIM)
            self.ui.add_text(f"g{index}-val", "", (cx, 0, z + h * 0.44), 0.048, WHITE, CENTER)
            self.ui.add_text(f"g{index}-mm", "", (cx, 0, z + h * 0.25), 0.019, DIM, CENTER)
            self.ui.add_text(f"g{index}-unit", unit, (cx, 0, z + 0.022), 0.019, DIM, CENTER)
        # Graph background (panel + grid + rpm axis) FIRST, so the legend/peaks/traces
        # layer on top of the opaque panel rather than behind it.
        self._build_graph_objects(gx0, gx1, gz0, gz1)
        # Graph header: POWER (cyan) + TORQUE (amber) legend, with peak readouts.
        self.ui.add_text("graph-title", "POWER", (gx0 + 0.03, 0, gz1 - 0.05), 0.026, DYNO_TRACE)
        self.ui.add_text("graph-title-tq", "TORQUE", (gx0 + 0.20, 0, gz1 - 0.05), 0.026, DYNO_TRACE_TQ)
        self.ui.add_text("graph-z", "", (gx1 - 0.03, 0, gz1 - 0.05), 0.024, DYNO_TRACE, TextNode.ARight)
        self.ui.add_text("graph-z-tq", "", (gx1 - 0.03, 0, gz1 - 0.10), 0.024, DYNO_TRACE_TQ, TextNode.ARight)
        # Controls live below the (taller) graph.
        self.ui.add_button("run", "Run Dyno Pull", (graph_cx, 0, -0.41), (0.46, 0.11),
                           self.start_pull, self.game.car.flashed and not self.running, GREEN_2)
        self.ui.add_text("status", "", (graph_cx, 0, -0.51), 0.032, DIM, CENTER)
        self.ui.add_text("grade", "", (graph_cx, 0, -0.585), 0.032, DIM, CENTER, wordwrap=46)
        self._update_graph_scale()  # graph-z / graph-z-tq now exist

    def update_ui(self, left, right):
        self._update_gauges()
        self._controls()
        self._draw_graph()

    def _update_gauges(self):
        for index, (x, z, w, h, gauge) in enumerate(self._gauge_layout()):
            self._update_gauge(index, x, z, w, h, gauge)

    def _update_gauge(self, index, x, z, w, h, gauge):
        _label, key, lo, hi, danger, _unit, decimals = gauge
        xr = x + w
        value = self.values.get(key, 0.0)
        vf = clamp((value - lo) / (hi - lo), 0, 1)
        df = clamp((danger - lo) / (hi - lo), 0, 1)
        green_top = z + h * min(vf, df)
        self.ui.get(f"g{index}-green").frame_size((x, xr, z, green_top))
        red = self.ui.get(f"g{index}-red")
        if vf > df:
            red.frame_size((x, xr, z + h * df, z + h * vf))
            red.is_visible(True)
        else:
            red.is_visible(False)
        self.ui.get(f"g{index}-val").text(self._fmt(value, decimals))
        self.ui.get(f"g{index}-mm").text(
            f"{self._fmt(self.vmin.get(key, value), decimals)} : {self._fmt(self.vmax.get(key, value), decimals)}")

    @staticmethod
    def _fmt(value, decimals):
        return f"{value:.{decimals}f}"

    def _build_graph_objects(self, x0, x1, z0, z1):
        self.ui.add_frame("graph-panel", frame_size=(x0, x1, z0, z1), color=DYNO_TILE, border=LINE)
        gx0, gx1, gz0, gz1 = x0 + 0.06, x1 - 0.05, z0 + 0.085, z1 - 0.16  # plot area (room for rpm labels)
        lo, hi = self.rpm_lo, self.rpm_hi
        for i in range(5):
            gx = gx0 + (gx1 - gx0) * i / 4
            self.ui.add_frame(f"graph-grid-x-{i}", frame_size=(gx, gx + 0.003, gz0, gz1),
                              color=DYNO_GRID, border=None)
            gz = gz0 + (gz1 - gz0) * i / 4
            self.ui.add_frame(f"graph-grid-z-{i}", frame_size=(gx0, gx1, gz, gz + 0.003),
                              color=DYNO_GRID, border=None)
            # X-axis rpm indication: a tick label under each vertical gridline.
            self.ui.add_text(f"graph-rpm-{i}", f"{(lo + (hi - lo) * i / 4) / 1000:.1f}k",
                             (gx, 0, gz0 - 0.045), 0.018, DIM, CENTER)
        self._graph_box = (gx0, gx1, gz0, gz1)

    def _update_graph_scale(self):
        whp_peak = round(max((p["pw"] for p in self.points), default=0))
        tq_peak = round(max((p["tq"] for p in self.points), default=0))
        self.ui.get("graph-z").text(f"{whp_peak} whp")
        self.ui.get("graph-z-tq").text(f"{tq_peak} lb-ft")

    def _draw_graph(self):
        if self.graph is not None:
            self.graph.removeNode()
            self.graph = None
        self._update_graph_scale()
        box = getattr(self, "_graph_box", None)
        if not box or (not self.points and not self.stock_points):
            return
        lo, hi = self.rpm_lo, self.rpm_hi
        # One shared vertical scale across power + torque, current + stock, so all fit.
        vmax = max([p["pw"] for p in self.points] + [p["tq"] for p in self.points]
                   + [p["pw"] for p in self.stock_points] + [p["tq"] for p in self.stock_points] + [1.0])
        cur_rpm = lo + (hi - lo) * self.pull_t
        segs = LineSegs()
        segs.setThickness(2.4)
        # Faint stock reference (full base curve), then the bright current curve (whp +
        # torque), the current one animated up to the live rpm during a pull.
        self._trace(segs, self.stock_points, "pw", _faint(DYNO_TRACE), lo, hi, vmax, box)
        self._trace(segs, self.stock_points, "tq", _faint(DYNO_TRACE_TQ), lo, hi, vmax, box)
        self._trace(segs, self.points, "pw", DYNO_TRACE, lo, hi, vmax, box, up_to=cur_rpm)
        self._trace(segs, self.points, "tq", DYNO_TRACE_TQ, lo, hi, vmax, box, up_to=cur_rpm)
        if not segs.isEmpty():  # NB: LineSegs.getNumVertices() is unreliable here
            # Attach to the UI-object layer (not self.root) so the traces draw ABOVE the
            # managed graph panel/gridlines, which the controller lifts over self.root.
            self.graph = self.ui.parent.attachNewNode(segs.create())

    def _trace(self, segs, pts, key, color, lo, hi, vmax, box, up_to=None):
        """Add one polyline (rpm vs ``key``) to ``segs`` in ``color`` (a new line via
        moveTo). ``up_to`` limits it to rpm <= that (the live pull position)."""
        gx0, gx1, gz0, gz1 = box
        segs.setColor(*color)
        started = False
        for p in pts:
            if up_to is not None and p["rpm"] > up_to:
                break
            if p["rpm"] < lo:
                continue
            gx = gx0 + clamp((p["rpm"] - lo) / (hi - lo), 0, 1) * (gx1 - gx0)
            gz = gz0 + clamp(p[key] / vmax, 0, 1) * (gz1 - gz0)
            segs.drawTo(gx, 0, gz) if started else segs.moveTo(gx, 0, gz)
            started = True

    def _controls(self):
        game = self.game
        self.ui.get("run").enabled(game.car.flashed and not self.running)
        state, color = next(
            result for condition, result in (
                (self.running, (f"pulling... {round(self.values['rpm'])} rpm", AMBER)),
                (game.car.flashed, ("Loaded. Send it.", DIM)),
                (True, ("Flash a tune first.", DIM)),
            )
            if condition
        )
        status = self.ui.get("status")
        status.text(state)
        status.color(color)
        grade = game.car.grade
        grade_lbl = self.ui.get("grade")
        grade_lbl.text(grade or "Run a pull to grade the map.")
        grade_lbl.color(GREEN if grade.startswith("Grade") else DIM)
