FROM ubuntu:24.04
RUN apt-get update && apt-get install -y --no-install-recommends clang python3 ca-certificates procps git && rm -rf /var/lib/apt/lists/*
WORKDIR /src
ENTRYPOINT ["python3", "benchmarks/sg4-fanout/run.py"]
