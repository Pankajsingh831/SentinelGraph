import urllib.request, urllib.error, json

base_url = "http://127.0.0.1:8000"

def check(url, expected_status):
    print(f"Testing: {url}")
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req) as resp:
            print(f"  Got status {resp.status} (expected {expected_status})")
            data = json.loads(resp.read().decode())
            print("  Response:", data)
    except urllib.error.HTTPError as e:
        print(f"  Got HTTPError {e.code} (expected {expected_status})")
        print("  Error detail:", e.read().decode())

check(f"{base_url}/api/v1/graph/entity/invalid_type/5c5001a1-887e-45e7-8ae8-f1c53fa808b0", 400)
check(f"{base_url}/api/v1/graph/entity/customer/not-a-valid-uuid", 400)
check(f"{base_url}/api/v1/graph/entity/customer/00000000-0000-0000-0000-000000000000", 200)
