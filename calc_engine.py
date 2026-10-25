from datetime import datetime
import numpy as np
from shapely.geometry import MultiPoint, Point, Polygon
from shapely.ops import voronoi_diagram


class GeometryError(Exception):
    pass


CATEGORY_THRESHOLDS = (
    (2.0, 15.0, "A"),
    (1.0, 25.0, "B"),
    (0.2, 40.0, "C1"),
)

ROCK_ORIGIN_NAMES = {
    "sedimentary": "осадочный",
    "metamorphic": "метаморфический",
    "magmatic": "магматический",
}


def fmt_num(value: float | int | None, digits: int = 0) -> str:
    if value is None:
        return ""
    val_float = float(value)
    formatted = f"{val_float:,.{digits}f}"
    return formatted.replace(",", "\u00a0").replace(".", ",")


def to_dms(value: float, axis: str = "lat") -> dict:
    val = abs(float(value))
    d = int(val)
    rem_minutes = (val - d) * 60.0
    m = int(rem_minutes)
    s = (rem_minutes - m) * 60.0
    s = round(s, 1)
    if s >= 60.0:
        s = 0.0
        m += 1
    if m >= 60:
        m = 0
        d += 1
    return {
        "d": d,
        "m": m,
        "s": s,
        "d_str": str(d),
        "m_str": f"{m:02d}",
        "s_str": fmt_num(s, 1),
    }


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


