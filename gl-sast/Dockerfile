FROM ghcr.io/astral-sh/uv:bookwork-slim AS build
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
ARG python_function

WORKDIR /app
COPY ./pyproject.toml uv.lock .python-version ./

RUN uv venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN uv sync --no-dev --active

COPY ./data/${python_function}/ ./data/
COPY ./scripts${python_function}/*.py .scripts
COPY ./scripts/utilities/*.* ./scripts/
