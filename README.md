# Footnote-Aware RAG Pipeline

A LangGraph pipeline that demonstrates how an **SLM pre-processing step** preserves footnote context in RAG summarization — preventing misleading summaries where footnotes materially change the meaning of the main text.

## Problem

Standard RAG pipelines chunk documents naively. When footnotes are separated from the sentences they qualify, the LLM summarizer never sees the critical fine print — producing summaries that can be **dangerously misleading** (e.g., reporting "$2.4B revenue with 34% growth" without noting that nearly all growth came from an acquisition and organic growth was only 3.2%).

## Solution: The "Specialist & Executive" Architecture

```
Load Document
     │
     ├──► Naive Chunker ──► FAISS (raw) ──► LLM Summary  ─── (baseline)
     │
     └──► SLM Stitcher ──► Enriched Chunker ──► FAISS (enriched) ──► LLM Summary  ─── (with footnotes)
                │
                └─ SLM inlines footnote text next to citing sentences
                   e.g., "revenue of $2.4B [1] {FOOTNOTE [1]: includes $820M from acquisition; organic growth was 3.2%}"

Both summaries → Markdown report + heatmap PNG + interactive HTML audit report.
```

| Step | Component | Default Model |
|---|---|---|
| Pre-processing | SLM "Librarian" — footnote stitcher | `gpt-5-mini` |
| Chunking | `RecursiveCharacterTextSplitter` (footnote-boundary-aware) | — |
| Storage & Retrieval | FAISS in-memory vector store | `text-embedding-3-small` |
| Summarization | LLM "Executive" — financial analyst | `gpt-5.2` |

## Quick Start

```bash
# 1. Clone
git clone https://github.com/mocelj/rag-footprint.git
cd rag-footprint

# 2. Virtual environment
python3 -m venv .venv && source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure API key
cp .env.example .env
# Edit .env → add your OPENAI_API_KEY
```

## Usage

```bash
# Run with the included test document
python3 src/LangGraph_Footnote_RAG_Advanced.py

# Run with the sample earnings PDF (generate it first)
python3 src/generate_sample_pdf.py
python3 src/LangGraph_Footnote_RAG_Advanced.py data/Exemplar_Corp_Q3_2025_Earnings.pdf

# Run with any .txt or .pdf
python3 src/LangGraph_Footnote_RAG_Advanced.py path/to/your/document.pdf

# Re-render reports from a previous run (zero API calls)
python3 src/LangGraph_Footnote_RAG_Advanced.py --rerender data/state_Exemplar_Corp_Q3_2025_Earnings_20260228_164328.json
```

### Pipeline Outputs

Each run produces timestamped files in the input file's directory:

| Output | Description |
|---|---|
| `summary_report_<name>_<timestamp>.md` | Side-by-side Markdown comparison of baseline vs. enriched summaries |
| `heatmap_<name>_<timestamp>.png` | Visual heatmap showing footnote coverage per chunk |
| `audit_report_<name>_<timestamp>.html` | Interactive HTML report with scorecard, chunk inspector, and footnote registry |
| `state_<name>_<timestamp>.json` | Serialized pipeline state — use with `--rerender` to regenerate reports without API calls |

## Sample Document

The repo includes a PDF generator that creates a realistic **8-page earnings report** for the fictitious company **Exemplar Corp** — containing 40 footnotes that materially qualify or contradict the main text claims:

```bash
python3 src/generate_sample_pdf.py
# → data/Exemplar_Corp_Q3_2025_Earnings.pdf
```

> **Disclaimer:** Exemplar Corp is entirely fictitious. All persons, figures, and entities in the sample document are imaginary.

## Configuration

All model choices are configurable via `.env`:

| Variable | Default | Purpose |
|---|---|---|
| `PROVIDER` | `openai` | `openai` or `azure` — selects which backend to use |
| `OPENAI_API_KEY` | — | Required when `PROVIDER=openai` |
| `SLM_MODEL` | `gpt-5-mini` | Lightweight model (or Azure deployment name) for footnote stitching |
| `LLM_MODEL` | `gpt-5.2` | Powerful model (or Azure deployment name) for summarization |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model (or Azure deployment name) for FAISS vectors |

