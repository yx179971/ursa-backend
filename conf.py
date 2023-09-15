import logging.config
import os
import sys
from typing import Any
from typing import Dict

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker

debug = True
mq_debug = False

front_exe = "Ursa-frontend.exe"

SINGLE_MODE = "single"
CLUSTER_MODE = "cluster"
mode = SINGLE_MODE

entry = sys.argv[0]
if entry.endswith("Ursa.exe"):
    base_dir = os.path.dirname(entry)
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))
img_dir = os.path.join(base_dir, "img")
os.makedirs(img_dir, exist_ok=True)
data_path = os.path.join(base_dir, "data.json")

REDIS_HOST = "127.0.0.1"
# REDIS_HOST = "192.168.31.112"
REDIS_PORT = 6379

accuracy = 0.8

SQLALCHEMY_DATABASE_URL = f"sqlite:///{base_dir}/sql_app.db"
# SQLALCHEMY_DATABASE_URL = "postgresql://user:password@postgresserver/db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db: Session = SessionLocal()

LOGGING_CONFIG: Dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "%(asctime)s - %(levelprefix)s %(message)s",
            "use_colors": None,
        },
        "access": {
            "()": "uvicorn.logging.AccessFormatter",
            "fmt": '%(asctime)s - %(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s',  # noqa: E501
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
        "access": {
            "formatter": "access",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "default",
            "filename": "ursa.log",
            "backupCount": 3,
        },
    },
    "loggers": {
        "uvicorn": {
            "handlers": ["default", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "uvicorn.error": {"level": "INFO", "handlers": ["default", "file"]},
        "uvicorn.access": {
            "handlers": ["access", "file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger("uvicorn")
