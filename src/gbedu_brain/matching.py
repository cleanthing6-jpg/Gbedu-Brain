"""Gbedu matching engine - vocal in, beat that fits it out.

Loop: analyze vocal -> ask worker -> measure the beat -> accept | re-ask -> tiny warp.
"""
from __future__ import annotations
import io, os, tempfile, time
import requests

NOTES = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
ENH = {"DB":"C#","EB":"D#","GB":"F#","AB":"G#","BB":"A#","CB":"B","FB":"E","E#":"F","B#":"C"}
MAJ = [6.35,2.23,3.48,2.33,4.38,4.09,2.52,5.19,2.39,3.66,2.29,2.88]
MIN = [6.33,2.68,3.52,5.38,2.60,3.53,2.54,4.75,3.98,2.69,3.34,3.17]

BPM_TOL     = 2.0    # accepted BPM gap after octave folding
MAX_TRIES   = 3      # worker calls before we keep the closest
MAX_STRETCH = 0.03   # only warp if within 3%
MAX_SHIFT   = 1      # only warp if within 1 semitone

def norm_key(k):
    k = (k or "").strip().upper().replace("#", "#").replace("b", "b")
    return ENH.get(k, k)

def fold_bpm(bpm):
    while bpm and bpm > 150: bpm /= 2
    while bpm and bpm < 70:  bpm *= 2
    return bpm

def fold_ratio(r):
    if not r or r <= 0: return 1.0
    while r < 0.7: r *= 2
    while r > 1.4: r /= 2
    return r

def note_steps(target, got):
    if target not in NOTES or got not in NOTES: return 0
    return ((NOTES.index(target) - NOTES.index(got) + 6) % 12) - 6

def bpm_gap(target_bpm, beat_bpm):
    if not beat_bpm: return 99.0
    return abs(target_bpm - beat_bpm * fold_ratio(target_bpm / beat_bpm))

def analyze(path, use_essentia=True):
    """-> {'bpm','key','scale','confidence','source'}"""
    if use_essentia:
        try:
            import essentia.standard as es
            a = es.MonoLoader(filename=path, sampleRate=44100)()
            bpm, _, _, _, _ = es.RhythmExtractor2013(method="multifeature")(a)
            k, scale, strength = es.KeyExtractor()(a)
            return {"bpm": round(fold_bpm(float(bpm)), 2), "key": norm_key(str(k)),
                    "scale": str(scale).strip().lower(),
                    "confidence": round(float(strength), 3), "source": "essentia"}
        except Exception as e:
            print("essentia unavailable:", type(e).__name__, str(e)[:120], flush=True)

    import numpy as np, librosa
    y, sr = librosa.load(path, sr=22050, mono=True)
    y, _ = librosa.effects.trim(y, top_db=35)

    votes = []
    try:
        from beat_this.inference import File2Beats
        beats, _ = File2Beats(checkpoint_path="final0", device="cuda", dbn=False)(path)
        d = np.diff(np.asarray(beats)); d = d[d > 0.15]
        if len(d) >= 4: votes.append(float(60.0/np.median(d)))
    except Exception as e:
        print("beat_this skipped:", type(e).__name__, str(e)[:100], flush=True)
    env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=512)
    try: votes.append(float(np.median(librosa.feature.tempo(onset_envelope=env, sr=sr, aggregate=None))))
    except Exception: pass
    try: votes.append(float(np.atleast_1d(librosa.beat.beat_track(onset_envelope=env, sr=sr)[0])[0]))
    except Exception: pass
    votes = [v for v in votes if 30 < v < 250]
    bpm = fold_bpm(float(np.median(votes))) if votes else 0.0

    def corr(p, q):
        p, q = np.asarray(p,float)-np.mean(p), np.asarray(q,float)-np.mean(q)
        return float(np.dot(p,q)/((np.linalg.norm(p)*np.linalg.norm(q))+1e-9))

    chroma = librosa.feature.chroma_cens(y=y, sr=sr).mean(axis=1)
    pc = chroma
    try:
        f0, _, vp = librosa.pyin(y, fmin=librosa.note_to_hz('E2'), fmax=librosa.note_to_hz('C6'), sr=sr)
        ok = ~np.isnan(f0)
        if ok.sum() > 20:
            h = np.zeros(12)
            for m, p in zip(np.round(librosa.hz_to_midi(f0[ok])).astype(int), np.nan_to_num(vp[ok], nan=0.0)):
                h[m % 12] += max(float(p), 0.05)
            if h.sum() > 1e-6: pc = h / h.sum()
    except Exception as e:
        print("pyin skipped:", type(e).__name__, flush=True)

    ranked = sorted(((0.5*corr(chroma, np.roll(prof, i)) + 0.5*corr(pc, np.roll(prof, i)), NOTES[i], mode)
                     for i in range(12)
                     for mode, prof in (("major", MAJ), ("minor", MIN))), reverse=True)
    return {"bpm": round(bpm, 2), "key": ranked[0][1], "scale": ranked[0][2],
            "confidence": round(float(ranked[0][0]), 3), "source": "librosa/beat_this"}

def analyze_bytes(data):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(data); p = f.name
    try: return analyze(p)
    finally:
        try: os.unlink(p)
        except OSError: pass

