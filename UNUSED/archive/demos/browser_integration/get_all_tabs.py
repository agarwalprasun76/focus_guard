"""
Get all open tabs from all browsers (Chrome, Edge) using the FocusGuard tab server.
Returns a dictionary with browser names as keys and lists of tab information as values.
"""
import requests
import pandas as pd
from typing import Dict, List, Any, Tuple, Optional
from collections import defaultdict
from datetime import datetime

TAB_SERVER_URL = "http://127.0.0.1:5000/api/tabs"

def get_browser_name(browser_info: Dict[str, Any]) -> str:
    """
    Extract and normalize browser name from browser info.
    
    Args:
        browser_info: Dictionary containing browser information, typically with 'name' and 'userAgent' keys
        
    Returns:
        Normalized browser name (edge, chrome, firefox, safari, or unknown)
    """
    if not browser_info:
        return "unknown"
    
    # Handle case where browser_info is a string (legacy format)
    if isinstance(browser_info, str):
        browser_info = {'name': browser_info}
    
    # Extract name and user agent
    name = str(browser_info.get('name', '')).lower()
    user_agent = str(browser_info.get('userAgent', '')).lower()
    
    # Debug info
    # print(f"Browser detection - name: {name}, user_agent: {user_agent}")
    
    # Check for Edge (needs to be before Chrome since Edge's UA also contains 'Chrome')
    if any(x in name for x in ['edg', 'edge', 'msedge', 'microsoft edge']) or \
       any(x in user_agent for x in ['edg/', 'edg ', 'edge/', 'msedge', 'microsoft edge']):
        return 'edge'
        
    # Check for Chrome
    if 'chrome' in name or 'chrome/' in user_agent or 'crios/' in user_agent:
        return 'chrome'
        
    # Check for Firefox
    if 'firefox' in name or 'firefox/' in user_agent or 'fxios/' in user_agent:
        return 'firefox'
        
    # Check for Safari (but not Chrome/Edge)
    if 'safari' in name or ('safari/' in user_agent and 'chrome' not in user_agent and 'edg' not in user_agent):
        return 'safari'
    
    # Fallback to the name if we couldn't determine the browser
    return name if name else 'unknown'

def get_all_tabs(debug: bool = True) -> Dict[str, List[Dict[str, Any]]]:
    """
    Get all open tabs from all browsers.
    
    Args:
        debug: If True, print debug information
        
    Returns:
        Dict with browser names as keys and lists of tab dictionaries as values.
        Each tab dictionary contains 'title', 'url', and other metadata.
    """
    try:
        response = requests.get(TAB_SERVER_URL, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if debug:
            print("\nRaw data from server:")
            print(f"- Browser info: {data.get('browser', 'No browser info')}")
            print(f"- Number of tabs: {len(data.get('tabs', []))}")
            if 'tabs' in data and len(data['tabs']) > 0:
                print("Sample tab data:", {k: v for k, v in data['tabs'][0].items() 
                                       if k not in ['favicon']})
        
        # Initialize result dictionary with lists
        result = defaultdict(list)
        
        # Get default browser info from the top level
        default_browser_info = data.get("browser", {})
        
        if debug:
            print(f"\nDefault browser info: {default_browser_info}")
        
        # Process tabs
        for i, tab in enumerate(data.get("tabs", []), 1):
            try:
                # Each tab can have its own browser info or inherit from the default
                tab_browser_info = tab.get("browser", default_browser_info)
                tab_browser = get_browser_name(tab_browser_info)
                
                if debug and i <= 3:  # Print first 3 tabs for debugging
                    print(f"\nTab {i}:")
                    print(f"- Raw browser info: {tab_browser_info}")
                    print(f"- Detected browser: {tab_browser}")
                    print(f"- Title: {tab.get('title', 'No title')}")
                    print(f"- URL: {tab.get('url', 'No URL')}")
                    print(f"- Active: {tab.get('active', False)}")
                    if 'timestamp' in tab:
                        print(f"- Timestamp: {tab['timestamp']} ({format_timestamp(tab['timestamp'])})")
                
                result[tab_browser].append({
                    'title': tab.get("title", ""),
                    'url': tab.get("url", ""),
                    'favicon': tab.get("favicon", ""),
                    'window_id': tab.get("windowId"),
                    'tab_id': tab.get("id"),
                    'active': tab.get("active", False),
                    'timestamp': tab.get("timestamp"),
                    'raw_browser_info': tab_browser_info  # Keep original browser info
                })
            except Exception as e:
                if debug:
                    print(f"\nError processing tab {i}: {e}")
                    print(f"Tab data: {tab}")
                continue
        
        return dict(result)
        
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to tab server: {e}")
        print("Make sure the FocusGuard tab server is running and accessible at", TAB_SERVER_URL)
        return {}
    except Exception as e:
        print(f"Error processing tab data: {e}")
        return {}

def format_timestamp(ts: Optional[float]) -> str:
    """Format timestamp to human-readable format."""
    if not ts:
        return "-"
    try:
        dt = datetime.fromtimestamp(ts / 1000)  # Convert from ms to seconds
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError):
        return str(ts)

