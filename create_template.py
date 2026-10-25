from pathlib import Path
from docx import Document
from docx.shared import Mm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn, nsdecls


def _set_cell_background(cell, hex_color: str):
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    cell._tc.get_or_add_tcPr().append(shd)


def _set_cell_padding(cell, top: int = 100, bottom: int = 100, left: int = 140, right: int = 140):
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    cell._tc.get_or_add_tcPr().append(tcMar)


def _set_table_borders(table, style: str = "grid"):
    if style == "horizontal":
        b_xml = (
            f'<w:tblBorders {nsdecls("w")}>'
            f'<w:top w:val="single" w:sz="6" w:space="0" w:color="B0C4DE"/>'
            f'<w:bottom w:val="single" w:sz="6" w:space="0" w:color="B0C4DE"/>'
            f'<w:insideH w:val="single" w:sz="4" w:space="0" w:color="E0E6ED"/>'
            f'<w:left w:val="none"/>'
            f'<w:right w:val="none"/>'
            f'<w:insideV w:val="none"/>'
            f'</w:tblBorders>'
        )
    else:
        b_xml = (
            f'<w:tblBorders {nsdecls("w")}>'
            f'<w:top w:val="single" w:sz="6" w:space="0" w:color="B0C4DE"/>'
            f'<w:bottom w:val="single" w:sz="6" w:space="0" w:color="B0C4DE"/>'
            f'<w:left w:val="single" w:sz="4" w:space="0" w:color="B0C4DE"/>'
            f'<w:right w:val="single" w:sz="4" w:space="0" w:color="B0C4DE"/>'
            f'<w:insideH w:val="single" w:sz="4" w:space="0" w:color="E0E6ED"/>'
            f'<w:insideV w:val="single" w:sz="4" w:space="0" w:color="E0E6ED"/>'
            f'</w:tblBorders>'
        )
    table._tbl.tblPr.append(parse_xml(b_xml))


def _set_col_widths(table, widths):
    for row in table.rows:
        for idx, w in enumerate(widths):
            cell = row.cells[idx]
            cell.width = w
            dxa = int(w.pt * 20)
            tcW = parse_xml(f'<w:tcW {nsdecls("w")} w:w="{dxa}" w:type="dxa"/>')
            cell._tc.get_or_add_tcPr().append(tcW)


def _format_header_row(row):
    trPr = row._tr.get_or_add_trPr()
    trPr.append(parse_xml(f'<w:tblHeader {nsdecls("w")}/>'))
    trPr.append(parse_xml(f'<w:cantSplit {nsdecls("w")}/>'))


