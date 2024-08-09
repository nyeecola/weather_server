# WeatherServer
A REST server that accepts requests to collect weather data from multiple cities using OpenWeatherMap's API.

## Tools

- Quart 0.19.6
	- A web framework very similar to Flask, but more suited to asynchronous jobs since it makes heavy use of Python's `asyncio`.
- MongoDB
	- A document-oriented NoSQL database.
	- I chose to use this instead of something more lightweight like SQLite since the project requires a lot of JSON manipulation, so it would be easier to implement and have a superior performance.
- Docker
	- A container management software.
	- We use it primarily to facilitate deployment and reproducibility.
- PyTest
	- A python testing framework.
	- Facilitates writing and running tests for our application.

## Configuration & Usage

1) This project uses two docker containers, one for the Quart webserver and one for MongoDB.
To ensure they can talk to eachother, create a shared docker network with the following command:
```
 docker network create mongodb
```

2) Edit the .env file in the project directory, adding your OpenWeatherMap API token.
It should look something like this:
```
MONGODB_URL = 'mongodb://mongodb:27017/'
OPEN_WEATHER_API_KEY = 'abcdefghijklmnopqrstuv012345'
```

3) Then, either download the webserver container or build it with:
```
 cd <project_path>
 docker build --tag weather_server .
```

4) Finally, run this script to deploy both MongoDB and the webserver:
```
 bash run.sh
```

5) That's it! If everything goes well, you should see both containers running when you run the following:
```
 docker ps
```
6) To make requests to the webserver, you can use curl, like this:
```
 curl -X POST 0.0.0.0:5000/collect/300
 curl -X GET 0.0.0.0:5000/progress/300
 curl -X GET 0.0.0.0:5000/result/300
```

## Running the tests
This project uses PyTest for UnitTesting.
You can run the tests with:
```
 cd <project_path>
 python -m pytest . -v
```

