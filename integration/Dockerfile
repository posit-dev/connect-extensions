FROM python:3

RUN apt-get update && apt-get install -y make

WORKDIR /connect-extensions

# Copy all files needed for package installation
COPY . /connect-extensions/integration

# Run before other copies to cache dependencies
WORKDIR /connect-extensions/integration

# DEBUG
RUN make debug-env

RUN --mount=type=cache,mode=0755,target=/root/.cache/pip make docker-deps
RUN --mount=type=cache,mode=0755,target=/root/.cache/pip make dev
