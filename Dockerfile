# Use a Python 3.12 Alpine base image
ARG REBUILD=1
FROM python:3.12-alpine

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install dependencies required for compiling Python packages
RUN apk add --no-cache --virtual .build-deps gcc musl-dev python3-dev libffi-dev openssl-dev \
    && apk add --no-cache jpeg-dev zlib-dev libjpeg

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements.txt file into the container
COPY requirements.txt /app/

# Install the Python dependencies
RUN pip install --upgrade pip \
    && pip install -r requirements.txt \
    && pip install gunicorn \
    && apk del .build-deps

# Copy the rest of the application into the container
COPY ./src .

# Copy the gunicorn configuration file
COPY gunicorn.conf.py /app/gunicorn.conf.py

# Expose the port Flask/Gunicorn is accessible on
EXPOSE 5000

# Set the default command to run the Flask app via Gunicorn
CMD ["gunicorn", "--config", "gunicorn.conf.py", "app:app"]
