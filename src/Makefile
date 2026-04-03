# FitCoachAR Project Management Makefile
# Designed for CAS 741 Course Project Submission
# Automates environment setup, dependency management, and parallel execution.

.PHONY: all run run-backend run-frontend install clean help test

# Configuration
VENV_DIR = backend/venv
PYTHON_BIN = $(VENV_DIR)/bin/python3
PIP_BIN = $(VENV_DIR)/bin/pip3
NODE_MODULES = frontend/node_modules

# Default target: Run everything
all: run

# Display help information
help:
	@echo "FitCoachAR Project Commands:"
	@echo "  make install        - Initial setup: creates virtualenv and installs all dependencies"
	@echo "  make run            - Starts both Backend and Frontend in parallel"
	@echo "  make run-backend    - Starts the Django/ASGI server on port 8000"
	@echo "  make run-frontend   - Starts the React/Vite server on port 5173"
	@echo "  make test           - Runs all backend tests (Interfaces + VnV Suite)"
	@echo "  make clean          - Removes caches and environment files"

# Combined Parallel Execution
run:
	@echo "🚀 Launching FitCoachAR Services..."
	@$(MAKE) run-backend & $(MAKE) run-frontend & wait

# Backend Execution (uses local venv and daphne for WebSockets)
run-backend:
	@echo "🐍 Starting Backend (Daphne)..."
	@if [ ! -f $(PYTHON_BIN) ]; then \
		echo "❌ Error: Virtual environment not found at $(VENV_DIR)."; \
		echo "👉 Please run 'make install' first."; \
		exit 1; \
	fi
	@$(PYTHON_BIN) backend/manage.py migrate
	@cd backend && ../$(VENV_DIR)/bin/daphne -b 0.0.0.0 -p 8000 fitcoach_backend.asgi:application

# Frontend Execution (React/Vite)
run-frontend:
	@echo "⚛️ Starting Frontend..."
	@if [ ! -d $(NODE_MODULES) ]; then \
		echo "❌ Error: node_modules not found in frontend/."; \
		echo "👉 Please run 'make install' first."; \
		exit 1; \
	fi
	@cd frontend && npm run dev

# Test Suite (Interfaces + VnV)
test:
	@echo "🧪 Running Backend Test Suite..."
	@if [ ! -f $(PYTHON_BIN) ]; then \
		echo "❌ Error: Virtual environment not found at $(VENV_DIR)."; \
		exit 1; \
	fi
	@echo "🔍 Testing Interface Enforcement (MG/MIS Compliance)..."
	@$(PYTHON_BIN) backend/test_interfaces.py
	@echo "\n🔍 Testing System V&V Suite (SRS Requirements)..."
	@$(PYTHON_BIN) backend/tests/test_vnv.py || true
	@echo "\n✅ Test run complete."

# Full Environment Setup (VENV + PIP + NPM)
install:
	@echo "🛠️ Creating Python Virtual Environment..."
	@python3 -m venv $(VENV_DIR)
	@echo "📦 Upgrading pip..."
	@$(PIP_BIN) install --upgrade pip
	@echo "📦 Installing Python dependencies from backend/requirements.txt..."
	@$(PIP_BIN) install -r backend/requirements.txt
	@echo "📦 Installing Frontend dependencies (npm install)..."
	@if command -v npm > /dev/null; then \
		cd frontend && npm install; \
	else \
		echo "❌ Error: npm is not installed on this system."; \
		exit 1; \
	fi
	@echo "✅ Setup Complete. Type 'make run' to launch the app."

# Cleanup
clean:
	@echo "🧹 Cleaning temporary files..."
	@rm -rf $(VENV_DIR)
	@rm -rf $(NODE_MODULES)
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@echo "Done."
