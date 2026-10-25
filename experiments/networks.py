import numpy as np
from shapely.geometry import Point, Polygon


def _is_valid_point(x: float, y: float, existing: list[tuple[float, float]], poly: Polygon, min_dist: float = 5.0) -> bool:
    if not poly.contains(Point(x, y)):
        return False
    min_dist_sq = min_dist * min_dist
    for ex, ey in existing:
        if (x - ex) * (x - ex) + (y - ey) * (y - ey) < min_dist_sq:
            return False
    return True


def generate_regular(poly: Polygon, n: int, seed: int) -> list[tuple[float, float]]:
    rng = np.random.default_rng(int(seed))
    minx, miny, maxx, maxy = poly.bounds
    w = maxx - minx
    h = maxy - miny
    aspect = w / h if h > 0 else 1.0
    ny = max(1, int(round(np.sqrt(n / aspect))))
    nx = max(1, int(np.ceil(n / ny)))
    pts: list[tuple[float, float]] = []
    while len(pts) < n:
        dx = w / (nx + 1)
        dy = h / (ny + 1)
        pts = []
        for i in range(1, nx + 1):
            for j in range(1, ny + 1):
                jx = float(rng.uniform(-0.1 * dx, 0.1 * dx))
                jy = float(rng.uniform(-0.1 * dy, 0.1 * dy))
                px = minx + i * dx + jx
                py = miny + j * dy + jy
                if _is_valid_point(px, py, pts, poly):
                    pts.append((px, py))
        if len(pts) >= n:
            break
        nx += 1
        ny += 1
    return pts[:n]


def generate_random(poly: Polygon, n: int, seed: int) -> list[tuple[float, float]]:
    rng = np.random.default_rng(int(seed))
    minx, miny, maxx, maxy = poly.bounds
    pts: list[tuple[float, float]] = []
    attempts = 0
    while len(pts) < n and attempts < 100000:
        attempts += 1
        x = float(rng.uniform(minx, maxx))
        y = float(rng.uniform(miny, maxy))
        if _is_valid_point(x, y, pts, poly):
            pts.append((x, y))
    return pts


def generate_clustered(poly: Polygon, n: int, seed: int) -> list[tuple[float, float]]:
    rng = np.random.default_rng(int(seed))
    minx, miny, maxx, maxy = poly.bounds
    k_clusters = int(rng.integers(2, 4))
    centers: list[tuple[float, float]] = []
    while len(centers) < k_clusters:
        cx = float(rng.uniform(minx, maxx))
        cy = float(rng.uniform(miny, maxy))
        if poly.contains(Point(cx, cy)):
            centers.append((cx, cy))
    n_cluster_pts = int(round(0.7 * n))
    pts: list[tuple[float, float]] = []
    attempts = 0
    while len(pts) < n_cluster_pts and attempts < 20000:
        attempts += 1
        c_idx = int(rng.integers(0, k_clusters))
        cx, cy = centers[c_idx]
        px = float(rng.normal(cx, 50.0))
        py = float(rng.normal(cy, 50.0))
        if _is_valid_point(px, py, pts, poly):
            pts.append((px, py))
    attempts = 0
    while len(pts) < n and attempts < 20000:
        attempts += 1
        px = float(rng.uniform(minx, maxx))
        py = float(rng.uniform(miny, maxy))
        if _is_valid_point(px, py, pts, poly):
            pts.append((px, py))
    return pts


def generate_preferential(poly: Polygon, field, n: int, k: int, seed: int) -> list[tuple[float, float]]:
    rng = np.random.default_rng(int(seed))
    minx, miny, maxx, maxy = poly.bounds
    max_t = field.max_t
    pts: list[tuple[float, float]] = []
    attempts = 0
    while len(pts) < n and attempts < 100000:
        attempts += 1
        px = float(rng.uniform(minx, maxx))
        py = float(rng.uniform(miny, maxy))
        if not poly.contains(Point(px, py)):
            continue
        t_val = float(field.field_value(px, py))
        prob = (t_val / max_t) ** k
        if rng.uniform(0.0, 1.0) <= prob:
            if _is_valid_point(px, py, pts, poly):
                pts.append((px, py))
    return pts


def generate_network(network_type: str, poly: Polygon, field, n: int, seed: int) -> list[tuple[float, float]]:
    if network_type == "regular":
        return generate_regular(poly, n, seed)
    if network_type == "random":
        return generate_random(poly, n, seed)
    if network_type == "clustered":
        return generate_clustered(poly, n, seed)
    if network_type == "preferential_k1":
        return generate_preferential(poly, field, n, 1, seed)
    if network_type == "preferential_k2":
        return generate_preferential(poly, field, n, 2, seed)
    raise ValueError(f"Unknown network type: {network_type}")
