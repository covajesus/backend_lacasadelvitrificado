from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

#SQLALCHEMY_DATABASE_URI = "mysql+pymysql://root:@localhost:3306/berger"

SQLALCHEMY_DATABASE_URI = "mysql+pymysql://admin:Admin2020!@31.97.250.169:3306/lacasadelvitrificado"

engine = create_engine(
    SQLALCHEMY_DATABASE_URI,
    pool_size=200,           # más conexiones simultáneas
    max_overflow=200,        # conexiones extra si se saturan las 200
    pool_timeout=60,        # segundos que espera antes de dar timeout
    pool_recycle=3600,      # reciclar conexiones cada hora
    echo=False
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


