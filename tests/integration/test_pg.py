import psycopg2

tests = [
    ("Direct db.fxhcafwnnisyvfmvggwt.supabase.co:5432", "postgresql://postgres:Xeren2026%21%40%23@db.fxhcafwnnisyvfmvggwt.supabase.co:5432/postgres"),
    ("Pooler Session 5432 (aws-0-ap-south-1.pooler.supabase.com:5432)", "postgresql://postgres.fxhcafwnnisyvfmvggwt:Xeren2026%21%40%23@aws-0-ap-south-1.pooler.supabase.com:5432/postgres"),
    ("Pooler Transaction 6543 (aws-0-ap-south-1.pooler.supabase.com:6543)", "postgresql://postgres.fxhcafwnnisyvfmvggwt:Xeren2026%21%40%23@aws-0-ap-south-1.pooler.supabase.com:6543/postgres"),
]

for name, uri in tests:
    print(f"\n--- Testing {name} ---")
    try:
        conn = psycopg2.connect(uri, connect_timeout=8)
        cur = conn.cursor()
        cur.execute("SELECT version();")
        ver = cur.fetchone()[0]
        print(f"  [OK] Connected! PostgreSQL Version: {ver[:60]}")
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
        tables = [t[0] for t in cur.fetchall()]
        print(f"  [OK] Public tables count: {len(tables)} -> {tables}")
        conn.close()
    except Exception as e:
        print(f"  [FAIL] {e}")
