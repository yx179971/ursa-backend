import os

import conf
from conf import db
import models


class CleanService:
    @classmethod
    def clean_img(cls):
        img = set()
        to_delete = set()
        for job in db.query(models.Job).all():
            for node in job.config.get("cells"):
                data = node.get("data", {})
                img.add(data.get("locate"))
                img.add(data.get("target"))
                img.add(data.get("background"))
        for dirpath, dirnames, filenames in os.walk(conf.img_dir):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                filepath = os.path.relpath(filepath, conf.img_dir)
                if filepath not in img:
                    to_delete.add(filepath)
        for p in to_delete:
            os.remove(os.path.join(conf.img_dir, p))

    @classmethod
    def clean_job_log(cls):
        pass
