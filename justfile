set dotenv-load := true

# List available recipes
default:
    @just --list

# Start infrastructure only (Postgres) in a container
infra:
    docker compose --profile infra up -d

# Run the API locally with autoreload against containerized Postgres
dev host="127.0.0.1" port="8000": infra
    uv run fastapi dev app/api.py --host {{host}} --port {{port}}

# Build and start the full production stack (Postgres + Gunicorn API)
prod:
    docker compose --profile prod up -d --build

# Alias for the full production stack
all: prod

# Follow logs from the production stack
logs:
    docker compose --profile prod logs -f

# Stop the stack, preserving the Postgres volume
down:
    docker compose --profile prod down

# Stop the stack and delete the Postgres volume (destroys data)
clean:
    docker compose --profile prod down -v
