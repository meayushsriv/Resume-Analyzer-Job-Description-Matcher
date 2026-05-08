#!/bin/bash
# Location: /setup.sh

echo "--- [AI Resume Parser] Starting Project Setup ---"

# 1. Check for Python 3.10+
echo "Checking Python version..."
if ! python3 --version &> /dev/null; then
    echo "ERROR: python3 is not installed. Please install Python 3.10 or higher."
    exit 1
fi

# 2. Create a virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment 'venv'..."
    python3 -m venv venv
else
    echo "Virtual environment 'venv' already exists."
fi

# 3. Activate the virtual environment
source venv/bin/activate
echo "Virtual environment activated."

# 4. Install Python dependencies
echo "Installing Python dependencies from requirements.txt..."
pip install -r requirements.txt

# 5. Create the .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    echo "IMPORTANT: Please edit the .env file with your GEMINI_API_KEY."
else
    echo ".env file already exists."
fi

# 6. Inform user how to run locally (no Docker)
echo ""
echo "--- Setup Complete! ---"
echo "To run the application locally (no Docker), make sure Redis is running on localhost:6379 and then:"
echo ""
echo "1) In one terminal:"
echo "   source venv/bin/activate"
echo "   uvicorn src.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "2) In another terminal:"
echo "   source venv/bin/activate"
echo "   celery -A src.worker.celery_app.celery_app worker --loglevel=info"
echo ""
echo "You can then access the API docs at http://localhost:8000/docs"