def distance(spec, beat):
    return (bpm_gap(spec["bpm"], beat.get("bpm", 0)) / BPM_TOL
            + 2.0 * abs(note_steps(spec["key"], beat.get("key", "C")))
            + (0.0 if spec.get("scale") == beat.get("scale") else 3.0))

def fits(spec, beat):
    return (bpm_gap(spec["bpm"], beat.get("bpm", 0)) <= BPM_TOL
            and note_steps(spec["key"], beat.get("key", "C")) == 0
            and spec.get("scale") == beat.get("scale"))

def build_prompt(spec, genre="afrobeats"):
    mood = "dark minor chords" if spec.get("scale") == "minor" else "bright major chords"
    return (f"professional nigerian {genre} instrumental, no vocals, log drum, shaker, "
            f"talking drum, warm sub bass, clean guitar, groovy, punchy kick, "
            f"{spec['key']} {spec['scale']}, {int(round(spec['bpm']))} bpm, {mood}")

def ask_worker(worker_url, spec, genre="afrobeats", seeds=None, worker_key=None, timeout=900):
    payload = {"key": spec["key"], "scale": spec["scale"], "bpm": spec["bpm"],
               "genre": genre, "prompt": build_prompt(spec, genre)}
    if seeds: payload["seeds"] = seeds
    headers = {"X-Gbedu-Key": worker_key} if worker_key else {}
    r = requests.post(worker_url.rstrip("/") + "/generate", json=payload,
                      headers=headers, timeout=timeout)
    r.raise_for_status()
    return r.content, dict(r.headers)

def produce_matched_beat(spec, worker_url, genre="afrobeats", worker_key=None,
                         max_tries=MAX_TRIES, log=print):
    pool = [42, 7, 99, 1234, 21, 555]
    best = None
    tries = 0
    for i in range(max_tries):
        seeds = pool[i*2:i*2+2] or [int(time.time()) % 9999]
        tries = i + 1
        log(f"[match] try {tries}/{max_tries} seeds={seeds}")
        try:
            audio, _ = ask_worker(worker_url, spec, genre, seeds, worker_key)
        except Exception as e:
            log(f"[match] worker error: {type(e).__name__} {str(e)[:200]}"); continue
        beat = analyze_bytes(audio)
        d = distance(spec, beat)
        log(f"[match] beat={beat} distance={round(d,3)} fits={fits(spec, beat)}")
        c = {"audio": audio, "beat": beat, "distance": d, "seeds": seeds}
        if best is None or d < best["distance"]: best = c
        if fits(spec, beat): break

    if best is None:
        raise RuntimeError("worker produced no usable beat")
    return _finish(best, spec, tries, log)

def _finish(cand, spec, tries, log):
    try:
        import librosa, soundfile as sf
    except ImportError:
        log('[match] librosa not on this host - returning beat unwarped')
        return cand['audio'], {'target': spec, 'beat_measured': cand['beat'],
                               'tries': tries, 'distance': round(cand['distance'], 3),
                               'warped': 'skipped (no librosa here)',
                               'matched': fits(spec, cand['beat'])}
    audio, beat = cand["audio"], cand["beat"]
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(audio); src = f.name

    y, sr = librosa.load(src, sr=44100, mono=True)
    r = fold_ratio(spec["bpm"] / beat["bpm"]) if beat.get("bpm") else 1.0
    stretched = False
    if 0.005 < abs(r - 1.0) <= MAX_STRETCH:
        log(f"[match] stretch x{round(r,4)}")
        y = librosa.effects.time_stretch(y, rate=r); stretched = True
    steps = note_steps(spec["key"], beat.get("key", "C"))
    shifted = False
    if steps and abs(steps) <= MAX_SHIFT:
        log(f"[match] pitch_shift {steps} semitone")
        y = librosa.effects.pitch_shift(y, sr=sr, n_steps=steps); shifted = True

    out = io.BytesIO()
    sf.write(out, y, sr, format="WAV")
    try: os.unlink(src)
    except OSError: pass

    report = {"target": spec, "beat_measured": beat, "seeds": cand["seeds"],
              "distance": round(cand["distance"], 3), "tries": tries,
              "stretched": stretched, "shifted": shifted,
              "matched": fits(spec, beat)}
    return out.getvalue(), report


def _norm_spec(d):
    key = norm_key(str(d.get("key") or d.get("tonic") or "C"))
    scale = str(d.get("scale") or d.get("mode") or "minor").strip().lower()
    bpm = fold_bpm(float(d.get("bpm") or d.get("tempo") or 0))
    return {"bpm": round(bpm, 2), "key": key, "scale": scale,
            "confidence": d.get("confidence") or d.get("strength"),
            "source": "remote", "raw": d}


def analyze_remote(path, base_url):
    """Ask the deployed brain (Essentia) to analyse a file - no local deps needed."""
    last = None
    for ep, field in (("/debug/analyze", "file"), ("/debug/analyze", "audio"),
                      ("/debug/analyze", "vocal"), ("/v1/analyze", "file")):
        try:
            with open(path, "rb") as f:
                r = requests.post(base_url.rstrip("/") + ep, files={field: f}, timeout=180)
            if r.status_code in (404, 405):
                continue
            r.raise_for_status()
            return _norm_spec(r.json())
        except Exception as e:
            last = f"{ep} field={field}: {type(e).__name__} {str(e)[:120]}"
    raise RuntimeError("remote analysis failed -> " + str(last))
