import requests
import time

def test_server():
    urls = ["http://127.0.0.1:8000", "http://localhost:8000"]
    for url in urls:
        print(f"Testing connectivity to {url}...")
        try:
            start_time = time.time()
            r = requests.get(url, timeout=5)
            end_time = time.time()
            print(f"Status: {r.status_code}")
            print(f"Time taken: {end_time - start_time:.2f} seconds")
        except Exception as e:
            print(f"Error for {url}: {e}")

if __name__ == "__main__":
    test_server()
