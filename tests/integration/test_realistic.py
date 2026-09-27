import math

def generate_realistic_human_point_cloud():
    points = []
    # (region, x, y, z, nx, ny, nz, isBreathing)
    
    # 1. CRANIUM & SCALP (~420 dots)
    # Realistic human skull: slightly elongated front-to-back, wider at parietal
    for phi_idx in range(15):
        phi = ((phi_idx + 1) / 16.0) * math.pi * 0.52 # 0 to ~85 deg
        y = -0.63 - math.cos(phi) * 0.125
        r = math.sin(phi) * 0.118
        dots = int(12 + r * 200)
        for d in range(dots):
            theta = (d / dots) * math.pi * 2
            # Parietal width vs frontal taper
            width_mod = 0.92 if math.sin(theta) > 0 else 1.02 # wider at back
            x = r * math.cos(theta) * width_mod
            z = r * math.sin(theta) * 1.12 # front-back elongation
            # Normal vector
            nx = math.cos(theta) * width_mod
            ny = -math.cos(phi)
            nz = math.sin(theta) * 1.12
            n_len = math.sqrt(nx*nx + ny*ny + nz*nz)
            points.append(('head', x, y, z, nx/n_len, ny/n_len, nz/n_len, False))

    # 2. FACE & JAW VISOR (~380 dots)
    # Smooth, faceless human facial plane with authentic cheekbone & jaw tapering
    for row in range(16):
        v = row / 15.0 # 0 (forehead) to 1 (chin)
        y = -0.60 + v * 0.26 # -0.60 to -0.34
        # Width: narrow at temple (0.10), wider at cheek (0.118), narrow at chin (0.045)
        if v < 0.4:
            w = 0.102 + (v / 0.4) * 0.016
        elif v < 0.75:
            w = 0.118 - ((v - 0.4) / 0.35) * 0.042
        else:
            w = 0.076 - ((v - 0.75) / 0.25) * 0.038
            
        dots = int(14 + w * 160)
        for d in range(dots):
            u = (d / (dots - 1)) * 2 - 1 # -1 to 1
            x = u * w
            # Curvature: convex frontal curve
            curv = math.cos(u * math.pi * 0.5)
            z = 0.045 + curv * (0.065 - v * 0.02)
            # Normal
            nx = math.sin(u * math.pi * 0.5) * 0.7
            ny = (v - 0.4) * 0.4
            nz = curv * 0.9
            n_len = math.sqrt(nx*nx + ny*ny + nz*nz)
            points.append(('face', x, y, z, nx/n_len, ny/n_len, nz/n_len, False))

    # 3. NECK & THROAT (~260 dots)
    # Anatomical neck cylinder with forward lordosis (tilt) and trapezius flare
    for ring in range(11):
        v = ring / 10.0
        y = -0.33 + v * 0.17 # -0.33 to -0.16
        tilt_z = (1 - v) * 0.025 # neck tilts slightly forward at top
        rad_x = 0.062 + v * 0.024 # flares outward toward clavicles
        rad_z = 0.056 + v * 0.016
        dots = 24
        for d in range(dots):
            ang = (d / dots) * math.pi * 2
            x = math.cos(ang) * rad_x
            z = math.sin(ang) * rad_z + tilt_z
            # Flatter back neck
            if z < tilt_z: z = tilt_z + (z - tilt_z) * 0.75
            nx = math.cos(ang)
            ny = 0.1
            nz = math.sin(ang)
            n_len = math.sqrt(nx*nx + ny*ny + nz*nz)
            points.append(('neck', x, y, z, nx/n_len, ny/n_len, nz/n_len, False))

    # 4. CLAVICLES & TRAPEZIUS SHOULDERS (~220 dots)
    for side in [-1, 1]:
        # Clavicle collarbones (S-curve from sternum to acromion)
        for i in range(28):
            t = i / 27.0
            x = side * (0.028 + t * 0.28)
            y = -0.155 + math.sin(t * math.pi) * 0.015 - t * 0.018
            z = 0.065 - t * 0.045
            points.append(('shoulders', x, y, z, 0.0, 0.3, 0.9, False))
            points.append(('shoulders', x, y - 0.012, z - 0.01, 0.0, 0.7, 0.7, False))
            
        # Trapezius shoulder slope (from neck to shoulder tip)
        for i in range(24):
            t = i / 23.0
            x = side * (0.075 + t * 0.24)
            y = -0.22 + t * 0.08
            z = -0.015 + (1 - t) * 0.03
            points.append(('shoulders', x, y, z, side * 0.3, 0.8, -0.4, False))

    # 5. DELTOIDS & UPPER ARMS (~420 dots)
    for side in [-1, 1]:
        # Deltoid shoulder caps
        for row in range(7):
            dy = -0.14 + row * 0.026
            rad = 0.068 - abs(row - 3) * 0.005
            for col in range(16):
                ang = (col / 15.0) * math.pi
                x = side * (0.31 + math.sin(ang) * rad)
                y = dy
                z = math.cos(ang) * rad * 0.92
                nx = side * math.sin(ang)
                ny = (row - 3) * 0.15
                nz = math.cos(ang)
                n_len = math.sqrt(nx*nx + ny*ny + nz*nz)
                points.append(('arms', x, y, z, nx/n_len, ny/n_len, nz/n_len, False))
                
        # Upper arm cylinder descending down alongside torso
        for lvl in range(8):
            v = lvl / 7.0
            ay = 0.03 + v * 0.24 # down to mid-arm
            # Slight outward angle ~8 degrees
            arm_x_center = side * (0.355 + v * 0.02)
            rad = 0.052 - v * 0.006
            for d in range(14):
                ang = (d / 14.0) * math.pi * 2
                x = arm_x_center + math.cos(ang) * rad
                z = math.sin(ang) * rad * 0.82
                nx = math.cos(ang)
                ny = 0.0
                nz = math.sin(ang)
                n_len = math.sqrt(nx*nx + ny*ny + nz*nz)
                points.append(('arms', x, ay, z, nx/n_len, ny/n_len, nz/n_len, False))

    # 6. PECTORALIS MAJOR & CHEST (~380 dots)
    # Left and right chest muscle plates
    for side in [-1, 1]:
        for row in range(9):
            pec_y = -0.11 + row * 0.03 # -0.11 to 0.13
            dots = 20
            for d in range(dots):
                t = d / (dots - 1)
                # Fans outward from sternum (0.022) to armpit/deltoid boundary (0.24)
                x = side * (0.022 + t * 0.22)
                y = pec_y - t * 0.016
                # Anatomical pectoral volume (bulges forward, peaks near mid-pec)
                z = 0.078 + math.sin(t * math.pi) * 0.062 - (row * 0.003)
                nx = side * (t - 0.5) * 0.6
                ny = (row - 4) * 0.1
                nz = 0.85
                n_len = math.sqrt(nx*nx + ny*ny + nz*nz)
                points.append(('chest', x, y, z, nx/n_len, ny/n_len, nz/n_len, True))

    # Sternum central division line
    for i in range(18):
        sy = -0.13 + (i / 17.0) * 0.25
        points.append(('chest', 0.0, sy, 0.082, 0.0, 0.0, 1.0, True))

    # 7. RIBCAGE, LATS & SUB-CHEST TORSO (~240 dots)
    for rib in range(7):
        v = rib / 6.0
        ry = 0.13 + v * 0.20 # 0.13 to 0.33
        rad_x = 0.225 - v * 0.028 # natural waist taper
        rad_z = 0.118 - v * 0.015
        dots = 28
        for d in range(dots):
            ang = (d / dots) * math.pi * 2
            x = math.cos(ang) * rad_x
            z = math.sin(ang) * rad_z
            if z < 0: z *= 0.68 # Flatter back spine
            nx = math.cos(ang)
            ny = 0.1
            nz = math.sin(ang)
            n_len = math.sqrt(nx*nx + ny*ny + nz*nz)
            points.append(('ribs', x, ry, z, nx/n_len, ny/n_len, nz/n_len, True))
            
    # Infrasternal sub-chest arch
    for i in range(24):
        t = (i / 23.0) * 2 - 1
        x = t * 0.155
        y = 0.13 + abs(t) * 0.09
        z = 0.088 - abs(t) * 0.035
        points.append(('ribs', x, y, z, 0.0, -0.4, 0.9, True))

    # 8. CENTRAL RADIANT HEART CORE (~120 dots)
    for i in range(120):
        t = i / 119.0
        r = math.pow(t, 0.6) * 0.065
        theta = (i * 137.5 * math.pi) / 180.0
        phi = math.sin(i * 3.7) * (math.pi * 0.45)
        x = r * math.cos(theta) * math.cos(phi)
        y = 0.038 + r * math.sin(phi)
        z = 0.082 + r * math.sin(theta) * math.cos(phi)
        points.append(('core', x, y, z, 0.0, 0.0, 1.0, True))

    return points

points = generate_realistic_human_point_cloud()
print(f"Total realistic anatomical points: {len(points)}")
regions = {}
for p in points:
    regions[p[0]] = regions.get(p[0], 0) + 1
for r, c in regions.items():
    print(f"  {r}: {c}")
