import csv
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from shapely.geometry import Polygon, MultiPoint, Point
from shapely.ops import voronoi_diagram

from experiments.synthetic_field import SyntheticField, RECT_CONTOUR
from experiments.networks import generate_network

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "DejaVu Serif", "Times", "serif"],
    "font.size": 8.0,
    "axes.labelsize": 8.5,
    "axes.titlesize": 9.0,
    "xtick.labelsize": 7.5,
    "ytick.labelsize": 7.5,
    "legend.fontsize": 7.5,
    "figure.titlesize": 10.0,
    "figure.dpi": 300,
    "savefig.dpi": 300,
})


def make_figure1(out_dir: Path):
    sf = SyntheticField(seed=42, target_cv=0.25, contour_coords=RECT_CONTOUR)
    poly = sf.poly
    minx, miny, maxx, maxy = poly.bounds
    gx = np.linspace(minx, maxx, 100)
    gy = np.linspace(miny, maxy, 80)
    xx, yy = np.meshgrid(gx, gy)
    grid_t = sf.field_value(xx, yy)

    net_specs = [
        ("regular", "(a) Regular network (n=16)", 42),
        ("clustered", "(b) Clustered network (n=16)", 105),
        ("preferential_k2", "(c) Preferential sampling (k=2, n=16)", 210),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(6.2, 2.5), constrained_layout=True)

    dx = max(maxx - minx, 10.0)
    dy = max(maxy - miny, 10.0)
    env_poly = Polygon([
        (minx - 2 * dx, miny - 2 * dy),
        (maxx + 2 * dx, miny - 2 * dy),
        (maxx + 2 * dx, maxy + 2 * dy),
        (minx - 2 * dx, maxy + 2 * dy),
    ])

    cax_mappable = None
    for idx, (net_type, title, seed_val) in enumerate(net_specs):
        ax = axes[idx]
        cf = ax.contourf(xx, yy, grid_t, levels=8, cmap="Greys", alpha=0.55)
        cax_mappable = cf
        ax.contour(xx, yy, grid_t, levels=6, colors="#555555", linewidths=0.5, alpha=0.7)

        pts = generate_network(net_type, poly, sf, 16, seed_val)
        pt_objs = [Point(float(px), float(py)) for px, py in pts]
        vd = voronoi_diagram(MultiPoint(pt_objs), envelope=env_poly)

        for cell in vd.geoms:
            clipped = cell.intersection(poly)
            if not clipped.is_empty:
                if clipped.geom_type == "Polygon":
                    cx_coords, cy_coords = clipped.exterior.xy
                    ax.plot(cx_coords, cy_coords, color="black", linestyle="--", linewidth=0.6)
                elif clipped.geom_type == "MultiPolygon":
                    for sub_poly in clipped.geoms:
                        cx_coords, cy_coords = sub_poly.exterior.xy
                        ax.plot(cx_coords, cy_coords, color="black", linestyle="--", linewidth=0.6)

        bx = [p[0] for p in pts]
        by = [p[1] for p in pts]
        ax.scatter(bx, by, c="black", s=18, marker="o", edgecolors="white", linewidths=0.5, zorder=5)

        bx_poly, by_poly = poly.exterior.xy
        ax.plot(bx_poly, by_poly, color="black", linewidth=1.0)

        ax.set_title(title, pad=4)
        ax.set_xlabel("X coordinate [m]")
        if idx == 0:
            ax.set_ylabel("Y coordinate [m]")
        ax.set_xlim(minx, maxx)
        ax.set_ylim(miny, maxy)
        ax.set_aspect("equal", adjustable="box")

    cbar = fig.colorbar(cax_mappable, ax=axes, orientation="horizontal", fraction=0.06, pad=0.18, aspect=35)
    cbar.set_label("Deposit thickness, T [m]")

    out_file = out_dir / "figure1_field_networks.jpg"
    plt.savefig(out_file, format="jpeg", dpi=300, pil_kwargs={"quality": 95})
    plt.close()


