FROM node:20-alpine AS build-stage

WORKDIR /app

# Install pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

# Copy package files
COPY frontend/pnpm-lock.yaml frontend/package.json ./

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy source code
COPY frontend/ .

# Build
RUN pnpm build

# Production image
FROM nginx:stable-alpine AS production-stage

COPY --from=build-stage /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
