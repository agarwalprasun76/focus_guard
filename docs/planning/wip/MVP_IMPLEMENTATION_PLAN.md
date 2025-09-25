# Focus Guard MVP Implementation Plan - UPDATED

## 🎯 Objective

Create a minimal viable product (MVP) that demonstrates end-to-end functionality with the bare minimum components needed for:
1. Domain classification
2. Browser tab monitoring
3. Basic blocking decisions
4. Simple user interface
5. Packaging and distribution

## 📋 Current State Assessment (UPDATED)

### ✅ What's Already Working (Extensively Implemented)
- **✅ FULL Coordinator System**: Complete `FocusGuardCoordinator` with lifecycle management, event bus, component registration
- **✅ FULL Core API**: `ClassifierBlockerAPI` with domain classification and blocking pipeline
- **✅ FULL Classification System**: YouTube classifier with rule-based classification (74+ tests passing)
- **✅ FULL Blocking Strategies**: Domain excluder and category blocker strategies with priority system
- **✅ FULL Browser Integration**: `BrowserIntegration` class with tab server communication and retry logic
- **✅ FULL Extension System**: `BrowserExtensionManager`, `ExtensionInstaller`, `TabServer` (singleton pattern)
- **✅ FULL Configuration System**: Multi-provider configuration with JSON support, schema validation
- **✅ FULL Component System**: All components wrapped for coordinator (Activity, Browser, Classification, Distraction, Alert, API)
- **✅ FULL Caching**: Memory cache with TTL support and cleanup
- **✅ FULL CLI Framework**: Cross-platform CLI with Windows implementation
- **✅ EXISTING Config Files**: `app_config.json`, `focus_guard_config.json` with distraction categories
- **✅ EXISTING Demo Scripts**: Multiple demo scripts in `scripts/demo/` and `UNUSED/archive/demos/`

### ❌ What's Missing for MVP (Much Less Than Expected!)

#### Critical Missing Components:
1. **Simple Entry Point**: A single script that starts everything
2. **Extension Auto-Installation**: Connect existing installer to startup flow
3. **Default Configuration Loading**: Use existing configs by default
4. **Integration Glue**: Connect coordinator components to API

#### Minor Missing Components:
1. **MVP Demo Script**: Simple demonstration script
2. **Installation Script**: Automated setup script

## 🚀 REVISED MVP Implementation Tasks

### Phase 1: Integration Glue (1 day)

#### Task 1.1: Create MVP Entry Point ⭐ NEW PRIORITY
**Priority**: P0 - Critical
**Effort**: 4 hours
**Status**: ✅ COORDINATOR EXISTS - Just needs entry point

**What Exists**:
- Complete `FocusGuardCoordinator` class with all lifecycle management
- All component wrappers (ActivityMonitorComponent, BrowserIntegrationComponent, etc.)
- Configuration manager with JSON providers

**What's Needed**:
```python
# focus_guard/core/mvp_main.py
import asyncio
from focus_guard.core.config.manager import DefaultConfigurationManager
from focus_guard.core.coordinator.focus_guard_coordinator import FocusGuardCoordinator

async def main():
    """MVP main entry point using existing coordinator."""
    # Use existing configuration manager
    config_manager = DefaultConfigurationManager()
    
    # Use existing full coordinator (no need for simplified version!)
    coordinator = FocusGuardCoordinator(config_manager)
    
    try:
        # Initialize and start (all methods exist)
        if await coordinator.initialize():
            if await coordinator.start():
                print("Focus Guard MVP is running...")
                while True:
                    await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        await coordinator.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
```

**Files to Create**:
- `focus_guard/core/mvp_main.py` (NEW - 50 lines)

#### Task 1.2: Fix Component Integration ⭐ REDUCED SCOPE
**Priority**: P0 - Critical
**Effort**: 4 hours
**Status**: ✅ COMPONENTS EXIST - Just need connection verification

**What Exists**:
- `BrowserIntegrationComponent` wrapper
- `ClassificationComponent` wrapper  
- `ApiServerComponent` wrapper
- All components registered in coordinator