def make_figure2(raw_csv_path: Path, out_dir: Path):
    data_arith = {
        "regular": [],
        "random": [],
        "clustered": [],
        "preferential_k1": [],
        "preferential_k2": [],
    }
    data_voronoi = {
        "regular": [],
        "random": [],
        "clustered": [],
        "preferential_k1": [],
        "preferential_k2": [],
    }

    with open(raw_csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r["scenario"] == "cv_med" and r["contour"] == "rect" and int(r["n"]) == 16:
                nt = r["network_type"]
                if nt in data_arith:
                    data_arith[nt].append(float(r["error_arith"]) * 100.0)
                    data_voronoi[nt].append(float(r["error_voronoi"]) * 100.0)

    fig, ax = plt.subplots(figsize=(6.2, 3.8), constrained_layout=True)

    categories = ["regular", "random", "clustered", "preferential_k1", "preferential_k2"]
    x_labels = ["Regular", "Random", "Clustered", "Preferential\n(k=1)", "Preferential\n(k=2)"]
    x_positions = np.arange(len(categories))
    width = 0.32

    bp_arith = ax.boxplot(
        [data_arith[c] for c in categories],
        positions=x_positions - width / 2.0,
        widths=width * 0.85,
        patch_artist=True,
        showmeans=False,
        showfliers=False,
        medianprops={"color": "black", "linewidth": 1.2},
        boxprops={"facecolor": "#d9d9d9", "edgecolor": "black", "hatch": "//", "linewidth": 0.8},
        whiskerprops={"color": "black", "linewidth": 0.8},
        capprops={"color": "black", "linewidth": 0.8},
    )

    bp_voronoi = ax.boxplot(
        [data_voronoi[c] for c in categories],
        positions=x_positions + width / 2.0,
        widths=width * 0.85,
        patch_artist=True,
        showmeans=False,
        showfliers=False,
        medianprops={"color": "black", "linewidth": 1.2},
        boxprops={"facecolor": "#ffffff", "edgecolor": "black", "linewidth": 0.8},
        whiskerprops={"color": "black", "linewidth": 0.8},
        capprops={"color": "black", "linewidth": 0.8},
    )

    ax.axhline(0.0, color="gray", linestyle="--", linewidth=0.8)
    ax.set_xticks(x_positions)
    ax.set_xticklabels(x_labels)
    ax.set_xlabel("Borehole network type")
    ax.set_ylabel("Relative error of reserves estimation, e [%]")
    ax.legend(
        [bp_arith["boxes"][0], bp_voronoi["boxes"][0]],
        ["Arithmetic mean", "Voronoi area-weighted"],
        loc="upper left",
        framealpha=0.9,
    )
    ax.grid(axis="y", linestyle=":", alpha=0.6)

    out_file = out_dir / "figure2_error_boxplots.jpg"
    plt.savefig(out_file, format="jpeg", dpi=300, pil_kwargs={"quality": 95})
    plt.close()


def make_figure3(summary_csv_path: Path, out_dir: Path):
    rows = []
    with open(summary_csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r["scenario"] == "cv_med" and r["contour"] == "rect":
                rows.append(r)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6.2, 3.2), sharey=True, constrained_layout=True)

    styles = {
        "regular": ("#000000", "o", "Regular"),
        "random": ("#444444", "s", "Random"),
        "clustered": ("#666666", "^", "Clustered"),
        "preferential_k1": ("#444444", "D", "Preferential (k=1)"),
        "preferential_k2": ("#000000", "v", "Preferential (k=2)"),
    }

    for nt in ["regular", "random", "clustered"]:
        c, m, lbl = styles[nt]
        sub = [r for r in rows if r["network_type"] == nt]
        sub.sort(key=lambda x: int(x["n"]))
        n_vals = [int(x["n"]) for x in sub]
        rmse_a = [float(x["rmse_arith"]) * 100.0 for x in sub]
        rmse_v = [float(x["rmse_voronoi"]) * 100.0 for x in sub]
        ax1.plot(n_vals, rmse_a, color=c, linestyle="-", marker=m, markersize=4.5, label=f"{lbl} (Arith)")
        ax1.plot(n_vals, rmse_v, color=c, linestyle="--", marker=m, markerfacecolor="white", markersize=4.5, label=f"{lbl} (Voronoi)")

    for nt in ["preferential_k1", "preferential_k2"]:
        c, m, lbl = styles[nt]
        sub = [r for r in rows if r["network_type"] == nt]
        sub.sort(key=lambda x: int(x["n"]))
        n_vals = [int(x["n"]) for x in sub]
        rmse_a = [float(x["rmse_arith"]) * 100.0 for x in sub]
        rmse_v = [float(x["rmse_voronoi"]) * 100.0 for x in sub]
        ax2.plot(n_vals, rmse_a, color=c, linestyle="-", marker=m, markersize=4.5, label=f"{lbl} (Arith)")
        ax2.plot(n_vals, rmse_v, color=c, linestyle="--", marker=m, markerfacecolor="white", markersize=4.5, label=f"{lbl} (Voronoi)")

    ax1.set_title("(a) Unbiased networks")
    ax1.set_xlabel("Number of boreholes, n")
    ax1.set_ylabel("RMSE of reserves estimation [%]")
    ax1.grid(True, linestyle=":", alpha=0.6)
    ax1.legend(loc="upper right", framealpha=0.9, fontsize=6.8)

    ax2.set_title("(b) Preferential sampling")
    ax2.set_xlabel("Number of boreholes, n")
    ax2.grid(True, linestyle=":", alpha=0.6)
    ax2.legend(loc="upper right", framealpha=0.9, fontsize=6.8)

    out_file = out_dir / "figure3_rmse_vs_n.jpg"
    plt.savefig(out_file, format="jpeg", dpi=300, pil_kwargs={"quality": 95})
    plt.close()


