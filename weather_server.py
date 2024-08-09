from datetime import datetime
from dotenv import load_dotenv
from quart import Quart
from quart import request
from quart.testing.client import QuartClient

import asyncio
import httpx
import json
import logging
import os
import pymongo
import time

from cities import cities_ids

# Start Quart
app = Quart(__name__)

class WeatherServer:
   def __init__(self):
      # MongoDB config
      db_client = pymongo.MongoClient(os.getenv('MONGODB_URL'))
      db = db_client['weatherDatabase']
      self.db_col = db['cityTempRequests']

      # Load .env
      load_dotenv()

      # Logging config
      logging.basicConfig(level=logging.INFO)

      # AsyncIO setup
      self.event_loop = asyncio.new_event_loop()

      # HTTPX config
      self.httpx_client = httpx.AsyncClient()

      # List of cities to collect data from
      self.cities_ids = cities_ids

# Instantiate WeatherServer
server = WeatherServer()

def kelvin_to_celsius(kelvin: float):
   return kelvin - 273.15

async def collect_from_api(uid: int, api_url: str):
   timestamp = datetime.now()

   #async with httpx.AsyncClient() as client:
   response = await server.httpx_client.get(api_url)

   try:
      response = response.raise_for_status()
   except httpx.HTTPError as e:
      logging.exception(f'API call to OpenWeatherMap returned error {e}.')      
      return 

   json_data = response.json()
   city_id = json_data['id']
   temperature = kelvin_to_celsius(json_data['main']['temp'])
   humidity = json_data['main']['humidity']
   city_data = {'city_id': city_id, 'temperature': temperature, 'humidity': humidity}

   document = server.db_col.find_one({'uid': uid})
   if not document:
      new_document = {'uid': uid, 'timestamp': timestamp, 'numRequestedCities': 2, 'cities': [city_data]}
      server.db_col.insert_one(new_document)
   else:
      server.db_col.update_one({'_id': document['_id']}, {'$push': {'cities': city_data}})

   logging.info(f'Updated database document {uid} with data from city {city_id}')

@app.route('/collect/<int:uid>', methods=['POST'])
async def collect(uid: int):
   if server.db_col.find_one({'uid': uid}):
      return {'error': 'ID already exists in database, ignoring request.'}, 409

   for city_id in server.cities_ids:
      api_token = os.getenv('OPEN_WEATHER_API_KEY')
      api_url = f'https://api.openweathermap.org/data/2.5/weather?id={city_id}&appid={api_token}'
      app.add_background_task(collect_from_api, uid, api_url)

   return {}, 202
   
@app.route('/progress/<int:uid>')
def get_progress(uid: int):
   doc = server.db_col.find_one({'uid': uid})
   if not doc:
      return {'error': f'No record with id {uid} found in database.'}, 404

   try:
      progress = 100 * len(doc['cities']) / doc['numRequestedCities']
   except KeyError as e:
      logging.exception(f'Missing expected field {e} in document.')      
      return {'error': f'Internal Error'}, 500

   return {'progress': progress}, 200



