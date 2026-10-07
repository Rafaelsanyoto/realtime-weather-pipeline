import os
import requests

API_URL = "http://api.weatherstack.com/current"


def get_cities():
    cities = os.getenv("WEATHER_CITIES", "Jakarta,Singapore,Tokyo")
    return [city.strip() for city in cities.split(",") if city.strip()]


def fetch_data(city):
    api_key = os.getenv("WEATHERSTACK_API_KEY")

    if not api_key:
        raise RuntimeError("WEATHERSTACK_API_KEY is not set")

    try:
        response = requests.get(
            API_URL,
            params={
                "access_key": api_key,
                "query": city
            },
            timeout=30
        )

        response.raise_for_status()
        data = response.json()

        if "current" not in data or "location" not in data:
            raise RuntimeError(f"Invalid Weatherstack response for {city}: {data}")

        print(f"Weather data received for {city}")

        return data

    except requests.exceptions.RequestException as e:
        print(f"API request failed for {city}: {e}")
        raise