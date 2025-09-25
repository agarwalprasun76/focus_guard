# Extension Deployment Workflow

This document outlines the complete workflow for deploying Focus Guard browser extensions.

## Prerequisites

1. **Chrome/Edge Browser** for testing
2. **Python 3.7+** for automation scripts
3. **Administrative privileges** for enterprise deployment
4. **Signing key** (provided in `deployment/extension/crx/key.pem`)

## Deployment Methods

### 1. Developer Mode (Testing)

```bash
# From project root
python deployment/extension/developer/developer_deploy.py
```

This will:
- Load unpacked extension in developer mode
- Enable extension for testing
- Provide extension ID for configuration

### 2. Enterprise Policy Deployment

```bash
# Configure Edge policy
python deployment/extension/enterprise/configure_edge_policy.py

# Install policy via PowerShell (as Administrator)
powershell deployment/extension/enterprise/install_edge_policy.ps1

# Alternative: Manual policy setup
python deployment/extension/enterprise/create_edge_policy_manual.py
```

### 3. CRX Package Deployment

```bash
# Build CRX package
python deployment/extension/scripts/build_crx.py

# Deploy CRX (enterprise)
python deployment/extension/enterprise/enterprise_deploy.py
```

## File Structure

- **CRX Package**: `deployment/extension/crx/FocusGuard_v1.0.0.crx`
- **Signing Key**: `deployment/extension/crx/key.pem`
- **Update Manifest**: `deployment/extension/crx/updates.xml`
- **Extension ID**: `deployment/extension/crx/extension_id.txt`

## Extension Details

- **Extension ID**: `hmjfbkppeejdnekjapejicmfhfogocjo`
- **Version**: `1.0.0`
- **Manifest Version**: `3`
- **Permissions**: `tabs`, `storage`, `nativeMessaging`

## Deployment Workflows

### Development Workflow
1. Make changes to extension source in `focus_guard/core/browser/extension/webextension_mv3/`
2. Run `python deployment/extension/developer/developer_deploy.py`
3. Test in browser developer mode
4. Reload extension after changes

### Production Workflow
1. Build CRX package: `python deployment/extension/scripts/build_crx.py`
2. Test CRX installation manually
3. Deploy via enterprise policy or distribution

### Enterprise Workflow
1. Configure group policy: `python deployment/extension/enterprise/configure_edge_policy.py`
2. Deploy policy: `powershell deployment/extension/enterprise/install_edge_policy.ps1`
3. Verify installation across organization

## Troubleshooting

### Extension Not Loading
- Check manifest.json syntax
- Verify permissions in browser
- Check browser console for errors

### Policy Deployment Issues
- Ensure administrative privileges
- Check Windows Registry entries
- Verify policy template installation

### CRX Package Problems
- Verify signing key is present
- Check CRX file integrity
- Ensure proper file permissions

## Security Notes

- Keep `key.pem` secure - it's used for signing
- Extension ID is derived from the public key
- CRX packages are signed and verified by browsers
- Enterprise policies require administrative deployment
