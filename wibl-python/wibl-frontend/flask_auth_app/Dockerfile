# Set base image (host OS)
FROM python:3.12-alpine AS builder

# Set the working directory in the container
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Copy the dependencies file to the working directory
COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

# Install any dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

RUN apt-get update -y
RUN apt-get install -y curl

# Copy the content of the local src directory to the working directory
COPY . /app

FROM builder as final

# By default, listen on port 5000
EXPOSE 5000/tcp

# Specify the command to run on container start
CMD [ "python", "project/main.py" ]
