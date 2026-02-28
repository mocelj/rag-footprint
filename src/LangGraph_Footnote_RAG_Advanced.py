"""
Footnote-Aware RAG Pipeline with SLM Pre-processing
=====================================================
A LangGraph pipeline that uses an SLM (GPT-5.2-mini) to inline footnotes
into their referencing text before chunking, then uses an LLM (GPT-5.2)
to summarize the enriched context via RAG with FAISS retrieval.

Produces a Markdown report comparing summaries WITH and WITHOUT the SLM
footnote-stitching technique.

Usage:
    python src/LangGraph_Footnote_RAG_Advanced.py [input_file]
    python src/LangGraph_Footnote_RAG_Advanced.py data/Footnote_Validation_Doc.txt
    python src/LangGraph_Footnote_RAG_Advanced.py data/report.pdf
"""

import operator
import os
import re
import sys
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Annotated, List, TypedDict

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langgraph.graph import StateGraph, START, END
from pypdf import PdfReader

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
# Load .env from project root (one level up from src/)
_PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

SLM_MODEL = os.getenv("SLM_MODEL", "gpt-5-mini")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-5.2")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

CHUNK_SIZE = 800        # characters per chunk
CHUNK_OVERLAP = 100     # overlap between chunks
TOP_K = 4               # number of chunks to retrieve for summarization

# Load SLM system prompt from file
_PROMPT_PATH = Path(__file__).parent / "slm-prompt.txt"
SLM_SYSTEM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8") if _PROMPT_PATH.exists() else ""

# ---------------------------------------------------------------------------
# 1. Graph State
# ---------------------------------------------------------------------------
class GraphState(TypedDict):
    source_file: str                                           # input file path
    raw_text: str                                              # original document text
    enriched_text: str                                         # text after SLM footnote stitching
    footnotes_registry: Annotated[List[dict], operator.add]    # accumulated footnote records
    raw_chunks: List[str]                                      # naive chunks (no stitching)
    enriched_chunks: List[str]                                 # chunks from stitched text
    raw_summary: str                                           # baseline summary (no SLM)
    enriched_summary: str                                      # summary with SLM enrichment
    report_path: str                                           # path to generated report


# ---------------------------------------------------------------------------
# 2. Node: Load Document
# ---------------------------------------------------------------------------
def load_document(state: GraphState) -> dict:
    """Read a .txt or .pdf file and populate raw_text."""
    file_path = Path(state["source_file"])

    if not file_path.exists():
        raise FileNotFoundError(f"Input file not found: {file_path}")

    if file_path.suffix.lower() == ".pdf":
        reader = PdfReader(str(file_path))
        pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n\n".join(pages)
    else:
        text = file_path.read_text(encoding="utf-8")

    print(f"[load_document] Loaded {len(text)} characters from {file_path.name}")
    return {"raw_text": text}


