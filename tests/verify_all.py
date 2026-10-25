import io
import json
import sys
from pathlib import Path
import urllib.error
import urllib.request
from docx import Document

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from calc_engine import to_dms

BASE_URL = "http://127.0.0.1:8000"


def request_http(url: str, data: dict = None, method: str = "GET", raw_bytes: bytes = None):
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if raw_bytes is not None:
        body = raw_bytes
    elif data is not None:
        body = json.dumps(data).encode("utf-8")
    else:
        body = None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            status = resp.status
            content = resp.read()
            cd_hdr = resp.headers.get("content-disposition", "")
            try:
                parsed = json.loads(content.decode("utf-8"))
            except Exception:
                parsed = content
            return status, parsed, cd_hdr
    except urllib.error.HTTPError as e:
        status = e.code
        content = e.read()
        cd_hdr = e.headers.get("content-disposition", "")
        try:
            parsed = json.loads(content.decode("utf-8"))
        except Exception:
            parsed = content.decode("utf-8", errors="replace")
        return status, parsed, cd_hdr


def get_base_v1_payload() -> dict:
    return {
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


def get_full_v3_payload() -> dict:
    p = get_base_v1_payload()
    p.update({
        "confidentiality_stamp": "Для служебного пользования",
        "copy_number": "2",
        "territorial_passport_number": "ТП-042",
        "authority_passport_number": "УО-101",
        "compiler_name": "Иванов И.И.",
        "checker_name": "Петров П.П.",
        "passport_date": "25.10.2026",
        "contract_info": "Контракт на недропользование № 123-Т",
        "legal_address": "г. Костанай, ул. Абая, 10",
        "phone": "+7 (7142) 55-55-55",
        "parent_deposit_name": "Северное материнское",
        "mining_method": "Открытый с применением экскаваторов",
        "oblast": "Костанайская область",
        "district": "Костанайский район",
        "locality": "с. Заречное",
        "storage": {
            "length_m": 250.0,
            "width_m": 120.0,
            "height_m": 15.0,
        },
        "reserves_methodology": "Метод геологических блоков с интерполяцией мощностей",
        "composition": {
            "mineral": "Кварц 92%, полевой шпат 8%",
            "chemical_oxides": [
                {"name": "SiO2", "value_pct": 91.5},
                {"name": "Al2O3", "value_pct": 4.2},
            ],
            "petrographic": "Песок кварцевый",
            "granulometric": "Фракция 0.5-1.0 мм",
            "physico_mechanical": "Плотность 1.6 т/м3",
        },
        "extra_characteristics": [
            {"name": "Радиоактивность", "description": "12 мкР/ч, I класс"},
        ],
        "applications": [
            {"mineral": "Песок строительный", "usage": "Бетонные смеси", "standard": "ГОСТ 8736-2014"},
        ],
        "rock_origin": "sedimentary",
        "unit": "тыс. т",
        "previous_passport_number": "ПР-001",
        "previous_reserves_t": 50.0,
        "reserves_increment_t": 40.0,
        "reserves_realized_t": 10.0,
        "corner_points_geo": [
            {"lat": 52.1, "lon": 63.5},
            {"lat": 52.11, "lon": 63.5},
            {"lat": 52.11, "lon": 63.51},
            {"lat": 52.1, "lon": 63.51},
        ],
    })
    return p


def run_all_checks() -> dict[str, tuple[bool, str]]:
    results = {}

    st1, body1, _ = request_http(f"{BASE_URL}/generate-passport", data=get_base_v1_payload(), method="POST")
    dl_url1 = body1.get("download_url", "")
    st_dl1, bytes1, _ = request_http(f"{BASE_URL}{dl_url1}", method="GET")
    doc1 = Document(io.BytesIO(bytes1))
    text1 = " ".join([p.text for p in doc1.paragraphs] + [c.text for t in doc1.tables for r in t.rows for c in r.cells])
    has_placeholders = "________" in text1 or "не указано" in text1
    check1_passed = st1 == 200 and st_dl1 == 200 and has_placeholders and len(doc1.paragraphs) > 0
    results["1. Контрольный запрос v1"] = (check1_passed, f"Status: {st1}, placeholders present: {has_placeholders}")

    st2, body2, _ = request_http(f"{BASE_URL}/generate-passport", data=get_full_v3_payload(), method="POST")
    dl_url2 = body2.get("download_url", "")
    st_dl2, bytes2, cd2 = request_http(f"{BASE_URL}{dl_url2}", method="GET")
    doc2 = Document(io.BytesIO(bytes2))
    t_geo = doc2.tables[2]
    geo_data_rows = len(t_geo.rows) - 1
    check2_passed = st2 == 200 and st_dl2 == 200 and geo_data_rows == 4
    results["2. Полный запрос со всеми полями"] = (check2_passed, f"Status: {st2}, corner points rows: {geo_data_rows}")

    doc_full_text = "\n".join([p.text for p in doc2.paragraphs] + [c.text for t in doc2.tables for r in t.rows for c in r.cells])
    required_sections = [
        "Приёмка паспорта",
        "Раздел 1. Географические координаты объекта",
        "Раздел 2. Организация-недропользователь",
        "Раздел 3. Способ отработки вскрышных и вмещающих пород материнского месторождения",
        "Раздел 4. Административное положение объекта",
        "Раздел 5. Параметры складирования вскрышных и вмещающих пород",
        "Раздел 6. Методика подсчёта запасов",
        "Раздел 7. Характеристика общераспространённых полезных ископаемых",
        "Раздел 8. Область применения",
        "Раздел 9. Запасы",
        "Приложение 1. Пояснительная записка",
        "Приложение 2. Графические материалы",
    ]
    indices = [doc_full_text.find(sec) for sec in required_sections]
    all_found = all(idx != -1 for idx in indices)
    order_ok = all(indices[i] < indices[i + 1] for i in range(len(indices) - 1)) if all_found else False
    check3_passed = all_found and order_ok
    results["3. Структура документа"] = (check3_passed, f"All found: {all_found}, Order correct: {order_ok}")

    has_raw_floats = "80000.0" in doc_full_text or "10000.0" in doc_full_text or "50000.0" in doc_full_text
    has_fmt_80k = "80\u00a0000" in doc_full_text or "80 000" in doc_full_text
    check4_passed = not has_raw_floats and has_fmt_80k
    results["4. Форматирование чисел"] = (check4_passed, f"Raw floats: {has_raw_floats}, 80k formatted: {has_fmt_80k}")

    leftovers = []
    for p in doc2.paragraphs:
        if "{{" in p.text or "{%" in p.text:
            leftovers.append(p.text)
    for t in doc2.tables:
        for r in t.rows:
            for c in r.cells:
                if "{{" in c.text or "{%" in c.text:
                    leftovers.append(c.text)
    for sec in doc2.sections:
        for p in sec.header.paragraphs:
            if "{{" in p.text or "{%" in p.text:
                leftovers.append(p.text)
        for p in sec.footer.paragraphs:
            if "{{" in p.text or "{%" in p.text:
                leftovers.append(p.text)
    check5_passed = len(leftovers) == 0
    results["5. Отсутствие остаточных тегов"] = (check5_passed, f"Leftover tags: {len(leftovers)}")

    dms55 = to_dms(55.5, "lat")
    dms0 = to_dms(0.0)
    dms59 = to_dms(59.99999)
    dms_neg = to_dms(-0.5)
    dms_ok = (
        dms55["d"] == 55 and dms55["m"] == 30 and dms55["s_str"] == "0,0"
        and dms0["d"] == 0 and dms0["m"] == 0 and dms0["s_str"] == "0,0"
        and dms59["s"] < 60.0
        and dms_neg["d"] == 0 and dms_neg["m"] == 30 and dms_neg["s_str"] == "0,0"
    )
    results["6. Функция to_dms"] = (dms_ok, f"55.5: {dms55['d']}deg {dms55['m']}min {dms55['s_str']}sec, 59.99999 sec: {dms59['s']}")

    p_bal_ok = get_base_v1_payload()
    p_bal_ok.update({
        "previous_reserves_t": 50.0,
        "reserves_increment_t": 40.0,
        "reserves_realized_t": 10.0,
    })
    st_bal_ok, body_bal_ok, _ = request_http(f"{BASE_URL}/generate-passport", data=p_bal_ok, method="POST")
    warn_ok = body_bal_ok.get("summary", {}).get("reserves_balance_warning")

    p_bal_bad = get_base_v1_payload()
    p_bal_bad.update({
        "contour": [
            {"x": 0.0, "y": 0.0},
            {"x": 100.0, "y": 0.0},
            {"x": 100.0, "y": 250.0},
            {"x": 0.0, "y": 250.0},
        ],
        "previous_reserves_t": 50.0,
        "reserves_increment_t": 40.0,
        "reserves_realized_t": 10.0,
    })
    st_bal_bad, body_bal_bad, _ = request_http(f"{BASE_URL}/generate-passport", data=p_bal_bad, method="POST")
    warn_bad = body_bal_bad.get("summary", {}).get("reserves_balance_warning")

    check7_passed = st_bal_ok == 200 and warn_ok is None and st_bal_bad == 200 and warn_bad is not None
    results["7. Баланс запасов"] = (check7_passed, f"Balanced warning: {warn_ok}, Imbalanced warning: {warn_bad is not None}")

    p_neg = get_base_v1_payload()
    p_neg["reserves_realized_t"] = -10.0
    st_neg, body_neg, _ = request_http(f"{BASE_URL}/generate-passport", data=p_neg, method="POST")
    err_fields = [e.get("field") for e in body_neg.get("errors", [])]
    check8_passed = st_neg == 422 and "reserves_realized_t" in err_fields
    results["8. Отрицательное reserves_realized_t"] = (check8_passed, f"Status: {st_neg}, fields: {err_fields}")

    p_no_co = get_base_v1_payload()
    del p_no_co["company_name"]
    st_r1, body_r1, _ = request_http(f"{BASE_URL}/generate-passport", data=p_no_co, method="POST")

    p_r2 = get_base_v1_payload()
    p_r2["boreholes"][0]["thickness_m"] = -5.0
    st_r2, _, _ = request_http(f"{BASE_URL}/generate-passport", data=p_r2, method="POST")

    p_r3 = get_base_v1_payload()
    p_r3["contour"] = [{"x": 0.0, "y": 0.0}, {"x": 100.0, "y": 100.0}, {"x": 100.0, "y": 0.0}, {"x": 0.0, "y": 100.0}]
    st_r3, body_r3, _ = request_http(f"{BASE_URL}/generate-passport", data=p_r3, method="POST")
    bf_msg = json.dumps(body_r3, ensure_ascii=False)

    st_r4, body_r4, _ = request_http(f"{BASE_URL}/generate-passport", raw_bytes=b"{\"broken\": ", method="POST")

    st_r5, _, _ = request_http(f"{BASE_URL}/download/..%2Fmain.py", method="GET")

    p_r6 = get_base_v1_payload()
    p_r6["boreholes"] = [
        {"borehole_id": "S-IN", "x": 50.0, "y": 50.0, "thickness_m": 5.0, "weight": 1.0},
        {"borehole_id": "S-OUT", "x": 500.0, "y": 500.0, "thickness_m": 5.0, "weight": 1.0},
    ]
    st_r6, body_r6, _ = request_http(f"{BASE_URL}/generate-passport", data=p_r6, method="POST")
    out_list = body_r6.get("summary", {}).get("boreholes_outside_contour", [])

    check9_passed = (
        st_r1 == 422
        and st_r2 == 422
        and st_r3 == 422
        and "самопересекается" in bf_msg
        and st_r4 == 422
        and st_r5 == 404
        and st_r6 == 200
        and "S-OUT" in out_list
    )
    results["9. Регрессия"] = (check9_passed, f"Missing: {st_r1 == 422}, NegThick: {st_r2 == 422}, Butterfly: {st_r3 == 422}, BrokenJSON: {st_r4 == 422}, Traversal: {st_r5 == 404}, Outside: {st_r6 == 200}")

    return results


if __name__ == "__main__":
    tests = run_all_checks()
    all_ok = True
    for name, (ok, detail) in tests.items():
        status_str = "PASS" if ok else "FAIL"
        if not ok:
            all_ok = False
        print(f"[{status_str}] {name}: {detail}")
    print("SUMMARY:", "ALL_PASSED" if all_ok else "SOME_FAILED")
