import uuid
import time


class JobStore:
    def __init__(self):
        self._jobs = {}

    def create(self) -> str:
        job_id = str(uuid.uuid4())
        self._jobs[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "progress": 0.0,
            "result": None,
            "error": None,
            "created_at": time.time(),
        }
        return job_id

    def get(self, job_id: str):
        return self._jobs.get(job_id)

    def update(self, job_id: str, **kwargs):
        job = self._jobs.get(job_id)
        if job:
            job.update(kwargs)

    def complete(self, job_id: str, result: dict):
        self.update(job_id, status="succeeded", progress=1.0, result=result)

    def fail(self, job_id: str, error: str):
        self.update(job_id, status="failed", error=error)


job_store = JobStore()
