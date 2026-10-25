import argparse
import csv
from datetime import datetime, timezone
import json
import multiprocessing as mp
import os
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
import shapely

from experiments.synthetic_field import SyntheticField, CONTOURS, DENSITY
from experiments.networks import generate_network
from experiments.estimators import estimate_arithmetic, estimate_voronoi
from experiments.stats_utils import compute_metrics, compute_win_rate, sign_test_p_value, paired_bootstrap_ci

SCENARIOS = {
    "cv_low": 0.10,
    "cv_med": 0.25,
    "cv_high": 0.50,
}
NETWORK_TYPES = [
    "regular",
    "random",
    "clustered",
    "preferential_k1",
    "preferential_k2",
]
N_VALUES = [8, 12, 16, 24, 36]
CONTOUR_NAMES = ["rect", "poly"]

CONTOUR_INDICES = {"rect": 0, "poly": 1}
SCENARIO_INDICES = {"cv_low": 0, "cv_med": 1, "cv_high": 2}
NETWORK_INDICES = {
    "regular": 0,
    "random": 1,
    "clustered": 2,
    "preferential_k1": 3,
    "preferential_k2": 4,
}
N_INDICES = {8: 0, 12: 1, 16: 2, 24: 3, 36: 4}


def _worker_task(args: tuple) -> list[dict]:
    scenario, target_cv, contour_name, r_start, r_end, master_seed = args
    contour_coords = CONTOURS[contour_name]
    c_idx = CONTOUR_INDICES[contour_name]
    sc_idx = SCENARIO_INDICES[scenario]

    rows = []
    for r in range(r_start, r_end):
        field_seed = master_seed + 100000 * c_idx + 10000 * sc_idx + r
        field = SyntheticField(seed=field_seed, target_cv=target_cv, contour_coords=contour_coords)

        for net_type in NETWORK_TYPES:
            net_idx = NETWORK_INDICES[net_type]
            for n_val in N_VALUES:
                n_idx = N_INDICES[n_val]
                net_seed = master_seed + 1000000 * c_idx + 100000 * sc_idx + 10000 * net_idx + 1000 * n_idx + r
                pts = generate_network(net_type, field.poly, field, n_val, net_seed)
                thick = [field.field_value(px, py) for px, py in pts]

                mean_a = estimate_arithmetic(thick)
                reserves_a = field.area * mean_a * DENSITY
                err_a = (reserves_a - field.true_reserves) / field.true_reserves

                mean_v = estimate_voronoi(pts, thick, field.poly)
                reserves_v = field.area * mean_v * DENSITY
                err_v = (reserves_v - field.true_reserves) / field.true_reserves

                rows.append({
                    "scenario": scenario,
                    "contour": contour_name,
                    "network_type": net_type,
                    "n": n_val,
                    "repeat": r,
                    "field_seed": field_seed,
                    "network_seed": net_seed,
                    "target_cv": target_cv,
                    "actual_cv": field.actual_cv,
                    "true_mean_thickness": field.true_mean_thickness,
                    "reserves_true": field.true_reserves,
                    "mean_arith": mean_a,
                    "reserves_arith": reserves_a,
                    "error_arith": err_a,
                    "mean_voronoi": mean_v,
                    "reserves_voronoi": reserves_v,
                    "error_voronoi": err_v,
                })
    return rows


def get_git_commit() -> str:
    try:
        res = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except Exception:
        return "unknown"


