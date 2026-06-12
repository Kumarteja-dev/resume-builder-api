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

from flask import Flask, request, jsonify
from flask_cors import CORS
from resume_pipeline import run_pipeline
import traceback

app = Flask(__name__)
CORS(app)  # Allows Bubble.io to call this API from the browser


@app.route("/health", methods=["GET"])
def health():
    """Quick health check — Bubble can ping this to confirm the server is alive."""
    return jsonify({"status": "ok", "service": "Elite Resume Builder API"})


@app.route("/generate-resume", methods=["POST"])
def generate_resume():
    """
    Main endpoint. Called by Bubble's API Connector plugin.

    Expects JSON body matching the payload schema in resume_pipeline.py.
    Returns the full pipeline result including resume_data JSON.
    """
    try:
        payload = request.get_json(force=True)

        # ── Basic validation ────────────────────────────────────────────
        required_fields = ["workflow", "company_target", "years_experience", "job_description"]
        for field in required_fields:
            if field not in payload:
                return jsonify({
                    "success": False,
                    "error": f"Missing required field: '{field}'"
                }), 400

        if payload["workflow"] not in ("tailor", "scratch"):
            return jsonify({
                "success": False,
                "error": "workflow must be 'tailor' or 'scratch'"
            }), 400

        if payload["workflow"] == "tailor" and not payload.get("existing_resume_text"):
            return jsonify({
                "success": False,
                "error": "existing_resume_text is required for workflow='tailor'"
            }), 400

        if payload["workflow"] == "scratch":
            for key in ["contact", "employment", "education"]:
                if not payload.get(key):
                    return jsonify({
                        "success": False,
                        "error": f"'{key}' is required for workflow='scratch'"
                    }), 400

        # ── Run the 3-step pipeline ──────────────────────────────────────
        result = run_pipeline(payload)
        return jsonify(result), 200

    except json.JSONDecodeError as e:
        return jsonify({
            "success": False,
            "error": f"Pipeline returned invalid JSON: {str(e)}"
        }), 500

    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/render-html", methods=["POST"])
def render_html():
    """
    Optional endpoint: takes the final resume_data JSON and renders
    the completed HTML/CSS template as a string.
    Bubble can iframe this or use it to generate a PDF via wkhtmltopdf.
    """
    from resume_renderer import render_resume_html

    try:
        body = request.get_json(force=True)
        resume_data = body.get("resume_data")
        page_target = body.get("page_target", 2)

        if not resume_data:
            return jsonify({"success": False, "error": "resume_data is required"}), 400

        html = render_resume_html(resume_data, page_target)
        return jsonify({"success": True, "html": html}), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


import json

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
