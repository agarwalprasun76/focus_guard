# Focus Guard Extension Deployment - Directory Reorganization Plan

## Current Problem
The extension deployment system has become cluttered with scattered files across multiple directories, making it difficult to maintain and understand the codebase structure.

## Current Structure Analysis

**Existing Well-Organized Areas:**
- `focus_guard/core/browser/extension/` - Core implementation ✅
- `focus_guard/tests/core/browser/` - Test structure ✅  
- `installer/` - Platform-specific installers ✅

**Problem Areas:**
- Root directory cluttered with test files
- `scripts/` mixed deployment, dev tools, and tests
- `build/crx/` isolated from deployment workflow

## Revised Directory Structure (Respecting Existing Organization)

```
focus_guard/
├── focus_guard/                               # Core package (keep as-is)
│   ├── core/browser/extension/                # ✅ Core implementation
│   │   ├── robust_installer.py               
│   │   ├── windows_admin_utils.py             
│   │   ├── installer.py                      
│   │   ├── manager.py                        
│   │   └── webextension_mv3/                 
│   └── tests/core/browser/                    # ✅ Existing test structure
│       └── integration/                       # Keep existing pattern
│
├── installer/                                 # ✅ Keep existing (platform installers)
│   ├── win/                                  
│   └── mac/                                  
│
├── deployment/                                # NEW: Extension deployment only
│   ├── crx/                                  # Move from build/crx/
│   │   ├── FocusGuard_v1.0.0.crx            
│   │   ├── updates.xml                       
│   │   └── deploy_extension.ps1              
│   ├── scripts/                              # Deployment automation
│   │   ├── build_crx.py                      # From scripts/build_crx_extension.py
│   │   ├── enterprise_deploy.py              # From scripts/complete_crx_setup.py
│   │   └── developer_deploy.py               # From scripts/load_extension_edge.py
│   └── config/                               
│       └── extension_config.json             # Centralized config
│
├── scripts/                                  # CLEANED: Dev tools only
│   ├── dev/                                  # ✅ Keep existing dev tools
│   ├── demo/                                 # ✅ Keep existing demos
│   └── integration_tests/                    # ✅ Keep existing integration tests
│
└── tools/                                    # NEW: Testing and debug utilities
    ├── extension/                            # Extension-specific tools
    │   ├── check_edge_extensions.py          # From root
    │   ├── get_extension_id.py               # From scripts/
    │   └── verify_installation.py            # From root tests
    └── testing/                              # Manual test scripts
        ├── test_robust_installation.py       # From root
        ├── test_edge_installation.py         # From root
        └── test_admin_functionality.py       # From root
```

## File Migration Plan

### Phase 1: Create New Directory Structure
- Create `deployment/`, `tools/`, organized subdirectories
- Set up proper configuration files

### Phase 2: Move Extension Deployment Files
**Create `deployment/crx/` (from `build/crx/`):**
- `build/crx/FocusGuard_v1.0.0.crx` → `deployment/crx/`
- `build/crx/updates.xml` → `deployment/crx/`
- `build/crx/deploy_extension.ps1` → `deployment/crx/`
- `build/crx/key.pem` → `deployment/crx/`
- `build/crx/extension_id.txt` → `deployment/config/extension_config.json`

**Create `deployment/scripts/` (from `scripts/`):**
- `scripts/build_crx_extension.py` → `deployment/scripts/build_crx.py`
- `scripts/complete_crx_setup.py` → `deployment/scripts/enterprise_deploy.py`
- `scripts/load_extension_edge.py` → `deployment/scripts/developer_deploy.py`
- `scripts/install_edge_policy.ps1` → `deployment/scripts/`
- `scripts/configure_edge_policy.py` → `deployment/scripts/`

### Phase 3: Move Testing and Debug Tools
**Create `tools/extension/` (extension-specific utilities):**
- `check_edge_extensions.py` → `tools/extension/`
- `check_edge_extensions_simple.py` → `tools/extension/`
- `scripts/get_extension_id.py` → `tools/extension/`
- `install_edge_extension_manual.py` → `tools/extension/`

**Create `tools/testing/` (manual test scripts):**
- `test_robust_extension_installation.py` → `tools/testing/`
- `test_actual_functionality.py` → `tools/testing/`
- `test_admin_functionality.py` → `tools/testing/`
- `test_edge_installation.py` → `tools/testing/`
- `test_real_installation.py` → `tools/testing/`

### Phase 4: Clean Scripts Directory
**Keep in `scripts/` (core dev tools):**
- `scripts/dev/` - ✅ Development utilities
- `scripts/demo/` - ✅ Demo scripts
- `scripts/integration_tests/` - ✅ Integration tests
- `scripts/focus_guard/` - ✅ Focus Guard specific tools

**Remove extension-specific files from `scripts/`:**
- Extension deployment scripts → moved to `deployment/`
- Extension testing scripts → moved to `tools/`
- Extension debug utilities → moved to `tools/`

### Phase 5: Clean Root Directory
**Remove from root:**
- `test_*.py` files → moved to `tools/testing/`
- `check_*.py` files → moved to `tools/extension/`
- `install_*.py` files → moved to `tools/extension/`
- Obsolete batch files

## Alignment with Existing Structure

**Respects Current Organization:**
- ✅ `focus_guard/core/browser/extension/` - Core implementation stays
- ✅ `focus_guard/tests/core/browser/` - Formal test structure stays
- ✅ `installer/win/`, `installer/mac/` - Platform installers stay
- ✅ `scripts/dev/`, `scripts/demo/` - Development tools stay

**Improves Problem Areas:**
- 🔧 Root directory clutter → moved to `tools/`
- 🔧 Mixed `scripts/` → separated deployment vs dev tools
- 🔧 Isolated `build/crx/` → integrated into `deployment/`

## Benefits
1. **Consistent with Existing** - Follows established patterns
2. **Clear Separation** - Extension deployment vs core development
3. **Easy Navigation** - Logical grouping by purpose
4. **Maintainable** - Single responsibility per directory
5. **Scalable** - Easy to add new deployment methods

## Implementation Priority
1. **High**: Create `deployment/` structure and move CRX files
2. **High**: Move extension-specific scripts from `scripts/`
3. **Medium**: Move test files from root to `tools/testing/`
4. **Medium**: Clean up root directory
5. **Low**: Create unified entry points
