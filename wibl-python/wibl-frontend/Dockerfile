FROM python:3.14.10-slim as builder

WORKDIR /var/local/wibl/frontend
ADD ./src /var/local/wibl/frontend

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install curl so that our healthcheck works under Docker
RUN apt-get update && apt-get install -y curl

COPY requirements.txt ./
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

FROM builder as final
