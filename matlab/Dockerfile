FROM rust:slim AS builder
RUN apt-get update && apt-get install -y --no-install-recommends \
    pkg-config libfontconfig-dev \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /build
COPY rust_src/ .
RUN cargo build --release

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends libgcc-s1 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /build/target/release/nsm-algorithm /usr/local/bin/
ENTRYPOINT ["/usr/local/bin/nsm-algorithm"]
