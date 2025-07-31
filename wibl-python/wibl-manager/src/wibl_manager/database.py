from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session, Session
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from fastapi import Depends
import os

Base = declarative_base()

MANAGER_DATABASE_URI = os.environ.get('MANAGER_DATABASE_URI',
                                      "postgresql+psycopg://postgres:postgres@managerDB:5432/postgres")

engine = create_async_engine(MANAGER_DATABASE_URI, plugins=['geoalchemy2'])
SessionLocal = async_sessionmaker(expire_on_commit=False, class_=AsyncSession, bind=engine)

# This function is called by Alembic when sosos
def get_db_url():
    return f"postgresql+psycopg://{os.environ['DATABASE_USER']}:{os.environ['DATABASE_PASSWORD']}@" \
               f"{os.environ['DATABASE_HOST']}:{os.environ['DATABASE_PORT']}/" \
               f"{os.environ['DATABASE_NAME']}"


async def get_async_db() -> AsyncSession:
    async with SessionLocal() as session:
        yield session

