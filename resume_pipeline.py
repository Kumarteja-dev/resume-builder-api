"""
=============================================================================
ELITE AI RESUME BUILDER — PRODUCTION BACKEND PIPELINE
=============================================================================
CTO Architecture: 3-Step Sequential LLM Pipeline
Model: claude-sonnet-4-6
=============================================================================
"""

import json
import re
import anthropic

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

MODEL = "claude-sonnet-4-6"
MAX_TOKENS_STEP1 = 4096
MAX_TOKENS_STEP2 = 8096   # Increased — critic needs room to rewrite
MAX_TOKENS_STEP3 = 8096   # Increased — ATS guard needs room to finalize

client = anthropic.Anthropic()  # Reads ANTHROPIC_API_KEY from environment


# ─────────────────────────────────────────────────────────────────────────────
# COMPANY-SPECIFIC STYLE PROMPTS
# ─────────────────────────────────────────────────────────────────────────────

COMPANY_STYLE_PROMPTS = {
    "GOOGLE": """
COMPANY STYLE: GOOGLE
- Write every single bullet using the X-Y-Z formula EXACTLY:
  "Accomplished [X] as measured by [Y], by doing [Z]"
- Lead with hard numbers, percentages, user counts, revenue figures, latency improvements.
- Prioritize technical rigor, system scale, and engineering precision.
- Use Google's vocabulary: "launched", "scaled", "shipped", "reduced latency", "drove adoption".
- The Professional Summary must reference cross-functional leadership and measurable product/technical impact.
""",

    "AMAZON": """
COMPANY STYLE: AMAZON
- Frame every bullet around Amazon's 16 Leadership Principles, especially:
  Customer Obsession, Ownership, Deliver Results, Bias for Action, Think Big.
- Include operational scale metrics: customers served, transactions processed, cost saved.
- Use Amazon vocabulary: "owned end-to-end", "wrote the PRD", "drove operational excellence",
  "eliminated waste", "mechanisms built".
- The Professional Summary must open with a customer-first framing and mention scale.
- Every bullet should imply someone who acts with autonomy and accountability.
""",

    "APPLE": """
COMPANY STYLE: APPLE
- Emphasize design precision, product craftsmanship, and cross-functional execution.
- Tone: elegant, concise, confident — never boastful. Let metrics speak quietly.
- Bullets should reference design systems, hardware/software integration, deep collaboration
  with design/engineering/marketing partners.
- Use Apple vocabulary: "crafted", "refined", "shipped", "collaborated cross-functionally",
  "drove adoption", "elevated the experience".
- The Professional Summary should feel like a cover of Fast Company — visionary but grounded.
""",

    "META": """
COMPANY STYLE: META
- "Move Fast" is the mantra. Every bullet should imply speed, iteration, and scale.
- Focus on data-driven decisions: A/B tests, north-star metrics, DAU/MAU, engagement rates.
- Emphasize cross-functional product impact: worked with eng, design, data science, policy.
- Use Meta vocabulary: "drove growth", "shipped experiment", "moved metric", "built at scale",
  "zero-to-one product", "iterated rapidly".
- The Professional Summary must reference building products that impact billions of users.
""",

    "NVIDIA": """
COMPANY STYLE: NVIDIA
- This is a deeply technical company. Lead with engineering problem-solving and innovation.
- Bullets should reference: CUDA, GPU architecture, ML infrastructure, silicon design,
  hardware/software co-design, performance benchmarks (FLOPs, throughput, power efficiency).
- Emphasize industry-defining impact: "first-of-kind", "state-of-the-art", "new benchmark".
- Use NVIDIA vocabulary: "architected", "optimized kernel", "reduced inference latency",
  "improved throughput by Nx", "developed pipeline".
- The Professional Summary must establish deep technical mastery and pioneering contributions.
""",

    "NETFLIX": """
COMPANY STYLE: NETFLIX
- Emphasize Netflix's "Freedom and Responsibility" culture: autonomous, high-judgment,
  no-rules-rules environment.
- Every bullet should imply a "stunning colleague" — someone who sets context, not control.
- Focus on high-performance outcomes, independent decision-making, giving/receiving radical feedback.
- Use Netflix vocabulary: "operated with full autonomy", "set context for", "owned the strategy",
  "earned trust of", "delivered outsized impact", "no playbook — built it".
- The Professional Summary should read like a confident executive who doesn't need supervision.
""",

    "TIKTOK": """
COMPANY STYLE: TIKTOK
- Emphasize hyper-growth, consumer trend adaptation, and international localization.
- Bullets should reference algorithm optimization, content loop design, creator/user
  growth funnels, and cross-border team collaboration.
- Include metrics: videos served, creator growth %, market penetration, engagement uplift.
- Use TikTok vocabulary: "localized for", "drove creator growth", "optimized the feed",
  "shipped viral feature", "collaborated with global counterparts".
- The Professional Summary should convey agility, global thinking, and rapid shipping culture.
""",

    "FORTUNE50": """
COMPANY STYLE: FORTUNE 50 / ELITE CORPORATE
- Focus on corporate scale: P&L responsibility, multi-million dollar budgets, enterprise clients,
  global team leadership (headcount), board-level presentations.
- Emphasize financial impact: cost savings, revenue generated, EBITDA contribution, market share gained.
- Use executive vocabulary: "P&L ownership", "managed $XXM budget", "led team of XX",
  "negotiated enterprise contracts", "drove strategic initiative".
- The Professional Summary should read like a C-suite executive biography — gravitas and impact.
""",

    "GENERAL": """
COMPANY STYLE: GENERAL COMPETITIVE
- Use the STAR method (Situation, Task, Action, Result) embedded naturally into each bullet.
- Balance hard skills (technical tools, methodologies) with leadership and collaboration.
- Integrate a robust mix of hard ATS keywords naturally throughout.
- Every bullet must be metric-driven: %, $, X times, ranked #N, N users, N team members.
- The Professional Summary should be a clean, impactful paragraph that any Fortune 500 recruiter
  would find compelling.
"""
}


