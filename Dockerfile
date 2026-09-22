# Stage 1: build frontend
FROM node:20-alpine AS frontend-build
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ .
RUN npm run build

# Stage 2: API + SPA
FROM python:3.12-slim
WORKDIR /app
COPY backend/ ./backend/
COPY --from=frontend-build /build/dist ./frontend/dist
WORKDIR /app/backend
RUN pip install --no-cache-dir -r requirements.txt \
  && chmod +x start.sh
ENV FRONTEND_DIST=../frontend/dist
EXPOSE 8000
CMD ["./start.sh"]
