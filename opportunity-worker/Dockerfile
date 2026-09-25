FROM node:20-bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates util-linux passwd && rm -rf /var/lib/apt/lists/*
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin codex \
    && printf '%s\n' '#!/bin/sh' 'exec setpriv --reuid=codex --regid=codex --init-groups --inh-caps=-all --bounding-set=-all --no-new-privs /app/node_modules/@openai/codex/bin/codex.js "$@"' > /usr/local/bin/codex-unprivileged \
    && chmod 0755 /usr/local/bin/codex-unprivileged
WORKDIR /app
COPY package*.json ./
RUN npm install --no-audit --no-fund
COPY tsconfig.json ./
COPY src ./src
COPY tests ./tests
RUN npm test
RUN npm run build
ENV NODE_ENV=production
EXPOSE 3000
CMD ["npm","start"]
