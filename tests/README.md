# Test Suite Documentation

This directory contains comprehensive unit and end-to-end tests for the window size analysis application.

## Test Structure

```
tests/
├── __init__.py              # Test package initialization
├── conftest.py              # Pytest fixtures and configuration
├── pytest.ini               # Pytest configuration file
├── unit/                    # Unit tests
│   ├── test_parse_window_results.py
│   ├── test_validate_conversion.py
│   ├── test_generate_html_report.py
│   └── test_generate_latex_report.py
└── e2e/                     # End-to-end tests
    └── test_full_pipeline.py
```

## Running Tests

### Prerequisites

Install test dependencies:
```bash
pip install -r requirements-test.txt
```

### Run All Tests

```bash
# Using the test runner script
./run_tests.sh

# Or directly with pytest (uses pytest.ini from tests/)
pytest tests/ -v
```

### Run Specific Test Suites

```bash
# Unit tests only
pytest tests/unit -v

# End-to-end tests only
pytest tests/e2e -v

# Specific test file
pytest tests/unit/test_parse_window_results.py -v

# Specific test function
pytest tests/unit/test_parse_window_results.py::TestParseWindowSize::test_parse_window_size_basic -v
```

## Test Coverage

### Unit Tests

- **parse_window_results.py**: Tests for parsing functions
  - Window size extraction
  - Video row parsing
  - Summary statistics parsing
  - Feature importance parsing
  - File parsing

- **validate_conversion.py**: Tests for validation functions
  - Video consistency validation
  - Row count validation
  - Numeric range validation
  - Summary statistics validation

- **generate_html_report.py**: Tests for HTML report generation
  - CSV loading
  - Statistics calculation
  - Best value finding
  - Plot generation
  - HTML escaping

- **generate_latex_report.py**: Tests for LaTeX report generation
  - CSV loading
  - Statistics calculation
  - LaTeX escaping
  - Plot generation

### End-to-End Tests

- **Full Pipeline**: Tests the complete workflow
  - Data parsing from input file
  - CSV output structure validation
  - HTML report generation
  - LaTeX report generation
  - Data consistency across pipeline

## Automatic Test Execution

Tests are automatically run in the following scenarios:

1. **Pre-commit Hook**: When you commit changes (if pre-commit is installed)
   ```bash
   pip install pre-commit
   pre-commit install
   ```

2. **CI/CD Pipeline**: On GitHub Actions when pushing to main/master/develop branches
   - See `.github/workflows/tests.yml`

## Writing New Tests

When adding new functionality, follow these guidelines:

1. **Unit Tests**: Test individual functions in isolation
   - Use fixtures from `conftest.py` for common test data
   - Mock external dependencies when possible
   - Test edge cases and error conditions

2. **End-to-End Tests**: Test the complete workflow
   - Use real data files when possible
   - Verify output file generation
   - Check data consistency

3. **Test Naming**: Follow pytest conventions
   - Test files: `test_*.py`
   - Test classes: `Test*`
   - Test functions: `test_*`

## Fixtures

Common fixtures are defined in `conftest.py`:

- `project_root`: Project root directory
- `test_data_dir`: Test data directory
- `temp_dir`: Temporary directory for test outputs
- `sample_video_results`: Sample video results data
- `sample_summary_stats`: Sample summary statistics
- `create_test_csv`: Factory for creating test CSV files
- `sample_window_scan_text`: Sample input text for parsing

## Troubleshooting

### Import Errors

If you see import errors, make sure:
1. The scripts directory is in the Python path
2. All dependencies are installed: `pip install -r requirements-test.txt`

### Pandas Not Available

Some tests require pandas. Install it with:
```bash
pip install pandas
```

### Test Failures

If tests fail:
1. Check that input data files exist in `data/raw/`
2. Run the parsing script first: `python3 scripts/parse_window_results.py`
3. Verify that processed data files exist in `data/processed/`

