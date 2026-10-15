from pathlib import Path
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, Inches, RGBColor


def generate_template(output_path: Path) -> None:
    doc = Document()

    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(0.8)

    title_p = doc.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_title = title_p.add_run("ПАСПОРТ МЕСТОРОЖДЕНИЯ")
    run_title.font.name = "Arial"
    run_title.font.size = Pt(18)
    run_title.font.bold = True
    run_title.font.color.rgb = RGBColor(0x1B, 0x36, 0x5D)

    sub_p = doc.add_paragraph()
    sub_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_sub = sub_p.add_run("{{ deposit_name }} ({{ mineral_type }})")
    run_sub.font.name = "Arial"
    run_sub.font.size = Pt(13)
    run_sub.font.bold = True

    meta_p = doc.add_paragraph()
    meta_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_meta = meta_p.add_run("Недропользователь: {{ company_name }}\nРегион работ: {{ region }}\nДата формирования: {{ generated_date }}")
    run_meta.font.name = "Arial"
    run_meta.font.size = Pt(10)
    run_meta.font.color.rgb = RGBColor(0x55, 0x55, 0x55)

    doc.add_heading("Раздел 1. Общие сведения", level=1)
    p1 = doc.add_paragraph()
    p1.add_run("Лицензионный номер (горный отвод): ").bold = True
    p1.add_run("{{ license_number }}\n")
    p1.add_run("Геологическая площадь участка: ").bold = True
    p1.add_run("{{ area_ha }} га ({{ area_m2 }} м²)\n")
    p1.add_run("Периметр лицензионного контура: ").bold = True
    p1.add_run("{{ perimeter_m }} м")

    doc.add_heading("Раздел 2. Геологическое строение", level=1)
    p2 = doc.add_paragraph()
    p2.add_run("{{ narrative_geology }}\n\n")
    p2.add_run("Средневзвешенная мощность продуктивной толщи: ").bold = True
    p2.add_run("{{ thickness_weighted_m }} м (мин: {{ thickness_min_m }} м, макс: {{ thickness_max_m }} м, вариация: {{ thickness_cv_pct }}%).")

    doc.add_heading("Раздел 3. Данные скважин", level=1)
    p3 = doc.add_paragraph()
    p3.add_run("Всего пройдено скважин: {{ boreholes_count }}. Перечень выработок:")

    table = doc.add_table(rows=4, cols=5)
    table.style = "Table Grid"

    headers = ["№ скважины", "Координата X (м / долг.)", "Координата Y (м / шир.)", "Мощность, м", "Вес (влияние)"]
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.paragraphs[0].text = h
        cell.paragraphs[0].runs[0].font.bold = True
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

    table.rows[1].cells[0].paragraphs[0].text = "{%tr for row in borehole_rows %}"

    data_row = table.rows[2].cells
    data_row[0].paragraphs[0].text = "{{ row.borehole_id }}"
    data_row[1].paragraphs[0].text = "{{ row.x }}"
    data_row[2].paragraphs[0].text = "{{ row.y }}"
    data_row[3].paragraphs[0].text = "{{ row.thickness_m }}"
    data_row[4].paragraphs[0].text = "{{ row.weight }}"

    table.rows[3].cells[0].paragraphs[0].text = "{%tr endfor %}"

    doc.add_heading("Раздел 4. Качество сырья", level=1)
    p4 = doc.add_paragraph()
    p4.add_run("{{ narrative_quality }}\n\n")
    p4.add_run("Лабораторные показатели:\n").bold = True
    p4.add_run("• Модуль крупности: {{ quality.modulus_fineness }}\n")
    p4.add_run("• Содержание глинистых и пылевидных частиц: {{ quality.clay_content_pct }}%\n")
    p4.add_run("• Влажность: {{ quality.moisture_pct }}%\n")
    p4.add_run("• Насыпная плотность: {{ quality.bulk_density_t_m3 }} т/м³")

    doc.add_heading("Раздел 5. Подсчёт запасов", level=1)
    p5 = doc.add_paragraph()
    p5.add_run("{{ narrative_reserves }}\n\n")
    p5.add_run("Итоговые показатели подсчёта:\n").bold = True
    p5.add_run("• Объём полезной толщи: {{ volume_m3 }} м³\n")
    p5.add_run("• Средняя плотность минерального сырья: {{ density_t_m3 }} т/м³\n")
    p5.add_run("• Геологические запасы: {{ reserves_t }} т ({{ reserves_kt }} тыс. т)\n")
    p5.add_run("• Условная категория запасов: {{ reserves_category }}")

    doc.add_paragraph()
    footer = doc.add_paragraph()
    footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run_footer = footer.add_run("Документ сформирован автоматически сервисом GeoSaaS API")
    run_footer.font.italic = True
    run_footer.font.size = Pt(9)
    run_footer.font.color.rgb = RGBColor(0x77, 0x77, 0x77)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))


if __name__ == "__main__":
    target = Path(__file__).resolve().parent / "templates" / "passport_template.docx"
    generate_template(target)
