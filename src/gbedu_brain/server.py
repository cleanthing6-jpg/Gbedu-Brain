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




@app.route("/debug/analyze", methods=["POST"])
def debug_analyze():
    import traceback
    f = request.files.get("vocal")
    if not f:
        return jsonify({"error": "no vocal"}), 400
    tmp = UPLOADS / ("dbg_" + (f.filename or "x.wav"))
    f.save(str(tmp))
    try:
        from gbedu_brain.analysis import analyze_vocal
        result = analyze_vocal(str(tmp))
        return jsonify({"ok": True, "result": result})
    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e),
            "type": type(e).__name__,
            "trace": traceback.format_exc()[-2000:],
        })


@app.route("/register-worker", methods=["POST"])
def register_worker():
    from gbedu_brain.ace_client import set_worker
    d = request.get_json() or {}
    u = (d.get("url") or "").rstrip("/")
    if not u.startswith("http"): return jsonify({"error":"bad url"}), 400
    set_worker(u)
    return jsonify({"ok": True, "url": u})

@app.route("/worker", methods=["GET"])
def get_worker():
    from gbedu_brain.ace_client import worker_url
    return jsonify({"url": worker_url()})



@app.route("/debug/fs", methods=["GET"])
def debug_fs():
    import os
    return jsonify({
        "storage": str(STORAGE),
        "beats": str(BEATS),
        "beats_files": sorted([x.name for x in BEATS.iterdir()]) if BEATS.exists() else None,
        "uploads_files": sorted([x.name for x in UPLOADS.iterdir()]) if UPLOADS.exists() else None,
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
