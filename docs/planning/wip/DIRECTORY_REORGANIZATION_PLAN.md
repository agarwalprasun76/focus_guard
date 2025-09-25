# Directory Reorganization Plan

## Current Issues

1. **Mixed Old and New Code**: Both `core` and `core_v2` directories exist
2. **Demo Clutter**: Multiple demo directories with overlapping purposes
3. **Build Artifacts**: Build, dist, and cache directories in root
4. **Configuration Files**: Scattered across multiple locations
5. **Test Organization**: Tests are not consistently organized

## Proposed Structure

```
focus_guard/
├── .github/                  # GitHub workflows and templates
├── build/                    # Build artifacts (gitignored)
├── dist/                     # Distribution packages (gitignored)
├── docs/                     # Documentation
│   ├── api/                  # API documentation
│   ├── guides/               # User guides
│   └── images/               # Documentation images
├── focus_guard/              # Main package
│   ├── __init__.py
│   ├── core/                 # Core functionality (from core_v2)
│   │   ├── activity/         # Activity monitoring
│   │   ├── alert/            # Alert system
│   │   ├── browser/          # Browser integration
│   │   ├── classification/   # Content classification
│   │   ├── config/           # Configuration management
│   │   ├── coordinator/      # Component coordination
│   │   ├── distraction/      # Distraction detection
│   │   └── utils/            # Shared utilities
│   ├── api/                  # API endpoints
│   ├── cli/                  # Command line interface
│   ├── gui/                  # Graphical user interface
│   └── tests/                # Unit and integration tests
│       ├── unit/             # Unit tests
│       └── integration/      # Integration tests
├── scripts/                  # Utility scripts
│   ├── dev/                  # Development tools
│   ├── setup/                # Setup and installation
│   └── tools/                # Other utilities
├── .gitignore
├── pyproject.toml            # Build configuration
├── README.md                 # Project documentation
└── requirements/             # Dependency specifications
    ├── base.txt              # Core dependencies
    ├── dev.txt               # Development dependencies
    └── test.txt              # Testing dependencies
```

## Migration Steps

### 1. Archive Old Code

1. Create an `archive/` directory for old code:
   ```
   mkdir -p archive/legacy_code/{core,demos,examples}
   ```

2. Move old core code:
   ```
   mv core/* archive/legacy_code/core/
   mv demos/* archive/legacy_code/demos/
   mv examples/* archive/legacy_code/examples/
   ```

### 2. Reorganize Core Functionality

1. Move `core_v2` to `focus_guard/core`:
   ```
   mkdir -p focus_guard
   mv core_v2/* focus_guard/core/
   ```

2. Move tests to the new structure:
   ```
   mkdir -p focus_guard/tests/{unit,integration}
   mv tests/core_v2/* focus_guard/tests/unit/
   ```

### 3. Clean Up Configuration

1. Move configuration files:
   ```
   mkdir -p focus_guard/config
   mv config/*.y*ml focus_guard/config/
   mv config/*.json focus_guard/config/
   ```

2. Update configuration paths in the codebase

### 4. Set Up Build System

1. Move build-related files:
   ```
   mkdir -p scripts/build
   mv setup.py scripts/build/
   mv *.spec scripts/build/
   ```

### 5. Update Imports and References

1. Update Python imports to reflect new structure
2. Update test paths and imports
3. Update documentation references

## Verification Steps

1. Run all tests to ensure nothing is broken
2. Verify imports in all Python files
3. Check that documentation builds correctly
4. Verify that the package can be built and installed

## Cleanup

After verification:
1. Remove empty directories
2. Update `.gitignore`
3. Commit the new structure

## Rollback Plan

If issues arise:
1. Revert to the previous commit
2. Restore from backup if needed
3. Document the issues encountered

## Timeline

- **Day 1**: Set up new structure and move files
- **Day 2**: Update imports and references
- **Day 3**: Testing and verification
- **Day 4**: Cleanup and documentation

## Notes

- Keep the `archive/` directory in version control for reference
- Update CI/CD pipelines to match the new structure
- Notify all team members of the new structure
- Update any documentation that references old paths