def consolidate_tabs(tabs_data: Dict[str, List[Dict[str, Any]]]) -> pd.DataFrame:
    """
    Consolidate all tabs from all browsers into a single DataFrame.
    
    Args:
        tabs_data: Dictionary of browser names to lists of tab data
        
    Returns:
        pd.DataFrame: Consolidated DataFrame with all tabs
    """
    all_tabs = []
    
    for browser, tabs in tabs_data.items():
        for tab in tabs:
            # Create a copy to avoid modifying the original data
            tab_data = tab.copy()
            # Add browser name
            tab_data['browser'] = browser
            # Format timestamp if it exists
            if 'timestamp' in tab_data:
                tab_data['last_updated'] = format_timestamp(tab_data['timestamp'])
            all_tabs.append(tab_data)
    
    # Convert to DataFrame
    if not all_tabs:
        return pd.DataFrame()
        
    df = pd.DataFrame(all_tabs)
    
    # Reorder columns for better readability
    columns = ['browser', 'title', 'url', 'active', 'last_updated']
    # Add any additional columns that exist in the data
    extra_columns = [col for col in df.columns if col not in columns]
    columns.extend(extra_columns)
    
    return df[[col for col in columns if col in df.columns]]

def print_tabs_table(tabs_data: Dict[str, List[Dict[str, Any]]], consolidated: bool = False):
    """
    Print tabs in a formatted table.
    
    Args:
        tabs_data: Dictionary of browser names to lists of tab data
        consolidated: If True, show all tabs in a single table with browser column
    """
    if not tabs_data:
        print("No tabs found or error occurred.")
        return
    
    total_tabs = sum(len(tabs) for tabs in tabs_data.values())
    print(f"\n{'='*60}")
    print(f"FOCUSGUARD TAB MONITOR - {total_tabs} tabs across {len(tabs_data)} browsers")
    print("="*60)
    
    if consolidated:
        # Show all tabs in a single table
        df = consolidate_tabs(tabs_data)
        if df.empty:
            print("\nNo tabs found.")
            return
            
        # Format the DataFrame for display
        display_df = df.copy()
        display_df['title'] = display_df['title'].apply(
            lambda x: (x[:47] + '...') if len(str(x)) > 50 else x
        )
        display_df['url'] = display_df['url'].apply(
            lambda x: (x[:47] + '...') if len(str(x)) > 50 else x
        )
        display_df['active'] = display_df['active'].apply(
            lambda x: '✓' if x else ''
        )
        
        # Print the consolidated table
        print("\nALL TABS:")
        print(display_df.to_string(
            index=False, 
            justify='left', 
            columns=['browser', 'title', 'url', 'active', 'last_updated'],
            max_colwidth=50
        ))
    else:
        # Show tabs grouped by browser (original behavior)
        for browser, tabs in sorted(tabs_data.items()):
            print(f"\n{browser.upper()} - {len(tabs)} tabs")
            print("-" * (len(browser) + 8 + len(str(len(tabs))) + 6))
            
            if not tabs:
                print("  No tabs found")
                continue
                
            # Create a list of dictionaries for the table
            table_data = []
            for i, tab in enumerate(tabs, 1):
                title = tab.get('title', 'No title')
                url = tab.get('url', 'No URL')
                active = "*" if tab.get('active') else " "
                
                table_data.append({
                    '#': f"{i:2d}{active}",
                    'Title': (title[:47] + '...') if len(title) > 50 else title,
                    'URL': (url[:47] + '...') if len(url) > 50 else url
                })
            
            # Print as pandas DataFrame for nice formatting
            if table_data:
                df = pd.DataFrame(table_data)
                print(df.to_string(index=False, justify='left', col_space=2))
    
    print("\n* = Active tab")

