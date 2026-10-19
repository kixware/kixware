FROM debian:trixie-slim@sha256:a29215f6a35e51e22adffa17f89e9d2ef06214e64a2bad10d765c46aea49f11f
RUN apt-get update && apt-get install -y --no-install-recommends wine wine64 xvfb xauth ca-certificates && rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 1000 builder && mkdir -p /build && chown builder:builder /build
USER builder
ENV WINEDEBUG=-all WINEPREFIX=/build/wine WINEARCH=win64
WORKDIR /build
