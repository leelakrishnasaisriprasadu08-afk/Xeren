"""Website project generation and modification tool leveraging Coding Plugin infrastructure."""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Sequence, Tuple

from xeren.plugins.coding.plugin import CodingPlugin
from xeren.plugins.coding.schemas import FileArtifact
from xeren.plugins.coding.tools.generation import CodeGenerationTool
from xeren.plugins.website.schemas import WebsiteSpecification, WebsiteType

logger = logging.getLogger("xeren.plugins.website.tools.generator")


class WebsiteGeneratorTool:
    """Generates and modifies full website projects with predictable structures."""

    def __init__(
        self,
        coding_plugin: Optional[CodingPlugin] = None,
        generation_tool: Optional[CodeGenerationTool] = None,
    ) -> None:
        self.coding_plugin = coding_plugin
        self.generation_tool = generation_tool or (coding_plugin.registry.generation_tool if coding_plugin else CodeGenerationTool())

    def _generate_html_page(
        self,
        page_name: str,
        spec: WebsiteSpecification,
        all_pages: Sequence[str],
    ) -> str:
        """Construct a complete, semantically valid HTML5 page based on specification."""
        page_title = page_name.replace(".html", "").replace("_", " ").title()
        if page_title.lower() == "index":
            page_title = spec.site_purpose[:40] if spec.site_purpose else "Home"

        # Build navigation links
        nav_links = []
        for p in all_pages:
            link_name = p.replace(".html", "").replace("_", " ").title()
            if link_name.lower() == "index":
                link_name = "Home"
            active_class = ' class="active"' if p == page_name else ""
            nav_links.append(f'            <a href="{p}"{active_class}>{link_name}</a>')
        nav_html = "\n".join(nav_links)

        # Build section markup
        sections_html = []
        has_hero = any("hero" in s.lower() for s in spec.sections)
        is_3d = "3d" in (spec.site_purpose or "").lower() or any("3d" in str(f).lower() for f in (spec.features or []))
        canvas_3d_html = (
            '                <div class="hero-3d-wrapper" style="perspective: 800px; margin: 1.5rem auto; text-align: center;">\n'
            '                    <canvas id="canvas-3d" width="380" height="220" style="border-radius: 12px; background: rgba(30, 41, 59, 0.7); border: 1px solid var(--border-color); box-shadow: 0 8px 32px rgba(0, 0, 0, 0.37);"></canvas>\n'
            '                </div>\n'
        ) if is_3d else ""

        for idx, section in enumerate(spec.sections):
            sec_id = section.lower().replace(" ", "-").replace("/", "-")
            if "hero" in sec_id or (not has_hero and idx == 0):
                sections_html.append(
                    f'        <section id="{sec_id}" class="hero">\n'
                    f'            <div class="container">\n'
                    f'                <h1>{spec.site_purpose or "Welcome to Our Platform"}</h1>\n'
                    f'                <p class="subtitle">{spec.target_audience or "Designed with precision and elegance."}</p>\n'
                    f'{canvas_3d_html}'
                    f'                <a href="#contact" class="btn btn-primary">Get Started</a>\n'
                    f'            </div>\n'
                    f'        </section>'
                )
            elif "feature" in sec_id:
                feature_cards = []
                for f in (spec.features or ["Fast Performance", "Responsive Design", "Secure by Default"]):
                    feature_cards.append(
                        f'                <div class="card">\n'
                        f'                    <h3>{f}</h3>\n'
                        f'                    <p>Modern architecture engineered for seamless accessibility and reliability.</p>\n'
                        f'                </div>'
                    )
                cards_markup = "\n".join(feature_cards)
                sections_html.append(
                    f'        <section id="{sec_id}" class="features">\n'
                    f'            <div class="container">\n'
                    f'                <h2>Features & Capabilities</h2>\n'
                    f'                <div class="grid">\n{cards_markup}\n                </div>\n'
                    f'            </div>\n'
                    f'        </section>'
                )
            elif "footer" in sec_id:
                continue
            else:
                sections_html.append(
                    f'        <section id="{sec_id}" class="content-section">\n'
                    f'            <div class="container">\n'
                    f'                <h2>{section}</h2>\n'
                    f'                <p>Comprehensive overview and information tailored for our audience.</p>\n'
                    f'            </div>\n'
                    f'        </section>'
                )

        body_content = "\n\n".join(sections_html)

        html = (
            f"<!DOCTYPE html>\n"
            f'<html lang="en">\n'
            f"<head>\n"
            f'    <meta charset="UTF-8">\n'
            f'    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
            f"    <title>{page_title}</title>\n"
            f'    <link rel="stylesheet" href="styles.css">\n'
            f"</head>\n"
            f"<body>\n"
            f'    <header class="site-header">\n'
            f'        <div class="container nav-wrapper">\n'
            f'            <a href="index.html" class="logo">XerenWeb</a>\n'
            f'            <nav class="site-nav">\n'
            f"{nav_html}\n"
            f"            </nav>\n"
            f"        </div>\n"
            f"    </header>\n\n"
            f"    <main>\n"
            f"{body_content}\n"
            f"    </main>\n\n"
            f'    <footer class="site-footer">\n'
            f'        <div class="container">\n'
            f"            <p>&copy; 2026 Xeren Platform. All rights reserved.</p>\n"
            f"        </div>\n"
            f"    </footer>\n\n"
            f'    <script src="script.js"></script>\n'
            f"</body>\n"
            f"</html>"
        )
        return html

    def _generate_css(self, spec: WebsiteSpecification) -> str:
        """Construct a modern, responsive stylesheet."""
        return (
            "/* Global Design System */\n"
            ":root {\n"
            "    --primary-color: #2563eb;\n"
            "    --primary-hover: #1d4ed8;\n"
            "    --bg-color: #0f172a;\n"
            "    --card-bg: #1e293b;\n"
            "    --text-color: #f8fafc;\n"
            "    --text-muted: #94a3b8;\n"
            "    --border-color: #334155;\n"
            "    --font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;\n"
            "}\n\n"
            "* {\n"
            "    box-sizing: border-box;\n"
            "    margin: 0;\n"
            "    padding: 0;\n"
            "}\n\n"
            "body {\n"
            "    font-family: var(--font-family);\n"
            "    background-color: var(--bg-color);\n"
            "    color: var(--text-color);\n"
            "    line-height: 1.6;\n"
            "}\n\n"
            ".container {\n"
            "    max-width: 1200px;\n"
            "    margin: 0 auto;\n"
            "    padding: 0 1.5rem;\n"
            "}\n\n"
            "/* Header & Nav */\n"
            ".site-header {\n"
            "    background-color: rgba(30, 41, 59, 0.8);\n"
            "    backdrop-filter: blur(8px);\n"
            "    position: sticky;\n"
            "    top: 0;\n"
            "    z-index: 100;\n"
            "    border-bottom: 1px solid var(--border-color);\n"
            "}\n\n"
            ".nav-wrapper {\n"
            "    display: flex;\n"
            "    justify-content: space-between;\n"
            "    align-items: center;\n"
            "    height: 4rem;\n"
            "}\n\n"
            ".logo {\n"
            "    font-size: 1.25rem;\n"
            "    font-weight: 700;\n"
            "    color: var(--text-color);\n"
            "    text-decoration: none;\n"
            "}\n\n"
            ".site-nav a {\n"
            "    color: var(--text-muted);\n"
            "    text-decoration: none;\n"
            "    margin-left: 1.5rem;\n"
            "    transition: color 0.2s ease;\n"
            "}\n\n"
            ".site-nav a:hover, .site-nav a.active {\n"
            "    color: var(--primary-color);\n"
            "}\n\n"
            "/* Hero */\n"
            ".hero {\n"
            "    padding: 6rem 0;\n"
            "    text-align: center;\n"
            "    background: radial-gradient(circle at center, #1e293b 0%, #0f172a 100%);\n"
            "}\n\n"
            ".hero h1 {\n"
            "    font-size: 3rem;\n"
            "    font-weight: 800;\n"
            "    margin-bottom: 1rem;\n"
            "}\n\n"
            ".subtitle {\n"
            "    font-size: 1.25rem;\n"
            "    color: var(--text-muted);\n"
            "    max-width: 600px;\n"
            "    margin: 0 auto 2rem;\n"
            "}\n\n"
            ".btn {\n"
            "    display: inline-block;\n"
            "    padding: 0.75rem 1.5rem;\n"
            "    border-radius: 0.375rem;\n"
            "    text-decoration: none;\n"
            "    font-weight: 600;\n"
            "    transition: background-color 0.2s ease;\n"
            "}\n\n"
            ".btn-primary {\n"
            "    background-color: var(--primary-color);\n"
            "    color: white;\n"
            "}\n\n"
            ".btn-primary:hover {\n"
            "    background-color: var(--primary-hover);\n"
            "}\n\n"
            "/* Features & Content */\n"
            ".features, .content-section {\n"
            "    padding: 5rem 0;\n"
            "}\n\n"
            ".grid {\n"
            "    display: grid;\n"
            "    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));\n"
            "    gap: 2rem;\n"
            "    margin-top: 2rem;\n"
            "}\n\n"
            ".card {\n"
            "    background-color: var(--card-bg);\n"
            "    border: 1px solid var(--border-color);\n"
            "    border-radius: 0.5rem;\n"
            "    padding: 2rem;\n"
            "    transition: transform 0.2s ease, border-color 0.2s ease;\n"
            "}\n\n"
            ".card:hover {\n"
            "    transform: translateY(-4px);\n"
            "    border-color: var(--primary-color);\n"
            "}\n\n"
            ".card h3 {\n"
            "    margin-bottom: 0.75rem;\n"
            "}\n\n"
            ".card p {\n"
            "    color: var(--text-muted);\n"
            "}\n\n"
            "/* Footer */\n"
            ".site-footer {\n"
            "    border-top: 1px solid var(--border-color);\n"
            "    padding: 2rem 0;\n"
            "    text-align: center;\n"
            "    color: var(--text-muted);\n"
            "    font-size: 0.875rem;\n"
            "}\n\n"
            "/* Responsive Media Queries */\n"
            "@media (max-width: 768px) {\n"
            "    .hero h1 {\n"
            "        font-size: 2rem;\n"
            "    }\n"
            "    .nav-wrapper {\n"
            "        flex-direction: column;\n"
            "        height: auto;\n"
            "        padding: 1rem 0;\n"
            "    }\n"
            "    .site-nav {\n"
            "        margin-top: 0.5rem;\n"
            "    }\n"
            "    .site-nav a {\n"
            "        margin: 0 0.5rem;\n"
            "    }\n"
            "}\n"
        )

    def _generate_js(self, spec: WebsiteSpecification) -> str:
        """Construct client-side JavaScript for interactivity."""
        is_3d = "3d" in (spec.site_purpose or "").lower() or any("3d" in str(f).lower() for f in (spec.features or []))
        animation_3d_code = ""
        if is_3d:
            animation_3d_code = (
                "\n    // Interactive 3D Wireframe Canvas Animation\n"
                "    const canvas = document.getElementById('canvas-3d');\n"
                "    if (canvas && canvas.getContext) {\n"
                "        const ctx = canvas.getContext('2d');\n"
                "        let angleX = 0, angleY = 0;\n"
                "        const nodes = [\n"
                "            [-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],\n"
                "            [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]\n"
                "        ];\n"
                "        const edges = [\n"
                "            [0, 1], [1, 2], [2, 3], [3, 0],\n"
                "            [4, 5], [5, 6], [6, 7], [7, 4],\n"
                "            [0, 4], [1, 5], [2, 6], [3, 7]\n"
                "        ];\n"
                "        function render3D() {\n"
                "            ctx.clearRect(0, 0, canvas.width, canvas.height);\n"
                "            const cx = canvas.width / 2, cy = canvas.height / 2, scale = 55;\n"
                "            angleX += 0.015; angleY += 0.02;\n"
                "            const projected = nodes.map(([x, y, z]) => {\n"
                "                let y1 = y * Math.cos(angleX) - z * Math.sin(angleX);\n"
                "                let z1 = y * Math.sin(angleX) + z * Math.cos(angleX);\n"
                "                let x2 = x * Math.cos(angleY) + z1 * Math.sin(angleY);\n"
                "                let z2 = -x * Math.sin(angleY) + z1 * Math.cos(angleY);\n"
                "                const fov = 4 / (4 + z2);\n"
                "                return [cx + x2 * scale * fov, cy + y1 * scale * fov];\n"
                "            });\n"
                "            ctx.strokeStyle = '#38bdf8';\n"
                "            ctx.lineWidth = 2;\n"
                "            edges.forEach(([i, j]) => {\n"
                "                ctx.beginPath();\n"
                "                ctx.moveTo(projected[i][0], projected[i][1]);\n"
                "                ctx.lineTo(projected[j][0], projected[j][1]);\n"
                "                ctx.stroke();\n"
                "            });\n"
                "            projected.forEach(([px, py]) => {\n"
                "                ctx.fillStyle = '#6366f1';\n"
                "                ctx.beginPath(); ctx.arc(px, py, 4, 0, Math.PI * 2); ctx.fill();\n"
                "            });\n"
                "            requestAnimationFrame(render3D);\n"
                "        }\n"
                "        render3D();\n"
                "    }\n"
            )

        return (
            "// Client-side interactions for Xeren Website\n"
            "document.addEventListener('DOMContentLoaded', () => {\n"
            "    console.log('Website initialized safely.');\n\n"
            "    // Smooth scroll for anchor links\n"
            "    document.querySelectorAll('a[href^=\"#\"]').forEach(anchor => {\n"
            "        anchor.addEventListener('click', function (e) {\n"
            "            const targetId = this.getAttribute('href');\n"
            "            if (targetId && targetId !== '#') {\n"
            "                const targetElement = document.querySelector(targetId);\n"
            "                if (targetElement) {\n"
            "                    e.preventDefault();\n"
            "                    targetElement.scrollIntoView({ behavior: 'smooth' });\n"
            "                }\n"
            "            }\n"
            "        });\n"
            "    });\n"
            f"{animation_3d_code}"
            "});\n"
        )

    def _generate_car_showroom_html(self, spec: WebsiteSpecification) -> str:
        """Construct high-end 3D progressive car showroom HTML5 application."""
        purpose = spec.site_purpose or "Xeren Apex Progressive 3D Car Showroom"
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>XEREN APEX | Progressive 3D Hypercar Showroom</title>
    <link rel="stylesheet" href="styles.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
