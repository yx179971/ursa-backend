import os
import uuid
import shutil

from fastapi import UploadFile

from conf import img_dir


class JobService:
    @classmethod
    def save_file(cls, file: UploadFile):
        file_name = f"{uuid.uuid4()}.png"
        des_path = os.path.join(img_dir, file_name)
        with open(des_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        return file_name
