import requests
_WORKER = {"url": None}
def set_worker(url): _WORKER["url"] = url
def worker_url(): return _WORKER["url"]
def generate_ace(bpm, key, scale, genre="afrobeats", duration=60, timeout=180):
    url = _WORKER["url"]
    if not url: raise RuntimeError("no GPU worker registered")
    r = requests.post(url.rstrip("/")+"/generate",
        json={"bpm":bpm,"key":key,"scale":scale,"genre":genre,"duration":duration}, timeout=timeout)
    r.raise_for_status()
    return r.content