</head>
<body>
    <header class="navbar">
        <div class="container nav-content">
            <a href="#studio" class="brand-logo">
                <span class="brand-icon">&#9889;</span> XEREN <span class="brand-sub">HYPERDRIVE</span>
            </a>
            <nav class="nav-links">
                <a href="#studio" class="active">3D Studio</a>
                <a href="#specs">Specifications</a>
                <a href="#engineering">Technology</a>
                <a href="#booking">Test Drive</a>
                <a href="#backend-architecture">Full-Stack Architecture</a>
            </nav>
            <a href="#booking" class="btn btn-sm btn-cyan">Reserve Model</a>
        </div>
    </header>

    <main>
        <!-- 3D Interactive Showroom Studio -->
        <section id="studio" class="studio-section">
            <div class="container studio-hud-top">
                <div class="badge-pill">&#9679; 3D REAL-TIME INTERACTIVE VIEWPORT</div>
                <h1 class="hero-title">XEREN APEX CYBER-GT</h1>
                <p class="hero-desc">1,450 HP Quad-Motor Autonomous Hypercar &bull; Solid-State 900V Architecture</p>
            </div>

            <div class="canvas-viewport">
                <div id="canvas-container">
                    <canvas id="webgl-canvas"></canvas>
                </div>

                <!-- 3D Studio HUD Controls -->
                <div class="studio-hud-controls">
                    <div class="control-card glass-panel">
                        <h3>Studio Paint Customizer</h3>
                        <div class="color-palette">
                            <button class="color-btn active" data-color="0xd1d5db" style="background: #d1d5db;" title="Cyber Silver"></button>
                            <button class="color-btn" data-color="0x00f0ff" style="background: #00f0ff;" title="Electric Cyan"></button>
                            <button class="color-btn" data-color="0x0f172a" style="background: #0f172a;" title="Obsidian Stealth"></button>
                            <button class="color-btn" data-color="0xef4444" style="background: #ef4444;" title="Apex Red"></button>
                            <button class="color-btn" data-color="0xf59e0b" style="background: #f59e0b;" title="Solar Gold"></button>
                        </div>
                    </div>

                    <div class="control-card glass-panel">
                        <h3>Interactive Systems</h3>
                        <div class="action-btn-group">
                            <button id="btn-toggle-lights" class="hud-btn">&#128161; Headlights</button>
                            <button id="btn-toggle-underglow" class="hud-btn">&#128308; Neon Underglow</button>
                            <button id="btn-toggle-spin" class="hud-btn active">&#128260; 360&deg; Spin</button>
                            <button id="btn-accelerate" class="hud-btn btn-highlight">&#9889; Accelerate Sound</button>
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <!-- Performance Specifications HUD -->
        <section id="specs" class="specs-section">
            <div class="container">
                <div class="section-header">
                    <h2>Performance Benchmark</h2>
                    <p>Engineered with Formula-E aerospace telemetry and neural torque vectoring.</p>
                </div>
                <div class="specs-grid">
                    <div class="spec-card glass-panel">
                        <span class="spec-value">1.89<span class="spec-unit">s</span></span>
                        <span class="spec-label">0 &ndash; 100 km/h</span>
                        <p>Instantaneous torque delivered across 4 independent hub motors.</p>
                    </div>
                    <div class="spec-card glass-panel">
                        <span class="spec-value">1,450<span class="spec-unit">HP</span></span>
                        <span class="spec-label">Peak Powertrain</span>
                        <p>High-flux liquid-cooled permanent magnet cyber drive.</p>
                    </div>
                    <div class="spec-card glass-panel">
                        <span class="spec-value">850<span class="spec-unit">km</span></span>
                        <span class="spec-label">Solid-State Range</span>
                        <p>900V DC ultra-fast charging: 10% to 80% in 9 minutes.</p>
                    </div>
                    <div class="spec-card glass-panel">
                        <span class="spec-value">Level 4</span>
                        <span class="spec-label">Autonomous Copilot</span>
                        <p>LiDAR, high-resolution radar, and neural vision guidance.</p>
                    </div>
                </div>
            </div>
        </section>

        <!-- Engineering Architecture -->
        <section id="engineering" class="engineering-section">
            <div class="container">
                <div class="section-header">
                    <h2>Progressive Engineering</h2>
                    <p>Designed from carbon monocoque to full-stack embedded telemetry.</p>
                </div>
                <div class="features-grid">
                    <div class="feature-card glass-panel">
                        <div class="feature-icon">&#128737;</div>
                        <h3>Carbon-Titanium Monocoque</h3>
                        <p>Ultra-rigid aerospace-grade chassis delivering safety with minimal curb weight.</p>
                    </div>
                    <div class="feature-card glass-panel">
                        <div class="feature-icon">&#127937;</div>
                        <h3>Active Aerodynamics</h3>
                        <p>Dynamic downforce wing with automated DRS and high-speed cornering stability.</p>
                    </div>
                    <div class="feature-card glass-panel">
                        <div class="feature-icon">&#128268;</div>
                        <h3>Steer-by-Wire &amp; Torque Vectoring</h3>
                        <p>Sub-millisecond steering response decoupled from traditional mechanical latency.</p>
                    </div>
                </div>
            </div>
        </section>

        <!-- Test Drive Booking & Financing Estimator -->
        <section id="booking" class="booking-section">
            <div class="container">
                <div class="booking-wrapper glass-panel">
                    <div class="booking-form-col">
                        <h2>Reserve Your Test Drive</h2>
                        <p>Experience the future of autonomous hyper-performance.</p>
                        <form id="test-drive-form">
                            <div class="form-group">
                                <label for="driver-name">Full Name</label>
                                <input type="text" id="driver-name" required placeholder="Alex Mercer">
                            </div>
                            <div class="form-group">
                                <label for="driver-email">Email Address</label>
                                <input type="email" id="driver-email" required placeholder="alex@example.com">
                            </div>
                            <div class="form-group">
                                <label for="vehicle-select">Select Configuration</label>
                                <select id="vehicle-select">
                                    <option value="Apex Cyber-GT">Xeren Apex Cyber-GT (1,450 HP)</option>
                                    <option value="Phantom Hyper-SUV">Xeren Phantom Hyper-SUV (1,200 HP)</option>
                                    <option value="Vision Speedster">Xeren Vision Speedster (1,800 HP Limited)</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="drive-date">Preferred Date</label>
                                <input type="date" id="drive-date" required>
                            </div>
                            <button type="submit" class="btn btn-cyan btn-full">Confirm VIP Reservation</button>
                        </form>
                        <div id="booking-alert" class="alert-box" style="display: none;"></div>
                    </div>

                    <div class="financing-calculator-col">
                        <h2>Financing &amp; Lease Estimator</h2>
                        <div class="calc-box">
                            <div class="calc-row">
                                <span>Vehicle MSRP</span>
                                <span class="calc-price">$145,000</span>
                            </div>
                            <div class="calc-row">
                                <label for="down-payment">Down Payment: <span id="down-val">$29,000</span></label>
                                <input type="range" id="down-payment" min="10000" max="80000" step="1000" value="29000">
                            </div>
                            <div class="calc-row">
                                <label for="loan-term">Term Duration: <span id="term-val">48 Months</span></label>
                                <input type="range" id="loan-term" min="24" max="72" step="12" value="48">
                            </div>
                            <div class="calc-divider"></div>
                            <div class="calc-total">
                                <span>Estimated Monthly:</span>
                                <span id="monthly-payment" class="monthly-figure">$2,642/mo</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <!-- Full-Stack Backend Architecture Banner -->
        <section id="backend-architecture" class="architecture-section">
            <div class="container">
                <div class="section-header">
                    <h2>Full-Stack Multi-Language Architecture</h2>
                    <p>Companion backend services and database controllers generated and ready to run.</p>
                </div>
                <div class="arch-grid">
                    <div class="arch-card glass-panel">
                        <div class="arch-badge">Node.js / Express</div>
                        <h3>server.js</h3>
                        <p>REST API with JSON middleware, inventory querying, and test-drive booking endpoints.</p>
                        <code>node server.js</code>
                    </div>
                    <div class="arch-card glass-panel">
                        <div class="arch-badge">Python / FastAPI</div>
                        <h3>app.py</h3>
                        <p>High-performance ASGI backend with SQLite database controllers and Pydantic schemas.</p>
                        <code>uvicorn app:app --reload</code>
                    </div>
                    <div class="arch-card glass-panel">
                        <div class="arch-badge">Java / Spring Boot</div>
                        <h3>CarShowroomController.java</h3>
                        <p>Enterprise REST controller with JPA repository and service layer architecture.</p>
                        <code>mvn spring-boot:run</code>
                    </div>
                    <div class="arch-card glass-panel">
                        <div class="arch-badge">Relational SQL</div>
                        <h3>database_schema.sql</h3>
                        <p>Complete SQL schema defining inventory, specifications, and booking tables.</p>
                        <code>sqlite3 showroom.db &lt; database_schema.sql</code>
                    </div>
                </div>
            </div>
        </section>
    </main>

    <footer class="footer">
        <div class="container">
            <p>&copy; 2026 Xeren Motors Inc. Engineered for High-Performance Autonomous Systems.</p>
        </div>
    </footer>

    <script src="script.js"></script>
