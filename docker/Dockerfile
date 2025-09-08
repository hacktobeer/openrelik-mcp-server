FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl

RUN pip install uv

ADD pyproject.toml uv.lock /app
RUN uv sync --all-groups

ADD . /app
WORKDIR /app
ENV PYTHONPATH=/app

CMD ["uv", "run", "fastmcp", "run", "src/main.py", "--transport", "http", "--host", "0.0.0.0", "--port", "8081"]

