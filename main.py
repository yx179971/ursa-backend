from typing import List

import uvicorn
from fastapi import FastAPI, UploadFile, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from services import JobService
import models
import schemas
from conf import engine
from utils.exception import UrsaException

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    # allow_origin_regex="http://192.168.31.*",
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(UrsaException)
async def unicorn_exception_handler(request: Request, exc: UrsaException):
    return JSONResponse(
        status_code=417,
        content={"code": exc.code, "detail": exc.detail},
    )


@app.get("/jobs", response_model=List[schemas.Job])
def jobs_get():
    return JobService.get_jobs()


@app.get("/job/{job_id}", response_model=schemas.Job)
def job_get(job_id: int):
    job = JobService.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="User not found")
    return job


@app.post("/job")
def job_create(job: schemas.JobCreate):
    return JobService.create_job(job)


@app.put("/job")
def job_update(job: schemas.Job):
    return JobService.update_job(job)


@app.delete("/job/{job_id}")
def job_delete(job_id: int):
    JobService.delete_job(job_id)
    return {"success": True}


@app.post("/job/run")
def job_run():
    return {"success": True}


@app.post("/job/stop")
def job_stop():
    return {"success": True}


@app.post("/uploadfile")
async def upload_file(file: UploadFile):
    file_path = JobService.save_file(file)
    return {"file_path": file_path}


@app.post("/worker/keepalive")
def worker_keepalive():
    return {"success": True}


if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0")
