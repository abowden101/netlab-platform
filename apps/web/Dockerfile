# syntax=docker/dockerfile:1
# Web UI image: builds the React + Vite app and serves the production bundle
# with `vite preview` on port 80 (compose maps 5173:80).
# Single-stage on purpose: this is the local-dev image, not a hardened prod one.
FROM node:20-alpine

ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL

WORKDIR /app

COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci

COPY apps/web/ ./
RUN npm run build

EXPOSE 80
CMD ["npx", "vite", "preview", "--port", "80", "--host", "0.0.0.0"]
