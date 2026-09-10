import json
import os

import requests
import streamlit as st

BACKEND = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="RepoMind AI", page_icon="🤖", layout="wide")

st.markdown("""
<style>
.stApp { background: #050609; color: #e6edf7; }
.stApp::before { content:""; position:fixed; inset:0; z-index:-1; pointer-events:none;
    background: radial-gradient(ellipse 46% 58% at -8% 28%, rgba(102,25,168,.20), transparent 72%),
                radial-gradient(ellipse 48% 58% at 105% 70%, rgba(10,91,191,.17), transparent 72%); }
header[data-testid="stHeader"] { background: rgba(5,6,9,.78); backdrop-filter: blur(18px);
    border-bottom: 1px solid rgba(148,163,184,.09); }
.block-container { max-width: 1180px; padding: 2.2rem 2rem 4.5rem; }
h1 { margin: 0 !important; font-size: clamp(2.5rem, 5vw, 4.6rem) !important; line-height: 1.02 !important;
     font-weight: 760 !important; letter-spacing: -.06em; color: #f8fafc !important; }
h1 em { color:#38bdf8; font-style:normal; }
input, textarea { border-radius: 12px !important; border: 1px solid #263244 !important;
        background-color: #0c111b !important; color: #f8fafc !important; }
input:focus, textarea:focus { border-color: #38bdf8 !important;
    box-shadow: 0 0 0 3px rgba(56,189,248,.13) !important; }
label, [data-testid="stWidgetLabel"] p { color: #dbe7f5 !important;
    font-weight: 600 !important; }
.stButton>button { border-radius: 10px; min-height: 44px; font-weight: 700; letter-spacing: .01em;
    background: #1687e8; color: #f8fbff; border: 1px solid #249bf7; transition: .18s ease;
    box-shadow: 0 7px 18px rgba(14,165,233,.16); }
.stButton>button:hover { transform: translateY(-1px); background: #2599f4; border-color: #5cc7ff; }
.st-key-reset_btn button, .st-key-parallel_reset_btn button {
    background: transparent !important; color: #9fb1c8 !important;
    border-color: #2a3649 !important; box-shadow: none !important; }
.st-key-reset_btn button:hover, .st-key-parallel_reset_btn button:hover {
    color:#e6edf7 !important; background:#131b28 !important; }
[data-testid="stMetric"] { background: linear-gradient(145deg, rgba(19,27,40,.85), rgba(12,17,27,.9));
    border: 1px solid #273449; padding: 18px; border-radius: 12px; }
.sev-critical { background: rgba(239,68,68,.15); border:1px solid #ef4444; border-radius:8px;
    padding:3px 10px; color:#ef4444; font-weight:700; font-size:.75rem; display:inline-block; }
.sev-high { background: rgba(249,115,22,.15); border:1px solid #f97316; border-radius:8px;
    padding:3px 10px; color:#f97316; font-weight:700; font-size:.75rem; display:inline-block; }
.sev-medium { background: rgba(234,179,8,.15); border:1px solid #eab308; border-radius:8px;
    padding:3px 10px; color:#eab308; font-weight:700; font-size:.75rem; display:inline-block; }
.approve-box { border:1px solid rgba(52,211,153,.55); border-radius:12px; padding:16px;
    background:rgba(16,185,129,.08); margin:8px 0; }
.stream-box { background:#0c111b; border:1px solid #273449; border-radius:12px;
    padding:16px; font-family:monospace; font-size:.82rem; line-height:1.6;
    max-height:400px; overflow-y:auto; color:#a5f3fc; }
hr { border: 0; border-top: 1px solid #202c3e; }
.hero { position:relative; overflow:hidden; text-align:center; padding: 34px 38px 30px;
  border: 1px solid rgba(91,105,148,.24); border-radius: 24px;
  background: linear-gradient(135deg, rgba(19,10,40,.54), rgba(5,8,15,.4) 42%, rgba(7,23,49,.58));
  box-shadow: 0 28px 80px rgba(0,0,0,.32); margin: 0 0 28px; }
.hero::before { content:""; position:absolute; width:460px; height:300px; left:-190px; top:-110px;
  background:radial-gradient(circle, rgba(139,92,246,.22), transparent 67%); pointer-events:none; }
.hero::after { content:""; position:absolute; width:460px; height:300px; right:-190px; bottom:-150px;
  background:radial-gradient(circle, rgba(34,211,238,.18), transparent 67%); pointer-events:none; }
.brain-mark { position:relative; z-index:1; width:88px; height:88px; margin:0 auto 18px; padding:10px;
  border:1px solid rgba(103,232,249,.75); border-radius:50%; background:rgba(6,11,22,.86);
  box-shadow:0 0 0 5px rgba(139,92,246,.12), 0 0 42px rgba(34,211,238,.18); }
.brain-mark svg { width:100%; height:100%; filter:drop-shadow(0 0 8px rgba(129,140,248,.6)); }
.hero-kicker { position:relative; z-index:1; color:#a5b4fc; font-size:.72rem; font-weight:800;
  letter-spacing:.22em; text-transform:uppercase; }
.hero-kicker b { color:#60a5fa; font-weight:800; }
.hero-copy { position:relative; z-index:1; color:#cbd5e1; max-width:720px; font-size:1.08rem;
  line-height:1.6; margin:18px auto 0; }
.hero h1 { position:relative; z-index:1; }
.trust-chip { display:inline-block; color:#b6f5d8; border:1px solid rgba(52,211,153,.38); border-radius:999px;
  background:rgba(16,185,129,.08); padding:5px 11px; font-size:.76rem; margin:20px 6px 0 0; }
[data-testid="stTabs"] { margin-bottom: 14px; }
[data-testid="stTabs"] button { color:#93a5bd; font-weight:700; border-radius: 8px 8px 0 0; padding: 0 2px; }
[data-testid="stTabs"] button[aria-selected="true"] { color: #7dd3fc; border-bottom-color: #38bdf8; }
[data-testid="stExpander"] { border-color:#273449 !important; border-radius:12px !important;
  background:#0c111b !important; }
.section-note { color:#8fa3bc; font-size:.94rem; margin:0 0 1.2rem; }
@media (max-width: 700px) { .block-container { padding:1rem 1rem 3rem; }
  .hero { padding:30px 20px 26px; } .brain-mark { width:76px; height:76px; } }
</style>
""", unsafe_allow_html=True)


