import math

def generate_orb_point_cloud():
    points = []
    
    # 1. Fibonacci Spherical Surface Shell (~950 dots)
    # Uniform spherical distribution using golden spiral (Fibonacci sphere)
    num_shell_dots = 950
    phi = (1 + math.sqrt(5)) / 2 # golden ratio
    orb_radius = 0.28
    
    for i in range(num_shell_dots):
        y = 1 - (i / float(num_shell_dots - 1)) * 2 # 1 to -1
        radius_at_y = math.sqrt(max(0, 1 - y * y))
        theta = 2 * math.pi * i / phi
        
        x = math.cos(theta) * radius_at_y * orb_radius
        z = math.sin(theta) * radius_at_y * orb_radius
        py = y * orb_radius
        
        # Normals point directly outward from center
        nx = x / orb_radius
        ny = py / orb_radius
        nz = z / orb_radius
        
        points.append(('core', x, py, z, nx, ny, nz, True))

    # 2. Orbital Crystalline Rings (Equatorial and Tilted Rings) (~480 dots)
    # Ring 1: Equatorial ring
    for d in range(160):
        ang = (d / 160.0) * math.pi * 2
        r = orb_radius * 1.28
        x = math.cos(ang) * r
        y = math.sin(ang) * 0.015
        z = math.sin(ang) * r
        points.append(('core', x, y, z, x/r, 0.0, z/r, False))
        
    # Ring 2: Tilted orbital ring (35 degrees)
    tilt1 = math.radians(35)
    for d in range(160):
        ang = (d / 160.0) * math.pi * 2
        r = orb_radius * 1.38
        rx = math.cos(ang) * r
        rz = math.sin(ang) * r
        # Tilt around X axis
        x = rx
        y = -rz * math.sin(tilt1)
        z = rz * math.cos(tilt1)
        points.append(('core', x, y, z, x/r, y/r, z/r, False))

    # Ring 3: Counter-tilted orbital ring (-45 degrees)
    tilt2 = math.radians(-45)
    for d in range(160):
        ang = (d / 160.0) * math.pi * 2
        r = orb_radius * 1.48
        rx = math.cos(ang) * r
        rz = math.sin(ang) * r
        # Tilt around Z axis
        x = rx * math.cos(tilt2)
        y = rx * math.sin(tilt2)
        z = rz
        points.append(('core', x, y, z, x/r, y/r, z/r, False))

    # 3. Inner Radiant Nucleus Core (~220 dots)
    num_nucleus = 220
    for i in range(num_nucleus):
        y = 1 - (i / float(num_nucleus - 1)) * 2
        radius_at_y = math.sqrt(max(0, 1 - y * y))
        theta = 2 * math.pi * i / phi
        r_nuc = 0.12 * math.pow((i + 1) / num_nucleus, 0.5)
        
        x = math.cos(theta) * radius_at_y * r_nuc
        z = math.sin(theta) * radius_at_y * r_nuc
        py = y * r_nuc
        points.append(('core', x, py, z, 0.0, 0.0, 1.0, True))

    # 4. Acoustic Wave / Radial Pulse Emitters (~150 dots)
    for i in range(150):
        theta = (i * 137.5 * math.pi) / 180.0
        pitch = math.sin(i * 2.3) * math.pi * 0.4
        r = 0.22 + (i / 150.0) * 0.14
        x = r * math.cos(theta) * math.cos(pitch)
        y = r * math.sin(pitch)
        z = r * math.sin(theta) * math.cos(pitch)
        points.append(('core', x, y, z, x/r, y/r, z/r, True))

    return points

points = generate_orb_point_cloud()
print(f"Total Orb points: {len(points)}")
