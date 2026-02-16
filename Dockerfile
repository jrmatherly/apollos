# syntax=docker/dockerfile:1
FROM ubuntu:noble AS base
LABEL homepage="https://github.com/jrmatherly/apollos"
LABEL repository="https://github.com/jrmatherly/apollos"
LABEL org.opencontainers.image.source="https://github.com/jrmatherly/apollos"
LABEL org.opencontainers.image.description="Your second brain, containerized for personal, local deployment."

# Install System Dependencies
RUN apt-get update -y && apt-get -y install --no-install-recommends \
    python3-pip \
    swig \
    curl \
    # Required by RapidOCR
    libgl1 \
    libglx-mesa0 \
    libglib2.0-0 \
    docker.io \
    # Required by llama-cpp-python pre-built wheels. See #1628
    musl-dev && \
    ln -s /usr/lib/x86_64-linux-musl/libc.so /lib/libc.musl-x86_64.so.1 && \
    # Clean up
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Build Server
FROM base AS server-deps
WORKDIR /app
COPY pyproject.toml .
COPY README.md .
ARG VERSION=0.0.0
# use the pre-built llama-cpp-python, torch cpu wheel
ENV PIP_EXTRA_INDEX_URL="https://download.pytorch.org/whl/cpu https://abetlen.github.io/llama-cpp-python/whl/cpu"
# avoid downloading unused cuda specific python packages
ENV CUDA_VISIBLE_DEVICES=""
RUN sed -i "s/dynamic = \\[\"version\"\\]/version = \"$VERSION\"/" pyproject.toml && \
    pip install --no-cache-dir --break-system-packages .

# Build Web App
FROM oven/bun:1-alpine AS web-app
# Set build optimization env vars
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
WORKDIR /app/src/interface/web
# Install dependencies first (cache layer)
COPY src/interface/web/package.json src/interface/web/bun.lock ./
RUN bun install --frozen-lockfile
# Copy source and build
COPY src/interface/web/. ./
RUN bun run build

# Merge the Server and Web App into a Single Image
FROM base
ENV PYTHONPATH=/app/src
WORKDIR /app
COPY --from=server-deps /usr/local/lib/python3.12/dist-packages /usr/local/lib/python3.12/dist-packages
COPY --from=web-app /app/src/interface/web/out ./src/apollos/interface/built
COPY . .
WORKDIR /app/src
RUN python3 apollos/manage.py collectstatic --noinput
WORKDIR /app

# Run the Application
# There are more arguments required for the application to run,
# but those should be passed in through the docker-compose.yml file.
ARG PORT=42110
EXPOSE ${PORT}
ENTRYPOINT ["python3", "src/apollos/main.py"]
