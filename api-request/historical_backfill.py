import os
import sys
import time
import requests
import psycopg2
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
HISTORICAL_URL = "https://archive-api.open-meteo.com/v1/archive"

WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snowfall",
    73: "Moderate snowfall",
    75: "Heavy snowfall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    97: "Heavy thunderstorm",
    99: "Thunderstorm with heavy hail"
}

def get_cities():
    cities = os.getenv("WEATHER_CITIES", "Jakarta,Singapore,Tokyo")
    return [city.strip() for city in cities.split(",") if city.strip()]

def connect_to_db():
    print("Connecting to PostgreSQL...")
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "db"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "db"),
        user=os.getenv("DB_USER", "db_user"),
        password=os.getenv("DB_PASSWORD", "db_password")
    )

def geocode_city(city):
    print(f"Finding coordinates for {city}...")

    for attempt in range(1, 4):
        try:
            response = requests.get(
                GEOCODING_URL,
                params={"name": city, "count": 1, "language": "en", "format": "json"},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            if not data.get("results"):
                raise RuntimeError(f"Could not find coordinates for {city}")

            location = data["results"][0]
            print(f"{city}: {location['latitude']}, {location['longitude']} ({location['timezone']})")
            return location

        except requests.exceptions.RequestException as e:
            print(f"Geocoding attempt {attempt}/3 failed for {city}: {e}")
            if attempt == 3:
                raise
            time.sleep(3)

def fetch_historical_weather(location, start_date, end_date):
    print(f"Downloading historical weather from {start_date} to {end_date}...")

    for attempt in range(1, 4):
        try:
            response = requests.get(
                HISTORICAL_URL,
                params={
                    "latitude": location["latitude"],
                    "longitude": location["longitude"],
                    "start_date": start_date,
                    "end_date": end_date,
                    "hourly": "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m,surface_pressure,precipitation",
                    "timezone": location["timezone"]
                },
                timeout=60
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"Historical API attempt {attempt}/3 failed: {e}")
            if attempt == 3:
                raise
            time.sleep(3)

def get_utc_offset(timestamp, timezone_name):
    dt = datetime.fromisoformat(timestamp)
    local_dt = dt.replace(tzinfo=ZoneInfo(timezone_name))
    offset = local_dt.utcoffset()
    return "0" if offset is None else str(offset.total_seconds() / 3600)

def insert_historical_data(conn, requested_city, location, data):
    hourly = data["hourly"]
    inserted_rows = 0
    skipped_rows = 0
    cursor = conn.cursor()

    for i, timestamp in enumerate(hourly["time"]):
        weather_code = hourly["weather_code"][i]
        description = WEATHER_CODES.get(weather_code, "Unknown")
        utc_offset = get_utc_offset(timestamp, location["timezone"])

        cursor.execute(
            """
            INSERT INTO dev.raw_weather_data (
                city, country, temperature, feelslike, humidity,
                weather_descriptions, wind_speed, pressure, precip,
                time, inserted_at, utc_offset
            )
            SELECT %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s
            WHERE NOT EXISTS (
                SELECT 1
                FROM dev.raw_weather_data
                WHERE city = %s AND time = %s
            )
            """,
            (
                requested_city,
                location.get("country"),
                hourly["temperature_2m"][i],
                hourly["apparent_temperature"][i],
                hourly["relative_humidity_2m"][i],
                description,
                hourly["wind_speed_10m"][i],
                hourly["surface_pressure"][i],
                hourly["precipitation"][i],
                timestamp,
                utc_offset,
                requested_city,
                timestamp
            )
        )

        if cursor.rowcount == 1:
            inserted_rows += 1
        else:
            skipped_rows += 1

    conn.commit()
    cursor.close()
    print(f"{requested_city}: {inserted_rows} inserted, {skipped_rows} already existed")

def main():
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    jakarta_today = datetime.now(ZoneInfo("Asia/Jakarta")).date()
    end_date = jakarta_today - timedelta(days=1)
    start_date = end_date - timedelta(days=days - 1)

    print(f"Backfilling {days} days: {start_date} → {end_date}")

    cities = get_cities()
    conn = None

    try:
        conn = connect_to_db()

        for city in cities:
            print(f"\n===== {city} =====")
            location = geocode_city(city)
            historical_data = fetch_historical_weather(location, start_date.isoformat(), end_date.isoformat())
            insert_historical_data(conn, city, location, historical_data)

        print("\nHistorical backfill completed!")

    finally:
        if conn:
            conn.close()
            print("Database connection closed")

if __name__ == "__main__":
    main()