import os
import psycopg2
import time

from api_request import fetch_data, get_cities


def connect_to_db():
    print("Connecting to database...")

    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "db"),
            port=int(os.getenv("DB_PORT", "5432")),
            dbname=os.getenv("DB_NAME", "db"),
            user=os.getenv("DB_USER", "db_user"),
            password=os.getenv("DB_PASSWORD", "db_password")
        )

        print("Database connection successful")

        return conn

    except psycopg2.Error as e:
        print(f"Database connection failed: {e}")
        raise


def create_table(conn):
    print("Preparing weather table...")

    try:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE SCHEMA IF NOT EXISTS dev;

            CREATE TABLE IF NOT EXISTS dev.raw_weather_data (
                id SERIAL PRIMARY KEY,
                city TEXT,
                temperature FLOAT,
                weather_descriptions TEXT,
                wind_speed FLOAT,
                time TIMESTAMP,
                inserted_at TIMESTAMP DEFAULT NOW(),
                utc_offset TEXT
            );
        """)

        cursor.execute("""
            ALTER TABLE dev.raw_weather_data
            ADD COLUMN IF NOT EXISTS country TEXT;

            ALTER TABLE dev.raw_weather_data
            ADD COLUMN IF NOT EXISTS feelslike FLOAT;

            ALTER TABLE dev.raw_weather_data
            ADD COLUMN IF NOT EXISTS humidity FLOAT;

            ALTER TABLE dev.raw_weather_data
            ADD COLUMN IF NOT EXISTS pressure FLOAT;

            ALTER TABLE dev.raw_weather_data
            ADD COLUMN IF NOT EXISTS precip FLOAT;
        """)

        conn.commit()

        cursor.close()

        print("Weather table ready")

    except psycopg2.Error as e:
        conn.rollback()

        print(f"Failed preparing weather table: {e}")

        raise


def insert_record(conn, data):
    location = data["location"]
    weather = data["current"]

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO dev.raw_weather_data (
                city,
                country,
                temperature,
                feelslike,
                humidity,
                weather_descriptions,
                wind_speed,
                pressure,
                precip,
                time,
                inserted_at,
                utc_offset
            )
            VALUES (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                NOW(),
                %s
            )
            """,
            (
                location.get("name"),
                location.get("country"),
                weather.get("temperature"),
                weather.get("feelslike"),
                weather.get("humidity"),
                weather.get(
                    "weather_descriptions",
                    ["Unknown"]
                )[0],
                weather.get("wind_speed"),
                weather.get("pressure"),
                weather.get("precip"),
                location.get("localtime"),
                location.get("utc_offset")
            )
        )

        conn.commit()

        cursor.close()

        print(
            f"Inserted weather data for "
            f"{location.get('name')}"
        )

    except psycopg2.Error as e:
        conn.rollback()

        print(
            f"Failed inserting weather data for "
            f"{location.get('name')}: {e}"
        )

        raise


def main():
    conn = None

    failed_cities = []

    try:
        conn = connect_to_db()

        create_table(conn)

        cities = get_cities()

        print(
            f"Collecting weather for: "
            f"{', '.join(cities)}"
        )

        for city in cities:
            try:
                data = fetch_data(city)
                insert_record(conn, data)
                time.sleep(2)

            except Exception as e:
                print(f"Failed processing {city}: {e}")
                failed_cities.append(city)

        if failed_cities:
            raise RuntimeError(
                "Weather ingestion failed for: "
                + ", ".join(failed_cities)
            )

        print(
            "Weather ingestion completed successfully"
        )

    finally:
        if conn:
            conn.close()

            print("Database connection closed")


if __name__ == "__main__":
    main()