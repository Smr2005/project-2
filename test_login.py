import requests

def test_login():
    url = "http://127.0.0.1:8001/auth/login"
    data = {
        "username": "test@example.com",
        "password": "password123"
    }
    print(f"Testing login at {url}...")
    try:
        r = requests.post(url, data=data, timeout=10)
        print(f"Status: {r.status_code}")
        print(f"Response: {r.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_login()