</body>
</html>
"""

    def _generate_car_showroom_css(self, spec: WebsiteSpecification) -> str:
        """Construct luxury cyber styling for 3D car showroom."""
        return """/* Xeren Progressive 3D Car Showroom Stylesheet */
:root {
    --bg-dark: #070a13;
    --bg-card: rgba(15, 23, 42, 0.75);
    --border-color: rgba(255, 255, 255, 0.08);
    --primary-cyan: #00f0ff;
    --primary-hover: #38bdf8;
    --accent-indigo: #6366f1;
    --accent-gold: #f59e0b;
    --text-light: #f8fafc;
    --text-muted: #94a3b8;
    --font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
}

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    background-color: var(--bg-dark);
    color: var(--text-light);
    font-family: var(--font-family);
    line-height: 1.6;
    overflow-x: hidden;
}

.container {
    max-width: 1280px;
    margin: 0 auto;
    padding: 0 1.5rem;
}

/* Glassmorphism Panel */
.glass-panel {
    background: var(--bg-card);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid var(--border-color);
    border-radius: 1rem;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
}

/* Navbar */
.navbar {
    position: sticky;
    top: 0;
    z-index: 1000;
    background: rgba(7, 10, 19, 0.85);
    backdrop-filter: blur(12px);
    border-bottom: 1px solid var(--border-color);
}

