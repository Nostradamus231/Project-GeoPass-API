import sys
from pathlib import Path
from shapely.geometry import Polygon

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from calc_engine import voronoi_weights, calculate_deposit


def test_square_four_boreholes():
    contour = Polygon([(0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0)])
    points = [(10.0, 10.0), (90.0, 10.0), (90.0, 90.0), (10.0, 90.0)]
    weights, fb = voronoi_weights(points, contour, return_fallback=True)
    assert not fb
    assert len(weights) == 4
    for w in weights:
        assert abs(w - 2500.0) < 1e-4


def test_two_boreholes_sum():
    contour = Polygon([(0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0)])
    points = [(20.0, 50.0), (80.0, 50.0)]
    weights, fb = voronoi_weights(points, contour, return_fallback=True)
    assert fb
    assert abs(sum(weights) - 10000.0) < 1e-4
    assert abs(weights[0] - 5000.0) < 1e-4
    assert abs(weights[1] - 5000.0) < 1e-4


def test_order_invariance():
    contour = Polygon([(0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0)])
    pts1 = [(10.0, 10.0), (90.0, 10.0), (90.0, 90.0), (10.0, 90.0)]
    w1 = voronoi_weights(pts1, contour)
    pts2 = [(90.0, 90.0), (10.0, 10.0), (10.0, 90.0), (90.0, 10.0)]
    w2 = voronoi_weights(pts2, contour)
    m1 = {pts1[i]: w1[i] for i in range(len(pts1))}
    m2 = {pts2[i]: w2[i] for i in range(len(pts2))}
    for pt in pts1:
        assert abs(m1[pt] - m2[pt]) < 1e-4


def test_fallback_collinear():
    contour = Polygon([(0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0)])
    pts_collinear = [(20.0, 20.0), (50.0, 50.0), (80.0, 80.0)]
    weights, fb = voronoi_weights(pts_collinear, contour, return_fallback=True)
    assert fb
    assert len(weights) == 3
    for w in weights:
        assert abs(w - 10000.0 / 3.0) < 1e-4


def test_v1_baseline_manual():
    payload = {
        "company_name": "ТОО Тестовый Карьер",
        "deposit_name": "Северное",
        "license_number": "ЛИЦ-001",
        "mineral_type": "Песок строительный",
        "region": "Костанайская область",
        "coordinate_system": "local_metric",
        "contour": [
            {"x": 0.0, "y": 0.0},
            {"x": 100.0, "y": 0.0},
            {"x": 100.0, "y": 100.0},
            {"x": 0.0, "y": 100.0},
        ],
        "boreholes": [
            {"borehole_id": "S-1", "x": 10.0, "y": 10.0, "thickness_m": 5.0, "weight": 1.0},
            {"borehole_id": "S-2", "x": 90.0, "y": 10.0, "thickness_m": 5.0, "weight": 1.0},
            {"borehole_id": "S-3", "x": 90.0, "y": 90.0, "thickness_m": 5.0, "weight": 1.0},
            {"borehole_id": "S-4", "x": 10.0, "y": 90.0, "thickness_m": 5.0, "weight": 1.0},
        ],
        "quality": {
            "modulus_fineness": 2.1,
            "clay_content_pct": 3.5,
            "moisture_pct": 4.0,
            "bulk_density_t_m3": 1.5,
        },
        "density_t_m3": 1.6,
        "declared_area_ha": 1.0,
    }
    res = calculate_deposit(payload)
    assert res["area_m2"] == 10000.0
    assert res["thickness_weighted_m"] == 5.0
    assert res["thickness_arithmetic_m"] == 5.0
    assert res["reserves_t"] == 80000.0
    assert res["reserves_kt"] == 80.0
    assert res["weighting_method"] == "manual"
    assert res["weighting_fallback"] is False


