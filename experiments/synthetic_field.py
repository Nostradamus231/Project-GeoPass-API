import numpy as np
import shapely
from shapely.geometry import Polygon

RECT_CONTOUR = [(0.0, 0.0), (1000.0, 0.0), (1000.0, 800.0), (0.0, 800.0)]
POLY_CONTOUR = [(0.0, 100.0), (300.0, 0.0), (950.0, 50.0), (1000.0, 650.0), (700.0, 800.0), (50.0, 750.0)]
CONTOURS = {
    "rect": RECT_CONTOUR,
    "poly": POLY_CONTOUR,
}
DENSITY = 1.6


class SyntheticField:
    def __init__(self, seed: int, target_cv: float, contour_coords: list[tuple[float, float]] | None = None, grid_step: float = 5.0):
        self.seed = int(seed)
        self.target_cv = float(target_cv)
        coords = contour_coords if contour_coords is not None else RECT_CONTOUR
        self.poly = Polygon(coords)
        self.area = float(self.poly.area)
        self.grid_step = float(grid_step)

        minx, miny, maxx, maxy = self.poly.bounds
        self.bounds = (minx, miny, maxx, maxy)
        self.cx_mid = 0.5 * (minx + maxx)
        self.cy_mid = 0.5 * (miny + maxy)

        rng = np.random.default_rng(self.seed)
        self.tx = float(rng.uniform(-0.002, 0.002))
        self.ty = float(rng.uniform(-0.002, 0.002))

        num_lenses = int(rng.integers(3, 6))
        self.lenses = []
        for _ in range(num_lenses):
            cx = float(rng.uniform(minx + 0.1 * (maxx - minx), maxx - 0.1 * (maxx - minx)))
            cy = float(rng.uniform(miny + 0.1 * (maxy - miny), maxy - 0.1 * (maxy - miny)))
            sx = float(rng.uniform(80.0, 220.0))
            sy = float(rng.uniform(80.0, 220.0))
            amp = float(rng.uniform(-2.0, 3.5))
            self.lenses.append((cx, cy, sx, sy, amp))

        self.waves = []
        for _ in range(12):
            kx = float(rng.uniform(-0.04, 0.04))
            ky = float(rng.uniform(-0.04, 0.04))
            phi = float(rng.uniform(0.0, 2.0 * np.pi))
            w_amp = float(rng.uniform(0.1, 0.4))
            self.waves.append((kx, ky, phi, w_amp))

        gx = np.arange(minx + 0.5 * self.grid_step, maxx, self.grid_step)
        gy = np.arange(miny + 0.5 * self.grid_step, maxy, self.grid_step)
        xx, yy = np.meshgrid(gx, gy)
        inside_mask = shapely.contains_xy(self.poly, xx.ravel(), yy.ravel())
        self.grid_x = xx.ravel()[inside_mask]
        self.grid_y = yy.ravel()[inside_mask]

        v_grid = self._raw_v(self.grid_x, self.grid_y)
        self.v_mean = float(np.mean(v_grid))
        self.v_std = float(np.std(v_grid))
        if self.v_std < 1e-9:
            self.v_std = 1.0
        v_norm = (v_grid - self.v_mean) / self.v_std

        self.base_m = 5.0
        alpha = self.target_cv
        for _ in range(20):
            t_cand = np.maximum(0.5, self.base_m * (1.0 + alpha * v_norm))
            cur_cv = float(np.std(t_cand) / np.mean(t_cand))
            if abs(cur_cv - self.target_cv) <= 0.005:
                break
            alpha = alpha * (self.target_cv / (cur_cv + 1e-9))

        self.alpha = float(alpha)
        t_final = np.maximum(0.5, self.base_m * (1.0 + self.alpha * v_norm))
        self.actual_cv = float(np.std(t_final) / np.mean(t_final))
        self.true_mean_thickness = float(np.mean(t_final))
        self.true_reserves = float(self.area * self.true_mean_thickness * DENSITY)
        self.max_t = float(np.max(t_final))

    def _raw_v(self, x, y):
        x_arr = np.asarray(x, dtype=float)
        y_arr = np.asarray(y, dtype=float)
        v = self.tx * (x_arr - self.cx_mid) + self.ty * (y_arr - self.cy_mid)
        for cx, cy, sx, sy, amp in self.lenses:
            v = v + amp * np.exp(-(((x_arr - cx)**2) / (2.0 * sx**2) + ((y_arr - cy)**2) / (2.0 * sy**2)))
        for kx, ky, phi, w_amp in self.waves:
            v = v + w_amp * np.sin(kx * x_arr + ky * y_arr + phi)
        return v

    def field_value(self, x, y):
        x_arr = np.asarray(x, dtype=float)
        y_arr = np.asarray(y, dtype=float)
        v = self._raw_v(x_arr, y_arr)
        v_norm = (v - self.v_mean) / self.v_std
        t = np.maximum(0.5, self.base_m * (1.0 + self.alpha * v_norm))
        if isinstance(x, (int, float)) and isinstance(y, (int, float)):
            return float(t)
        return t
