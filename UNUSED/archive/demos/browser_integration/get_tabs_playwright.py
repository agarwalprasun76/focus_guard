import asyncio
from playwright.async_api import async_playwright
from typing import List, Dict, Any, Optional
import platform
import json
from datetime import datetime
import os
import psutil
import re
import sys
import win32gui
import win32process
import win32api
import win32con
import win32ui
import win32gui_struct
from pathlib import Path

# Set console output encoding to UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Constants for Windows API
GWL_STYLE = -16
WS_VISIBLE = 0x10000000
WS_BORDER = 0x00800000
WS_DLGFRAME = 0x00400000
WS_THICKFRAME = 0x00040000
WS_CAPTION = WS_BORDER | WS_DLGFRAME
WS_TABSTOP = 0x00010000
WS_CHILD = 0x40000000
WS_EX_APPWINDOW = 0x00040000
WS_EX_TOOLWINDOW = 0x00000080

# Configuration
DEBUG = True
BROWSER_PATHS = {
    'win32': {
        'chrome': [
            r'C:\Program Files\Google\Chrome\Application\chrome.exe',
            r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
            os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe')
        ],
        'msedge': [
            r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
            r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
            os.path.expandvars(r'%PROGRAMFILES(X86)%\Microsoft\Edge\Application\msedge.exe')
        ]
    },
    'darwin': {
        'chrome': [
            '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
            '~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
        ],
        'msedge': [
            '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
            '~/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge'
        ]
    }
}

def find_browser_path(browser_name):
    """Find the first valid browser path."""
    system = platform.system().lower()
    if system not in BROWSER_PATHS:
        return None
        
    paths = BROWSER_PATHS[system].get(browser_name, [])
    for path in paths:
        path = os.path.expanduser(path)  # Handle ~ in paths
        if os.path.exists(path):
            if DEBUG:
                print(f"Found {browser_name} at: {path}")
            return path
    return None

