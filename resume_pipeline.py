"""
=============================================================================
ELITE AI RESUME BUILDER — PRODUCTION BACKEND PIPELINE v4
=============================================================================
Model: claude-sonnet-4-6
3-Step Pipeline: Specialist Writer → FAANG Critic → ATS Guard

NEW IN v4:
- Target job title field support
- Smart AI-generated projects (based on actual role/company/sector)
- Stronger JD keyword matching in Step 2
- Optional projects section (only renders if generated or provided)
- All sector awareness and anti-fabrication rules from v3
=============================================================================
"""

import json
import re
import anthropic
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

MODEL = "claude-sonnet-4-6"
MAX_TOKENS_STEP1 = 4096
MAX_TOKENS_STEP2 = 8096
MAX_TOKENS_STEP3 = 8096

client = anthropic.Anthropic()


# ─────────────────────────────────────────────────────────────────────────────
# COMPANY STYLE PROMPTS
# ─────────────────────────────────────────────────────────────────────────────

COMPANY_STYLE_PROMPTS = {
    "GOOGLE": """
COMPANY STYLE: GOOGLE
- Write every bullet using the X-Y-Z formula: "Accomplished [X] as measured by [Y], by doing [Z]"
- Lead with hard numbers, percentages, user counts, revenue figures, latency improvements.
- Prioritize technical rigor, system scale, and engineering precision.
- Use Google vocabulary: "launched", "scaled", "shipped", "reduced latency", "drove adoption".
- Professional Summary must reference cross-functional leadership and measurable impact.
- Projects should demonstrate personal initiative, open source contributions, or system design.
""",
    "AMAZON": """
COMPANY STYLE: AMAZON
- Frame every bullet around Amazon Leadership Principles:
  Customer Obsession, Ownership, Deliver Results, Bias for Action, Think Big.
- Include operational scale metrics: customers served, transactions processed, cost saved.
- Use Amazon vocabulary: "owned end-to-end", "drove operational excellence", "eliminated waste".
- Professional Summary must open with customer-first framing and mention scale.
- Projects should demonstrate ownership and bias for action outside normal job scope.
""",
    "APPLE": """
COMPANY STYLE: APPLE
- Emphasize design precision, product craftsmanship, and cross-functional execution.
- Tone: elegant, concise, confident. Let metrics speak quietly.
- Use Apple vocabulary: "crafted", "refined", "shipped", "elevated the experience".
- Professional Summary should feel visionary but grounded.
- Projects should demonstrate attention to detail and end-user experience focus.
""",
    "META": """
COMPANY STYLE: META
- Every bullet implies speed, iteration, and scale.
- Focus on data-driven decisions: A/B tests, DAU/MAU, engagement rates.
- Use Meta vocabulary: "drove growth", "shipped experiment", "moved metric", "built at scale".
- Professional Summary must reference building products that impact billions.
- Projects should demonstrate data-driven thinking and rapid iteration.
""",
    "NVIDIA": """
COMPANY STYLE: NVIDIA
- Deeply technical. Lead with engineering problem-solving and innovation.
- Reference: CUDA, GPU architecture, ML infrastructure, performance benchmarks.
- Use NVIDIA vocabulary: "architected", "optimized kernel", "reduced inference latency".
- Professional Summary must establish deep technical mastery.
- Projects should demonstrate low-level technical depth and performance optimization.
""",
    "NETFLIX": """
COMPANY STYLE: NETFLIX
- Emphasize autonomy, high-judgment, Freedom and Responsibility culture.
- Use Netflix vocabulary: "operated with full autonomy", "owned the strategy",
  "delivered outsized impact", "no playbook - built it".
- Professional Summary should read like a confident executive who needs no supervision.
- Projects should demonstrate independent thinking and outsized personal impact.
""",
    "TIKTOK": """
COMPANY STYLE: TIKTOK
- Emphasize hyper-growth, consumer trend adaptation, international localization.
- Include metrics: videos served, creator growth, market penetration, engagement uplift.
- Use TikTok vocabulary: "drove creator growth", "optimized the feed", "shipped viral feature".
- Projects should demonstrate consumer product thinking and rapid shipping culture.
""",
    "FORTUNE50": """
COMPANY STYLE: FORTUNE 50 / ELITE CORPORATE
- Focus on corporate scale: P&L responsibility, budgets, enterprise clients, global teams.
- Use executive vocabulary: "P&L ownership", "managed $XXM budget", "led team of XX".
- Professional Summary should read like a C-suite biography — gravitas and impact.
- Projects should demonstrate strategic thinking and enterprise-scale impact.
""",
    "GENERAL": """
COMPANY STYLE: GENERAL COMPETITIVE
- Use STAR method embedded naturally into each bullet.
- Balance hard skills with leadership and collaboration.
- Every bullet must be metric-driven: %, $, X times, N users, N team members.
- Professional Summary should be compelling to any Fortune 500 recruiter.
- Projects should demonstrate initiative and measurable personal contribution.
"""
}


