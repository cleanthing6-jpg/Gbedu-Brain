"""Layer 2: Real audio analysis via Essentia.

Returns the same dict shape as models.analysis_to_dict() so mock_engine
and any downstream layer can use it unchanged.
"""
from pathlib import Path


def analyze_vocal(path: str) -> dict:
    """Analyze a vocal file. WAV only — convert mp3/m4a upstream."""
    import essentia.standard as es

    audio = es.MonoLoader(filename=path, sampleRate=44100)()

    # Rhythm
    bpm, beats, bpm_conf, _, _ = es.RhythmExtractor2013(method="multifeature")(audio)

    # Key
    key, scale, key_strength = es.KeyExtractor()(audio)

    # Loudness / energy (RMS-based, mono-safe)
    rms = float((audio ** 2).mean()) ** 0.5
    db = 20.0 * (rms ** 0.5 if rms > 0 else 0.0) if False else 20.0 * __import__("math").log10(rms) if rms > 0 else -80.0
    # map [-60, 0] dBFS to [0, 1] energy
    energy = max(0.0, min(1.0, (db + 60.0) / 60.0))

    return {
        "bpm": float(bpm),
        "key": str(key),
        "scale": str(scale),
        "key_strength": float(key_strength),
        "duration": float(len(audio)) / 44100.0,
        "energy": energy,
        "pitch_contour": [],
    }
