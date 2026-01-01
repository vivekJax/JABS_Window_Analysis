#!/bin/bash
# Test runner script for window size analysis application
# Runs all tests and reports results

set -e  # Exit on error

echo "=========================================="
echo "Window Size Analysis - Test Suite"
echo "=========================================="
echo ""

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo "ERROR: pytest is not installed"
    echo "Install it with: pip install pytest"
    exit 1
fi

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "Running unit tests..."
echo "----------------------------------------"
pytest tests/unit -v --tb=short -m "not slow"

echo ""
echo "Running end-to-end tests..."
echo "----------------------------------------"
pytest tests/e2e -v --tb=short -m "not slow"

echo ""
echo "=========================================="
echo "All tests completed!"
echo "=========================================="

