import psycopg2

pooler_host = "aws-0-ap-northeast-2.pooler.supabase.com"
user = "postgres.fxhcafwnnisyvfmvggwt"
pwd = "Xeren2026%21%40%23"

for port, mode in [(5432, "Session Mode"), (6543, "Transaction Mode")]:
    uri = f"postgresql://{user}:{pwd}@{pooler_host}:{port}/postgres"
    print(f"\nTesting Supabase {mode} (Port {port})...")
    try:
        conn = psycopg2.connect(uri, connect_timeout=8)
        cur = conn.cursor()
        cur.execute("SELECT version();")
        print(f"  [SUCCESS] Connected! Version: {cur.fetchone()[0]}")
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
        tables = [t[0] for t in cur.fetchall()]
        print(f"  [SUCCESS] Public tables in DB ({len(tables)}): {tables}")
        conn.close()
    except Exception as e:
        print(f"  [FAIL] Port {port}: {e}")
