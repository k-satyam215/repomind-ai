# 🤖 RepoMind AI — Autonomous Repository Debugging Agent

![RepoMind Demo](assets/demo.png)

RepoMind AI is an experimental autonomous software engineering agent designed to understand unfamiliar codebases, detect realistic runtime issues, generate minimal corrective patches, and validate fixes through iterative reasoning workflows.

The system demonstrates applied **Agentic AI architecture** by combining structured reasoning, tool-driven execution, reflection loops, and automated validation pipelines inspired by real software engineering debugging practices.

---

## 🚀 Key Capabilities

* 🔍 Automated repository architecture interpretation
* 🐞 Heuristic + LLM-assisted runtime issue detection
* 🛠 Minimal, targeted fix generation
* 📊 Unified diff-level patch transparency
* 🔁 Reflection-based retry loops (agent convergence behavior)
* 🧠 Lightweight short-term fix memory
* 🧪 Automated test execution for validation
* ⚡ FastAPI orchestration layer
* 🎯 Streamlit interactive debugging interface
* 🐳 Fully containerized deployment

---

## 🧠 Motivation

Understanding unfamiliar repositories and diagnosing runtime failures introduces significant cognitive overhead for developers.

RepoMind AI explores how autonomous reasoning systems can assist engineers by:

* Structurally interpreting unknown codebases
* Hypothesizing realistic runtime failures
* Generating minimal actionable patches
* Iteratively improving solutions through feedback loops

---

## 🧩 System Architecture

```
User
  ↓
Streamlit Interface (Interaction Layer)
  ↓
FastAPI Backend (Execution Orchestrator)
  ↓
LangGraph Agent Controller
  ↓
LLM Reasoning Engine

Execution Pipeline:
  → Repository Structure Analysis
  → Runtime Issue Hypothesis
  → Fix Patch Generation
  → Patch Application
  → Test Execution
  → Reflection & Retry
```

---

## 🤖 Agent Workflow

1. Clone target repository
2. Parse file structure and dependencies
3. Perform architecture reasoning using LLM
4. Detect potential runtime issues
5. Generate minimal corrective patch
6. Apply patch to repository
7. Execute automated tests
8. Reflect on results
9. Retry until convergence
10. Store successful fix context in memory

---

## 📊 Prototype Evaluation

RepoMind AI has been qualitatively evaluated on small-to-medium Python repositories, including:

* Flask sample applications
* FastAPI template projects
* Lightweight open-source Python utilities

Observed experimental behavior:

* Successful issue hypothesis in multiple scenarios
* Partial automated fix validation through test execution
* Typical convergence within a few retry iterations

⚠️ These observations represent early prototype experimentation rather than controlled benchmark results.

---

## ⚠️ Current Limitations

* Limited scalability for large monolithic codebases
* Context window constraints in deeply nested dependency graphs
* Heuristic bug hypothesis formulation
* No persistent long-term memory across sessions
* Currently optimized for Python repositories

---

## 🔮 Future Directions

* Hierarchical planning-based agent orchestration
* Multi-repository reasoning capabilities
* Hybrid static + dynamic analysis integration
* Vector database-backed long-term memory
* Autonomous pull-request generation pipelines
* Distributed agent execution architecture

---

## 🛠 Technology Stack

* Python
* FastAPI
* Streamlit
* LangGraph
* LangChain
* Groq LLM API
* GitPython
* PyTest
* Docker

---

## 📂 Project Structure

```
repomind-ai/
│
├── backend/
│   └── main.py
│
├── frontend/
│   └── app.py
│
├── src/
│   ├── agents/
│   │   ├── repo_analyzer.py
│   │   ├── bug_detector.py
│   │   ├── fix_generator.py
│   │   ├── patch_apply_agent.py
│   │   ├── reflection_agent.py
│   │   └── test_runner_agent.py
│   │
│   ├── api/
│   │   └── routes.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   └── logger.py
│   │
│   ├── graph/
│   │   └── agent_graph.py
│   │
│   ├── memory/
│   │   └── simple_memory.py
│   │
│   ├── tools/
│   │   ├── diff_tools.py
│   │   └── file_tools.py
│   │
│   └── utils/
│       ├── repo_parser.py
│       └── repo_filter.py
│
├── assets/
│   └── demo.png
│
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🚀 Installation

```bash
git clone https://github.com/k-satyam215/repomind-ai.git
cd repomind-ai
pip install -r requirements.txt
```

Create `.env` file:

```bash
GROQ_API_KEY=your_api_key_here
```

---

## ▶️ Run Locally

Backend:

```bash
uvicorn backend.main:app --reload
```

Frontend:

```bash
streamlit run frontend/app.py
```

---

## 🐳 Docker Deployment

```bash
docker build -t repomind-ai .
docker run -p 8000:8000 -p 8501:8501 --env-file .env repomind-ai
```

---

## ⭐ Contribution

Research discussions, feedback, and experimental improvements are welcome.

---

## 📜 License

Open-source research prototype intended for educational and experimental use.
