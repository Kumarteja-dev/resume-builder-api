"""
=============================================================================
ELITE RESUME BUILDER — DOCX RENDERER
=============================================================================
Converts resume_data JSON into a downloadable .docx file matching the
Jake's Resume / Harvard single-column ATS-safe format.
=============================================================================
"""

import io
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


def _set_cell_border_none(paragraph):
    pass


def _add_horizontal_line(paragraph):
    """Adds a bottom border to a paragraph - used as a section divider."""
    p = paragraph._p
    pPr = p.get_or_add_pPr()
    pBdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), '8')
    bottom.set(qn('w:space'), '1')
    bottom.set(qn('w:color'), '000000')
    pBdr.append(bottom)

    # pBdr must appear in correct schema order within pPr:
    # pStyle, keepNext, keepLines, pageBreakBefore, framePr, widowControl,
    # numPr, suppressLineNumbers, pBdr, shd, tabs, ...
    # Insert after numPr/suppressLineNumbers if present, else after pStyle,
    # else as first child.
    insert_after_tags = [
        qn('w:suppressLineNumbers'), qn('w:numPr'), qn('w:pageBreakBefore'),
        qn('w:keepLines'), qn('w:keepNext'), qn('w:pStyle')
    ]
    inserted = False
    for tag in insert_after_tags:
        existing = pPr.find(tag)
        if existing is not None:
            existing.addnext(pBdr)
            inserted = True
            break
    if not inserted:
        pPr.insert(0, pBdr)


def _fix_zoom_setting(doc):
    """
    python-docx's default template includes a <w:zoom> element without
    the required percent attribute, which fails strict OOXML validation.
    Remove it - Word defaults to 100% zoom without it.
    """
    settings = doc.settings.element
    for zoom in settings.findall(qn('w:zoom')):
        settings.remove(zoom)


def _set_margins(doc, top=0.5, bottom=0.5, left=0.6, right=0.6):
    section = doc.sections[0]
    section.top_margin = Inches(top)
    section.bottom_margin = Inches(bottom)
    section.left_margin = Inches(left)
    section.right_margin = Inches(right)
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)


def _set_base_font(doc, font_name="Times New Roman", size=10.5):
    style = doc.styles['Normal']
    style.font.name = font_name
    style.font.size = Pt(size)
    style.element.rPr.rFonts.set(qn('w:eastAsia'), font_name)
    style.paragraph_format.space_after = Pt(0)
    style.paragraph_format.space_before = Pt(0)
    style.paragraph_format.line_spacing = 1.0


