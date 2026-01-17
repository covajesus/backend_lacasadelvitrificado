from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URI = (
    "mysql+pymysql://admin:Admin2020!@31.97.250.169:3306/lacasadelvitrificado"
)

engine = create_engine(
    SQLALCHEMY_DATABASE_URI,
    pool_pre_ping=True,    # 🔥 EVITA conexiones muertas
    pool_recycle=300,      # 🔥 menor que wait_timeout
    pool_size=20,          # suficiente para FastAPI
    max_overflow=30,       # picos de tráfico
    pool_timeout=30,
    echo=False
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


