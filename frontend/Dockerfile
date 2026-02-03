# =============================================================================
# BillAgent Pro - Frontend Dockerfile
# =============================================================================
# Multi-stage build for production React application with Nginx
#
# Build: docker build -t billagent-frontend .
# Run:   docker run -p 80:80 billagent-frontend
# =============================================================================

# =============================================================================
# Stage 1: Build Stage
# =============================================================================
FROM node:20-alpine AS builder

# Set working directory
WORKDIR /app

# Install dependencies first (better caching)
COPY package.json package-lock.json* yarn.lock* pnpm-lock.yaml* ./

# Install dependencies based on available lock file
RUN \
    if [ -f yarn.lock ]; then yarn install --frozen-lockfile; \
    elif [ -f package-lock.json ]; then npm ci; \
    elif [ -f pnpm-lock.yaml ]; then corepack enable pnpm && pnpm install --frozen-lockfile; \
    else npm install; \
    fi

# Copy source files
COPY . .

# Build arguments for environment configuration
ARG VITE_API_URL=/api
ARG VITE_ENVIRONMENT=production

# Set environment variables for build
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_ENVIRONMENT=$VITE_ENVIRONMENT

# Build the application
RUN npm run build

# =============================================================================
# Stage 2: Production Stage with Nginx
# =============================================================================
FROM nginx:1.25-alpine AS production

# Install curl for health checks
RUN apk add --no-cache curl

# Remove default nginx config
RUN rm -rf /etc/nginx/conf.d/*

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Copy built assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Create non-root user for security
RUN addgroup -g 101 -S nginx || true && \
    adduser -S -D -H -u 101 -h /var/cache/nginx -s /sbin/nologin -G nginx -g nginx nginx || true && \
    chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /var/run && \
    chown -R nginx:nginx /var/log/nginx && \
    chown -R nginx:nginx /usr/share/nginx/html && \
    touch /var/run/nginx.pid && \
    chown -R nginx:nginx /var/run/nginx.pid

# Expose port 80
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:80/health || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