async def get_browser_tabs(browser_type, headless=False, executable_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get all open tabs from a browser using Playwright."""
    browser = None
    try:
        # Configure launch options to connect to existing browser
        launch_options = {
            'headless': False,  # Must be False to connect to existing browser
            'channel': 'chrome' if 'chrome' in browser_type.name else 'msedge',
            'args': [
                '--remote-debugging-port=9222',
                '--user-data-dir=' + os.path.expanduser('~/.config/google-chrome'),
                '--profile-directory=Default',
            ]
        }
        
        # Try to connect to existing browser first
        try:
            browser = await browser_type.connect_over_cdp('http://localhost:9222')
            print("Connected to existing browser instance")
        except Exception as e:
            print(f"Could not connect to existing browser: {e}")
            # If can't connect, try to launch a new instance
            if executable_path and os.path.exists(executable_path):
                launch_options['executable_path'] = executable_path
            browser = await browser_type.launch(**launch_options)
        
        # Get all browser contexts
        contexts = browser.contexts if hasattr(browser, 'contexts') else [browser]
        all_tabs = []
        
        if DEBUG:
            print(f"Found {len(contexts)} contexts in {browser_type.name}")
        
        # Get pages from each context
        for context in contexts:
            try:
                pages = await context.pages()
                if DEBUG:
                    print(f"Found {len(pages)} pages in context")
                
                for page in pages:
                    try:
                        # Add a small delay to let the page load
                        await asyncio.sleep(1)
                        
                        title = await page.title()
                        url = page.url
                        
                        if url and url not in ['about:blank', 'chrome://newtab/', 'edge://newtab/']:
                            tab_info = {
                                'title': title or 'No Title',
                                'url': url,
                                'browser': browser_type.name,
                                'timestamp': datetime.now().isoformat(),
                                'active': await page.evaluate('document.hasFocus()')
                            }
                            all_tabs.append(tab_info)
                            
                            if DEBUG:
                                print(f"Found tab: {tab_info['title']} ({tab_info['url']})")
                                
                    except Exception as e:
                        if DEBUG:
                            print(f"Error getting page info: {type(e).__name__}: {e}")
                        continue
                        
            except Exception as e:
                if DEBUG:
                    print(f"Error processing context: {type(e).__name__}: {e}")
                continue
        
        return all_tabs
        
    except Exception as e:
        print(f"Error with {browser_type.name}: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return []
        
    finally:
        if browser:
            try:
                await browser.close()
            except Exception as e:
                print(f"Error closing browser: {e}")

async def get_installed_browsers(p):
    """Get list of installed browsers with their paths."""
    browsers = []
    
    # Standard browser names to check (Playwright's built-in detection)
    browser_names = ['chromium', 'chrome', 'msedge', 'firefox']
    
    # First try built-in detection
    for name in browser_names:
        try:
            browser_type = getattr(p, name, None)
            if browser_type:
                browsers.append((name, browser_type, None))
                print(f"✅ Detected browser (built-in): {name}")
        except Exception as e:
            print(f"⚠️  Error detecting {name} (built-in): {e}")
    
    # Then try system-installed browsers with explicit paths
    system = platform.system().lower()
    system_browsers = {
        'chrome': 'chromium',
        'msedge': 'chromium',
    }
    
    # Print available browser types for debugging
    print("\nAvailable browser types:")
    for name in dir(p):
        if not name.startswith('_') and name not in ['Error', 'Request', 'Route', 'selectors']:
            print(f"- {name}")
    
    # Try to find and use system browsers
    for name, browser_type_name in system_browsers.items():
        try:
            paths = BROWSER_PATHS.get(system, {}).get(name, [])
            found = False
            
            for path in paths:
                path = os.path.expanduser(path)  # Handle ~ in paths
                path = os.path.expandvars(path)  # Handle environment variables
                
                if os.path.exists(path):
                    try:
                        browser_type = getattr(p, browser_type_name)
                        browsers.append((name, browser_type, path))
                        print(f"✅ Found {name} at: {path}")
                        found = True
                        break
                    except Exception as e:
                        print(f"⚠️  Error using {name} at {path}: {e}")
            
            if not found:
                print(f"❌ Could not find {name} in any standard location")
                
        except Exception as e:
            print(f"⚠️  Error detecting {name} (system): {e}")
    
    # Try to connect to existing browser instances
    try:
        print("\nAttempting to connect to existing browser instances...")
        for port in [9222, 9223, 9224]:
            try:
                browser = await p.chromium.connect_over_cdp(f'http://localhost:{port}')
                browsers.append((f'chrome-devtools-{port}', browser.browser_type, None))
                print(f"✅ Connected to Chrome DevTools on port {port}")
            except Exception:
                pass
    except Exception as e:
        print(f"⚠️  Error connecting to existing browsers: {e}")
    
    # Remove duplicates while preserving order
    seen = set()
    unique_browsers = []
    for b in browsers:
        if b[0] not in seen:
            seen.add(b[0])
            unique_browsers.append(b)
    
    if not unique_browsers:
        print("\n❌ No browsers detected! Please make sure you have Chrome or Edge installed.")
    else:
        print(f"\n✅ Detected {len(unique_browsers)} browsers: {', '.join([b[0] for b in unique_browsers])}")
    
    return unique_browsers

async def get_all_browser_tabs() -> List[Dict[str, Any]]:
    """Get tabs from all installed browsers."""
    all_tabs = []
    
    async with async_playwright() as p:
        browsers = await get_installed_browsers(p)
        
        if not browsers:
            print("No supported browsers found!")
            return []
            
        print(f"\nDetected browsers: {', '.join([b[0] for b in browsers])}")
        
        for name, browser_type, executable_path in browsers:
            try:
                print(f"\nChecking {name}...")
                tabs = await get_browser_tabs(
                    browser_type, 
                    headless=False,  # Set to False to see the browser
                    executable_path=executable_path
                )
                all_tabs.extend(tabs)
                print(f"Found {len(tabs)} tabs in {name}")
            except Exception as e:
                print(f"Error with {name}: {str(e)[:200]}")
    
    return all_tabs

def display_tabs(tabs: List[Dict[str, Any]]):
    """Display tabs in a readable format."""
    if not tabs:
        print("\nNo tabs found in any browser. Make sure you have at least one browser open.")
        return
    
    print("\n" + "="*60)
    print(f"FOCUSGUARD TAB MONITOR - {len(tabs)} tabs found")
    print("="*60 + "\n")
    
    # Group by browser
    by_browser = {}
    for tab in tabs:
        browser = tab['browser'].capitalize()
        if browser not in by_browser:
            by_browser[browser] = []
        by_browser[browser].append(tab)
    
    # Print summary
    print("BROWSER SUMMARY:")
    for browser, btabs in by_browser.items():
        active_tabs = sum(1 for t in btabs if t.get('active', False))
        print(f"- {browser.upper()}: {len(btabs)} tabs ({active_tabs} active)")
    print("\n")
    
    # Print detailed list
    print("DETAILED TAB LIST:")
    for browser, btabs in by_browser.items():
        print(f"\n{browser.upper()}:")
        for i, tab in enumerate(btabs, 1):
            active_marker = "* " if tab.get('active', False) else "  "
            print(f"{active_marker}{i}. {tab['title']}")
            print(f"     {tab['url']}")

def get_browser_tabs_psutil() -> List[Dict[str, Any]]:
    """Get open browser tabs using psutil to find running browser processes."""
    tabs = []
    
    # Map of process names to browser types
    browser_map = {
        'chrome.exe': 'Chrome',
        'msedge.exe': 'Edge',
        'firefox.exe': 'Firefox',
        'browser.exe': 'Edge',  # For Edge on Windows 11
        'msedgewebview2.exe': 'Edge',
    }
    
    # Regular expression to extract URLs from command line arguments
    url_pattern = re.compile(r'--(?:app|app-id|app-url|app-shell-host-window-id|app-window-id|app-shell-host-window-type|app-shell-host-window-title|app-shell-host-window-bounds|app-shell-host-window-show-state|app-shell-host-window-show-command|app-shell-host-window-style|app-shell-host-window-ex-style|app-shell-host-window-rect|app-shell-host-window-placement|app-shell-host-window-show|app-shell-host-window-update|app-shell-host-window-activate|app-shell-host-window-deactivate|app-shell-host-window-minimize|app-shell-host-window-maximize|app-shell-host-window-restore|app-shell-host-window-show-window|app-shell-host-window-hide-window|app-shell-host-window-bring-to-front|app-shell-host-window-set-foreground|app-shell-host-window-set-focus|app-shell-host-window-set-active|app-shell-host-window-enable-window|app-shell-host-window-disable-window|app-shell-host-window-is-window|app-shell-host-window-is-window-visible|app-shell-host-window-is-window-enabled|app-shell-host-window-is-iconic|app-shell-host-window-is-zoomed|app-shell-host-window-is-maximized|app-shell-host-window-has-focus|app-shell-host-window-is-focused|app-shell-host-window-get-window-rect|app-shell-host-window-get-client-rect|app-shell-host-window-get-window-info|app-shell-host-window-get-window-text|app-shell-host-window-set-window-text|app-shell-host-window-get-class-name|app-shell-host-window-get-window-thread-process-id|app-shell-host-window-get-window-long-ptr|app-shell-host-window-set-window-long-ptr|app-shell-host-window-get-class-long-ptr|app-shell-host-window-set-class-long-ptr|app-shell-host-window-get-window-placement|app-shell-host-window-set-window-placement|app-shell-host-window-show-window-async|app-shell-host-window-update-window|app-shell-host-window-set-parent|app-shell-host-window-get-parent|app-shell-host-window-get-window|app-shell-host-window-set-window-pos|app-shell-host-window-get-window-rect-ex|app-shell-host-window-get-client-rect-ex|app-shell-host-window-get-window-info-ex|app-shell-host-window-get-window-text-ex|app-shell-host-window-set-window-text-ex|app-shell-host-window-get-class-name-ex|app-shell-host-window-get-window-thread-process-id-ex|app-shell-host-window-get-window-long-ptr-ex|app-shell-host-window-set-window-long-ptr-ex|app-shell-host-window-get-class-long-ptr-ex|app-shell-host-window-set-class-long-ptr-ex|app-shell-host-window-get-window-placement-ex|app-shell-host-window-set-window-placement-ex|app-shell-host-window-show-window-async-ex|app-shell-host-window-update-window-ex|app-shell-host-window-set-parent-ex|app-shell-host-window-get-parent-ex|app-shell-host-window-get-window-ex|app-shell-host-window-set-window-pos-ex)=([^\s]+)')
    
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                browser_name = browser_map.get(proc.info['name'].lower())
                if not browser_name:
                    continue
                    
                cmdline = ' '.join(proc.info['cmdline'] or [])
                urls = re.findall(r'https?://[^\s"]+', cmdline)
                
                for url in urls:
                    # Clean up URL
                    url = url.split('"')[0].split(' ')[0].rstrip(',').rstrip(')')
                    if any(x in url.lower() for x in ['localhost', '127.0.0.1', 'chrome://', 'edge://', 'about:']):
                        continue
                        
                    tabs.append({
                        'title': f"{browser_name} Tab",
                        'url': url,
                        'browser': browser_name,
                        'timestamp': datetime.now().isoformat(),
                        'active': False
                    })
                    
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
                
    except Exception as e:
        print(f"⚠️  Error scanning processes: {e}")
    
    return tabs

def get_browser_windows() -> List[Dict[str, Any]]:
    """Get information about browser windows and their tabs using Windows API."""
    browsers = []
    
    def enum_windows_callback(hwnd, results):
        # Skip invisible windows
        if not win32gui.IsWindowVisible(hwnd):
            return True
            
        # Get window style
        style = win32gui.GetWindowLong(hwnd, GWL_STYLE)
        if not (style & WS_VISIBLE):
            return True
            
        # Skip tool windows
        if win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) & WS_EX_TOOLWINDOW:
            return True
            
        # Get window text
        window_text = win32gui.GetWindowText(hwnd)
        if not window_text:
            return True
            
        # Get process ID
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        
        try:
            # Get process name
            process = psutil.Process(pid)
            process_name = process.name().lower()
            
            # Map process name to browser name
            browser_map = {
                'chrome.exe': 'Chrome',
                'msedge.exe': 'Edge',
                'firefox.exe': 'Firefox',
                'browser.exe': 'Edge',
                'msedgewebview2.exe': 'Edge',
            }
            
            browser_name = browser_map.get(process_name)
            if not browser_name:
                return True
                
            # Get window class name
            class_name = win32gui.GetClassName(hwnd)
            
            # Skip popup and tool windows
            if 'tool' in class_name.lower() or 'popup' in window_text.lower():
                return True
                
            # Skip empty or system windows
            if not window_text or window_text.startswith('Default IME') or 'msctls_statusbar' in class_name.lower():
                return True
                
            # Check if this is a browser window with tabs
            if any(x in window_text for x in [' - Google Chrome', ' - Microsoft Edge', ' - Mozilla Firefox']):
                # Get URL from address bar (if possible)
                url = ""
                try:
                    # Try to find the address bar and get its text
                    # This is a simplified approach - a more robust solution would use UI Automation
                    # or browser-specific extensions
                    if 'chrome' in process_name or 'msedge' in process_name:
                        # For Chrome/Edge, we can try to find the address bar
                        # This is a best-effort approach
                        url = f"browser://{process_name.split('.')[0]}/tab/{pid}"
                except Exception as e:
                    if DEBUG:
                        print(f"Error getting URL: {e}")
                
                # Add browser window info
                window_info = {
                    'hwnd': hwnd,
                    'title': window_text,
                    'class': class_name,
                    'pid': pid,
                    'process_name': process_name,
                    'browser': browser_name,
                    'url': url,
                    'timestamp': datetime.now().isoformat(),
                    'active': win32gui.GetForegroundWindow() == hwnd
                }
                
                # Find or create browser entry
                browser = next((b for b in browsers if b['name'] == browser_name and b['pid'] == pid), None)
                if not browser:
                    browser = {
                        'name': browser_name,
                        'pid': pid,
                        'exe': process.exe(),
                        'windows': [],
                        'tabs': []
                    }
                    browsers.append(browser)
                
                # Add window to browser
                browser['windows'].append(window_info)
                
                # Add as a tab if it looks like a tab
                if ' - ' in window_text and ('Google Chrome' in window_text or 'Microsoft Edge' in window_text or 'Mozilla Firefox' in window_text):
                    tab_title = window_text.split(' - ')[0]
                    if tab_title and tab_title != 'New Tab' and tab_title != 'New Tab - ':
                        tab_info = {
                            'title': tab_title,
                            'url': url,
                            'browser': browser_name,
                            'timestamp': datetime.now().isoformat(),
                            'active': win32gui.GetForegroundWindow() == hwnd,
                            'window': hwnd
                        }
                        browser['tabs'].append(tab_info)
        
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
        except Exception as e:
            if DEBUG:
                print(f"Error processing window {hwnd}: {e}")
        
        return True
    
    # Enumerate all top-level windows
    win32gui.EnumWindows(enum_windows_callback, None)
    
    return browsers

async def main():
    print("\n" + "="*60)
    print("FOCUSGUARD BROWSER TAB DETECTOR")
    print("="*60)
    
    # Skip input for non-interactive terminals
    try:
        input("\nPress Enter to start scanning for browser tabs...")
    except EOFError:
        print("\nRunning in non-interactive mode...")
    
    print("\nScanning for browser tabs using Windows API...")
    
    # Get browser windows and tabs using Windows API
    browsers = get_browser_windows()
    
    if not browsers:
        print("\n[!] No browser windows found.")
    else:
        print(f"\n[+] Found {len(browsers)} browsers with open windows:")
        
        all_tabs = []
        
        for browser in browsers:
            tab_count = len(browser.get('tabs', []))
            window_count = len(browser.get('windows', []))
            
            print(f"\n  {browser['name']} (PID: {browser['pid']})")
            print(f"  Path: {browser.get('exe', 'Unknown')}")
            print(f"  Windows: {window_count}")
            print(f"  Tabs: {tab_count}")
            
            # Show first few tabs if any
            for i, tab in enumerate(browser.get('tabs', [])[:3], 1):
                print(f"    {i}. {tab.get('title', 'No title')}")
                if tab.get('url'):
                    print(f"       {tab['url']}")
            
            if tab_count > 3:
                print(f"    ... and {tab_count - 3} more")
            
            all_tabs.extend(browser.get('tabs', []))
        
        print(f"\n[+] Total tabs found: {len(all_tabs)}")
    
    # Try the Playwright method as a fallback
    try:
        print("\n=== Attempting to use Playwright for more detailed tab info ===")
        tabs = await get_all_browser_tabs()
        if tabs:
            print(f"\n[+] Found {len(tabs)} tabs using Playwright:")
            display_tabs(tabs)
        else:
            print("\n[!] No additional tabs found using Playwright")
    except Exception as e:
        print(f"\n[!] Error using Playwright: {e}")
    
    # Final summary
    all_tabs = []
    for browser in browsers:
        all_tabs.extend(browser['tabs'])
    
    if 'tabs' in locals() and tabs:
        all_tabs.extend(tab for tab in tabs if tab not in all_tabs)
    
    if all_tabs:
        print(f"\n[+] Found {len(all_tabs)} total tabs across all methods!")
    else:
        print("\n[!] No tabs found using any method. Please try:")
        print("1. Make sure your browser is running")
        print("2. Try running the browser with remote debugging enabled")
        print("3. Check firewall/antivirus settings")
        print("4. Try running as administrator")

if __name__ == "__main__":
    asyncio.run(main())