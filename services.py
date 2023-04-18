import os
import uuid
import shutil
import json

from fastapi import UploadFile

import models
import schemas
import conf
from conf import db
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
        return db.query(models.Job).all()

    @classmethod
    def get_job(cls, job_id):
        return db.query(models.Job).filter(models.Job.id == job_id).first()

    @classmethod
    def _job_maker(cls, job):
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
        job = cls._job_maker(job)
        db.bulk_update_mappings(models.Job, job)
        db.commit()
        db.refresh()
        return cls.get_job(job.id)

    @classmethod
    def delete_job(cls, job_id):
        db.delete(cls.get_job(job_id))
