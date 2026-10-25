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

    clust_seed = 42
    for s in range(1, 1000):
        rng = np.random.default_rng(s)
        k_c = int(rng.integers(2, 4))
        centers = []
        while len(centers) < k_c:
            cx = float(rng.uniform(minx, maxx))
            cy = float(rng.uniform(miny, maxy))
            if poly.contains(Point(cx, cy)):
                centers.append((cx, cy))
        if all(cx >= minx + 80 and cx <= maxx - 80 and cy >= miny + 80 and cy <= maxy - 80 for cx, cy in centers):
            clust_seed = s
            break

    net_specs = [
        ("regular", "(a) Regular network (n=16)", 42),
        ("clustered", "(b) Clustered network (n=16)", clust_seed),
        ("preferential_k2", "(c) Preferential sampling (k=2, n=16)", 210),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(5.8, 2.5), constrained_layout=True)

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
                    ax.plot(cx_coords, cy_coords, color="black", linestyle="-", linewidth=0.6)
                elif clipped.geom_type == "MultiPolygon":
                    for sub_poly in clipped.geoms:
                        cx_coords, cy_coords = sub_poly.exterior.xy
                        ax.plot(cx_coords, cy_coords, color="black", linestyle="-", linewidth=0.6)

        bx = [p[0] for p in pts]
        by = [p[1] for p in pts]
        ax.scatter(bx, by, c="black", s=18, marker="o", edgecolors="white", linewidths=0.5, zorder=5)

        bx_poly, by_poly = poly.exterior.xy
        ax.plot(bx_poly, by_poly, color="black", linewidth=1.0)

        ax.set_title(title, pad=6)
        ax.set_xlabel("X coordinate [m]")
        if idx == 0:
            ax.set_ylabel("Y coordinate [m]")
        ax.set_xlim(minx, maxx)
        ax.set_ylim(miny, maxy)
        ax.set_aspect("equal", adjustable="box")

    cbar = fig.colorbar(cax_mappable, ax=axes, orientation="horizontal", fraction=0.06, pad=0.18, aspect=35)
    cbar.set_label("Deposit thickness, T [m]")

    out_file = out_dir / "figure1_field_networks.jpg"
    plt.savefig(out_file, format="jpeg", dpi=300, bbox_inches="tight", pil_kwargs={"quality": 95})
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

    fig, ax = plt.subplots(figsize=(5.8, 3.8), constrained_layout=True)

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
        whis=[5, 95],
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
        whis=[5, 95],
        medianprops={"color": "black", "linewidth": 1.2},
        boxprops={"facecolor": "#ffffff", "edgecolor": "black", "hatch": "..", "linewidth": 0.8},
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
        loc="lower center",
        bbox_to_anchor=(0.5, 1.02),
        ncol=2,
        frameon=False,
    )
    ax.grid(axis="y", linestyle=":", alpha=0.6)

    out_file = out_dir / "figure2_error_boxplots.jpg"
    plt.savefig(out_file, format="jpeg", dpi=300, bbox_inches="tight", pil_kwargs={"quality": 95})
    plt.close()


def make_figure3(summary_csv_path: Path, out_dir: Path):
    rows = []
    with open(summary_csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r["scenario"] == "cv_med" and r["contour"] == "rect":
                rows.append(r)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(5.8, 3.4), sharey=True)

    styles = {
        "regular": ("#000000", "o", "Regular"),
        "random": ("#444444", "s", "Random"),
        "clustered": ("#666666", "^", "Clustered"),
        "preferential_k1": ("#444444", "D", "Preferential (k=1)"),
        "preferential_k2": ("#000000", "v", "Preferential (k=2)"),
    }

    lines_handles = []
    lines_labels = []

    for nt in ["regular", "random", "clustered"]:
        c, m, lbl = styles[nt]
        sub = [r for r in rows if r["network_type"] == nt]
        sub.sort(key=lambda x: int(x["n"]))
        n_vals = [int(x["n"]) for x in sub]
        rmse_a = [float(x["rmse_arith"]) * 100.0 for x in sub]
        rmse_v = [float(x["rmse_voronoi"]) * 100.0 for x in sub]
        l1, = ax1.plot(n_vals, rmse_a, color=c, linestyle="-", marker=m, markersize=4.5)
        l2, = ax1.plot(n_vals, rmse_v, color=c, linestyle="--", marker=m, markerfacecolor="white", markersize=4.5)
        lines_handles.extend([l1, l2])
        lines_labels.extend([f"{lbl} (Arith)", f"{lbl} (Voronoi)"])

    for nt in ["preferential_k1", "preferential_k2"]:
        c, m, lbl = styles[nt]
        sub = [r for r in rows if r["network_type"] == nt]
        sub.sort(key=lambda x: int(x["n"]))
        n_vals = [int(x["n"]) for x in sub]
        rmse_a = [float(x["rmse_arith"]) * 100.0 for x in sub]
        rmse_v = [float(x["rmse_voronoi"]) * 100.0 for x in sub]
        l1, = ax2.plot(n_vals, rmse_a, color=c, linestyle="-", marker=m, markersize=4.5)
        l2, = ax2.plot(n_vals, rmse_v, color=c, linestyle="--", marker=m, markerfacecolor="white", markersize=4.5)
        lines_handles.extend([l1, l2])
        lines_labels.extend([f"{lbl} (Arith)", f"{lbl} (Voronoi)"])

    ax1.set_title("(a) Non-preferential networks", pad=6)
    ax1.set_xlabel("Number of boreholes, n")
    ax1.set_ylabel("RMSE of reserves estimation [%]")
    ax1.grid(True, linestyle=":", alpha=0.6)

    ax2.set_title("(b) Preferential sampling", pad=6)
    ax2.set_xlabel("Number of boreholes, n")
    ax2.grid(True, linestyle=":", alpha=0.6)

    fig.legend(
        lines_handles,
        lines_labels,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.02),
        ncol=3,
        columnspacing=0.8,
        frameon=False,
        fontsize=6.8,
    )

    out_file = out_dir / "figure3_rmse_vs_n.jpg"
    plt.savefig(out_file, format="jpeg", dpi=300, bbox_inches="tight", pil_kwargs={"quality": 95})
    plt.close()


