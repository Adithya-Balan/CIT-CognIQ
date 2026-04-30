#!/bin/bash

# Exit on any error
set -o errexit

# Install Python dependencies
pip install -r requirements.txt

# Install Node.js dependencies for Tailwind CSS
npm install

# Build Tailwind CSS (one-time build for production, no --watch)
npx @tailwindcss/cli -i ./static/styles/input.css -o ./static/styles/output.css

# Collect static files 
python manage.py collectstatic --noinput

# Run database migrations (for PostgreSQL)
python manage.py migrate