# ─────────────────────────────────────────────────────────────────────────────
# PAGE DENSITY RULES
# ─────────────────────────────────────────────────────────────────────────────

def get_density_rules(years_experience: int, num_jobs: int) -> str:
    if years_experience >= 8:
        page_target = 3
        scope = "3 FULL PAGES (Senior/Executive level)"
    else:
        page_target = 2
        scope = "2 FULL PAGES (Mid-level professional)"

    job_rules = []
    for i in range(num_jobs):
        if i == 0:
            job_rules.append(f"  - Job 1 (Most Recent): Generate EXACTLY 9-10 bullet points.")
        elif i == 1:
            job_rules.append(f"  - Job 2: Generate EXACTLY 7-8 bullet points.")
        else:
            job_rules.append(f"  - Job {i+1} (Older Role): Generate EXACTLY 5-6 bullet points.")

    bullet_job_rules = "\n".join(job_rules)

    return f"""
MANDATORY PAGE DENSITY RULES:
TARGET: {scope} — you MUST fill this space completely.

1. PROFESSIONAL SUMMARY: Exactly 5 dense, impactful sentences as a single paragraph.

2. PER-JOB BULLET POINT COUNTS:
{bullet_job_rules}

3. BULLET POINT FORMULA (every single bullet):
   - MUST start with a strong action verb
   - MUST contain at least one quantified metric (%, $, Xx, N users, N team members)
   - MUST reference a specific technical tool, methodology, or framework

4. SKILLS SECTION: 18-24 skills in 3 subcategories.

5. TOTAL WORD COUNT:
   - 2-page resume: 900-1,100 words
   - 3-page resume: 1,400-1,700 words
"""


# ─────────────────────────────────────────────────────────────────────────────
# SAFE JSON EXTRACTOR (shared utility)
# ─────────────────────────────────────────────────────────────────────────────

def extract_json(raw: str) -> dict:
    """Strips markdown fences and extracts the outermost JSON object."""
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No valid JSON found. Raw output:\n{raw[:500]}")
    return json.loads(cleaned[start:end])


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: THE SPECIALIST WRITER
# ─────────────────────────────────────────────────────────────────────────────

