"""
=============================================================================
ELITE RESUME BUILDER — FLASK API SERVER
=============================================================================
This is the web server that sits between Bubble (your no-code frontend)
and the Python pipeline. Bubble sends a POST request here, this server
runs the 3-step pipeline, and returns JSON back to Bubble.

SETUP:
  pip install flask flask-cors anthropic
  export ANTHROPIC_API_KEY="sk-ant-..."
  python server.py

DEPLOY:
  Railway.app or Render.com — see PHASE 1 blueprint for deployment steps.
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
        required_fields = ["workflow", "company_target", "years_experience", "job_description"]
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
