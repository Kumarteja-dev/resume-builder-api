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


def sanitize_text(value):
    if not isinstance(value, str):
        return value
    value = value.replace('\u2018', "'").replace('\u2019', "'")
    value = value.replace('\u201c', '"').replace('\u201d', '"')
    value = value.replace('\u2022', '-').replace('\u2023', '-')
    value = value.replace('\u25cf', '-').replace('\u25e6', '-')
    value = value.replace('\u2014', '-').replace('\u2013', '-')
    value = value.replace('\u00a0', ' ')
    value = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', ' ', value)
    value = re.sub(r'  +', ' ', value)
    return value.strip()


def sanitize_payload(payload):
    if isinstance(payload, dict):
        return {k: sanitize_payload(v) for k, v in payload.items()}
    elif isinstance(payload, list):
        return [sanitize_payload(item) for item in payload]
    elif isinstance(payload, str):
        return sanitize_text(payload)
    return payload


def reconstruct_scratch_payload(payload):
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
        raw_data = request.get_data(as_text=True)
        raw_data = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', ' ', raw_data)

        payload = json.loads(raw_data)
        payload = sanitize_payload(payload)

        if "years_experience" in payload:
            try:
                payload["years_experience"] = int(float(str(payload["years_experience"])))
            except (ValueError, TypeError):
                payload["years_experience"] = 4

        if "workflow" not in payload or not payload["workflow"]:
            if payload.get("existing_resume_text", "").strip():
                payload["workflow"] = "tailor"
            else:
                payload["workflow"] = "scratch"

        if payload.get("workflow") == "scratch":
            payload = reconstruct_scratch_payload(payload)

        required_fields = ["company_target", "years_experience", "job_description"]
        for field in required_fields:
            if field not in payload:
                return jsonify({
                    "success": False,
                    "error": f"Missing required field: '{field}'"
                }), 400

        result = run_pipeline(payload)

        resume_id = str(uuid.uuid4())[:8]
        resume_store[resume_id] = result.get("html", "")
        result["resume_id"] = resume_id

        return jsonify(result), 200

    except json.JSONDecodeError as e:
        return jsonify({
            "success": False,
            "error": f"Invalid JSON in request: {str(e)}"
        }), 400

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/get-resume", methods=["GET"])
def get_resume():
    resume_id = request.args.get("id", "")
    html = resume_store.get(resume_id, "<p>Resume not found or expired</p>")
    return jsonify({"success": True, "html": html}), 200


@app.route("/resume", methods=["GET"])
def show_resume():
    return send_from_directory("templates", "results.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