# ─────────────────────────────────────────────────────────────────────────────
# SECTOR DETECTION
# ─────────────────────────────────────────────────────────────────────────────

SECTOR_KEYWORDS = {
    "finance": [
        "banking", "financial", "investment", "trading", "risk", "compliance",
        "sox", "basel", "fintech", "capital markets", "wealth management",
        "jpmorgan", "goldman", "morgan stanley", "wells fargo", "citibank",
        "hedge fund", "private equity", "insurance", "credit", "loan"
    ],
    "healthcare": [
        "healthcare", "health care", "hospital", "clinical", "patient",
        "hipaa", "ehr", "electronic health", "medical", "pharma",
        "pharmaceutical", "cvs", "walgreens", "unitedhealth", "cigna",
        "aetna", "fda", "drug", "diagnosis", "treatment", "care"
    ],
    "ecommerce": [
        "ecommerce", "e-commerce", "retail", "marketplace", "shopify",
        "fulfillment", "inventory", "catalog", "checkout", "merchant"
    ],
    "technology": [
        "software", "engineer", "developer", "cloud", "infrastructure",
        "platform", "api", "microservices", "kubernetes", "devops",
        "machine learning", "ai", "data science", "backend", "frontend"
    ],
    "cpg": [
        "consumer goods", "cpg", "fmcg", "supply chain", "manufacturing",
        "pepsi", "coca-cola", "unilever", "procter", "nestle",
        "distribution", "logistics", "warehouse", "procurement"
    ]
}


def detect_sector(text: str) -> str:
    text_lower = text.lower()
    scores = {}
    for sector, keywords in SECTOR_KEYWORDS.items():
        scores[sector] = sum(1 for kw in keywords if kw in text_lower)
    if max(scores.values()) == 0:
        return "general"
    return max(scores, key=scores.get)


# ─────────────────────────────────────────────────────────────────────────────
# YEARS OF EXPERIENCE CALCULATOR
# ─────────────────────────────────────────────────────────────────────────────

def calculate_years_from_jobs(employment: list) -> int:
    if not employment:
        return 4

    month_map = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
    }

    earliest_start = None
    now = datetime.now()

    for job in employment:
        try:
            start_str = job.get("start_date", "").strip().lower()
            parts = start_str.replace(",", "").split()
            if len(parts) == 2:
                month = month_map.get(parts[0][:3], 1)
                year = int(parts[1])
                start_dt = datetime(year, month, 1)
                if earliest_start is None or start_dt < earliest_start:
                    earliest_start = start_dt
        except Exception:
            continue

    if earliest_start is None:
        return 4

    years = (now - earliest_start).days / 365.25
    return max(1, int(years))


# ─────────────────────────────────────────────────────────────────────────────
# PAGE DENSITY RULES
# ─────────────────────────────────────────────────────────────────────────────

