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

    # Loudness / energy (EBU R128 integrated loudness as a proxy)
    loudness = es.LoudnessEBUR128(sampleRate=44100)(audio)
    lufs = float(loudness[1]) if loudness else -70.0
    # map [-40, 0] LUFS to [0, 1] energy
    energy = max(0.0, min(1.0, (lufs + 40.0) / 40.0))

    return {
        "bpm": float(bpm),
        "key": str(key),
        "scale": str(scale),
        "key_strength": float(key_strength),
        "duration": float(len(audio)) / 44100.0,
        "energy": energy,
        "pitch_contour": [],
    }