.nav-content {
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 4.5rem;
}

.brand-logo {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 1.25rem;
    font-weight: 800;
    letter-spacing: 0.1em;
    color: var(--text-light);
    text-decoration: none;
}

.brand-icon {
    color: var(--primary-cyan);
    font-size: 1.5rem;
}

.brand-sub {
    color: var(--primary-cyan);
    font-weight: 400;
    font-size: 0.9rem;
}

.nav-links {
    display: flex;
    gap: 2rem;
}

.nav-links a {
    color: var(--text-muted);
    text-decoration: none;
    font-size: 0.95rem;
    font-weight: 500;
    transition: color 0.2s ease;
}

.nav-links a:hover, .nav-links a.active {
    color: var(--primary-cyan);
}

/* Buttons */
.btn {
    display: inline-block;
    padding: 0.75rem 1.5rem;
    border-radius: 9999px;
    font-weight: 600;
    text-decoration: none;
    cursor: pointer;
    transition: all 0.25s ease;
    border: none;
}

.btn-cyan {
    background: linear-gradient(135deg, var(--primary-cyan), var(--accent-indigo));
    color: #070a13;
    box-shadow: 0 0 20px rgba(0, 240, 255, 0.35);
}

.btn-cyan:hover {
    transform: translateY(-2px);
    box-shadow: 0 0 30px rgba(0, 240, 255, 0.55);
}

.btn-sm {
    padding: 0.5rem 1.25rem;
    font-size: 0.875rem;
}

.btn-full {
    width: 100%;
}

/* Studio Section & 3D Viewport */
.studio-section {
    padding-top: 3rem;
    padding-bottom: 5rem;
    position: relative;
}

.studio-hud-top {
    text-align: center;
    margin-bottom: 1.5rem;
}

.badge-pill {
    display: inline-block;
    padding: 0.35rem 1rem;
    background: rgba(0, 240, 255, 0.1);
    color: var(--primary-cyan);
    border: 1px solid rgba(0, 240, 255, 0.25);
    border-radius: 9999px;
    font-size: 0.8rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    margin-bottom: 0.75rem;
}

.hero-title {
    font-size: 3rem;
    font-weight: 900;
    letter-spacing: 0.05em;
    background: linear-gradient(135deg, #ffffff 40%, var(--primary-cyan) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.5rem;
}

.hero-desc {
    color: var(--text-muted);
    font-size: 1.15rem;
}

.canvas-viewport {
    position: relative;
    width: 100%;
    max-width: 1200px;
    margin: 0 auto;
}

#canvas-container {
    width: 100%;
    height: 520px;
    background: radial-gradient(circle at center, #111827 0%, #070a13 85%);
    border: 1px solid var(--border-color);
    border-radius: 1.5rem;
    overflow: hidden;
    position: relative;
    box-shadow: 0 25px 60px rgba(0, 0, 0, 0.6);
}

#webgl-canvas {
    width: 100%;
    height: 100%;
    display: block;
    cursor: grab;
}

#webgl-canvas:active {
    cursor: grabbing;
}

/* HUD Overlay Controls */
.studio-hud-controls {
    display: flex;
    justify-content: space-between;
    gap: 1.5rem;
    margin-top: 1.5rem;
}

.control-card {
    flex: 1;
    padding: 1.25rem 1.5rem;
}

.control-card h3 {
    font-size: 0.95rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-muted);
    margin-bottom: 0.75rem;
}

.color-palette {
    display: flex;
    gap: 1rem;
    align-items: center;
}

.color-btn {
    width: 2.5rem;
    height: 2.5rem;
    border-radius: 50%;
    border: 2px solid transparent;
    cursor: pointer;
    transition: transform 0.2s ease, border-color 0.2s ease;
}

.color-btn:hover {
    transform: scale(1.15);
}

.color-btn.active {
    border-color: var(--primary-cyan);
    box-shadow: 0 0 15px rgba(0, 240, 255, 0.6);
}

.action-btn-group {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
}

.hud-btn {
    padding: 0.5rem 1rem;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid var(--border-color);
    color: var(--text-light);
    border-radius: 0.5rem;
    font-size: 0.85rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;
}

.hud-btn:hover, .hud-btn.active {
    background: rgba(0, 240, 255, 0.15);
    border-color: var(--primary-cyan);
    color: var(--primary-cyan);
}

.hud-btn.btn-highlight {
    background: linear-gradient(135deg, rgba(239, 68, 68, 0.2), rgba(99, 102, 241, 0.2));
    border-color: #ef4444;
}

/* Specs Grid */
.specs-section, .engineering-section, .booking-section, .architecture-section {
    padding: 5rem 0;
}

