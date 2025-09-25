# Focus Guard Domain Module

## Overview

The Domain module provides core domain models and utilities for the Focus Guard application. It defines fundamental entities such as domains, URLs, and categories that are used throughout the system for classification, filtering, and blocking functionality.

## Components

### Models (`models.py`)

- **Domain**: Represents a normalized and validated domain name
  - Handles validation, normalization, and subdomain detection
  - Provides methods for extracting parts, TLD, and registered domain
  - Supports equality comparison and string representation

- **URL**: Represents a normalized and parsed URL
  - Extracts components like scheme, path, query, and domain
  - Handles various URL formats and edge cases
  - Integrates with the Domain class for domain extraction

- **Category**: Enum defining domain categories
  - Includes categories like SOCIAL_MEDIA, ENTERTAINMENT, PRODUCTIVITY, etc.
  - Provides conversion between string representations and enum values

- **Classification**: Represents the result of domain classification
  - Links a domain to its assigned category
  - Includes confidence score and optional metadata

### Constants (`constants.py`)

- **DOMAIN_CATEGORIES**: Maps user-friendly category names to lists of domains
- **DOMAIN_WHITELIST**: Set of always-allowed domains
- **APPLICATION_DOMAINS**: Maps application types to executable names
- **CATEGORY_TO_ENUM_MAPPING**: Maps user-friendly categories to enum values
- **DEFAULT_CONFIG**: Default configuration for the system

### Utilities (`utils.py`)

- **Domain validation**: Functions to validate domain names according to RFC standards
- **Domain normalization**: Functions to normalize domain formats (lowercase, remove trailing dots, etc.)
- **URL processing**: Robust functions to extract and normalize domains from URLs, including:
  - Handling of various URL formats and edge cases
  - Support for URLs with authentication
  - Protocol-relative URL support
- **IDN support**: Full support for Internationalized Domain Names (IDNs)
- **Malformed URL handling**: Graceful handling of malformed URLs with appropriate fallbacks

## Usage

The domain module serves as the foundation for:

1. **Domain Classification**: Categorizing domains into predefined categories
2. **URL Processing**: Extracting and validating domains from URLs
3. **Filtering Rules**: Defining which domains should be blocked or allowed
4. **Application Categorization**: Categorizing applications by executable name

## Recent Updates (v1.1.0)

### URL Normalization Improvements

- Enhanced URL normalization to handle edge cases:
  - URLs with empty usernames (e.g., `http://@example.com`)
  - Malformed URLs with various authentication patterns
  - Improved handling of protocol-relative URLs

### Edge Case Handling

- Added comprehensive test coverage for:
  - Internationalized Domain Names (IDNs)
  - Long domain names (up to 253 characters)
  - Malformed and unusual URL formats
  - IP addresses in URLs
  - Unicode characters in URLs

## Architecture

The module follows a hybrid approach for domain classification:

1. **Enum-based system** (Category enum in models.py):
   - Provides type safety and compile-time checking
   - Used internally by the code for classification and processing

2. **Dictionary-based configuration** (constants.py):
   - Uses user-friendly string keys like "social", "work", "entertainment"
   - More flexible for configuration files and user interfaces

3. **Mapping layer** (CATEGORY_TO_ENUM_MAPPING):
   - Bridges the two systems by mapping user-friendly strings to enum values
   - Allows the system to accept human-readable categories but work with type-safe enums internally

This separation of concerns enables both user-friendly configuration and robust internal processing.
