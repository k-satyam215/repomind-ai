import json
import os
import time

import requests
import streamlit as st

BACKEND = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="RepoMind AI", page_icon="🤖", layout="wide")

st.markdown("""
<style>
.stApp { background: radial-gradient(circle at top, #0f172a, #020617); color: #e2e8f0; }
h1 { font-size: 2.8rem !important; font-weight: 700;
     background: linear-gradient(90deg, #818cf8, #c084fc);
     -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
input { border-radius: 12px !important; border: 1px solid #334155 !important;
        background-color: #020617 !important; color: white !important; }
.stButton>button { border-radius: 12px; height: 45px; font-weight: 600;
    background: linear-gradient(135deg, #6366f1, #a855f7); color: white;
    border: none; transition: 0.3s; }
.stButton>button:hover { transform: scale(1.04); background: linear-gradient(135deg, #4f46e5, #9333ea); }
[data-testid="stMetric"] { background: rgba(15,23,42,0.6); border: 1px solid #334155;
    padding: 20px; border-radius: 14px; backdrop-filter: blur(10px); }
.sev-critical { background: rgba(239,68,68,.15); border:1px solid #ef4444; border-radius:8px;
    padding:3px 10px; color:#ef4444; font-weight:700; font-size:.75rem; display:inline-block; }
.sev-high { background: rgba(249,115,22,.15); border:1px solid #f97316; border-radius:8px;
    padding:3px 10px; color:#f97316; font-weight:700; font-size:.75rem; display:inline-block; }
.sev-medium { background: rgba(234,179,8,.15); border:1px solid #eab308; border-radius:8px;
    padding:3px 10px; color:#eab308; font-weight:700; font-size:.75rem; display:inline-block; }
.approve-box { border:1px solid #22c55e; border-radius:12px; padding:16px;
    background:rgba(34,197,94,.07); margin:8px 0; }
.stream-box { background:#0f172a; border:1px solid #334155; border-radius:12px;
    padding:16px; font-family:monospace; font-size:.82rem; line-height:1.6;
    max-height:400px; overflow-y:auto; color:#a5f3fc; }
hr { border:1px solid #1e293b; }
</style>
""", unsafe_allow_html=True)


def sev_badge(sev: str) -> str:
    s = (sev or "medium").lower()
    return f'<span class="sev-{s}">{s.upper()}</span>'


# ─── Header ─────────────────────────────────────────────────────────────────
st.markdown("# 🤖 RepoMind AI")
st.caption("⚡ Autonomous Code Debugging Agent · v1.3.0")
st.divider()

tab_analyze, tab_stream, tab_parallel, tab_metrics = st.tabs([
    "🔍 Analyze", "⚡ Streaming Fix", "🚀 Parallel Mode", "📊 Observability"
])

