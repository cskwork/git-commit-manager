#!/bin/bash

# Git Commit Manager - Complete Setup Script for Linux/macOS

set -e  # Exit on any error

echo "====================================="
echo "Git Commit Manager - Complete Setup"
echo "====================================="
echo

# Check if already installed
if command -v gcm &> /dev/null; then
    echo "[INFO] Git Commit Manager is already installed."
    run_options
fi

# Python version check
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed."
    echo "Please install Python 3.8 or higher from https://python.org"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "[OK] Python $PYTHON_VERSION detected"

# pip check
if ! command -v pip3 &> /dev/null; then
    echo "[ERROR] pip3 is not installed."
    echo "Please install pip or reinstall Python."
    exit 1
fi

# Virtual environment setup
echo
echo "====================================="
echo "Virtual Environment Setup"
echo "====================================="

if [ -d "venv" ]; then
    echo "[INFO] Virtual environment already exists."
    read -p "Use existing virtual environment? (Y/n): " USE_EXISTING
    if [[ $USE_EXISTING =~ ^[Nn]$ ]]; then
        echo "Removing existing virtual environment..."
        rm -rf venv
        create_venv
    else
        source venv/bin/activate
        echo "[OK] Existing virtual environment activated"
        install_deps
    fi
else
    create_venv
fi

create_venv() {
    read -p "Create virtual environment? (Y/n): " CREATE_VENV
    if [[ $CREATE_VENV =~ ^[Nn]$ ]]; then
        echo "[WARNING] Running without virtual environment."
        install_deps
        return
    fi
    
    echo "Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "[ERROR] Failed to create virtual environment."
        exit 1
    fi
    
    source venv/bin/activate
    echo "[OK] Virtual environment created and activated"
}

install_deps() {
    # Install dependencies
    echo
    echo "====================================="
    echo "Installing Dependencies"
    echo "====================================="
    echo "Installing required packages..."
    
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "[ERROR] Failed to install dependencies."
        echo "Make sure requirements.txt exists and try again."
        exit 1
    fi

    # Install package in development mode
    echo
    echo "Installing Git Commit Manager..."
    pip install -e .
    if [ $? -ne 0 ]; then
        echo "[ERROR] Failed to install Git Commit Manager."
        exit 1
    fi

    ollama_setup
}

ollama_setup() {
    # Ollama setup
    echo
    echo "====================================="
    echo "Ollama Setup (Optional)"
    echo "====================================="
    
    if ! command -v ollama &> /dev/null; then
        echo "[WARNING] Ollama is not installed."
        echo "          Install from: https://ollama.ai"
        echo "          Or configure OpenRouter/Gemini API keys instead."
        read -p "Would you like to open Ollama download page? (y/N): " INSTALL_OLLAMA
        if [[ $INSTALL_OLLAMA =~ ^[Yy]$ ]]; then
            if command -v xdg-open &> /dev/null; then
                xdg-open https://ollama.ai
            elif command -v open &> /dev/null; then
                open https://ollama.ai
            else
                echo "Please visit: https://ollama.ai"
            fi
        fi
    else
        echo "[OK] Ollama is installed."
        echo
        echo "Current Ollama models:"
        ollama list
        
        # Check for recommended model
        if ! ollama list | grep -q "gemma3:1b"; then
            echo
            read -p "Install recommended model gemma3:1b (~1GB)? (y/N): " INSTALL_MODEL
            if [[ $INSTALL_MODEL =~ ^[Yy]$ ]]; then
                echo "Downloading gemma3:1b model (this may take a few minutes)..."
                ollama pull gemma3:1b
                if [ $? -ne 0 ]; then
                    echo "[WARNING] Failed to download model. You can try again later."
                else
                    echo "[OK] gemma3:1b model installed successfully."
                fi
            fi
        else
            echo "[OK] Recommended model gemma3:1b is already installed."
        fi
    fi

    env_setup
}

env_setup() {
    # Environment configuration
    echo
    echo "====================================="
    echo "Environment Configuration"
    echo "====================================="
    
    if [ ! -f ".env" ]; then
        echo "Creating .env configuration file..."
        cp env.example .env
        echo "[OK] .env file created from template."
        echo "[INFO] Edit .env file to add your API keys if using OpenRouter or Gemini."
    else
        echo "[INFO] .env file already exists."
    fi

    setup_complete
}

setup_complete() {
    echo
    echo "====================================="
    echo "Setup Complete!"
    echo "====================================="
    echo
    echo "Available commands:"
    echo "  gcm watch    - Real-time file monitoring with commit message generation"
    echo "  gcm analyze  - Analyze current changes once"
    echo "  gcm review   - Perform code review on changes"
    echo "  gcm config   - Show configuration guide"
    echo
    echo "Note: Code review is now disabled by default."
    echo "      You'll be prompted whether to run it during monitoring."
    echo

    run_options
}

run_options() {
    # Run options
    read -p "What would you like to do? (w)atch/(a)nalyze/(r)eview/(q)uit: " RUN_CHOICE

    case $RUN_CHOICE in
        w|watch)
            run_watch
            ;;
        a|analyze)
            run_analyze
            ;;
        r|review)
            run_review
            ;;
        q|quit)
            end_script
            ;;
        *)
            run_watch
            ;;
    esac
}

run_watch() {
    echo
    echo "Starting real-time monitoring..."
    echo "Press Ctrl+C to stop monitoring."
    echo
    gcm watch
    end_script
}

run_analyze() {
    echo
    echo "Analyzing current changes..."
    gcm analyze
    echo
    run_options
}

run_review() {
    echo
    echo "Running code review..."
    gcm review
    echo
    run_options
}

end_script() {
    echo
    echo "Thank you for using Git Commit Manager!"
    exit 0
}

# Start the script
if [ -d "venv" ]; then
    install_deps
else
    create_venv
fi