import json
import os
import httpx
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")

NODE_ICONS = {
    "classifier": "🏷️",
    "planner":    "📝",
    "gatherer":   "📥",
    "comparator": "⚖️",
    "writer":     "✍️",
    "scorer":     "🎯",
    "persist":    "💾",
}
NODE_LABELS = {
    "classifier": "Classifying query",
    "planner":    "Breaking into sub-questions",
    "gatherer":   "Retrieving from knowledge base",
    "comparator": "Comparing sources",
    "writer":     "Writing report",
    "scorer":     "Scoring confidence",
    "persist":    "Saving run",
}

st.set_page_config(
    page_title="Genie AI — Research Engine",
    page_icon="🔍",
    layout="wide",
)

# ── Session state ────────────────────────────────────────────────────────────
if "loaded_result" not in st.session_state:
    st.session_state.loaded_result = None

# ── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")
    user_api_key = st.text_input(
        "OpenAI API Key",
        type="password",
        placeholder="sk-… (overrides server key)",
        help="Sent per-request as X-Api-Key header.",
    )
    st.divider()

    st.header("🕓 Recent Runs")
    try:
        resp = httpx.get(f"{API_URL}/runs/recent", timeout=5)
        recent = resp.json() if resp.status_code == 200 else []
        if not isinstance(recent, list):
            recent = []
    except Exception:
        recent = []

    if recent:
        for run in recent:
            status = run.get("status", "—")
            colour = "🟢" if status == "completed" else "🟡" if status == "needs_review" else "🔴"
            query_text = run.get("query", "—")
            trace = (run.get("trace_id") or "—")[:8]
            confidence = run.get("confidence")
            conf_str = f"{confidence:.0%}" if confidence is not None else "—"

            if st.button(
                f"{colour} {query_text[:35]}{'…' if len(query_text) > 35 else ''}",
                key=f"run_{trace}",
                help=f"Trace: {trace}… · {conf_str}",
                use_container_width=True,
            ):
                # Load this run's report into main area
                artifacts = run.get("artifacts")
                if isinstance(artifacts, str):
                    try:
                        artifacts = json.loads(artifacts)
                    except Exception:
                        artifacts = {}
                report = (artifacts or {}).get("report") if artifacts else run.get("report")
                if isinstance(report, str):
                    try:
                        report = json.loads(report)
                    except Exception:
                        report = {}
                st.session_state.loaded_result = {
                    "trace_id": run.get("trace_id"),
                    "status": status,
                    "confidence": confidence,
                    "report": report,
                    "pipeline": [],
                }
            st.caption(f"`{trace}…` · {conf_str}")
    else:
        st.caption("No runs yet.")

# ── Main ─────────────────────────────────────────────────────────────────────
st.title("🔍 Genie AI — Research Engine")
st.caption("Multi-Agent Research & Reporting Engine (MARRE) · Phase 1")

query = st.text_area(
    "Research Query",
    placeholder="e.g. Compare AcmeDoc AI and PaperMind AI for enterprise document processing",
    height=100,
)

run_btn = st.button("Run Research", type="primary", disabled=not query.strip())


