"""
Test script to verify the Tab Server API endpoints.
Run this script after starting the main FocusGuard application.
"""
import requests
import json
import time

def test_status():
    """Test the /api/status endpoint."""
    print("\n=== Testing /api/status ===")
    try:
        response = requests.get("http://127.0.0.1:5000/api/status")
        print(f"Status Code: {response.status_code}")
        print("Response:")
        print(json.dumps(response.json(), indent=2))
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_get_tabs():
    """Test the /api/tabs GET endpoint."""
    print("\n=== Testing GET /api/tabs ===")
    try:
        response = requests.get("http://127.0.0.1:5000/api/tabs")
        print(f"Status Code: {response.status_code}")
        print("Response:")
        print(json.dumps(response.json(), indent=2))
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_post_tabs():
    """Test the /api/tabs POST endpoint."""
    print("\n=== Testing POST /api/tabs ===")
    test_data = {
        "browser": {
            "name": "test-browser",
            "version": "1.0.0"
        },
        "tabs": [
            {
                "id": 1,
                "url": "https://example.com",
                "title": "Example Domain",
                "active": True,
                "windowId": 1
            }
        ]
    }
    
    try:
        response = requests.post(
            "http://127.0.0.1:5000/api/tabs",
            json=test_data,
            headers={"Content-Type": "application/json"}
        )
        print(f"Status Code: {response.status_code}")
        print("Response:")
        print(json.dumps(response.json(), indent=2))
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_cors():
    """Test CORS headers."""
    print("\n=== Testing CORS Headers ===")
    try:
        # Test OPTIONS request
        response = requests.options(
            "http://127.0.0.1:5000/api/tabs",
            headers={
                "Origin": "http://example.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type"
            }
        )
        
        print("CORS Headers:")
        for header in [
            'Access-Control-Allow-Origin',
            'Access-Control-Allow-Methods',
            'Access-Control-Allow-Headers',
            'Access-Control-Allow-Credentials'
        ]:
            print(f"{header}: {response.headers.get(header, 'Not found')}")
        
        return all(header in response.headers for header in [
            'Access-Control-Allow-Origin',
            'Access-Control-Allow-Methods',
            'Access-Control-Allow-Headers'
        ])
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    print("Starting Tab Server API Tests...")
    
    # Wait a moment for the server to start
    time.sleep(2)
    
    tests = [
        ("Status Endpoint", test_status),
        ("GET Tabs Endpoint", test_get_tabs),
        ("POST Tabs Endpoint", test_post_tabs),
        ("CORS Headers", test_cors)
    ]
    
    results = []
    for name, test in tests:
        print(f"\n{'='*50}\nRunning test: {name}\n{'-'*50}")
        result = test()
        results.append((name, result))
        print(f"\nResult: {'PASS' if result else 'FAIL'}")
    
    # Print summary
    print("\n" + "="*50)
    print("Test Summary:")
    print("-"*50)
    for name, result in results:
        print(f"{name}: {'PASS' if result else 'FAIL'}")
    
    if all(result for _, result in results):
        print("\n✅ All tests passed! The Tab Server API is working correctly with CORS support.")
    else:
        print("\n❌ Some tests failed. Please check the output above for details.")

if __name__ == "__main__":
    main()
