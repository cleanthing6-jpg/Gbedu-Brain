import time
import shutil
from pathlib import Path

from gbedu_brain.models import VocalAnalysis, SongSpec, analysis_to_dict, spec_to_dict
from gbedu_brain.jobs import job_store


def mock_analyze(vocal_path: str) -> VocalAnalysis:
    time.sleep(0.5)
    return VocalAnalysis(
        bpm=105.0,
        key="F",
        scale="minor",
        key_strength=0.82,
        duration=30.0,
        energy=0.74,
        pitch_contour=[],
    )


def mock_songspec(analysis: VocalAnalysis, genre: str) -> SongSpec:
    defaults = {
        "afrobeats": ["log_drum", "shaker", "conga", "rimshot", "guitar_skank"],
        "amapiano": ["log_drum", "shaker", "piano", "synth_bass", "rimshot"],
        "hip_hop": ["kick", "snare", "hi_hat", "808_bass", "piano"],
        "dancehall": ["kick", "snare", "hi_hat", "bass", "guitar_skank"],
    }
    mood = "energetic" if analysis.bpm > 110 else "groovy"
    return SongSpec(
        genre=genre,
        bpm=analysis.bpm,
        key=analysis.key,
        scale=analysis.scale,
        mood=mood,
        duration=max(analysis.duration * 2, 180),
        instruments=defaults.get(genre, defaults["afrobeats"]),
    )


def run_mock_production(job_id: str, vocal_path: str, genre: str, output_dir: Path):
    try:
        job_store.update(job_id, status="processing", progress=0.1)

        analysis = mock_analyze(vocal_path)
        job_store.update(job_id, progress=0.3)

        spec = mock_songspec(analysis, genre)
        job_store.update(job_id, progress=0.5)

        beat_path = Path(output_dir) / (job_id + ".wav")
        time.sleep(2.0)
        shutil.copy(vocal_path, str(beat_path))
        job_store.update(job_id, progress=0.9)

        job_store.complete(job_id, {
            "beat_url": "/static/beats/" + job_id + ".wav",
            "songspec": spec_to_dict(spec),
            "analysis": analysis_to_dict(analysis),
        })
    except Exception as e:
        job_store.fail(job_id, str(e))