# ─── Session state ───────────────────────────────────────────────────────────
for key, default in [
    ("analysis_data", None),
    ("fix_results", {}),
    ("pending_approvals", {}),   # {idx: {file: fixed_code}}
    ("parallel_results", None),
    ("stream_fix", {}),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Standard Analyze
# ══════════════════════════════════════════════════════════════════════════════
with tab_analyze:
    repo = st.text_input("🔗 GitHub Repository URL", key="repo_url_standard",
                         placeholder="https://github.com/owner/repo")
    col1, col2 = st.columns([1, 5])
    with col1:
        go = st.button("🚀 Analyze", use_container_width=True, key="analyze_btn")
    with col2:
        if st.button("🔄 Reset", use_container_width=True, key="reset_btn"):
            st.session_state.analysis_data = None
            st.session_state.fix_results = {}
            st.session_state.pending_approvals = {}
            st.rerun()

    if go:
        if not repo.strip():
            st.error("Enter a valid GitHub URL")
        else:
            bar = st.progress(0)
            try:
                st.info("🔍 Cloning + analyzing...")
                bar.progress(30)
                res = requests.post(f"{BACKEND}/analyze", json={"repo_url": repo}, timeout=300)
                bar.progress(80)
                data = res.json()
                bar.progress(100)
                if res.status_code != 200:
                    st.error(data.get("detail", "Error"))
                else:
                    st.session_state.analysis_data = data
                    st.success("✅ Analysis complete!")
            except Exception as e:
                st.error(str(e))

    data = st.session_state.analysis_data
    if data:
        issues = data.get("issues", [])
        crit = sum(1 for i in issues if i.get("report", {}).get("severity") == "critical")
        high = sum(1 for i in issues if i.get("report", {}).get("severity") == "high")
        med  = sum(1 for i in issues if i.get("report", {}).get("severity") == "medium")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📁 Files scanned", len(issues))
        c2.metric("🔴 Critical", crit)
        c3.metric("🟠 High", high)
        c4.metric("🟡 Medium", med)

        st.divider()
        st.subheader("📊 Architecture")
        st.markdown(data.get("analysis", ""))
        st.divider()

        if not issues:
            st.success("✅ No bugs detected!")
        else:
            st.subheader(f"🐞 {len(issues)} issue(s) detected")

            for idx, issue in enumerate(issues):
                report = issue["report"]
                sev = report.get("severity", "medium")
                conf = report.get("confidence", 0.0)
                btype = report.get("bug_type", "other")

                with st.expander(
                    f"📄 `{issue['file']}` — {sev.upper()}  (confidence {conf:.0%})",
                    expanded=(sev == "critical")
                ):
                    st.markdown(
                        f"{sev_badge(sev)} &nbsp; "
                        f"<span style='color:#94a3b8;font-size:.85rem;'>{btype} · confidence {conf:.0%}</span>",
                        unsafe_allow_html=True
                    )
                    st.markdown(f"""
<div style="padding:14px;border-radius:12px;background:rgba(15,23,42,.6);border:1px solid #334155;margin:8px 0">
<p style="color:#ff4b4b"><b>🔴 Bug:</b> {report.get('bug')}</p>
<p style="color:#facc15"><b>🟡 Impact:</b> {report.get('impact')}</p>
<p style="color:#4ade80"><b>🟢 Fix hint:</b> {report.get('fix_hint')}</p>
</div>""", unsafe_allow_html=True)

                    col_fix, col_multi = st.columns(2)

                    # ── Standard fix ──────────────────────────────────────────
                    with col_fix:
                        if st.button("⚡ Generate Fix", key=f"fix_{idx}"):
                            with st.spinner("Generating fix..."):
                                try:
                                    fix_res = requests.post(f"{BACKEND}/fix", json={
                                        "repo_path": data["repo_path"],
                                        "file": issue["file"],
                                        "bug": report
                                    })
                                    fd = fix_res.json()
                                    diff_res = requests.post(f"{BACKEND}/diff", json={
                                        "old": fd["old"], "new": fd["new"],
                                        "filename": issue["file"]
                                    })
                                    dd = diff_res.json()
                                    st.session_state.fix_results[idx] = {
                                        "diff": dd.get("diff", ""),
                                        "new": fd["new"],
                                        "old": fd["old"],
                                        "file": issue["file"]
                                    }
                                except Exception as e:
                                    st.error(str(e))

                    # ── Multi-file fix ────────────────────────────────────────
                    with col_multi:
                        if st.button("🗂 Multi-file Fix", key=f"multifix_{idx}",
                                     help="Detect and fix related files too"):
                            with st.spinner("Analyzing dependencies + generating multi-file fix..."):
                                try:
                                    mf_res = requests.post(f"{BACKEND}/fix/multi", json={
                                        "repo_path": data["repo_path"],
                                        "file": issue["file"],
                                        "related_files": [],
                                        "bug": report
                                    })
                                    mfd = mf_res.json()
                                    if mfd.get("changed_file_count", 0) > 0:
                                        st.session_state.pending_approvals[idx] = {
                                            "fixed_files": mfd["fixed_files"],
                                            "diffs": mfd["diffs"],
                                            "repo_path": data["repo_path"]
                                        }
                                    else:
                                        st.info("No changes needed across related files.")
                                except Exception as e:
                                    st.error(str(e))

                    # ── Show standard fix result ──────────────────────────────
                    if idx in st.session_state.fix_results:
                        fr = st.session_state.fix_results[idx]
                        st.markdown("#### 🛠 Diff preview")
                        st.code(fr["diff"], language="diff")

                        # Human-in-the-loop approve/reject
                        st.markdown('<div class="approve-box">', unsafe_allow_html=True)
                        st.markdown("**Apply this fix to the repo?**")
                        ca, cr = st.columns(2)
                        with ca:
                            if st.button("✅ Approve & Apply", key=f"approve_{idx}"):
                                try:
                                    ap = requests.post(f"{BACKEND}/fix/approve", json={
                                        "repo_path": data["repo_path"],
                                        "approved_fixes": {fr["file"]: fr["new"]}
                                    })
                                    if ap.status_code == 200:
                                        st.success(f"✅ Fix applied to `{fr['file']}`")
                                    else:
                                        st.error(ap.json().get("detail", "Apply failed"))
                                except Exception as e:
                                    st.error(str(e))
                        with cr:
                            if st.button("❌ Reject", key=f"reject_{idx}"):
                                del st.session_state.fix_results[idx]
                                st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)

                        with st.expander("📂 Full fixed file"):
                            st.code(fr["new"], language="python")

                    # ── Show multi-file approval UI ───────────────────────────
                    if idx in st.session_state.pending_approvals:
                        pa = st.session_state.pending_approvals[idx]
                        st.markdown("#### 🗂 Multi-file fix preview")
                        st.caption(f"{len(pa['diffs'])} file(s) will change")

                        for fname, diff_txt in pa["diffs"].items():
                            st.markdown(f"**`{fname}`**")
                            st.code(diff_txt, language="diff")

                        st.markdown('<div class="approve-box">', unsafe_allow_html=True)
                        st.markdown(f"**Apply changes to {len(pa['diffs'])} file(s)?**")
                        ma, mr = st.columns(2)
                        with ma:
                            if st.button("✅ Approve All & Apply", key=f"mf_approve_{idx}"):
                                try:
                                    ap = requests.post(f"{BACKEND}/fix/approve", json={
                                        "repo_path": pa["repo_path"],
                                        "approved_fixes": pa["fixed_files"]
                                    })
                                    if ap.status_code == 200:
                                        applied = ap.json().get("applied", [])
                                        st.success(f"✅ Applied: {', '.join(applied)}")
                                        del st.session_state.pending_approvals[idx]
                                    else:
                                        st.error(ap.json().get("detail", "Apply failed"))
                                except Exception as e:
                                    st.error(str(e))
                        with mr:
                            if st.button("❌ Reject All", key=f"mf_reject_{idx}"):
                                del st.session_state.pending_approvals[idx]
                                st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Streaming Fix
