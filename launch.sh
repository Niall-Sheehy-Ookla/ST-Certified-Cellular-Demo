#!/bin/bash

# Cellular Certification Dashboard - Quick Start Setup
# This script sets up the environment and launches the application

echo "=========================================="
echo "📡 Cellular Certification Dashboard"
echo "Quick Start Setup"
echo "=========================================="
echo ""

# Check Python version
echo "✓ Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.8+"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "  Python version: $PYTHON_VERSION"
echo ""

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "  ✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate
echo "  ✓ Environment activated"
echo ""

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
echo "  ✓ Dependencies installed"
echo ""

# Verify files exist
echo "✓ Verifying application files..."
FILES=("app.py" "metrics_processor.py" "certification_scorer.py" "dashboard_ui.py")
for file in "${FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo "  ❌ Missing: $file"
        exit 1
    fi
    echo "  ✓ $file"
done
echo ""

# Launch Streamlit
echo "🚀 Launching Cellular Certification Dashboard..."
echo ""
echo "The dashboard will open in your default browser at:"
echo "http://localhost:8501"
echo ""
echo "To stop the application, press Ctrl+C in the terminal"
echo ""
echo "=========================================="
echo ""

streamlit run app.py