# ---------------------------------------------------------------------------
# 3. Node: Naive Chunker (baseline — no footnote stitching)
# ---------------------------------------------------------------------------
def naive_chunker(state: GraphState) -> dict:
    """Split raw text into overlapping chunks WITHOUT footnote processing."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_text(state["raw_text"])
    print(f"[naive_chunker] Created {len(chunks)} raw chunks")
    return {"raw_chunks": chunks}


# ---------------------------------------------------------------------------
# 4. Node: SLM Footnote Stitcher (the "Librarian")
# ---------------------------------------------------------------------------
def slm_footnote_stitcher(state: GraphState) -> dict:
    """
    Call the SLM to identify footnote markers in the raw text and inline
    the corresponding footnote definitions next to the citing sentence.
    """
    slm = ChatOpenAI(model=SLM_MODEL, temperature=0.0, max_tokens=4096)

    messages = [
        {"role": "system", "content": SLM_SYSTEM_PROMPT},
        {"role": "user", "content": f"Source_Text:\n\n{state['raw_text']}"},
    ]

    response = slm.invoke(messages)
    healed_text = response.content.strip()

    # Extract footnote registry from the healed text
    footnote_pattern = re.compile(
        r"\{FOOTNOTE\s*\[(\d+)\]\s*:\s*(.+?)\}", re.DOTALL
    )
    footnotes = [
        {"marker": int(m.group(1)), "text": m.group(2).strip(), "status": "linked"}
        for m in footnote_pattern.finditer(healed_text)
    ]

    # De-duplicate (same marker may appear in multiple chunks later)
    seen = set()
    unique_footnotes = []
    for fn in footnotes:
        if fn["marker"] not in seen:
            seen.add(fn["marker"])
            unique_footnotes.append(fn)

    print(f"[slm_footnote_stitcher] Inlined {len(unique_footnotes)} footnotes")
    return {
        "enriched_text": healed_text,
        "footnotes_registry": unique_footnotes,
    }


# ---------------------------------------------------------------------------
# 5. Node: Enriched Chunker (footnote-boundary-aware)
# ---------------------------------------------------------------------------
def enriched_chunker(state: GraphState) -> dict:
    """
    Chunk the SLM-stitched text, being careful not to split inside
    {FOOTNOTE ...} blocks.
    """
    text = state["enriched_text"]

    # Protect footnote blocks from being split: temporarily replace
    # newlines inside {FOOTNOTE ...} with a placeholder so the splitter
    # treats each block as a single token.
    def _protect(match: re.Match) -> str:
        return match.group(0).replace("\n", " ")

    protected = re.sub(r"\{FOOTNOTE.*?\}", _protect, text, flags=re.DOTALL)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_text(protected)
    print(f"[enriched_chunker] Created {len(chunks)} enriched chunks")
    return {"enriched_chunks": chunks}


# ---------------------------------------------------------------------------
# 6. Node: Build FAISS Vector Stores & Summarize (Raw — baseline)
# ---------------------------------------------------------------------------
def summarize_raw(state: GraphState) -> dict:
    """
    Build a FAISS index from raw (non-stitched) chunks, retrieve the
    most relevant ones, and ask the LLM for a summary — baseline mode.
    """
    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
    docs = [Document(page_content=c, metadata={"has_footnote": False}) for c in state["raw_chunks"]]
    vectorstore = FAISS.from_documents(docs, embeddings)

    query = "Summarize the key financial metrics, operational status, and any risks."
    retrieved = vectorstore.similarity_search(query, k=TOP_K)
    context = "\n\n---\n\n".join(doc.page_content for doc in retrieved)

    llm = ChatOpenAI(model=LLM_MODEL, temperature=0.0, max_tokens=2048)
    prompt = textwrap.dedent(f"""\
        You are a financial analyst. Summarize the following document sections
        into a clear, accurate executive summary. Cover revenue, operational
        status, and risks. Be concise but thorough.

        DOCUMENT SECTIONS:
        {context}
    """)
    response = llm.invoke([{"role": "user", "content": prompt}])
    summary = response.content.strip()
    print(f"[summarize_raw] Generated baseline summary ({len(summary)} chars)")
    return {"raw_summary": summary}


# ---------------------------------------------------------------------------
# 7. Node: Build FAISS Vector Stores & Summarize (Enriched — with SLM)
# ---------------------------------------------------------------------------
def summarize_enriched(state: GraphState) -> dict:
    """
    Build a FAISS index from enriched (footnote-stitched) chunks, retrieve
    the most relevant ones, and ask the LLM for a summary — enriched mode.
    """
    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
    docs = [
        Document(
            page_content=c,
            metadata={"has_footnote": bool(re.search(r"\{FOOTNOTE", c))},
        )
        for c in state["enriched_chunks"]
    ]
    vectorstore = FAISS.from_documents(docs, embeddings)

    query = "Summarize the key financial metrics, operational status, and any risks."
    retrieved = vectorstore.similarity_search(query, k=TOP_K)
    context = "\n\n---\n\n".join(doc.page_content for doc in retrieved)

    llm = ChatOpenAI(model=LLM_MODEL, temperature=0.0, max_tokens=2048)
    prompt = textwrap.dedent(f"""\
        You are a financial analyst. Summarize the following document sections
        into a clear, accurate executive summary. Cover revenue, operational
        status, and risks. Be concise but thorough.

        IMPORTANT: The text contains inline {{FOOTNOTE [n]: ...}} annotations.
        These footnotes provide CRITICAL context — they may qualify, limit, or
        even contradict the main text claims. You MUST incorporate footnote
        information into your summary. Do NOT present a claim as unqualified
        fact if a footnote adds conditions or exceptions.

        DOCUMENT SECTIONS:
        {context}
    """)
    response = llm.invoke([{"role": "user", "content": prompt}])
    summary = response.content.strip()
    print(f"[summarize_enriched] Generated enriched summary ({len(summary)} chars)")
    return {"enriched_summary": summary}


# ---------------------------------------------------------------------------
# 8. Node: Generate Comparison Report
# ---------------------------------------------------------------------------
def generate_report(state: GraphState) -> dict:
    """Write a Markdown report comparing both summaries side by side."""
    source = Path(state["source_file"]).name
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_name = f"summary_report_{Path(state['source_file']).stem}.md"
    report_path = Path(state["source_file"]).parent / report_name

    # Format footnotes table
    fn_rows = ""
    for fn in state.get("footnotes_registry", []):
        fn_rows += f"| [{fn['marker']}] | {fn['text']} | {fn['status']} |\n"
    if not fn_rows:
        fn_rows = "| — | No footnotes detected | — |\n"

    report = textwrap.dedent(f"""\
    # Footnote-Aware RAG — Summary Comparison Report

    | Field | Value |
    |---|---|
    | **Source Document** | `{source}` |
    | **Generated** | {timestamp} |
    | **SLM Model** | `{SLM_MODEL}` |
    | **LLM Model** | `{LLM_MODEL}` |
    | **Chunk Size** | {CHUNK_SIZE} chars |
    | **Top-K Retrieval** | {TOP_K} |

    ---

    ## 1. Baseline Summary (Without SLM Footnote Stitching)

    > Standard RAG approach: raw text is chunked and summarized directly.
    > Footnotes may be separated from the text they qualify.

    {state.get('raw_summary', 'N/A')}

    ---

    ## 2. Enriched Summary (With SLM Footnote Stitching)

    > Hybrid approach: an SLM first inlines footnote text next to citing
    > sentences, then the enriched text is chunked and summarized.

    {state.get('enriched_summary', 'N/A')}

    ---

    ## 3. Key Differences

    The baseline summary likely presents headline figures at face value,
    while the enriched summary incorporates footnote qualifications that
    may materially change interpretation. Compare how each version handles:

    - **Revenue figures** — Does the summary mention the one-time insurance payout?
    - **Growth expectations** — Does it note the merger contingency?
    - **Operational capacity** — Does it mention broken machinery?

    ---

    ## 4. Discovered Footnotes

    | Marker | Footnote Text | Status |
    |---|---|---|
    {fn_rows}
    ---

    ## 5. Architecture

    ```
    ┌─────────────┐
    │ Load Doc    │
    └──────┬──────┘
           │
     ┌─────┴─────┐
     │            │
     ▼            ▼
    ┌──────┐  ┌───────────┐
    │Naive │  │SLM Stitch │  ← GPT-5.2-mini inlines footnotes
    │Chunk │  └─────┬─────┘
    └──┬───┘        │
       │        ┌───┴───┐
       │        │Enrich │
       │        │Chunk  │
       │        └───┬───┘
       ▼            ▼
    ┌──────┐  ┌──────────┐
    │FAISS │  │  FAISS   │
    │(raw) │  │(enriched)│
    └──┬───┘  └────┬─────┘
       │           │
       ▼           ▼
    ┌──────┐  ┌──────────┐
    │ LLM  │  │   LLM    │  ← GPT-5.2 summarizes
    │ Sum  │  │   Sum    │
    └──┬───┘  └────┬─────┘
       │           │
       └─────┬─────┘
             ▼
       ┌───────────┐
       │  Report   │  → summary_report_*.md
       └───────────┘
    ```

    *Generated by LangGraph Footnote RAG Pipeline*
    """)

    report_path.write_text(report, encoding="utf-8")
    print(f"[generate_report] Report written to {report_path}")
    return {"report_path": str(report_path)}


# ---------------------------------------------------------------------------
# 9. Build the LangGraph Workflow
# ---------------------------------------------------------------------------
workflow = StateGraph(GraphState)

# Register nodes
workflow.add_node("load_document", load_document)
workflow.add_node("naive_chunker", naive_chunker)
workflow.add_node("slm_footnote_stitcher", slm_footnote_stitcher)
workflow.add_node("enriched_chunker", enriched_chunker)
workflow.add_node("summarize_raw", summarize_raw)
workflow.add_node("summarize_enriched", summarize_enriched)
workflow.add_node("generate_report", generate_report)

# Define edges (sequential pipeline)
workflow.add_edge(START, "load_document")
workflow.add_edge("load_document", "naive_chunker")
workflow.add_edge("naive_chunker", "slm_footnote_stitcher")
workflow.add_edge("slm_footnote_stitcher", "enriched_chunker")
workflow.add_edge("enriched_chunker", "summarize_raw")
workflow.add_edge("summarize_raw", "summarize_enriched")
workflow.add_edge("summarize_enriched", "generate_report")
workflow.add_edge("generate_report", END)

# Compile
app = workflow.compile()


# ---------------------------------------------------------------------------
# 10. CLI Entry Point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Determine input file
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = str(_PROJECT_ROOT / "data" / "Footnote_Validation_Doc.txt")

    # Resolve relative paths
    input_path = Path(input_file)
    if not input_path.is_absolute():
        input_path = _PROJECT_ROOT / input_path

    if not input_path.exists():
        print(f"Error: File not found — {input_path}")
        sys.exit(1)

    print("=" * 60)
    print("  Footnote-Aware RAG Pipeline")
    print(f"  SLM: {SLM_MODEL}  |  LLM: {LLM_MODEL}")
    print(f"  Input: {input_path.name}")
    print("=" * 60)

    # Run the graph
    initial_state: GraphState = {
        "source_file": str(input_path),
        "raw_text": "",
        "enriched_text": "",
        "footnotes_registry": [],
        "raw_chunks": [],
        "enriched_chunks": [],
        "raw_summary": "",
        "enriched_summary": "",
        "report_path": "",
    }

    result = app.invoke(initial_state)

    print("\n" + "=" * 60)
    print("  Pipeline complete!")
    print(f"  Report: {result['report_path']}")
    print(f"  Footnotes found: {len(result['footnotes_registry'])}")
    print("=" * 60)
