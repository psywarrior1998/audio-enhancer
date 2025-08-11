#!/bin/bash
# Aura Audio Suite Launcher for macOS and Linux

# Set the name of the virtual environment directory
VENV_DIR="venv"

# Function to display errors and exit
die() {
    echo "ERROR: $1" >&2
    exit 1
}

# Check if the virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
    echo "First-time setup: Creating virtual environment and installing dependencies."
    echo "This may take several minutes. Please be patient..."
    
    # Create virtual environment
    python3 -m venv "$VENV_DIR" || die "Failed to create virtual environment. Make sure Python 3.8+ is installed."
    
    # Activate the environment
    source "$VENV_DIR/bin/activate"
    
    # Upgrade pip and install requirements
    python3 -m pip install --upgrade pip || die "Failed to upgrade pip."
    pip install -r requirements.txt || die "Failed to install dependencies from requirements.txt."
else
    # Activate the existing environment
    source "$VENV_DIR/bin/activate"
fi

echo ""
echo "Launching Aura Audio Suite..."
python3 app.py

echo ""
echo "Application closed."