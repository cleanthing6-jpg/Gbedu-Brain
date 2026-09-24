import json, os, pathlib, sys
sys.path.insert(0, "src")
from gbedu_brain.matching import analyze, produce_matched_beat

vocal = sys.argv[1]
worker = sys.argv[2] if len(sys.argv) > 2 else os.environ["GBEDU_WORKER"]
spec = analyze(vocal)
print("VOCAL SPEC:", spec, flush=True)
audio, report = produce_matched_beat(spec, worker, genre=os.environ.get("GBEDU_GENRE", "afrobeats"))
out = pathlib.Path("matched_beat.wav"); out.write_bytes(audio)
print(json.dumps(report, indent=2))
print("SAVED:", out, out.stat().st_size, "bytes")
