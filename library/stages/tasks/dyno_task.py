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
    live = True

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
            self.game.finish_dyno(self.result)  # record + grade-based toast/Dave quip
            self.dirty = True
        self._sample()
        self.spin -= dt * 1700
        for wheel in self.wheels:
            wheel.setP(self.spin)
        self.app.audio.set_engine(self.values["rpm"], AUDIO["pull_load"])
        if finished:  # lift off at redline -> overrun crackle
            self.app.audio.bov()
            self.app.audio.overrun(self.game.car.active_pop(), 1.1)
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

    # -- UI ----------------------------------------------------------------
    def build_buttons(self):
        left, right = self.bounds()
        cx = ((left + right) / 2 + right) / 2
        self.buttons.add("run", "Run Dyno Pull", (cx, 0, -0.30), (0.46, 0.12), self.start_pull,
                         self.game.car.flashed and not self.running, GREEN_2)

    def build_ui(self, left, right):
        mid = (left + right) / 2
        cols, rows = 2, 3
        gx_lo, gx_hi, gz_lo, gz_hi = left, mid - 0.03, -0.60, 0.50
        tile_w, tile_h = (gx_hi - gx_lo) / cols, (gz_hi - gz_lo) / rows
        for index, gauge in enumerate(DYNO_GAUGES):
            row, col = divmod(index, cols)
            x = gx_lo + tile_w * col
            z = gz_hi - tile_h * (row + 1)
            self._gauge(x + 0.012, z + 0.012, tile_w - 0.024, tile_h - 0.024, *gauge)
        self._graph_panel(mid + 0.04, right, -0.16, 0.50)
        self._controls(mid, right)
        self._draw_graph()

    def _gauge(self, x, z, w, h, label, key, lo, hi, danger, unit, decimals):
        xr, zt = x + w, z + h
        self.frame((x, xr, z, zt), color=DYNO_TILE, border=LINE)
        value = self.values.get(key, 0.0)
        vf = clamp((value - lo) / (hi - lo), 0, 1)
        df = clamp((danger - lo) / (hi - lo), 0, 1)
        green_top = z + h * min(vf, df)
        self.frame((x, xr, z, green_top), color=DYNO_ZONE_GREEN, border=None)
        if vf > df:
            self.frame((x, xr, z + h * df, z + h * vf), color=DYNO_ZONE_RED, border=None)
        for i in range(3):
            self.label(f"{lo + (hi - lo) * i / 2:.0f}", (x + 0.02, 0, z + h * i / 2 - 0.008), 0.020, DIM)
        cx = x + w / 2
        self.label(label, (cx, 0, zt - 0.045), 0.024, TEXT, align=CENTER)
        self.label(self._fmt(value, decimals), (cx, 0, z + h * 0.44), 0.058, WHITE, align=CENTER)
        self.label(f"{self._fmt(self.vmin.get(key, value), decimals)} : {self._fmt(self.vmax.get(key, value), decimals)}", (cx, 0, z + h * 0.26), 0.022, DIM, align=CENTER)
        self.label(unit, (cx, 0, z + 0.025), 0.022, DIM, align=CENTER)

    @staticmethod
    def _fmt(value, decimals):
        return f"{value:.{decimals}f}"

    def _graph_panel(self, x0, x1, z0, z1):
        self.frame((x0, x1, z0, z1), color=DYNO_TILE, border=LINE)
        self.label("POWER  whp : rpm", (x0 + 0.03, 0, z1 - 0.05), 0.026, DYNO_TRACE)
        peak = round(max((p["pw"] for p in self.points), default=0))
        self.label(f"Z[{peak}]", (x0 + 0.03, 0, z1 - 0.10), 0.022, DIM)
        self.label(f"T[{round(DYNO_RPM_RANGE[1])}]", (x1 - 0.03, 0, z1 - 0.10), 0.022, DIM, align=TextNode.ARight)
        gx0, gx1, gz0, gz1 = x0 + 0.06, x1 - 0.05, z0 + 0.06, z1 - 0.16
        for i in range(5):
            gx = gx0 + (gx1 - gx0) * i / 4
            self.frame((gx, gx + 0.003, gz0, gz1), color=DYNO_GRID, border=None)
            gz = gz0 + (gz1 - gz0) * i / 4
            self.frame((gx0, gx1, gz, gz + 0.003), color=DYNO_GRID, border=None)
        self._graph_box = (gx0, gx1, gz0, gz1)

    def _draw_graph(self):
        if self.graph is not None:
            self.graph.removeNode()
            self.graph = None
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

    def _controls(self, mid, right):
        game = self.game
        cx = (mid + right) / 2
        self.buttons.get("run").enabled(game.car.flashed and not self.running)
        if self.running:
            state, color = f"pulling... {round(self.values['rpm'])} rpm", AMBER
        elif game.car.flashed:
            state, color = "Loaded. Send it.", DIM
        else:
            state, color = "Flash a tune first.", DIM
        self.label(state, (cx, 0, -0.42), 0.034, color, align=CENTER)
        grade = game.car.grade
        self.label(grade or "Run a pull to grade the map.", (cx, 0, -0.54), 0.034, GREEN if grade.startswith("Grade") else DIM, align=CENTER, wordwrap=30)
