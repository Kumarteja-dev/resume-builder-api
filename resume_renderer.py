"""
=============================================================================
ELITE RESUME BUILDER — HTML RENDERER
=============================================================================
Takes the final JSON from the pipeline and injects it into the
Jake's Resume / Harvard-standard ATS-safe HTML template.
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

  /* ===================================================================
     RESET & BASE
  =================================================================== */
  * {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
  }

  html, body {
    background: #ffffff;
    color: #000000;
    font-family: "Times New Roman", Times, serif;
    font-size: 10.5pt;
    line-height: 1.35;
  }

  /* ===================================================================
     PAGE GEOMETRY
     Mirrors US Letter (8.5in × 11in) at 96dpi.
     Tight 0.5in margins — maximizes content density.
  =================================================================== */
  .page {
    width: 8.5in;
    min-height: 11in;
    padding: 0.5in 0.6in 0.5in 0.6in;
    margin: 0 auto;
    background: #ffffff;
    position: relative;
  }

  /* Soft visual guide for page breaks — invisible on print */
  .page-break-guide {
    position: absolute;
    left: 0;
    right: 0;
    border-top: 1px dashed #e0e0e0;
    pointer-events: none;
  }
  .page-break-guide.p2 { top: 11in; }
  .page-break-guide.p3 { top: 22in; }

  @media print {
    .page {
      width: 8.5in;
      padding: 0.5in 0.6in 0.5in 0.6in;
      margin: 0;
    }
    .page-break-guide { display: none; }
    @page {
      size: letter;
      margin: 0;
    }
  }

  /* ===================================================================
     HEADER / CONTACT BLOCK
  =================================================================== */
  .header {
    text-align: center;
    margin-bottom: 4pt;
    padding-bottom: 3pt;
  }

  .header .name {
    font-size: 20pt;
    font-weight: bold;
    letter-spacing: 0.5pt;
    line-height: 1.1;
    margin-bottom: 3pt;
  }

  .header .contact-line {
    font-size: 9.5pt;
    color: #000000;
    letter-spacing: 0.1pt;
  }

  .header .contact-line a {
    color: #000000;
    text-decoration: none;
  }

  .contact-separator {
    margin: 0 5pt;
    font-weight: normal;
    color: #555;
  }

  /* ===================================================================
     SECTION STRUCTURE
  =================================================================== */
  .section {
    margin-top: 7pt;
    margin-bottom: 0;
  }

  .section-title {
    font-size: 10.5pt;
    font-weight: bold;
    text-transform: uppercase;
    letter-spacing: 0.8pt;
    border-bottom: 1.2pt solid #000000;
    padding-bottom: 1.5pt;
    margin-bottom: 5pt;
  }

  /* ===================================================================
     EXPERIENCE ENTRIES
  =================================================================== */
  .experience-entry {
    margin-bottom: 6pt;
  }

  .experience-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 1pt;
  }

  .company-title-block {
    flex: 1;
  }

  .company-name {
    font-size: 10.5pt;
    font-weight: bold;
  }

  .job-title {
    font-size: 10.5pt;
    font-style: italic;
    font-weight: normal;
  }

  .date-location {
    font-size: 10.5pt;
    text-align: right;
    white-space: nowrap;
    padding-left: 8pt;
  }

  .date-location .dates {
    font-weight: bold;
  }

  /* ===================================================================
     BULLET POINTS
  =================================================================== */
  .bullets {
    list-style: none;
    padding-left: 0;
    margin-top: 2pt;
  }

  .bullets li {
    position: relative;
    padding-left: 12pt;
    margin-bottom: 1.8pt;
    font-size: 10.5pt;
    line-height: 1.32;
    text-align: justify;
  }

  .bullets li::before {
    content: "-";
    position: absolute;
    left: 0;
    top: 0;
    font-weight: normal;
  }

  /* ===================================================================
     PROFESSIONAL SUMMARY
  =================================================================== */
  .summary-text {
    font-size: 10.5pt;
    line-height: 1.45;
    text-align: justify;
    margin-top: 1pt;
  }

  /* ===================================================================
     EDUCATION ENTRIES
  =================================================================== */
  .education-entry {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 3pt;
  }

  .edu-left .school-name {
    font-weight: bold;
    font-size: 10.5pt;
  }

  .edu-left .degree-line {
    font-style: italic;
    font-size: 10.5pt;
  }

  .edu-right {
    text-align: right;
    font-size: 10.5pt;
    font-weight: bold;
    white-space: nowrap;
    padding-left: 8pt;
  }

  /* ===================================================================
     SKILLS SECTION
  =================================================================== */
  .skills-grid {
    display: block;
  }

  .skill-row {
    display: flex;
    margin-bottom: 2.5pt;
    font-size: 10.5pt;
    line-height: 1.35;
  }

  .skill-category {
    font-weight: bold;
    min-width: 145pt;
    flex-shrink: 0;
  }

  .skill-list {
    flex: 1;
  }

  /* ===================================================================
     PRINT OVERRIDES
     Ensure clean page breaks — no orphaned headers or lone bullets
  =================================================================== */
  @media print {
    .experience-entry {
      page-break-inside: avoid;
    }
    .section {
      page-break-inside: avoid;
    }
    .section-title {
      page-break-after: avoid;
    }
  }

</style>
</head>
<body>
<div class="page">

  <!-- PAGE BREAK GUIDES (visible only on screen) -->
  <div class="page-break-guide p2"></div>
  {% if page_target == 3 %}
  <div class="page-break-guide p3"></div>
  {% endif %}

  <!-- ═══════════════════════════════════════════════════════
       HEADER: NAME + CONTACT
  ════════════════════════════════════════════════════════ -->
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

  <!-- ═══════════════════════════════════════════════════════
       PROFESSIONAL SUMMARY
  ════════════════════════════════════════════════════════ -->
  <div class="section">
    <div class="section-title">Professional Summary</div>
    <p class="summary-text">{{ professional_summary }}</p>
  </div>

  <!-- ═══════════════════════════════════════════════════════
       EXPERIENCE
  ════════════════════════════════════════════════════════ -->
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

  <!-- ═══════════════════════════════════════════════════════
       EDUCATION
  ════════════════════════════════════════════════════════ -->
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

  <!-- ═══════════════════════════════════════════════════════
       SKILLS
  ════════════════════════════════════════════════════════ -->
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
    """
    Takes the final JSON from the pipeline and renders the HTML template.

    Args:
        resume_data: The 'resume_data' field from the pipeline output dict.
        page_target: 2 or 3 (drives page break guide display).

    Returns:
        Fully rendered HTML string, ready to display or convert to PDF.
    """
    template = Template(RESUME_HTML_TEMPLATE)

    return template.render(
        contact=resume_data.get("contact", {}),
        professional_summary=resume_data.get("professional_summary", ""),
        experience=resume_data.get("experience", []),
        education=resume_data.get("education", []),
        skills=resume_data.get("skills", {}),
        page_target=page_target
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test this renderer standalone with sample data
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import json

    sample_data = {
        "contact": {
            "name": "Alex Chen",
            "email": "alex.chen@email.com",
            "phone": "+1 (415) 555-0192",
            "linkedin": "linkedin.com/in/alexchen",
            "location": "San Francisco, CA"
        },
        "professional_summary": (
            "Software Engineer II with 5 years of experience designing and scaling "
            "distributed systems at high-growth fintech companies. "
            "Expert in Python, Go, and cloud-native infrastructure, with a track record "
            "of reducing system latency by 40-70% across services handling 10M+ daily transactions. "
            "Recognized for cross-functional leadership, driving alignment between product, data, "
            "and engineering teams to deliver zero-defect launches ahead of schedule."
        ),
        "experience": [
            {
                "company": "Stripe",
                "title": "Software Engineer II",
                "start_date": "Mar 2022",
                "end_date": "Present",
                "bullets": [
                    "Architected a real-time fraud detection pipeline using Apache Kafka and Python, processing 8M transactions/day with 99.97% uptime and reducing fraudulent chargebacks by 34%.",
                    "Engineered a distributed rate-limiting service in Go that cut API abuse incidents by 61%, protecting 120K merchant accounts across 42 countries.",
                    "Redesigned the payment reconciliation system using PostgreSQL and event sourcing, reducing end-of-day processing time by 78% and eliminating 3 manual audit workflows.",
                    "Spearheaded a latency optimization initiative across 14 microservices, achieving a 45ms P99 improvement and increasing checkout conversion by 2.3% ($18M ARR impact).",
                    "Scaled the webhooks delivery infrastructure from 500K to 4M events/day using Kubernetes horizontal pod autoscaling, maintaining sub-200ms delivery SLAs.",
                    "Led a 4-engineer squad in migrating a legacy billing monolith to microservices, completing 6 weeks ahead of schedule with zero downtime across 85K active subscriptions.",
                    "Implemented automated integration test suite covering 1,400 API endpoints, reducing regression detection time from 3 days to 40 minutes and enabling daily deployments.",
                    "Collaborated with the ML team to build a dynamic pricing engine using scikit-learn, serving 2M daily pricing decisions with A/B-tested 7% revenue lift.",
                    "Mentored 3 junior engineers through bi-weekly code reviews and pairing sessions, accelerating their promotion timelines by an average of 4 months."
                ]
            },
            {
                "company": "Robinhood",
                "title": "Software Engineer I",
                "start_date": "Jun 2020",
                "end_date": "Feb 2022",
                "bullets": [
                    "Built the options order routing engine in Python using Celery and Redis, executing 1.2M trades/day with sub-50ms average latency during peak trading hours.",
                    "Optimized the real-time portfolio valuation service, reducing P99 response time from 820ms to 95ms using in-memory caching with Redis Cluster.",
                    "Developed an automated compliance reporting pipeline using Airflow and Snowflake, reducing SEC filing preparation time by 70% and eliminating manual errors.",
                    "Delivered a new account onboarding flow in Django REST Framework, increasing 7-day user activation by 22% across 800K new signups.",
                    "Integrated Plaid's bank verification API into the deposit flow, reducing ACH failure rates by 41% and saving $2.1M annually in failed transaction fees.",
                    "Contributed to the incident response runbook, reducing MTTD from 18 minutes to 4 minutes for P0 production events.",
                    "Shipped 14 A/B experiments on the home feed using internal experimentation framework, lifting weekly active trading sessions by 9% across 5M users."
                ]
            },
            {
                "company": "Palantir Technologies",
                "title": "Junior Software Engineer",
                "start_date": "Jul 2019",
                "end_date": "May 2020",
                "bullets": [
                    "Developed data transformation pipelines for a federal defense client using Foundry, processing 40TB/month of sensor data with 99.9% accuracy requirements.",
                    "Built interactive dashboards using React and TypeScript consumed by 200+ analysts, reducing time-to-insight from 3 days to 4 hours.",
                    "Automated a manual data ingestion workflow using Python and REST APIs, saving 120 analyst hours/week and reducing error rates by 95%.",
                    "Implemented row-level security controls in Foundry for a classified dataset, passing a third-party security audit with zero critical findings.",
                    "Supported production incidents across 6 client deployments, maintaining 99.95% uptime SLA and authoring 8 postmortem documents."
                ]
            }
        ],
        "education": [
            {
                "school": "UC Berkeley",
                "degree": "B.S.",
                "major": "Electrical Engineering & Computer Science",
                "grad_year": "2019"
            }
        ],
        "skills": {
            "Languages": ["Python", "Go", "TypeScript", "SQL", "Java"],
            "Infrastructure & Cloud": ["Kubernetes", "AWS (EC2, RDS, S3, Lambda)", "Docker", "Terraform", "GCP"],
            "Data & Frameworks": ["PostgreSQL", "Redis", "Apache Kafka", "Snowflake", "Airflow", "Django", "React"]
        }
    }

    html = render_resume_html(sample_data, page_target=2)

    with open("/home/claude/resume-builder/sample_resume_output.html", "w") as f:
        f.write(html)

    print("Sample resume HTML written to sample_resume_output.html")
