"""Weather data collecting REST server"""

import asyncio
import logging
import os
from datetime import datetime

import httpx
import pymongo
from dotenv import load_dotenv
from quart import Quart
from quart import Response

from cities import cities_ids

# start Quart
app = Quart(__name__)

class WeatherServer:
    """Class responsible for requesting and storing weather data"""

    def __init__(self):
        # MongoDB config
        db_client = pymongo.MongoClient(os.getenv('MONGODB_URL'))
        db = db_client['weatherDatabase']
        self.db_col = db['cityTempRequests']

        # load .env
        load_dotenv()

        # logging config
        logging.basicConfig(level=logging.INFO)

        # AsyncIO setup
        self.event_loop = asyncio.new_event_loop()

        # HTTPX config
        self.httpx_client = httpx.AsyncClient(timeout=None)

        # list of cities to collect data from
        self.cities_ids = cities_ids

# Instantiate WeatherServer
server = WeatherServer()

def kelvin_to_celsius(kelvin: float) -> int:
    """Convert kelvin to celsius"""
    return kelvin - 273.15

async def collect_from_api(uid: int, api_url: str):
    """Requests data from OpenWeatherAPI and stores the result in MongoDB"""

    # get current timestamp
    timestamp = datetime.now()

    # retrieve data from OpenWeatherMap for the given city
    response = await server.httpx_client.get(api_url)

    # handle errors
    try:
        response = response.raise_for_status()
    except httpx.HTTPError as e:
        logging.exception(f'API call to OpenWeatherMap returned error {e}.')
        return

    # parse data from response
    try:
        json_data = response.json()
        city_id = json_data['id']
        temperature = kelvin_to_celsius(json_data['main']['temp'])
        humidity = json_data['main']['humidity']
        city_data = {
            'city_id': city_id,
            'temperature': temperature,
            'humidity': humidity}
    except KeyError as e:
        # log error if the API returns data in a unexpected format
        logging.exception(f'Got unexpectedly formatted data from OpenWeatherMap {e}.')
        return

    # find relevant request in the database
    document = server.db_col.find_one({'uid': uid})

    # if it doesn't exist, this is the first response
    if not document:
        # create and insert document in database
        new_document = {
            'uid': uid,
            'timestamp': timestamp,
            'numRequestedCities': len(server.cities_ids),
            'cities': [city_data]}
        server.db_col.insert_one(new_document)
    # if it exists, just append this data to the cities list
    else:
        server.db_col.update_one({'_id': document['_id']}, {
                                 '$push': {'cities': city_data}})

    # log success
    logging.info(
        f'Updated database document {uid} with data from city {city_id}')


@app.route('/collect/<int:uid>', methods=['POST'])
async def collect(uid: int) -> Response:
    """Create asynchronous tasks to collect weather data"""

    # get document
    if server.db_col.find_one({'uid': uid}):
        return {'error': 'ID already exists in database, ignoring request.'}, 409

    # asynchronously retrieve data from OpenWeatherMap for each city in our list
    for city_id in server.cities_ids:
        api_token = os.getenv('OPEN_WEATHER_API_KEY')
        api_url = f'https://api.openweathermap.org/data/2.5/weather?id={city_id}&appid={api_token}'
        app.add_background_task(collect_from_api, uid, api_url)

    # 202 means "accepted request, but haven't yet completed it"
    return {}, 202


@app.route('/progress/<int:uid>')
def get_progress(uid: int) -> Response:
    """Returns the % of weather data collected for a previous request"""

    # get document
    doc = server.db_col.find_one({'uid': uid})

    # if not found, return 404
    if not doc:
        logging.exception(f'No record with id {uid} found in database.')
        return {'error': f'No record with id {uid} found in database.'}, 404

    # if found, return % of progress
    try:
        progress = 100 * len(doc['cities']) / doc['numRequestedCities']
    except KeyError as e:
        # handle corrupted document in database, return internal error
        logging.exception(f'Missing expected field {e} in document.')
        return {'error': 'Internal Error'}, 500

    return {'progress': progress}, 200

@app.route('/result/<int:uid>')
def get_weather_data(uid: int) -> Response:
    """Returns the weather data collected for a previous request"""

    # get document
    doc = server.db_col.find_one({'uid': uid})

    # if not found, return 404
    if not doc:
        logging.exception(f'No record with id {uid} found in database.')
        return {'error': f'No record with id {uid} found in database.'}, 404

    # if found, return % of progress
    if not doc['cities']:
        # handle corrupted document in database, return internal error
        logging.exception(f'Missing expected field \'cities\' in document.')
        return {'error': 'Internal Error'}, 500

    return {'cities': doc['cities']}, 200
