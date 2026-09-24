import requests
_WORKER = {"url": None}
def set_worker(url): _WORKER["url"] = url
def worker_url(): return _WORKER["url"]
def generate_ace(bpm, key, scale, genre="afrobeats", duration=30, timeout=600, src_audio_path=None):
    url = _WORKER["url"]
    if not url: raise RuntimeError("no GPU worker registered")
    payload = {"bpm":bpm,"key":key,"scale":scale,"genre":genre,"duration":duration}
    if src_audio_path: payload["src_audio_path"] = src_audio_path
    r = requests.post(url.rstrip("/")+"/generate", json=payload, timeout=timeout)
    r.raise_for_status()
    return r.content