def step1_specialist_writer(payload: dict) -> str:
    company = payload.get("company_target", "GENERAL")
    company_prompt = COMPANY_STYLE_PROMPTS.get(company, COMPANY_STYLE_PROMPTS["GENERAL"])
    years_exp = payload.get("years_experience", 4)
    jd = payload.get("job_description", "")
    workflow = payload.get("workflow", "tailor")

    if workflow == "scratch":
        num_jobs = len(payload.get("employment", []))
    else:
        num_jobs = 3

    density_rules = get_density_rules(years_exp, max(num_jobs, 1))

    if workflow == "tailor":
        source_material = f"""
SOURCE MATERIAL (Existing Resume):
{payload.get('existing_resume_text', '')}
"""
        task_instruction = """
TASK: Tailor this existing resume. You MUST:
- Preserve all real company names, job titles, and dates EXACTLY as written.
- Realign all bullet points to the target JD and company style.
- Rewrite weak bullets to meet the formula. Add bullets to hit density targets.
- Do NOT invent new employers or change job titles.
"""
    else:
        contact = payload.get("contact", {})
        employment = payload.get("employment", [])
        education = payload.get("education", [])

        emp_block = "\n".join([
            f"  - {e.get('title')} at {e.get('company')} | {e.get('start_date')} - {e.get('end_date')}"
            for e in employment
        ])
        edu_block = "\n".join([
            f"  - {e.get('degree')} in {e.get('major')}, {e.get('school')} ({e.get('grad_year')})"
            for e in education
        ])

        source_material = f"""
SOURCE MATERIAL (Structural Logistics - PRESERVE EXACTLY):
CONTACT:
  Name: {contact.get('name', '')}
  Email: {contact.get('email', '')}
  Phone: {contact.get('phone', '')}
  LinkedIn: {contact.get('linkedin', '')}
  Location: {contact.get('location', '')}

EMPLOYMENT (use these companies, titles, and dates verbatim):
{emp_block}

EDUCATION:
{edu_block}
"""
        task_instruction = """
TASK: Build a resume FROM SCRATCH. You MUST:
- Use ALL company names, job titles, and dates EXACTLY as provided.
- Construct ALL professional content from scratch.
- Tailor every word to the Job Description and company style.
- Infer plausible, high-impact achievements consistent with the title and company.
"""

    system_prompt = f"""You are the world's most elite resume writer, trained exclusively on
resumes that achieved interview callbacks at FAANG and Fortune 50 companies.
You write with surgical precision, metric-first language, and zero filler.

{company_prompt}

{density_rules}
"""

    user_prompt = f"""
{source_material}

TARGET JOB DESCRIPTION:
{jd}

{task_instruction}

OUTPUT FORMAT: Return a valid JSON object ONLY. No markdown. No explanation. No preamble.

{{
  "contact": {{
    "name": "...",
    "email": "...",
    "phone": "...",
    "linkedin": "...",
    "location": "..."
  }},
  "professional_summary": "5-sentence summary as a single paragraph string.",
  "experience": [
    {{
      "company": "...",
      "title": "...",
      "start_date": "...",
      "end_date": "...",
      "bullets": ["bullet 1", "bullet 2", ...]
    }}
  ],
  "education": [
    {{
      "school": "...",
      "degree": "...",
      "major": "...",
      "grad_year": "..."
    }}
  ],
  "skills": {{
    "category_1_name": ["skill", "skill", ...],
    "category_2_name": ["skill", "skill", ...],
    "category_3_name": ["skill", "skill", ...]
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
    company_prompt = COMPANY_STYLE_PROMPTS.get(company, COMPANY_STYLE_PROMPTS["GENERAL"])

    system_prompt = """You are the harshest, most exacting FAANG resume critic alive.
You have personally reviewed 50,000+ resumes at Google, Amazon, and Meta.
You hate: vague language, weak verbs, AI-sounding filler, missing metrics,
and bullets that don't prove direct personal impact.

Your job: tear apart the draft below and rebuild it to perfection.
Return ONLY improved JSON. Same schema. No markdown. No explanation."""

    user_prompt = f"""
COMPANY TARGET: {company}
{company_prompt}

JOB DESCRIPTION:
{jd}

DRAFT RESUME JSON TO CRITIQUE AND UPGRADE:
{step1_output}

