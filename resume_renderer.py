"""
=============================================================================
ELITE RESUME BUILDER — HTML RENDERER v3
=============================================================================
Sections: Header, Summary, Experience, Education,
          Certifications (optional), Projects (optional), Skills
=============================================================================
"""

from jinja2 import Template

RESUME_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{ contact.name }} — Resume</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html, body {
    background: #ffffff; color: #000000;
    font-family: "Times New Roman", Times, serif;
    font-size: 10.5pt; line-height: 1.35;
  }
  .page {
    width: 8.5in; min-height: 11in;
    padding: 0.5in 0.6in 0.5in 0.6in;
    margin: 0 auto; background: #ffffff; position: relative;
  }
  .page-break-guide {
    position: absolute; left: 0; right: 0;
    border-top: 1px dashed #e0e0e0; pointer-events: none;
  }
  .page-break-guide.p2 { top: 11in; }
  .page-break-guide.p3 { top: 22in; }
  @media print {
    .page { width: 8.5in; padding: 0.5in 0.6in; margin: 0; }
    .page-break-guide { display: none; }
    @page { size: letter; margin: 0; }
  }
  .header { text-align: center; margin-bottom: 4pt; padding-bottom: 3pt; }
  .header .name {
    font-size: 20pt; font-weight: bold;
    letter-spacing: 0.5pt; line-height: 1.1; margin-bottom: 3pt;
  }
  .header .contact-line { font-size: 9.5pt; color: #000000; }
  .header .contact-line a { color: #000000; text-decoration: none; }
  .contact-separator { margin: 0 5pt; color: #555; }
  .section { margin-top: 7pt; }
  .section-title {
    font-size: 10.5pt; font-weight: bold; text-transform: uppercase;
    letter-spacing: 0.8pt; border-bottom: 1.2pt solid #000000;
    padding-bottom: 1.5pt; margin-bottom: 5pt;
  }
  .experience-entry { margin-bottom: 6pt; }
  .experience-header {
    display: flex; justify-content: space-between;
    align-items: baseline; margin-bottom: 1pt;
  }
  .company-title-block { flex: 1; }
  .company-name { font-size: 10.5pt; font-weight: bold; }
  .job-title { font-size: 10.5pt; font-style: italic; }
  .date-location {
    font-size: 10.5pt; text-align: right;
    white-space: nowrap; padding-left: 8pt;
  }
  .date-location .dates { font-weight: bold; }
  .bullets { list-style: none; padding-left: 0; margin-top: 2pt; }
  .bullets li {
    position: relative; padding-left: 12pt; margin-bottom: 1.8pt;
    font-size: 10.5pt; line-height: 1.32; text-align: justify;
  }
  .bullets li::before { content: "•"; position: absolute; left: 0; top: 0; }
  .summary-text {
    font-size: 10.5pt; line-height: 1.45;
    text-align: justify; margin-top: 1pt;
  }
  .education-entry {
    display: flex; justify-content: space-between;
    align-items: baseline; margin-bottom: 3pt;
  }
  .edu-left .school-name { font-weight: bold; font-size: 10.5pt; }
  .edu-left .degree-line { font-style: italic; font-size: 10.5pt; }
  .edu-right {
    text-align: right; font-size: 10.5pt;
    font-weight: bold; white-space: nowrap; padding-left: 8pt;
  }
  .cert-entry {
    display: flex; justify-content: space-between;
    align-items: baseline; margin-bottom: 3pt;
  }
  .cert-left .cert-name { font-weight: bold; font-size: 10.5pt; }
  .cert-left .cert-issuer { font-style: italic; font-size: 10.5pt; }
  .cert-right {
    text-align: right; font-size: 10.5pt;
    font-weight: bold; white-space: nowrap; padding-left: 8pt;
  }
  .project-entry { margin-bottom: 6pt; }
  .project-header {
    display: flex; justify-content: space-between;
    align-items: baseline; margin-bottom: 1pt;
  }
  .project-name { font-size: 10.5pt; font-weight: bold; }
  .project-stack { font-size: 10.5pt; font-style: italic; padding-left: 8pt; }
  .skills-grid { display: block; }
  .skill-row { display: flex; margin-bottom: 2.5pt; font-size: 10.5pt; }
  .skill-category { font-weight: bold; min-width: 145pt; flex-shrink: 0; }
  .skill-list { flex: 1; }
  @media print {
    .experience-entry { page-break-inside: avoid; }
    .project-entry { page-break-inside: avoid; }
    .section { page-break-inside: avoid; }
    .section-title { page-break-after: avoid; }
  }
</style>
</head>
<body>
<div class="page">

  <div class="page-break-guide p2"></div>
  {% if page_target == 3 %}
  <div class="page-break-guide p3"></div>
  {% endif %}

  <!-- HEADER -->
  <div class="header">
    <div class="name">{{ contact.name }}</div>
    <div class="contact-line">
      {{ contact.phone }}
      <span class="contact-separator">|</span>
      <a href="mailto:{{ contact.email }}">{{ contact.email }}</a>
      <span class="contact-separator">|</span>
      <a href="https://{{ contact.linkedin }}" target="_blank">{{ contact.linkedin }}</a>
      <span class="contact-separator">|</span>
      {{ contact.location }}
    </div>
  </div>

  <!-- PROFESSIONAL SUMMARY -->
  <div class="section">
    <div class="section-title">Professional Summary</div>
    <p class="summary-text">{{ professional_summary }}</p>
  </div>

  <!-- EXPERIENCE -->
  <div class="section">
    <div class="section-title">Experience</div>
    {% for job in experience %}
    <div class="experience-entry">
      <div class="experience-header">
        <div class="company-title-block">
          <span class="company-name">{{ job.company }}</span>
          &nbsp;&mdash;&nbsp;
          <span class="job-title">{{ job.title }}</span>
        </div>
        <div class="date-location">
          <span class="dates">{{ job.start_date }} &ndash; {{ job.end_date }}</span>
        </div>
      </div>
      <ul class="bullets">
        {% for bullet in job.bullets %}
        <li>{{ bullet }}</li>
        {% endfor %}
      </ul>
    </div>
    {% endfor %}
  </div>

  <!-- NOTABLE PROJECTS (optional) -->
  {% if projects and projects|length > 0 %}
  <div class="section">
    <div class="section-title">Notable Projects</div>
    {% for project in projects %}
    <div class="project-entry">
      <div class="project-header">
        <span class="project-name">{{ project.name }}</span>
        {% if project.tech_stack %}
        <span class="project-stack">{{ project.tech_stack }}</span>
        {% endif %}
      </div>
      <ul class="bullets">
        {% for bullet in project.bullets %}
        <li>{{ bullet }}</li>
        {% endfor %}
      </ul>
    </div>
    {% endfor %}
  </div>
  {% endif %}

  <!-- EDUCATION -->
  <div class="section">
    <div class="section-title">Education</div>
    {% for edu in education %}
    <div class="education-entry">
      <div class="edu-left">
        <div class="school-name">{{ edu.school }}</div>
        <div class="degree-line">{{ edu.degree }} in {{ edu.major }}</div>
      </div>
      <div class="edu-right">{{ edu.grad_year }}</div>
    </div>
    {% endfor %}
  </div>

  <!-- CERTIFICATIONS (optional) -->
  {% if certifications and certifications|length > 0 %}
  <div class="section">
    <div class="section-title">Certifications</div>
    {% for cert in certifications %}
    <div class="cert-entry">
      <div class="cert-left">
        <div class="cert-name">{{ cert.name }}</div>
        {% if cert.issuer %}
        <div class="cert-issuer">{{ cert.issuer }}</div>
        {% endif %}
      </div>
      {% if cert.year %}
      <div class="cert-right">{{ cert.year }}</div>
      {% endif %}
    </div>
    {% endfor %}
  </div>
  {% endif %}

  <!-- TECHNICAL SKILLS -->
  <div class="section">
    <div class="section-title">Technical Skills</div>
    <div class="skills-grid">
      {% for category, items in skills.items() %}
      <div class="skill-row">
        <span class="skill-category">{{ category }}:</span>
        <span class="skill-list">{{ items | join(", ") }}</span>
      </div>
      {% endfor %}
    </div>
  </div>

</div>
</body>
</html>"""


def render_resume_html(resume_data: dict, page_target: int = 2) -> str:
    template = Template(RESUME_HTML_TEMPLATE)
    return template.render(
        contact=resume_data.get("contact", {}),
        professional_summary=resume_data.get("professional_summary", ""),
        experience=resume_data.get("experience", []),
        projects=resume_data.get("projects", []),
        education=resume_data.get("education", []),
        certifications=resume_data.get("certifications", []),
        skills=resume_data.get("skills", {}),
        page_target=page_target
    )
