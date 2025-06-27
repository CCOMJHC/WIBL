from sqlalchemy.orm import declarative_base
import os
Base = declarative_base()


def get_db_url():
    return f"postgresql://{os.environ['DATABASE_USER']}:{os.environ['DATABASE_PASSWORD']}@" \
               f"{os.environ['DATABASE_HOST']}:{os.environ['DATABASE_PORT']}/" \
               f"{os.environ['DATABASE_NAME']}"
