# Production Dockerfile for QuardLink Web SPA
FROM node:22-alpine AS build
WORKDIR /repo
RUN corepack enable && corepack prepare pnpm@10.13.1 --activate

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json ./apps/web/package.json
RUN pnpm install --frozen-lockfile

COPY . .

ARG VITE_API_URL=""
ARG VITE_CONTACT_EMAIL="adarshs18400@gmail.com"
ARG VITE_CDN_URL=""
ENV VITE_API_URL=${VITE_API_URL} VITE_CONTACT_EMAIL=${VITE_CONTACT_EMAIL} VITE_CDN_URL=${VITE_CDN_URL}

RUN pnpm --filter web build

FROM nginx:1.27-alpine AS prod
COPY --from=build /repo/apps/web/dist /usr/share/nginx/html
COPY infra/nginx/spa.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
