FROM node:20-bookworm AS frontend

WORKDIR /workspace

COPY package.json package-lock.json ./
COPY apps/desktop/package.json ./apps/desktop/package.json
RUN npm ci

COPY apps ./apps

EXPOSE 1420

CMD ["npm", "--workspace", "apps/desktop", "run", "dev", "--", "--host", "0.0.0.0"]
