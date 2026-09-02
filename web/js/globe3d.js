/**
 * globe3d.js
 * Renders an interactive 3D particle Cyber Globe with financial hub nodes
 * and animated arc trajectories for real-time transactions.
 */

const CyberGlobe3D = (() => {
  let scene, camera, renderer, globeGroup;
  let particles, hubNodes = [];
  let isRotating = true;

  // Major Financial Hubs Coordinates (Lat, Lon)
  const HUBS = [
    { name: 'New York (NYSE)', lat: 40.7128, lon: -74.0060, color: 0x00f3ff },
    { name: 'London (LSE)', lat: 51.5074, lon: -0.1278, color: 0xa855f7 },
    { name: 'Tokyo (TSE)', lat: 35.6762, lon: 139.6503, color: 0x10b981 },
    { name: 'Singapore (SGX)', lat: 1.3521, lon: 103.8198, color: 0x00f3ff },
    { name: 'Frankfurt (DB)', lat: 50.1109, lon: 8.6821, color: 0xf59e0b },
    { name: 'Dubai (DFM)', lat: 25.2048, lon: 55.2708, color: 0xa855f7 }
  ];

  function latLonToVector3(lat, lon, radius) {
    const phi = (90 - lat) * (Math.PI / 180);
    const theta = (lon + 180) * (Math.PI / 180);
    const x = -(radius * Math.sin(phi) * Math.cos(theta));
    const z = (radius * Math.sin(phi) * Math.sin(theta));
    const y = (radius * Math.cos(phi));
    return new THREE.Vector3(x, y, z);
  }

  function init(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const width = container.clientWidth;
    const height = container.clientHeight;

    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.z = 240;

    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.innerHTML = '';
    container.appendChild(renderer.domElement);

    globeGroup = new THREE.Group();
    scene.add(globeGroup);

    // 1. Create Base Particle Globe
    const globeRadius = 75;
    const particleCount = 1800;
    const geometry = new THREE.BufferGeometry();
    const positions = [];
    const colors = [];

    const baseColor = new THREE.Color(0x00f3ff);

    for (let i = 0; i < particleCount; i++) {
      const u = Math.random();
      const v = Math.random();
      const theta = u * 2.0 * Math.PI;
      const phi = Math.acos(2.0 * v - 1.0);
      const r = Math.cbrt(Math.random()) * 2 + globeRadius;

      const x = r * Math.sin(phi) * Math.cos(theta);
      const y = r * Math.sin(phi) * Math.sin(theta);
      const z = r * Math.cos(phi);

      positions.push(x, y, z);
      colors.push(baseColor.r, baseColor.g, baseColor.b);
    }

    geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));

    const material = new THREE.PointsMaterial({
      size: 2.2,
      vertexColors: true,
      transparent: true,
      opacity: 0.65,
      blending: THREE.AdditiveBlending
    });

    particles = new THREE.Points(geometry, material);
    globeGroup.add(particles);

    // 2. Wireframe Inner Sphere
    const innerGeo = new THREE.SphereGeometry(globeRadius - 2, 24, 24);
    const innerMat = new THREE.MeshBasicMaterial({
      color: 0x0a1628,
      wireframe: true,
      transparent: true,
      opacity: 0.15
    });
    const innerSphere = new THREE.Mesh(innerGeo, innerMat);
    globeGroup.add(innerSphere);

    // 3. Add Financial Hub Nodes
    HUBS.forEach(hub => {
      const pos = latLonToVector3(hub.lat, hub.lon, globeRadius + 1);
      
      const nodeGeo = new THREE.SphereGeometry(2.5, 12, 12);
      const nodeMat = new THREE.MeshBasicMaterial({
        color: hub.color,
        wireframe: false
      });
      const nodeMesh = new THREE.Mesh(nodeGeo, nodeMat);
      nodeMesh.position.copy(pos);
      globeGroup.add(nodeMesh);

      // Outer Pulse Ring
      const ringGeo = new THREE.RingGeometry(3.5, 4.5, 16);
      const ringMat = new THREE.MeshBasicMaterial({
        color: hub.color,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0.6
      });
      const ringMesh = new THREE.Mesh(ringGeo, ringMat);
      ringMesh.position.copy(pos);
      ringMesh.lookAt(new THREE.Vector3(0, 0, 0));
      globeGroup.add(ringMesh);

      hubNodes.push({ mesh: nodeMesh, ring: ringMesh, name: hub.name });
    });

    // 4. Mouse Interactive Drag Rotation
    let isDragging = false;
    let prevMousePos = { x: 0, y: 0 };

    container.addEventListener('mousedown', (e) => {
      isDragging = true;
      prevMousePos = { x: e.clientX, y: e.clientY };
    });

    window.addEventListener('mouseup', () => { isDragging = false; });

    container.addEventListener('mousemove', (e) => {
      if (isDragging) {
        const deltaX = e.clientX - prevMousePos.x;
        const deltaY = e.clientY - prevMousePos.y;

        globeGroup.rotation.y += deltaX * 0.005;
        globeGroup.rotation.x += deltaY * 0.005;

        prevMousePos = { x: e.clientX, y: e.clientY };
      }
    });

    // Window Resize handler
    window.addEventListener('resize', () => {
      if (!container) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    });

    animate();
  }

  // Flash the globe red when a critical fraud threat occurs
  function pulseThreat() {
    if (!particles) return;
    const colors = particles.geometry.attributes.color.array;
    const red = new THREE.Color(0xef4444);
    const cyan = new THREE.Color(0x00f3ff);

    for (let i = 0; i < colors.length; i += 3) {
      colors[i] = red.r;
      colors[i + 1] = red.g;
      colors[i + 2] = red.b;
    }
    particles.geometry.attributes.color.needsUpdate = true;

    setTimeout(() => {
      for (let i = 0; i < colors.length; i += 3) {
        colors[i] = cyan.r;
        colors[i + 1] = cyan.g;
        colors[i + 2] = cyan.b;
      }
      particles.geometry.attributes.color.needsUpdate = true;
    }, 1200);
  }

  function animate() {
    requestAnimationFrame(animate);
    if (isRotating && globeGroup) {
      globeGroup.rotation.y += 0.0025;
    }
    if (renderer && scene && camera) {
      renderer.render(scene, camera);
    }
  }

  return {
    init: init,
    pulseThreat: pulseThreat,
    toggleRotation: () => { isRotating = !isRotating; return isRotating; }
  };
})();