# ══════════════════════════════════════════════════════════════════════════════
with tab_stream:
    st.subheader("⚡ Real-time Streaming Fix Generation")
    st.caption("Watch the fix generate token-by-token. Powered by FastAPI SSE + Groq streaming.")

    s_repo = st.text_input("Repo path (from a previous analysis)", key="stream_repo_path",
                           placeholder="/tmp/repomind_repo_abc123")
    s_file = st.text_input("File to fix", key="stream_file",
                           placeholder="src/agents/bug_detector.py")
    s_bug  = st.text_area("Bug description (paste from analysis)", key="stream_bug",
                           placeholder='{"bug": "...", "impact": "...", "fix_hint": "..."}',
                           height=100)

    if st.button("⚡ Stream Fix", key="stream_btn"):
        if not s_repo or not s_file or not s_bug:
            st.error("Fill in all fields")
        else:
            try:
                bug_dict = json.loads(s_bug)
            except Exception:
                bug_dict = {"bug": s_bug, "impact": "unknown", "fix_hint": ""}

            st.markdown("#### Live output")
            stream_box = st.empty()
            tokens = []

            try:
                with requests.post(
                    f"{BACKEND}/fix/stream",
                    json={"repo_path": s_repo, "file": s_file, "bug": bug_dict},
                    stream=True,
                    timeout=120
                ) as r:
                    for raw_line in r.iter_lines():
                        if not raw_line:
                            continue
                        line = raw_line.decode("utf-8")
                        if not line.startswith("data: "):
                            continue
                        payload = json.loads(line[6:])

                        if payload["type"] == "token":
                            tokens.append(payload["content"])
                            stream_box.markdown(
                                f'<div class="stream-box">{"".join(tokens)}</div>',
                                unsafe_allow_html=True
                            )
                        elif payload["type"] == "done":
                            st.session_state.stream_fix = {
                                "fix": payload["fix"],
                                "diff": payload["diff"],
                                "original": payload["original"],
                                "file": s_file,
                                "repo_path": s_repo
                            }
                        elif payload["type"] == "error":
                            st.error(f"Streaming error: {payload['message']}")

            except Exception as e:
                st.error(f"Stream error: {e}")

    sf = st.session_state.stream_fix
    if sf:
        st.divider()
        st.markdown("#### 🛠 Generated diff")
        st.code(sf.get("diff", ""), language="diff")

        st.markdown('<div class="approve-box">', unsafe_allow_html=True)
        st.markdown("**Apply this fix?**")
        sc1, sc2 = st.columns(2)
        with sc1:
            if st.button("✅ Approve & Apply", key="stream_approve"):
                try:
                    ap = requests.post(f"{BACKEND}/fix/approve", json={
                        "repo_path": sf["repo_path"],
                        "approved_fixes": {sf["file"]: sf["fix"]}
                    })
                    if ap.status_code == 200:
                        st.success(f"✅ Applied to `{sf['file']}`")
                        st.session_state.stream_fix = {}
                    else:
                        st.error(ap.json().get("detail", "Apply failed"))
                except Exception as e:
                    st.error(str(e))
        with sc2:
            if st.button("❌ Discard", key="stream_reject"):
                st.session_state.stream_fix = {}
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Parallel Mode
# ══════════════════════════════════════════════════════════════════════════════
with tab_parallel:
    st.subheader("🚀 Parallel Issue Processing")
    st.caption(
        "All bugs are detected and fixed simultaneously using async parallel processing. "
        "Each fix is previewed before applying — no changes without your approval."
    )

    p_repo = st.text_input("🔗 GitHub URL", key="parallel_repo",
                           placeholder="https://github.com/owner/repo")
    p_concurrency = st.slider("Max concurrent LLM calls", 1, 5, 3,
                              help="Higher = faster but more likely to hit rate limits")

    if st.button("🚀 Analyze + Fix All (Parallel)", key="parallel_btn"):
        if not p_repo.strip():
            st.error("Enter a GitHub URL")
        else:
            with st.spinner("🔄 Cloning, detecting, and fixing all issues in parallel..."):
                try:
                    res = requests.post(
                        f"{BACKEND}/analyze/parallel",
                        json={"repo_url": p_repo, "max_concurrent": p_concurrency},
                        timeout=600
                    )
                    if res.status_code == 200:
                        st.session_state.parallel_results = res.json()
                        st.success("✅ Parallel processing complete!")
                    else:
                        st.error(res.json().get("detail", "Error"))
                except Exception as e:
                    st.error(str(e))

    pr = st.session_state.parallel_results
    if pr:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🐞 Issues found", pr.get("total_issues", 0))
        c2.metric("🔧 Fixes generated", pr.get("issues_with_fixes", 0))
        c3.metric("📁 Files to change", pr.get("total_files_to_change", 0))
        c4.metric("📊 Fix rate",
                  f"{pr.get('issues_with_fixes',0)/max(pr.get('total_issues',1),1)*100:.0f}%")

        st.divider()

        processed = pr.get("processed_issues", [])
        repo_path = pr.get("repo_path", "")

        for idx, p in enumerate(processed):
            file_name = p.get("file", "unknown")
            report = p.get("report", {})
            sev = report.get("severity", "medium")
            diffs = p.get("diffs", {})
            fixed_files = p.get("fixed_files", {})
            success = p.get("success", False)

            status_icon = "✅" if success else "⚠️"
            with st.expander(
                f"{status_icon} `{file_name}` — {sev.upper()} · {len(diffs)} file(s) to change",
                expanded=(sev == "critical")
            ):
                if not success:
                    st.warning(p.get("error", "Fix generation failed"))
                    continue

                st.markdown(
                    f"{sev_badge(sev)} &nbsp; <span style='color:#94a3b8;font-size:.85rem;'>"
                    f"confidence {report.get('confidence',0):.0%} · {report.get('bug_type','other')}</span>",
                    unsafe_allow_html=True
                )
                st.markdown(f"**Bug:** {report.get('bug', '')}")
                st.markdown(f"**Impact:** {report.get('impact', '')}")

                if diffs:
                    for fname, diff_txt in diffs.items():
                        st.markdown(f"**`{fname}`**")
                        st.code(diff_txt, language="diff")

                    st.markdown('<div class="approve-box">', unsafe_allow_html=True)
                    st.markdown(f"**Apply {len(diffs)} file change(s)?**")
                    pa_col, pr_col = st.columns(2)
                    with pa_col:
                        if st.button("✅ Approve & Apply", key=f"p_approve_{idx}"):
                            try:
                                ap = requests.post(f"{BACKEND}/fix/approve", json={
                                    "repo_path": repo_path,
                                    "approved_fixes": fixed_files
                                })
                                if ap.status_code == 200:
                                    applied = ap.json().get("applied", [])
                                    st.success(f"Applied: {', '.join(applied)}")
                                else:
                                    st.error(ap.json().get("detail", "Apply failed"))
                            except Exception as e:
                                st.error(str(e))
                    with pr_col:
                        if st.button("❌ Skip", key=f"p_reject_{idx}"):
                            st.info("Skipped.")
                    st.markdown("</div>", unsafe_allow_html=True)
                else:
                    st.info("No diff generated — file may already be correct.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Observability
# ══════════════════════════════════════════════════════════════════════════════
with tab_metrics:
    st.subheader("📊 Live Pipeline Observability")
    st.caption("Data from `GET /metrics` — updates after each run")

    if st.button("🔄 Refresh", key="metrics_refresh"):
        st.rerun()

    try:
        mr = requests.get(f"{BACKEND}/metrics", timeout=5)
        if mr.status_code == 200:
            m = mr.json()
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("🏃 Runs", m.get("total_runs", 0))
            c2.metric("🐞 Bugs detected", m.get("total_bugs_detected", 0))
            c3.metric("✅ Fixes applied", m.get("total_fixes_succeeded", 0))
            c4.metric("📈 Success rate", f"{m.get('fix_success_rate_pct', 0):.1f}%")

            st.divider()
            ca, cb = st.columns(2)
            with ca:
                st.markdown("#### Severity breakdown")
                for k, v in m.get("severity_distribution", {}).items():
                    st.markdown(f"{sev_badge(k)} &nbsp; **{v}** bugs", unsafe_allow_html=True)

                st.markdown("#### Retry distribution")
                for k, v in sorted(m.get("retry_distribution", {}).items()):
                    st.markdown(f"- `{k} retries`: **{v}** fixes")

            with cb:
                st.markdown("#### Avg stage latency")
                for stage, ms in m.get("avg_stage_latency_ms", {}).items():
                    if ms is not None:
                        st.markdown(f"- `{stage}`: **{ms:.0f}ms**")

                st.markdown("#### Success by severity")
                for sk, counts in m.get("fix_success_by_severity", {}).items():
                    total = counts["success"] + counts["fail"]
                    rate = round(counts["success"] / total * 100) if total > 0 else 0
                    st.markdown(
                        f"{sev_badge(sk)} &nbsp; {rate}% ({counts['success']}/{total})",
                        unsafe_allow_html=True
                    )

            st.divider()
            st.markdown("#### Recent runs")
            for run in reversed(m.get("recent_runs", [])[-10:]):
                icon = "✅" if run.get("success") else "❌"
                st.markdown(
                    f"{icon} **{run.get('repo','?')}** — "
                    f"bugs: {run.get('bugs_detected',0)}, "
                    f"fixes: {run.get('fixes_applied',0)}, "
                    f"{run.get('duration_ms',0)/1000:.1f}s"
                )

            with st.expander("Raw JSON"):
                st.json(m)
        else:
            st.error(f"HTTP {mr.status_code}")
    except Exception as e:
        st.warning(f"Backend unreachable: {e}")

# ─── Footer ─────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("FastAPI · LangGraph · MCP · ChromaDB · Groq · Streamlit")
