{{ config(
    materialized='table'
) }}

with ranked_weather as (

    select
        *,
        row_number() over (
            partition by city
            order by
                weather_time_local desc,
                inserted_at_local desc
        ) as rn
    from {{ ref(
        'stg_weather_data'
    ) }}
)

select
    city,
    country,
    temperature,
    feelslike,
    humidity,
    weather_descriptions,
    wind_speed,
    pressure,
    precip,
    weather_time_local,
    inserted_at_local
from ranked_weather
where rn = 1
order by city