**What's Needed**:
- Verify component integration works
- Fix any import issues
- Ensure API is accessible through coordinator

**Files to Check/Fix**:
- `focus_guard/core/coordinator/components/api.py` (verify API integration)
- `focus_guard/core/coordinator/components/browser.py` (verify browser integration)

### Phase 2: Extension Auto-Setup (0.5 days)

#### Task 2.1: Auto-Install Extension on Startup ⭐ MOSTLY EXISTS
**Priority**: P1 - High
**Effort**: 2 hours
**Status**: ✅ INSTALLER EXISTS - Just needs startup integration

**What Exists**:
- Complete `ExtensionInstaller` class
- `BrowserExtensionManager` with installation methods
- Tab server with automatic startup

**What's Needed**:
```python
# Add to mvp_main.py startup sequence
installer = ExtensionInstaller()
if not installer.is_extension_installed():
    print("Installing browser extension...")
    installer.install_for_detected_browsers()
```

**Files to Modify**:
- `focus_guard/core/mvp_main.py` (add extension check)

### Phase 3: Configuration & Demo (0.5 days)

#### Task 3.1: Use Existing Configuration ⭐ ALREADY EXISTS
**Priority**: P1 - High
**Effort**: 1 hour
**Status**: ✅ CONFIGS EXIST - Just need to use them

**What Exists**:
- `config/app_config.json` with distraction categories
- `config/focus_guard_config.json` with full settings
- Configuration loader system

**What's Needed**:
- Point MVP to use existing config files
- Verify default settings work

**Files to Modify**:
- `focus_guard/core/mvp_main.py` (specify config path)

#### Task 3.2: Create Simple Demo Script ⭐ NEW
**Priority**: P1 - High  
**Effort**: 2 hours

**What's Needed**:
```python
# demo_mvp.py
"""Simple MVP demonstration script."""
import asyncio
from focus_guard.core.api.api import ClassifierBlockerAPI

async def demo():
    print("=== Focus Guard MVP Demo ===")
    
    # Test API directly (exists and works)
    api = ClassifierBlockerAPI()
    
    # Test classification
    result = api.classify_domain("youtube.com")
    print(f"youtube.com classified as: {result}")
    
    # Test blocking decision  
    should_block = api.should_block_tab("https://youtube.com/watch?v=123")
    print(f"Should block YouTube: {should_block}")
    
    print("Starting full coordinator...")
    # Import and run mvp_main
    from focus_guard.core.mvp_main import main
    await main()

if __name__ == "__main__":
    asyncio.run(demo())
```

**Files to Create**:
- `demo_mvp.py` (NEW - 30 lines)

### Phase 4: Packaging (Already Mostly Done)

#### Task 4.1: Installation Script ⭐ MINIMAL NEEDED
**Priority**: P2 - Medium
**Effort**: 1 hour

**What Exists**:
- `setup.py` and `pyproject.toml`
- Requirements files
- CLI entry points

**What's Needed**:
```bash
# install_mvp.bat
@echo off
echo Installing Focus Guard MVP...
pip install -e .
echo Running MVP demo...
python demo_mvp.py
```

**Files to Create**:
- `install_mvp.bat` (NEW - 5 lines)

## 📊 REVISED Timeline

**Total Estimated Time**: 1.5 days (down from 5-6 days!)

- **Day 1 Morning**: Create MVP entry point (4 hours)
- **Day 1 Afternoon**: Fix component integration (4 hours)  
- **Day 2 Morning**: Extension auto-setup (2 hours)
- **Day 2 Afternoon**: Demo script and installation (3 hours)

## 🎯 REVISED Success Criteria

### Functional Requirements (All Components Exist!)
- ✅ Classify domains → `ClassifierBlockerAPI.classify_domain()` EXISTS
- ✅ Make blocking decisions → `ClassifierBlockerAPI.should_block_tab()` EXISTS  
- ✅ Monitor browser tabs → `BrowserIntegration` + `TabServer` EXISTS
- ✅ Extension communication → `BrowserExtensionManager` EXISTS
- ✅ Package and install → `setup.py` EXISTS