def sev_badge(sev: str) -> str:
    s = (sev or "medium").lower()
    return f'<span class="sev-{s}">{s.upper()}</span>'


# ─── Header ─────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <div class="brain-mark" aria-hidden="true">
    <svg viewBox="0 0 96 96" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="brain-gradient" x1="12" y1="18" x2="85" y2="80">
          <stop stop-color="#A78BFA"/><stop offset="1" stop-color="#22D3EE"/>
        </linearGradient>
      </defs>
      <path d="M47 18C38 12 26 16 24 27C15 28 11 39 17 47C11 56 16 68 27 69C30 79 40 83 48 77"
        stroke="url(#brain-gradient)" stroke-width="4" stroke-linecap="round"/>
      <path d="M49 18C58 12 70 16 72 27C81 28 85 39 79 47C85 56 80 68 69 69C66 79 56 83 48 77"
        stroke="url(#brain-gradient)" stroke-width="4" stroke-linecap="round"/>
      <path d="M48 21V74M25 36C33 35 35 42 42 41M72 36C64 35 62 42 55 41"
        stroke="url(#brain-gradient)" stroke-width="3" stroke-linecap="round"/>
      <path d="M24 57C33 56 35 64 43 61M72 57C63 56 61 64 53 61"
        stroke="url(#brain-gradient)" stroke-width="3" stroke-linecap="round"/>
      <circle cx="34" cy="31" r="3" fill="#C4B5FD"/><circle cx="62" cy="31" r="3" fill="#67E8F9"/>
      <circle cx="37" cy="54" r="3" fill="#C4B5FD"/><circle cx="59" cy="54" r="3" fill="#67E8F9"/>
    </svg>
  </div>
  <div class="hero-kicker">R E P O M I N D &nbsp; <b>● v1.6</b></div>
  <h1>GitHub repository analysis,<br><em>code review &amp; safe fixes.</em></h1>
  <p class="hero-copy">Understand repositories faster with context-aware AI. From a URL to
  architecture, security findings, and review-ready, sandbox-tested patches.</p>
  <span class="trust-chip">● Sandbox-tested</span>
  <span class="trust-chip">● Secret-safe execution</span>
  <span class="trust-chip">● Approval required</span>
