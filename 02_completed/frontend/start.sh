#!/bin/bash

# Cosmos Voyager Frontend - Quick Start Script
echo "🚀 Starting Cosmos Voyager Frontend..."
echo ""

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
    echo "✅ Dependencies installed"
    echo ""
fi

# Check if backend is running
echo "🔍 Checking backend connection..."
if curl -s http://localhost:8000/health/ready > /dev/null 2>&1; then
    echo "✅ Backend is running on port 8000"
else
    echo "⚠️  Backend is NOT running!"
    echo "Please start the backend first:"
    echo "  cd ../python"
    echo "  python -m src.app.services.mcp_http_server &"
    echo "  uvicorn src.app.travel_agents_api:app --reload --host 0.0.0.0 --port 8000"
    echo ""
    read -p "Press Enter to continue anyway or Ctrl+C to exit..."
fi

echo ""
echo "🌐 Starting development server..."
echo "Frontend will be available at: http://localhost:4200"
echo "API proxy: http://localhost:4200/api → http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

npm start
