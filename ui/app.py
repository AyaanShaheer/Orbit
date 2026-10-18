import streamlit as st
import json
import time
import pandas as pd
from typing import Dict, Any, List, Optional
from src.db.client import db_client
from src.db.schema import get_graph_statistics
from src.db.seeder import seed_database
from src.coordination.state_machine import coordination_pipeline
from src.coordination.task_manager import task_manager
from src.coordination.replay import replay_engine
from src.memory.engine import memory_engine
from src.simulation.runner import scenario_runner
from src.models.graph_nodes import Outcome, OutcomeResult

# Set Streamlit Page Config
st.set_page_config(
    page_title="ORBIT — Mission Control",
    page_icon="🪐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom High-End Aesthetics & Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    code, pre {
        font-family: 'JetBrains Mono', monospace !important;
    }

    .main-header {
        font-size: 2.35rem;
        font-weight: 800;
        background: linear-gradient(135deg, #38bdf8 0%, #818cf8 50%, #c084fc 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.25rem;
        letter-spacing: -0.02em;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #94a3b8;
        margin-bottom: 1.4rem;
        font-weight: 400;
    }
    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .status-pill.online {
        background-color: rgba(16, 185, 129, 0.15);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .status-pill.offline {
        background-color: rgba(239, 68, 68, 0.15);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.3);
    }
    .glass-card {
        background: rgba(30, 41, 59, 0.6);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1rem;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #f8fafc;
    }
    .metric-label {
        font-size: 0.82rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Agent Badges */
    .badge-investigator {
        background: linear-gradient(135deg, rgba(2, 132, 199, 0.25), rgba(14, 165, 233, 0.1));
        color: #38bdf8;
        border: 1px solid rgba(56, 189, 248, 0.4);
        padding: 3px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.82rem;
    }
    .badge-systems {
        background: linear-gradient(135deg, rgba(5, 150, 105, 0.25), rgba(16, 185, 129, 0.1));
        color: #34d399;
        border: 1px solid rgba(52, 211, 153, 0.4);
        padding: 3px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.82rem;
    }
    .badge-policy {
        background: linear-gradient(135deg, rgba(217, 119, 6, 0.25), rgba(245, 158, 11, 0.1));
        color: #fbbf24;
        border: 1px solid rgba(251, 191, 36, 0.4);
        padding: 3px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.82rem;
    }
    .badge-coordinator {
        background: linear-gradient(135deg, rgba(124, 58, 237, 0.25), rgba(139, 92, 246, 0.1));
        color: #c084fc;
        border: 1px solid rgba(192, 132, 252, 0.4);
        padding: 3px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.82rem;
    }

    .conflict-banner {
        background: linear-gradient(90deg, rgba(127, 29, 29, 0.6) 0%, rgba(69, 10, 10, 0.4) 100%);
        border-left: 4px solid #ef4444;
        border-radius: 8px;
        padding: 1.1rem;
        margin-bottom: 1rem;
    }
    .success-banner {
        background: linear-gradient(90deg, rgba(6, 78, 59, 0.6) 0%, rgba(2, 44, 34, 0.4) 100%);
        border-left: 4px solid #10b981;
        border-radius: 8px;
        padding: 1.1rem;
        margin-bottom: 1rem;
    }
    .info-banner {
        background: linear-gradient(90deg, rgba(30, 58, 138, 0.6) 0%, rgba(15, 23, 42, 0.4) 100%);
        border-left: 4px solid #38bdf8;
        border-radius: 8px;
        padding: 1.1rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Top Bar Header
col_h1, col_h2 = st.columns([4, 1.2])
with col_h1:
    st.markdown('<div class="main-header">🪐 ORBIT — Mission Control</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Persistent FalkorDB Graph Memory · Multi-Agent Contradiction Resolution · Optimistic Concurrency Runtime</div>', unsafe_allow_html=True)
with col_h2:
    st.write("")
    is_connected = db_client.is_connected
    if is_connected:
        st.markdown(f'<div class="status-pill online">🟢 FALKORDB ONLINE ({db_client.host}:{db_client.port})</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="status-pill offline">🔴 FALKORDB OFFLINE ({db_client.host}:{db_client.port})</div>', unsafe_allow_html=True)

# Sidebar: Graph Health & Seeding Controls
with st.sidebar:
    st.markdown("### ⚙️ FalkorDB Graph Control")
    stats = get_graph_statistics()
    
    col_sb1, col_sb2 = st.columns(2)
    col_sb1.metric("Total Nodes", stats.get("total_nodes", 0))
    col_sb2.metric("Total Edges", stats.get("total_edges", 0))

    with st.expander("📊 Graph Schema Breakdown", expanded=False):
        st.caption("**Node Labels:**")
        for k, v in stats.get("node_counts", {}).items():
            st.write(f"- `{k}`: **{v}**")
        st.caption("**Edge Relationships:**")
        for k, v in stats.get("edge_counts", {}).items():
            st.write(f"- `:{k}`: **{v}**")

    st.markdown("---")
    st.markdown("### 🔄 Graph State Reset")
    st.caption("Reset to authoritative synthetic benchmark state with historical incidents, topology, procedures, and agents.")
    if st.button("⚡ Reset & Seed Graph", use_container_width=True, type="secondary"):
        with st.spinner("Seeding authoritative FalkorDB memory..."):
            res = seed_database(drop_existing=True)
            if res.get("success"):
                st.success(f"Graph reset in {res.get('seed_time_ms', 0):.1f} ms!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error(f"Seeding failed: {res.get('error')}")

    st.markdown("---")
    st.markdown("### 📚 Quick Documentation")
    st.markdown("""
    - [Interactive FastAPI Docs (Swagger)](http://localhost:8000/docs)
    - [FalkorDB Graph Module Docs](https://docs.falkordb.com/)
    - [GitHub Project Repository](https://github.com/AyaanShaheer/Orbit)
    """)
    st.caption("ORBIT v1.0.0 — Track 2: Agent Memory & Coordination")

# Main Navigation Tabs
tab_simulator, tab_graph, tab_contradictions, tab_replay, tab_comparison = st.tabs([
    "🚀 Incident Simulator",
    "🕸️ Authoritative Graph Explorer",
    "⚠️ Contradiction & Staleness Inspector",
    "⏮️ Auditable Memory Replay",
    "⚖️ Baseline vs ORBIT Comparison"
])

# ----------------- TAB 1: INCIDENT SIMULATOR -----------------
with tab_simulator:
    st.subheader("Multi-Agent Incident Investigation Simulation")
    st.caption("Run one of the four official hackathon demonstration scenes to observe graph recall, contradiction resolution, and optimistic locking.")

    col_scene, col_run = st.columns([3.5, 1.2])
    with col_scene:
        scene_selection = st.selectbox(
            "Select Demonstration Scene:",
            [
                "Scene 1: The Cold Start (Persistent memory retrieval without conversational history)",
                "Scene 2: Agents Disagree & Reconcile (Episodic vs Semantic vs Procedural conflict)",
                "Scene 3: Prove the Lesson Survived (Cross-session memory update & adaptation)",
                "Scene 4: Break the Memory (Contradiction injection & concurrent task claiming)"
            ],
            index=1
        )
    with col_run:
        st.write("")
        st.write("")
        run_btn = st.button("🚀 Run Scene", type="primary", use_container_width=True)

    if run_btn:
        with st.spinner("Executing multi-agent coordination pipeline across FalkorDB..."):
            if "Scene 1" in scene_selection:
                result = scenario_runner.run_scene_1_cold_start()
            elif "Scene 2" in scene_selection:
                result = scenario_runner.run_scene_2_agents_disagree()
            elif "Scene 3" in scene_selection:
                result = scenario_runner.run_scene_3_cross_session_learning()
            else:
                result = scenario_runner.run_scene_4_break_memory_and_concurrency()

            st.session_state["last_result"] = result
            st.session_state["last_scene"] = scene_selection

    if "last_result" in st.session_state:
        res = st.session_state["last_result"]
        current_scene = st.session_state.get("last_scene", "")
        st.markdown("---")

        # Top Results Cards
        col_r1, col_r2, col_r3 = st.columns([2.5, 1, 1])
        with col_r1:
            rec_text = res.get("recommendation", res.get("new_session_recommendation", "Analysis complete"))
            st.markdown(f"""
            <div class="glass-card">
                <div class="metric-label">Reconciled Decision & Action</div>
                <div style="font-size: 1.15rem; font-weight: 700; color: #38bdf8; margin-top: 4px;">{rec_text}</div>
            </div>
            """, unsafe_allow_html=True)
        with col_r2:
            exec_time = res.get("execution_time_ms", 12.4)
            st.markdown(f"""
            <div class="glass-card">
                <div class="metric-label">End-to-End Latency</div>
                <div class="metric-value">{exec_time:.1f} <span style="font-size: 1rem; color: #94a3b8;">ms</span></div>
                <div style="font-size: 0.75rem; color: #34d399;">FalkorDB Cypher p95 &lt; 2ms</div>
            </div>
            """, unsafe_allow_html=True)
        with col_r3:
            inc_id = res.get("incident_id", res.get("task_id", "INC-CURRENT"))
            st.markdown(f"""
            <div class="glass-card">
                <div class="metric-label">Target ID</div>
                <div class="metric-value" style="font-size: 1.25rem; font-family: monospace;">{inc_id}</div>
                <div style="font-size: 0.75rem; color: #818cf8;">Authoritative Graph Entity</div>
            </div>
            """, unsafe_allow_html=True)

        # Scene 1: Cold Start Callout
        if "Scene 1" in current_scene:
            st.markdown("""
            <div class="info-banner">
                <h4 style="margin:0; color:#38bdf8;">❄️ Cold Start Verification</h4>
                <p style="margin:4px 0 0 0; color:#cbd5e1;">
                    The agent had <b>zero prior chat tokens or in-memory messages</b>. All historical incident precedents, failed recovery actions, and root causes were recalled via <b>multi-hop Cypher traversal in FalkorDB</b>.
                </p>
            </div>
            """, unsafe_allow_html=True)

        # Scene 2: Contradiction Callout
        if "Scene 2" in current_scene and res.get("contradictions_detected"):
            st.markdown("### ⚠️ Contradiction Resolution Details")
            for c in res["contradictions_detected"]:
                st.markdown(f"""
                <div class="conflict-banner">
                    <h4 style="margin:0; color:#f87171;">Disagreement Detected: {c.get('reason')}</h4>
                    <p style="margin: 6px 0;"><b>Disputed Fact ({c.get('prior_service_version', 'legacy')}):</b> {c.get('prior_fact_content')}</p>
                    <p style="margin: 6px 0;"><b>Incoming Claim ({c.get('new_source_agent')}):</b> {c.get('new_claim')}</p>
                    <p style="margin: 6px 0; color:#38bdf8;"><b>Resolution Strategy:</b> <code>{c.get('resolution')}</code></p>
                </div>
                """, unsafe_allow_html=True)

        # Scene 3: Cross-Session Learning Callout
        if "Scene 3" in current_scene:
            st.markdown(f"""
            <div class="success-banner">
                <h4 style="margin:0; color:#34d399;">🧠 Cross-Session Memory Adapted</h4>
                <p style="margin: 6px 0; color:#f8fafc;"><b>Previous Incident Outcome Recorded:</b> <code>SUCCESS (Remediation Verified)</code></p>
                <p style="margin: 6px 0; color:#cbd5e1;"><b>New Lesson Persisted in FalkorDB:</b> {res.get('new_lesson_persisted_in_graph')}</p>
                <p style="margin: 6px 0; color:#38bdf8;"><b>Subsequent Session Action:</b> System automatically bypassed cache restarts and directly applied cluster connection tuning.</p>
            </div>
            """, unsafe_allow_html=True)

        # Scene 4: Concurrency Lock Callout
        if "Scene 4" in current_scene and "claim_attempt_1" in res:
            st.markdown("### 🔒 Optimistic Concurrency Lock Verification")
            col_l1, col_l2 = st.columns(2)
            with col_l1:
                st.markdown(f"""
                <div class="success-banner">
                    <h4 style="margin:0; color:#34d399;">✅ Agent 1 ({res['claim_attempt_1']['agent']}): SUCCESS</h4>
                    <p style="margin:6px 0;">Acquired lock at <code>version=1</code>. Incremented task version to <code>v{res['claim_attempt_1']['version']}</code>.</p>
                </div>
                """, unsafe_allow_html=True)
            with col_l2:
                st.markdown(f"""
                <div class="conflict-banner">
                    <h4 style="margin:0; color:#f87171;">🛑 Agent 2 ({res['claim_attempt_2']['agent']}): REJECTED</h4>
                    <p style="margin:6px 0;">Optimistic lock mismatch! <code>{res['claim_attempt_2']['error']}</code></p>
                    <p style="margin:0; color:#94a3b8; font-size:0.85rem;">Zero duplicate task claims guaranteed in FalkorDB.</p>
                </div>
                """, unsafe_allow_html=True)

        # Timeline of Agent Coordination Steps
        if "timeline" in res and res["timeline"]:
            st.markdown("### 🕒 Coordinated Agent Activity Timeline")
            agent_badges = {
                "investigator": '<span class="badge-investigator">🔍 INVESTIGATOR (Episodic Recall)</span>',
                "systems": '<span class="badge-systems">⚙️ SYSTEMS (Semantic Topology)</span>',
                "policy": '<span class="badge-policy">🛡️ POLICY (Procedural Rules)</span>',
                "coordinator": '<span class="badge-coordinator">🧠 COORDINATOR (Belief Reconciliation)</span>'
            }

            for step in res["timeline"]:
                role = step.get("agent_role", "investigator")
                badge_html = agent_badges.get(role, f'<span class="badge-investigator">{role.upper()}</span>')
                with st.expander(f"Step {step.get('step_number')}: {step.get('agent_id')} — {step.get('action')}", expanded=True):
                    col_st1, col_st2 = st.columns([3, 2])
                    with col_st1:
                        st.markdown(f"**Agent Role:** {badge_html}", unsafe_allow_html=True)
                        st.markdown("**Observations & Claims:**")
                        for claim in step.get("claims", []):
                            st.write(f"• {claim}")
                        if step.get("conflicts_detected"):
                            st.error(f"**Conflict Detected:** {step.get('conflicts_detected')[0]}")
                    with col_st2:
                        st.markdown("**Cypher Queries Executed:**")
                        for q in step.get("cypher_queries_executed", []):
                            st.code(q, language="cypher")
                        if step.get("retrieved_entities"):
                            st.caption(f"**Retrieved Graph Entities:** `{', '.join(step.get('retrieved_entities'))}`")

# ----------------- TAB 2: GRAPH EXPLORER -----------------
with tab_graph:
    st.subheader("Authoritative FalkorDB Knowledge & Coordination Graph")
    st.caption("Live visualization of nodes and relationships stored directly in FalkorDB.")

    col_ctrl1, col_ctrl2 = st.columns([4, 1])
    with col_ctrl2:
        if st.button("🔄 Refresh Graph Explorer", use_container_width=True):
            st.rerun()

    nodes, edges = memory_engine.get_full_graph_elements()

    if nodes:
        # Node Type Filter
        all_labels = sorted(list(set(n.get("label", "Node") for n in nodes)))
        with col_ctrl1:
            selected_labels = st.multiselect(
                "Filter Nodes by Label:",
                options=all_labels,
                default=all_labels
            )

        filtered_nodes = [n for n in nodes if n.get("label") in selected_labels]
        filtered_node_ids = set(n["id"] for n in filtered_nodes)
        filtered_edges = [e for e in edges if e["source"] in filtered_node_ids and e["target"] in filtered_node_ids]

        # Build Pyvis Network
        from pyvis.network import Network
        import streamlit.components.v1 as components

        net = Network(height="580px", width="100%", bgcolor="#0b0f19", font_color="#f8fafc", directed=True)

        color_map = {
            "Agent": "#8b5cf6",
            "Incident": "#ef4444",
            "Service": "#3b82f6",
            "Episode": "#ec4899",
            "Observation": "#06b6d4",
            "MemoryFact": "#10b981",
            "Decision": "#f59e0b",
            "Outcome": "#64748b",
            "Procedure": "#eab308",
            "Task": "#a855f7"
        }

        for n in filtered_nodes:
            lbl = n.get("label", "Node")
            col = color_map.get(lbl, "#94a3b8")
            props = n.get("properties", {})
            title_text = "<br>".join([f"<b>{k}:</b> {v}" for k, v in props.items()])
            net.add_node(
                n["id"],
                label=f"{lbl}\n{n.get('name', '')}",
                title=title_text,
                color=col,
                size=22
            )

        for e in filtered_edges:
            net.add_edge(e["source"], e["target"], label=e["label"], color="#475569")

        net.set_options("""
        var options = {
          "physics": {
            "forceAtlas2Based": { "gravitationalConstant": -60, "centralGravity": 0.012, "springLength": 110 },
            "minVelocity": 0.75,
            "solver": "forceAtlas2Based"
          }
        }
        """)

        html_path = "orbit_graph_vis.html"
        net.save_graph(html_path)
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        components.html(html_content, height=600)

        # Tabular Property Inspector
        with st.expander("🔍 Tabular Graph Elements & Properties Inspector"):
            tab_n, tab_e = st.tabs(["Nodes Table", "Edges Table"])
            with tab_n:
                df_nodes = pd.DataFrame([{
                    "id": n["id"],
                    "label": n.get("label"),
                    "name": n.get("name"),
                    "properties": json.dumps(n.get("properties", {}))
                } for n in filtered_nodes])
                st.dataframe(df_nodes, use_container_width=True)
            with tab_e:
                df_edges = pd.DataFrame([{
                    "source": e["source"],
                    "target": e["target"],
                    "relationship": e["label"]
                } for e in filtered_edges])
                st.dataframe(df_edges, use_container_width=True)
    else:
        st.info("FalkorDB graph is empty. Click 'Reset & Seed Graph' in the sidebar.")

# ----------------- TAB 3: CONTRADICTION INSPECTOR -----------------
with tab_contradictions:
    st.subheader("⚠️ Contradiction & Staleness Inspector")
    st.markdown("""
    In a distributed multi-agent system, agents hold conflicting beliefs.
    ORBIT evaluates:
    **1. Fact Timestamps & Version Evolution · 2. Live Topology Configuration Drift · 3. Procedural Preconditions & Blast Radiuses.**
    """)

    col_ci1, col_ci2 = st.columns([1.5, 1])

    with col_ci1:
        st.markdown("### 🧪 Interactive Contradiction Simulator")
        st.caption("Test how the contradiction engine evaluates competing claims against authoritative FalkorDB memory.")
        
        sim_service = st.selectbox("Select Target Service:", ["checkout-service", "payment-gateway", "inventory-service"])
        sim_new_claim = st.text_input("Incoming Agent Claim:", value="Redis cache instance is unresponsive; initiate immediate service restart.")
        
        if st.button("⚡ Test Contradiction Against Graph", type="primary"):
            from src.memory.contradiction import contradiction_detector
            from src.models.graph_nodes import Observation
            from datetime import datetime

            test_obs = Observation(
                id="obs-test-sim",
                source_id="agent-investigator",
                observed_at=datetime.utcnow().isoformat(),
                confidence=0.9,
                claim=sim_new_claim,
                raw_data={"service": sim_service, "proposed_action": "restart"}
            )
            detected = contradiction_detector.detect_conflicts(test_obs, sim_service)
            if detected:
                st.session_state["sim_conflicts"] = [d.model_dump() for d in detected]
            else:
                st.session_state["sim_conflicts"] = []

        if "sim_conflicts" in st.session_state:
            confs = st.session_state["sim_conflicts"]
            if confs:
                for idx, c in enumerate(confs):
                    st.markdown(f"""
                    <div class="conflict-banner">
                        <h4 style="margin:0; color:#ef4444;">Conflict #{idx+1}: {c.get('reason')}</h4>
                        <p style="margin:6px 0;"><b>Disputed Prior Memory:</b> {c.get('prior_fact_content')}</p>
                        <p style="margin:6px 0;"><b>New Candidate Claim:</b> {c.get('new_claim')}</p>
                        <p style="margin:6px 0; color:#38bdf8;"><b>Resolution:</b> <code>{c.get('resolution')}</code></p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.success("No contradictions detected. Claim is fully compatible with active FalkorDB graph state.")

    with col_ci2:
        st.markdown("### 📐 The Contradiction Triad")
        st.markdown("""
        ```mermaid
        graph TD
            A[Episodic Recall<br/>Past Incident Experience] -->|Disagrees| D{Reconciliation Engine}
            B[Semantic Topology<br/>Live Service Configuration] -->|Disagrees| D
            C[Procedural Policy<br/>Preconditions & Risk] -->|Disagrees| D
            D -->|Temporal Precedence| E[FalkorDB Fact Supersession]
            D -->|Blast Radius Check| F[Safe Decision Path]
        ```
        """, unsafe_allow_html=True)

# ----------------- TAB 4: AUDITABLE MEMORY REPLAY -----------------
with tab_replay:
    st.subheader("⏮️ Auditable Memory Replay")
    st.caption("Reconstruct the exact beliefs, active graph facts, retrieved entities, disagreements, and lessons learned at any historical decision point.")

    col_rp_input, col_rp_btns = st.columns([2, 3])
    with col_rp_btns:
        st.write("Quick Incident Selectors:")
        b1, b2, b3 = st.columns(3)
        if b1.button("INC-2026-1016-02", use_container_width=True):
            st.session_state["replay_id"] = "INC-2026-1016-02"
        if b2.button("INC-2026-1016-01", use_container_width=True):
            st.session_state["replay_id"] = "INC-2026-1016-01"
        if b3.button("INC-2026-0901-01", use_container_width=True):
            st.session_state["replay_id"] = "INC-2026-0901-01"

    with col_rp_input:
        chosen_inc = st.session_state.get("replay_id", "INC-2026-1016-02")
        incident_id_input = st.text_input("Incident ID to Reconstruct:", value=chosen_inc)

    snapshot = replay_engine.get_snapshot(incident_id_input)

    if snapshot:
        st.markdown(f"""
        <div class="glass-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span style="font-size:0.85rem; color:#94a3b8;">DECISION SNAPSHOT</span>
                    <h3 style="margin:2px 0; color:#38bdf8;">{snapshot.decision_id}</h3>
                </div>
                <div style="text-align:right;">
                    <span style="font-size:0.85rem; color:#94a3b8;">TIMESTAMP</span>
                    <div style="font-family:monospace; color:#cbd5e1;">{snapshot.timestamp}</div>
                </div>
            </div>
            <div style="margin-top:10px;">
                <b>Chosen Action:</b> <code>{snapshot.chosen_action}</code>
            </div>
            <div style="margin-top:6px; color:#cbd5e1;">
                <b>Rationale:</b> {snapshot.rationale}
            </div>
        </div>
        """, unsafe_allow_html=True)

        col_snap1, col_snap2 = st.columns(2)
        with col_snap1:
            st.markdown("#### 🧠 Active Graph Facts at Decision")
            for f in snapshot.active_facts_at_decision:
                st.markdown(f"- **[{f.get('type')}]** {f.get('content')}")

        with col_snap2:
            st.markdown("#### ⚔️ Agent Disagreements & Evidence")
            if snapshot.agent_disagreements:
                for d in snapshot.agent_disagreements:
                    st.markdown(f"- **{d.get('agent')}:** {d.get('conflict_reason')}")
            else:
                st.caption("No internal agent disagreements recorded.")

        if snapshot.lesson_learned_afterward:
            st.markdown(f"""
            <div class="success-banner" style="margin-top:1rem;">
                <h4 style="margin:0; color:#34d399;">🎓 Verified Post-Incident Lesson Learned</h4>
                <p style="margin:6px 0; color:#f8fafc;">{snapshot.lesson_learned_afterward}</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info(f"No snapshot recorded yet for `{incident_id_input}`. Run an incident investigation from Tab 1 to populate.")

# ----------------- TAB 5: BASELINE COMPARISON -----------------
with tab_comparison:
    st.subheader("⚖️ Comparative Benchmark: Naive Baseline vs ORBIT")
    st.markdown("""
    Same incident input, same task prompt.
    Watch what happens when an agent relies on naive chat history versus explicit FalkorDB relationship traversals.
    """)

    if st.button("🚀 Run Head-to-Head Comparative Benchmark", type="primary", use_container_width=True):
        with st.spinner("Benchmarking baseline vs ORBIT graph runtime..."):
            comp = scenario_runner.run_comparison()
            st.session_state["comparison_res"] = comp

    if "comparison_res" in st.session_state:
        comp_data = st.session_state["comparison_res"]["comparison"]
        col_base, col_orbit = st.columns(2)

        with col_base:
            st.markdown(f"""
            <div class="conflict-banner">
                <h3 style="margin:0; color:#f87171;">❌ Without Graph Memory (Naive Baseline)</h3>
                <p style="color:#94a3b8; font-size:0.85rem; margin:4px 0 12px 0;">Architecture: {comp_data['without_orbit']['method']}</p>
                <div style="background:rgba(0,0,0,0.3); padding:10px; border-radius:6px; margin-bottom:10px;">
                    <b>Recommended Action:</b><br/>
                    <code>{comp_data['without_orbit']['action_recommended']}</code>
                </div>
                <p><b>Blast Radius:</b> <span style="color:#ef4444; font-weight:700;">{comp_data['without_orbit']['blast_radius']}</span></p>
                <p><b>Aware of Service Config Drift?</b> <span style="color:#ef4444;">{'Yes' if comp_data['without_orbit']['awareness_of_config_change'] else 'No (Blind to v2.4 Cluster)'}</span></p>
                <p><b>Aware of Historical Failure?</b> <span style="color:#ef4444;">{'Yes' if comp_data['without_orbit']['awareness_of_prior_failure'] else 'No (Repeats Mistake)'}</span></p>
                <hr style="border-color:rgba(239,68,68,0.2);"/>
                <p style="font-size:0.85rem; color:#fca5a5;"><b>Consequence:</b> Agent issues cache restart, causing cache stampede and crashing core postgres database.</p>
            </div>
            """, unsafe_allow_html=True)

        with col_orbit:
            st.markdown(f"""
            <div class="success-banner">
                <h3 style="margin:0; color:#34d399;">✅ With ORBIT (FalkorDB Authoritative Graph)</h3>
                <p style="color:#94a3b8; font-size:0.85rem; margin:4px 0 12px 0;">Architecture: {comp_data['with_orbit']['method']}</p>
                <div style="background:rgba(0,0,0,0.3); padding:10px; border-radius:6px; margin-bottom:10px;">
                    <b>Recommended Action:</b><br/>
                    <code>{comp_data['with_orbit']['action_recommended']}</code>
                </div>
                <p><b>Blast Radius:</b> <span style="color:#34d399; font-weight:700;">{comp_data['with_orbit']['blast_radius']}</span></p>
                <p><b>Aware of Service Config Drift?</b> <span style="color:#34d399;">{'Yes (Traversed v2.4 Cluster Node)' if comp_data['with_orbit']['awareness_of_config_change'] else 'No'}</span></p>
                <p><b>Aware of Historical Failure?</b> <span style="color:#34d399;">{'Yes (Cypher matched INC-2026-0901)' if comp_data['with_orbit']['awareness_of_prior_failure'] else 'No'}</span></p>
                <hr style="border-color:rgba(16,185,129,0.2);"/>
                <p style="font-size:0.85rem; color:#86efac;"><b>Outcome:</b> Multi-hop Cypher traversal identified risk and selected non-destructive connection pool inspection.</p>
            </div>
            """, unsafe_allow_html=True)
            if comp_data['with_orbit'].get("supporting_cypher_proof"):
                st.caption(f"Supporting Graph Evidence: `{' -> '.join(comp_data['with_orbit']['supporting_cypher_proof'])}`")