YOUR CRITIQUE CHECKLIST (fix ALL of these):

1. WEAK VERBS - Replace immediately:
   BAD: "Helped", "Assisted", "Supported", "Worked on", "Participated in",
        "Was responsible for", "Contributed to", "Involved in"
   GOOD: "Architected", "Engineered", "Spearheaded", "Accelerated", "Slashed",
         "Drove", "Launched", "Negotiated", "Scaled", "Orchestrated", "Pioneered"

2. AI FILLER PHRASES - Delete on sight:
   "Leveraged synergies", "Demonstrated expertise in", "Utilized best practices",
   "Passionate about", "Results-driven", "Detail-oriented", "Team player",
   "Proven track record", "Dynamic professional", "Seeking to"

3. MISSING METRICS - Every bullet needs a number. If a bullet has none, add one.

4. JD KEYWORD GAPS - If a required skill in the JD is missing from the resume,
   inject it naturally into the most relevant bullet or skills section.

5. SUMMARY QUALITY - Must NOT start with "I". Must NOT use filler phrases above.

6. DENSITY CHECK - If any job is below the minimum bullet count, add new bullets.

Return the corrected, perfected JSON. Same schema as input. No markdown fences.
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

    system_prompt = """You are an elite ATS compliance officer and proofreader
with deep knowledge of Applicant Tracking Systems (Greenhouse, Workday, Lever, Taleo).
Your job is the final quality gate before a resume is sent to a recruiter.
Return ONLY clean JSON. Same schema. No markdown."""

    user_prompt = f"""
PAGE TARGET: {page_target} pages

RESUME JSON FROM PREVIOUS STEP:
{step2_output}

FINAL QUALITY CHECKLIST:

1. GRAMMAR & SPELLING - Correct all errors. Tense consistency:
   - Current job: present tense ("Leads", "Manages", "Drives")
   - Past jobs: past tense ("Led", "Managed", "Drove")

2. WORD REPETITION - No action verb may appear more than twice across the entire resume.

3. ATS SAFETY RULES:
   - No special characters: no arrows, stars, checkmarks (these break parsers)
   - Use plain ASCII hyphens only
   - Spell out all acronyms at first use: "Machine Learning (ML)"

4. BULLET LENGTH CONTROL:
   - Each bullet: 1-2 lines at 10pt font, roughly 100 characters max
   - Split any bullet that exceeds this into two bullets
   - No bullet under 60 characters

5. SUMMARY: Must be exactly 5 sentences. Roughly 75-85 words total.

6. SKILLS DEDUPLICATION: Each skill category should have 6-8 items.

7. DENSITY VERIFICATION:
   - If page_target is 3 and total word count is under 1,400 — expand bullets
   - If page_target is 2 and total word count is under 900 — expand bullets

Return the final, flawless JSON object. This is the production output.
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
          f"Years: {payload.get('years_experience')}")

    # ── STEP 1: Specialist Writer ─────────────────────────────────────────
    print("[PIPELINE] Step 1: Specialist Writer...")
    s1_output = step1_specialist_writer(payload)
    print(f"[PIPELINE] Step 1 complete. Output: {len(s1_output)} chars")

    # ── STEP 2: FAANG Critic ─────────────────────────────────────────────
    print("[PIPELINE] Step 2: FAANG Critic...")
    try:
        s2_output = step2_faang_critic(s1_output, payload)
        # Validate Step 2 returned parseable JSON before proceeding
        extract_json(s2_output)
        print(f"[PIPELINE] Step 2 complete. Output: {len(s2_output)} chars")
    except Exception as e:
        print(f"[PIPELINE] Step 2 failed ({e}). Falling back to Step 1 output.")
        s2_output = s1_output

    # ── STEP 3: ATS Guard ────────────────────────────────────────────────
    print("[PIPELINE] Step 3: ATS Guard & Proofreader...")
    try:
        final_data = step3_ats_guard(s2_output, payload)
        print("[PIPELINE] Step 3 complete. Final JSON parsed successfully.")
    except Exception as e:
        print(f"[PIPELINE] Step 3 failed ({e}). Falling back to Step 2 output.")
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
        }
    }
