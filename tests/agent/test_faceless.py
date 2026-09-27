import math

def generate_faceless_human_point_cloud():
    points = []
    
    # 1. Cranium Dome & Scalp (Concentric latitude rings across skull)
    ring_count = 16
    for r_idx in range(ring_count):
        phi = ((r_idx + 1) / (ring_count + 1)) * math.pi * 0.54
        ring_y = -0.62 - math.cos(phi) * 0.13
        ring_rad = math.sin(phi) * 0.128
        dots_in_ring = int(14 + ring_rad * 190)
        for d in range(dots_in_ring):
            theta = (d / dots_in_ring) * math.pi * 2
            x = ring_rad * math.cos(theta) * 0.94
            z = ring_rad * math.sin(theta) * 1.04
            points.append(('head', x, ring_y, z))

    # 2. Smooth Faceless Facial Surface (NO eyes, NO nose, NO lips)
    # A sleek, continuous, curved futuristic digital face mask / visor plane
    # 14 smooth horizontal curved rows from upper forehead down to jaw
    for row in range(14):
        t_row = row / 13.0
        fy = -0.60 + t_row * 0.25 # from -0.60 down to -0.35
        # Width curves from forehead (0.115) to cheek (0.125) to lower face (0.09)
        fw = 0.115 + math.sin(t_row * math.pi * 0.8) * 0.015 - (t_row * t_row) * 0.04
        dots_in_row = int(18 + math.sin(t_row * math.pi) * 8)
        for d in range(dots_in_row):
            u = (d / (dots_in_row - 1)) * 2 - 1 # -1 to 1
            x = u * fw
            # Smooth anatomical facial curvature without eye hollows or nose protrusions
            # Gentle convex curvature forward
            curve = math.cos(u * math.pi * 0.5)
            z = 0.05 + curve * 0.065 - (t_row * 0.015)
            points.append(('face', x, fy, z))

    # 3. Mandible Jawline & Chin
    for side in [-1, 1]:
        for i in range(28):
            t = i / 27.0
            jx = side * (0.025 + (1 - t) * 0.095)
            jy = -0.33 - (1 - t) * 0.09
            jz = 0.075 * t + 0.015 * (1 - t)
            points.append(('face', jx, jy, jz))
            
    # Chin base
    for row in range(4):
        cy = -0.355 + row * 0.012
        for col in range(10):
            t = (col / 9.0) * 2 - 1
            cx = t * (0.035 - row * 0.005)
            cz = 0.08 - abs(t) * 0.02 - row * 0.01
            points.append(('face', cx, cy, cz))

    # 4. Neck (10 Concentric Rings + SCM Bands)
    for ring in range(10):
        ny = -0.32 + ring * 0.016
        rad_x = 0.068 + ring * 0.008
        rad_z = 0.060 + ring * 0.006
        for d in range(24):
            ang = (d / 24.0) * math.pi * 2
            pz = math.sin(ang) * rad_z
            if pz < 0: pz *= 0.75
            points.append(('neck', math.cos(ang) * rad_x, ny, pz))
            
    for side in [-1, 1]:
        for i in range(18):
            t = i / 17.0
            sx = side * (0.025 + (1 - t) * 0.07)
            sy = -0.17 - t * 0.14
            sz = 0.065 * t + 0.02 * (1 - t)
            points.append(('neck', sx, sy, sz))

    # 5. Clavicles & Trapezius Shoulders
    for side in [-1, 1]:
        for i in range(26):
            t = i / 25.0
            cx = side * (0.035 + t * 0.30)
            cy = -0.165 + math.sin(t * math.pi) * 0.018 - t * 0.01
            cz = 0.065 - t * 0.05
            points.append(('shoulders', cx, cy, cz))
            points.append(('shoulders', cx, cy - 0.012, cz - 0.008))
        for i in range(22):
            t = i / 21.0
            tx = side * (0.08 + t * 0.26)
            ty = -0.23 + t * 0.08
            tz = -0.02 + (1 - t) * 0.03
            points.append(('shoulders', tx, ty, tz))

    # 6. Deltoids & Upper Arms
    for side in [-1, 1]:
        for row in range(6):
            dy = -0.15 + row * 0.028
            rad = 0.072 - abs(row - 2) * 0.006
            for col in range(16):
                ang = (col / 15.0) * math.pi
                dx = side * (0.32 + math.sin(ang) * rad)
                dz = math.cos(ang) * rad * 0.9
                points.append(('arms', dx, dy, dz))
        for arm_level in range(8):
            ay = 0.02 + arm_level * 0.032
            rad = 0.056 - arm_level * 0.002
            for d in range(14):
                ang = (d / 14.0) * math.pi * 2
                ax = side * (0.38 + math.cos(ang) * rad)
                az = math.sin(ang) * rad * 0.8
                points.append(('arms', ax, ay, az))

    # 7. Pectoralis Major (Chest Plates)
    for side in [-1, 1]:
        for row in range(8):
            pec_y = -0.12 + row * 0.032
            dots_in_pec = 20
            for d in range(dots_in_pec):
                t = d / (dots_in_pec - 1)
                px = side * (0.025 + t * 0.22)
                py = pec_y - t * 0.02
                pz = 0.075 + math.sin(t * math.pi) * 0.065 - row * 0.004
                points.append(('chest', px, py, pz))
    for i in range(18):
        sy = -0.14 + (i / 17.0) * 0.24
        points.append(('chest', 0.0, sy, 0.078))

    # 8. Ribcage & Sub-Chest Torso
    for rib in range(6):
        ry = 0.12 + rib * 0.035
        rad_x = 0.23 - rib * 0.014
        rad_z = 0.12 - rib * 0.01
        for d in range(26):
            ang = (d / 26.0) * math.pi * 2
            pz = math.sin(ang) * rad_z
            if pz < 0: pz *= 0.65
            points.append(('ribs', math.cos(ang) * rad_x, ry, pz))
    for i in range(24):
        t = (i / 23.0) * 2 - 1
        ex = t * 0.16
        ey = 0.12 + abs(t) * 0.10
        ez = 0.09 - abs(t) * 0.04
        points.append(('ribs', ex, ey, ez))

    # 9. Central Radiant Chest Core
    for i in range(110):
        t = i / 109.0
        r = math.pow(t, 0.6) * 0.068
        theta = (i * 137.5 * math.pi) / 180.0
        phi = math.sin(i * 3.7) * (math.pi * 0.45)
        points.append(('core', r * math.cos(theta) * math.cos(phi), 0.038 + r * math.sin(phi), 0.082 + r * math.sin(theta) * math.cos(phi)))

    return points

points = generate_faceless_human_point_cloud()
print(f"Total points: {len(points)}")
region_counts = {}
for r, x, y, z in points:
    region_counts[r] = region_counts.get(r, 0) + 1
for r, c in region_counts.items():
    print(f"  {r}: {c}")
