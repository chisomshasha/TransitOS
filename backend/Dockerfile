# TransitOS backend — alternate location (kept for parity with the root Dockerfile).

FROM python:3.11-slim

# System deps for bcrypt and cryptography wheels.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (better Docker layer caching).
# Paths are relative to the REPO ROOT, since that's the build context.
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend source into the image.
COPY backend/app ./app
COPY backend/scripts ./scripts
COPY backend/start.sh ./start.sh

# GitHub's web UI does not preserve Unix permissions, so a file committed
# via drag-and-drop arrives without its execute bit. Force it on here so
# ``CMD ["./start.sh"]`` doesn't fail with "permission denied".
RUN chmod +x ./start.sh

# uvicorn listens on the port Railway assigns via the PORT env var,
# falling back to 8000 for local Docker / docker-compose runs.
EXPOSE 8000

# Run the start script (handles $PORT env var expansion + exec for proper signal handling).
CMD ["./start.sh"]
