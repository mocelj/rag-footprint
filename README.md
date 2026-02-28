# Footnote-Aware RAG Pipeline

A LangGraph pipeline that demonstrates how an **SLM pre-processing step** preserves footnote context in RAG summarization — preventing misleading summaries where footnotes materially change the meaning of the main text.

## Problem

Standard RAG pipelines chunk documents naively. When footnotes are separated from the sentences they qualify, the LLM summarizer never sees the critical fine print — producing summaries that can be **dangerously misleading** (e.g., reporting "$10M revenue" without noting $9M was a one-time insurance payout).

## Solution: The "Specialist & Executive" Architecture

```
Load Document
     │
     ├──► Naive Chunker ──► FAISS (raw) ──► LLM Summary  ─── (baseline)
     │
     └──► SLM Stitcher ──► Enriched Chunker ──► FAISS (enriched) ──► LLM Summary  ─── (with footnotes)
                │
                └─ GPT-5.2-mini inlines footnote text next to citing sentences
                   e.g., "revenue of $10M [1] {FOOTNOTE [1]: includes one-time $9M insurance payout}"

Both summaries are written to a Markdown comparison report.
```

| Step | Component | Model |
|---|---|---|
| Pre-processing | SLM "Librarian" — footnote stitcher | `gpt-5.2-mini` |
| Chunking | `RecursiveCharacterTextSplitter` (footnote-boundary-aware) | — |
| Storage & Retrieval | FAISS in-memory vector store | `text-embedding-3-small` |
| Summarization | LLM "Executive" — financial analyst | `gpt-5.2` |

## Setup

```bash
# 1. Clone and enter the project
cd rag-footprint

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and add your OpenAI API key
```

## Usage

```bash
# Run with the included validation document (default)
python src/LangGraph_Footnote_RAG_Advanced.py

# Run with a specific file
python src/LangGraph_Footnote_RAG_Advanced.py data/Footnote_Validation_Doc.txt

# Run with a PDF
python src/LangGraph_Footnote_RAG_Advanced.py data/report.pdf
```

The pipeline produces a `summary_report_<filename>.md` in the same directory as the input file.

## Configuration

All model choices are configurable via `.env`:

| Variable | Default | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | — | Required. Your OpenAI API key |
| `SLM_MODEL` | `gpt-5.2-mini` | Lightweight model for footnote stitching |
| `LLM_MODEL` | `gpt-5.2` | Powerful model for summarization |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model for FAISS |

## How It Works

1. **Load Document** — Reads `.txt` or `.pdf` input files
2. **Naive Chunker** — Splits raw text into overlapping chunks (baseline path)
3. **SLM Footnote Stitcher** — GPT-5.2-mini scans for footnote markers (`[1]`, `[2]`, etc.), finds their definitions, and inlines them next to the citing sentence as `{FOOTNOTE [n]: ...}`
4. **Enriched Chunker** — Splits the "healed" text into chunks, preserving `{FOOTNOTE}` blocks intact
5. **FAISS Retrieval** — Builds two separate vector indices (raw vs. enriched) and retrieves top-k relevant chunks
6. **LLM Summarization** — GPT-5.2 generates summaries from each index. The enriched path explicitly instructs the LLM to incorporate footnote qualifications
7. **Comparison Report** — Writes a Markdown report with both summaries side-by-side

## Example Output

With the included `Footnote_Validation_Doc.txt`:

- **Baseline summary** will likely state: *"Revenue of $10M with 50% YoY growth, facilities at 95% capacity"*
- **Enriched summary** will note: *"Reported revenue of $10M includes a one-time $9M insurance payout; actual product sales are ~$1M. Growth expectations are contingent on a pending merger with 90% chance of regulatory block. 95% capacity refers to available space, but 40% of machinery is broken."*

## Project Structure

```
rag-footprint/
├── src/
│   ├── LangGraph_Footnote_RAG_Advanced.py  # Main pipeline
│   └── slm-prompt.txt                      # SLM system prompt
├── data/
│   └── Footnote_Validation_Doc.txt          # Test document
├── requirements.txt                         # Python dependencies
├── .env.example                             # Environment template
├── .gitignore
└── README.md
```
