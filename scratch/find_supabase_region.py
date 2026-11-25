import psycopg2

regions = [
    "sa-east-1", "us-east-1", "us-east-2", "us-west-1", "us-west-2",
    "eu-west-1", "eu-west-2", "eu-west-3", "eu-central-1", "eu-north-1",
    "ap-southeast-1", "ap-southeast-2", "ap-northeast-1", "ap-northeast-2",
    "ca-central-1"
]

project_ref = "fxhcafwnnisyvfmvggwt"
pwd = "Xeren2026%21%40%23"

found = False
for r in regions:
    host = f"aws-0-{r}.pooler.supabase.com"
    uri = f"postgresql://postgres.{project_ref}:{pwd}@{host}:6543/postgres"
    try:
        conn = psycopg2.connect(uri, connect_timeout=4)
        print(f"[FOUND & CONNECTED!] Region: {r} via {host}")
        cur = conn.cursor()
        cur.execute("SELECT version();")
        print("  Version:", cur.fetchone()[0])
        conn.close()
        found = True
        break
    except Exception as e:
        err = str(e)
        if "tenant/user" not in err:
            print(f"  Region {r}: {err.strip()}")
        else:
            # tenant not in this region
            pass

if not found:
    print("Project ref not found on tested pooler regions or project is paused on Supabase.")
