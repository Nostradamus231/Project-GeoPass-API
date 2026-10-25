from datetime import datetime
import numpy as np
from shapely.geometry import Point, Polygon


class GeometryError(Exception):
    pass


CATEGORY_THRESHOLDS = (
    (2.0, 15.0, "A"),
    (1.0, 25.0, "B"),
    (0.2, 40.0, "C1"),
)


def fmt_num(value: float | int | None, digits: int = 0) -> str:
    if value is None:
        return ""
    val_float = float(value)
    formatted = f"{val_float:,.{digits}f}"
    return formatted.replace(",", "\u00a0").replace(".", ",")


def _convert_to_metric(coords: list[tuple[float, float]], center_lon: float, center_lat: float) -> list[tuple[float, float]]:
    r = 6371008.8
    phi0 = np.radians(center_lat)
    cos_phi0 = np.cos(phi0)
    result = []
    for lon, lat in coords:
        delta_lon = np.radians(lon - center_lon)
        delta_lat = np.radians(lat - center_lat)
        x_m = float(r * cos_phi0 * delta_lon)
        y_m = float(r * delta_lat)
        result.append((x_m, y_m))
    return result


def _classify_reserves(boreholes_per_ha: float, cv_pct: float) -> str:
    for min_density, max_cv, category in CATEGORY_THRESHOLDS:
        if boreholes_per_ha >= min_density and cv_pct <= max_cv:
            return category
    return "C2"