def get_density_rules(years_experience: int, num_jobs: int) -> str:
    if years_experience >= 8:
        scope = "3 FULL PAGES (Senior/Executive level)"
    else:
        scope = "2 FULL PAGES (Mid-level professional)"

    job_rules = []
    for i in range(num_jobs):
        if i == 0:
            job_rules.append(f"  - Job 1 (Most Recent): EXACTLY 9-10 bullet points.")
        elif i == 1:
            job_rules.append(f"  - Job 2: EXACTLY 7-8 bullet points.")
        else:
            job_rules.append(f"  - Job {i+1} (Older Role): EXACTLY 5-6 bullet points.")

    return f"""
MANDATORY PAGE DENSITY RULES:
TARGET: {scope}

1. PROFESSIONAL SUMMARY: Exactly 5 dense sentences as a single paragraph.
   - Open with the candidate's exact target job title
   - Reference years of experience accurately
   - Include 2-3 hard metrics
   - End with what they bring to the target company

2. PER-JOB BULLET COUNTS:
{chr(10).join(job_rules)}

3. EVERY BULLET MUST:
   - Start with a strong action verb
   - Contain at least one quantified metric (%, $, Xx, N users, N team members)
   - Reference a specific tool, methodology, or framework

4. SKILLS: 3 categories of 6-8 items each.
   Use candidate's provided skills as foundation.

5. CERTIFICATIONS: Include exactly as provided. Never invent.

6. PROJECTS: If included, each project needs:
   - Project name
   - Tech stack used
   - 2 bullet points with metrics and impact

7. WORD COUNT:
   - 2-page resume: 900-1,100 words
   - 3-page resume: 1,400-1,700 words
"""


# ─────────────────────────────────────────────────────────────────────────────
# SECTOR AWARENESS RULES
# ─────────────────────────────────────────────────────────────────────────────

def get_sector_rules(candidate_sector: str, target_sector: str,
                     target_company: str) -> str:
    same_sector = (candidate_sector == target_sector or
                   candidate_sector == "general" or
                   target_sector == "general")

    base_rules = f"""
CRITICAL HONESTY AND SECTOR RULES — NEVER VIOLATE:

1. TARGET COMPANY NAME RULE:
   - NEVER write the target company name ({target_company}) inside any
     bullet point or summary UNLESS the candidate actually worked there.
   - Injecting the target company name into bullets where the candidate
     did not work there is resume fraud. Do not do it.

2. SECTOR INTEGRITY:
   - Candidate sector: {candidate_sector.upper()}
   - Target company sector: {target_sector.upper()}
"""

    if same_sector:
        base_rules += """
   - Sectors are compatible. You may use industry terminology from
     the JD naturally within the candidate's experience.
"""
    else:
        base_rules += f"""
   - SECTORS DIFFER. Do NOT inject {target_sector.upper()}-specific
     jargon into the candidate's {candidate_sector.upper()} experience.
   - Instead highlight TRANSFERABLE SKILLS:
     * Leadership and team scale
     * System scale and reliability metrics
     * Process improvement percentages
     * Cross-functional collaboration
     * Delivery and execution metrics
   - For PROJECTS: generate projects realistic for a
     {candidate_sector.upper()} professional at their seniority level.
     Use technologies natural to their domain, not the target domain.
"""

    base_rules += """
3. FABRICATION RULE:
   - Never invent companies, certifications, or technologies not provided.
   - Never imply the candidate worked somewhere they did not.
   - Never add years of experience beyond what the dates show.
   - For projects: generate realistic projects a person in their role
     and company would actually work on. Must be defensible in interview.
"""
    return base_rules


# ─────────────────────────────────────────────────────────────────────────────
# SMART PROJECT GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

def generate_projects_prompt(employment: list, candidate_sector: str,
                              target_company: str, target_job_title: str,
                              jd: str, years_exp: int) -> str:
    """
    Builds the prompt section for AI-generated notable projects.
    Projects are based on the candidate's actual role and company,
    not fabricated to match the target company's domain.
    """

    if not employment:
        return ""

    most_recent = employment[0]
    current_title = most_recent.get("title", "")
    current_company = most_recent.get("company", "")

    seniority = "junior" if years_exp < 3 else \
                "mid-level" if years_exp < 6 else \
                "senior" if years_exp < 10 else "principal/staff"

    return f"""
NOTABLE PROJECTS GENERATION INSTRUCTIONS:
Generate 2 notable projects for this candidate. Follow these rules strictly:

CANDIDATE CONTEXT:
  - Current Role: {current_title} at {current_company}
  - Sector: {candidate_sector.upper()}
  - Seniority: {seniority} ({years_exp} years experience)
  - Applying for: {target_job_title} at {target_company}

PROJECT RULES:
1. Projects MUST be realistic for a {seniority} {current_title}
   working at a company like {current_company}.
2. Use technologies natural to their role and sector — not the target
   company's tech stack unless they overlap with the candidate's domain.
3. Projects should show initiative BEYOND their normal job duties —
   internal tools they built, automation they created, systems they
   improved on their own time or as side initiatives.
4. Each project must have 2 bullet points with real metrics.
5. Projects must be defensible in a technical interview — a real person
   in this role could explain them in detail.
6. DO NOT generate projects that require knowledge the candidate
   wouldn't have based on their role and sector.
7. Projects should highlight skills that transfer to the target role
   without fabricating cross-sector expertise.

EXAMPLE of a GOOD project for a Software Engineer at a healthcare company
applying to a bank:
  - "Patient Data Analytics Dashboard" using Python and React — shows
    full-stack skills, data handling, internal tooling — transferable.

EXAMPLE of a BAD project for the same person:
  - "Algorithmic Trading Engine" — they work in healthcare, this is
    fabricated finance expertise. Do not do this.

Include projects in the JSON output under the "projects" key.
"""


