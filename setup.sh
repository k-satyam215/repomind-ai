#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# RepoMind AI — Setup Script
# Usage: bash setup.sh
# ─────────────────────────────────────────────────────────────────────────────

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo "🤖 RepoMind AI — Setup"
echo "────────────────────────────────────────"

# ── 1. Python version check ───────────────────────────────────────────────────
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
REQUIRED="3.11"

if python3 -c "import sys; exit(0 if sys.version_info >= (3,11) else 1)" 2>/dev/null; then
    echo -e "${GREEN}✓ Python ${PYTHON_VERSION} detected${NC}"
else
    echo -e "${RED}✗ Python 3.11+ required. Found: ${PYTHON_VERSION}${NC}"
    exit 1
fi

# ── 2. Virtual environment ────────────────────────────────────────────────────
if [ ! -d ".venv" ]; then
    echo "→ Creating virtual environment..."
    python3 -m venv .venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment already exists${NC}"
fi

# Activate
source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate 2>/dev/null

# ── 3. Install dependencies ───────────────────────────────────────────────────
echo "→ Installing dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo -e "${GREEN}✓ Dependencies installed${NC}"

# ── 4. .env file ─────────────────────────────────────────────────────────────
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${YELLOW}⚠ .env file created from .env.example${NC}"
    echo -e "${YELLOW}  → Please add your GROQ_API_KEY to .env before running${NC}"
else
    echo -e "${GREEN}✓ .env file already exists${NC}"
fi

# ── 5. Create directories ─────────────────────────────────────────────────────
mkdir -p logs repomind_memory assets
echo -e "${GREEN}✓ Required directories created${NC}"

# ── 6. Run tests ──────────────────────────────────────────────────────────────
echo ""
echo "→ Running tests..."
if pytest tests/ -v --tb=short -q 2>/dev/null; then
    echo -e "${GREEN}✓ All tests passed${NC}"
else
    echo -e "${YELLOW}⚠ Some tests failed — check output above${NC}"
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "────────────────────────────────────────"
echo -e "${GREEN}✅ Setup complete!${NC}"
echo ""
echo "Next steps:"
echo "  1. Edit .env and add your GROQ_API_KEY"
echo "  2. Run backend:  uvicorn backend.main:app --reload"
echo "  3. Run MCP:      uvicorn src.mcp.server:app --port 9000"
echo "  4. Run frontend: streamlit run frontend/app.py"
echo ""
echo "  Or with Docker:  docker-compose up --build"
echo ""
