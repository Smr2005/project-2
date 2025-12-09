# test_client.py
import requests, json

API = "http://127.0.0.1:8000/analyze"
sql = """
SELECT c.customer_name, s.product_name, s.sale_amount
FROM customers c
JOIN sales s ON c.customer_id = s.customer_id
WHERE s.sale_amount > 100;
"""

payload = {"sql": sql, "run_in_sandbox": True}

r = requests.post(API, json=payload, timeout=120)
print("Status:", r.status_code)
try:
    print(json.dumps(r.json(), indent=2, default=str))
except Exception:
    
    print(r.text)