def make_figure4(summary_csv_path: Path, out_dir: Path):
    rows = []
    with open(summary_csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r["contour"] == "rect" and r["network_type"] in ("preferential_k1", "preferential_k2"):
                rows.append(r)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(5.8, 3.4), sharey=True)

    cv_styles = {
        "cv_low": ("#777777", ":", "o", "Low CV (10%)"),
        "cv_med": ("#444444", "--", "s", "Medium CV (25%)"),
        "cv_high": ("#000000", "-", "^", "High CV (50%)"),
    }

    legend_handles = []
    legend_labels = []

    for sc in ["cv_low", "cv_med", "cv_high"]:
        c, ls, m, lbl = cv_styles[sc]
        sub1 = [r for r in rows if r["network_type"] == "preferential_k1" and r["scenario"] == sc]
        sub1.sort(key=lambda x: int(x["n"]))
        n_vals1 = [int(x["n"]) for x in sub1]
        bias_a1 = [float(x["bias_arith"]) * 100.0 for x in sub1]
        bias_v1 = [float(x["bias_voronoi"]) * 100.0 for x in sub1]

        l1, = ax1.plot(n_vals1, bias_a1, color=c, linestyle=ls, marker=m, markersize=4.5)
        l2, = ax1.plot(n_vals1, bias_v1, color=c, linestyle=ls, marker=m, markerfacecolor="white", markersize=4.5)
        legend_handles.extend([l1, l2])
        legend_labels.extend([f"{lbl} (Arith)", f"{lbl} (Voronoi)"])

    for sc in ["cv_low", "cv_med", "cv_high"]:
        c, ls, m, lbl = cv_styles[sc]
        sub2 = [r for r in rows if r["network_type"] == "preferential_k2" and r["scenario"] == sc]
        sub2.sort(key=lambda x: int(x["n"]))
        n_vals2 = [int(x["n"]) for x in sub2]
        bias_a2 = [float(x["bias_arith"]) * 100.0 for x in sub2]
        bias_v2 = [float(x["bias_voronoi"]) * 100.0 for x in sub2]

        ax2.plot(n_vals2, bias_a2, color=c, linestyle=ls, marker=m, markersize=4.5)
        ax2.plot(n_vals2, bias_v2, color=c, linestyle=ls, marker=m, markerfacecolor="white", markersize=4.5)

    ax1.axhline(0.0, color="gray", linestyle="-", linewidth=0.7)
    ax2.axhline(0.0, color="gray", linestyle="-", linewidth=0.7)

    ax1.set_title("(a) Preferential sampling (k=1)", pad=6)
    ax1.set_xlabel("Number of boreholes, n")
    ax1.set_ylabel("Reserves estimation bias, E[e] [%]")
    ax1.grid(True, linestyle=":", alpha=0.6)

    ax2.set_title("(b) Preferential sampling (k=2)", pad=6)
    ax2.set_xlabel("Number of boreholes, n")
    ax2.grid(True, linestyle=":", alpha=0.6)

    fig.legend(
        legend_handles,
        legend_labels,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.02),
        ncol=3,
        frameon=False,
        fontsize=7.0,
    )

    out_file = out_dir / "figure4_preferential_bias.jpg"
    plt.savefig(out_file, format="jpeg", dpi=300, bbox_inches="tight", pil_kwargs={"quality": 95})
    plt.close()


