#!/bin/bash
#./setup.sh
# Quick start script for PDF Generator

echo "🚀 Starting PDF Generator Setup..."
echo ""

# Check Python version
python3 --version

echo ""
echo "📦 Creating virtual environment..."
python3 -m venv venv

echo ""
echo "✅ Activating virtual environment..."
source venv/bin/activate

echo ""
echo "📥 Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the server:"
echo "  source venv/bin/activate  # Activate virtual environment first"
echo "  uvicorn app.app:app --reload"
echo ""
echo "Then test with:"
echo "  curl -X POST http://127.0.0.1:8000/render -H 'Content-Type: application/json' --data @example.json -o output.pdf"
echo ""
echo "API Documentation:"
echo "  Swagger UI: http://127.0.0.1:8000/docs"
echo "  ReDoc:      http://127.0.0.1:8000/redoc"
echo ""
