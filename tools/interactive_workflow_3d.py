"""
tools/interactive_workflow_3d.py - Live Interactive 3D WebGL Workflow Pipeline
Renders an interactive Three.js 3D spatial visualization of the multi-agent research pipeline.
Features:
  - Full 3D spatial node architecture with orbital rotation, panning, and zoom.
  - Glowing spline pipelines with real-time flowing data packet particles.
  - Interactive click inspection revealing node contracts, inputs, outputs, and source links.
  - "Run Live Simulation" mode stepping through Stage 1 -> Stage 5 with animated packet transit.
  - Institutional terminal aesthetics (charcoal/emerald/gold/cyan palette, zero cartoon AI styling).
"""

def render_interactive_3d_workflow(height: int = 620) -> str:
    """Returns standalone HTML string containing the Three.js 3D interactive workflow component."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Meridian 3D Multi-Agent Pipeline</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; user-select: none; }}
    body {{
      background: #0d1412;
      color: #e4e9e5;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      overflow: hidden;
      width: 100vw;
      height: {height}px;
      position: relative;
    }}
    #canvas3d {{ width: 100%; height: 100%; display: block; }}

    /* Top HUD Header */
    .hud-header {{
      position: absolute;
      top: 14px;
      left: 18px;
      z-index: 10;
      pointer-events: none;
    }}
    .hud-title {{
      font-size: 15px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: #c8e45e;
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .hud-title::before {{
      content: '';
      display: inline-block;
      width: 9px;
      height: 9px;
      border-radius: 50%;
      background: #22c55e;
      box-shadow: 0 0 10px #22c55e;
      animation: pulse 2s infinite ease-in-out;
    }}
    @keyframes pulse {{
      0%, 100% {{ opacity: 1; transform: scale(1); }}
      50% {{ opacity: 0.4; transform: scale(0.8); }}
    }}
    .hud-sub {{
      font-size: 11.5px;
      color: #8fa196;
      margin-top: 3px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    }}

    /* Control Toolbar */
    .toolbar {{
      position: absolute;
      top: 14px;
      right: 18px;
      z-index: 10;
      display: flex;
      gap: 8px;
      align-items: center;
    }}
    .btn {{
      background: rgba(28, 42, 37, 0.85);
      border: 1px solid #334d40;
      color: #e4e9e5;
      padding: 6px 13px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: all 0.15s ease;
      backdrop-filter: blur(6px);
    }}
    .btn:hover {{
      background: #2c4137;
      border-color: #d6ed75;
      color: #ffffff;
      transform: translateY(-1px);
    }}
    .btn-primary {{
      background: #d6ed75;
      border-color: #d6ed75;
      color: #121c17;
      font-weight: 700;
    }}
    .btn-primary:hover {{
      background: #c2dc4b;
      color: #0b120f;
    }}

    /* Inspection Detail Card */
    .detail-card {{
      position: absolute;
      bottom: 16px;
      left: 18px;
      width: 380px;
      max-width: calc(100vw - 36px);
      background: rgba(18, 28, 24, 0.94);
      border: 1px solid #314a3e;
      border-radius: 8px;
      padding: 14px 16px;
      box-shadow: 0 12px 32px rgba(0,0,0,0.45);
      backdrop-filter: blur(10px);
      z-index: 10;
      transition: opacity 0.2s ease, transform 0.2s ease;
    }}
    .detail-tag {{
      display: inline-block;
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      padding: 2px 7px;
      border-radius: 4px;
      margin-bottom: 6px;
    }}
    .tag-analyst {{ background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4); }}
    .tag-verifier {{ background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4); }}
    .tag-skeptic {{ background: rgba(244, 63, 94, 0.2); color: #fb7185; border: 1px solid rgba(244, 63, 94, 0.4); }}
    .tag-orchestrator {{ background: rgba(56, 189, 248, 0.2); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.4); }}
    .tag-evidence {{ background: rgba(168, 85, 247, 0.2); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.4); }}
    .tag-dossier {{ background: rgba(214, 237, 117, 0.2); color: #d6ed75; border: 1px solid rgba(214, 237, 117, 0.4); }}

    .detail-title {{
      font-size: 15px;
      font-weight: 700;
      color: #ffffff;
      margin-bottom: 5px;
    }}
    .detail-desc {{
      font-size: 12px;
      color: #a7b7ac;
      line-height: 1.5;
      margin-bottom: 10px;
    }}
    .detail-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 6px;
      font-size: 11px;
      margin-bottom: 8px;
    }}
    .detail-box {{
      background: rgba(255,255,255,0.035);
      border: 1px solid #2a3e34;
      padding: 6px 8px;
      border-radius: 4px;
    }}
    .detail-box-label {{ color: #7f9387; font-size: 10px; font-weight: 600; text-transform: uppercase; }}
    .detail-box-val {{ color: #e4e9e5; font-family: ui-monospace, monospace; margin-top: 2px; }}
    .detail-code {{
      font-size: 11px;
      color: #9eb1a6;
      border-top: 1px solid #283c32;
      padding-top: 7px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .detail-code code {{
      background: rgba(0,0,0,0.3);
      padding: 2px 5px;
      border-radius: 3px;
      color: #d6ed75;
      font-family: ui-monospace, monospace;
    }}

    /* Simulation HUD */
    .sim-status {{
      position: absolute;
      bottom: 16px;
      right: 18px;
      background: rgba(18, 28, 24, 0.92);
      border: 1px solid #314a3e;
      border-radius: 8px;
      padding: 10px 14px;
      z-index: 10;
      font-size: 12px;
      display: flex;
      align-items: center;
      gap: 10px;
      font-family: ui-monospace, monospace;
    }}
    .status-dot {{ width: 8px; height: 8px; border-radius: 50%; background: #22c55e; }}

    /* Legend Overlay */
    .legend {{
      position: absolute;
      top: 58px;
      left: 18px;
      background: rgba(18, 28, 24, 0.78);
      border: 1px solid #26382f;
      border-radius: 6px;
      padding: 7px 11px;
      font-size: 11px;
      display: flex;
      gap: 12px;
      z-index: 9;
      pointer-events: none;
    }}
    .legend-item {{ display: flex; align-items: center; gap: 5px; color: #a0b2a7; }}
    .legend-color {{ width: 9px; height: 9px; border-radius: 2px; }}
  </style>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
</head>
<body>

  <div class="hud-header">
    <div class="hud-title">Live 3D Multi-Agent Spatial Pipeline</div>
    <div class="hud-sub">Interactive Topology · Direct Memory Contracts · Zero Mental Arithmetic</div>
  </div>

  <div class="toolbar">
    <button class="btn btn-primary" id="btnSimulate">▶ Run Live Flow Simulation</button>
    <button class="btn" id="btnResetCamera">⟲ Reset View</button>
  </div>

  <div class="legend">
    <div class="legend-item"><div class="legend-color" style="background:#38bdf8"></div>Orchestrator</div>
    <div class="legend-item"><div class="legend-color" style="background:#c084fc"></div>Evidence Vault</div>
    <div class="legend-item"><div class="legend-color" style="background:#34d399"></div>Analyst</div>
    <div class="legend-item"><div class="legend-color" style="background:#fbbf24"></div>Verifier</div>
    <div class="legend-item"><div class="legend-color" style="background:#fb7185"></div>Skeptic</div>
    <div class="legend-item"><div class="legend-color" style="background:#d6ed75"></div>Dossier</div>
  </div>

  <div class="detail-card" id="detailCard">
    <div class="detail-tag tag-orchestrator" id="cardTag">Stage 0 · Orchestration</div>
    <div class="detail-title" id="cardTitle">Pipeline Orchestrator</div>
    <div class="detail-desc" id="cardDesc">Controls stage sequences, strictly disallows synthetic filings, passes structured dictionaries, and halts execution upon verification failure.</div>
    <div class="detail-grid">
      <div class="detail-box">
        <div class="detail-box-label">Input Contract</div>
        <div class="detail-box-val" id="cardInputs">ticker, workflow_num</div>
      </div>
      <div class="detail-box">
        <div class="detail-box-label">Output Artifact</div>
        <div class="detail-box-val" id="cardOutputs">final_report.md + sidecar</div>
      </div>
    </div>
    <div class="detail-code">
      <span>Implementation File:</span>
      <code id="cardFile">run_research.py</code>
    </div>
  </div>

  <div class="sim-status" id="simStatus">
    <div class="status-dot" id="statusDot"></div>
    <span id="statusText">System Ready · Click any node or drag to orbit in 3D</span>
  </div>

  <canvas id="canvas3d"></canvas>

  <script>
    // --- PIPELINE NODE DEFINITIONS ---
    const PIPELINE_NODES = [
      {{
        id: "input",
        name: "Terminal Input / Ticker Selection",
        tag: "Terminal Trigger",
        tagClass: "tag-orchestrator",
        color: 0x38bdf8,
        desc: "Researcher selects equity ticker (US, Indian .NS, European, Asian) and research workflow depth in the Meridian Terminal.",
        inputs: "Symbol string (e.g. AAPL, TCS.NS)",
        outputs: "Sanitized ticker & workflow",
        file: "dashboard.py (lines 764-805)",
        x: -9, y: 1.5, z: 0
      }},
      {{
        id: "orchestrator",
        name: "Pipeline Orchestrator (run_research)",
        tag: "Stage 0 · Pipeline Controller",
        tagClass: "tag-orchestrator",
        color: 0x38bdf8,
        desc: "Coordinates direct Python calls across agents. Enforces strict fail-closed audit policy with no message broker delay.",
        inputs: "ticker, workflow_number, strict_audit",
        outputs: "Consolidated dossier & sidecars",
        file: "run_research.py (run_pipeline)",
        x: -5.5, y: 1.5, z: 0
      }},
      {{
        id: "evidence",
        name: "Evidence Vault & Filing Extractor",
        tag: "Primary Evidence Store",
        tagClass: "tag-evidence",
        color: 0xa855f7,
        desc: "Extracts audited 10-K / Ind AS filings from SEC EDGAR and NSE India. Verifies SHA-256 sidecars and enforces HTTP 200 checks.",
        inputs: "Filing URLs, CIK, XBRL concept tags",
        outputs: "Raw tables & .meta.json sidecars",
        file: "tools/filing.py & tools/data_layer.py",
        x: -5.5, y: -2.0, z: 1.5
      }},
      {{
        id: "analyst",
        name: "1 · Analyst Agent (Drafting & Provenance)",
        tag: "Stage 1 · Modeling & Synthesis",
        tagClass: "tag-analyst",
        color: 0x10b981,
        desc: "Extracts 15+ fundamental metrics, executes DCF & reverse DCF models, hashes every figure into the ProvenanceLedger, and drafts memorandum.",
        inputs: "Audited tables, stock price, share registry",
        outputs: "analyst_report.md + skeptic_inputs",
        file: "agents/analyst.py (run_workflow)",
        x: -1.5, y: 1.5, z: 0
      }},
      {{
        id: "verifier1",
        name: "2 · Cryptographic Verifier (Analyst Audit)",
        tag: "Stage 2 · Audit & Re-Fetch",
        tagClass: "tag-verifier",
        color: 0xf59e0b,
        desc: "Verifies HMAC signature, audits half-unit stated precision, verifies document sidecar existence, and independently re-fetches primary facts.",
        inputs: "analyst_report.md + provenance.json",
        outputs: "audit summary (PASS / FAIL) + wrong_items",
        file: "agents/verifier.py (ReportVerifier.audit)",
        x: 2.2, y: 1.5, z: 0
      }},
      {{
        id: "skeptic",
        name: "3 · Skeptic Agent (Adversarial Stress Engine)",
        tag: "Stage 3 · Empirical Defense",
        tagClass: "tag-skeptic",
        color: 0xf43f5e,
        desc: "Adversarially stress-tests valuation assumptions: -200 bps margin contraction, +100 bps WACC elevation, working capital divergence.",
        inputs: "skeptic_inputs dictionary from Analyst",
        outputs: "Thesis Verdict + skeptic_report.md",
        file: "agents/skeptic.py (evaluate_thesis)",
        x: 2.2, y: -2.0, z: -1.0
      }},
      {{
        id: "verifier2",
        name: "4 · Round 2 Verifier (Skeptic Review Audit)",
        tag: "Stage 4 · Final Integrity Audit",
        tagClass: "tag-verifier",
        color: 0xf59e0b,
        desc: "Audits Skeptic's quantitative calculations against ledger records to ensure adversarial tests introduce zero mathematical errors.",
        inputs: "skeptic_report.md + skeptic provenance sidecar",
        outputs: "Skeptic audit status (PASS / FAIL)",
        file: "agents/verifier.py (Round 2 Verifier)",
        x: 5.8, y: -2.0, z: -1.0
      }},
      {{
        id: "dossier",
        name: "5 · Audited Investment Memorandum",
        tag: "Stage 5 · Institutional Output",
        tagClass: "tag-dossier",
        color: 0xd6ed75,
        desc: "Produces the comprehensive final dossier with executive summary, scorecard, stress checklist, and cryptographic sidecar citations.",
        inputs: "Analyst draft, Skeptic verdict, dual audits",
        outputs: "final_report.md (Saved in reports/)",
        file: "reports/<ticker>_<timestamp>/final_report.md",
        x: 8.5, y: 0, z: 0
      }}
    ];

    // Pipeline Connections (Source -> Target)
    const CONNECTIONS = [
      {{ from: "input", to: "orchestrator", label: "Initiates Run" }},
      {{ from: "orchestrator", to: "evidence", label: "Fetches Filings" }},
      {{ from: "evidence", to: "analyst", label: "Provides Primary Data" }},
      {{ from: "orchestrator", to: "analyst", label: "Invokes Workflow" }},
      {{ from: "analyst", to: "verifier1", label: "Audits Draft" }},
      {{ from: "verifier1", to: "skeptic", label: "Passed to Stress Test" }},
      {{ from: "skeptic", to: "verifier2", label: "Audits Stress Math" }},
      {{ from: "verifier2", to: "dossier", label: "Final Synthesis" }},
      {{ from: "evidence", to: "verifier1", label: "Re-fetch Ground Truth" }}
    ];

    // --- THREE.JS SCENE SETUP ---
    const container = document.getElementById("canvas3d");
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x0d1412, 0.028);

    const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.set(0, 7, 20);

    const renderer = new THREE.WebGLRenderer({{ canvas: container, antialias: true, alpha: true }});
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

    const controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.maxDistance = 45;
    controls.minDistance = 5;
    controls.target.set(0, 0, 0);

    // Subtle Grid Floor
    const gridHelper = new THREE.GridHelper(34, 34, 0x1f3328, 0x14221b);
    gridHelper.position.y = -4.5;
    scene.add(gridHelper);

    // Ambient & Directional Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
    scene.add(ambientLight);

    const dirLight1 = new THREE.DirectionalLight(0xd6ed75, 1.0);
    dirLight1.position.set(10, 20, 15);
    scene.add(dirLight1);

    const dirLight2 = new THREE.DirectionalLight(0x38bdf8, 0.8);
    dirLight2.position.set(-15, -10, -10);
    scene.add(dirLight2);

    // --- MESH GENERATION ---
    const nodeMeshes = [];
    const nodeMap = {{}};

    // Geometric builders
    function createNodeGeometry(id) {{
      if (id === "orchestrator") return new THREE.OctahedronGeometry(1.1, 0);
      if (id === "evidence") return new THREE.CylinderGeometry(0.9, 0.9, 1.4, 16);
      if (id === "analyst") return new THREE.DodecahedronGeometry(1.05, 0);
      if (id === "verifier1" || id === "verifier2") return new THREE.BoxGeometry(1.5, 1.5, 1.5);
      if (id === "skeptic") return new THREE.IcosahedronGeometry(1.1, 0);
      if (id === "dossier") return new THREE.BoxGeometry(1.6, 2.0, 0.5);
      return new THREE.SphereGeometry(1.0, 24, 24);
    }}

    PIPELINE_NODES.forEach((n) => {{
      const geom = createNodeGeometry(n.id);
      const mat = new THREE.MeshStandardMaterial({{
        color: n.color,
        roughness: 0.25,
        metalness: 0.45,
        emissive: n.color,
        emissiveIntensity: 0.18,
      }});
      const mesh = new THREE.Mesh(geom, mat);
      mesh.position.set(n.x, n.y, n.z);
      mesh.userData = n;
      scene.add(mesh);

      // Glowing outer ring / wireframe aura
      const wireGeom = new THREE.WireframeGeometry(geom);
      const wireMat = new THREE.LineBasicMaterial({{ color: n.color, transparent: true, opacity: 0.4 }});
      const wire = new THREE.LineSegments(wireGeom, wireMat);
      wire.scale.set(1.15, 1.15, 1.15);
      mesh.add(wire);

      nodeMeshes.push(mesh);
      nodeMap[n.id] = mesh;
    }});

    // --- PIPELINE CONNECTIONS & TUBES ---
    const splineCurves = [];
    CONNECTIONS.forEach((c) => {{
      const startNode = nodeMap[c.from];
      const endNode = nodeMap[c.to];
      if (startNode && endNode) {{
        const p1 = startNode.position;
        const p2 = endNode.position;
        const mid = new THREE.Vector3().addVectors(p1, p2).multiplyScalar(0.5);
        // Add curve height
        mid.y += 0.6;
        mid.z += (p1.z + p2.z) * 0.2;

        const curve = new THREE.QuadraticBezierCurve3(p1, mid, p2);
        splineCurves.push({{ curve: curve, from: c.from, to: c.to }});

        const tubeGeom = new THREE.TubeGeometry(curve, 32, 0.05, 8, false);
        const tubeMat = new THREE.MeshBasicMaterial({{
          color: 0x335343,
          transparent: true,
          opacity: 0.55
        }});
        const tube = new THREE.Mesh(tubeGeom, tubeMat);
        scene.add(tube);
      }}
    }});

    // --- FLOWING PARTICLES ---
    const particleCount = 60;
    const particleGeometry = new THREE.SphereGeometry(0.12, 8, 8);
    const particleMaterial = new THREE.MeshBasicMaterial({{ color: 0xd6ed75 }});
    const particles = [];

    for (let i = 0; i < particleCount; i++) {{
      const pMesh = new THREE.Mesh(particleGeometry, particleMaterial);
      pMesh.visible = false;
      scene.add(pMesh);
      particles.push({{
        mesh: pMesh,
        curveIndex: Math.floor(Math.random() * splineCurves.length),
        t: Math.random(),
        speed: 0.003 + Math.random() * 0.004
      }});
    }}

    // --- INTERACTION & RAYCASTING ---
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();
    let selectedMesh = null;

    function selectNode(nodeData, mesh) {{
      selectedMesh = mesh;
      document.getElementById("cardTag").className = "detail-tag " + nodeData.tagClass;
      document.getElementById("cardTag").innerText = nodeData.tag;
      document.getElementById("cardTitle").innerText = nodeData.name;
      document.getElementById("cardDesc").innerText = nodeData.desc;
      document.getElementById("cardInputs").innerText = nodeData.inputs;
      document.getElementById("cardOutputs").innerText = nodeData.outputs;
      document.getElementById("cardFile").innerText = nodeData.file;
      document.getElementById("statusText").innerText = `Inspecting: ${{nodeData.name}}`;
      document.getElementById("statusDot").style.background = "#" + nodeData.color.toString(16).padStart(6, '0');
    }}

    window.addEventListener("pointerdown", (e) => {{
      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(nodeMeshes);
      if (intersects.length > 0) {{
        const hit = intersects[0].object;
        selectNode(hit.userData, hit);
      }}
    }});

    // Default select Orchestrator
    selectNode(nodeMap["orchestrator"].userData, nodeMap["orchestrator"]);

    // Reset Camera
    document.getElementById("btnResetCamera").addEventListener("click", () => {{
      camera.position.set(0, 7, 20);
      controls.target.set(0, 0, 0);
      controls.update();
      document.getElementById("statusText").innerText = "Camera reset to default orbital view.";
    }});

    // --- LIVE SIMULATION SEQUENCER ---
    let isSimulating = false;
    let simStep = 0;
    const simSteps = [
      {{ id: "input", msg: "Step 1/6: Terminal captures ticker and initiates pipeline run..." }},
      {{ id: "orchestrator", msg: "Step 2/6: Orchestrator downloads verified primary filings from Evidence Vault..." }},
      {{ id: "analyst", msg: "Step 3/6: Analyst drafts report, computes metrics, hashes ledger entries..." }},
      {{ id: "verifier1", msg: "Step 4/6: Verifier audits HMAC, stated precision, and checks .meta.json sidecars..." }},
      {{ id: "skeptic", msg: "Step 5/6: Skeptic stress-tests valuation (-200 bps margin, +100 bps WACC)..." }},
      {{ id: "dossier", msg: "Step 6/6: Verifier round 2 passes; Final Audited Dossier synthesized in reports/." }}
    ];

    document.getElementById("btnSimulate").addEventListener("click", () => {{
      if (isSimulating) return;
      isSimulating = true;
      simStep = 0;
      particles.forEach(p => p.mesh.visible = true);
      runNextSimStep();
    }});

    function runNextSimStep() {{
      if (simStep >= simSteps.length) {{
        isSimulating = false;
        document.getElementById("statusText").innerText = "Simulation Completed: Pipeline execution audited with PASS status!";
        document.getElementById("statusDot").style.background = "#22c55e";
        return;
      }}
      const s = simSteps[simStep];
      const targetMesh = nodeMap[s.id];
      if (targetMesh) {{
        selectNode(targetMesh.userData, targetMesh);
        document.getElementById("statusText").innerText = s.msg;
        document.getElementById("statusDot").style.background = "#" + targetMesh.userData.color.toString(16).padStart(6, '0');
        // Pulse animation
        targetMesh.scale.set(1.35, 1.35, 1.35);
        setTimeout(() => targetMesh.scale.set(1.0, 1.0, 1.0), 450);
      }}
      simStep++;
      setTimeout(runNextSimStep, 1750);
    }}

    // --- RESIZE HANDLER ---
    window.addEventListener("resize", () => {{
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    }});

    // --- RENDER LOOP ---
    let clock = new THREE.Clock();

    function animate() {{
      requestAnimationFrame(animate);
      const delta = clock.getDelta();

      // Slow rotation of idle nodes
      nodeMeshes.forEach((mesh) => {{
        mesh.rotation.y += 0.008;
        mesh.rotation.x += 0.004;
      }});

      // Update particle positions along splines
      particles.forEach((p) => {{
        p.t += p.speed;
        if (p.t > 1.0) p.t = 0.0;
        const curve = splineCurves[p.curveIndex].curve;
        const pt = curve.getPoint(p.t);
        p.mesh.position.copy(pt);
      }});

      controls.update();
      renderer.render(scene, camera);
    }}

    animate();
  </script>
</body>
</html>
"""
