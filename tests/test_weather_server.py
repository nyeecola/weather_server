import json
import mongomock
import pytest

from pytest import approx
from weather_server import app
from weather_server import kelvin_to_celsius
from weather_server import server

# Pytest setup
pytest_plugins = ('pytest_asyncio',)

# Mock WeatherServer list of cities
server.cities_ids = []

# Setup testable Quart instance
client = app.test_client()


def test_kelvin_to_celsius():
    """Test conversion from kelvin to celsius"""
    assert kelvin_to_celsius(273.15) == approx(0)
    assert kelvin_to_celsius(303.15) == approx(30)
    assert kelvin_to_celsius(223.15) == approx(-50)
    assert kelvin_to_celsius(273) == approx(-0.15)


@pytest.mark.asyncio
async def test_get_progress_not_found():
    """Test failing to get progress from an inexistent request id"""
    server.db_col = mongomock.MongoClient().db.collection
    response = await client.get('/progress/555')
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_progress_internal_error():
    """Test failing to get progress from a corrupted db document"""
    server.db_col = mongomock.MongoClient().db.collection
    server.db_col.insert_one({'uid': 707})
    response = await client.get('/progress/707')
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_get_progress_success(httpx_mock):
    """Test getting the progress of a previous request"""
    server.db_col = mongomock.MongoClient().db.collection
    server.cities_ids = ['111', '234']
    httpx_mock.add_response(
        json={
            'id': 111,
            'main': {
                'temp': 90,
                'humidity': 50}})
    httpx_mock.add_response(
        json={
            'id': 234,
            'main': {
                'temp': 5.4,
                'humidity': 72.1}})

    response = await client.post('/collect/222')
    assert response.status_code == 202

    response = await client.get('/progress/222')
    assert response.status_code == 200
    json_data = json.loads(await response.data)
    assert json_data['progress'] == approx(100)


@pytest.mark.asyncio
async def test_collect_duplicated_id():
    """Test failing to collect data from a duplicated request id"""
    server.db_col = mongomock.MongoClient().db.collection
    server.db_col.insert_one({'uid': 101})
    response = await client.post('/collect/101')
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_collect_db_insert(httpx_mock):
    """Test if inserted weather data after a /collect/ POST request"""
    server.db_col = mongomock.MongoClient().db.collection
    server.cities_ids = ['133']
    httpx_mock.add_response(
        json={
            'id': 133,
            'main': {
                'temp': 90,
                'humidity': 50}})
    response = await client.post('/collect/133')
    assert response.status_code == 202
    assert server.db_col.find_one({'uid': 133})
