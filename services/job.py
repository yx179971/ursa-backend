from collections import Counter
import hashlib
import os
import shutil
import time
import uuid

import conf
from conf import db
from conf import logger
from fastapi import UploadFile
import models
from mq import tasks
from mq.mq_utils import activate_window
import pyautogui as gui
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
    def get_windows(cls):
        return [x.title for x in gui.getAllWindows() if x.title]

    @classmethod
    def get_jobs(cls):
        return db.query(models.Job).order_by(models.Job.sort, models.Job.id).all()

    @classmethod
    def sort_jobs(cls, data):
        db.execute(
            update(models.Job),
            [{"id": job.id, "sort": sort} for sort, job in enumerate(data, start=1)],
        )
        db.commit()

    @classmethod
    def get_job(cls, job_id):
        return db.query(models.Job).filter(models.Job.id == job_id).first()

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
    def get_job_sig(cls, job):
        map_list = []
        for item in job.config.get("cells"):
            if item["shape"] == "edge":
                map_list.append((item["source"]["cell"], item["target"]["cell"]))
        map_list.sort(key=lambda x: x[1])
        map_list.sort(key=lambda x: x[0])
        return hashlib.md5(str(map_list).encode("utf-8")).hexdigest()

    @classmethod
    def update_job(cls, job: schemas.Job):
        map_sig = cls.get_job_sig(job)
        db.execute(
            update(models.Job)
            .where(models.Job.id == job.id)
            .values(config=job.config, name=job.name, map_signature=map_sig)
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
    def run(cls, job_id, force=False, node_id=""):
        cls.init_mq(force)
        tasks.send_job_run(job_id, node_id)

    @classmethod
    def stop(cls, job_id):
        redis_utils.set_mq("signal", models.MqSignal.stopping.name)

    @classmethod
    def pause(cls, job_id):
        redis_utils.set_mq("signal", models.MqSignal.pause.name)

    @classmethod
    def continue_(cls, job_id):
        job = cls.get_job(job_id)
        window = job.config.get("window")
        if window:
            activate_window(window)
        redis_utils.set_mq("signal", models.MqSignal.running.name)

    @classmethod
    def record_start(cls, job_id, force=False):
        job = cls.get_job(job_id)
        if not job.config.get("window"):
            raise UrsaException("请先配置目标窗口")
        cls.init_mq(force)
        tasks.send_record_start(job_id)

    @classmethod
    def record_stop(cls):
        redis_utils.set_mq("signal", models.MqSignal.stopping.name)
        for _ in range(60):
            if redis_utils.get_mq().status == models.MqStatus.finish:
                break
            time.sleep(1)

    @classmethod
    def stat(cls):
        stat = {}
        for job in db.query(models.Job).all():
            stat[job.name] = Counter(
                ["shape"] == "edge" for d in job.config.get("cells", [])
            )[False]
        for k, v in stat.items():
            logger.info(f"{k}: {v}")
