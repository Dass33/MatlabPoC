# ── Build stage ───────────────────────────────────────────────────────────────
FROM rust:1.82-slim AS builder

# libhdf5-dev + pkg-config required for the hdf5 crate
RUN apt-get update && apt-get install -y \
    libhdf5-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Cache dependency compilation separately from application source
COPY Cargo.toml Cargo.lock ./
RUN mkdir src && echo 'fn main(){}' > src/main.rs \
    && cargo build --release \
    && rm -rf src

COPY src       ./src
COPY templates ./templates
COPY static    ./static

# Touch main.rs so Cargo rebuilds the binary
RUN touch src/main.rs && cargo build --release

# ── Runtime stage ──────────────────────────────────────────────────────────────
FROM debian:bookworm-slim AS runtime

RUN apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    libhdf5-103 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /build/target/release/nsm-processor .
COPY --from=builder /build/templates ./templates
COPY --from=builder /build/static    ./static

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:3000/health || exit 1

ENV RUST_LOG=nsm_processor=info,tower_http=warn

CMD ["./nsm-processor"]