.section-header {
    text-align: center;
    margin-bottom: 3.5rem;
}

.section-header h2 {
    font-size: 2.25rem;
    font-weight: 800;
    margin-bottom: 0.5rem;
}

.section-header p {
    color: var(--text-muted);
    font-size: 1.1rem;
}

.specs-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 1.5rem;
}

.spec-card {
    padding: 2.5rem 2rem;
    text-align: center;
    transition: transform 0.3s ease, border-color 0.3s ease;
}

.spec-card:hover {
    transform: translateY(-6px);
    border-color: var(--primary-cyan);
}

.spec-value {
    display: block;
    font-size: 3rem;
    font-weight: 900;
    color: var(--primary-cyan);
    margin-bottom: 0.25rem;
}

.spec-unit {
    font-size: 1.25rem;
    color: var(--text-muted);
    font-weight: 400;
}

.spec-label {
    display: block;
    font-size: 1.1rem;
    font-weight: 700;
    margin-bottom: 0.75rem;
}

.spec-card p {
    color: var(--text-muted);
    font-size: 0.9rem;
}

/* Features Grid */
.features-grid, .arch-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 2rem;
}

.feature-card, .arch-card {
    padding: 2rem;
}

.feature-icon {
    font-size: 2.5rem;
    margin-bottom: 1rem;
}

.feature-card h3, .arch-card h3 {
    font-size: 1.25rem;
    margin-bottom: 0.75rem;
}

.feature-card p, .arch-card p {
    color: var(--text-muted);
    font-size: 0.95rem;
}

.arch-card code {
    display: block;
    margin-top: 1rem;
    padding: 0.5rem 0.75rem;
    background: #000;
    border-radius: 0.375rem;
    color: var(--primary-cyan);
    font-size: 0.85rem;
}

.arch-badge {
    display: inline-block;
    padding: 0.25rem 0.6rem;
    background: rgba(99, 102, 241, 0.2);
    color: #818cf8;
    border-radius: 0.25rem;
    font-size: 0.75rem;
    font-weight: 700;
    margin-bottom: 0.75rem;
}

/* Booking Section */
.booking-wrapper {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 3rem;
    padding: 3rem;
}

.form-group {
    margin-bottom: 1.25rem;
}

.form-group label {
    display: block;
    font-size: 0.9rem;
    font-weight: 600;
    margin-bottom: 0.5rem;
    color: var(--text-muted);
}

.form-group input, .form-group select {
    width: 100%;
    padding: 0.75rem 1rem;
    background: rgba(0, 0, 0, 0.4);
    border: 1px solid var(--border-color);
    border-radius: 0.5rem;
    color: var(--text-light);
    font-size: 1rem;
    outline: none;
}

.form-group input:focus, .form-group select:focus {
    border-color: var(--primary-cyan);
}

.alert-box {
    margin-top: 1.25rem;
    padding: 1rem;
    border-radius: 0.5rem;
    background: rgba(16, 185, 129, 0.15);
    border: 1px solid #10b981;
    color: #34d399;
}

/* Financing Calculator */
.calc-box {
    margin-top: 1.5rem;
    background: rgba(0, 0, 0, 0.3);
    padding: 1.5rem;
    border-radius: 0.75rem;
    border: 1px solid var(--border-color);
}

