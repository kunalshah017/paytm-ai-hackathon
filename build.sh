#!/usr/bin/env bash
set -e

# Install Node.js dependencies and build client
cd client
npm install
npm run build
cd ..

# Install Python dependencies
cd server
pip install --upgrade pip
pip install .

# Install Playwright Chromium browser (without system deps - Render has them)
export PLAYWRIGHT_BROWSERS_PATH=/opt/render/.cache/ms-playwright
playwright install chromium
