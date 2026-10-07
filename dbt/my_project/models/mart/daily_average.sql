{{ config(
    materialized='table'
) }}


select

    city,
    country,
    date(
        weather_time_local
    ) as date,
    round(
        avg(temperature)::numeric,
        2
    ) as avg_temperature,
    round(
        min(temperature)::numeric,
        2
    ) as min_temperature,
    round(
        max(temperature)::numeric,
        2
    ) as max_temperature,
    round(
        avg(feelslike)::numeric,
        2
    ) as avg_feelslike,
    round(
        avg(humidity)::numeric,
        2
    ) as avg_humidity,
    round(
        avg(wind_speed)::numeric,
        2
    ) as avg_wind_speed,
    round(
        avg(pressure)::numeric,
        2
    ) as avg_pressure,
    round(
        avg(precip)::numeric,
        2
    ) as avg_precipitation,
    count(*) as observation_count
from {{ ref(
    'stg_weather_data'
) }}

group by
    city,
    country,
    date(
        weather_time_local
    )
order by
    date(
        weather_time_local
    ),
    city