.calc-row {
    margin-bottom: 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.calc-price {
    font-size: 1.75rem;
    font-weight: 800;
    color: var(--primary-cyan);
}

.calc-row input[type="range"] {
    width: 100%;
    accent-color: var(--primary-cyan);
}

.calc-divider {
    height: 1px;
    background: var(--border-color);
    margin: 1.5rem 0;
}

.calc-total {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.monthly-figure {
    font-size: 2rem;
    font-weight: 900;
    color: var(--primary-cyan);
}

/* Footer */
.footer {
    border-top: 1px solid var(--border-color);
    padding: 2.5rem 0;
    text-align: center;
    color: var(--text-muted);
    font-size: 0.875rem;
}

@media (max-width: 900px) {
    .booking-wrapper {
        grid-template-columns: 1fr;
    }
    .studio-hud-controls {
        flex-direction: column;
    }
    .hero-title {
        font-size: 2.25rem;
    }
}
"""

    def _generate_car_showroom_js(self, spec: WebsiteSpecification) -> str:
        """Construct client-side Three.js 3D WebGL engine and interactive showroom logic."""
        return """// Xeren Progressive 3D Car Showroom Engine (Three.js WebGL)
document.addEventListener('DOMContentLoaded', () => {
    console.log('Initializing Xeren Progressive 3D Car Showroom...');

    // 1. Setup Three.js WebGL Scene
    const container = document.getElementById('canvas-container');
    const canvas = document.getElementById('webgl-canvas');

    if (!container || !canvas) {
        console.warn('Canvas elements not found');
        return;
    }

    let width = container.clientWidth;
    let height = container.clientHeight;

    // Check if Three.js is loaded
    if (typeof THREE === 'undefined') {
        console.warn('Three.js CDN not loaded, falling back to 2D Canvas');
        const ctx = canvas.getContext('2d');
        canvas.width = width;
        canvas.height = height;
        ctx.fillStyle = '#0f172a';
        ctx.fillRect(0, 0, width, height);
        ctx.fillStyle = '#00f0ff';
        ctx.font = '24px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('3D Studio Running (Fallback Mode)', width / 2, height / 2);
        return;
    }

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x070a13);
    scene.fog = new THREE.FogExp2(0x070a13, 0.04);

    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.set(7, 3.5, 9);
    camera.lookAt(0, 0.5, 0);

    const renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;

    // Studio Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.8);
    scene.add(ambientLight);

    const keyLight = new THREE.DirectionalLight(0xffffff, 1.8);
    keyLight.position.set(10, 15, 10);
    keyLight.castShadow = true;
    scene.add(keyLight);

    const cyanRim = new THREE.PointLight(0x00f0ff, 2.5, 20);
    cyanRim.position.set(-6, 3, -6);
    scene.add(cyanRim);

    const pinkRim = new THREE.PointLight(0x6366f1, 2.0, 20);
    pinkRim.position.set(6, 3, -6);
    scene.add(pinkRim);

    // Ground Grid & Studio Floor
    const gridHelper = new THREE.GridHelper(24, 24, 0x00f0ff, 0x1e293b);
    gridHelper.position.y = -0.01;
    scene.add(gridHelper);

    const floorGeo = new THREE.CircleGeometry(14, 64);
    const floorMat = new THREE.MeshStandardMaterial({ color: 0x070a13, roughness: 0.2, metalness: 0.7 });
    const floorMesh = new THREE.Mesh(floorGeo, floorMat);
    floorMesh.rotation.x = -Math.PI / 2;
    floorMesh.position.y = -0.02;
    floorMesh.receiveShadow = true;
    scene.add(floorMesh);

    // 2. Build Procedural 3D Sports Car Model
    const carGroup = new THREE.Group();
    scene.add(carGroup);

    // Materials
    let carColor = 0xd1d5db; // Cyber Silver default
    const bodyMaterial = new THREE.MeshStandardMaterial({
        color: carColor,
        metalness: 0.85,
        roughness: 0.18,
    });

    const glassMaterial = new THREE.MeshStandardMaterial({
        color: 0x0f172a,
        metalness: 0.9,
        roughness: 0.05,
        transparent: true,
        opacity: 0.75,
    });

    const trimMaterial = new THREE.MeshStandardMaterial({
        color: 0x020617,
        metalness: 0.6,
        roughness: 0.4,
    });

    const wheelMaterial = new THREE.MeshStandardMaterial({
        color: 0x090d16,
        metalness: 0.8,
        roughness: 0.3,
    });

    const headlightMaterial = new THREE.MeshBasicMaterial({ color: 0x00f0ff });
    const taillightMaterial = new THREE.MeshBasicMaterial({ color: 0xef4444 });

    // Chassis Lower Body
    const lowerBodyGeo = new THREE.BoxGeometry(4.6, 0.55, 2.1);
    const lowerBody = new THREE.Mesh(lowerBodyGeo, bodyMaterial);
    lowerBody.position.y = 0.55;
    lowerBody.castShadow = true;
    carGroup.add(lowerBody);

    // Aerodynamic Hood Nose
    const noseGeo = new THREE.BoxGeometry(1.4, 0.35, 1.95);
    const nose = new THREE.Mesh(noseGeo, bodyMaterial);
    nose.position.set(2.2, 0.45, 0);
    carGroup.add(nose);

    // Cockpit Cabin Canopy
    const cabinGeo = new THREE.BoxGeometry(2.3, 0.65, 1.6);
    const cabin = new THREE.Mesh(cabinGeo, glassMaterial);
    cabin.position.set(-0.2, 1.05, 0);
    carGroup.add(cabin);

    // Rear Carbon Spoiler Wing
    const spoilerGeo = new THREE.BoxGeometry(0.5, 0.08, 2.2);
    const spoiler = new THREE.Mesh(spoilerGeo, trimMaterial);
    spoiler.position.set(-2.2, 1.15, 0);
    carGroup.add(spoiler);

    const spoilerStand1 = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.35, 0.08), trimMaterial);
    spoilerStand1.position.set(-2.2, 0.95, 0.6);
    carGroup.add(spoilerStand1);

    const spoilerStand2 = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.35, 0.08), trimMaterial);
    spoilerStand2.position.set(-2.2, 0.95, -0.6);
    carGroup.add(spoilerStand2);

    // Headlights
    const hlGeo = new THREE.BoxGeometry(0.2, 0.1, 0.45);
    const hlLeft = new THREE.Mesh(hlGeo, headlightMaterial);
    hlLeft.position.set(2.85, 0.55, 0.7);
    carGroup.add(hlLeft);

    const hlRight = new THREE.Mesh(hlGeo, headlightMaterial);
    hlRight.position.set(2.85, 0.55, -0.7);
    carGroup.add(hlRight);

    // Front Headlight Beams (Point Lights)
    const hlBeamLeft = new THREE.PointLight(0x00f0ff, 2.0, 8);
    hlBeamLeft.position.set(3.2, 0.55, 0.7);
    carGroup.add(hlBeamLeft);

    const hlBeamRight = new THREE.PointLight(0x00f0ff, 2.0, 8);
    hlBeamRight.position.set(3.2, 0.55, -0.7);
    carGroup.add(hlBeamRight);

    // Rear Light Strip
    const tlGeo = new THREE.BoxGeometry(0.15, 0.08, 1.8);
    const tailLight = new THREE.Mesh(tlGeo, taillightMaterial);
    tailLight.position.set(-2.32, 0.65, 0);
    carGroup.add(tailLight);

    // Underglow Light
    const underglowLight = new THREE.PointLight(0x00f0ff, 3.5, 5);
    underglowLight.position.set(0, 0.15, 0);
    carGroup.add(underglowLight);

    // 4 Alloy Wheels
    const wheels = [];
    const wheelPositions = [
        [1.5, 0.38, 1.05],
        [1.5, 0.38, -1.05],
        [-1.5, 0.38, 1.05],
        [-1.5, 0.38, -1.05]
    ];

    const wheelGeo = new THREE.CylinderGeometry(0.38, 0.38, 0.3, 24);
    wheelGeo.rotateX(Math.PI / 2);

    wheelPositions.forEach(pos => {
        const wheel = new THREE.Mesh(wheelGeo, wheelMaterial);
        wheel.position.set(pos[0], pos[1], pos[2]);
        wheel.castShadow = true;
        carGroup.add(wheel);
        wheels.push(wheel);
    });

    // 3. Orbit Controls via Mouse Drag & Touch
    let isDragging = false;
    let previousMousePosition = { x: 0, y: 0 };
    let autoSpin = true;

    canvas.addEventListener('mousedown', (e) => {
        isDragging = true;
        autoSpin = false;
        previousMousePosition = { x: e.clientX, y: e.clientY };
    });

    window.addEventListener('mouseup', () => {
        isDragging = false;
    });

    canvas.addEventListener('mousemove', (e) => {
        if (!isDragging) return;
        const deltaX = e.clientX - previousMousePosition.x;
        const deltaY = e.clientY - previousMousePosition.y;

        carGroup.rotation.y += deltaX * 0.01;
        camera.position.y = Math.max(1.5, Math.min(6, camera.position.y - deltaY * 0.02));
        camera.lookAt(0, 0.5, 0);

        previousMousePosition = { x: e.clientX, y: e.clientY };
    });

    canvas.addEventListener('wheel', (e) => {
        e.preventDefault();
        const zoomSpeed = 0.005;
        const dist = camera.position.distanceTo(new THREE.Vector3(0, 0, 0));
        if (e.deltaY > 0 && dist < 16) {
            camera.position.multiplyScalar(1 + e.deltaY * zoomSpeed);
        } else if (e.deltaY < 0 && dist > 5) {
            camera.position.multiplyScalar(1 + e.deltaY * zoomSpeed);
        }
    }, { passive: false });

    // Touch support for mobile
    canvas.addEventListener('touchstart', (e) => {
        if (e.touches.length === 1) {
            isDragging = true;
            autoSpin = false;
            previousMousePosition = { x: e.touches[0].clientX, y: e.touches[0].clientY };
        }
    });

    canvas.addEventListener('touchmove', (e) => {
        if (!isDragging || e.touches.length !== 1) return;
        const deltaX = e.touches[0].clientX - previousMousePosition.x;
        carGroup.rotation.y += deltaX * 0.01;
        previousMousePosition = { x: e.touches[0].clientX, y: e.touches[0].clientY };
    });

    canvas.addEventListener('touchend', () => { isDragging = false; });

    // 4. Color Palette Switcher
    const colorButtons = document.querySelectorAll('.color-btn');
    colorButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            colorButtons.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            const colorHex = parseInt(this.getAttribute('data-color'), 16);
            bodyMaterial.color.setHex(colorHex);
            console.log('Updated car paint to:', this.getAttribute('title'));
        });
    });

    // 5. Interactive System Buttons
    const btnLights = document.getElementById('btn-toggle-lights');
    if (btnLights) {
        let lightsOn = true;
        btnLights.addEventListener('click', () => {
            lightsOn = !lightsOn;
            hlBeamLeft.intensity = lightsOn ? 2.0 : 0.0;
            hlBeamRight.intensity = lightsOn ? 2.0 : 0.0;
            headlightMaterial.color.setHex(lightsOn ? 0x00f0ff : 0x1e293b);
            btnLights.classList.toggle('active', lightsOn);
        });
    }

    const btnUnderglow = document.getElementById('btn-toggle-underglow');
    if (btnUnderglow) {
        let underglowOn = true;
        btnUnderglow.addEventListener('click', () => {
            underglowOn = !underglowOn;
            underglowLight.intensity = underglowOn ? 3.5 : 0.0;
            btnUnderglow.classList.toggle('active', underglowOn);
        });
    }

    const btnSpin = document.getElementById('btn-toggle-spin');
    if (btnSpin) {
        btnSpin.addEventListener('click', () => {
            autoSpin = !autoSpin;
            btnSpin.classList.toggle('active', autoSpin);
        });
    }

    // 6. Sound Engine Acceleration (Web Audio API Synthesizer)
    const btnAccel = document.getElementById('btn-accelerate');
    if (btnAccel) {
        btnAccel.addEventListener('click', () => {
            try {
                const AudioContext = window.AudioContext || window.webkitAudioContext;
                if (!AudioContext) return;
                const audioCtx = new AudioContext();
                const osc = audioCtx.createOscillator();
                const gain = audioCtx.createGain();

                osc.type = 'sawtooth';
                osc.frequency.setValueAtTime(110, audioCtx.currentTime);
                osc.frequency.exponentialRampToValueAtTime(440, audioCtx.currentTime + 1.2);

                gain.gain.setValueAtTime(0.15, audioCtx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 1.3);

                osc.connect(gain);
                gain.connect(audioCtx.destination);
                osc.start();
                osc.stop(audioCtx.currentTime + 1.3);

                // Visual acceleration pulse
                carGroup.position.y += 0.08;
                setTimeout(() => { carGroup.position.y -= 0.08; }, 200);
            } catch (err) {
                console.log('Audio playback notice:', err);
            }
        });
    }

    // 7. Booking Form & Financing Calculator
    const bookingForm = document.getElementById('test-drive-form');
    const alertBox = document.getElementById('booking-alert');
    if (bookingForm && alertBox) {
        bookingForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const name = document.getElementById('driver-name').value;
            const model = document.getElementById('vehicle-select').value;
            const refCode = 'XR-' + Math.floor(100000 + Math.random() * 900000);

            alertBox.style.display = 'block';
            alertBox.textContent = `Reservation Confirmed for ${name}! Configuration: ${model}. Confirmation Code: ${refCode}. Our VIP concierge will reach out.`;
            bookingForm.reset();
        });
    }

    const downSlider = document.getElementById('down-payment');
    const termSlider = document.getElementById('loan-term');
    const downVal = document.getElementById('down-val');
    const termVal = document.getElementById('term-val');
    const monthlyText = document.getElementById('monthly-payment');

    function updateFinancing() {
        if (!downSlider || !termSlider) return;
        const down = parseInt(downSlider.value);
        const term = parseInt(termSlider.value);
        downVal.textContent = `$${down.toLocaleString()}`;
        termVal.textContent = `${term} Months`;

        const principal = 145000 - down;
        const annualRate = 0.045;
        const monthlyRate = annualRate / 12;
        const monthly = (principal * monthlyRate) / (1 - Math.pow(1 + monthlyRate, -term));
        monthlyText.textContent = `$${Math.round(monthly).toLocaleString()}/mo`;
    }

    if (downSlider && termSlider) {
        downSlider.addEventListener('input', updateFinancing);
        termSlider.addEventListener('input', updateFinancing);
    }

    // 8. Animation Render Loop
    let clock = new THREE.Clock();
    function animate() {
        requestAnimationFrame(animate);

        const delta = clock.getDelta();
        if (autoSpin) {
            carGroup.rotation.y += 0.008;
            wheels.forEach(w => { w.rotation.z += 0.03; });
        }

        // Slight suspension breathing idle
        carGroup.position.y = 0.02 * Math.sin(clock.getElapsedTime() * 2);

        renderer.render(scene, camera);
    }

    animate();

    // Window resize handler
    window.addEventListener('resize', () => {
        if (!container) return;
        width = container.clientWidth;
        height = container.clientHeight;
        camera.aspect = width / height;
        camera.updateProjectionMatrix();
        renderer.setSize(width, height);
    });
});
"""

    def _generate_node_backend(self, spec: WebsiteSpecification) -> str:
        """Construct companion Node.js REST API backend with zero-dependency fallback."""
        return """// Xeren Progressive Car Showroom Node.js Backend API
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
"""

    def _generate_python_backend(self, spec: WebsiteSpecification) -> str:
        """Construct companion Python API & SQLite database backend with zero-dependency fallback."""
        return """# Xeren Progressive Car Showroom Python Backend
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
"""

    def _generate_java_controller(self, spec: WebsiteSpecification) -> str:
        """Construct companion Java Spring Boot REST Controller."""
        return """package com.xeren.showroom.controller;