def render_result(final: dict, node_outputs: dict) -> None:
    status = final.get("status", "unknown")
    confidence = final.get("confidence")
    trace_id = final.get("trace_id", "—")
    report = final.get("report")
    if isinstance(report, str):
        try:
            report = json.loads(report)
        except Exception:
            report = {}

    c1, c2, c3 = st.columns(3)
    with c1:
        colour = "🟢" if status == "completed" else "🟡" if status == "needs_review" else "🔴"
        st.metric("Status", f"{colour} {status}")
    with c2:
        st.metric("Confidence", f"{confidence:.0%}" if confidence is not None else "—")
    with c3:
        st.metric("Trace ID", trace_id[:8] + "…" if trace_id and trace_id != "—" else "—")

    if status == "needs_review":
        st.warning("Confidence below 0.7 — results flagged for human review.")

    if node_outputs:
        st.divider()
        st.subheader("🔬 Pipeline Trace")
        for node, output in node_outputs.items():
            icon = NODE_ICONS.get(node, "⚙️")
            with st.expander(f"{icon} **{node.capitalize()}**", expanded=False):
                if node == "classifier":
                    st.markdown(f"**Classification:** `{output.get('classification', '—')}`")
                elif node == "planner":
                    st.markdown("**Sub-questions:**")
                    for i, q in enumerate(output.get("sub_questions", []), 1):
                        st.markdown(f"{i}. {q}")
                elif node == "gatherer":
                    chunks = output.get("chunks", [])
                    rag = [c for c in chunks if c["source_id"] != "hackernews"]
                    hn  = [c for c in chunks if c["source_id"] == "hackernews"]
                    st.markdown(
                        f"**{len(chunks)} total chunks** — "
                        f"{output.get('rag_count', len(rag))} from knowledge base, "
                        f"{output.get('hn_count', len(hn))} from HackerNews"
                    )
                    if rag:
                        st.markdown("**📚 Knowledge Base**")
                        for c in rag:
                            st.markdown(f"- `{c['source_id']}` ({c['source_type']}) — *{c['preview']}…*")
                    if hn:
                        st.markdown("**💬 HackerNews (last 6 months)**")
                        for c in hn:
                            title = c.get("title", "")
                            url = c.get("url", "")
                            link = f"[{title}]({url})" if url else title
                            st.markdown(f"- {link} — *{c['preview'][:150]}…*")
                elif node == "comparator":
                    for comp in output.get("comparisons", []):
                        if not isinstance(comp, dict):
                            continue
                        st.markdown(f"**{comp.get('claim', '—')}**")
                        for a in comp.get("agreement", []):
                            st.markdown(f"  ✅ {a}")
                        for c in comp.get("conflicts", []):
                            st.markdown(f"  ❌ {c}")
                elif node == "scorer":
                    st.markdown(f"**Confidence:** `{output.get('confidence', 0):.3f}`")
                    st.markdown(f"**Rationale:** {output.get('rationale', '—')}")
                else:
                    st.json(output)

    if not report:
        st.info("Query classified as casual — no report generated.")
        return

    st.divider()
    st.subheader("📋 Executive Summary")
    st.write(report.get("executive_summary", "—"))
    if report.get("recommendation"):
        st.info(f"**Recommendation:** {report['recommendation']}")

    st.divider()
    left, right = st.columns(2)
    with left:
        st.subheader("📌 Key Findings")
        for f in report.get("findings", []):
            st.markdown(f"- {f}")
    with right:
        st.subheader("⚖️ Comparisons")
        for comp in report.get("comparisons", []):
            if not isinstance(comp, dict):
                continue
            with st.expander(f"{comp.get('claim', 'Claim')}  —  {comp.get('confidence', 0):.0%}"):
                for a in comp.get("agreement", []):
                    st.markdown(f"✅ {a}")
                for c in comp.get("conflicts", []):
                    st.markdown(f"❌ {c}")

    st.divider()
    if report.get("open_questions"):
        st.subheader("❓ Open Questions")
        for q in report["open_questions"]:
            st.markdown(f"- {q}")
        st.divider()

    sc, cc = st.columns(2)
    with sc:
        st.subheader("📚 Sources Used")
        for s in report.get("sources_used", []):
            st.markdown(f"- `{s}`")
    with cc:
        st.subheader("🔗 Citations")
        for cite in report.get("citations") or []:
            st.markdown(
                f"- **{cite.get('source_id')}** · {cite.get('location', '')} — *{cite.get('used_for', '')}*"
            )

    with st.expander("🗂 Raw JSON"):
        st.json(final)


# ── Show loaded run from sidebar ─────────────────────────────────────────────
if st.session_state.loaded_result and not run_btn:
    st.info("📂 Showing saved run from recent history")
    render_result(st.session_state.loaded_result, {})

# ── Run pipeline ─────────────────────────────────────────────────────────────
if run_btn and query.strip():
    st.session_state.loaded_result = None
    node_outputs: dict[str, dict] = {}
    final: dict = {}

    with st.status("🔍 Starting research pipeline…", expanded=True) as status_ui:
        headers = {"x-api-key": user_api_key} if user_api_key else {}
        try:
            with httpx.Client(timeout=180) as client:
                with client.stream(
                    "POST",
                    f"{API_URL}/research/stream",
                    json={"query": query},
                    headers=headers,
                ) as response:
                    response.raise_for_status()
                    for line in response.iter_lines():
                        line = line.strip()
                        if not line.startswith("data:"):
                            continue
                        try:
                            event = json.loads(line[5:].strip())
                        except json.JSONDecodeError:
                            continue

                        node = event.get("node", "")
                        state = event.get("state", "")
                        output = event.get("output", {})
                        icon = NODE_ICONS.get(node, "⚙️")
                        label = NODE_LABELS.get(node, node)

                        if node == "done":
                            final = event
                            status_ui.update(label="✅ Research complete!", state="complete", expanded=False)
                        elif state == "running":
                            status_ui.write(f"{icon} **{label}…**")
                        elif state == "done":
                            node_outputs[node] = output
                            status_ui.write(f"  ✅ {label} — done")

        except httpx.HTTPStatusError as e:
            st.error(f"API error {e.response.status_code}")
            st.stop()
        except Exception as e:
            st.error(f"Stream failed: {e}")
            st.stop()

    if not final:
        st.warning("No response received from pipeline.")
        st.stop()

    render_result(final, node_outputs)
