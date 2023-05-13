import os
import shutil
import time
import uuid

import conf
from conf import db
from fastapi import UploadFile
import models
from mq import tasks
import schemas
from sqlalchemy import update
from utils import redis_utils
from utils.exception import MqException
from utils.exception import UrsaException


class JobService:
    @classmethod
    def save_file(cls, file: UploadFile):
        file_name = f"{uuid.uuid4()}.png"
        des_path = os.path.join(conf.img_dir, file_name)
        with open(des_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        return file_name

    @classmethod
    def get_jobs(cls):
        return db.query(models.Job).order_by(models.Job.sort, models.Job.id).all()

    @classmethod
    def sort_jobs(cls, data):
        db.execute(
            update(models.Job),
            [{"id": job.id, "sort": sort} for sort, job in enumerate(data)],
        )
        db.commit()

    @classmethod
    def get_job(cls, job_id):
        return db.query(models.Job).filter(models.Job.id == job_id).first()

    @classmethod
    def _job_checker(cls, job):
        # todo
        return job

    @classmethod
    def create_job(cls, job: schemas.JobCreate):
        if db.query(models.Job).filter(models.Job.name == job.name).first():
            raise UrsaException("作业名称已存在")
        job = models.Job(name=job.name)
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    @classmethod
    def update_job(cls, job: schemas.Job):
        job = cls._job_checker(job)
        db.execute(
            update(models.Job)
            .where(models.Job.id == job.id)
            .values(config=job.config, name=job.name)
        )
        db.commit()
        return cls.get_job(job.id)

    @classmethod
    def delete_job(cls, job_id):
        db.delete(cls.get_job(job_id))
        db.commit()

    @classmethod
    def init_mq(cls, force=False):
        mq = redis_utils.get_mq()
        if mq.status == models.MqStatus.running:
            if not force:
                job = cls.get_job(mq.job_id)
                raise MqException(f"任务<{job.name}>正在运行/录制")
            else:
                redis_utils.set_mq("signal", models.MqSignal.stopping.name)
                for _ in range(60):
                    if redis_utils.get_mq().status == models.MqStatus.stopped:
                        break
                    time.sleep(1)
        redis_utils.set_mq("signal", models.MqSignal.running.name)
        redis_utils.set_mq("status", models.MqStatus.running.name)

    @classmethod
    def run(cls, job_id, force=False):
        cls.init_mq(force)
        tasks.job_run.delay(job_id)

    @classmethod
    def stop(cls, job_id):
        redis_utils.set_mq("signal", models.MqSignal.stopping.name)

    @classmethod
    def record_start(cls, job_id, force=False):
        cls.init_mq(force)
        tasks.record_start.delay(job_id)

    @classmethod
    def record_stop(cls):
        redis_utils.set_mq("signal", models.MqSignal.stopping.name)
        for _ in range(60):
            if redis_utils.get_mq().status == models.MqStatus.finish:
                break
            time.sleep(1)
