FROM python:3.12-slim-bookworm
ENV PYTHONUNBUFFERED=1
WORKDIR /var/local/wibl/frontend
COPY requirements.txt ./
RUN pip install -r requirements.txt
