#!/bin/bash
set -e

echo "💡 Bootstrapping OTEL from ECS metadata using Python..."

# Run the header setup before OTEL is initialized
otel_headers=$(python src/utils/bootstrap_otel_config_ecs.py)
export OTEL_EXPORTER_OTLP_LOGS_HEADERS="$otel_headers"
echo "OTEL_EXPORTER_OTLP_LOGS_HEADERS: $OTEL_EXPORTER_OTLP_LOGS_HEADERS"

# Replace shell with actual application (for ECS / Docker best practice)
exec opentelemetry-instrument python ecs_main.py
