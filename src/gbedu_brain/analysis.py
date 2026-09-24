"""Layer 2: Real audio analysis via Essentia.
Returns static BPM + dynamic tempo map (ticks) for ACE-Step cover mode.
"""
import numpy as np


def analyze_vocal(path: str) -> dict:
    import essentia.standard as es

    # BeatTrackerMultiFeature REQUIRES 44100 Hz
    audio = es.MonoLoader(filename=path, sampleRate=44100)()

    ticks, confidence = es.BeatTrackerMultiFeature(
        maxTempo=208, minTempo=40,
    )(audio)

    ticks = ticks.tolist()

    if confidence < 1.0 or len(ticks) < 4:
        # Fallback: static grid
        bpm, beats, bconf, _, _ = es.RhythmExtractor2013(method="multifeature")(audio)
        return {
            "bpm": float(bpm),
            "key": "C", "scale": "minor", "key_strength": 0.0,
            "duration": float(len(audio)) / 44100.0,
            "energy": 0.0,
            "pitch_contour": [],
            "ticks": None,
            "beat_confidence": float(confidence),
        }

    intervals = np.diff(ticks)
    local_bpm = 60.0 / intervals

    key, scale, key_strength = es.KeyExtractor()(audio)

    rms = float((audio ** 2).mean()) ** 0.5
    import math
    db = 20.0 * math.log10(rms) if rms > 0 else -80.0
    energy = max(0.0, min(1.0, (db + 60.0) / 60.0))

    return {
        "bpm": float(np.mean(local_bpm)),
        "key": str(key),
        "scale": str(scale),
        "key_strength": float(key_strength),
        "duration": float(len(audio)) / 44100.0,
        "energy": energy,
        "pitch_contour": [],
        "ticks": ticks,
        "local_bpm": local_bpm.tolist(),
        "beat_confidence": float(confidence),
    }