### What We Actually Need to Build
- 🔨 1 entry point script (`mvp_main.py`)
- 🔨 1 demo script (`demo_mvp.py`)  
- 🔨 1 installation script (`install_mvp.bat`)
- 🔨 Minor integration fixes

## 🚀 Key Insight

**The MVP is 90% already built!** We have a complete, tested system with:
- Full coordinator with lifecycle management
- Complete API with classification and blocking
- Browser integration with extension support
- Configuration system with existing configs
- All components wrapped and ready

We just need to create simple entry points and connect the pieces that are already there.

#### Task 1.2: Create MVP Entry Point
**Priority**: P0 - Critical  
**Effort**: 0.5 days

**Implementation**:
```python
# focus_guard/core/mvp_main.py
async def main():
    """MVP main entry point."""
    coordinator = MVPCoordinator()
    
    try:
        await coordinator.start()
        print("Focus Guard MVP is running...")
        
        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        await coordinator.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

**Files to Create**:
- `focus_guard/core/mvp_main.py`

#### Task 1.3: Fix Browser Integration
**Priority**: P0 - Critical
**Effort**: 1 day

**Current Issue**: Browser integration exists but needs to be connected to the API.

**Implementation**:
- Ensure `BrowserIntegration` class works with current API
- Fix any import issues or missing dependencies
- Add simple tab monitoring that calls the classification API

**Files to Modify**:
- `focus_guard/core/browser/integration/browser_integration.py`

### Phase 2: Extension Setup (1-2 days)

#### Task 2.1: Automated Extension Installation
**Priority**: P1 - High
**Effort**: 1 day

**Implementation**:
- Create simple extension installer that works for Chrome/Edge
- Add verification that extension is properly installed
- Include extension files in package

**Files to Create/Modify**:
- `focus_guard/core/browser/extension/mvp_installer.py` (new)
- Update existing extension files for MVP compatibility

#### Task 2.2: Tab Server Auto-Start
**Priority**: P1 - High
**Effort**: 0.5 days

**Implementation**:
- Ensure tab server starts automatically with MVP
- Add retry logic for server startup
- Include proper error handling

**Files to Modify**:
- `focus_guard/core/browser/extension/tab_server.py`

### Phase 3: Configuration & Demo (1 day)

#### Task 3.1: Default Configuration
**Priority**: P1 - High
**Effort**: 0.5 days

**Implementation**:
```json
{
  "classification": {
    "cache_ttl_seconds": 3600,
    "enabled_classifiers": ["youtube_rules"]
  },
  "blocking": {
    "enabled_strategies": ["category_blocker"],
    "blocked_categories": ["SOCIAL_MEDIA", "ENTERTAINMENT"]
  },
  "browser": {
    "tab_server_port": 5000,
    "auto_start_server": true
  }
}
```

**Files to Create**:
- `focus_guard/core/config/mvp_defaults.json`

#### Task 3.2: Demo Script
**Priority**: P1 - High
**Effort**: 0.5 days

**Implementation**:
```python
# demo_mvp.py
"""
Simple demo script that shows Focus Guard MVP functionality.
"""
async def demo():
    print("=== Focus Guard MVP Demo ===")
    
    # Test classification
    api = ClassifierBlockerAPI()
    result = api.classify_domain("youtube.com")
    print(f"youtube.com classified as: {result}")
    
    # Test blocking decision
    should_block = api.should_block_tab("https://youtube.com/watch?v=123")
    print(f"Should block YouTube: {should_block}")
    
    # Start coordinator
    coordinator = MVPCoordinator()
    await coordinator.start()
    
    print("MVP is running. Press Ctrl+C to stop.")
    
if __name__ == "__main__":
    asyncio.run(demo())
