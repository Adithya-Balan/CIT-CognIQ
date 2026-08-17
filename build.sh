#!/bin/bash

# Exit on any error
set -o errexit

# Install Python dependencies
uv sync

# Install Node.js dependencies for Tailwind CSS
npm install

# Build Tailwind CSS (one-time build for production, no --watch)
npx @tailwindcss/cli -i ./static/styles/input.css -o ./static/styles/output.css

# Collect static files 
uv run python manage.py collectstatic --noinput

# Run database migrations (for PostgreSQL)
uv run python manage.py migrate