def check_server_status() -> bool:
    """Check if the tab server is running and accessible."""
    try:
        # Try the direct status endpoint first
        status_url = TAB_SERVER_URL.replace('/api/tabs', '/api/status')
        response = requests.get(status_url, timeout=2)
        
        if response.status_code == 200:
            try:
                data = response.json()
                if data.get('status') == 'ok':
                    print(f"✅ Tab server is running at {TAB_SERVER_URL}")
                    print(f"   - Uptime: {data.get('uptime', 0):.1f} seconds")
                    print(f"   - Tab count: {data.get('tab_count', 0)} tabs")
                    return True
            except ValueError:
                pass
                
        print(f"⚠️  Server returned status code: {response.status_code}")
        return False
        
    except requests.RequestException as e:
        print(f"❌ Could not connect to tab server: {e}")
        print(f"   - Make sure the server is running at {TAB_SERVER_URL}")
        print(f"   - Try running: python demos/browser_integration/run_demo.py")
        return False

def main():
    """Main function to fetch and display tabs."""
    try:
        # Check if server is running
        print("Checking FocusGuard tab server status...")
        if not check_server_status():
            print("\n❌ Tab server is not running. Please start it first with:")
            print("   python demos/browser_integration/run_demo.py")
            return
            
        # Get all tabs with debug info
        print("\nFetching tabs from FocusGuard tab server...")
        tabs = get_all_tabs(debug=True)
        
        if not tabs:
            print("\n❌ No tabs found. This could be because:")
            print("1. No browsers with the FocusGuard extension are connected")
            print("2. The extension doesn't have permission to access tab data")
            print("3. No tabs are currently open in the connected browsers")
            print("\nFor Edge, please ensure:")
            print("1. The FocusGuard extension is installed from the Edge Add-ons store")
            print("2. The extension has 'Tabs' permission enabled")
            print("3. The extension is not in 'disabled' state")
            return
            
        # Print as consolidated table by default
        print("\n" + "="*60)
        print(f"FOCUSGUARD TAB MONITOR - {sum(len(t) for t in tabs.values())} tabs across {len(tabs)} browsers")
        print("="*60)
        
        # Print browser summary first
        print("\nBROWSER SUMMARY:")
        for browser, browser_tabs in sorted(tabs.items()):
            active_tabs = sum(1 for t in browser_tabs if t.get('active'))
            print(f"- {browser.upper()}: {len(browser_tabs)} tabs ({active_tabs} active)")
        
        # Then show the detailed table
        print("\nDETAILED TAB LIST:")
        print_tabs_table(tabs, consolidated=True)
        
        # Also return the raw data for programmatic use
        return tabs
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    
    # Example of how to use the consolidate_tabs function programmatically:
    # if tabs:
    #     df = consolidate_tabs(tabs)
    #     # Now you can work with the DataFrame
    #     print("\nSample of consolidated tab data:")
    #     print(df[['browser', 'title', 'url']].head())

if __name__ == "__main__":
    main()
