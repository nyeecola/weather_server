# syntax=docker/dockerfile:1
FROM python:3.12-slim-bullseye
WORKDIR /weather-docker
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
COPY . .
CMD ["python", "-m", "quart", "--app", "weather_server", "run", "--host", "0.0.0.0"]