def calculate_deposit(payload: dict) -> dict:
    company_name = payload["company_name"]
    deposit_name = payload["deposit_name"]
    license_number = payload["license_number"]
    mineral_type = payload.get("mineral_type", "Песок строительный")
    region = payload["region"]
    coord_system = payload.get("coordinate_system", "local_metric")
    contour_raw = payload["contour"]
    boreholes_raw = payload["boreholes"]
    quality = payload["quality"]
    density_t_m3 = float(payload["density_t_m3"])
    declared_area_ha = payload.get("declared_area_ha")

    if coord_system == "geographic":
        center_lon = float(np.mean([pt["x"] for pt in contour_raw]))
        center_lat = float(np.mean([pt["y"] for pt in contour_raw]))
        metric_contour = _convert_to_metric([(pt["x"], pt["y"]) for pt in contour_raw], center_lon, center_lat)
        metric_boreholes = _convert_to_metric([(b["x"], b["y"]) for b in boreholes_raw], center_lon, center_lat)
    else:
        metric_contour = [(float(pt["x"]), float(pt["y"])) for pt in contour_raw]
        metric_boreholes = [(float(b["x"]), float(b["y"])) for b in boreholes_raw]

    poly = Polygon(metric_contour)
    if not poly.is_valid:
        raise GeometryError("Контур самопересекается")
    if poly.area <= 0:
        raise GeometryError("Площадь полигона равна нулю (вырожденный контур)")

    area_m2 = float(poly.area)
    area_ha = area_m2 / 10000.0
    perimeter_m = float(poly.length)

    area_deviation_pct = None
    if declared_area_ha is not None and declared_area_ha > 0:
        area_deviation_pct = round(abs(area_ha - declared_area_ha) / declared_area_ha * 100.0, 2)

    thicknesses = np.array([float(b["thickness_m"]) for b in boreholes_raw], dtype=float)
    weights = np.array([float(b.get("weight", 1.0)) for b in boreholes_raw], dtype=float)

    thickness_weighted_m = float(np.average(thicknesses, weights=weights))
    thickness_min_m = float(np.min(thicknesses))
    thickness_max_m = float(np.max(thicknesses))
    thickness_mean = float(np.mean(thicknesses))
    thickness_std = float(np.std(thicknesses))
    thickness_cv_pct = float((thickness_std / thickness_mean) * 100.0) if thickness_mean > 0 else 0.0

    boreholes_outside_contour = []
    for idx, (bx, by) in enumerate(metric_boreholes):
        pt = Point(bx, by)
        if not poly.contains(pt):
            boreholes_outside_contour.append(boreholes_raw[idx]["borehole_id"])

    boreholes_count = len(boreholes_raw)
    density_density_network = boreholes_count / area_ha if area_ha > 0 else 0.0
    reserves_category = _classify_reserves(density_density_network, thickness_cv_pct)

    volume_m3 = area_m2 * thickness_weighted_m
    reserves_t = volume_m3 * density_t_m3
    reserves_kt = round(reserves_t / 1000.0, 3)

    stability_text = "высокой" if thickness_cv_pct <= 20 else ("умеренной" if thickness_cv_pct <= 40 else "значительной")
    narrative_geology = (
        f"Месторождение «{deposit_name}» расположено в регионе {region}. "
        f"Полезная толща сложена полезным ископаемым ({mineral_type}). "
        f"По результатам бурения {boreholes_count} скважин средневзвешенная мощность пласта составляет "
        f"{fmt_num(thickness_weighted_m, 2)} м (минимальная — {fmt_num(thickness_min_m, 2)} м, максимальная — {fmt_num(thickness_max_m, 2)} м). "
        f"Коэффициент вариации мощности составляет {fmt_num(thickness_cv_pct, 1)}%, что характеризует продуктивный горизонт как "
        f"пласт с {stability_text} выдержанностью залегания."
    )

    narrative_reserves = (
        f"Подсчёт запасов полезного ископаемого выполнен в границах горного отвода площадью {fmt_num(area_ha, 2)} га "
        f"({fmt_num(area_m2, 0)} м²). Геологический объём продуктивной толщи составляет {fmt_num(volume_m3, 0)} м³. "
        f"При принятой средней плотности минерального сырья {fmt_num(density_t_m3, 2)} т/м³ балансовые запасы сырья оцениваются в "
        f"{fmt_num(reserves_t, 0)} т ({fmt_num(reserves_kt, 3)} тыс. т). "
        f"По степени изученности и плотности разведочной сети запасы отнесены к условной категории {reserves_category}."
    )

    narrative_quality = (
        f"Согласно результатам лабораторных анализов, полезное ископаемое имеет модуль крупности "
        f"{fmt_num(quality['modulus_fineness'], 2)}, содержание глинистых и пылевидных частиц {fmt_num(quality['clay_content_pct'], 1)}%, "
        f"влажность {fmt_num(quality['moisture_pct'], 1)}% и насыпную плотность {fmt_num(quality['bulk_density_t_m3'], 2)} т/м³. "
        f"Качественные характеристики сырья соответствуют установленным нормативным требованиям к строительным пескам."
    )

    fmt_borehole_rows = []
    for b in boreholes_raw:
        fmt_borehole_rows.append({
            "borehole_id": str(b["borehole_id"]),
            "x": fmt_num(b["x"], 1),
            "y": fmt_num(b["y"], 1),
            "thickness_m": fmt_num(b["thickness_m"], 2),
            "weight": fmt_num(b.get("weight", 1.0), 2),
        })

    generated_date = datetime.now().strftime("%d.%m.%Y")

    fmt = {
        "area_ha": fmt_num(area_ha, 2),
        "area_m2": fmt_num(area_m2, 0),
        "perimeter_m": fmt_num(perimeter_m, 0),
        "declared_area_ha": fmt_num(declared_area_ha, 2) if declared_area_ha is not None else "",
        "area_deviation_pct": fmt_num(area_deviation_pct, 1) if area_deviation_pct is not None else "",
        "boreholes_count": str(boreholes_count),
        "thickness_weighted_m": fmt_num(thickness_weighted_m, 2),
        "thickness_min_m": fmt_num(thickness_min_m, 2),
        "thickness_max_m": fmt_num(thickness_max_m, 2),
        "thickness_cv_pct": fmt_num(thickness_cv_pct, 1),
        "volume_m3": fmt_num(volume_m3, 0),
        "density_t_m3": fmt_num(density_t_m3, 2),
        "reserves_t": fmt_num(reserves_t, 0),
        "reserves_kt": fmt_num(reserves_kt, 3),
        "reserves_category": reserves_category,
        "quality": {
            "modulus_fineness": fmt_num(quality["modulus_fineness"], 2),
            "clay_content_pct": fmt_num(quality["clay_content_pct"], 1),
            "moisture_pct": fmt_num(quality["moisture_pct"], 1),
            "bulk_density_t_m3": fmt_num(quality["bulk_density_t_m3"], 2),
        },
        "borehole_rows": fmt_borehole_rows,
    }

    return {
        "company_name": company_name,
        "deposit_name": deposit_name,
        "license_number": license_number,
        "mineral_type": mineral_type,
        "region": region,
        "generated_date": generated_date,
        "area_m2": round(area_m2, 2),
        "area_ha": round(area_ha, 4),
        "perimeter_m": round(perimeter_m, 2),
        "declared_area_ha": declared_area_ha,
        "area_deviation_pct": area_deviation_pct,
        "boreholes_count": boreholes_count,
        "boreholes_outside_contour": boreholes_outside_contour,
        "thickness_weighted_m": round(thickness_weighted_m, 2),
        "thickness_min_m": round(thickness_min_m, 2),
        "thickness_max_m": round(thickness_max_m, 2),
        "thickness_cv_pct": round(thickness_cv_pct, 2),
        "volume_m3": round(volume_m3, 2),
        "density_t_m3": round(density_t_m3, 2),
        "reserves_t": round(reserves_t, 2),
        "reserves_kt": reserves_kt,
        "reserves_category": reserves_category,
        "quality": quality,
        "borehole_rows": fmt_borehole_rows,
        "fmt": fmt,
        "narrative_geology": narrative_geology,
        "narrative_reserves": narrative_reserves,
        "narrative_quality": narrative_quality,
    }