def make_figure5(main_summary_csv: Path, neutral_summary_csv: Path, out_dir: Path):
    def read_subset(csv_path: Path) -> dict:
        data = {}
        if not csv_path.exists():
            return data
        with open(csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                if r["scenario"] == "cv_med" and r["contour"] == "rect" and int(r["n"]) == 16:
                    nt = r["network_type"]
                    data[nt] = {
                        "bias_arith": float(r["bias_arith"]) * 100.0,
                        "bias_arith_err": [
                            (float(r["bias_arith"]) - float(r["bias_arith_ci_lower"])) * 100.0,
                            (float(r["bias_arith_ci_upper"]) - float(r["bias_arith"])) * 100.0,
                        ],
                        "bias_voronoi": float(r["bias_voronoi"]) * 100.0,
                        "bias_voronoi_err": [
                            (float(r["bias_voronoi"]) - float(r["bias_voronoi_ci_lower"])) * 100.0,
                            (float(r["bias_voronoi_ci_upper"]) - float(r["bias_voronoi"])) * 100.0,
                        ],
                    }
        return data

    main_data = read_subset(main_summary_csv)
    neutral_data = read_subset(neutral_summary_csv)

    categories = ["regular", "random", "clustered", "preferential_k1", "preferential_k2"]
    x_labels = ["Regular", "Random", "Clustered", "Preferential\n(k=1)", "Preferential\n(k=2)"]
    x_positions = np.arange(len(categories))
    width = 0.19

    fig, ax = plt.subplots(figsize=(5.8, 3.8), constrained_layout=True)

    def get_vals_errs(d, key_val, key_err):
        vals = [d.get(c, {}).get(key_val, 0.0) for c in categories]
        err_low = [d.get(c, {}).get(key_err, [0.0, 0.0])[0] for c in categories]
        err_up = [d.get(c, {}).get(key_err, [0.0, 0.0])[1] for c in categories]
        return vals, np.array([err_low, err_up])

    b1_vals, b1_errs = get_vals_errs(main_data, "bias_arith", "bias_arith_err")
    b2_vals, b2_errs = get_vals_errs(main_data, "bias_voronoi", "bias_voronoi_err")
    b3_vals, b3_errs = get_vals_errs(neutral_data, "bias_arith", "bias_arith_err")
    b4_vals, b4_errs = get_vals_errs(neutral_data, "bias_voronoi", "bias_voronoi_err")

    err_kw = {"elinewidth": 0.8, "capthick": 0.8, "ecolor": "black"}

    b1 = ax.bar(x_positions - 1.5 * width, b1_vals, yerr=b1_errs, capsize=2.0, error_kw=err_kw, width=width * 0.9, label="Edge-thin: Arithmetic", color="#b0b0b0", hatch="//", edgecolor="black", linewidth=0.8)
    b2 = ax.bar(x_positions - 0.5 * width, b2_vals, yerr=b2_errs, capsize=2.0, error_kw=err_kw, width=width * 0.9, label="Edge-thin: Voronoi", color="#ffffff", hatch="//", edgecolor="black", linewidth=0.8)
    b3 = ax.bar(x_positions + 0.5 * width, b3_vals, yerr=b3_errs, capsize=2.0, error_kw=err_kw, width=width * 0.9, label="Neutral: Arithmetic", color="#707070", hatch="xx", edgecolor="black", linewidth=0.8)
    b4 = ax.bar(x_positions + 1.5 * width, b4_vals, yerr=b4_errs, capsize=2.0, error_kw=err_kw, width=width * 0.9, label="Neutral: Voronoi", color="#ffffff", hatch="xx", edgecolor="black", linewidth=0.8)

    ax.axhline(0.0, color="gray", linestyle="-", linewidth=0.8)
    ax.set_xticks(x_positions)
    ax.set_xticklabels(x_labels)
    ax.set_xlabel("Borehole network type")
    ax.set_ylabel("Reserves estimation bias, E[e] [%]")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=2, frameon=False, fontsize=7.2)
    ax.grid(axis="y", linestyle=":", alpha=0.6)

    out_file = out_dir / "figure5_control_bias_comparison.jpg"
    plt.savefig(out_file, format="jpeg", dpi=300, bbox_inches="tight", pil_kwargs={"quality": 95})
    plt.close()


