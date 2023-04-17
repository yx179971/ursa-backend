import uvicorn

from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from services import JobService

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    # allow_origin_regex="http://192.168.31.*",
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("job/{job_id}")
def job_get(job_id: int):
    return {}


@app.post("job/")
def job_create():
    return {}


@app.put("job/{job_id}")
def job_update(job_id: int):
    return {}


@app.delete("job/{job_id}")
def job_delete(job_id: int):
    return {}


@app.post("/job/run")
def job_run():
    return {"success": True}


@app.post("/job/stop")
def job_stop():
    return {"success": True}


@app.post("/uploadfile/")
async def upload_file(file: UploadFile):
    file_path = JobService.save_file(file)
    return {"file_path": file_path}


@app.post("/worker/keepalive")
def worker_keepalive():
    return {"success": True}


if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0")