def run_experiment(repeats: int = 1000, seed: int = 20261025, out_dir: str = "results", workers: int | None = None):
    start_time_iso = datetime.now(timezone.utc).isoformat()
    t0 = time.time()

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    if workers is None:
        cpu_cnt = os.cpu_count() or 1
        workers = max(1, min(cpu_cnt, 12))

    chunk_size = 25 if repeats >= 50 else 10
    tasks = []
    for sc_name, sc_cv in SCENARIOS.items():
        for c_name in CONTOUR_NAMES:
            for r_start in range(0, repeats, chunk_size):
                r_end = min(r_start + chunk_size, repeats)
                tasks.append((sc_name, sc_cv, c_name, r_start, r_end, seed))

    total_tasks = len(tasks)
    print(f"Starting experiment: {repeats} repeats, seed {seed}, {total_tasks} batches across {workers} workers")

    raw_runs: list[dict] = []
    completed_tasks = 0
    with mp.Pool(processes=workers) as pool:
        for batch_rows in pool.imap_unordered(_worker_task, tasks):
            raw_runs.extend(batch_rows)
            completed_tasks += 1
            if completed_tasks % 10 == 0 or completed_tasks == total_tasks:
                pct = (completed_tasks / total_tasks) * 100.0
                elapsed = time.time() - t0
                print(f"Progress: {completed_tasks}/{total_tasks} batches ({pct:.1f}%) in {elapsed:.1f}s")

    raw_runs.sort(key=lambda r: (
        SCENARIO_INDICES[r["scenario"]],
        CONTOUR_INDICES[r["contour"]],
        NETWORK_INDICES[r["network_type"]],
        N_INDICES[r["n"]],
        r["repeat"],
    ))

    raw_fields = [
        "scenario",
        "contour",
        "network_type",
        "n",
        "repeat",
        "field_seed",
        "network_seed",
        "target_cv",
        "actual_cv",
        "true_mean_thickness",
        "reserves_true",
        "mean_arith",
        "reserves_arith",
        "error_arith",
        "mean_voronoi",
        "reserves_voronoi",
        "error_voronoi",
    ]
    raw_csv_path = out_path / "raw_runs.csv"
    with open(raw_csv_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=raw_fields)
        writer.writeheader()
        writer.writerows(raw_runs)

    grouped: dict[tuple, list[dict]] = {}
    for r in raw_runs:
        key = (r["scenario"], r["contour"], r["network_type"], r["n"])
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(r)

    summary_rows = []
    for sc_name in SCENARIOS:
        for c_name in CONTOUR_NAMES:
            for net_type in NETWORK_TYPES:
                for n_val in N_VALUES:
                    key = (sc_name, c_name, net_type, n_val)
                    group = grouped.get(key, [])
                    runs_cnt = len(group)
                    if runs_cnt == 0:
                        continue

                    e_a = np.array([item["error_arith"] for item in group], dtype=float)
                    e_v = np.array([item["error_voronoi"] for item in group], dtype=float)
                    actual_cvs = np.array([item["actual_cv"] for item in group], dtype=float)

                    m_a = compute_metrics(e_a)
                    m_v = compute_metrics(e_v)
                    win_rate = compute_win_rate(e_a, e_v)
                    p_val = sign_test_p_value(np.abs(e_a) - np.abs(e_v))

                    delta_bias = m_a["bias"] - m_v["bias"]
                    delta_rmse = m_a["rmse"] - m_v["rmse"]

                    sc_seed = seed + 1000 * SCENARIO_INDICES[sc_name] + 100 * CONTOUR_INDICES[c_name] + 10 * NETWORK_INDICES[net_type] + N_INDICES[n_val]
                    ci_res = paired_bootstrap_ci(e_a, e_v, n_resamples=5000, seed=sc_seed)

                    summary_rows.append({
                        "scenario": sc_name,
                        "contour": c_name,
                        "network_type": net_type,
                        "n": n_val,
                        "runs_count": runs_cnt,
                        "target_cv": SCENARIOS[sc_name],
                        "mean_actual_cv": float(np.mean(actual_cvs)),
                        "bias_arith": m_a["bias"],
                        "bias_voronoi": m_v["bias"],
                        "delta_bias": delta_bias,
                        "delta_bias_ci_lower": ci_res["delta_bias_ci"][0],
                        "delta_bias_ci_upper": ci_res["delta_bias_ci"][1],
                        "rmse_arith": m_a["rmse"],
                        "rmse_voronoi": m_v["rmse"],
                        "delta_rmse": delta_rmse,
                        "delta_rmse_ci_lower": ci_res["delta_rmse_ci"][0],
                        "delta_rmse_ci_upper": ci_res["delta_rmse_ci"][1],
                        "mae_arith": m_a["mae"],
                        "mae_voronoi": m_v["mae"],
                        "p95_abs_err_arith": m_a["p95"],
                        "p95_abs_err_voronoi": m_v["p95"],
                        "voronoi_win_rate": win_rate,
                        "sign_test_p_value": p_val,
                    })

    summary_fields = [
        "scenario",
        "contour",
        "network_type",
        "n",
        "runs_count",
        "target_cv",
        "mean_actual_cv",
        "bias_arith",
        "bias_voronoi",
        "delta_bias",
        "delta_bias_ci_lower",
        "delta_bias_ci_upper",
        "rmse_arith",
        "rmse_voronoi",
        "delta_rmse",
        "delta_rmse_ci_lower",
        "delta_rmse_ci_upper",
        "mae_arith",
        "mae_voronoi",
        "p95_abs_err_arith",
        "p95_abs_err_voronoi",
        "voronoi_win_rate",
        "sign_test_p_value",
    ]
    summary_csv_path = out_path / "summary_by_scenario.csv"
    with open(summary_csv_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=summary_fields)
        writer.writeheader()
        writer.writerows(summary_rows)

    t1 = time.time()
    duration = t1 - t0
    end_time_iso = datetime.now(timezone.utc).isoformat()

    meta = {
        "python_version": sys.version.split()[0],
        "numpy_version": np.__version__,
        "shapely_version": shapely.__version__,
        "seed": seed,
        "repeats": repeats,
        "start_time": start_time_iso,
        "end_time": end_time_iso,
        "duration_seconds": round(duration, 2),
        "git_commit": get_git_commit(),
    }
    meta_path = out_path / "run_meta.json"
    with open(meta_path, mode="w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    print(f"Experiment finished successfully in {duration:.2f} seconds.")
    print(f"Saved: {raw_csv_path}")
    print(f"Saved: {summary_csv_path}")
    print(f"Saved: {meta_path}")


def main():
    parser = argparse.ArgumentParser(description="Run computational experiment for reserves estimation")
    parser.add_argument("--repeats", type=int, default=1000, help="Number of repeats per scenario")
    parser.add_argument("--seed", type=int, default=20261025, help="Master random seed")
    parser.add_argument("--out", type=str, default="results", help="Output directory")
    parser.add_argument("--quick", action="store_true", help="Quick run with 50 repeats")
    parser.add_argument("--workers", type=int, default=None, help="Worker processes")
    args = parser.parse_args()

    reps = 50 if args.quick else args.repeats
    run_experiment(repeats=reps, seed=args.seed, out_dir=args.out, workers=args.workers)


if __name__ == "__main__":
    main()
