"""
=============================================================================
ELITE RESUME BUILDER — FLASK API SERVER
=============================================================================
"""
from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from resume_pipeline import run_pipeline
from resume_docx_renderer import render_resume_docx
import traceback
import json
import re
import uuid
import threading
import io
from datetime import datetime

resume_store = {}

app = Flask(__name__, static_folder="templates")
CORS(app)


def deep_clean_raw(raw: str) -> str:
    """
    Aggressively cleans raw request body BEFORE JSON parsing.
    Handles all special characters that break JSON parsing.
    """
    # Replace smart/curly quotes with straight quotes
    raw = raw.replace('\u2018', "'").replace('\u2019', "'")
    raw = raw.replace('\u201c', '"').replace('\u201d', '"')

    # Replace bullet characters with hyphens
    raw = raw.replace('\u2022', '-').replace('\u2023', '-')
    raw = raw.replace('\u25cf', '-').replace('\u25e6', '-')
    raw = raw.replace('\u2043', '-').replace('\u204c', '-')

    # Replace em dash and en dash with hyphen
    raw = raw.replace('\u2014', '-').replace('\u2013', '-')

    # Replace non-breaking spaces
    raw = raw.replace('\u00a0', ' ')

    # Replace ellipsis
    raw = raw.replace('\u2026', '...')

    # Replace other common special chars
    raw = raw.replace('\u00b7', '-')  # middle dot
    raw = raw.replace('\u2192', '->') # arrow
    raw = raw.replace('\u2714', '')   # checkmark
    raw = raw.replace('\u2713', '')   # checkmark
    raw = raw.replace('\u2717', '')   # cross
    raw = raw.replace('\u2605', '')   # star
    raw = raw.replace('\u00ae', '')   # registered trademark
    raw = raw.replace('\u2122', '')   # trademark

    # Remove ALL control characters except newline, tab, carriage return
    raw = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', ' ', raw)

    # Normalize multiple spaces (but preserve newlines)
    raw = re.sub(r'[ \t]+', ' ', raw)

    return raw


def fix_broken_lines(text: str) -> str:
    """
    Joins lines that were broken mid-sentence in copy-pasted resume text.
    A line break inside a sentence (not starting a new bullet/section)
    gets joined with a space instead of treated as a new bullet.
    """
    if not text:
        return text

    lines = text.split('\n')
    result = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            result.append('')
            i += 1
            continue

        # Keep joining next line if current line doesn't end with
        # sentence-ending punctuation and next line doesn't start
        # a new bullet or section header
        while i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            if not next_line:
                break
            # Next line starts a new bullet or section = stop joining
            if next_line[0] in ('-', '*', '#', '\u2022') or \
               next_line.isupper() or \
               (len(next_line) > 2 and next_line[0].isupper() and
                    next_line.endswith(':')):
                break
            # Current line ends with punctuation = stop joining
            if line and line[-1] in ('.', '!', '?', ':'):
                break
            # Join the lines
            line = line + ' ' + next_line
            i += 1

        result.append(line)
        i += 1

    return '\n'.join(result)


def sanitize_payload(payload):
    """Recursively sanitize all string values after JSON parsing."""
    if isinstance(payload, dict):
        result = {}
        for k, v in payload.items():
            if k in ('existing_resume_text', 'job_description') and \
               isinstance(v, str):
                result[k] = fix_broken_lines(v.strip())
            else:
                result[k] = sanitize_payload(v)
        return result
    elif isinstance(payload, list):
        return [sanitize_payload(item) for item in payload]
    elif isinstance(payload, str):
        return payload.strip()
    return payload


