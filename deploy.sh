#!/bin/bash

# Deploy script for self-hosted tnyr.me
# This script builds the frontend with custom domain configuration

set -e

# Check if domain is provided
if [ -z "$1" ]; then
    echo "Usage: ./deploy.sh your-domain.com"
    echo "Example: ./deploy.sh myshortener.com"
    echo "Or configure backend/config.json and run: ./deploy.sh"
    exit 1
fi

DOMAIN=$1
# Determine default API URL scheme based on domain (use http for localhost/ports)
if [[ "$DOMAIN" =~ ^(localhost|127\.0\.0\.1)(:[0-9]+)?$ ]]; then
	DEFAULT_API_URL="http://$DOMAIN"
else
	DEFAULT_API_URL="https://$DOMAIN"
fi

API_URL=${2:-"$DEFAULT_API_URL"}

echo "🔧 Configuring deployment for domain: $DOMAIN"
echo "🔧 API URL: $API_URL"

# Update backend config.json with the new domain
echo "📝 Updating backend/config.json..."
if [ -f "backend/config.json" ]; then
    # Use jq if available, otherwise use sed (less reliable but more portable)
    if command -v jq >/dev/null 2>&1; then
        jq --arg domain "$DOMAIN" --arg api_url "$API_URL" \
           '.domain.name = $domain | .domain.api_base_url = $api_url' \
           backend/config.json > backend/config.json.tmp && \
        mv backend/config.json.tmp backend/config.json
    else
        # Fallback to sed (assumes the config has the domain section)
        sed -i.bak "s|\"name\": \"[^\"]*\"|\"name\": \"$DOMAIN\"|g" backend/config.json
        sed -i.bak "s|\"api_base_url\": \"[^\"]*\"|\"api_base_url\": \"$API_URL\"|g" backend/config.json
        rm -f backend/config.json.bak
    fi
    echo "✅ Updated backend/config.json"
else
    echo "❌ backend/config.json not found. Please copy from config_template.json"
    exit 1
fi

# Build the frontend
echo "📦 Building frontend..."
cd frontend
npm install
npm run build
cd ..

# Replace any remaining placeholders in the built files
echo "🔧 Replacing domain placeholders in static files..."
find backend/dist -type f \( -name "*.html" -o -name "*.xml" -o -name "*.json" -o -name "*.webmanifest" \) -exec sed -i.bak "s/%VITE_DOMAIN%/$DOMAIN/g" {} \;
find backend/dist -name "*.bak" -delete

echo "✅ Deployment built successfully!"
echo "📁 Built files are in backend/dist/"
echo ""
echo "Next steps:"
echo "1. Update your backend/config.json with appropriate settings"
echo "2. Configure your backend to run on the specified domain"
echo "3. Update DNS records to point to your server"
echo ""
echo "For development:"
echo "  cd frontend && npm run dev"
echo ""
echo "For production backend:"
echo "  cd backend && python main.py"