### Azure OpenAI

To use Azure OpenAI instead of the public OpenAI API, set `PROVIDER=azure` and add the Azure-specific variables to your `.env`:

```dotenv
PROVIDER=azure
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-azure-openai-api-key
AZURE_OPENAI_API_VERSION=2024-12-01-preview

# Use your Azure deployment names:
SLM_MODEL=gpt-4o-mini
LLM_MODEL=gpt-4o
EMBEDDING_MODEL=text-embedding-3-small
```

The pipeline auto-switches between `ChatOpenAI` / `AzureChatOpenAI` and `OpenAIEmbeddings` / `AzureOpenAIEmbeddings` based on the `PROVIDER` value. No code changes required.

## Algorithm & Approach

### The Footnote Problem in RAG

Financial, legal, and regulatory documents routinely place **material qualifications** in footnotes — fine print that can reverse the meaning of headline claims. Standard RAG pipelines chunk text by character count, inevitably splitting footnote references (in the body) from their definitions (at the page bottom). When the LLM summarizer retrieves chunks, it sees the claim but never the qualifying footnote, producing a summary that is factually misleading.

### Solution Overview

The pipeline inserts an **SLM pre-processing layer** ("the Librarian") between document loading and chunking. This smaller, cheaper model re-writes the document with every footnote definition inlined next to its citing sentence, so that downstream chunking and retrieval always keep claim + qualification together.

### Pipeline Nodes (LangGraph DAG)

```
                     ┌─────────────┐
                     │ Load Doc    │  ← .txt or .pdf
                     └──────┬──────┘
                            │
                      ┌─────┴─────┐
                      │           │
                      ▼           ▼
               ┌──────────┐ ┌───────────────┐
               │  Naive   │ │  SLM Footnote │  ← gpt-5-mini
               │  Chunker │ │  Stitcher     │
               └────┬─────┘ └──────┬────────┘
                    │              │
                    │         ┌────┴─────┐
                    │         │ Enriched │
                    │         │ Chunker  │
                    │         └────┬─────┘
                    ▼              ▼
               ┌────────┐   ┌──────────┐
               │ FAISS  │   │  FAISS   │    ← text-embedding-3-small
               │ (raw)  │   │(enriched)│
               └────┬───┘   └────┬─────┘
                    ▼             ▼
               ┌────────┐   ┌──────────┐
               │  LLM   │   │   LLM    │    ← gpt-5.2
               │Summary │   │ Summary  │
               └────┬───┘   └────┬─────┘
                    │             │
                    └──────┬──────┘
                           ▼
                    ┌─────────────┐
                    │  Reports    │  → .md + .png + .html
                    └─────────────┘
```

### SLM Footnote Stitcher — Detailed Algorithm

The stitcher is the core of the pipeline. It solves the problem that footnote references in the body text (e.g., `[30]`) are often separated from their definitions by thousands of characters, landing in different batches when the document exceeds the SLM's context window.

#### Step 1 — Pre-extract a Global Footnote Dictionary

Before any batching, a regex scan collects **every** footnote definition from the raw text:

```
[N] Definition text that may span
    multiple lines...
```

The regex matches lines starting with `[N]` and captures text up to the next `[N]` definition, a `Page N/M` marker, or a `CONFIDENTIAL` header. Results are stored in a `{marker_int: full_text}` dictionary. If a marker appears more than once (e.g., on different pages), the longer definition wins.

#### Step 2 — Page-Aware Batch Splitting

