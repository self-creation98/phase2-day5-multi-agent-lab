# Multi-Agent Research System

Hệ thống nghiên cứu tự động sử dụng kiến trúc **multi-agent** với 5 agent chuyên biệt, được điều phối bởi **LangGraph** và theo dõi qua **LangSmith**. Hệ thống nhận câu hỏi nghiên cứu, tự động tìm kiếm thông tin, phân tích, viết báo cáo và kiểm tra chất lượng.

## Kiến trúc hệ thống

```
User Query
   |
   v
Supervisor / Router (LLM routing + deterministic fallback)
   |------> Researcher Agent  --> Tavily Search + LLM --> research_notes
   |------> Analyst Agent     --> LLM analysis        --> analysis_notes
   |------> Writer Agent      --> LLM synthesis        --> final_answer
   |             |
   |             v
   |         Critic Agent     --> fact-check + citation review
   |
   v
LangSmith Trace + Benchmark Report
```

| Agent | Vai tro | Input | Output |
|---|---|---|---|
| **Supervisor** | Dinh tuyen va dieu phoi | Trang thai hien tai | Route tiep theo |
| **Researcher** | Tim kiem va tong hop nguon | Query | research_notes + sources |
| **Analyst** | Phan tich va danh gia | research_notes | analysis_notes |
| **Writer** | Viet bai voi trich dan | research + analysis | final_answer |
| **Critic** | Kiem tra chat luong | final_answer + sources | review findings |

## Cau truc thu muc

```text
.
├── src/multi_agent_research_lab/
│   ├── agents/              # Supervisor, Researcher, Analyst, Writer, Critic
│   ├── core/                # Config, state, schemas, errors
│   ├── graph/               # LangGraph workflow (StateGraph + conditional routing)
│   ├── services/            # LLM client (OpenAI), Search client (Tavily)
│   ├── evaluation/          # Benchmark scoring + report generation
│   ├── observability/       # Logging + LangSmith tracing
│   └── cli.py               # CLI: baseline, multi-agent, benchmark
├── configs/                 # YAML config (models, temperature, max_iterations)
├── docs/                    # Lab guide, peer review rubric
├── tests/                   # Unit tests (5 tests)
├── reports/                 # Benchmark report + LangSmith screenshots
├── .env.example             # Template cho API keys
├── requirements.txt         # Python dependencies
├── pyproject.toml           # Project config + linting + testing
├── Dockerfile               # Container hoa
└── Makefile                 # Lenh tat
```

## Quickstart

### 1. Tao moi truong

```bash
python -m venv .venv

# Linux/Mac
source .venv/bin/activate

# Windows
.venv\Scripts\activate

pip install -r requirements.txt
pip install -e ".[dev,llm]"
```

### 2. Cau hinh API keys

Tao file `.env` tu template:

```bash
cp .env.example .env
```

Mo `.env` va dien cac key:

```env
# Bat buoc
OPENAI_API_KEY=sk-proj-...

# Khuyen khich (search that + tracing)
TAVILY_API_KEY=tvly-...
LANGSMITH_API_KEY=lsv2_pt_...
```

| Key | Bat buoc | Muc dich | Dang ky |
|---|---|---|---|
| `OPENAI_API_KEY` | Co | LLM cho tat ca agents | https://platform.openai.com |
| `TAVILY_API_KEY` | Nen co | Researcher Agent tim kiem web | https://tavily.com (free 1000 req/thang) |
| `LANGSMITH_API_KEY` | Nen co | Tracing + monitoring | https://smith.langchain.com (free 5000 traces/thang) |

### 3. Chay tests

```bash
pytest tests/ -v
```

## Su dung

### Single-Agent Baseline

Chay 1 LLM call duy nhat de tra loi:

```bash
python -m multi_agent_research_lab.cli baseline \
  --query "Research GraphRAG state-of-the-art and write a 500-word summary"
```

### Multi-Agent Workflow

Chay day du pipeline: Supervisor -> Researcher -> Analyst -> Writer -> Critic:

```bash
python -m multi_agent_research_lab.cli multi-agent \
  --query "Research GraphRAG state-of-the-art and write a 500-word summary"
```

### Benchmark (so sanh Single vs Multi-Agent)

Chay 3 queries, do latency/cost/quality, xuat report:

```bash
# Windows
$env:PYTHONIOENCODING="utf-8"
python -m multi_agent_research_lab.cli benchmark

# Linux/Mac
PYTHONIOENCODING=utf-8 python -m multi_agent_research_lab.cli benchmark
```

Report duoc luu tai `reports/benchmark_report.md`.

## Ket qua Benchmark

| Metric | Single-Agent | Multi-Agent |
|---|---|---|
| **Chat luong** | 6.0/10 | **10.0/10** |
| **Citation coverage** | 0% | **100%** |
| **Latency** | **~11s** | ~38s |
| **Chi phi/query** | **$0.0005** | $0.0022 |
| **So nguon** | 0 | **5** |
| **Ti le loi** | 0% | 0% |

> Multi-agent cho chat luong cao hon 67%, citation coverage 100%, nhung cham hon 3.5x va dat hon 4.4x.

## Guardrails

| Guardrail | Mo ta | Config |
|---|---|---|
| `max_iterations` | Gioi han so vong lap cua Supervisor | `.env` hoac `configs/lab_default.yaml` (default: 6) |
| `timeout_seconds` | Timeout cho moi LLM call | `.env` (default: 60s) |
| Retry | Tu dong thu lai khi LLM fail | `tenacity` (3 lan, exponential backoff) |
| Deterministic fallback | Routing khong can LLM neu LLM fail | `supervisor._deterministic_route()` |
| Mock search | Du lieu gia khi Tavily khong kha dung | `search_client._mock_search()` |

## LangSmith Tracing

Khi cau hinh `LANGSMITH_API_KEY`, tat ca cac LangGraph run duoc tu dong trace:

- **Project**: `multi-agent-research-lab`
- **Dashboard**: https://smith.langchain.com
- Xem chi tiet tung agent call, input/output, latency, token usage

Screenshots: [`reports/screenshots/`](reports/screenshots/)

## Tech Stack

| Component | Technology |
|---|---|
| LLM | OpenAI GPT-4o-mini |
| Search | Tavily Search API |
| Orchestration | LangGraph (StateGraph) |
| Tracing | LangSmith |
| Schemas | Pydantic v2 |
| CLI | Typer + Rich |
| Retry | Tenacity |
| Testing | Pytest |
| Linting | Ruff |

## References

- [Building Effective Agents - Anthropic](https://www.anthropic.com/engineering/building-effective-agents)
- [LangGraph Concepts](https://langchain-ai.github.io/langgraph/concepts/)
- [LangSmith Tracing](https://docs.smith.langchain.com/)
- [Tavily Search API](https://tavily.com/)