def make_captions_file(fig_dir: Path):
    captions_md = r"""# Figure Captions

### Figure 1. Spatial model of deposit thickness and borehole exploration networks
* **Conditions**: Rectangular deposit contour (1,000 × 800 m), medium variability scenario (target CV = 25%, actual CV = 25.0%), number of boreholes $n = 16$.
* **Panels**:
  * (a) Quasi-regular grid network with random nodal jitter ($\\le 10\\%$ of grid step);
  * (b) Clustered borehole network (centers located $\\ge 80$ m from deposit boundaries);
  * (c) Preferential sampling network with sampling density proportional to squared thickness ($w \\propto T^2$, $k = 2$).
* **Elements**: Background grayscale shading represents continuous thickness field $T(x, y)$ [m]; black markers denote borehole collars; solid thin lines delineate Voronoi influence polygon boundaries clipped by the deposit perimeter.

---

### Figure 2. Box plots of relative error of reserves estimation across network configurations
* **Conditions**: Rectangular deposit contour (1,000 × 800 m), medium variability scenario (CV = 25%), number of boreholes $n = 16$, 1,000 independent simulation repeats per scenario.
* **Box Plot Definition**: Center line represents sample median; lower and upper box hinges represent first and third quartiles (25th and 75th percentiles); whiskers extend to the 5th and 95th percentiles of the distribution without outlier markers.
* **Methods**: Shaded hatched boxes denote the simple arithmetic mean method; open dotted boxes denote the Voronoi polygon area-weighted method. Dashed horizontal line indicates zero relative error ($e = 0\\%$).

---

### Figure 3. Root mean square error (RMSE) of reserves estimation as a function of borehole count
* **Conditions**: Rectangular deposit contour (1,000 × 800 m), medium variability scenario (CV = 25%), 1,000 independent repeats per point. Both panels share identical vertical axis scaling.
* **Panels**:
  * (a) Non-preferential exploration geometries: Regular, Random, and Clustered networks;
  * (b) Preferential exploration geometries: Linear ($k = 1$) and Quadratic ($k = 2$) preferential sampling.
* **Methods**: Solid lines with filled markers denote simple arithmetic mean estimation; dashed lines with open white markers denote Voronoi area-weighted estimation.

---

### Figure 4. Reserves estimation bias under preferential sampling across variability scenarios
* **Conditions**: Rectangular deposit contour (1,000 × 800 m), 1,000 independent repeats per scenario. Solid horizontal line denotes zero bias ($\mathbb{E}[e] = 0\\%$).
* **Panels**:
  * (a) Linear preferential sampling ($k = 1$);
  * (b) Quadratic preferential sampling ($k = 2$).
* **Methods**: Filled markers denote arithmetic mean; open white markers denote Voronoi weighting. Line styles distinguish variability levels: dotted (Low CV = 10%), dashed (Medium CV = 25%), solid (High CV = 50%).

---

### Figure 5. Comparison of reserves estimation bias between baseline and neutral deposit field modes
* **Conditions**: Rectangular deposit contour (1,000 × 800 m), medium variability scenario (CV = 25%), number of boreholes $n = 16$, 1,000 independent repeats per configuration.
* **Bars and Error Bars**: Grouped bars display sample mean bias $\mathbb{E}[e]$ [%]; error bars denote non-parametric 95% bootstrap confidence intervals computed from 5,000 resamples.
* **Modes**: Diagonal hatching indicates the baseline field mode (`edge_thin`); cross hatching indicates the neutral control field mode (`neutral`). Shaded bars denote arithmetic mean; white bars denote Voronoi area-weighting.
"""
    captions_path = fig_dir / "CAPTIONS.md"
    with open(captions_path, mode="w", encoding="utf-8") as f:
        f.write(captions_md)


def main():
    base_dir = Path(__file__).resolve().parent.parent
    results_dir = base_dir / "results"
    fig_dir = results_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    raw_csv = results_dir / "raw_runs.csv"
    summary_csv = results_dir / "summary_by_scenario.csv"
    neutral_summary_csv = results_dir / "neutral" / "summary_by_scenario.csv"

    print("Generating Figure 1 (field maps and networks)...")
    make_figure1(fig_dir)
    print("Generating Figure 2 (error boxplots)...")
    make_figure2(raw_csv, fig_dir)
    print("Generating Figure 3 (RMSE vs n curves)...")
    make_figure3(summary_csv, fig_dir)
    print("Generating Figure 4 (preferential bias vs n and CV)...")
    make_figure4(summary_csv, fig_dir)
    print("Generating Figure 5 (control bias comparison)...")
    make_figure5(summary_csv, neutral_summary_csv, fig_dir)
    print("Generating CAPTIONS.md...")
    make_captions_file(fig_dir)
    print("ALL FIGURES AND CAPTIONS GENERATED SUCCESSFULLY")


if __name__ == "__main__":
    main()
