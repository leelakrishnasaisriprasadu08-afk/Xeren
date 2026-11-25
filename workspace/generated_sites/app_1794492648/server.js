// Xeren Progressive Car Showroom Node.js Backend API
// Run: node server.js (Zero external dependencies required!)
const http = require('http');
const PORT = process.env.PORT || 5000;

// In-Memory Database Controller (Syncs with database_schema.sql)
const carInventory = [
    {
        id: 1,
        modelName: "Xeren Apex Cyber-GT",
        category: "Hypercar",
        horsepower: 1450,
        zeroToSixty: "1.89s",
        rangeKm: 850,
        priceUSD: 145000,
        driveType: "AWD Quad-Motor",
        status: "AVAILABLE"
    },
    {
        id: 2,
        modelName: "Xeren Phantom Hyper-SUV",
        category: "Luxury Performance SUV",
        horsepower: 1200,
        zeroToSixty: "2.40s",
        rangeKm: 780,
        priceUSD: 120000,
        driveType: "AWD Tri-Motor",
        status: "IN_PRODUCTION"
    },
    {
        id: 3,
        modelName: "Xeren Vision Speedster",
        category: "Limited Track Special",
        horsepower: 1800,
        zeroToSixty: "1.65s",
        rangeKm: 920,
        priceUSD: 220000,
        driveType: "Torque-Vectoring AWD",
        status: "LIMITED_EDITION"
    }
];

const bookings = [];

// Built-in HTTP Server (works without npm install express)
const server = http.createServer((req, res) => {
    // CORS Headers
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') {
        res.writeHead(204);
        res.end();
        return;
    }

    const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
    
    if (req.method === 'GET' && url.pathname === '/api/cars') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ success: true, count: carInventory.length, data: carInventory }, null, 2));
        return;
    }

    if (req.method === 'POST' && url.pathname === '/api/test-drive') {
        let body = '';
        req.on('data', chunk => { body += chunk; });
        req.on('end', () => {
            try {
                const parsed = JSON.parse(body || '{}');
                const booking = {
                    bookingId: "XR-" + Math.floor(100000 + Math.random() * 900000),
                    name: parsed.name || "Guest Driver",
                    email: parsed.email || "driver@example.com",
                    carModel: parsed.carModel || "Xeren Apex Cyber-GT",
                    preferredDate: parsed.preferredDate || new Date().toISOString().split('T')[0],
                    status: "CONFIRMED",
                    createdAt: new Date().toISOString()
                };
                bookings.push(booking);
                res.writeHead(201, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ success: true, message: 'Test drive confirmed', booking }, null, 2));
            } catch (e) {
                res.writeHead(400, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ success: false, error: 'Invalid JSON body' }));
            }
        });
        return;
    }

    // Default 404
    res.writeHead(404, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ success: false, error: 'Route not found. Use GET /api/cars or POST /api/test-drive' }));
});

server.listen(PORT, () => {
    console.log(`=======================================================`);
    console.log(` Xeren Car Showroom Node.js Server Active!`);
    console.log(` Endpoint: http://localhost:${PORT}/api/cars`);
    console.log(`=======================================================`);
});
