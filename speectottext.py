#!/bin/bash

# Setup script for Speech-to-Text Application

echo "Setting up Speech-to-Text Application..."

# Create virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip

# Install core requirements
echo "Installing core requirements..."
pip install streamlit SpeechRecognition

# Install recommended packages
echo "Installing recommended packages..."
pip install openai pydub

# Install text processing packages
echo "Installing text processing packages..."
pip install fuzzywuzzy python-levenshtein

# Install Indic language support
echo "Installing Indic language support..."
pip install indic-transliteration

echo "Setup complete!"
echo "To run the application:"
echo "streamlit run your_app_name.py"
