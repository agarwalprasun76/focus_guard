# Focus Guard Deployment

This directory contains all packaging and deployment files for the Focus Guard application and browser extension.

## Directory Structure

```
deployment/
├── application/            # Application packaging and distribution
│   ├── windows/
│   │   ├── specs/         # PyInstaller spec files
│   │   ├── scripts/       # Build scripts
│   │   ├── installers/    # Inno Setup files
│   │   └── version_info.txt
│   ├── mac/
│   │   ├── specs/
│   │   └── scripts/
│   ├── build/             # Build artifacts
│   ├── dist/              # Distribution files
│   ├── requirements/      # Packaging requirements
│   └── README.md
├── extension/             # Browser extension deployment
│   ├── crx/              # CRX packages and signing
│   ├── enterprise/       # Enterprise deployment scripts
│   ├── developer/        # Developer mode deployment
│   ├── scripts/          # Extension build scripts
│   └── native_host/      # Native host configurations
├── installer/            # End-user installers
│   ├── windows/          # Windows installers and batch files
│   ├── mac/              # Mac installation scripts
│   └── scripts/          # Cross-platform installer scripts
├── config/               # Deployment configurations
└── tools/                # Deployment utilities and testing
```

## Quick Start

### Application Packaging
```bash
# Build Windows executable
python deployment/application/windows/scripts/build_exe.py

# Create installer
# Use Inno Setup with deployment/application/windows/installers/*.iss
```

### Extension Deployment
```bash
# Developer mode
python deployment/extension/developer/developer_deploy.py

# Enterprise deployment
python deployment/extension/enterprise/enterprise_deploy.py

# Build CRX package
python deployment/extension/scripts/build_crx.py
```

### End-User Installation
```bash
# Windows installation
deployment/installer/windows/install_focus_guard.bat

# Extension installation
deployment/installer/scripts/install_extension_automated.py
```

## Key Components

### Application Packaging
- **PyInstaller specs**: Windows and Mac executable configurations
- **Build scripts**: Automated packaging workflows
- **Inno Setup**: Windows installer creation
- **Distribution files**: Ready-to-deploy executables

### Extension Deployment
- **CRX packages**: Signed extension packages
- **Enterprise policies**: Registry-based deployment
- **Developer tools**: Development and testing utilities
- **Native host**: Browser-application communication

### Installation Tools
- **Batch installers**: One-click Windows installation
- **Cross-platform scripts**: Python-based installation automation
- **Testing utilities**: VM creation and deployment verification

## Extension Details
- **Extension ID (Chrome)**: hnpfnmlcmdhkbhnfifmnonehebeafclp
- **Extension ID (Edge)**: legaalcjhhgofgpgbbpoadafdjllckgg
- **Version**: 1.0.1
- **Manifest**: v3

See individual component README files for detailed usage instructions.
