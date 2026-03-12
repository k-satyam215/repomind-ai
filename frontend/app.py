import streamlit as st
import requests

BACKEND = "http://localhost:8000"

st.set_page_config(page_title="RepoMind AI", layout="wide")

st.title("🚀 RepoMind AI")

repo = st.text_input("Enter GitHub Repo URL")

# SESSION STATE INIT
if "analysis_data" not in st.session_state:
    st.session_state.analysis_data = None

if "fix_diff" not in st.session_state:
    st.session_state.fix_diff = None

# ANALYZE BUTTON
if st.button("Analyze"):

    with st.spinner("Analyzing repository..."):

        res = requests.post(
            f"{BACKEND}/analyze",
            json={"repo_url": repo}
        )

        data = res.json()

        if "error" in data:
            st.error(data["error"])
        else:
            st.session_state.analysis_data = data

# DISPLAY ANALYSIS
data = st.session_state.analysis_data

if data:

    st.subheader("📊 Architecture Summary")
    st.write(data["analysis"])

    st.subheader("🐞 Issues")

    for idx, issue in enumerate(data["issues"]):

        st.markdown(f"### 📄 {issue['file']}")
        st.json(issue["report"])

        if st.button("Generate Fix", key=f"fix_{idx}"):

            with st.spinner("Generating fix..."):

                fix = requests.post(
                    f"{BACKEND}/fix",
                    json={
                        "repo_path": data["repo_path"],
                        "file": issue["file"],
                        "bug": issue["report"]
                    }
                ).json()

                diff = requests.post(
                    f"{BACKEND}/diff",
                    json={
                        "old": fix["old"],
                        "new": fix["new"]
                    }
                ).json()

                st.session_state.fix_diff = diff["diff"]

# SHOW DIFF
if st.session_state.fix_diff:

    st.subheader("🛠 Fix Diff")
    st.code(st.session_state.fix_diff, language="diff")