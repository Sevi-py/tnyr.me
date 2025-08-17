#!/bin/bash

# Simple build script that uses the current config.json settings
# Use this after you've manually configured backend/config.json

set -e

echo "📦 Building frontend using backend/config.json settings..."

# Check if config exists
if [ ! -f "backend/config.json" ]; then
    echo "❌ backend/config.json not found. Please copy from config_template.json and configure it."
    exit 1
fi

# Extract domain from config for the placeholder replacement
DOMAIN=$(cat backend/config.json | grep -o '"name": "[^"]*"' | sed 's/"name": "\([^"]*\)"/\1/')
if [ -z "$DOMAIN" ]; then
    echo "❌ Could not find domain.name in backend/config.json"
    exit 1
fi

echo "🔧 Using domain: $DOMAIN"

# Build the frontend
cd frontend
npm install
npm run build
cd ..

# Replace any remaining placeholders in the built files
echo "🔧 Replacing domain placeholders in static files..."
find backend/dist -type f \( -name "*.html" -o -name "*.xml" -o -name "*.json" -o -name "*.webmanifest" \) -exec sed -i.bak "s/%VITE_DOMAIN%/$DOMAIN/g" {} \;
find backend/dist -name "*.bak" -delete

echo "✅ Build completed successfully!"
echo "📁 Built files are in backend/dist/"
echo ""
echo "To run the backend:"
echo "  cd backend && python main.py"