Instead of slicing the document at arbitrary character offsets (which split body text from its page's footnote definitions), the text is split on `Page N/M` markers — natural page boundaries from PDF extraction. Adjacent pages are then merged into batches up to ~4,500 characters to keep the number of SLM calls reasonable while preserving the body-plus-definitions relationship within each page.

#### Step 3 — Footnote Appendix Injection

Each batch is scanned for `[N]` markers. A `--- FOOTNOTE DEFINITIONS (for reference) ---` appendix is appended listing the full definition (from the Step 1 dictionary) for every marker found in the batch. This ensures that even cross-page references — where the body cites a footnote defined on a different page — have the definition available within the same SLM context window.

#### Step 4 — SLM Invocation

Each enriched batch is sent to the SLM with a system prompt instructing it to:

- Find every `[N]` marker in the body text
- Look up its definition (from the in-page footnotes **or** the injected appendix)
- Inline the definition as `{FOOTNOTE [N]: <text>}` right after the citing sentence
- Remove the original footnote section and the appendix from the output
- Mark any truly missing footnote as `{FOOTNOTE [N]: MISSING — no matching footnote found}`

#### Step 5 — Smart De-duplication

The same footnote marker may be inlined in multiple batches. The de-duplication strategy prefers:

1. **Real content over MISSING** — if one batch produced MISSING but another resolved the definition, the resolved version wins
2. **Longer text over truncated** — if both have content, the longer (more complete) text is kept

#### Step 6 — Post-Validation Backfill

A final pass compares the SLM's footnote registry against the pre-extracted global dictionary:

- **MISSING entries** are replaced with the pre-extracted definition and marked `"backfilled"`
- **Truncated entries** (SLM text < 60% of known definition length) are replaced
- **Unresolved markers** that the SLM never encountered are added directly

The enriched text is also patched in-place: any remaining `{FOOTNOTE [N]: MISSING ...}` blocks are replaced with the real definition.

### Downstream Processing

| Step | Description |
|---|---|
| **Enriched Chunker** | Splits stitched text with `RecursiveCharacterTextSplitter`, but first collapses newlines inside `{FOOTNOTE ...}` blocks so the splitter treats each annotation as a single token — preventing footnote blocks from being split across chunks. |
| **Dual FAISS Retrieval** | Two independent vector stores are built (raw chunks vs. enriched chunks) using the same embedding model. Top-K similarity search retrieves the most relevant chunks for summarization. |
| **LLM Summarization** | The "Executive" LLM receives retrieved chunks and system prompts from external files (`llm-prompt-raw.txt`, `llm-prompt-enriched.txt`). The enriched prompt explicitly instructs the LLM to incorporate `{FOOTNOTE}` qualifications and not present claims as unqualified facts. |
| **Reports** | A Markdown comparison report, a matplotlib heatmap showing footnote density per chunk, and a self-contained interactive HTML audit report with scorecard, chunk inspector, and footnote registry. |

### Prompt Externalization

All LLM/SLM prompts are loaded from text files at startup rather than hardcoded:

| File | Purpose |
|---|---|
| `slm-prompt.txt` | SLM system prompt — footnote stitching rules and output format |
| `llm-prompt-raw.txt` | LLM prompt for the baseline (no-footnote) summary |
| `llm-prompt-enriched.txt` | LLM prompt for the enriched summary — includes instructions to respect `{FOOTNOTE}` annotations |

This makes prompt iteration easy without touching Python code.

### State Serialization & Re-rendering

After each full pipeline run, the complete graph state (raw text, enriched text, chunks, summaries, footnote registry) is serialized to a JSON file. The `--rerender` flag reloads this state and regenerates only the report artifacts — **zero API calls** — allowing rapid iteration on report formatting.

## Project Structure

```
rag-footprint/
├── src/
│   ├── LangGraph_Footnote_RAG_Advanced.py   # Main pipeline (LangGraph)
│   ├── rag_heatmap_visualizer.py            # Heatmap generator (matplotlib)
│   ├── audit_report_generator.py            # Interactive HTML report
│   ├── generate_sample_pdf.py               # Exemplar Corp PDF generator
│   ├── slm-prompt.txt                       # SLM system prompt (footnote stitcher)
│   ├── llm-prompt-raw.txt                   # LLM prompt — baseline summarization
│   └── llm-prompt-enriched.txt              # LLM prompt — enriched summarization
├── data/
│   ├── Footnote_Validation_Doc.txt          # Minimal test document (3 footnotes)
│   └── Exemplar_Corp_Q3_2025_Earnings.pdf   # Generated sample (40 footnotes)
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## License

MIT
