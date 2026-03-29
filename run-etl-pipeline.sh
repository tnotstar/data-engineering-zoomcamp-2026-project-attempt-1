#!/bin/bash
docker compose exec etl-pipeline bruin run --force /pipeline --var number_of_variants=10000
