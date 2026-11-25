# Xeren Progressive Car Showroom Python Backend
# Run: python app.py (Zero extra packages required!)
import http.server
import json
import sqlite3
import datetime
import urllib.parse

PORT = 8000
DB_FILE = "showroom.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS cars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_name TEXT NOT NULL,
            horsepower INTEGER NOT NULL,
            zero_to_sixty TEXT NOT NULL,
            range_km INTEGER NOT NULL,
            price_usd REAL NOT NULL,
            status TEXT DEFAULT 'AVAILABLE'
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS test_drives (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_code TEXT UNIQUE,
            customer_name TEXT NOT NULL,
            customer_email TEXT NOT NULL,
            vehicle_model TEXT NOT NULL,
            booking_date TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute("SELECT COUNT(*) FROM cars")
    if c.fetchone()[0] == 0:
        c.executemany("INSERT INTO cars (model_name, horsepower, zero_to_sixty, range_km, price_usd) VALUES (?, ?, ?, ?, ?)", [
            ("Xeren Apex Cyber-GT", 1450, "1.89s", 850, 145000.0),
            ("Xeren Phantom Hyper-SUV", 1200, "2.40s", 780, 120000.0),
            ("Xeren Vision Speedster", 1800, "1.65s", 920, 220000.0)
        ])
    conn.commit()
    conn.close()

init_db()

class ShowroomHandler(http.server.BaseHTTPRequestHandler):
    def _set_headers(self, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(204)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ('/api/v1/cars', '/api/cars'):
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT id, model_name, horsepower, zero_to_sixty, range_km, price_usd, status FROM cars").fetchall()
            cars = [dict(r) for r in rows]
            conn.close()
            self._set_headers(200)
            self.wfile.write(json.dumps({"success": True, "count": len(cars), "data": cars}, indent=2).encode('utf-8'))
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Route not found. Use GET /api/v1/cars"}).encode('utf-8'))

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ('/api/v1/test-drive', '/api/test-drive'):
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode('utf-8') if length > 0 else '{}'
            data = json.loads(body)
            name = data.get('name', 'Guest Driver')
            email = data.get('email', 'driver@example.com')
            model = data.get('vehicle_model', 'Xeren Apex Cyber-GT')
            b_date = data.get('preferred_date', str(datetime.date.today()))
            code = f"XR-{datetime.datetime.now().strftime('%M%S%f')[:6]}"

            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute(
                "INSERT INTO test_drives (booking_code, customer_name, customer_email, vehicle_model, booking_date) VALUES (?, ?, ?, ?, ?)",
                (code, name, email, model, b_date)
            )
            conn.commit()
            conn.close()

            self._set_headers(201)
            self.wfile.write(json.dumps({
                "success": True,
                "booking_code": code,
                "message": f"Test drive successfully scheduled for {name}."
            }, indent=2).encode('utf-8'))
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Route not found"}).encode('utf-8'))

if __name__ == '__main__':
    server = http.server.ThreadingHTTPServer(('127.0.0.1', PORT), ShowroomHandler)
    print(f"=======================================================")
    print(f" Xeren Python SQLite Backend Server Running!")
    print(f" Endpoint: http://localhost:{PORT}/api/v1/cars")
    print(f"=======================================================")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
