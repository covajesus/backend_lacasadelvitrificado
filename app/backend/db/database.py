from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URI = (
    "mysql+pymysql://admin:Admin2020!@31.97.250.169:3306/lacasadelvitrificado"
)

_POOL_KWARGS = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
    "pool_timeout": 30,
    "echo": False,
}

# Pool para peticiones HTTP (FastAPI).
engine = create_engine(
    SQLALCHEMY_DATABASE_URI,
    pool_size=20,
    max_overflow=30,
    **_POOL_KWARGS,
)

# Pool separado para hilos en background (envío de campañas, etc.).
# Evita que tareas largas agoten el pool de la API.
background_engine = create_engine(
    SQLALCHEMY_DATABASE_URI,
    pool_size=5,
    max_overflow=5,
    **_POOL_KWARGS,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

BackgroundSessionLocal = sessionmaker(
    bind=background_engine,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


@contextmanager
def background_session():
    """Sesión de corta duración para trabajo en background."""
    db = BackgroundSessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