</div>
""", unsafe_allow_html=True)

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
    st.markdown(
        '<p class="section-note">Start with a public repository, or use a fine-grained '
        'read-only token for a private one.</p>',
        unsafe_allow_html=True,
    )
    repo = st.text_input("🔗 GitHub Repository URL", key="repo_url_standard",
                         placeholder="https://github.com/owner/repo")
    github_token = st.text_input(
        "GitHub personal access token (optional)", type="password", key="github_token_standard",
        placeholder="github_pat_...",
        help=(
            "Only used for this analysis to clone a private repository. It is never "
            "displayed, logged, returned, or placed in the shared cache."
        )
    )
    col1, col2, _ = st.columns([1.2, 1.2, 4])
    with col1:
        go = st.button("🚀 Analyze", use_container_width=True, key="analyze_btn")
    with col2:
        if st.button("🔄 Reset", use_container_width=True, key="reset_btn"):
            st.session_state.analysis_data = None
            st.session_state.fix_results = {}
            st.session_state.pending_approvals = {}
            st.session_state.github_token_standard = ""
            st.rerun()

    if go:
        if not repo.strip():
            st.error("Enter a valid GitHub URL")
        else:
            progress_box = st.empty()
            status_box = st.empty()
            bar = st.progress(0)

            stage_progress = {
                "start":      (5,  "🔗 Connecting..."),
                "cache":      (100, "⚡ Cache hit — instant result!"),
                "clone":      (15, "📥 Cloning repository..."),
                "parse":      (30, "🔍 Parsing file structure..."),
                "deps":       (45, "🕸️  Building dependency graph..."),
                "analyze":    (60, "🧠 Analyzing architecture..."),
                "prioritize": (72, "📊 Prioritizing files..."),
                "detect":     (85, "🐛 Detecting bugs in each file..."),
                "complete":   (100, "✅ Analysis complete!"),
                "error":      (0,  "❌ Error occurred"),
            }

            try:
                with requests.post(
                    f"{BACKEND}/analyze/stream",
                    json={"repo_url": repo, "github_token": github_token or None},
                    stream=True,
                    timeout=600
                ) as r:
                    for raw_line in r.iter_lines():
                        if not raw_line:
                            continue
                        line = raw_line.decode("utf-8")
                        if not line.startswith("data: "):
                            continue

                        payload = json.loads(line[6:])
                        stage = payload.get("stage", "")
                        message = payload.get("message", "")

                        pct, label = stage_progress.get(stage, (bar, message))
                        bar.progress(int(pct))
                        progress_box.markdown(
                            f"""
