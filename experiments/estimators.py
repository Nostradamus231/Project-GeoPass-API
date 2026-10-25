import numpy as np
from shapely.geometry import Polygon
from calc_engine import voronoi_weights


def estimate_arithmetic(thickness: list[float] | np.ndarray) -> float:
    arr = np.asarray(thickness, dtype=float)
    if len(arr) == 0:
        return 0.0
    return float(np.mean(arr))


def estimate_voronoi(points: list[tuple[float, float]], thickness: list[float] | np.ndarray, contour: Polygon) -> float:
    t_arr = np.asarray(thickness, dtype=float)
    if len(t_arr) == 0:
        return 0.0
    weights = voronoi_weights(points, contour)
    w_arr = np.asarray(weights, dtype=float)
    if np.sum(w_arr) <= 0:
        return float(np.mean(t_arr))
    return float(np.average(t_arr, weights=w_arr))
