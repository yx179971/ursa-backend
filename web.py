import json
import logging

import conf
from conf import engine
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Request
from fastapi import UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import models
import schemas
from services import CleanService
from services import JobService
from utils import redis_utils
from utils.exception import UrsaException
import uvicorn

models.Base.metadata.create_all(bind=engine)

app = FastAPI()
app.mount("/img", StaticFiles(directory=conf.img_dir), name="img")


def log_request_body_middleware(app):
    async def wrapped_app(scope, receive, send):
        await Request(scope, receive).body()
        await app(scope, receive, send)

    return wrapped_app


app.add_middleware(
    CORSMiddleware,
    # allow_origin_regex="http://192.168.31.*",
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# todo: 记录请求体，由于fastapi的request在不同scope中只能有一次读取body，所以会hang住
# @app.middleware("http")
# async def log_request_body(request: Request, call_next):
#     response = await call_next(request)
#     if conf.debug and request.method != "OPTIONS":
#         body = (await request.body())
#         # print(f"request body: {body}")
#     return response


@app.exception_handler(UrsaException)
async def unicorn_exception_handler(request: Request, exc: UrsaException):
    return JSONResponse(
        status_code=417,
        content={"code": exc.code, "detail": exc.detail},
    )


@app.get("/jobs", response_model=schemas.JobListResponse)
async def jobs_get():
    return {"data": JobService.get_jobs()}


@app.post("/jobs/sort", response_model=schemas.SuccessResponse)
async def jobs_sort(data: schemas.JobListRequest):
    JobService.sort_jobs(data.data)
    return {"success": True}


@app.get("/job/{job_id}", response_model=schemas.JobResponse)
async def job_get(job_id: int):
    job = JobService.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="User not found")
    return {"data": job}


@app.post("/job", response_model=schemas.JobResponse)
async def job_create(job: schemas.JobCreate):
    return {"data": JobService.create_job(job)}


@app.put("/job/{job_id}", response_model=schemas.JobResponse)
async def job_update(job: schemas.Job):
    return {"data": JobService.update_job(job)}


@app.delete("/job/{job_id}", response_model=schemas.SuccessResponse)
async def job_delete(job_id: int):
    JobService.delete_job(job_id)
    return {"success": True}


@app.post("/job/run/{job_id}", response_model=schemas.SuccessResponse)
async def job_run(job_id: int, body: schemas.JobRunRequest):
    JobService.run(job_id, body.force, body.node_id or "")
    return {"success": True}


@app.post("/job/pause/{job_id}", response_model=schemas.SuccessResponse)
async def job_pause(job_id: int):
    JobService.pause(job_id)
    return {"success": True}


@app.post("/job/continue/{job_id}", response_model=schemas.SuccessResponse)
async def job_continue(job_id: int):
    JobService.continue_(job_id)
    return {"success": True}


@app.post("/job/stop/{job_id}", response_model=schemas.SuccessResponse)
async def job_stop(job_id: int):
    JobService.stop(job_id)
    return {"success": True}


@app.get("/mq/status", response_model=schemas.MqResponse)
async def job_status():
    return {"data": redis_utils.get_mq()}


@app.post("/record/start/{job_id}", response_model=schemas.SuccessResponse)
async def record_start(job_id: int, force: bool = False):
    JobService.record_start(job_id, force)
    return {"success": True}


@app.post("/record/stop/{job_id}", response_model=schemas.SuccessResponse)
async def record_stop(job_id: int):
    JobService.record_stop()
    with open(conf.data_path) as f:
        data = json.load(f)
    return JSONResponse(data)


@app.post("/uploadfile")
async def upload_file(file: UploadFile):
    file_path = JobService.save_file(file)
    return {"data": {"file_path": file_path}}


@app.get("/windows")
async def get_windows():
    return {"data": {"windows": JobService.get_windows()}}


@app.post("/worker/keepalive")
async def worker_keepalive():
    return {"success": True}


# app = log_request_body_middleware(app)


def main():
    conf.debug = True
    # todo: 清除无用图片和JobLog
    CleanService.clean_img()
    JobService.stat()
    uvicorn.run(
        app, host="0.0.0.0", log_config=conf.LOGGING_CONFIG, log_level=logging.DEBUG
    )


if __name__ == "__main__":
    main()
