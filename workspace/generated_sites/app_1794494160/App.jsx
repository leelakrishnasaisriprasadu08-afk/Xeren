// Xeren Progressive Car Showroom React.js Component
import React, { useState } from 'react';

export default function CarShowroomApp() {
    const [selectedColor, setSelectedColor] = useState('#00f0ff');
    const [engineEngaged, setEngineEngaged] = useState(false);

    const colors = [
        { name: 'Chroma Silver', hex: '#d1d5db' },
        { name: 'Apex Cyan', hex: '#00f0ff' },
        { name: 'Stealth Black', hex: '#0f172a' },
        { name: 'Hyper Red', hex: '#ef4444' },
        { name: 'Solar Gold', hex: '#f59e0b' },
    ];

    return (
        <div style={{ minHeight: '100vh', background: '#070a13', color: '#f8fafc', padding: '2rem', fontFamily: 'sans-serif' }}>
            <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #1e293b', paddingBottom: '1rem', marginBottom: '2rem' }}>
                <h1 style={{ fontSize: '1.75rem', fontWeight: 800, color: '#00f0ff' }}>
                    XEREN APEX 3D SHOWROOM
                </h1>
                <button
                    onClick={() => setEngineEngaged(!engineEngaged)}
                    style={{ padding: '0.6rem 1.5rem', borderRadius: '9999px', background: engineEngaged ? '#ef4444' : '#00f0ff', color: '#000', fontWeight: 'bold', border: 'none', cursor: 'pointer' }}
                >
                    {engineEngaged ? 'Disengage Thrusters' : 'Engage 1,450 HP'}
                </button>
            </header>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
                <div style={{ background: 'rgba(15, 23, 42, 0.8)', padding: '1.5rem', borderRadius: '1rem', border: '1px solid #334155' }}>
                    <span style={{ color: '#94a3b8' }}>0-100 km/h</span>
                    <h2 style={{ color: '#00f0ff', fontSize: '2rem', margin: '0.25rem 0' }}>1.89s</h2>
                </div>
                <div style={{ background: 'rgba(15, 23, 42, 0.8)', padding: '1.5rem', borderRadius: '1rem', border: '1px solid #334155' }}>
                    <span style={{ color: '#94a3b8' }}>Powertrain</span>
                    <h2 style={{ color: '#00f0ff', fontSize: '2rem', margin: '0.25rem 0' }}>1,450 HP</h2>
                </div>
                <div style={{ background: 'rgba(15, 23, 42, 0.8)', padding: '1.5rem', borderRadius: '1rem', border: '1px solid #334155' }}>
                    <span style={{ color: '#94a3b8' }}>Solid-State Range</span>
                    <h2 style={{ color: '#00f0ff', fontSize: '2rem', margin: '0.25rem 0' }}>850 km</h2>
                </div>
                <div style={{ background: 'rgba(15, 23, 42, 0.8)', padding: '1.5rem', borderRadius: '1rem', border: '1px solid #334155' }}>
                    <span style={{ color: '#94a3b8' }}>Neural Copilot</span>
                    <h2 style={{ color: '#00f0ff', fontSize: '2rem', margin: '0.25rem 0' }}>Level 4</h2>
                </div>
            </div>

            <div style={{ background: 'rgba(15, 23, 42, 0.8)', padding: '1.5rem', borderRadius: '1rem', border: '1px solid #334155' }}>
                <h3>Select Paint Finish:</h3>
                <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
                    {colors.map((c) => (
                        <button
                            key={c.hex}
                            onClick={() => setSelectedColor(c.hex)}
                            style={{ width: '40px', height: '40px', borderRadius: '50%', background: c.hex, border: selectedColor === c.hex ? '3px solid #00f0ff' : 'none', cursor: 'pointer' }}
                            title={c.name}
                        />
                    ))}
                </div>
            </div>
        </div>
    );
}
