#!/bin/bash
docker run --name mongodb -p 27017:27017 -d --network mongodb mongodb/mongodb-community-server:latest &
docker container run -p 5000:5000 -d -v $(pwd)/.env:/weather-docker/.env --network mongodb --name weather-container weather_server &
wait -n