# ─────────────────────────────────────────────────────────────────────────────
# SAFE JSON EXTRACTOR
# ─────────────────────────────────────────────────────────────────────────────

def extract_json(raw: str) -> dict:
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No valid JSON found. Raw:\n{raw[:500]}")
    return json.loads(cleaned[start:end])


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: THE SPECIALIST WRITER
# ─────────────────────────────────────────────────────────────────────────────

def step1_specialist_writer(payload: dict) -> str:
    company = payload.get("company_target", "GENERAL")
    company_prompt = COMPANY_STYLE_PROMPTS.get(
        company, COMPANY_STYLE_PROMPTS["GENERAL"])
    years_exp = payload.get("years_experience", 4)
    jd = payload.get("job_description", "")
    workflow = payload.get("workflow", "tailor")
    user_skills = payload.get("skills", "")
    certifications = payload.get("certifications", [])
    target_job_title = payload.get("target_job_title", "")
    include_projects = payload.get("include_projects", False)

    # Detect sectors
    candidate_text = payload.get("existing_resume_text", "")
    if not candidate_text and payload.get("employment"):
        candidate_text = " ".join([
            f"{e.get('title', '')} {e.get('company', '')}"
            for e in payload.get("employment", [])
        ])
    candidate_sector = detect_sector(candidate_text)
    target_sector = detect_sector(jd + " " + company)
    sector_rules = get_sector_rules(candidate_sector, target_sector, company)

    if workflow == "scratch":
        employment = payload.get("employment", [])
        num_jobs = len(employment) if employment else 1
        calculated_years = calculate_years_from_jobs(employment)
        years_exp = max(years_exp, calculated_years)
    else:
        num_jobs = 3
        employment = []

    density_rules = get_density_rules(years_exp, max(num_jobs, 1))

    # Projects prompt
    projects_prompt = ""
    if include_projects and workflow == "scratch":
        projects_prompt = generate_projects_prompt(
            employment, candidate_sector, company,
            target_job_title or "the target role", jd, years_exp
        )

    # Certifications block
    cert_block = ""
    if certifications:
        if isinstance(certifications, list):
            cert_lines = "\n".join([
                f"  - {c.get('name', '')} | "
                f"{c.get('issuer', '')} | {c.get('year', '')}"
                for c in certifications if c.get("name")
            ])
        else:
            cert_lines = str(certifications)
        cert_block = f"""
CERTIFICATIONS (include accurately — never alter or invent):
{cert_lines}
"""

    # Skills block
    skills_block = ""
    if user_skills:
        skills_block = f"""
CANDIDATE'S ACTUAL SKILLS (use as foundation):
{user_skills}
"""

    # Target job title instruction
    title_instruction = ""
    if target_job_title:
        title_instruction = f"""
TARGET JOB TITLE: {target_job_title}
- Open the Professional Summary with this exact title.
- Use this title as the lens for all keyword and skill alignment.
"""

    if workflow == "tailor":
        source_material = f"""
SOURCE MATERIAL (Existing Resume):
{payload.get('existing_resume_text', '')}
{cert_block}
{skills_block}
"""
        task_instruction = f"""
TASK: Tailor this existing resume. You MUST:
- Preserve ALL company names, job titles, and dates EXACTLY as written.
- Rewrite bullets to be stronger, metric-driven, and JD-aligned.
- Add bullets to hit density targets if needed.
- Candidate has {years_exp} years experience — reflect this accurately.
- Do NOT invent employers, change titles, or fabricate experience.
- Do NOT inject target company name into bullets unless candidate worked there.
{title_instruction}
"""
    else:
        contact = payload.get("contact", {})
        education = payload.get("education", [])

        emp_block = "\n".join([
            f"  - {e.get('title', '')} at {e.get('company', '')} | "
            f"{e.get('start_date', '')} - {e.get('end_date', '')}"
            for e in employment
        ])
        edu_block = "\n".join([
            f"  - {e.get('degree', '')} in {e.get('major', '')}, "
            f"{e.get('school', '')} ({e.get('grad_year', '')})"
            for e in education
        ])

        source_material = f"""
SOURCE MATERIAL (preserve ALL of this exactly):
CONTACT:
  Name: {contact.get('name', '')}
  Email: {contact.get('email', '')}
  Phone: {contact.get('phone', '')}
  LinkedIn: {contact.get('linkedin', '')}
  Location: {contact.get('location', '')}

EMPLOYMENT (verbatim — never change):
{emp_block}

EDUCATION (verbatim):
{edu_block}
{cert_block}
{skills_block}
"""
        task_instruction = f"""
TASK: Build resume FROM SCRATCH using structural data above. You MUST:
- Use ALL company names, job titles, and dates EXACTLY as provided.
- Candidate has {years_exp} years experience. Reflect THIS — not the JD requirement.
- Construct all bullets tailored to JD and company style.
- Use candidate's actual skills as foundation for skills section.
- Include all certifications exactly as provided.
- Apply sector rules — do not fabricate cross-sector experience.
{title_instruction}
{projects_prompt}
"""

    system_prompt = f"""You are the world's most elite resume writer, trained exclusively
on resumes that achieved callbacks at FAANG and Fortune 50 companies.
You write with surgical precision, metric-first language, and absolute honesty.
You never fabricate experience. You never inject false company associations.
You highlight real transferable value rather than inventing fake matches.

{company_prompt}
{density_rules}
{sector_rules}
"""

    # Build JSON schema based on whether projects are included
    projects_schema = ""
    if include_projects:
        projects_schema = """
  "projects": [
    {
      "name": "...",
      "tech_stack": "...",
      "bullets": ["bullet with metric", "bullet with metric"]
    }
  ],"""

    user_prompt = f"""
{source_material}

TARGET JOB DESCRIPTION:
{jd}

{task_instruction}

OUTPUT: Valid JSON only. No markdown. No explanation.

{{
  "contact": {{
    "name": "...", "email": "...", "phone": "...",
    "linkedin": "...", "location": "..."
  }},
  "professional_summary": "Exactly 5 sentences as single paragraph.",
  "experience": [
    {{
      "company": "...", "title": "...",
      "start_date": "...", "end_date": "...",
      "bullets": ["bullet 1", "bullet 2"]
    }}
  ],
  "education": [
    {{"school": "...", "degree": "...", "major": "...", "grad_year": "..."}}
  ],
  "certifications": [
    {{"name": "...", "issuer": "...", "year": "..."}}
  ],{projects_schema}
  "skills": {{
    "category_1": ["skill", "skill"],
    "category_2": ["skill", "skill"],
    "category_3": ["skill", "skill"]
  }}
}}
"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS_STEP1,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}]
    )

    return response.content[0].text


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: THE HARSH FAANG CRITIC
# ─────────────────────────────────────────────────────────────────────────────

def step2_faang_critic(step1_output: str, payload: dict) -> str:
    jd = payload.get("job_description", "")
    company = payload.get("company_target", "GENERAL")
    company_prompt = COMPANY_STYLE_PROMPTS.get(
        company, COMPANY_STYLE_PROMPTS["GENERAL"])
    years_exp = payload.get("years_experience", 4)
    target_job_title = payload.get("target_job_title", "")

    candidate_text = payload.get("existing_resume_text", "")
    if not candidate_text and payload.get("employment"):
        candidate_text = " ".join([
            f"{e.get('title', '')} {e.get('company', '')}"
            for e in payload.get("employment", [])
        ])
    candidate_sector = detect_sector(candidate_text)
    target_sector = detect_sector(jd + " " + company)
    sector_rules = get_sector_rules(candidate_sector, target_sector, company)

    # Extract top 10 JD keywords for gap analysis
    jd_words = re.findall(r'\b[A-Za-z][A-Za-z+#.]{2,}\b', jd)
    jd_freq = {}
    for word in jd_words:
        w = word.lower()
        jd_freq[w] = jd_freq.get(w, 0) + 1
    stop_words = {
        "the", "and", "for", "with", "that", "this", "will", "are",
        "have", "from", "our", "you", "your", "not", "but", "all",
        "can", "been", "their", "they", "what", "who", "how", "when"
    }
    top_keywords = [
        w for w, c in sorted(jd_freq.items(), key=lambda x: -x[1])
        if w not in stop_words
    ][:15]
    keyword_list = ", ".join(top_keywords)

    system_prompt = f"""You are the harshest, most exacting FAANG resume critic alive.
