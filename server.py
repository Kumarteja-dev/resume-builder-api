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

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "Elite Resume Builder API"})

@app.route("/generate-resume", methods=["POST"])
def generate_resume():
    try:
        raw_data = request.get_data(as_text=True)
        raw_data = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', ' ', raw_data)
        payload = json.loads(raw_data)

        # Convert years_experience to int (Bubble sends it as a string)
        if "years_experience" in payload:
            try:
                payload["years_experience"] = int(float(str(payload["years_experience"])))
            except (ValueError, TypeError):
                payload["years_experience"] = 4  # safe default

        # If workflow is missing, infer it from the payload
        if "workflow" not in payload:
            if "existing_resume_text" in payload and payload["existing_resume_text"]:
                payload["workflow"] = "tailor"
            else:
                payload["workflow"] = "scratch"

        required_fields = ["company_target", "years_experience", "job_description"]
        for field in required_fields:
            if field not in payload:
                return jsonify({"success": False, "error": f"Missing required field: '{field}'"}), 400

        result = run_pipeline(payload)
        resume_id = str(uuid.uuid4())[:8]
        resume_store[resume_id] = result.get("html", "")
        result["resume_id"] = resume_id

        return jsonify(result), 200

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