def voronoi_weights(points: list[tuple[float, float]], contour: Polygon, return_fallback: bool = False) -> list[float] | tuple[list[float], bool]:
    n_pts = len(points)
    if n_pts == 0:
        return ([], False) if return_fallback else []

    contour_area = float(contour.area)
    if contour_area <= 0:
        raise GeometryError("Площадь контура должна быть больше нуля")

    unique_pts = {(float(p[0]), float(p[1])) for p in points}
    is_collinear = False
    if n_pts >= 3 and len(unique_pts) == n_pts:
        hull = MultiPoint([Point(float(p[0]), float(p[1])) for p in points]).convex_hull
        if hull.geom_type in ("Point", "LineString"):
            is_collinear = True

    if n_pts < 3 or len(unique_pts) < n_pts or is_collinear:
        equal_w = contour_area / float(n_pts)
        weights = [equal_w] * n_pts
        return (weights, True) if return_fallback else weights

    minx, miny, maxx, maxy = contour.bounds
    for px, py in points:
        minx = min(minx, float(px))
        miny = min(miny, float(py))
        maxx = max(maxx, float(px))
        maxy = max(maxy, float(py))
    dx = max(maxx - minx, 10.0)
    dy = max(maxy - miny, 10.0)
    env_poly = Polygon([
        (minx - 2 * dx, miny - 2 * dy),
        (maxx + 2 * dx, miny - 2 * dy),
        (maxx + 2 * dx, maxy + 2 * dy),
        (minx - 2 * dx, maxy + 2 * dy),
    ])

    pt_objs = [Point(float(p[0]), float(p[1])) for p in points]
    try:
        vd = voronoi_diagram(MultiPoint(pt_objs), envelope=env_poly)
    except Exception:
        equal_w = contour_area / float(n_pts)
        weights = [equal_w] * n_pts
        return (weights, True) if return_fallback else weights

    cells = list(vd.geoms)
    weights = []
    for pt in pt_objs:
        matched_cell = None
        for cell in cells:
            if cell.contains(pt) or cell.distance(pt) < 1e-9:
                matched_cell = cell
                break
        if matched_cell is not None:
            inter = matched_cell.intersection(contour)
            weights.append(float(inter.area))
        else:
            weights.append(0.0)

    total_w = sum(weights)
    if abs(total_w - contour_area) > 1e-6 * contour_area:
        raise GeometryError(
            f"Сумма весов Вороного ({total_w:.4f}) не совпадает с площадью контура ({contour_area:.4f})"
        )

    return (weights, False) if return_fallback else weights


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
    weighting_method = payload.get("weighting_method", "manual")
    if weighting_method == "voronoi":
        weights_list, weighting_fallback = voronoi_weights(metric_boreholes, poly, return_fallback=True)
        weights = np.array(weights_list, dtype=float)
    else:
        weights = np.array([float(b.get("weight", 1.0)) for b in boreholes_raw], dtype=float)
        weighting_fallback = False

    thickness_weighted_m = float(np.average(thicknesses, weights=weights))
    thickness_arithmetic_m = float(np.mean(thicknesses))
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
    for idx, b in enumerate(boreholes_raw):
        fmt_borehole_rows.append({
            "borehole_id": str(b["borehole_id"]),
            "x": fmt_num(b["x"], 1),
            "y": fmt_num(b["y"], 1),
            "thickness_m": fmt_num(b["thickness_m"], 2),
            "weight": fmt_num(weights[idx], 2),
        })

    generated_date = datetime.now().strftime("%d.%m.%Y")
    passport_date = payload.get("passport_date") or generated_date

    corner_points_geo = payload.get("corner_points_geo")
    corner_points = []
    if corner_points_geo:
        for idx, pt in enumerate(corner_points_geo):
            lat_d = to_dms(pt["lat"], "lat")
            lon_d = to_dms(pt["lon"], "lon")
            corner_points.append({
                "n": str(idx + 1),
                "lat_d": lat_d["d_str"],
                "lat_m": lat_d["m_str"],
                "lat_s": lat_d["s_str"],
                "lon_d": lon_d["d_str"],
                "lon_m": lon_d["m_str"],
                "lon_s": lon_d["s_str"],
            })
    elif coord_system == "geographic":
        for idx, pt in enumerate(contour_raw):
            lat_d = to_dms(pt["y"], "lat")
            lon_d = to_dms(pt["x"], "lon")
            corner_points.append({
                "n": str(idx + 1),
                "lat_d": lat_d["d_str"],
                "lat_m": lat_d["m_str"],
                "lat_s": lat_d["s_str"],
                "lon_d": lon_d["d_str"],
                "lon_m": lon_d["m_str"],
                "lon_s": lon_d["s_str"],
            })

    corner_points_note = (
        ""
        if corner_points
        else "Географические координаты не заданы (локальная система координат)"
    )

    storage = payload.get("storage") or {}
    storage_length_m = fmt_num(storage.get("length_m"), 1) if storage.get("length_m") is not None else "________"
    storage_width_m = fmt_num(storage.get("width_m"), 1) if storage.get("width_m") is not None else "________"
    storage_height_m = fmt_num(storage.get("height_m"), 1) if storage.get("height_m") is not None else "________"
    storage_area_km2 = fmt_num(area_m2 / 1000000.0, 4)
    storage_volume_thousand_m3 = fmt_num(volume_m3 / 1000.0, 1)

    unit = payload.get("unit") or "тыс. т"
    if unit == "тыс. т":
        current_reserves_num = reserves_t / 1000.0
        current_reserves_str = fmt_num(current_reserves_num, 3)
    else:
        current_reserves_num = reserves_t
        current_reserves_str = fmt_num(current_reserves_num, 0)

    prev_res = payload.get("previous_reserves_t")
    inc_res = payload.get("reserves_increment_t")
    real_res = payload.get("reserves_realized_t")

    reserves_balance_warning = None
    if prev_res is not None and inc_res is not None and real_res is not None:
        balance_sum = prev_res + inc_res - real_res
        diff_tons = abs(balance_sum - reserves_t) / reserves_t if reserves_t > 0 else 0.0
        diff_kt = abs(balance_sum - (reserves_t / 1000.0)) / (reserves_t / 1000.0) if reserves_t > 0 else 0.0
        if diff_tons > 0.01 and diff_kt > 0.01:
            reserves_balance_warning = (
                f"Предупреждение: баланс запасов (предыдущие {prev_res} + прирост {inc_res} - реализовано {real_res} = {balance_sum}) "
                f"отличается от расчётных запасов ({reserves_t} т / {reserves_kt} тыс. т)"
            )

    digits_res = 3 if unit == "тыс. т" else 0
    previous_reserves_str = fmt_num(prev_res, digits_res) if prev_res is not None else "________"
    reserves_increment_str = fmt_num(inc_res, digits_res) if inc_res is not None else "________"
    reserves_realized_str = fmt_num(real_res, digits_res) if real_res is not None else "________"

    reserves_methodology = (
        payload.get("reserves_methodology")
        or "Подсчёт выполнен методом среднего арифметического (объёмный метод): запасы определены как произведение площади контура, средневзвешенной мощности и плотности"
    )

    composition = payload.get("composition") or {}
    composition_mineral = composition.get("mineral") or "не указано"
    composition_petrographic = composition.get("petrographic") or "не указано"
    composition_granulometric = composition.get("granulometric") or "не указано"
    composition_physico_mechanical = composition.get("physico_mechanical") or "не указано"

    chemical_oxides_raw = composition.get("chemical_oxides")
    chemical_oxides = []
    if chemical_oxides_raw:
        for ox in chemical_oxides_raw:
            chemical_oxides.append({
                "name": ox["name"],
                "value_pct": fmt_num(ox["value_pct"], 1),
            })
    else:
        chemical_oxides.append({"name": "не указано", "value_pct": "—"})

    extra_chars_raw = payload.get("extra_characteristics")
    extra_characteristics = []
    if extra_chars_raw:
        for ch in extra_chars_raw:
            extra_characteristics.append({
                "name": ch["name"],
                "description": ch["description"],
            })
    else:
        extra_characteristics.append({"name": "не указано", "description": "не указано"})

    apps_raw = payload.get("applications")
    applications = []
    if apps_raw:
        for a in apps_raw:
            applications.append({
                "mineral": a.get("mineral") or mineral_type,
                "usage": a.get("usage") or "не указано",
                "standard": a.get("standard") or "не указано",
            })
    else:
        applications.append({
            "mineral": mineral_type,
            "usage": "не указано",
            "standard": "не указано",
        })

    rock_origin_code = payload.get("rock_origin")
    rock_origin_text = ROCK_ORIGIN_NAMES.get(rock_origin_code, "не указано")

    contract_info = payload.get("contract_info") or license_number
    legal_address = payload.get("legal_address") or "не указано"
    phone = payload.get("phone") or "не указано"
    parent_deposit_name = payload.get("parent_deposit_name") or deposit_name
    mining_method = payload.get("mining_method") or "открытый (карьерный)"
    oblast = payload.get("oblast") or region
    district = payload.get("district") or "не указано"
    locality = payload.get("locality") or "не указано"

    explanatory_note = [
        f"1. Сведения о недропользователе и контрактных правах: паспорт месторождения составлен для организации {company_name}. Лицензия (контракт) на недропользование: {contract_info}. Юридический адрес: {legal_address}. Телефон: {phone}.",
        f"2. Административно-территориальное положение: объект расположен в пределах: область {oblast}, район {district}, населенный пункт {locality}.",
        f"3. Геологическое строение: {narrative_geology}",
        f"4. Способ отработки пород материнского месторождения ({parent_deposit_name}): {mining_method}.",
        f"5. Геометрические параметры залежи: площадь горного отвода составляет {fmt_num(area_ha, 2)} га ({fmt_num(area_m2, 0)} м²), периметр контура — {fmt_num(perimeter_m, 0)} м. Средневзвешенная мощность продуктивной толщи — {fmt_num(thickness_weighted_m, 2)} м.",
        f"6. Качественная характеристика полезного ископаемого: {narrative_quality}",
        f"7. Методика и результаты подсчёта запасов: {reserves_methodology}. {narrative_reserves}",
        f"8. Вещественный состав: минеральный состав — {composition_mineral}; петрографический состав — {composition_petrographic}; гранулометрический состав — {composition_granulometric}; физико-механические свойства — {composition_physico_mechanical}.",
        f"9. Область применения: полезное ископаемое ({mineral_type}) предназначено для использования в строительстве и промышленности согласно действующим техническим регламентам и стандартам.",
    ]

    fmt = {
        "confidentiality_stamp": payload.get("confidentiality_stamp") or "не секретно",
        "copy_number": payload.get("copy_number") or "1",
        "territorial_passport_number": payload.get("territorial_passport_number") or "________",
        "authority_passport_number": payload.get("authority_passport_number") or "________",
        "compiler_name": payload.get("compiler_name") or "________",
        "checker_name": payload.get("checker_name") or "________",
        "passport_date": passport_date,
        "contract_info": contract_info,
        "legal_address": legal_address,
        "phone": phone,
        "parent_deposit_name": parent_deposit_name,
        "mining_method": mining_method,
        "oblast": oblast,
        "district": district,
        "locality": locality,
        "storage_length_m": storage_length_m,
        "storage_width_m": storage_width_m,
        "storage_height_m": storage_height_m,
        "storage_area_km2": storage_area_km2,
        "storage_volume_thousand_m3": storage_volume_thousand_m3,
        "reserves_methodology": reserves_methodology,
        "rock_origin_text": rock_origin_text,
        "unit": unit,
        "previous_passport_number": payload.get("previous_passport_number") or "________",
        "previous_reserves": previous_reserves_str,
        "reserves_increment": reserves_increment_str,
        "reserves_realized": reserves_realized_str,
        "current_reserves": current_reserves_str,
        "composition_mineral": composition_mineral,
        "composition_petrographic": composition_petrographic,
        "composition_granulometric": composition_granulometric,
        "composition_physico_mechanical": composition_physico_mechanical,
        "corner_points_note": corner_points_note,
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
        "thickness_arithmetic_m": round(thickness_arithmetic_m, 2),
        "thickness_min_m": round(thickness_min_m, 2),
        "thickness_max_m": round(thickness_max_m, 2),
        "thickness_cv_pct": round(thickness_cv_pct, 2),
        "volume_m3": round(volume_m3, 2),
        "density_t_m3": round(density_t_m3, 2),
        "reserves_t": round(reserves_t, 2),
        "reserves_kt": reserves_kt,
        "reserves_category": reserves_category,
        "weighting_method": weighting_method,
        "weighting_fallback": weighting_fallback,
        "summary": {
            "area_m2": round(area_m2, 2),
            "area_ha": round(area_ha, 4),
            "thickness_weighted_m": round(thickness_weighted_m, 2),
            "thickness_arithmetic_m": round(thickness_arithmetic_m, 2),
            "volume_m3": round(volume_m3, 2),
            "reserves_t": round(reserves_t, 2),
            "reserves_kt": reserves_kt,
            "reserves_category": reserves_category,
            "boreholes_outside_contour": boreholes_outside_contour,
            "corner_points_count": len(corner_points),
            **({"weighting_method": "voronoi", "weighting_fallback": weighting_fallback} if weighting_method == "voronoi" else {}),
            **({"reserves_balance_warning": reserves_balance_warning} if reserves_balance_warning else {}),
        },
        "quality": quality,
        "borehole_rows": fmt_borehole_rows,
        "corner_points": corner_points,
        "chemical_oxides": chemical_oxides,
        "extra_characteristics": extra_characteristics,
        "applications": applications,
        "explanatory_note": explanatory_note,
        "reserves_balance_warning": reserves_balance_warning,
        "fmt": fmt,
        "narrative_geology": narrative_geology,
        "narrative_reserves": narrative_reserves,
        "narrative_quality": narrative_quality,
    }