def test_v1_voronoi_mode():
    payload = {
        "company_name": "ТОО Тестовый Карьер",
        "deposit_name": "Северное",
        "license_number": "ЛИЦ-001",
        "mineral_type": "Песок строительный",
        "region": "Костанайская область",
        "coordinate_system": "local_metric",
        "contour": [
            {"x": 0.0, "y": 0.0},
            {"x": 100.0, "y": 0.0},
            {"x": 100.0, "y": 100.0},
            {"x": 0.0, "y": 100.0},
        ],
        "boreholes": [
            {"borehole_id": "S-1", "x": 10.0, "y": 10.0, "thickness_m": 4.0, "weight": 99.0},
            {"borehole_id": "S-2", "x": 90.0, "y": 10.0, "thickness_m": 6.0, "weight": 99.0},
            {"borehole_id": "S-3", "x": 90.0, "y": 90.0, "thickness_m": 4.0, "weight": 99.0},
            {"borehole_id": "S-4", "x": 10.0, "y": 90.0, "thickness_m": 6.0, "weight": 99.0},
        ],
        "quality": {
            "modulus_fineness": 2.1,
            "clay_content_pct": 3.5,
            "moisture_pct": 4.0,
            "bulk_density_t_m3": 1.5,
        },
        "density_t_m3": 1.6,
        "declared_area_ha": 1.0,
        "weighting_method": "voronoi",
    }
    res = calculate_deposit(payload)
    assert res["area_m2"] == 10000.0
    assert res["thickness_weighted_m"] == 5.0
    assert res["thickness_arithmetic_m"] == 5.0
    assert res["reserves_t"] == 80000.0
    assert res["weighting_method"] == "voronoi"
    assert res["weighting_fallback"] is False


def test_stats_metrics():
    from experiments.stats_utils import compute_metrics, compute_win_rate
    m_zero = compute_metrics([0.0, 0.0, 0.0])
    assert m_zero["bias"] == 0.0
    assert m_zero["rmse"] == 0.0
    assert m_zero["mae"] == 0.0
    m_sym = compute_metrics([-0.1, 0.1])
    assert abs(m_sym["bias"]) < 1e-6
    assert abs(m_sym["rmse"] - 0.1) < 1e-6
    assert abs(m_sym["mae"] - 0.1) < 1e-6
    wr = compute_win_rate([0.2, 0.2, 0.05], [0.1, 0.1, 0.1])
    assert abs(wr - 2.0 / 3.0) < 1e-6


def test_sign_test_ten_of_ten():
    from experiments.stats_utils import sign_test_p_value
    diffs = [1.0] * 10
    p = sign_test_p_value(diffs)
    assert abs(p - 0.001953125) < 1e-6


def test_bootstrap_ci():
    from experiments.stats_utils import paired_bootstrap_ci
    e_a = [0.1] * 50
    e_v = [0.0] * 50
    res = paired_bootstrap_ci(e_a, e_v, n_resamples=50, seed=42)
    assert abs(res["delta_bias_ci"][0] - 0.1) < 1e-5
    assert abs(res["delta_bias_ci"][1] - 0.1) < 1e-5


def test_estimators():
    from experiments.estimators import estimate_arithmetic, estimate_voronoi
    contour = Polygon([(0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0)])
    points = [(10.0, 10.0), (90.0, 10.0), (90.0, 90.0), (10.0, 90.0)]
    thick = [4.0, 6.0, 4.0, 6.0]
    ea = estimate_arithmetic(thick)
    ev = estimate_voronoi(points, thick, contour)
    assert abs(ea - 5.0) < 1e-6
    assert abs(ev - 5.0) < 1e-6


def test_field_modes():
    import numpy as np
    from experiments.synthetic_field import SyntheticField
    f_def = SyntheticField(123, 0.25)
    f_edge = SyntheticField(123, 0.25, field_mode="edge_thin")
    assert abs(f_def.field_value(100.0, 100.0) - 3.252471572011291) < 1e-9
    assert abs(f_edge.field_value(100.0, 100.0) - 3.252471572011291) < 1e-9

    all_c, all_e, all_o = [], [], []
    for s in range(200):
        f_neu = SyntheticField(seed=s, target_cv=0.25, field_mode="neutral")
        assert abs(f_neu.actual_cv - 0.25) <= 0.03
        mx = (f_neu.grid_x >= 250) & (f_neu.grid_x <= 750) & (f_neu.grid_y >= 150) & (f_neu.grid_y <= 450)
        vals = f_neu.field_value(f_neu.grid_x, f_neu.grid_y)
        all_c.append(np.mean(vals[mx]))
        all_e.append(np.mean(vals[~mx]))
        all_o.append(np.mean(vals))
    diff = abs(np.mean(all_c) - np.mean(all_e)) / np.mean(all_o)
    assert diff < 0.05


def run_tests():
    test_square_four_boreholes()
    test_two_boreholes_sum()
    test_order_invariance()
    test_fallback_collinear()
    test_v1_baseline_manual()
    test_v1_voronoi_mode()
    test_stats_metrics()
    test_sign_test_ten_of_ten()
    test_bootstrap_ci()
    test_estimators()
    test_field_modes()
    print("ALL EXPERIMENT TESTS PASSED")


if __name__ == "__main__":
    run_tests()
