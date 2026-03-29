#!/bin/bash
docker compose exec etl-pipeline bruin validate --force /pipeline --var number_of_variants=100
