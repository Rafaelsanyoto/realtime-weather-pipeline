{{ config(
    materialized='table'
) }}


with source as (

    select *
    from {{ source(
        'dev',
        'raw_weather_data'
    ) }}
),

de_dup as (

    select
        *,
        row_number() over (
            partition by
                city,
                time
            order by
                inserted_at desc,
                id desc
        ) as rn
    from source
)

select
    id,
    city,
    country,
    temperature,
    feelslike,
    humidity,
    weather_descriptions,
    wind_speed,
    pressure,
    precip,
    time as weather_time_local,
    inserted_at,
    inserted_at
        + (
            utc_offset || ' hours'
        )::interval
        as inserted_at_local,
    utc_offset
from de_dup
where rn = 1