import threading
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from gbedu_brain.jobs import job_store
from gbedu_brain.mock_engine import run_mock_production


ROOT = Path(__file__).resolve().parents[2]
STORAGE = ROOT / "storage"
UPLOADS = STORAGE / "uploads"
BEATS = STORAGE / "beats"
UPLOADS.mkdir(parents=True, exist_ok=True)
BEATS.mkdir(parents=True, exist_ok=True)


app = Flask(__name__)
CORS(app)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "service": "gbedu-brain",
        "version": "0.1.0",
    })


@app.route("/v1/produce", methods=["POST"])
def produce():
    if "vocal" not in request.files:
        return jsonify({"error": "no vocal file provided"}), 400

    vocal = request.files["vocal"]
    genre = request.form.get("genre", "afrobeats")
    mood = request.form.get("mood", "auto")
    duration = request.form.get("duration", "180")

    job_id = job_store.create()
    safe_name = vocal.filename or "vocal.wav"
    upload_path = UPLOADS / (job_id + "_" + safe_name)
    vocal.save(str(upload_path))

    thread = threading.Thread(
        target=run_mock_production,
        args=(job_id, str(upload_path), genre, BEATS),
        daemon=True,
    )
    thread.start()

    return jsonify({
        "job_id": job_id,
        "status": "queued",
        "poll_url": "/v1/jobs/" + job_id,
    })


@app.route("/v1/jobs/<job_id>", methods=["GET"])
def job_status(job_id):
    job = job_store.get(job_id)
    if not job:
        return jsonify({"error": "job not found"}), 404
    return jsonify(job)


@app.route("/static/<path:filename>", methods=["GET"])
def static_files(filename):
    return send_from_directory(str(STORAGE), filename)


@app.route("/", methods=["GET"])
def root():
    return jsonify({
        "name": "GBEDU Brain Engine",
        "endpoints": [
            "POST /v1/produce",
            "GET  /v1/jobs/<job_id>",
            "GET  /health",
        ],
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