def reconstruct_scratch_payload(payload):
    """
    Bubble sends flat parameters for scratch workflow (legacy), or a
    pre-built employment array with multiple job slots (current).
    Reconstruct/clean nested contact/employment/education structure.
    """
    contact = {
        "name": payload.get("contact_name", ""),
        "email": payload.get("contact_email", ""),
        "phone": payload.get("contact_phone", ""),
        "linkedin": payload.get("contact_linkedin", ""),
        "location": payload.get("contact_location", "")
    }

    # PRIMARY SOURCE: employment_json - a JSON string from the dynamic
    # "Add job" HTML form (via Toolbox JavaScript-to-Bubble), containing
    # an array of job objects with unlimited entries. Takes precedence
    # over the older structured-array and flat-field formats below.
    employment_json = payload.get("employment_json", "")
    employment_from_json = None
    if employment_json and isinstance(employment_json, str):
        try:
            parsed = json.loads(employment_json)
            if isinstance(parsed, list):
                employment_from_json = parsed
        except (json.JSONDecodeError, ValueError):
            employment_from_json = None

    # If Bubble already sent a structured employment array, clean it:
    # drop any job entries that are entirely empty (e.g. unused Job 2-4
    # slots the user left blank).
    employment = employment_from_json if employment_from_json is not None \
        else payload.get("employment", [])
    if isinstance(employment, list) and employment:
        cleaned_employment = []
        for job in employment:
            if not isinstance(job, dict):
                continue
            company = str(job.get("company", "")).strip()
            title = str(job.get("title", "")).strip()
            if not company and not title:
                continue  # empty/unused job slot - skip it
            cleaned_employment.append({
                "company": company,
                "title": title,
                "location": str(job.get("location", "")).strip(),
                "start_date": str(job.get("start_date", "")).strip(),
                "end_date": str(job.get("end_date", "") or "Present").strip()
            })
        employment = cleaned_employment
    else:
        employment = []

    # Legacy fallback: flat fields for a single job (no structured array)
    if not employment and (payload.get("company_name") or payload.get("job_title")):
        employment.append({
            "company": payload.get("company_name", ""),
            "title": payload.get("job_title", ""),
            "location": payload.get("job_location", ""),
            "start_date": payload.get("start_date", ""),
            "end_date": payload.get("end_date", "Present")
        })

    education = []
    if payload.get("school") or payload.get("degree"):
        education.append({
            "school": payload.get("school", ""),
            "degree": payload.get("degree", ""),
            "major": payload.get("major", ""),
            "grad_year": payload.get("grad_year", "")
        })

    if "contact" not in payload or not payload["contact"]:
        payload["contact"] = contact

    # Always use our cleaned employment array (handles both structured
    # input from Bubble and legacy flat-field fallback)
    payload["employment"] = employment

    if "education" not in payload or not payload["education"]:
        payload["education"] = education

    return payload


def parse_and_prepare_payload(raw_data: str) -> dict:
    """
    Shared payload preparation logic: cleaning, sanitizing,
    type conversion, and workflow reconstruction.
    Raises json.JSONDecodeError or ValueError on bad input.
    """
    # Deep clean BEFORE JSON parsing — this is critical
    raw_data = deep_clean_raw(raw_data)

    # Parse JSON
    try:
        payload = json.loads(raw_data)
    except json.JSONDecodeError:
        # If still failing, try a more aggressive clean
        raw_data = raw_data.encode('ascii', errors='ignore').decode('ascii')
        payload = json.loads(raw_data)

    # Sanitize all string values after parsing
    payload = sanitize_payload(payload)

    # Convert years_experience to int safely
    if "years_experience" in payload:
        try:
            payload["years_experience"] = int(
                float(str(payload["years_experience"]))
            )
        except (ValueError, TypeError):
            payload["years_experience"] = 4

    # Convert include_projects to bool
    if "include_projects" in payload:
        val = payload["include_projects"]
        if isinstance(val, str):
            payload["include_projects"] = val.lower() in (
                "true", "1", "yes"
            )
        elif not isinstance(val, bool):
            payload["include_projects"] = bool(val)

    # Auto-detect workflow if missing
    if "workflow" not in payload or not payload["workflow"]:
        if payload.get("existing_resume_text", "").strip():
            payload["workflow"] = "tailor"
        else:
            payload["workflow"] = "scratch"

    # For scratch workflow, reconstruct nested structures
    if payload.get("workflow") == "scratch":
        payload = reconstruct_scratch_payload(payload)

    # Validate required fields
    required_fields = ["company_target", "years_experience",
                       "job_description"]
    for field in required_fields:
        if field not in payload:
            raise ValueError(f"Missing required field: '{field}'")

    return payload