<div style='padding:12px 16px;border-radius:10px;
border:1px solid #334155;background:rgba(15,23,42,.8);
font-size:.9rem;color:#e2e8f0;'>
{message}
</div>""",
                            unsafe_allow_html=True
                        )

                        if stage == "complete":
                            result = payload.get("result", {})
                            if result:
                                st.session_state.analysis_data = result
                                cache_hit = result.get("cache_hit", False)
                                if cache_hit:
                                    status_box.success(
                                        "⚡ Served from Redis cache — instant result!"
                                    )
                                else:
                                    status_box.success("✅ Analysis complete!")
                            break

                        elif stage == "error":
                            status_box.error(message)
                            break

            except requests.exceptions.Timeout:
                st.error(
                    "⏱ Request timed out. The repo may be too large or the "
                    "backend is slow to start. Try again or use a smaller repo."
                )
            except requests.exceptions.ConnectionError:
                st.error("🔌 Cannot connect to backend. Make sure FastAPI is running at: " + BACKEND)
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
    p_github_token = st.text_input(
        "GitHub personal access token (optional)", type="password", key="github_token_parallel",
        placeholder="github_pat_...",
        help=(
            "Use a fine-grained, read-only token for private repositories. "
            "Token-authorised runs bypass the shared cache."
        )
    )
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
                        json={"repo_url": p_repo, "max_concurrent": p_concurrency,
                              "github_token": p_github_token or None},
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

            # ── Integrations status ─────────────────────────────────
            integrations = m.get("integrations", {})
            if integrations:
                st.divider()
                st.markdown("#### 🔌 Integrations")
                ic1, ic2 = st.columns(2)

                redis_info = integrations.get("redis", {})
                with ic1:
                    redis_ok = redis_info.get("connected", False)
                    redis_enabled = redis_info.get("enabled", False)
                    if not redis_enabled:
                        st.markdown("""
<div style='padding:14px;border-radius:12px;
border:1px solid #334155;background:rgba(15,23,42,.6)'>
<b>🟡 Redis</b><br>
<span style='color:#94a3b8;font-size:.85rem'>Not configured —
set <code>REDIS_URL</code> in .env to enable caching</span></div>""",
                        unsafe_allow_html=True)
                    elif redis_ok:
                        st.markdown("""
<div style='padding:14px;border-radius:12px;
border:1px solid #22c55e;background:rgba(34,197,94,.07)'>
<b>🟢 Redis</b><br>
<span style='color:#4ade80;font-size:.85rem'>✔ Connected —
Analysis results cached, memory persisted</span></div>""",
                        unsafe_allow_html=True)
                    else:
                        st.markdown("""
<div style='padding:14px;border-radius:12px;
border:1px solid #ef4444;background:rgba(239,68,68,.07)'>
<b>🔴 Redis</b><br>
<span style='color:#f87171;font-size:.85rem'>✘ Configured but unreachable —
check REDIS_URL</span></div>""",
                        unsafe_allow_html=True)

                langsmith_info = integrations.get("langsmith", {})
                with ic2:
                    ls_enabled = langsmith_info.get("enabled", False)
                    ls_url = langsmith_info.get("url")
                    ls_project = langsmith_info.get("project")
                    if not ls_enabled:
                        st.markdown("""
<div style='padding:14px;border-radius:12px;
border:1px solid #334155;background:rgba(15,23,42,.6)'>
<b>🟡 LangSmith</b><br>
<span style='color:#94a3b8;font-size:.85rem'>Not configured —
set <code>LANGSMITH_API_KEY</code> to enable LLM tracing</span></div>""",
                        unsafe_allow_html=True)
                    else:
                        link = (
                            f"<a href='{ls_url}' target='_blank' "
                            f"style='color:#818cf8'>View traces →</a>"
                            if ls_url else ""
                        )
                        st.markdown(f"""
<div style='padding:14px;border-radius:12px;
border:1px solid #818cf8;background:rgba(129,140,248,.07)'>
<b>🟣 LangSmith</b><br>
<span style='color:#a5b4fc;font-size:.85rem'>✔ Tracing enabled —
Project: <b>{ls_project}</b><br>{link}</span></div>""",
                        unsafe_allow_html=True)

            with st.expander("Raw JSON"):
                st.json(m)
        else:
            st.error(f"HTTP {mr.status_code}")
    except Exception as e:
        st.warning(f"Backend unreachable: {e}")

# ─── Footer ─────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("FastAPI · LangGraph · MCP · ChromaDB · Groq · LangSmith · Redis · Streamlit")
