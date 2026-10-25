import math
import numpy as np


def compute_metrics(errors: list[float] | np.ndarray) -> dict[str, float]:
    arr = np.asarray(errors, dtype=float)
    if len(arr) == 0:
        return {
            "bias": 0.0,
            "rmse": 0.0,
            "mae": 0.0,
            "p95": 0.0,
        }
    bias = float(np.mean(arr))
    rmse = float(np.sqrt(np.mean(arr * arr)))
    mae = float(np.median(np.abs(arr)))
    p95 = float(np.percentile(np.abs(arr), 95))
    return {
        "bias": bias,
        "rmse": rmse,
        "mae": mae,
        "p95": p95,
    }


def compute_win_rate(errors_arith: list[float] | np.ndarray, errors_voronoi: list[float] | np.ndarray) -> float:
    e_a = np.asarray(errors_arith, dtype=float)
    e_v = np.asarray(errors_voronoi, dtype=float)
    if len(e_a) == 0 or len(e_a) != len(e_v):
        return 0.0
    wins = np.abs(e_v) < np.abs(e_a)
    return float(np.mean(wins))


def sign_test_p_value(diffs: list[float] | np.ndarray) -> float:
    arr = np.asarray(diffs, dtype=float)
    valid = arr[arr != 0]
    n = len(valid)
    if n == 0:
        return 1.0
    k = int(np.sum(valid > 0))
    m = min(k, n - k)
    prob = sum(math.comb(n, j) for j in range(m + 1)) * (0.5 ** n)
    return min(1.0, float(2.0 * prob))


def paired_bootstrap_ci(
    errors_arith: list[float] | np.ndarray,
    errors_voronoi: list[float] | np.ndarray,
    n_resamples: int = 5000,
    seed: int = 20261025,
) -> dict[str, tuple[float, float]]:
    e_a = np.asarray(errors_arith, dtype=float)
    e_v = np.asarray(errors_voronoi, dtype=float)
    n = len(e_a)
    if n == 0 or n != len(e_v):
        return {
            "delta_bias_ci": (0.0, 0.0),
            "delta_rmse_ci": (0.0, 0.0),
        }

    rng = np.random.default_rng(int(seed))
    idx_matrix = rng.integers(0, n, size=(int(n_resamples), n))

    sample_a = e_a[idx_matrix]
    sample_v = e_v[idx_matrix]

    bias_a = np.mean(sample_a, axis=1)
    bias_v = np.mean(sample_v, axis=1)
    diff_bias = bias_a - bias_v

    rmse_a = np.sqrt(np.mean(sample_a * sample_a, axis=1))
    rmse_v = np.sqrt(np.mean(sample_v * sample_v, axis=1))
    diff_rmse = rmse_a - rmse_v

    delta_bias_ci = (float(np.percentile(diff_bias, 2.5)), float(np.percentile(diff_bias, 97.5)))
    delta_rmse_ci = (float(np.percentile(diff_rmse, 2.5)), float(np.percentile(diff_rmse, 97.5)))

    return {
        "delta_bias_ci": delta_bias_ci,
        "delta_rmse_ci": delta_rmse_ci,
    }