You have reviewed 50,000+ resumes at Google, Amazon, and Meta.
You are also an expert in resume ethics — you never fabricate experience.

{sector_rules}

Return ONLY improved JSON. Same schema. No markdown. No explanation."""

    user_prompt = f"""
COMPANY: {company}
TARGET JOB TITLE: {target_job_title or "Not specified"}
CANDIDATE YEARS: {years_exp} (do not change this in the summary)
{company_prompt}

TOP JD KEYWORDS TO VERIFY ARE IN RESUME:
{keyword_list}

JOB DESCRIPTION:
{jd}

DRAFT RESUME JSON:
{step1_output}

CRITIQUE CHECKLIST — fix ALL:

1. WEAK VERBS — Replace:
   BAD: "Helped", "Assisted", "Supported", "Worked on", "Participated",
        "Was responsible for", "Contributed to", "Involved in"
   GOOD: "Architected", "Engineered", "Spearheaded", "Accelerated",
         "Slashed", "Drove", "Launched", "Scaled", "Orchestrated"

2. AI FILLER — Delete:
   "Leveraged synergies", "Demonstrated expertise", "Utilized best practices",
   "Passionate about", "Results-driven", "Detail-oriented",
   "Proven track record", "Dynamic professional", "Seeking to"

3. MISSING METRICS — Every bullet needs a number. Add one if missing.

