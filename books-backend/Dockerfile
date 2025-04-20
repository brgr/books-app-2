FROM python:3.12-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:0.6.14 /uv /uvx /bin/

# Copy the project into the image
ADD . /app

# Sync the project into a new environment, using the frozen lockfile
WORKDIR /app
RUN uv sync --frozen

EXPOSE 80
CMD ["uv", "run", "fastapi", "run", "main.py", "--port", "80"]