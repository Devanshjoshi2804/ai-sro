# The console.
#
#     docker build -t ai-sro-web:$(git rev-parse --short HEAD) \
#       --build-arg NEXT_PUBLIC_API_URL=https://sro.example.internal/api \
#       --build-arg NEXT_PUBLIC_EXTENSION_ORIGINS=chrome-extension://<id> \
#       frontend/
#
# **Both build args are baked in and cannot be changed at run time.** Next
# inlines `NEXT_PUBLIC_*` into the browser bundle where it appears verbatim,
# and `next.config.ts` reads the extension origins in `headers()`, which is
# evaluated during the build. So one image does not serve two environments:
# staging and production are two builds, or the console is proxied so that
# `NEXT_PUBLIC_API_URL` can stay a same-origin path.
#
# Getting either wrong is quiet, not loud. A wrong API url is a console that
# loads and fails every request; a wrong extension origin is a side panel whose
# handshake never completes and never says why.

FROM node:22-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci


FROM node:22-slim AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_EXTENSION_ORIGINS
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NEXT_PUBLIC_EXTENSION_ORIGINS=$NEXT_PUBLIC_EXTENSION_ORIGINS \
    NEXT_TELEMETRY_DISABLED=1

# `lib/env.ts` validates at module load and fails the boot rather than the
# first request that needs a value. That runs during the build too, so a
# malformed url fails here -- which is the point of validating it at all.
RUN npm run build


FROM node:22-slim AS runtime
WORKDIR /app

RUN useradd --create-home --uid 10001 sro

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

# `output: "standalone"` traces what the server actually imports. `static` and
# `public` are not traced into it and are copied separately -- miss them and
# the console serves HTML with no CSS and no fonts, which looks like a broken
# stylesheet rather than a broken image.
COPY --from=build --chown=sro:sro /app/.next/standalone ./
COPY --from=build --chown=sro:sro /app/.next/static ./.next/static
COPY --from=build --chown=sro:sro /app/public ./public

USER sro
EXPOSE 3000

CMD ["node", "server.js"]