4. JD KEYWORD GAP ANALYSIS:
   Check these top keywords from the JD: {keyword_list}
   For each keyword NOT in the resume:
   - If it matches the candidate's sector and experience → inject naturally
   - If it does NOT match their background → skip it (do not fabricate)

5. SUMMARY:
   - Must open with target job title: "{target_job_title or 'their job title'}"
   - Must reflect {years_exp} years accurately
   - Must NOT start with "I"
   - Must NOT use filler phrases
   - Exactly 5 sentences

6. DENSITY — Add bullets if any job is below minimum.

7. FABRICATION SCAN:
   - Remove any bullet implying candidate worked at {company} if they did not
   - Remove any cross-sector jargon not matching candidate's background
   - Verify projects (if present) are realistic for candidate's role

8. CERTIFICATIONS — Preserve exactly. Never alter.

9. PROJECTS — If present, verify each has 2 metric-driven bullets
   and is realistic for the candidate's actual role and company.

Return perfected JSON. Same schema. No markdown.
"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS_STEP2,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}]
    )

    return response.content[0].text


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3: THE ATS GUARD & PROOFREADER
# ─────────────────────────────────────────────────────────────────────────────

def step3_ats_guard(step2_output: str, payload: dict) -> dict:
    years_exp = payload.get("years_experience", 4)
    page_target = 3 if years_exp >= 8 else 2
    company = payload.get("company_target", "GENERAL")

    system_prompt = """You are an elite ATS compliance officer, proofreader,
and resume ethics officer. You are the final gate before a resume
reaches a real recruiter. Return ONLY clean JSON. Same schema. No markdown."""

    user_prompt = f"""
PAGE TARGET: {page_target} pages
TARGET COMPANY: {company}

RESUME JSON:
{step2_output}

FINAL CHECKLIST:

1. GRAMMAR & TENSE:
   - Current job: present tense ("Leads", "Manages", "Drives")
   - Past jobs: past tense ("Led", "Managed", "Drove")

2. VERB REPETITION:
   - No action verb more than twice across entire resume.
   - Replace duplicates with strong synonyms.

3. ATS SAFETY:
   - No special characters: no arrows, stars, checkmarks
   - Spell out acronyms at first use: "Machine Learning (ML)"
   - Plain ASCII only

4. BULLET LENGTH:
   - Each bullet: ~100 characters max at 10pt font
   - Split bullets over limit into two
   - No bullet under 60 characters

5. SUMMARY: Exactly 5 sentences, 75-85 words total.

6. SKILLS: 6-8 items per category. No duplicates.

7. CERTIFICATIONS: Preserve exactly. Never alter or remove.

8. PROJECTS: If present, ensure each has exactly 2 bullet points
   with metrics. Verify they are realistic for the candidate's role.

9. FABRICATION FINAL SCAN:
   - Any bullet implying candidate worked at {company} when they
     did not → rewrite to remove false implication.
   - Any invented certifications → remove.
   - Any cross-sector jargon not matching candidate background → remove.

10. DENSITY:
    - 3-page + under 1,400 words = expand bullets
    - 2-page + under 900 words = expand bullets

Return the final, flawless, honest JSON.
"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS_STEP3,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}]
    )

    raw = response.content[0].text
    return extract_json(raw)


# ─────────────────────────────────────────────────────────────────────────────
# MASTER PIPELINE ORCHESTRATOR
# ─────────────────────────────────────────────────────────────────────────────

def run_pipeline(payload: dict) -> dict:

    print(f"[PIPELINE] Starting | Company: {payload.get('company_target')} | "
          f"Workflow: {payload.get('workflow')} | "
          f"Years: {payload.get('years_experience')} | "
          f"Projects: {payload.get('include_projects', False)}")

    # Auto-calculate years for scratch workflow
    if payload.get("workflow") == "scratch":
        employment = payload.get("employment", [])
        if employment:
            calculated = calculate_years_from_jobs(employment)
            provided = payload.get("years_experience", 4)
            payload["years_experience"] = max(provided, calculated)
            print(f"[PIPELINE] Years: provided={provided}, "
                  f"calculated={calculated}, "
                  f"using={payload['years_experience']}")

    # Detect and log sectors
    candidate_text = payload.get("existing_resume_text", "")
    if not candidate_text and payload.get("employment"):
        candidate_text = " ".join([
            f"{e.get('title', '')} {e.get('company', '')}"
            for e in payload.get("employment", [])
        ])
    jd = payload.get("job_description", "")
    company = payload.get("company_target", "GENERAL")
    candidate_sector = detect_sector(candidate_text)
    target_sector = detect_sector(jd + " " + company)
    print(f"[PIPELINE] Sectors: candidate={candidate_sector}, "
          f"target={target_sector}")

    # ── STEP 1 ───────────────────────────────────────────────────────────
    print("[PIPELINE] Step 1: Specialist Writer...")
    s1_output = step1_specialist_writer(payload)
    print(f"[PIPELINE] Step 1 complete. {len(s1_output)} chars")

    # ── STEP 2 ───────────────────────────────────────────────────────────
    print("[PIPELINE] Step 2: FAANG Critic...")
    try:
        s2_output = step2_faang_critic(s1_output, payload)
        extract_json(s2_output)
        print(f"[PIPELINE] Step 2 complete. {len(s2_output)} chars")
    except Exception as e:
        print(f"[PIPELINE] Step 2 failed ({e}). Using Step 1 output.")
        s2_output = s1_output

    # ── STEP 3 ───────────────────────────────────────────────────────────
    print("[PIPELINE] Step 3: ATS Guard...")
    try:
        final_data = step3_ats_guard(s2_output, payload)
        print("[PIPELINE] Step 3 complete.")
    except Exception as e:
        print(f"[PIPELINE] Step 3 failed ({e}). Using Step 2 output.")
        final_data = extract_json(s2_output)

    years_exp = payload.get("years_experience", 4)
    page_target = 3 if years_exp >= 8 else 2

    from resume_renderer import render_resume_html
    html = render_resume_html(final_data, page_target)

    return {
        "success": True,
        "resume_data": final_data,
        "page_target": page_target,
        "company_target": payload.get("company_target", "GENERAL"),
        "html": html,
        "debug": {
            "step1_chars": len(s1_output),
            "step2_chars": len(s2_output),
            "step3_complete": True,
            "years_experience_used": payload.get("years_experience", 4),
            "candidate_sector": candidate_sector,
            "target_sector": target_sector,
            "projects_included": payload.get("include_projects", False)
        }
    }
