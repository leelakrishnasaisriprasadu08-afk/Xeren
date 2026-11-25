// Xeren Progressive 3D Car Showroom Engine (Three.js WebGL)
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
