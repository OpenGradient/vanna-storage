# Use a Python 3.8 Alpine base image
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
    # Adding gunicorn to the installation
    && pip install gunicorn \
    # Remove temporary packages to reduce image size
    && apk del .build-deps

# Copy the rest of the application into the container
COPY ./src .

# Expose the port Flask/Gunicorn is accessible on
EXPOSE 5000

# Set the default command to run the Flask app via Gunicorn
CMD ["gunicorn", "--workers=3", "--bind=0.0.0.0:5000", "app:app"]