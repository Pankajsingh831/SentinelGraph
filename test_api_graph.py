import urllib.request, json

base_url = "http://127.0.0.1:8000"

# 1. Test get_entity_graph
url1 = f"{base_url}/api/v1/graph/entity/customer/5c5001a1-887e-45e7-8ae8-f1c53fa808b0"
print(f"--- Calling: {url1} ---")
req1 = urllib.request.Request(url1)
with urllib.request.urlopen(req1) as resp:
    print("STATUS_CODE:", resp.status)
    data1 = json.loads(resp.read().decode())
    print("DEGRADED:", data1.get("degraded"))
    print("NODE COUNT:", len(data1.get("nodes", [])))
    print("EDGE COUNT:", len(data1.get("edges", [])))
    print("NODES:")
    for n in data1.get("nodes", []):
        print(f"  {n['type']}: {n['id']}")
    print("EDGES:")
    for e in data1.get("edges", []):
        print(f"  {e['source']} -[:{e['type']}]-> {e['target']}")

# 2. Test get_neighbors depth=1
url2 = f"{base_url}/api/v1/graph/entity/customer/5c5001a1-887e-45e7-8ae8-f1c53fa808b0/neighbors?depth=1&limit=50"
print(f"\n--- Calling: {url2} ---")
req2 = urllib.request.Request(url2)
with urllib.request.urlopen(req2) as resp:
    print("STATUS_CODE:", resp.status)
    data2 = json.loads(resp.read().decode())
    print("DEGRADED:", data2.get("degraded"))
    print("NEIGHBORS COUNT:", len(data2.get("neighbors", [])))
    print("EDGE COUNT:", len(data2.get("edges", [])))
    print("DEPTH:", data2.get("depth"))
    print("LIMIT:", data2.get("limit"))
    print("NEIGHBOR TYPES:", {n["type"] for n in data2.get("neighbors", [])})

# 3. Test get_neighbors depth=2
url3 = f"{base_url}/api/v1/graph/entity/customer/5c5001a1-887e-45e7-8ae8-f1c53fa808b0/neighbors?depth=2&limit=50"
print(f"\n--- Calling: {url3} ---")
req3 = urllib.request.Request(url3)
with urllib.request.urlopen(req3) as resp:
    print("STATUS_CODE:", resp.status)
    data3 = json.loads(resp.read().decode())
    print("DEGRADED:", data3.get("degraded"))
    print("NEIGHBORS COUNT:", len(data3.get("neighbors", [])))
    print("EDGE COUNT:", len(data3.get("edges", [])))
    print("NEIGHBOR TYPES:", {n["type"] for n in data3.get("neighbors", [])})
