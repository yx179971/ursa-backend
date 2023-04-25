from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, JSON
from sqlalchemy.orm import relationship

from conf import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    config = Column(JSON, default=dict)


class Node(Base):
    __abstract__ = True
    id = Column(String)
    img_url = Column(String)


class Edge(Base):
    __abstract__ = True
    id = Column(String)