def _add_section_title(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(7)
    p.paragraph_format.space_after = Pt(3)
    run = p.add_run(text.upper())
    run.bold = True
    run.font.size = Pt(10.5)
    _add_horizontal_line(p)
    return p


def _add_bullet(doc, text):
    p = doc.add_paragraph(style='List Bullet')
    p.paragraph_format.space_after = Pt(1.5)
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.left_indent = Inches(0.18)
    run = p.add_run(text)
    run.font.size = Pt(10.5)
    return p


def _add_two_column_line(doc, left_text, right_text, left_bold=False,
                          right_bold=True, left_italic=False):
    """Creates a line with left-aligned and right-aligned text using a tab stop."""
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(1)

    # Set a right tab stop at the right margin (6.3 inches content width)
    tab_stops = p.paragraph_format.tab_stops
    tab_stops.add_tab_stop(Inches(7.3), alignment=2)  # 2 = WD_TAB_ALIGNMENT.RIGHT

    run_left = p.add_run(left_text)
    run_left.bold = left_bold
    run_left.italic = left_italic
    run_left.font.size = Pt(10.5)

    p.add_run('\t')

    run_right = p.add_run(right_text)
    run_right.bold = right_bold
    run_right.font.size = Pt(10.5)

    return p


def render_resume_docx(resume_data: dict) -> bytes:
    """
    Generates a .docx file from resume_data and returns it as bytes,
    ready to be sent as a file download.
    """
    doc = Document()
    _set_margins(doc)
    _set_base_font(doc)
    _fix_zoom_setting(doc)

    contact = resume_data.get("contact", {})
    experience = resume_data.get("experience", [])
    education = resume_data.get("education", [])
    certifications = resume_data.get("certifications", [])
    projects = resume_data.get("projects", [])
    skills = resume_data.get("skills", {})
    summary = resume_data.get("professional_summary", "")

    # ── HEADER: NAME ──────────────────────────────────────────────────────
    name_p = doc.add_paragraph()
    name_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    name_p.paragraph_format.space_after = Pt(3)
    name_run = name_p.add_run(contact.get("name", ""))
    name_run.bold = True
    name_run.font.size = Pt(20)

    # ── HEADER: CONTACT LINE ─────────────────────────────────────────────
    contact_parts = []
    if contact.get("phone"):
        contact_parts.append(contact["phone"])
    if contact.get("email"):
        contact_parts.append(contact["email"])
    if contact.get("linkedin"):
        contact_parts.append(contact["linkedin"])
    if contact.get("location"):
        contact_parts.append(contact["location"])

    contact_p = doc.add_paragraph()
    contact_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    contact_p.paragraph_format.space_after = Pt(4)
    contact_run = contact_p.add_run(" | ".join(contact_parts))
    contact_run.font.size = Pt(9.5)

    # ── PROFESSIONAL SUMMARY ─────────────────────────────────────────────
    _add_section_title(doc, "Professional Summary")
    summary_p = doc.add_paragraph()
    summary_p.paragraph_format.space_after = Pt(2)
    summary_p.paragraph_format.line_spacing = 1.15
    summary_p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    summary_run = summary_p.add_run(summary)
    summary_run.font.size = Pt(10.5)

    # ── EXPERIENCE ────────────────────────────────────────────────────────
    _add_section_title(doc, "Experience")
    for job in experience:
        company = job.get("company", "")
        title = job.get("title", "")
        start = job.get("start_date", "")
        end = job.get("end_date", "")

        header_p = doc.add_paragraph()
        header_p.paragraph_format.space_after = Pt(1)
        tab_stops = header_p.paragraph_format.tab_stops
        tab_stops.add_tab_stop(Inches(7.3), alignment=2)

        run1 = header_p.add_run(company)
        run1.bold = True
        run1.font.size = Pt(10.5)

        run2 = header_p.add_run("  \u2014  ")
        run2.font.size = Pt(10.5)

        run3 = header_p.add_run(title)
        run3.italic = True
        run3.font.size = Pt(10.5)

        header_p.add_run('\t')

        run4 = header_p.add_run(f"{start} \u2013 {end}")
        run4.bold = True
        run4.font.size = Pt(10.5)

        for bullet in job.get("bullets", []):
            _add_bullet(doc, bullet)

    # ── NOTABLE PROJECTS (optional) ─────────────────────────────────────
    if projects:
        _add_section_title(doc, "Notable Projects")
        for project in projects:
            proj_p = doc.add_paragraph()
            proj_p.paragraph_format.space_after = Pt(1)
            tab_stops = proj_p.paragraph_format.tab_stops
            tab_stops.add_tab_stop(Inches(7.3), alignment=2)

            run1 = proj_p.add_run(project.get("name", ""))
            run1.bold = True
            run1.font.size = Pt(10.5)

            if project.get("tech_stack"):
                proj_p.add_run('\t')
                run2 = proj_p.add_run(project["tech_stack"])
                run2.italic = True
                run2.font.size = Pt(10.5)

            for bullet in project.get("bullets", []):
                _add_bullet(doc, bullet)

    # ── EDUCATION ─────────────────────────────────────────────────────────
    _add_section_title(doc, "Education")
    for edu in education:
        school = edu.get("school", "")
        degree = edu.get("degree", "")
        major = edu.get("major", "")
        grad_year = edu.get("grad_year", "")

        edu_p = doc.add_paragraph()
        edu_p.paragraph_format.space_after = Pt(1)
        tab_stops = edu_p.paragraph_format.tab_stops
        tab_stops.add_tab_stop(Inches(7.3), alignment=2)

        run1 = edu_p.add_run(school)
        run1.bold = True
        run1.font.size = Pt(10.5)

        edu_p.add_run('\t')

        run2 = edu_p.add_run(grad_year)
        run2.bold = True
        run2.font.size = Pt(10.5)

        degree_p = doc.add_paragraph()
        degree_p.paragraph_format.space_after = Pt(3)
        degree_run = degree_p.add_run(f"{degree} in {major}")
        degree_run.italic = True
        degree_run.font.size = Pt(10.5)

    # ── CERTIFICATIONS (optional) ────────────────────────────────────────
    if certifications:
        _add_section_title(doc, "Certifications")
        for cert in certifications:
            cert_p = doc.add_paragraph()
            cert_p.paragraph_format.space_after = Pt(1)
            tab_stops = cert_p.paragraph_format.tab_stops
            tab_stops.add_tab_stop(Inches(7.3), alignment=2)

            run1 = cert_p.add_run(cert.get("name", ""))
            run1.bold = True
            run1.font.size = Pt(10.5)

            if cert.get("year"):
                cert_p.add_run('\t')
                run2 = cert_p.add_run(cert["year"])
                run2.bold = True
                run2.font.size = Pt(10.5)

            if cert.get("issuer"):
                issuer_p = doc.add_paragraph()
                issuer_p.paragraph_format.space_after = Pt(2)
                issuer_run = issuer_p.add_run(cert["issuer"])
                issuer_run.italic = True
                issuer_run.font.size = Pt(10.5)

    # ── TECHNICAL SKILLS ──────────────────────────────────────────────────
    _add_section_title(doc, "Technical Skills")
    for category, items in skills.items():
        skill_p = doc.add_paragraph()
        skill_p.paragraph_format.space_after = Pt(2.5)
        skill_p.paragraph_format.line_spacing = 1.1

        cat_run = skill_p.add_run(f"{category}: ")
        cat_run.bold = True
        cat_run.font.size = Pt(10.5)

        items_run = skill_p.add_run(", ".join(items))
        items_run.font.size = Pt(10.5)

    # ── SAVE TO BYTES ─────────────────────────────────────────────────────
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.read()
