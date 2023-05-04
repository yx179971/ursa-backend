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
from services import JobService
from utils.exception import UrsaException
import uvicorn

models.Base.metadata.create_all(bind=engine)

app = FastAPI()
app.mount("/img", StaticFiles(directory="img"), name="img")


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
def jobs_get():
    return {"data": JobService.get_jobs()}


@app.get("/job/{job_id}", response_model=schemas.JobResponse)
def job_get(job_id: int):
    job = JobService.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="User not found")
    return {"data": job}


@app.post("/job", response_model=schemas.JobResponse)
async def job_create(job: schemas.JobCreate):
    return {"data": JobService.create_job(job)}


@app.put("/job/{job_id}", response_model=schemas.JobResponse)
def job_update(job: schemas.Job):
    return {"data": JobService.update_job(job)}


@app.delete("/job/{job_id}", response_model=schemas.SuccessResponse)
def job_delete(job_id: int):
    JobService.delete_job(job_id)
    return {"success": True}


@app.post("/job/run/{job_id}", response_model=schemas.SuccessResponse)
def job_run(job_id: int):
    JobService.run(job_id)
    return {"success": True}


@app.post("/job/stop")
def job_stop():
    return {"success": True}


@app.post("/uploadfile")
async def upload_file(file: UploadFile):
    file_path = JobService.save_file(file)
    return {"data": {"file_path": file_path}}


@app.post("/worker/keepalive")
def worker_keepalive():
    return {"success": True}


# app = log_request_body_middleware(app)
if __name__ == "__main__":
    conf.debug = True
    uvicorn.run(app, host="0.0.0.0")
