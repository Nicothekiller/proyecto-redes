FROM oven/bun:1.4.4 AS build

WORKDIR /app

COPY package.json bun.lock ./
RUN bun install --frozen-lockfile

COPY . .
RUN bun run --bun build

FROM oven/bun:1.4.4

WORKDIR /app

COPY --from=build --chown=bun:bun /app/build ./build
COPY --from=build --chown=bun:bun /app/package.json ./

ENV HOST=0.0.0.0
ENV PORT=3000
ENV HOME=/home/bun

USER bun

EXPOSE 3000

HEALTHCHECK --interval=5s --timeout=3s --start-period=5s --retries=10 \
    CMD bun -e "fetch('http://127.0.0.1:3000/').then((r) => process.exit(r.ok ? 0 : 1)).catch(() => process.exit(1))"

CMD ["bun", "./build"]