def make_figure4(summary_csv_path: Path, out_dir: Path):
    rows = []
    with open(summary_csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r["contour"] == "rect" and r["network_type"] in ("preferential_k1", "preferential_k2"):
                rows.append(r)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6.2, 3.2), sharey=True, constrained_layout=True)

    cv_styles = {
        "cv_low": ("#777777", ":", "o", "Low CV (10%)"),
        "cv_med": ("#444444", "--", "s", "Medium CV (25%)"),
        "cv_high": ("#000000", "-", "^", "High CV (50%)"),
    }

    for sc in ["cv_low", "cv_med", "cv_high"]:
        c, ls, m, lbl = cv_styles[sc]
        sub1 = [r for r in rows if r["network_type"] == "preferential_k1" and r["scenario"] == sc]
        sub1.sort(key=lambda x: int(x["n"]))
        n_vals1 = [int(x["n"]) for x in sub1]
        bias_a1 = [float(x["bias_arith"]) * 100.0 for x in sub1]
        bias_v1 = [float(x["bias_voronoi"]) * 100.0 for x in sub1]

        ax1.plot(n_vals1, bias_a1, color=c, linestyle=ls, marker=m, markersize=4.5, label=f"{lbl} Arith")
        ax1.plot(n_vals1, bias_v1, color=c, linestyle=ls, marker=m, markerfacecolor="white", markersize=4.5, alpha=0.7)

    for sc in ["cv_low", "cv_med", "cv_high"]:
        c, ls, m, lbl = cv_styles[sc]
        sub2 = [r for r in rows if r["network_type"] == "preferential_k2" and r["scenario"] == sc]
        sub2.sort(key=lambda x: int(x["n"]))
        n_vals2 = [int(x["n"]) for x in sub2]
        bias_a2 = [float(x["bias_arith"]) * 100.0 for x in sub2]
        bias_v2 = [float(x["bias_voronoi"]) * 100.0 for x in sub2]

        ax2.plot(n_vals2, bias_a2, color=c, linestyle=ls, marker=m, markersize=4.5, label=f"{lbl} Arith")
        ax2.plot(n_vals2, bias_v2, color=c, linestyle=ls, marker=m, markerfacecolor="white", markersize=4.5, alpha=0.7)

    ax1.axhline(0.0, color="gray", linestyle="-", linewidth=0.6)
    ax2.axhline(0.0, color="gray", linestyle="-", linewidth=0.6)

    ax1.set_title("(a) Preferential sampling (k=1)")
    ax1.set_xlabel("Number of boreholes, n")
    ax1.set_ylabel("Reserves estimation bias, E[e] [%]")
    ax1.grid(True, linestyle=":", alpha=0.6)
    ax1.legend(loc="upper right", framealpha=0.9, fontsize=6.8)

    ax2.set_title("(b) Preferential sampling (k=2)")
    ax2.set_xlabel("Number of boreholes, n")
    ax2.grid(True, linestyle=":", alpha=0.6)
    ax2.legend(loc="upper right", framealpha=0.9, fontsize=6.8)

    out_file = out_dir / "figure4_preferential_bias.jpg"
    plt.savefig(out_file, format="jpeg", dpi=300, pil_kwargs={"quality": 95})
    plt.close()


def main():
    base_dir = Path(__file__).resolve().parent.parent
    results_dir = base_dir / "results"
    fig_dir = results_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    raw_csv = results_dir / "raw_runs.csv"
    summary_csv = results_dir / "summary_by_scenario.csv"

    print("Generating Figure 1 (field maps and networks)...")
    make_figure1(fig_dir)
    print("Generating Figure 2 (error boxplots)...")
    make_figure2(raw_csv, fig_dir)
    print("Generating Figure 3 (RMSE vs n curves)...")
    make_figure3(summary_csv, fig_dir)
    print("Generating Figure 4 (preferential bias vs n and CV)...")
    make_figure4(summary_csv, fig_dir)
    print("ALL 4 FIGURES GENERATED SUCCESSFULLY")


if __name__ == "__main__":
    main()