import org.springframework.web.bind.annotation.*;
import org.springframework.http.ResponseEntity;
import java.util.*;

/**
 * Enterprise Spring Boot REST Controller for Xeren Progressive Car Showroom.
 */
@RestController
@RequestMapping("/api/v1/showroom")
@CrossOrigin(origins = "*")
public class CarShowroomController {

    private final List<Map<String, Object>> inventory = new ArrayList<>();

    public CarShowroomController() {
        inventory.add(Map.of(
            "id", 1,
            "modelName", "Xeren Apex Cyber-GT",
            "horsepower", 1450,
            "zeroToSixty", "1.89s",
            "rangeKm", 850,
            "priceUSD", 145000.00
        ));
        inventory.add(Map.of(
            "id", 2,
            "modelName", "Xeren Phantom Hyper-SUV",
            "horsepower", 1200,
            "zeroToSixty", "2.40s",
            "rangeKm", 780,
            "priceUSD", 120000.00
        ));
        inventory.add(Map.of(
            "id", 3,
            "modelName", "Xeren Vision Speedster",
            "horsepower", 1800,
            "zeroToSixty", "1.65s",
            "rangeKm", 920,
            "priceUSD", 220000.00
        ));
    }

    @GetMapping("/cars")
    public ResponseEntity<List<Map<String, Object>>> getCarInventory() {
        return ResponseEntity.ok(this.inventory);
    }

    @PostMapping("/book")
    public ResponseEntity<Map<String, Object>> reserveTestDrive(@RequestBody Map<String, String> payload) {
        String name = payload.getOrDefault("name", "Guest Driver");
        String model = payload.getOrDefault("carModel", "Xeren Apex Cyber-GT");
        String confirmationCode = "XR-" + UUID.randomUUID().toString().substring(0, 8).toUpperCase();

        Map<String, Object> response = new HashMap<>();
        response.put("status", "CONFIRMED");
        response.put("confirmationCode", confirmationCode);
        response.put("message", "VIP test drive reserved for " + name + " in the " + model);

        return ResponseEntity.ok(response);
    }
}
"""

    def _generate_database_schema(self, spec: WebsiteSpecification) -> str:
        """Construct relational database schema for car showroom."""
        return """-- Xeren Progressive Car Showroom Relational Database Schema
-- Compatible with SQLite, PostgreSQL, and MySQL

