# Focus Guard Admin Console User Guide

## Quick Start

### Accessing the Admin Console

1. **Make sure FocusGuard is running** - You should see the FocusGuard icon in your system tray (bottom-right corner of Windows)

2. **Open the Admin Dashboard**:
   - Right-click the FocusGuard tray icon
   - Select "Admin Dashboard" from the menu
   - OR open your browser and go to: `http://127.0.0.1:58393/admin`

3. **Login**:
   - Default credentials: 
     - Username: `admin`
     - Password: (check your first-run wizard setup or deployment config)
   - If you forgot the password, check the `deployment_config.json` file in `C:\ProgramData\FocusGuard\`

## Dashboard Overview

### Main Sections

#### 1. **Dashboard Tab** - Main Overview
- **Device Status**: Shows if FocusGuard is running and connected
- **Today's Activity**: Active time, sessions, focus score
- **Blocked Sites**: List of sites blocked today with counts
- **Budget Usage**: How much time has been used vs. limits

#### 2. **Exceptions Tab** - Manage Overrides
- **Create Exception**: Grant temporary access to blocked sites
- **View Active Exceptions**: See all current overrides
- **Revoke Exceptions**: Cancel active overrides early

#### 3. **Devices Tab** - Monitor Connected Devices
- **Device List**: All browsers/devices running FocusGuard
- **Connection Status**: Online/offline status
- **Last Seen**: When each device was active

#### 4. **Settings Tab** - Configuration
- **Enforcement Modes**: 
  - *Tracking*: Monitor only (no blocking)
  - *Advisory*: Block with easy override
  - *Enforcing*: Strict blocking with penalties
- **Time Limits**: Set daily time limits for categories
- **Email Reports**: Configure hourly/daily email summaries

## Common Tasks

### Checking What's Been Blocked
1. Go to Dashboard tab
2. Look at "Blocked Sites Today" section
3. Click on any site to see details

### Allowing Temporary Access (Override)
1. Go to Exceptions tab
2. Click "Create Exception"
3. Enter the URL/website
4. Set duration (5-60 minutes)
5. Add reason (optional)
6. Click "Create Exception"

### Viewing Saved Links
1. Go to Dashboard tab
2. Look for "Saved Links" section
3. Click "View All Saved Links" to see full list

### Changing Blocking Strictness
1. Go to Settings tab
2. Select "Enforcement Mode"
3. Choose your preferred level
4. Enter enforcement password if prompted
5. Click "Update Settings"

### Setting Up Email Reports
1. Go to Settings tab
2. Expand "Email Configuration"
3. Enter SMTP settings (Gmail recommended)
4. Set report frequency (hourly/daily)
5. Test configuration with "Send Test Email"

## Troubleshooting

### Can't Access Admin Dashboard
- **Check if FocusGuard is running**: Look for tray icon
- **Check the port**: Make sure nothing is blocking port 58393
- **Try restarting**: Right-click tray icon → Exit, then restart FocusGuard

### Login Issues
- **Default password**: Check your first-run wizard setup
- **Reset password**: Edit `deployment_config.json` in `C:\ProgramData\FocusGuard\`
- **Check enforcement password**: Some changes require the enforcement password

### No Data Showing
- **Check browser extension**: Make sure it's installed and connected
- **Check activity tracking**: Look in Settings tab under "Monitoring"
- **Wait a few minutes**: Data updates every 30-60 seconds

### Extension Not Working
- **Chrome**: Install from https://chromewebstore.google.com/detail/focusguard-productivity-t/hnpfnmlcmdhkbhnfifmnonehebeafclp
- **Edge**: Install from https://microsoftedge.microsoft.com/addons/detail/focusguard-productivity/legaalcjhhgofgpgbbpoadafdjllckgg
- **Check connection**: Extension popup should show "Connected" status

## Quick Reference

### Important URLs
- **Admin Dashboard**: `http://127.0.0.1:58393/admin`
- **Tab Server API**: `http://127.0.0.1:58392/api/health`
- **Chrome Extension**: Chrome Web Store (search "FocusGuard")
- **Edge Extension**: Edge Add-ons (search "FocusGuard")

### Configuration Files Location
- **Main Config**: `C:\ProgramData\FocusGuard\deployment_config.json`
- **Domain Rules**: `C:\ProgramData\FocusGuard\domain_config.json`
- **User Settings**: `C:\ProgramData\FocusGuard\users\default.json`
- **Logs**: `C:\ProgramData\FocusGuard\logs\`

### Common Ports
- **Admin Gateway**: 58393 (web dashboard)
- **Tab Server**: 58392 (browser extension API)

### Getting Help
1. Check the logs in `C:\ProgramData\FocusGuard\logs\`
2. Restart FocusGuard from the tray menu
3. Check that browser extensions are installed and connected
4. Verify no other software is blocking ports 58392-58393

---

**Last Updated**: February 21, 2026  
**Version**: FocusGuard v1.0.0
