# Backend Testing Guide

This document explains the comprehensive test suite for the URL shortener backend.

## 🧪 Test Overview

The test suite covers all critical functionality:

- **Cryptographic Functions** (`test_crypto.py`) - AES encryption, Argon2 key derivation
- **API Endpoints** (`test_api.py`) - All Flask routes and error handling
- **Database Operations** (`test_database.py`) - SQLite schema, CRUD operations, constraints
- **Utility Functions** (`test_utils.py`) - ID generation, configuration validation

## 📦 Installation

Install testing dependencies:

```bash
pip install -r requirements.txt
```

## 🚀 Running Tests

### Quick Start
```bash
# Run all tests
pytest

# Or use the test runner
python run_tests.py
```

### Specific Test Categories
```bash
# Cryptographic tests only
python run_tests.py crypto

# API endpoint tests only  
python run_tests.py api

# Database tests only
python run_tests.py database

# Utility function tests only
python run_tests.py utils
```

### Test Options
```bash
# Run with coverage report
python run_tests.py coverage

# Fast mode (stop on first failure)
python run_tests.py fast

# Verbose output
python run_tests.py verbose

# See all available options
python run_tests.py help
```

## 📊 Coverage Requirements

The test suite maintains **80%+ code coverage** and covers:

### Cryptographic Security ⚡
- ✅ AES-256-CBC encryption/decryption roundtrips
- ✅ Argon2 key derivation consistency and security
- ✅ Invalid key length handling
- ✅ Corruption detection (wrong keys, corrupted data)
- ✅ Unicode URL handling
- ✅ Edge cases (empty strings, large data)

### API Robustness 🌐
- ✅ All endpoint success paths
- ✅ Comprehensive error handling (400, 404, 409, 500)
- ✅ Input validation and sanitization
- ✅ JSON parsing error handling
- ✅ HTTP method validation
- ✅ URL prefix normalization
- ✅ ID collision handling with retry logic

### Database Integrity 🗄️
- ✅ Schema creation and validation
- ✅ Primary key and NOT NULL constraints
- ✅ BLOB data integrity across various byte patterns
- ✅ Concurrent access patterns
- ✅ Performance characteristics
- ✅ Data type validation (TEXT, BLOB)

### ID Generation 🎲
- ✅ Character set compliance (no confusing chars: 0, O, I, l)
- ✅ Length consistency
- ✅ Uniqueness verification (statistical)
- ✅ Configuration flexibility

## 🔧 Test Configuration

Tests use isolated configuration:
- **In-memory SQLite database** (no interference with production data)
- **Reduced Argon2 parameters** (faster test execution)
- **Deterministic test salts** (reproducible results)

## 📁 Test Files Structure

```
backend/
├── tests/
│   ├── conftest.py           # Test fixtures and configuration
│   ├── test_crypto.py        # Cryptographic function tests
│   ├── test_api.py          # API endpoint tests  
│   ├── test_database.py     # Database operation tests
│   └── test_utils.py        # Utility function tests
├── pytest.ini              # Pytest configuration
├── run_tests.py             # Test runner script
└── README_TESTING.md        # This documentation
```

## ⚠️ Security Test Notes

**Critical Security Areas Tested:**
1. **Encryption Integrity** - Ensures no data corruption or key leakage
2. **ID Collision Handling** - Prevents duplicate shortened URLs
3. **Input Validation** - Protects against malformed requests
4. **Database Constraints** - Maintains data integrity

**Known Test Limitations:**
- Tests use reduced Argon2 parameters for speed (production uses stronger settings)
- Some timing-based attacks are not covered (out of scope for unit tests)
- Network-level security is tested in integration/E2E tests

## 🐛 Debugging Failed Tests

### Common Issues

1. **Import Errors**: Ensure you're in the backend directory
2. **Missing Dependencies**: Run `pip install -r requirements.txt`
3. **Database Errors**: Tests use in-memory DB, but check file permissions
4. **Config Mocking Issues**: Restart test session if config patches interfere

### Debug Commands
```bash
# Run single test with full output
pytest tests/test_crypto.py::TestCryptographicFunctions::test_encrypt_decrypt_roundtrip -v -s

# Run with Python debugger on failure
pytest --pdb tests/test_api.py

# Show all print statements
pytest -s
```

## 📈 Performance Expectations

**Test Execution Times:**
- Full test suite: < 30 seconds
- Crypto tests: < 10 seconds  
- API tests: < 15 seconds
- Database tests: < 10 seconds
- Utils tests: < 5 seconds

**Coverage Targets:**
- Overall: ≥ 80%
- Critical crypto functions: 100%
- API endpoints: ≥ 90%
- Database operations: ≥ 85%

## 🔄 Continuous Integration

For CI/CD pipelines, use:

```bash
# CI-friendly command with XML output
pytest --junitxml=test-results.xml --cov=main --cov-report=xml

# Fail on low coverage
pytest --cov=main --cov-fail-under=80
```

## 🆘 Getting Help

If tests fail unexpectedly:

1. **Check test output** for specific assertion failures
2. **Run individual test files** to isolate issues
3. **Verify dependencies** are correctly installed
4. **Check file permissions** for database operations
5. **Review recent code changes** that might affect tested functionality

## 🎯 Best Practices

When adding new functionality:

1. **Write tests first** (TDD approach)
2. **Test error conditions** as thoroughly as success cases  
3. **Use descriptive test names** that explain what is being tested
4. **Mock external dependencies** (filesystem, network)
5. **Maintain test isolation** (no shared state between tests)
6. **Update this documentation** when adding new test categories 