CREATE TABLE IF NOT EXISTS vehicle_inventory (
    vehicle_id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    base_price DECIMAL(10, 2) NOT NULL,
    horsepower INTEGER NOT NULL,
    zero_to_sixty_sec DECIMAL(3, 2) NOT NULL,
    battery_range_km INTEGER NOT NULL,
    drive_type VARCHAR(50) DEFAULT 'AWD Tri-Motor',
    status VARCHAR(20) DEFAULT 'AVAILABLE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS test_drive_bookings (
    booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_code VARCHAR(30) UNIQUE NOT NULL,
    customer_name VARCHAR(150) NOT NULL,
    customer_email VARCHAR(150) NOT NULL,
    vehicle_model VARCHAR(100) NOT NULL,
    preferred_date DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'CONFIRMED',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed Initial Hypercar Models
INSERT INTO vehicle_inventory (model_name, category, base_price, horsepower, zero_to_sixty_sec, battery_range_km, drive_type)
VALUES 
    ('Xeren Apex Cyber-GT', 'Hypercar', 145000.00, 1450, 1.89, 850, 'AWD Quad-Motor'),
    ('Xeren Phantom Hyper-SUV', 'Luxury Performance SUV', 120000.00, 1200, 2.40, 780, 'AWD Tri-Motor'),
    ('Xeren Vision Speedster', 'Limited Track Special', 220000.00, 1800, 1.65, 920, 'Torque-Vectoring AWD');
"""

    def _generate_react_component(self, spec: WebsiteSpecification) -> str:
        """Construct companion modern React.js component."""
        return """// Xeren Progressive Car Showroom React.js Component
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
"""

    def _generate_package_json(self, spec: WebsiteSpecification) -> str:
        """Construct package.json manifest for Node/React services."""
        return """{
  "name": "xeren-progressive-car-showroom",
  "version": "1.0.0",
  "description": "Progressive 3D Car Showroom with Three.js, Node.js Express API, and React",
  "main": "server.js",
  "scripts": {
    "start": "node server.js",
    "dev": "nodemon server.js"
  },
  "dependencies": {
    "cors": "^2.8.5",
    "express": "^4.19.2",
    "three": "^0.160.0"
  }
}
"""

    def _generate_requirements_txt(self, spec: WebsiteSpecification) -> str:
        """Construct requirements.txt for Python backend."""
        return """fastapi>=0.110.0
uvicorn>=0.29.0
pydantic>=2.6.0
"""

    def generate_project(
        self,
        spec: WebsiteSpecification,
    ) -> List[FileArtifact]:
        """Generate a complete website project based on a structured specification."""
        pages = spec.pages if spec.pages else ["index.html"]
        if "index.html" not in pages:
            pages = ["index.html"] + [p for p in pages if p != "index.html"]

        files: List[FileArtifact] = []

        purpose_lower = (spec.site_purpose or "").lower()
        is_car_showroom = any(w in purpose_lower for w in ["car", "showroom", "automobile", "motors", "vehicle", "hypercar", "speedster"])
        is_fullstack = is_car_showroom or any(w in purpose_lower for w in ["backend", "database", "node", "python", "java", "react", "next", "controller", "sql"])

        if is_car_showroom:
            # Generate high-end 3D progressive car showroom
            html_content = self._generate_car_showroom_html(spec)
            files.append(FileArtifact(file_path="index.html", content=html_content, language="html"))

            css_content = self._generate_car_showroom_css(spec)
            files.append(FileArtifact(file_path="styles.css", content=css_content, language="css"))

            js_content = self._generate_car_showroom_js(spec)
            files.append(FileArtifact(file_path="script.js", content=js_content, language="javascript"))
        else:
            # 1. Generate standard HTML pages
            for page in pages:
                html_content = self._generate_html_page(page, spec, pages)
                files.append(FileArtifact(file_path=page, content=html_content, language="html"))

            # 2. Generate standard CSS stylesheet
            css_content = self._generate_css(spec)
            files.append(FileArtifact(file_path="styles.css", content=css_content, language="css"))

            # 3. Generate standard JavaScript file
            js_content = self._generate_js(spec)
            files.append(FileArtifact(file_path="script.js", content=js_content, language="javascript"))

        if is_fullstack:
            # Generate full-stack companion backend controllers, database schema, and React app
            files.append(FileArtifact(file_path="server.js", content=self._generate_node_backend(spec), language="javascript"))
            files.append(FileArtifact(file_path="app.py", content=self._generate_python_backend(spec), language="python"))
            files.append(FileArtifact(file_path="CarShowroomController.java", content=self._generate_java_controller(spec), language="java"))
            files.append(FileArtifact(file_path="database_schema.sql", content=self._generate_database_schema(spec), language="sql"))
            files.append(FileArtifact(file_path="App.jsx", content=self._generate_react_component(spec), language="javascript"))
            files.append(FileArtifact(file_path="package.json", content=self._generate_package_json(spec), language="json"))
            files.append(FileArtifact(file_path="requirements.txt", content=self._generate_requirements_txt(spec), language="text"))

        return files

    def edit_project(
        self,
        existing_files: Sequence[FileArtifact],
        modification_request: str,
        spec: Optional[WebsiteSpecification] = None,
    ) -> Tuple[List[FileArtifact], List[FileArtifact]]:
        """Modify an existing website project according to instruction.

        Returns:
            (all_files, modified_files)
        """
        mod_lower = modification_request.lower()
        file_map = {f.file_path: f for f in existing_files}
        modified_files: List[FileArtifact] = []

        # Target identification
        target_path = None
        if "style" in mod_lower or "css" in mod_lower or "color" in mod_lower or "theme" in mod_lower:
            target_path = "styles.css"
        elif "script" in mod_lower or "js" in mod_lower or "interaction" in mod_lower:
            target_path = "script.js"
        elif "html" in mod_lower or "title" in mod_lower or "hero" in mod_lower or "header" in mod_lower:
            target_path = "index.html"

        # If a specific existing file was explicitly referenced
        for f in existing_files:
            if f.file_path.lower() in mod_lower:
                target_path = f.file_path
                break

        # If no specific target matched, default to index.html or first file
        if not target_path:
            target_path = "index.html" if "index.html" in file_map else existing_files[0].file_path

        target_file = file_map.get(target_path)
        if target_file:
            # Modify target file using CodeGenerationTool if available
            try:
                modified_code = self.generation_tool.edit(
                    task=modification_request,
                    source_code=target_file.content,
                    language=target_file.language,
                )
            except Exception:
                modified_code = target_file.content + f"\n/* Modified according to: {modification_request} */\n"

            # Check for fallback MockLLM response
            if modified_code.startswith("Mock response to:") or modified_code.startswith("// Modified solution for:"):
                # Deterministic modification
                if target_file.language == "html":
                    modified_code = target_file.content.replace(
                        "<title>", f"<!-- Edited: {modification_request} -->\n    <title>"
                    )
                elif target_file.language == "css":
                    modified_code = target_file.content + f"\n/* Edited: {modification_request} */\n.accent-highlight {{ color: var(--primary-color); }}\n"
                elif target_file.language == "javascript":
                    modified_code = target_file.content + f"\n// Edited: {modification_request}\nconsole.log('Update applied.');\n"

            updated_artifact = FileArtifact(
                file_path=target_file.file_path,
                content=modified_code,
                language=target_file.language,
            )
            file_map[target_path] = updated_artifact
            modified_files.append(updated_artifact)

        # Reassemble complete file list, preserving unchanged files
        all_files = list(file_map.values())
        return all_files, modified_files

    async def agenerate_project(
        self,
        spec: WebsiteSpecification,
    ) -> List[FileArtifact]:
        """Asynchronously generate website project."""
        return await asyncio.to_thread(self.generate_project, spec)

    async def aedit_project(
        self,
        existing_files: Sequence[FileArtifact],
        modification_request: str,
        spec: Optional[WebsiteSpecification] = None,
    ) -> Tuple[List[FileArtifact], List[FileArtifact]]:
        """Asynchronously edit website project."""
        return await asyncio.to_thread(self.edit_project, existing_files, modification_request, spec)


__all__ = ["WebsiteGeneratorTool"]
