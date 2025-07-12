from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

#SQLALCHEMY_DATABASE_URI = "mysql+pymysql://root:@localhost:3306/berger"

SQLALCHEMY_DATABASE_URI = "mysql+pymysql://root:@localhost:3306/lacasadelvitrificado"

engine = create_engine(SQLALCHEMY_DATABASE_URI, pool_size=20, max_overflow=0, echo=False)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

