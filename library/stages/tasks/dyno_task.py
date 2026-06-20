from __future__ import annotations

from panda3d.core import LineSegs, TextNode

from library.core.constants import (
    AMBER,
    AUDIO,
    DIM,
    DYNO_GAUGES,
    DYNO_GRID,
    DYNO_PULL_SECONDS,
    DYNO_RPM_RANGE,
    DYNO_TILE,
    DYNO_TRACE,
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
from library.game.tuning import dyno_curve
from library.stages.task_base import TaskBase

CENTER = TextNode.ACenter


class DynoTask(TaskBase):
    """SimosTools-style dyno: a pull sweeps RPM idle->redline while gauge tiles and a
    live power-vs-RPM graph animate, then the peak + grade are shown."""

    title = "DYNO"
    key = "dyno"
    live = False

    def build_scene(self):
        self.car_np = self.add_garage_scene()
        self.wheels = self.prepare_wheels(self.car_np)
        self.spin = 0.0
        self.running = False
        self.pull_t = 0.0
        self.result = None
        self.points = []
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
        self.result = self.game.car.compute()
        self.points = dyno_curve(self.result["whp"])
        self.running = True
        self.pull_t = 0.0
        self.vmin, self.vmax = {}, {}
        self.game.log("dyno pull started", "info")
        self.dirty = True

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
        lo, hi = DYNO_RPM_RANGE
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
        if result["blown"]:
            game.unlock("money_shift", "Money Shift")
            game.hurt_bro(ED_BLOWN)
            game.dave("blown")
        elif game.car.grade.startswith("Grade S"):
            game.unlock("tuner_of_year", "Tuner of the Year")
            game.dave("sgrade")
        else:
            game.dave("dyno")
        if result["pop"] > 90:
            game.unlock("cat_delete", "Cat Delete Speedrun")

    # -- UI ----------------------------------------------------------------
    def _gauge_layout(self):
        """Per-gauge tile rects: (x, z, w, h, gauge_tuple), in a 2x3 grid on the left."""
        left, right = self.bounds()
        mid = (left + right) / 2
        cols, rows = 2, 3
        gx_lo, gx_hi, gz_lo, gz_hi = left, mid - 0.03, -0.60, 0.50
        tile_w, tile_h = (gx_hi - gx_lo) / cols, (gz_hi - gz_lo) / rows
        out = []
        for index, gauge in enumerate(DYNO_GAUGES):
            row, col = divmod(index, cols)
            x = gx_lo + tile_w * col
            z = gz_hi - tile_h * (row + 1)
            out.append((x + 0.012, z + 0.012, tile_w - 0.024, tile_h - 0.024, gauge))
        return out

    def build_ui(self):
        left, right = self.bounds()
        mid = (left + right) / 2
        self.ui.add_button("run", "Run Dyno Pull", ((mid + right) / 2, 0, -0.30), (0.46, 0.12),
                           self.start_pull, self.game.car.flashed and not self.running, GREEN_2)
        # Gauge frames and labels are persistent; values/fill sizes are edited live.
        for index, (x, z, w, h, gauge) in enumerate(self._gauge_layout()):
            label, _key, lo, hi, _danger, unit, _dec = gauge
            cx = x + w / 2
            xr, zt = x + w, z + h
            self.ui.add_frame(f"g{index}-tile", frame_size=(x, xr, z, zt), color=DYNO_TILE, border=LINE)
            self.ui.add_frame(f"g{index}-green", frame_size=(x, xr, z, z), color=DYNO_ZONE_GREEN, border=None)
            self.ui.add_frame(f"g{index}-red", frame_size=(x, xr, z, z), color=DYNO_ZONE_RED, border=None, is_visible=False)
            self.ui.add_text(f"g{index}-title", label, (cx, 0, z + h - 0.045), 0.024, TEXT, CENTER)
            for i in range(3):
                self.ui.add_text(f"g{index}-s{i}", f"{lo + (hi - lo) * i / 2:.0f}", (x + 0.02, 0, z + h * i / 2 - 0.008), 0.020, DIM)
            self.ui.add_text(f"g{index}-val", "", (cx, 0, z + h * 0.44), 0.058, WHITE, CENTER)
            self.ui.add_text(f"g{index}-mm", "", (cx, 0, z + h * 0.26), 0.022, DIM, CENTER)
            self.ui.add_text(f"g{index}-unit", unit, (cx, 0, z + 0.025), 0.022, DIM, CENTER)
        # Graph + controls labels.
        gx0p = mid + 0.04
        self.ui.add_text("graph-title", "POWER  whp : rpm", (gx0p + 0.03, 0, 0.45), 0.026, DYNO_TRACE)
        self.ui.add_text("graph-z", "", (gx0p + 0.03, 0, 0.40), 0.022, DIM)
        self.ui.add_text("graph-t", f"T[{round(DYNO_RPM_RANGE[1])}]", (right - 0.03, 0, 0.40), 0.022, DIM, TextNode.ARight)
        self.ui.add_text("status", "", ((mid + right) / 2, 0, -0.42), 0.034, DIM, CENTER)
        self.ui.add_text("grade", "", ((mid + right) / 2, 0, -0.54), 0.034, DIM, CENTER, wordwrap=30)
        self._build_graph_objects(mid + 0.04, right, -0.16, 0.50)

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
        gx0, gx1, gz0, gz1 = x0 + 0.06, x1 - 0.05, z0 + 0.06, z1 - 0.16
        for i in range(5):
            gx = gx0 + (gx1 - gx0) * i / 4
            self.ui.add_frame(f"graph-grid-x-{i}", frame_size=(gx, gx + 0.003, gz0, gz1),
                              color=DYNO_GRID, border=None)
            gz = gz0 + (gz1 - gz0) * i / 4
            self.ui.add_frame(f"graph-grid-z-{i}", frame_size=(gx0, gx1, gz, gz + 0.003),
                              color=DYNO_GRID, border=None)
        self._graph_box = (gx0, gx1, gz0, gz1)
        self._update_graph_scale()

    def _update_graph_scale(self):
        peak = round(max((p["pw"] for p in self.points), default=0))
        self.ui.get("graph-z").text(f"Z[{peak}]")

    def _draw_graph(self):
        if self.graph is not None:
            self.graph.removeNode()
            self.graph = None
        self._update_graph_scale()
        box = getattr(self, "_graph_box", None)
        if not box or not self.points:
            return
        gx0, gx1, gz0, gz1 = box
        lo, hi = DYNO_RPM_RANGE
        peak = max((p["pw"] for p in self.points), default=1) or 1
        cur_rpm = lo + (hi - lo) * self.pull_t
        segs = LineSegs()
        segs.setThickness(2.6)
        segs.setColor(*DYNO_TRACE)
        started = False
        for point in self.points:
            if point["rpm"] > cur_rpm:
                break
            gx = gx0 + (point["rpm"] - lo) / (hi - lo) * (gx1 - gx0)
            gz = gz0 + clamp(point["pw"] / peak, 0, 1) * (gz1 - gz0)
            segs.drawTo(gx, 0, gz) if started else segs.moveTo(gx, 0, gz)
            started = True
        if started:
            self.graph = self.root.attachNewNode(segs.create())

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
