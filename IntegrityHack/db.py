# utils/db.py

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Boolean, Date, ForeignKey
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker


# ---------------------------
# Подключение к базе данных
# ---------------------------

# SQLite-файл. Он автоматически создастся в корне проекта.
DATABASE_URL = "sqlite:///integrity.db"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()


# ---------------------------
# Таблица Objects (объекты)
# ---------------------------

class Object(Base):
    __tablename__ = "objects"

    id = Column(Integer, primary_key=True)  # object_id
    object_name = Column(String, nullable=False)
    object_type = Column(String, nullable=False)
    pipeline = Column(String)               # MT-01 / MT-02 и т.п.
    lat = Column(Float)
    lon = Column(Float)
    year = Column(Integer)
    material = Column(String)

    inspections = relationship("Inspection", back_populates="object")


# ---------------------------
# Таблица Inspections (диагностики)
# ---------------------------

class Inspection(Base):
    __tablename__ = "inspections"

    id = Column(Integer, primary_key=True)  # diag_id
    object_id = Column(Integer, ForeignKey("objects.id"), nullable=False)
    date = Column(Date, nullable=False)
    method = Column(String, nullable=False)
    temperature = Column(Float)
    humidity = Column(Float)
    illumination = Column(Float)
    defect_found = Column(Boolean)
    defect_descr = Column(String)
    quality_grade = Column(String)
    param1 = Column(Float)
    param2 = Column(Float)
    param3 = Column(Float)
    ml_label = Column(String)  # normal / medium / high

    object = relationship("Object", back_populates="inspections")
    defects = relationship("Defect", back_populates="inspection")


# ---------------------------
# Таблица Defects (дефекты)
# ---------------------------

class Defect(Base):
    __tablename__ = "defects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    inspection_id = Column(Integer, ForeignKey("inspections.id"), nullable=False)

    depth = Column(Float)   # обычно param1
    length = Column(Float)  # param2
    width = Column(Float)   # param3
    severity = Column(String)     # normal / medium / high
    description = Column(String)  # описание дефекта

    inspection = relationship("Inspection", back_populates="defects")


# ---------------------------
# Создание таблиц
# ---------------------------

def init_db():
    """Создаёт все таблицы, если их нет."""
    Base.metadata.create_all(bind=engine)

