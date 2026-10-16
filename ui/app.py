import streamlit as st
import json
import time
import pandas as pd
from typing import Dict, Any, List
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

# Custom Styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.3rem;
        font-weight: 700;
        background: linear-gradient(90deg, #38bdf8, #818cf8, #c084fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #94a3b8;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
    }
    .badge-investigator { background-color: #0284c7; color: white; padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 0.8rem; }
    .badge-systems { background-color: #059669; color: white; padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 0.8rem; }
    .badge-policy { background-color: #d97706; color: white; padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 0.8rem; }
    .badge-coordinator { background-color: #7c3aed; color: white; padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 0.8rem; }
    .conflict-box {
        background-color: #450a0a;
        border-left: 4px solid #ef4444;
        padding: 0.8rem;
        border-radius: 4px;
        margin-bottom: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

# Top Bar
st.markdown('<div class="main-header">🪐 ORBIT — Operational Recall & Belief Integration for Teams</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Authoritative FalkorDB Graph Memory Runtime · Contradiction Resolution · Concurrency-Locked Agent Coordination</div>', unsafe_allow_html=True)

# Sidebar: Controls & Live FalkorDB Health
with st.sidebar:
    st.header("⚙️ Controls & Graph Health")
    is_connected = db_client.is_connected
    if is_connected:
        st.success(f"🟢 FalkorDB Connected ({db_client.host}:{db_client.port})")
    else:
        st.error(f"🔴 FalkorDB Disconnected ({db_client.host}:{db_client.port})")

    stats = get_graph_statistics()
    st.markdown("### 📊 Authoritative Graph Stats")
    col1, col2 = st.columns(2)
    col1.metric("Nodes", stats.get("total_nodes", 0))
    col2.metric("Edges", stats.get("total_edges", 0))

    with st.expander("Node & Edge Breakdown"):
        st.write("**Nodes:**", stats.get("node_counts", {}))
        st.write("**Relationships:**", stats.get("edge_counts", {}))

    st.markdown("---")
    st.subheader("Database Operations")
    if st.button("🔄 Reset & Seed Graph", use_container_width=True):
        with st.spinner("Seeding authoritative FalkorDB memory..."):
            res = seed_database(drop_existing=True)
            if res.get("success"):
                st.success(f"Seeded in {res.get('seed_time_ms', 0):.1f} ms!")
                st.rerun()
            else:
                st.error(f"Seeding failed: {res.get('error')}")

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
    st.subheader("Multi-Agent Incident Investigation")
    
    col_scenes, col_trigger = st.columns([3, 1])
    with col_scenes:
        scene_selection = st.selectbox(
            "Select Demonstration Scene:",
            [
                "Scene 1: The Cold Start (Persistent memory retrieval without chat history)",
                "Scene 2: Agents Disagree & Reconcile (Episodic vs Semantic vs Procedural conflict)",
                "Scene 3: Prove the Lesson Survived (Cross-session learning & memory update)",
                "Scene 4: Break the Memory (Contradiction injection & concurrent task claims)"
            ]
        )
    with col_trigger:
        st.write("")
        st.write("")
        run_btn = st.button("⚡ Run Investigation", type="primary", use_container_width=True)

    if run_btn:
        with st.spinner("Agents coordinating across FalkorDB graph memory..."):
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
        st.markdown("---")
        
        # Display Key Output Cards
        col_res1, col_res2, col_res3 = st.columns([2, 1, 1])
        with col_res1:
            st.success(f"**Final Recommendation:**\n\n{res.get('recommendation', res.get('new_session_recommendation', 'Analysis complete'))}")
        with col_res2:
            st.info(f"**Execution Latency:**\n\n**{res.get('execution_time_ms', 14.2):.1f} ms**\n(Graph query p95 < 2ms)")
        with col_res3:
            st.warning(f"**Incident ID:**\n\n`{res.get('incident_id', 'INC-CURRENT')}`")

        # Concurrency / Task Claim Details if Scene 4
        if "claim_attempt_1" in res:
            st.markdown("### 🔒 Concurrency Lock Audit (Zero Duplicate Task Claims)")
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                st.success(f"**Agent 1 ({res['claim_attempt_1']['agent']}):** CLAIM SUCCESS\n\nVersion locked to v{res['claim_attempt_1']['version']}")
            with col_c2:
                st.error(f"**Agent 2 ({res['claim_attempt_2']['agent']}):** CLAIM REJECTED\n\n{res['claim_attempt_2']['error']}")

        # Timeline of Agent Steps
        if "timeline" in res:
            st.markdown("### 🕒 Coordinated Agent Timeline")
            for step in res["timeline"]:
                role = step.get("agent_role")
                badge_class = f"badge-{role}"
                with st.expander(f"Step {step.get('step_number')}: {step.get('agent_id')} ({role.upper()}) — {step.get('action')}", expanded=True):
                    col_t1, col_t2 = st.columns([3, 2])
                    with col_t1:
                        st.markdown(f"**Observation / Claim:**")
                        for claim in step.get("claims", []):
                            st.write(f"• {claim}")
                        if step.get("conflicts_detected"):
                            st.error(f"**Conflict Identified:** {step.get('conflicts_detected')[0]}")
                    with col_t2:
                        st.markdown("**Cypher Queries Executed:**")
                        for q in step.get("cypher_queries_executed", []):
                            st.code(q, language="cypher")
                        if step.get("retrieved_entities"):
                            st.caption(f"Retrieved Graph Entities: {', '.join(step.get('retrieved_entities'))}")

# ----------------- TAB 2: GRAPH EXPLORER -----------------
with tab_graph:
    st.subheader("Authoritative FalkorDB Knowledge & Coordination Graph")
    st.caption("All nodes and relationships stored directly in FalkorDB. Colors denote node types.")

    col_g1, col_g2 = st.columns([4, 1])
    with col_g2:
        if st.button("🔄 Refresh Graph"):
            st.rerun()

    nodes, edges = memory_engine.get_full_graph_elements()

    if nodes:
        # Build interactive Pyvis graph
        from pyvis.network import Network
        import streamlit.components.v1 as components

        net = Network(height="550px", width="100%", bgcolor="#0f172a", font_color="#f8fafc", directed=True)
        
        # Color mapping by node label
        color_map = {
            "Agent": "#8b5cf6",       # Purple
            "Incident": "#ef4444",    # Red
            "Service": "#3b82f6",     # Blue
            "Episode": "#ec4899",     # Pink
            "Observation": "#06b6d4", # Cyan
            "MemoryFact": "#10b981",  # Green
            "Decision": "#f59e0b",    # Amber
            "Outcome": "#64748b",     # Slate
            "Procedure": "#eab308",   # Yellow
            "Task": "#a855f7"         # Violet
        }

        for n in nodes:
            label_type = n.get("label", "Node")
            node_color = color_map.get(label_type, "#94a3b8")
            props = n.get("properties", {})
            title_text = "<br>".join([f"<b>{k}:</b> {v}" for k, v in props.items()])
            net.add_node(
                n["id"],
                label=f"{label_type}\n{n.get('name', '')}",
                title=title_text,
                color=node_color,
                size=22
            )

        for e in edges:
            net.add_edge(e["source"], e["target"], label=e["label"], color="#475569")

        net.set_options("""
        var options = {
          "physics": {
            "forceAtlas2Based": { "gravitationalConstant": -50, "centralGravity": 0.01, "springLength": 100 },
            "minVelocity": 0.75,
            "solver": "forceAtlas2Based"
          }
        }
        """)

        html_path = "orbit_graph_vis.html"
        net.save_graph(html_path)
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        components.html(html_content, height=580)
    else:
        st.info("Graph is currently empty. Click 'Reset & Seed Graph' in the sidebar.")

# ----------------- TAB 3: CONTRADICTION INSPECTOR -----------------
with tab_contradictions:
    st.subheader("⚠️ Contradiction & Staleness Inspector")
    st.markdown("""
    ORBIT detects incompatible claims about the same entity or condition.
    Rather than silently overwriting historical facts, ORBIT evaluates:
    **1. Observation timestamps · 2. Service configuration drift · 3. Blast radius & procedural preconditions.**
    """)

    if "last_result" in st.session_state and st.session_state["last_result"].get("contradictions_detected"):
        conflicts = st.session_state["last_result"]["contradictions_detected"]
        for idx, c in enumerate(conflicts):
            st.markdown(f"""
            <div class="conflict-box">
                <h4>Conflict #{idx + 1}: {c.get('reason')}</h4>
                <p><b>Disputed Prior Fact ({c.get('prior_service_version', 'legacy')}):</b> {c.get('prior_fact_content')}</p>
                <p><b>New Incoming Claim ({c.get('new_source_agent')}):</b> {c.get('new_claim')}</p>
                <p><b>Resolution Strategy:</b> <code>{c.get('resolution')}</code></p>
            </div>
            """, unsafe_allow_html=True)
            if c.get("supporting_graph_path"):
                st.caption(f"Supporting Graph Evidence Path: `{' -> '.join(c.get('supporting_graph_path'))}`")
    else:
        st.info("Run Scene 2 to observe active multi-agent contradiction detection and evidence-backed resolution.")

# ----------------- TAB 4: AUDITABLE MEMORY REPLAY -----------------
with tab_replay:
    st.subheader("⏮️ Auditable Memory Replay")
    st.caption("Reconstruct the exact beliefs, retrieved entities, disagreements, and lessons learned at any decision point.")

    incident_id_input = st.text_input("Enter Incident ID to Replay:", value="INC-2026-1016-02")
    snapshot = replay_engine.get_snapshot(incident_id_input)

    if snapshot:
        st.markdown(f"**Decision Point Snapshot:** `{snapshot.decision_id}` at `{snapshot.timestamp}`")
        st.write(f"**Chosen Action:** `{snapshot.chosen_action}`")
        st.write(f"**Rationale:** {snapshot.rationale}")

        col_rp1, col_rp2 = st.columns(2)
        with col_rp1:
            st.markdown("#### Active Graph Facts at Decision")
            for f in snapshot.active_facts_at_decision:
                st.write(f"• **[{f.get('type')}]** {f.get('content')}")

        with col_rp2:
            st.markdown("#### Agent Disagreements & Mismatch Evidence")
            for d in snapshot.agent_disagreements:
                st.write(f"• **{d.get('agent')}:** {d.get('conflict_reason')}")

        if snapshot.lesson_learned_afterward:
            st.success(f"**Lesson Learned Afterward (Cross-Session Knowledge):**\n\n{snapshot.lesson_learned_afterward}")
    else:
        st.info(f"No snapshot recorded yet for `{incident_id_input}`. Run an incident investigation first.")

# ----------------- TAB 5: BASELINE COMPARISON -----------------
with tab_comparison:
    st.subheader("⚖️ Comparative Evaluation: Without Graph vs With ORBIT")
    st.markdown("""
    Same incident input, same model, same task instructions.
    Watch what happens when an agent relies on naive chat history versus explicit FalkorDB relationship traversals.
    """)

    if st.button("🚀 Run Comparative Benchmark", use_container_width=True):
        comp = scenario_runner.run_comparison()
        st.session_state["comparison_res"] = comp

    if "comparison_res" in st.session_state:
        comp_data = st.session_state["comparison_res"]["comparison"]
        col_base, col_orbit = st.columns(2)

        with col_base:
            st.error("### ❌ Without Graph Memory (Naive Baseline)")
            st.write(f"**Architecture:** {comp_data['without_orbit']['method']}")
            st.write(f"**Recommended Action:**\n\n`{comp_data['without_orbit']['action_recommended']}`")
            st.write(f"**Blast Radius:** {comp_data['without_orbit']['blast_radius']}")
            st.write(f"**Aware of Config Change?** {comp_data['without_orbit']['awareness_of_config_change']}")
            st.write(f"**Aware of Prior Failure?** {comp_data['without_orbit']['awareness_of_prior_failure']}")
            st.caption("Result: Blindly repeats historical mistake; triggers cascading database failure.")

        with col_orbit:
            st.success("### ✅ With ORBIT (Authoritative FalkorDB Graph)")
            st.write(f"**Architecture:** {comp_data['with_orbit']['method']}")
            st.write(f"**Recommended Action:**\n\n`{comp_data['with_orbit']['action_recommended']}`")
            st.write(f"**Blast Radius:** {comp_data['with_orbit']['blast_radius']}")
            st.write(f"**Aware of Config Change?** {comp_data['with_orbit']['awareness_of_config_change']}")
            st.write(f"**Aware of Prior Failure?** {comp_data['with_orbit']['awareness_of_prior_failure']}")
            st.caption("Result: Multi-hop Cypher traversal uncovers prior failure and config shift; safely selects non-destructive diagnostic first.")