def generate_template(output_path: Path) -> None:
    doc = Document()

    sec = doc.sections[0]
    sec.different_first_page_header_footer = True
    sec.page_width = Mm(210)
    sec.page_height = Mm(297)
    sec.left_margin = Mm(30)
    sec.right_margin = Mm(20)
    sec.top_margin = Mm(20)
    sec.bottom_margin = Mm(20)

    normal_style = doc.styles["Normal"]
    normal_style.font.name = "Times New Roman"
    normal_style.font.size = Pt(12)
    normal_style.font.color.rgb = RGBColor(0x22, 0x22, 0x22)
    normal_style.paragraph_format.line_spacing = 1.15
    normal_style.paragraph_format.space_after = Pt(4)
    normal_style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    h1_style = doc.styles["Heading 1"]
    h1_style.font.name = "Times New Roman"
    h1_style.font.size = Pt(14)
    h1_style.font.bold = True
    h1_style.font.color.rgb = RGBColor(0x1B, 0x36, 0x5D)
    h1_style.paragraph_format.space_before = Pt(12)
    h1_style.paragraph_format.space_after = Pt(6)
    h1_style.paragraph_format.line_spacing = 1.15
    h1_style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT

    title_style = doc.styles["Title"]
    title_style.font.name = "Times New Roman"
    title_style.font.size = Pt(18)
    title_style.font.bold = True
    title_style.font.color.rgb = RGBColor(0x1B, 0x36, 0x5D)
    title_style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_style.paragraph_format.space_before = Pt(28)
    title_style.paragraph_format.space_after = Pt(8)

    p_hdr = sec.header.paragraphs[0]
    p_hdr.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r_hdr = p_hdr.add_run("GeoSaaS API • Паспорт месторождения: {{ deposit_name }}")
    r_hdr.font.name = "Times New Roman"
    r_hdr.font.size = Pt(9)
    r_hdr.font.italic = True
    r_hdr.font.color.rgb = RGBColor(0x77, 0x77, 0x77)

    p_ftr = sec.footer.paragraphs[0]
    p_ftr.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r_f1 = p_ftr.add_run("Страница ")
    r_f1.font.name = "Times New Roman"
    r_f1.font.size = Pt(9)
    r_f1.font.color.rgb = RGBColor(0x77, 0x77, 0x77)
    fld1 = OxmlElement("w:fldSimple")
    fld1.set(qn("w:instr"), "PAGE")
    p_ftr._p.append(fld1)
    r_f2 = p_ftr.add_run(" из ")
    r_f2.font.name = "Times New Roman"
    r_f2.font.size = Pt(9)
    r_f2.font.color.rgb = RGBColor(0x77, 0x77, 0x77)
    fld2 = OxmlElement("w:fldSimple")
    fld2.set(qn("w:instr"), "NUMPAGES")
    p_ftr._p.append(fld2)

    p_t = doc.add_paragraph(style="Title")
    p_t.add_run("ПАСПОРТ МЕСТОРОЖДЕНИЯ")

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sub.paragraph_format.space_after = Pt(4)
    r_sub = p_sub.add_run("{{ deposit_name }}")
    r_sub.font.name = "Times New Roman"
    r_sub.font.size = Pt(14)
    r_sub.font.bold = True
    r_sub.font.color.rgb = RGBColor(0x1B, 0x36, 0x5D)

    p_min = doc.add_paragraph()
    p_min.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_min.paragraph_format.space_after = Pt(28)
    r_min = p_min.add_run("Вид минерального сырья: {{ mineral_type }}")
    r_min.font.name = "Times New Roman"
    r_min.font.size = Pt(12)
    r_min.font.italic = True
    r_min.font.color.rgb = RGBColor(0x55, 0x55, 0x55)

    req_table = doc.add_table(rows=4, cols=2)
    req_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    _set_table_borders(req_table, style="horizontal")
    req_widths = [Mm(60), Mm(100)]
    req_data = [
        ("Недропользователь", "{{ company_name }}"),
        ("Регион работ", "{{ region }}"),
        ("Лицензия (горный отвод)", "{{ license_number }}"),
        ("Дата формирования паспорта", "{{ generated_date }}"),
    ]
    for r_idx, (label, val) in enumerate(req_data):
        row = req_table.rows[r_idx]
        _set_cell_padding(row.cells[0], top=120, bottom=120, left=140, right=140)
        _set_cell_padding(row.cells[1], top=120, bottom=120, left=140, right=140)
        p0 = row.cells[0].paragraphs[0]
        p0.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r0 = p0.add_run(label)
        r0.font.bold = True
        p1 = row.cells[1].paragraphs[0]
        p1.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p1.add_run(val)
    _set_col_widths(req_table, req_widths)

    doc.add_page_break()

    doc.add_heading("Раздел 1. Общие сведения", level=1)
    t1 = doc.add_table(rows=5, cols=2)
    t1.alignment = WD_TABLE_ALIGNMENT.CENTER
    _set_table_borders(t1, style="grid")
    t1_widths = [Mm(85), Mm(75)]
    t1_data = [
        ("Показатель", "Значение"),
        ("Лицензионный номер (горный отвод)", "{{ license_number }}"),
        ("Геологическая площадь участка (га)", "{{ fmt.area_ha }}"),
        ("Геологическая площадь участка (м²)", "{{ fmt.area_m2 }}"),
        ("Периметр лицензионного контура (м)", "{{ fmt.perimeter_m }}"),
    ]
    for r_idx, (c0, c1) in enumerate(t1_data):
        row = t1.rows[r_idx]
        _set_cell_padding(row.cells[0], top=100, bottom=100, left=120, right=120)
        _set_cell_padding(row.cells[1], top=100, bottom=100, left=120, right=120)
        p0 = row.cells[0].paragraphs[0]
        p1 = row.cells[1].paragraphs[0]
        if r_idx == 0:
            _format_header_row(row)
            _set_cell_background(row.cells[0], "F0F4F8")
            _set_cell_background(row.cells[1], "F0F4F8")
            p0.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            p0.add_run(c0).font.bold = True
            p1.add_run(c1).font.bold = True
        else:
            p0.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            p0.add_run(c0)
            p1.add_run(c1)
    _set_col_widths(t1, t1_widths)

    doc.add_heading("Раздел 2. Геологическое строение", level=1)
    p_geo = doc.add_paragraph()
    p_geo.add_run("{{ narrative_geology }}")

    t2 = doc.add_table(rows=5, cols=3)
    t2.alignment = WD_TABLE_ALIGNMENT.CENTER
    _set_table_borders(t2, style="grid")
    t2_widths = [Mm(90), Mm(40), Mm(30)]
    t2_data = [
        ("Показатель", "Значение", "Единица"),
        ("Средневзвешенная мощность пласта", "{{ fmt.thickness_weighted_m }}", "м"),
        ("Минимальная мощность полезной толщи", "{{ fmt.thickness_min_m }}", "м"),
        ("Максимальная мощность полезной толщи", "{{ fmt.thickness_max_m }}", "м"),
        ("Коэффициент вариации мощности", "{{ fmt.thickness_cv_pct }}", "%"),
    ]
    for r_idx, (c0, c1, c2) in enumerate(t2_data):
        row = t2.rows[r_idx]
        _set_cell_padding(row.cells[0], top=100, bottom=100, left=120, right=120)
        _set_cell_padding(row.cells[1], top=100, bottom=100, left=120, right=120)
        _set_cell_padding(row.cells[2], top=100, bottom=100, left=120, right=120)
        p0 = row.cells[0].paragraphs[0]
        p1 = row.cells[1].paragraphs[0]
        p2 = row.cells[2].paragraphs[0]
        if r_idx == 0:
            _format_header_row(row)
            _set_cell_background(row.cells[0], "F0F4F8")
            _set_cell_background(row.cells[1], "F0F4F8")
            _set_cell_background(row.cells[2], "F0F4F8")
            p0.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p0.add_run(c0).font.bold = True
            p1.add_run(c1).font.bold = True
            p2.add_run(c2).font.bold = True
        else:
            p0.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p0.add_run(c0)
            p1.add_run(c1)
            p2.add_run(c2)
    _set_col_widths(t2, t2_widths)

    doc.add_heading("Раздел 3. Данные скважин", level=1)
    p_bh = doc.add_paragraph()
    p_bh.add_run("Всего пройдено выработок: {{ fmt.boreholes_count }}. Реестр скважин и мощности продуктивного горизонта приведены в таблице:")

    t3 = doc.add_table(rows=4, cols=5)
    t3.alignment = WD_TABLE_ALIGNMENT.CENTER
    _set_table_borders(t3, style="grid")
    t3_widths = [Mm(28), Mm(34), Mm(34), Mm(32), Mm(32)]

    h_cells = t3.rows[0].cells
    _format_header_row(t3.rows[0])
    h_titles = ["№ скважины", "Координата X", "Координата Y", "Мощность, м", "Вес (влияние)"]
    for i, title in enumerate(h_titles):
        _set_cell_background(h_cells[i], "F0F4F8")
        _set_cell_padding(h_cells[i], top=100, bottom=100, left=100, right=100)
        p = h_cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER if i == 0 else WD_ALIGN_PARAGRAPH.RIGHT
        r = p.add_run(title)
        r.font.bold = True

    t3.rows[1].cells[0].paragraphs[0].text = "{%tr for row in borehole_rows %}"

    d_cells = t3.rows[2].cells
    for i in range(5):
        _set_cell_padding(d_cells[i], top=90, bottom=90, left=100, right=100)
    p_d0 = d_cells[0].paragraphs[0]
    p_d0.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_d0.add_run("{{ row.borehole_id }}")

    p_d1 = d_cells[1].paragraphs[0]
    p_d1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_d1.add_run("{{ row.x }}")

    p_d2 = d_cells[2].paragraphs[0]
    p_d2.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_d2.add_run("{{ row.y }}")

    p_d3 = d_cells[3].paragraphs[0]
    p_d3.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_d3.add_run("{{ row.thickness_m }}")

    p_d4 = d_cells[4].paragraphs[0]
    p_d4.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_d4.add_run("{{ row.weight }}")

    t3.rows[3].cells[0].paragraphs[0].text = "{%tr endfor %}"
    _set_col_widths(t3, t3_widths)

    doc.add_heading("Раздел 4. Качество сырья", level=1)
    p_q = doc.add_paragraph()
    p_q.add_run("{{ narrative_quality }}")

    t4 = doc.add_table(rows=5, cols=3)
    t4.alignment = WD_TABLE_ALIGNMENT.CENTER
    _set_table_borders(t4, style="grid")
    t4_widths = [Mm(90), Mm(40), Mm(30)]
    t4_data = [
        ("Показатель", "Значение", "Единица"),
        ("Модуль крупности", "{{ fmt.quality.modulus_fineness }}", "—"),
        ("Содержание глинистых и пылевидных частиц", "{{ fmt.quality.clay_content_pct }}", "%"),
        ("Естественная влажность сырья", "{{ fmt.quality.moisture_pct }}", "%"),
        ("Насыпная плотность сырья", "{{ fmt.quality.bulk_density_t_m3 }}", "т/м³"),
    ]
    for r_idx, (c0, c1, c2) in enumerate(t4_data):
        row = t4.rows[r_idx]
        _set_cell_padding(row.cells[0], top=100, bottom=100, left=120, right=120)
        _set_cell_padding(row.cells[1], top=100, bottom=100, left=120, right=120)
        _set_cell_padding(row.cells[2], top=100, bottom=100, left=120, right=120)
        p0 = row.cells[0].paragraphs[0]
        p1 = row.cells[1].paragraphs[0]
        p2 = row.cells[2].paragraphs[0]
        if r_idx == 0:
            _format_header_row(row)
            _set_cell_background(row.cells[0], "F0F4F8")
            _set_cell_background(row.cells[1], "F0F4F8")
            _set_cell_background(row.cells[2], "F0F4F8")
            p0.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p0.add_run(c0).font.bold = True
            p1.add_run(c1).font.bold = True
            p2.add_run(c2).font.bold = True
        else:
            p0.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p0.add_run(c0)
            p1.add_run(c1)
            p2.add_run(c2)
    _set_col_widths(t4, t4_widths)

    doc.add_heading("Раздел 5. Подсчёт запасов", level=1)
    p_res = doc.add_paragraph()
    p_res.add_run("{{ narrative_reserves }}")

    t5 = doc.add_table(rows=6, cols=3)
    t5.alignment = WD_TABLE_ALIGNMENT.CENTER
    _set_table_borders(t5, style="grid")
    t5_widths = [Mm(90), Mm(40), Mm(30)]
    t5_data = [
        ("Показатель", "Значение", "Единица"),
        ("Геологический объём полезной толщи", "{{ fmt.volume_m3 }}", "м³"),
        ("Средняя плотность минерального сырья", "{{ fmt.density_t_m3 }}", "т/м³"),
        ("Балансовые запасы полезного ископаемого", "{{ fmt.reserves_t }}", "т"),
        ("Балансовые запасы в тыс. тонн", "{{ fmt.reserves_kt }}", "тыс. т"),
        ("Условная категория разведанности запасов", "{{ fmt.reserves_category }}", "—"),
    ]
    for r_idx, (c0, c1, c2) in enumerate(t5_data):
        row = t5.rows[r_idx]
        _set_cell_padding(row.cells[0], top=100, bottom=100, left=120, right=120)
        _set_cell_padding(row.cells[1], top=100, bottom=100, left=120, right=120)
        _set_cell_padding(row.cells[2], top=100, bottom=100, left=120, right=120)
        p0 = row.cells[0].paragraphs[0]
        p1 = row.cells[1].paragraphs[0]
        p2 = row.cells[2].paragraphs[0]
        if r_idx == 0:
            _format_header_row(row)
            _set_cell_background(row.cells[0], "F0F4F8")
            _set_cell_background(row.cells[1], "F0F4F8")
            _set_cell_background(row.cells[2], "F0F4F8")
            p0.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p0.add_run(c0).font.bold = True
            p1.add_run(c1).font.bold = True
            p2.add_run(c2).font.bold = True
        else:
            p0.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p0.add_run(c0)
            p1.add_run(c1)
            p2.add_run(c2)
    _set_col_widths(t5, t5_widths)

    p_sign = doc.add_paragraph()
    p_sign.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_sign.paragraph_format.space_before = Pt(24)
    p_sign.paragraph_format.space_after = Pt(2)
    r_s1 = p_sign.add_run("Документ сформирован автоматически сервисом GeoSaaS API\n")
    r_s1.font.name = "Times New Roman"
    r_s1.font.italic = True
    r_s1.font.size = Pt(10)
    r_s1.font.color.rgb = RGBColor(0x66, 0x66, 0x66)
    r_s2 = p_sign.add_run("Дата формирования: {{ generated_date }}")
    r_s2.font.name = "Times New Roman"
    r_s2.font.italic = True
    r_s2.font.size = Pt(10)
    r_s2.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))


if __name__ == "__main__":
    target = Path(__file__).resolve().parent / "templates" / "passport_template.docx"
    generate_template(target)