```

**Files to Create**:
- `demo_mvp.py` (in project root)

### Phase 4: Packaging (1 day)

#### Task 4.1: Setup.py and Requirements
**Priority**: P1 - High
**Effort**: 0.5 days

**Implementation**:
- Update `setup.py` with MVP entry points
- Ensure all dependencies are listed
- Add console script for easy execution

**Files to Modify**:
- `setup.py`
- `requirements.txt`

#### Task 4.2: Installation Script
**Priority**: P1 - High
**Effort**: 0.5 days

**Implementation**:
```bash
# install_mvp.bat (Windows)
@echo off
echo Installing Focus Guard MVP...
pip install -e .
echo Installing browser extension...
python -m focus_guard.core.browser.extension.mvp_installer
echo MVP installation complete!
echo Run: python demo_mvp.py
```

**Files to Create**:
- `install_mvp.bat` (Windows)
- `install_mvp.sh` (Linux/Mac)

## 🧪 MVP Testing Strategy

### Manual Testing Checklist
- [ ] Classification API works for common domains
- [ ] Browser extension installs successfully
- [ ] Tab server starts and communicates with extension
- [ ] Blocking decisions are made correctly
- [ ] Demo script runs without errors
- [ ] Package installs cleanly

### Automated Testing
- [ ] Unit tests for MVP coordinator
- [ ] Integration test for end-to-end flow
- [ ] Browser extension communication test

## 📦 MVP Deliverables

1. **Working Demo**: `demo_mvp.py` that shows classification and blocking
2. **Installable Package**: Can be installed via `pip install -e .`
3. **Browser Extension**: Automatically installs and connects
4. **Documentation**: Simple README with setup instructions
5. **Configuration**: Default settings that work out of the box

## 🎯 Success Criteria

### Functional Requirements
- ✅ Classify domains (at least YouTube)
- ✅ Make blocking decisions based on categories
- ✅ Monitor browser tabs in real-time
- ✅ Communicate between extension and application
- ✅ Package and install cleanly

### Performance Requirements
- Classification response time: < 100ms
- Tab monitoring latency: < 500ms
- Memory usage: < 100MB
- Startup time: < 10 seconds

### User Experience Requirements
- One-command installation
- Automatic extension setup
- Clear demo of functionality
- Simple configuration

## 🔧 Technical Constraints

### MVP Limitations (Acceptable for Demo)
- **Single Browser Support**: Chrome/Edge only
- **Basic Classification**: Rule-based only (no LLM)
- **Simple Blocking**: Category-based only
- **No Persistence**: Settings don't persist between runs
- **No GUI**: Command-line interface only
- **Windows Only**: Focus on Windows platform first

### Architecture Decisions
- Use existing `ClassifierBlockerAPI` as core
- Minimal coordinator for MVP
- File-based configuration
- In-memory caching only
- Direct browser extension communication

## 🚀 Post-MVP Migration Path

The MVP is designed to be easily extensible to the full implementation:

1. **Coordinator**: MVP coordinator can be replaced with full `FocusGuardCoordinator`
2. **Classification**: Additional classifiers can be registered
3. **Blocking**: More sophisticated blocking strategies can be added
4. **Configuration**: Can be enhanced with advanced features
5. **UI**: GUI can be added without changing core logic
6. **Cross-Platform**: Other platforms can be added incrementally

## 📅 Timeline

**Total Estimated Time**: 5-6 days

- **Day 1**: Core integration and coordinator
- **Day 2**: Browser integration fixes
- **Day 3**: Extension installation and tab server
- **Day 4**: Configuration and demo script
- **Day 5**: Packaging and testing
- **Day 6**: Documentation and polish

## 🎉 MVP Demonstration Flow

1. **Installation**: `install_mvp.bat`
2. **Demo**: `python demo_mvp.py`
3. **Browser Test**: Open YouTube, see classification
4. **Blocking Test**: Configure blocking, see tabs close
5. **Monitoring**: Watch real-time tab monitoring

This MVP provides a solid foundation that demonstrates all core functionality while being simple enough to implement quickly and package easily.
