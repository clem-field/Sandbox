FROM ghcr.io/astral-sh/uv:bookwork-slim AS build
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Set Proxy
ENV HTTP_PROXY=http://my-proxy.org:8080 \
    HTTPS_PROXY=http://my-proxy.org:8080 \
    http_proxy=HTTP_PROXY \
    https_proxy=HTTPS_PROXY

# Validate stable container
HEALTHCHECK --interval=90s --timeout=2s --start-period=5s --retries=2 \
 CMD [ -e /proc/1/exe ] && kill -0 1 || exit 1

# Set up the container and ENV
COPY ./pyproject.toml uv.lock .python-version ./
RUN uv venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN uv sync --no-dev --active

RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates libcap2-bin \
    && setcap cap_net_raw+ep /opt/venv/bin/python* \
    && apt-get remove -y libcap2-bin \
    && rm-rf /var/lib/apt/lists/*

COPY ./files/my-cert.pem /etc/ssl/certs/my-cert.pem
RUN update-ca-certificates

RUN adduser --disabled-password --gecos '' --uid 1000 appuser \
    && mkdir -p /home/appuser 

USER appuser
WORKDIR /app

# Specific Repo Information 
COPY ./output_files ./data/
COPY ./files/ ./files/
COPY ./creds/ ./creds/
COPY ./scripts/ .scripts/
# Globally needed
COPY ./*.py ./

CMD [ "bash" ]
