import sys

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

from airflow.providers.docker.operators.docker import (
    DockerOperator
)

from docker.types import Mount


sys.path.append(
    "/opt/airflow/api-request"
)


def ingest_weather_data():
    from insert_records import main

    main()


DBT_IMAGE = (
    "ghcr.io/dbt-labs/"
    "dbt-postgres:1.9.latest"
)


DBT_PROJECT_PATH = (
    "/home/rafael_sanyoto/repos/"
    "weather-data-project/dbt/my_project"
)


DBT_PROFILE_PATH = (
    "/home/rafael_sanyoto/repos/"
    "weather-data-project/dbt"
)


DBT_MOUNTS = [
    Mount(
        source=DBT_PROJECT_PATH,
        target="/usr/app",
        type="bind"
    ),

    Mount(
        source=DBT_PROFILE_PATH,
        target="/root/.dbt",
        type="bind"
    )
]


with DAG(
    dag_id="weather-api-orchestrator",

    start_date=datetime(
        2025,
        4,
        30
    ),

    schedule=timedelta(
        minutes=30
    ),

    catchup=False,

    max_active_runs=1,

    tags=[
        "weather",
        "data-engineering"
    ]

) as dag:

    ingest_data_task = PythonOperator(
        task_id="ingest_weather_data",

        python_callable=ingest_weather_data
    )


    dbt_run_task = DockerOperator(
        task_id="dbt_run",

        image=DBT_IMAGE,

        command="run",

        docker_url=(
            "unix://var/run/docker.sock"
        ),

        network_mode=(
            "weather-data-project_my-network"
        ),

        working_dir="/usr/app",

        mounts=DBT_MOUNTS,

        environment={
            "DBT_PROFILES_DIR": "/root/.dbt"
        },

        mount_tmp_dir=False
    )


    dbt_test_task = DockerOperator(
        task_id="dbt_test",

        image=DBT_IMAGE,

        command="test",

        docker_url=(
            "unix://var/run/docker.sock"
        ),

        network_mode=(
            "weather-data-project_my-network"
        ),

        working_dir="/usr/app",

        mounts=DBT_MOUNTS,

        environment={
            "DBT_PROFILES_DIR": "/root/.dbt"
        },

        mount_tmp_dir=False
    )


    (
        ingest_data_task
        >> dbt_run_task
        >> dbt_test_task
    )