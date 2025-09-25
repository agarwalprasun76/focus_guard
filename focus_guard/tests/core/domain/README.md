# Focus Guard Domain Module Tests

## Overview

This directory contains unit tests for the Focus Guard domain module. The tests verify the functionality of domain models, constants, and utilities that form the foundation of the Focus Guard system.

## Test Files

### `test_constants.py`

Tests for domain constants and predefined configurations:

- **TestDomainConstants**: Verifies that domain constants are properly structured and contain expected values
  - Tests for DOMAIN_CATEGORIES structure and content
  - Tests for DOMAIN_WHITELIST validation
  - Tests for APPLICATION_DOMAINS structure and content
  - Tests for CATEGORY_TO_ENUM_MAPPING validation
  - Tests for DEFAULT_CONFIG structure

### `test_models.py`

Tests for domain models and their functionality:

- **TestDomain**: Verifies Domain class functionality
  - Domain initialization, validation, and normalization
  - Domain parts extraction (TLD, registered domain)
  - Subdomain detection
  - Domain equality and string representation

- **TestURL**: Verifies URL class functionality
  - URL initialization and validation
  - Component extraction (domain, scheme, path, query)
  - String representation

- **TestCategory**: Verifies Category enum functionality
  - String to Category conversion
  - Invalid category handling

## Running the Tests

To run all domain tests:

```bash
python -m unittest focus_guard/tests/core/domain/test_*.py
```

To run a specific test file:

```bash
python -m unittest focus_guard/tests/core/domain/test_constants.py
```

## Test Results

Current test status:
- Total tests: 26
- Passing: 25
- Failing: 1 (`test_domain_equality` in `TestDomain`)

## Known Issues

1. **Domain Equality Test Failure**: The `test_domain_equality` test in `TestDomain` fails because it attempts to compare a Domain object with a string directly. The test expects `Domain('example.com') == 'example.com'` to be True, but the current implementation only supports equality between Domain objects.
