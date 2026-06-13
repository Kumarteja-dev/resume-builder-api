"""
=============================================================================
ELITE RESUME BUILDER — FLASK API SERVER
=============================================================================
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from resume_pipeline import run_pipeline
import traceback
import json
import re
import uuid

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
    Bubble sends flat parameters for scratch workflow.
    Reconstruct nested contact/employment/education structure.
    """
    contact = {
        "name": payload.get("contact_name", ""),
        "email": payload.get("contact_email", ""),
        "phone": payload.get("contact_phone", ""),
        "linkedin": payload.get("contact_linkedin", ""),
        "location": payload.get("contact_location", "")
    }

    employment = []
    if payload.get("company_name") or payload.get("job_title"):
        employment.append({
            "company": payload.get("company_name", ""),
            "title": payload.get("job_title", ""),
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
    if "employment" not in payload or not payload["employment"]:
        payload["employment"] = employment
    if "education" not in payload or not payload["education"]:
        payload["education"] = education

    return payload


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "Elite Resume Builder API"})


@app.route("/generate-resume", methods=["POST"])
def generate_resume():
    try:
        # Get raw data
        raw_data = request.get_data(as_text=True)

        # Deep clean BEFORE JSON parsing — this is critical
        raw_data = deep_clean_raw(raw_data)

        # Parse JSON
        try:
            payload = json.loads(raw_data)
        except json.JSONDecodeError as e:
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
                return jsonify({
                    "success": False,
                    "error": f"Missing required field: '{field}'"
                }), 400

        # Run the pipeline
        result = run_pipeline(payload)

        # Store and return
        resume_id = str(uuid.uuid4())[:8]
        resume_store[resume_id] = result.get("html", "")
        result["resume_id"] = resume_id

        return jsonify(result), 200

    except json.JSONDecodeError as e:
        return jsonify({
            "success": False,
            "error": f"Could not parse request. Please avoid special "
                     f"characters in your resume or job description: {str(e)}"
        }), 400

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/get-resume", methods=["GET"])
def get_resume():
    resume_id = request.args.get("id", "")
    html = resume_store.get(
        resume_id, "<p>Resume not found or expired.</p>"
    )
    return jsonify({"success": True, "html": html}), 200


@app.route("/resume", methods=["GET"])
def show_resume():
    return send_from_directory("templates", "results.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