def run_pipeline_in_background(job_id: str, payload: dict):
    """
    Runs the full 3-step pipeline in a background thread and
    stores the result (or error) in resume_store under job_id.
    """
    try:
        result = run_pipeline(payload)
        resume_store[job_id] = {
            "status": "done",
            "html": result.get("html", ""),
            "resume_data": result.get("resume_data", {}),
            "page_target": result.get("page_target", 2),
            "company_target": result.get("company_target", "GENERAL"),
            "score": result.get("score", {}),
            "debug": result.get("debug", {})
        }
        print(f"[ASYNC] Job {job_id} completed successfully.")
    except Exception as e:
        traceback.print_exc()
        resume_store[job_id] = {
            "status": "error",
            "error": str(e)
        }
        print(f"[ASYNC] Job {job_id} failed: {e}")


def check_usage_limits(payload: dict) -> dict:
    """
    Checks the user's subscription status and usage limits.

    Returns a dict:
      {"allowed": True, "updated_counts": {...}}  - request can proceed
      {"allowed": False, "error": "..."}          - request blocked

    "updated_counts" contains the new values for trial_resumes_used,
    resumes_generated_today, and last_generation_date that Bubble
    should save back to the User record after a successful generation.
    """
    TRIAL_LIMIT = 3
    DAILY_LIMIT = 30

    subscription_status = str(payload.get("subscription_status", "trial")).strip().lower()

    try:
        trial_resumes_used = int(float(str(payload.get("trial_resumes_used", 0) or 0)))
    except (ValueError, TypeError):
        trial_resumes_used = 0

    try:
        resumes_generated_today = int(float(str(payload.get("resumes_generated_today", 0) or 0)))
    except (ValueError, TypeError):
        resumes_generated_today = 0

    last_generation_date = str(payload.get("last_generation_date", "") or "").strip()
    today_str = datetime.now().strftime("%Y-%m-%d")

    if subscription_status == "trial":
        if trial_resumes_used >= TRIAL_LIMIT:
            return {
                "allowed": False,
                "error": (
                    f"You've used all {TRIAL_LIMIT} free trial resumes. "
                    f"Subscribe to continue generating tailored resumes."
                )
            }
        return {
            "allowed": True,
            "updated_counts": {
                "trial_resumes_used": trial_resumes_used + 1,
                "resumes_generated_today": resumes_generated_today,
                "last_generation_date": last_generation_date or today_str
            }
        }

    elif subscription_status == "active":
        # Reset daily count if last generation was on a different day
        if last_generation_date != today_str:
            resumes_generated_today = 0

        if resumes_generated_today >= DAILY_LIMIT:
            return {
                "allowed": False,
                "error": (
                    f"You've reached your daily limit of {DAILY_LIMIT} resumes. "
                    f"Your limit resets tomorrow."
                )
            }

        return {
            "allowed": True,
            "updated_counts": {
                "trial_resumes_used": trial_resumes_used,
                "resumes_generated_today": resumes_generated_today + 1,
                "last_generation_date": today_str
            }
        }

    else:
        # expired or unknown status
        return {
            "allowed": False,
            "error": (
                "Your subscription has expired or is inactive. "
                "Please subscribe to continue."
            )
        }


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "Elite Resume Builder API"})


