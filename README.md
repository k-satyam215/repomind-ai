# 🤖 RepoMind AI — Autonomous Repository Debugging Agent

![RepoMind Demo](assets/demo.png)

RepoMind AI is an autonomous software engineering agent designed to analyze real-world GitHub repositories, detect runtime issues, generate minimal fixes, apply patches, and validate solutions through iterative reasoning.

This system simulates real debugging workflows followed by software engineers and demonstrates applied **Agentic AI system design** using structured reasoning, tool execution, and reflection loops.

---

## 🚀 Key Capabilities

* 🔍 Automated repository architecture understanding
* 🐞 AI-driven runtime bug detection
* 🛠 Minimal and targeted fix generation
* 📊 Unified diff preview for transparency
* 🔁 Reflection-based retry loop (agentic behavior)
* 🧠 Lightweight memory for past successful fixes
* 🧪 Automated test execution for fix validation
* ⚡ FastAPI backend for orchestration
* 🎯 Streamlit UI for interactive debugging
* 🐳 Fully Dockerized deployment

---

## 🧠 Problem Statement

Understanding unfamiliar codebases and debugging runtime failures is time-consuming and cognitively demanding.

RepoMind AI assists developers by:

1. Interpreting repository architecture
2. Identifying realistic runtime issues
3. Generating actionable minimal fixes
4. Iteratively improving solutions using reflection

---

## 🧩 System Architecture

```
User
  ↓
Streamlit UI (Interaction Layer)
  ↓
FastAPI Backend (Orchestration Layer)
  ↓
LangGraph Agent Controller
  ↓
LLM Reasoning Engine

Execution Pipeline:
  → Repository Analysis
  → Runtime Issue Detection
  → Fix Generation
  → Patch Application
  → Test Execution
  → Reflection Loop
  → Retry / Convergence
```

---

## 🤖 Agent Workflow

1. Clone target repository
2. Parse project structure and dependencies
3. Analyze architecture using LLM reasoning
4. Detect realistic runtime issues
5. Generate minimal fix patches
6. Apply fixes to codebase
7. Execute test suite for validation
8. Reflect on failure/success
9. Retry until convergence
10. Store successful fixes in memory

---

## 📊 Evaluation (Prototype Stage)

Tested on:

* Sample Flask applications
* FastAPI template repositories
* Small open-source Python utilities

Observed behavior:

* Bug detection success: ~70%
* Fix validation success: ~60%
* Retry convergence: ~2 iterations average

⚠️ These metrics are early experimental observations.

---

## ⚠️ Current Limitations

* Limited support for large monolithic repositories
* Context window constraints for deep dependency graphs
* Heuristic bug hypothesis generation
* No long-term persistent memory yet
* Python-focused (multi-language support planned)

---

## 🔮 Future Work

* Hierarchical planning agents
* Multi-repository reasoning
* Static + dynamic hybrid analysis
* Vector database based long-term memory
* Autonomous pull-request generation
* Distributed agent orchestration

---

## 🛠 Tech Stack

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

Create a `.env` file:

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

## 🐳 Run with Docker

```bash
docker build -t repomind-ai .
docker run -p 8000:8000 -p 8501:8501 --env-file .env repomind-ai
```

---

## ⭐ Contribution

Contributions, ideas, and research discussions are welcome.

---

## 📜 License

This project is open-source and intended for research and educational purposes.
