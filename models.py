from conf import Base
from sqlalchemy import Column
from sqlalchemy import Float
from sqlalchemy import Integer
from sqlalchemy import JSON
from sqlalchemy import String


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    config = Column(JSON, default=dict)


class Node(Base):
    __abstract__ = True
    id = Column(String)
    name = Column(String)
    img_url = Column(String)
    accuracy = Column(Float)
    position = Column(JSON)
    interval = Column(Integer)
    action = Column(String)


class Edge(Base):
    __abstract__ = True
    id = Column(String)
    source = Column(String)
    target = Column(String)
