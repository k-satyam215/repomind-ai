# 🤖 RepoMind AI — Autonomous Code Review Agent

![RepoMind Demo](assets/demo.png)

RepoMind AI is an LLM-powered autonomous software engineering agent that analyzes real-world GitHub repositories, detects runtime issues, generates fixes, applies patches, and validates solutions through iterative reasoning.

This project simulates real debugging workflows followed by software engineers and demonstrates applied Agentic AI system design.

---

## 🚀 Features

- 🔍 Automated repository architecture analysis  
- 🐞 AI-driven runtime bug detection  
- 🛠 Minimal-change fix generation  
- 📊 Unified diff preview of suggested fixes  
- 🔁 Reflection-based retry loop (Agentic behavior)  
- 🧠 Lightweight memory for past fixes  
- 🧪 Automated test execution for validation  
- ⚡ FastAPI backend for AI orchestration  
- 🎯 Streamlit UI for interactive debugging  
- 🐳 Dockerized deployment support  

---

## 🧠 Problem Statement

Understanding unfamiliar codebases and debugging runtime failures is time-consuming and error-prone.

RepoMind AI assists developers by:

1. Interpreting repository architecture  
2. Identifying real runtime issues  
3. Generating actionable fixes  
4. Iteratively improving solutions  

---

## 🧩 System Architecture

User → Streamlit UI → FastAPI → Agent Graph → LLM
↓
Analyze → Detect → Fix → Apply → Test
↓
Reflect → Retry → Learn

---

## 🤖 Agent Workflow

1. Clone repository  
2. Parse project structure  
3. Analyze architecture using LLM  
4. Detect realistic runtime issues  
5. Generate minimal fix patches  
6. Apply fix to repository  
7. Execute tests for validation  
8. Reflect and retry if needed  
9. Store successful fixes in memory  

---

## 🛠 Tech Stack

- Python  
- FastAPI  
- Streamlit  
- LangGraph  
- LangChain  
- Groq LLM API  
- GitPython  
- PyTest  
- Docker  

---

## 📂 Project Structure

repomind-ai/
│
├── backend/
│ └── main.py
│
├── frontend/
│ └── app.py
│
├── src/
│ ├── agents/
│ │ ├── repo_analyzer.py
│ │ ├── bug_detector.py
│ │ ├── fix_generator.py
│ │ ├── patch_apply_agent.py
│ │ ├── reflection_agent.py
│ │ └── test_runner_agent.py
│ │
│ ├── api/
│ │ └── routes.py
│ │
│ ├── core/
│ │ ├── config.py
│ │ └── logger.py
│ │
│ ├── graph/
│ │ └── agent_graph.py
│ │
│ ├── memory/
│ │ └── simple_memory.py
│ │
│ ├── tools/
│ │ ├── diff_tools.py
│ │ └── file_tools.py
│ │
│ └── utils/
│ ├── repo_parser.py
│ └── repo_filter.py
│
├── assets/
│ └── demo.png
│
├── Dockerfile
├── requirements.txt
├── .env
└── README.md

---

## 🚀 Installation

```bash
git clone https://github.com/your-username/repomind-ai.git
cd repomind-ai
pip install -r requirements.txt
```

Create a `.env` file with the following content:

```bash
GROQ_API_KEY=your_api_key_here
```

### ▶️ Run locally

**Backend:**

```bash
uvicorn backend.main:app --reload
```

**Frontend:**

```bash
streamlit run frontend/app.py
```

### 🐳 Run with Docker

```bash
docker build -t repomind-ai .
docker run -p 8000:8000 -p 8501:8501 --env-file .env repomind-ai
```

