import os
import time

import requests
import streamlit as st

BACKEND = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="RepoMind AI", page_icon="🤖", layout="wide")

# 🎨 PREMIUM CSS
st.markdown("""
<style>
.stApp {
    background: radial-gradient(circle at top, #0f172a, #020617);
    color: #e2e8f0;
}

h1 {
    font-size: 2.8rem !important;
    font-weight: 700;
    background: linear-gradient(90deg, #818cf8, #c084fc);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

input {
    border-radius: 12px !important;
    border: 1px solid #334155 !important;
    background-color: #020617 !important;
    color: white !important;
}

.stButton>button {
    border-radius: 12px;
    height: 45px;
    font-weight: 600;
    background: linear-gradient(135deg, #6366f1, #a855f7);
    color: white;
    border: none;
    transition: 0.3s;
}

.stButton>button:hover {
    transform: scale(1.04);
    background: linear-gradient(135deg, #4f46e5, #9333ea);
}

[data-testid="stMetric"] {
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid #334155;
    padding: 20px;
    border-radius: 14px;
    backdrop-filter: blur(10px);
}

div.stContainer {
    background: rgba(2, 6, 23, 0.7);
    border-left: 4px solid #6366f1;
    border-radius: 12px;
    padding: 18px;
    margin-bottom: 15px;
}

hr {
    border: 1px solid #1e293b;
}
</style>
""", unsafe_allow_html=True)

# ─── HEADER ─────────────────────
st.markdown("# 🤖 RepoMind AI")
st.caption("⚡ Autonomous Code Debugging System")
st.divider()

# ─── STATE ─────────────────────
if "analysis_data" not in st.session_state:
    st.session_state.analysis_data = None

if "fix_results" not in st.session_state:
    st.session_state.fix_results = {}

# ─── INPUT ─────────────────────
repo = st.text_input("🔗 GitHub Repository URL")

col1, col2 = st.columns([1, 5])
with col1:
    analyze_clicked = st.button("🚀 Analyze", use_container_width=True)
with col2:
    if st.button("🔄 Reset", use_container_width=True):
        st.session_state.analysis_data = None
        st.session_state.fix_results = {}
        st.rerun()

# ─── ANALYSIS ─────────────────────
if analyze_clicked:
    if not repo.strip():
        st.error("Enter a valid GitHub URL")
    else:
        progress = st.progress(0)

        try:
            st.info("🧠 Starting analysis...")
            progress.progress(20)
            time.sleep(0.3)

            st.info("🔍 Cloning repository...")
            progress.progress(40)

            res = requests.post(
                f"{BACKEND}/analyze",
                json={"repo_url": repo},
                timeout=300
            )

            st.info("🐞 Detecting bugs...")
            progress.progress(70)
            time.sleep(0.3)

            data = res.json()
            progress.progress(100)

            if res.status_code != 200:
                st.error(data.get("detail", "Error"))
            else:
                st.session_state.analysis_data = data
                st.success("✅ Analysis Complete!")

        except Exception as e:
            st.error(str(e))

# ─── RESULTS ─────────────────────
data = st.session_state.analysis_data

if data:
    col1, col2, col3 = st.columns(3)
    col1.metric("📁 Files", len(data.get("issues", [])))
    col2.metric("🐞 Issues", len(data.get("issues", [])))
    col3.metric("✅ Status", "Success")

    st.divider()

    # Architecture
    st.subheader("📊 Architecture Summary")
    with st.container():
        st.markdown(data.get("analysis", "No analysis"))

    st.divider()

    issues = data.get("issues", [])

    if not issues:
        st.success("✅ No issues found!")
    else:
        st.subheader(f"🐞 Issues — {len(issues)}")

        for idx, issue in enumerate(issues):
            with st.container():
                st.markdown(f"### 📄 `{issue['file']}`")

                report = issue["report"]

                st.markdown(f"""
                🔴 **Bug:** {report.get("bug")}
                🟡 **Impact:** {report.get("impact")}
                🟢 **Fix:** {report.get("fix_hint")}
                """)

                # FIX BUTTON
                if st.button("⚡ Generate Fix", key=f"fix_{idx}"):

                    with st.spinner("🤖 Generating fix..."):

                        try:
                            fix_res = requests.post(
                                f"{BACKEND}/fix",
                                json={
                                    "repo_path": data["repo_path"],
                                    "file": issue["file"],
                                    "bug": report
                                }
                            )

                            fix_data = fix_res.json()

                            diff_res = requests.post(
                                f"{BACKEND}/diff",
                                json={
                                    "old": fix_data["old"],
                                    "new": fix_data["new"],
                                    "filename": issue["file"]
                                }
                            )

                            diff_data = diff_res.json()

                            st.session_state.fix_results[idx] = {
                                "diff": diff_data.get("diff", ""),
                                "new": fix_data["new"]
                            }

                        except Exception as e:
                            st.error(str(e))

                # SHOW RESULT
                if idx in st.session_state.fix_results:
                    result = st.session_state.fix_results[idx]

                    st.markdown("#### 🛠 Diff")
                    st.code(result["diff"], language="diff")

                    with st.expander("📂 Full Fixed File"):
                        st.code(result["new"], language="python")

                st.divider()

# ─── FOOTER ─────────────────────
st.markdown("---")
st.caption("Built with ❤️ using FastAPI + LangGraph + MCP")
