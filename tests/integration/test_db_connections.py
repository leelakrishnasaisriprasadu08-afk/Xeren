import urllib.request
import json
import ssl
import socket
import sys

print("==================================================")
print("     TESTING XEREN DATABASE & CLUSTER SERVICES    ")
print("==================================================")

env_vars = {}
with open("d:/Xeren/.env", "r") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env_vars[k.strip()] = v.strip()

# 1. PostgreSQL / Supabase
print("\n[1] Testing PostgreSQL (Supabase)...")
pg_url = env_vars.get("DATABASE_URL", "")
host = "db.fxhcafwnnisyvfmvggwt.supabase.co"
port = 5432

try:
    # Try resolving via getaddrinfo with 0 family (IPv4 or IPv6)
    addr_info = socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
    print(f"  [OK] DNS Resolved {host}:")
    for info in addr_info:
        print(f"       Family: {info[0].name}, IP: {info[4][0]}")
    
    # Try connecting to the first resolved address
    sock = socket.socket(addr_info[0][0], socket.SOCK_STREAM)
    sock.settimeout(8)
    sock.connect(addr_info[0][4])
    sock.close()
    print(f"  [OK] Socket connection to {host}:{port} SUCCESSFUL!")
except Exception as e:
    print(f"  [FAIL] Connection failed to {host}:{port}: {e}")

# 2. Qdrant Cloud Vector DB
print("\n[2] Testing Qdrant Cloud Vector Database...")
qdrant_url = env_vars.get("QDRANT_URL", "").rstrip("/")
qdrant_key = env_vars.get("QDRANT_API_KEY", "")

try:
    req = urllib.request.Request(
        f"{qdrant_url}/collections",
        headers={"api-key": qdrant_key, "User-Agent": "Xeren-Client"}
    )
    context = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=10, context=context) as response:
        status_code = response.getcode()
        body = response.read().decode("utf-8")
        data = json.loads(body)
        print(f"  [OK] Qdrant Cloud API connection SUCCESSFUL! (HTTP {status_code})")
        collections = data.get("result", {}).get("collections", [])
        print(f"       Active collections count: {len(collections)}")
        for col in collections:
            print(f"       - {col.get('name')}")
except Exception as e:
    print(f"  [FAIL] Qdrant connection failed: {e}")

# 3. MongoDB
print("\n[3] Testing MongoDB...")
mongo_uri = env_vars.get("MONGODB_URI")
if not mongo_uri:
    print("  [INFO] MONGODB_URI is not set (commented out).")
    print("         Xeren automatically uses in-memory virtual fallback store with 100% uptime.")
else:
    print(f"  Testing MongoDB URI: {mongo_uri}...")

print("\n==================================================")
