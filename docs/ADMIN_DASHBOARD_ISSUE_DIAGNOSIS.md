# Admin Dashboard Access Issue - Diagnosis & Solution

## Problem Identified
The admin dashboard at `http://127.0.0.1:58393/admin` returns "Not Found" even though:
- Admin gateway is running (port 58393 listening)
- API endpoints work (`/admin/api/v1/meta` returns 200)
- Admin UI built successfully (assets exist)

## Root Cause
The admin gateway loads the UI directory at startup, but the UI was built **after** the service started. The gateway needs to be restarted to pick up the new UI files.

## Immediate Solutions

### Option 1: Restart FocusGuard (Recommended)
1. Right-click FocusGuard tray icon
2. Select "Exit"
3. Restart FocusGuard from the desktop shortcut or `FocusGuard.exe`

### Option 2: Access UI Directly (Temporary)
Open the UI file directly in browser:
```
file:///C:/Users/prasun_agarwal/focus_guard/admin_ui/dist/index.html
```
*Note: API calls will fail due to CORS, but you can see the UI*

### Option 3: Manual Service Restart
```powershell
# Stop FocusGuard
Get-Process | Where-Object {$_.ProcessName -like "*focus*"} | Stop-Process

# Restart FocusGuard
cd "C:\Users\prasun_agarwal\focus_guard\dist"
.\FocusGuard.exe
```

## Verification Steps
After restarting:
1. Visit `http://127.0.0.1:58393/admin`
2. Should see the admin login page
3. Login with credentials from deployment config

## Admin Login Credentials
The admin password is stored in `C:\ProgramData\FocusGuard\deployment_config.json` under `config_password_hash`. 
You'll need to use the password you set during the first-run wizard, or try common defaults like "admin".

## Long-term Fix
The admin gateway should watch for UI file changes or have a reload endpoint to avoid requiring full service restarts during development.

---

**Status**: Issue diagnosed, solution provided  
**Next Action**: Restart FocusGuard service