@app.route("/generate-resume", methods=["POST"])
def generate_resume():
    """
    LEGACY SYNCHRONOUS ENDPOINT — kept for backward compatibility.
    Runs the full pipeline and waits for completion before responding.
    Prefer /start-resume for new integrations to avoid timeouts.
    """
    try:
        raw_data = request.get_data(as_text=True)
        payload = parse_and_prepare_payload(raw_data)

        result = run_pipeline(payload)

        resume_id = str(uuid.uuid4())[:8]
        resume_store[resume_id] = {
            "status": "done",
            "html": result.get("html", ""),
            "resume_data": result.get("resume_data", {}),
            "page_target": result.get("page_target", 2),
            "company_target": result.get("company_target", "GENERAL"),
            "score": result.get("score", {}),
            "debug": result.get("debug", {})
        }
        result["resume_id"] = resume_id

        return jsonify(result), 200

    except json.JSONDecodeError as e:
        return jsonify({
            "success": False,
            "error": f"Could not parse request. Please avoid special "
                     f"characters in your resume or job description: {str(e)}"
        }), 400

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/start-resume", methods=["POST"])
def start_resume():
    """
    ASYNC ENDPOINT — returns immediately with a job_id.
    The pipeline runs in a background thread.
    Poll /check-status?id=<job_id> for progress and final result.
    """
    try:
        raw_data = request.get_data(as_text=True)
        payload = parse_and_prepare_payload(raw_data)

        # Check trial/subscription usage limits before starting the pipeline
        # Return HTTP 200 (not 403) so Bubble's API Connector doesn't show
        # its default error popup - we handle success:false via "Only when"
        # conditions in the Bubble workflow instead.
        limit_check = check_usage_limits(payload)
        if not limit_check["allowed"]:
            return jsonify({
                "success": False,
                "error": limit_check["error"],
                "limit_reached": True
            }), 200

        job_id = str(uuid.uuid4())[:8]
        resume_store[job_id] = {"status": "pending"}

        thread = threading.Thread(
            target=run_pipeline_in_background,
            args=(job_id, payload),
            daemon=True
        )
        thread.start()

        print(f"[ASYNC] Job {job_id} started in background.")

        return jsonify({
            "success": True,
            "resume_id": job_id,
            "status": "pending",
            "updated_counts": limit_check["updated_counts"]
        }), 202

    except json.JSONDecodeError as e:
        return jsonify({
            "success": False,
            "error": f"Could not parse request. Please avoid special "
                     f"characters in your resume or job description: {str(e)}"
        }), 400

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/check-status", methods=["GET"])
def check_status():
    """
    Poll this endpoint with ?id=<job_id> to check pipeline progress.
    Returns status: pending | done | error
    """
    job_id = request.args.get("id", "")
    entry = resume_store.get(job_id)

    if entry is None:
        return jsonify({
            "success": False,
            "status": "not_found",
            "error": "Resume ID not found or expired."
        }), 404

    status = entry.get("status", "pending")

    if status == "pending":
        return jsonify({"success": True, "status": "pending"}), 200

    elif status == "error":
        return jsonify({
            "success": False,
            "status": "error",
            "error": entry.get("error", "Unknown error")
        }), 200

    else:  # done
        return jsonify({
            "success": True,
            "status": "done",
            "html": entry.get("html", ""),
            "resume_data": entry.get("resume_data", {}),
            "page_target": entry.get("page_target", 2),
            "company_target": entry.get("company_target", "GENERAL"),
            "score": entry.get("score", {})
        }), 200


@app.route("/get-resume", methods=["GET"])
def get_resume():
    """Legacy endpoint - returns html once ready, or pending status."""
    resume_id = request.args.get("id", "")
    entry = resume_store.get(resume_id)

    if entry is None:
        return jsonify({
            "success": True,
            "html": "<p>Resume not found or expired.</p>"
        }), 200

    status = entry.get("status", "pending")
    if status == "done":
        return jsonify({"success": True, "html": entry.get("html", "")}), 200
    elif status == "error":
        return jsonify({
            "success": True,
            "html": f"<p>Resume generation failed: "
                    f"{entry.get('error', 'Unknown error')}</p>"
        }), 200
    else:
        return jsonify({
            "success": True,
            "html": "<p>Your resume is still generating. Please wait...</p>",
            "pending": True
        }), 200


@app.route("/download-docx", methods=["GET"])
def download_docx():
    """
    Returns the resume as a downloadable .docx file.
    Usage: /download-docx?id=<resume_id>
    """
    resume_id = request.args.get("id", "")
    entry = resume_store.get(resume_id)

    if entry is None or entry.get("status") != "done":
        return jsonify({
            "success": False,
            "error": "Resume not found, expired, or not yet ready."
        }), 404

    resume_data = entry.get("resume_data", {})

    try:
        docx_bytes = render_resume_docx(resume_data)
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"Could not generate Word document: {str(e)}"
        }), 500

    # Build a clean filename from the candidate's name
    name = resume_data.get("contact", {}).get("name", "Resume")
    safe_name = re.sub(r'[^A-Za-z0-9 _-]', '', name).strip().replace(' ', '_')
    filename = f"{safe_name or 'Resume'}_Resume.docx"

    return send_file(
        io.BytesIO(docx_bytes),
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        as_attachment=True,
        download_name=filename
    )


@app.route("/resume", methods=["GET"])
def show_resume():
    return send_from_directory("templates", "results.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
