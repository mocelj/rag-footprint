"""
Footnote-Aware RAG Pipeline with SLM Pre-processing
=====================================================
A LangGraph pipeline that uses an SLM to inline footnotes into their
referencing text before chunking, then uses an LLM to summarize the
enriched context via RAG with FAISS retrieval.

Produces a timestamped Markdown report, a heatmap PNG, and an
interactive HTML audit report comparing summaries WITH and WITHOUT
the SLM footnote-stitching technique.

Usage:
    python src/LangGraph_Footnote_RAG_Advanced.py [input_file]
    python src/LangGraph_Footnote_RAG_Advanced.py data/Footnote_Validation_Doc.txt
    python src/LangGraph_Footnote_RAG_Advanced.py data/Exemplar_Corp_Q3_2025_Earnings.pdf
"""

import operator
import json
import os
import re
import sys
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Annotated, List, TypedDict

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
try:
    from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
except ImportError:  # older langchain-openai versions
    AzureChatOpenAI = None  # type: ignore[assignment,misc]
    AzureOpenAIEmbeddings = None  # type: ignore[assignment,misc]
try:
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider
except ImportError:  # azure-identity not installed
    DefaultAzureCredential = None  # type: ignore[assignment,misc]
    get_bearer_token_provider = None  # type: ignore[assignment,misc]
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langgraph.graph import StateGraph, START, END
from pypdf import PdfReader

# Audit & visualization modules (same directory)
from rag_heatmap_visualizer import generate_heatmap
from audit_report_generator import generate_audit_report

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
# Load .env from project root (one level up from src/)
_PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

PROVIDER = os.getenv("PROVIDER", "openai").lower()  # "openai" or "azure"

SLM_MODEL = os.getenv("SLM_MODEL", "gpt-5-mini")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-5.2")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

CHUNK_SIZE = 800        # characters per chunk
CHUNK_OVERLAP = 100     # overlap between chunks
TOP_K = 4               # chunks to retrieve **per sub-query**

# Multi-query retrieval — each sub-query targets a distinct topic so the
# combined results cover the full breadth of the document.  Duplicates are
# removed before the context is sent to the LLM.
RETRIEVAL_QUERIES = [
    "Financial performance, revenue, earnings, and profitability metrics",
    "Cash flow, capital expenditure, liquidity, and debt position",
    "Risks, challenges, regulatory issues, and compliance concerns",
    "Strategic outlook, forward guidance, and growth projections",
    "Operational highlights, market position, and competitive landscape",
]


# ---------------------------------------------------------------------------
# Provider-agnostic model factories (OpenAI / Azure OpenAI)
# ---------------------------------------------------------------------------
def _azure_token_provider():
    """Build a bearer-token provider for Azure OpenAI (Entra ID / RBAC).

    Requires ``azure-identity`` and a prior ``az login``.
    """
    if DefaultAzureCredential is None or get_bearer_token_provider is None:
        raise ImportError(
            "azure-identity is required for keyless Azure auth — "
            "pip install azure-identity"
        )
    credential = DefaultAzureCredential()
    return get_bearer_token_provider(
        credential, "https://cognitiveservices.azure.com/.default"
    )


def _make_chat(deployment_or_model: str, **kwargs) -> ChatOpenAI:
    """Return a ChatOpenAI or AzureChatOpenAI depending on PROVIDER.

    For Azure: uses API key if ``AZURE_OPENAI_API_KEY`` is set, otherwise
    falls back to Entra ID / RBAC via ``DefaultAzureCredential``.
    """
    if PROVIDER == "azure":
        if AzureChatOpenAI is None:
            raise ImportError("AzureChatOpenAI not available — upgrade langchain-openai")
        azure_kwargs = dict(
            azure_deployment=deployment_or_model,
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
        )
        if os.getenv("AZURE_OPENAI_API_KEY"):
            azure_kwargs["api_key"] = os.environ["AZURE_OPENAI_API_KEY"]
        else:
            azure_kwargs["azure_ad_token_provider"] = _azure_token_provider()
        return AzureChatOpenAI(**azure_kwargs, **kwargs)
    return ChatOpenAI(model=deployment_or_model, **kwargs)


def _make_embeddings(deployment_or_model: str) -> OpenAIEmbeddings:
    """Return an OpenAIEmbeddings or AzureOpenAIEmbeddings depending on PROVIDER.

    For Azure: uses API key if ``AZURE_OPENAI_API_KEY`` is set, otherwise
    falls back to Entra ID / RBAC via ``DefaultAzureCredential``.
    """
    if PROVIDER == "azure":
        if AzureOpenAIEmbeddings is None:
            raise ImportError("AzureOpenAIEmbeddings not available — upgrade langchain-openai")
        azure_kwargs = dict(
            azure_deployment=deployment_or_model,
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
        )
        if os.getenv("AZURE_OPENAI_API_KEY"):
            azure_kwargs["api_key"] = os.environ["AZURE_OPENAI_API_KEY"]
        else:
            azure_kwargs["azure_ad_token_provider"] = _azure_token_provider()
        return AzureOpenAIEmbeddings(**azure_kwargs)
    return OpenAIEmbeddings(model=deployment_or_model)

# Load prompt files
_PROMPT_DIR = Path(__file__).parent

_SLM_PROMPT_PATH = _PROMPT_DIR / "slm-prompt.txt"
SLM_SYSTEM_PROMPT = _SLM_PROMPT_PATH.read_text(encoding="utf-8") if _SLM_PROMPT_PATH.exists() else ""

_LLM_RAW_PROMPT_PATH = _PROMPT_DIR / "llm-prompt-raw.txt"
LLM_RAW_PROMPT = _LLM_RAW_PROMPT_PATH.read_text(encoding="utf-8") if _LLM_RAW_PROMPT_PATH.exists() else ""

_LLM_ENRICHED_PROMPT_PATH = _PROMPT_DIR / "llm-prompt-enriched.txt"
LLM_ENRICHED_PROMPT = _LLM_ENRICHED_PROMPT_PATH.read_text(encoding="utf-8") if _LLM_ENRICHED_PROMPT_PATH.exists() else ""

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
    heatmap_path: str                                          # path to heatmap PNG
    audit_report_path: str                                     # path to HTML audit report


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
# 4. Helpers: Pre-extract footnote definitions & page-aware batching
# ---------------------------------------------------------------------------
_FOOTNOTE_DEF_RE = re.compile(
    r"^\[(\d+)\]\s+(.+?)(?=\n\[\d+\]|\nPage \d+/|\nCONFIDENTIAL|\Z)",
    re.MULTILINE | re.DOTALL,
)


def _extract_global_footnote_defs(raw_text: str) -> dict[int, str]:
    """
    Pre-scan *raw_text* for every footnote definition line (``[N] <text>``
    appearing at the start of a line) and return ``{marker_int: full_text}``.
    Definitions that span multiple lines are captured correctly.
    """
    defs: dict[int, str] = {}
    for m in _FOOTNOTE_DEF_RE.finditer(raw_text):
        marker = int(m.group(1))
        text = " ".join(m.group(2).split())  # normalise whitespace
        # Keep the longer definition if a marker appears more than once
        if marker not in defs or len(text) > len(defs[marker]):
            defs[marker] = text
    return defs


def _page_aware_sections(raw_text: str, max_size: int = 4500) -> list[str]:
    """
    Split *raw_text* on ``Page N/M`` markers so that every page's body
    text AND its footnote definitions stay together in the same batch.

    Adjacent pages are merged as long as the combined size stays under
    *max_size* characters, keeping the number of SLM calls reasonable.
    """
    # Split at the boundary *after* each "Page N/M" marker
    parts = re.split(r"(Page \d+/\d+)", raw_text)
    # Re-assemble so each element = page content + its "Page N/M" trailer
    pages: list[str] = []
    buf = ""
    for part in parts:
        buf += part
        if re.fullmatch(r"Page \d+/\d+", part):
            pages.append(buf)
            buf = ""
    if buf.strip():
        pages.append(buf)

    # Merge small consecutive pages into batches up to max_size
    sections: list[str] = []
    current = ""
    for page in pages:
        if current and len(current) + len(page) > max_size:
            sections.append(current)
            current = page
        else:
            current += page
    if current.strip():
        sections.append(current)

    return sections


def _inject_footnote_appendix(
    section: str, global_defs: dict[int, str]
) -> str:
    """
    Append a *Footnote Reference Appendix* to *section* listing the
    full definitions of every ``[N]`` marker referenced in the section
    body.  This ensures the SLM always has the definition available even
    when batching splits references from their definitions.
    """
    # Find all [N] markers in the section text
    markers_in_section = sorted(set(int(m) for m in re.findall(r"\[(\d+)\]", section)))
    if not markers_in_section:
        return section

    appendix_lines = []
    for marker in markers_in_section:
        if marker in global_defs:
            appendix_lines.append(f"[{marker}] {global_defs[marker]}")

    if not appendix_lines:
        return section

    appendix = "\n\n--- FOOTNOTE DEFINITIONS (for reference) ---\n" + "\n".join(appendix_lines)
    return section + appendix


# ---------------------------------------------------------------------------
# 4. Node: SLM Footnote Stitcher (the "Librarian")
# ---------------------------------------------------------------------------
def slm_footnote_stitcher(state: GraphState) -> dict:
    """
    Call the SLM to identify footnote markers in the raw text and inline
    the corresponding footnote definitions next to the citing sentence.

    Strategy:
    1. Pre-extract a global footnote-definitions dictionary from *raw_text*.
    2. Split the document on page boundaries (``Page N/M`` markers) so
       body text and its footnote definitions stay in the same batch.
    3. Inject a reference appendix into each batch so the SLM has access
       to any cross-page definitions.
    4. De-duplicate results preferring real content over MISSING markers,
       and longer text over truncated entries.
    5. Post-validate: any footnote still MISSING or truncated is back-
       filled from the pre-extracted definitions.
    """
    slm = _make_chat(SLM_MODEL, max_tokens=8192)
    raw_text = state["raw_text"]

    # --- Step 1: Pre-extract global footnote definitions ---
    global_defs = _extract_global_footnote_defs(raw_text)
    print(f"[slm_footnote_stitcher] Pre-extracted {len(global_defs)} footnote definitions from raw text")

    # --- Step 2: Page-aware batching ---
    SLM_BATCH_SIZE = 4500  # generous per-batch limit

    if len(raw_text) <= SLM_BATCH_SIZE * 1.5:
        # Small document — single pass
        sections = [raw_text]
    else:
        sections = _page_aware_sections(raw_text, max_size=SLM_BATCH_SIZE)
        print(f"[slm_footnote_stitcher] Document split into {len(sections)} page-aware sections")

    # --- Step 3: Process each batch with injected appendix ---
    healed_sections = []
    for i, section in enumerate(sections):
        enriched_section = _inject_footnote_appendix(section, global_defs)
        messages = [
            {"role": "system", "content": SLM_SYSTEM_PROMPT},
            {"role": "user", "content": f"Source_Text:\n\n{enriched_section}"},
        ]
        response = slm.invoke(messages)
        healed_sections.append(response.content.strip())
        if len(sections) > 1:
            print(f"  [slm_footnote_stitcher] Processed section {i+1}/{len(sections)}")

    healed_text = "\n\n".join(healed_sections)

    # --- Step 4: Extract + smart de-duplicate footnote registry ---
    footnote_pattern = re.compile(
        r"\{FOOTNOTE\s*\[(\d+)\]\s*:\s*(.+?)\}", re.DOTALL
    )
    footnotes = [
        {"marker": int(m.group(1)), "text": m.group(2).strip(), "status": "linked"}
        for m in footnote_pattern.finditer(healed_text)
    ]

    registry: dict[int, dict] = {}
    for fn in footnotes:
        marker = fn["marker"]
        is_missing = "MISSING" in fn["text"].upper()
        existing = registry.get(marker)
        if existing is None:
            registry[marker] = fn
        elif "MISSING" in existing["text"].upper() and not is_missing:
            # Prefer real content over MISSING
            registry[marker] = fn
        elif not is_missing and len(fn["text"]) > len(existing["text"]):
            # Prefer longer (more complete) text
            registry[marker] = fn

    # --- Step 5: Post-validation backfill from global defs ---
    backfilled = 0
    for marker, defn_text in global_defs.items():
        entry = registry.get(marker)
        if entry is None:
            # Not discovered by SLM at all — backfill
            registry[marker] = {
                "marker": marker,
                "text": defn_text,
                "status": "backfilled",
            }
            backfilled += 1
        elif "MISSING" in entry["text"].upper():
            # SLM marked it MISSING but we have the definition
            registry[marker] = {
                "marker": marker,
                "text": defn_text,
                "status": "backfilled",
            }
            backfilled += 1
            # Also patch the healed text so downstream sees the real content
            healed_text = re.sub(
                rf"\{{FOOTNOTE\s*\[{marker}\]\s*:\s*MISSING[^}}]*\}}",
                f"{{FOOTNOTE [{marker}]: {defn_text}}}",
                healed_text,
                count=0,
            )
        elif len(entry["text"]) < len(defn_text) * 0.6:
            # Truncated — the SLM text is much shorter than the definition
            registry[marker] = {
                "marker": marker,
                "text": defn_text,
                "status": "backfilled",
            }
            backfilled += 1

    unique_footnotes = sorted(registry.values(), key=lambda fn: fn["marker"])

    if backfilled:
        print(f"[slm_footnote_stitcher] Backfilled {backfilled} footnotes from pre-extracted definitions")
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
# Multi-query retrieval helper
# ---------------------------------------------------------------------------
def _multi_query_retrieve(vectorstore, k_per_query: int = TOP_K) -> list[Document]:
    """Run multiple topical queries against *vectorstore* and deduplicate."""
    seen: set[str] = set()
    results: list[Document] = []
    for query in RETRIEVAL_QUERIES:
        for doc in vectorstore.similarity_search(query, k=k_per_query):
            key = doc.page_content[:200]  # first 200 chars as identity key
            if key not in seen:
                seen.add(key)
                results.append(doc)
    print(
        f"[multi_query_retrieve] {len(RETRIEVAL_QUERIES)} queries × k={k_per_query}"
        f" → {len(results)} unique chunks"
    )
    return results


# ---------------------------------------------------------------------------
# 6. Node: Build FAISS Vector Stores & Summarize (Raw — baseline)
# ---------------------------------------------------------------------------
def summarize_raw(state: GraphState) -> dict:
    """
    Build a FAISS index from raw (non-stitched) chunks, retrieve the
    most relevant ones, and ask the LLM for a summary — baseline mode.
    """
    embeddings = _make_embeddings(EMBEDDING_MODEL)
    docs = [Document(page_content=c, metadata={"has_footnote": False}) for c in state["raw_chunks"]]
    vectorstore = FAISS.from_documents(docs, embeddings)

    retrieved = _multi_query_retrieve(vectorstore)
    context = "\n\n---\n\n".join(doc.page_content for doc in retrieved)

    llm = _make_chat(LLM_MODEL, max_tokens=2048)
    prompt = LLM_RAW_PROMPT.replace("{context}", context)
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
    Falls back to raw chunks if the SLM produced no enriched chunks.
    """
    chunks = state["enriched_chunks"] if state["enriched_chunks"] else state["raw_chunks"]
    if not chunks:
        print("[summarize_enriched] No chunks available — skipping")
        return {"enriched_summary": "(no enriched summary — no chunks available)"}

    embeddings = _make_embeddings(EMBEDDING_MODEL)
    docs = [
        Document(
            page_content=c,
            metadata={"has_footnote": bool(re.search(r"\{FOOTNOTE", c))},
        )
        for c in chunks
    ]
    vectorstore = FAISS.from_documents(docs, embeddings)

    retrieved = _multi_query_retrieve(vectorstore)
    context = "\n\n---\n\n".join(doc.page_content for doc in retrieved)

    llm = _make_chat(LLM_MODEL, max_tokens=2048)
    prompt = LLM_ENRICHED_PROMPT.replace("{context}", context)
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
    ts_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_name = f"summary_report_{Path(state['source_file']).stem}_{ts_tag}.md"
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
    | **Retrieval** | Multi-query ({len(RETRIEVAL_QUERIES)} sub-queries × k={TOP_K}) |

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

    - **Revenue composition** — Does the summary flag one-time items or acquisition effects?
    - **Forward guidance** — Does it note conditions, risks, or contingencies in the footnotes?
    - **Reported metrics** — Does it surface GAAP vs. non-GAAP discrepancies?
    - **Cash flow & liquidity** — Does it include capex context and debt detail?
    - **Operational highlights** — Does it cover market position and competitive landscape?

    > **Tip — HTML Audit Report colour coding:**
    > Open the companion `audit_report_*.html` for a visual, sentence-level
    > semantic diff.  Sentences with an **amber left-border** appear only in
    > the baseline summary (information lost or absent in the enriched version).
    > Sentences with a **green left-border** appear only in the enriched
    > summary (new insights surfaced by footnote stitching).  Sentences with
    > no border are semantically shared by both summaries.

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
# 9. Node: Generate Heatmap & Interactive Audit Report
# ---------------------------------------------------------------------------
def generate_audit(state: GraphState) -> dict:
    """Generate the retrieval heatmap PNG and interactive HTML audit report."""
    source_path = Path(state["source_file"])
    output_dir = source_path.parent
    stem = source_path.stem
    ts_tag = datetime.now().strftime("%Y%m%d_%H%M%S")

    # --- Heatmap ---
    heatmap_file = output_dir / f"heatmap_{stem}_{ts_tag}.png"
    heatmap_path = generate_heatmap(
        raw_chunks=state["raw_chunks"],
        enriched_chunks=state["enriched_chunks"],
        output_path=heatmap_file,
        source_name=source_path.name,
    )

    # --- Interactive HTML audit report ---
    audit_file = output_dir / f"audit_report_{stem}_{ts_tag}.html"
    audit_path = generate_audit_report(
        raw_text=state["raw_text"],
        enriched_text=state["enriched_text"],
        raw_chunks=state["raw_chunks"],
        enriched_chunks=state["enriched_chunks"],
        footnotes_registry=state.get("footnotes_registry", []),
        raw_summary=state.get("raw_summary", ""),
        enriched_summary=state.get("enriched_summary", ""),
        heatmap_path=heatmap_path,
        output_path=audit_file,
        source_name=source_path.name,
        slm_model=SLM_MODEL,
        llm_model=LLM_MODEL,
        embeddings_model=_make_embeddings(EMBEDDING_MODEL),
    )

    return {"heatmap_path": heatmap_path, "audit_report_path": audit_path}


# ---------------------------------------------------------------------------
# 10. Build the LangGraph Workflow
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
workflow.add_node("generate_audit", generate_audit)

# Define edges (sequential pipeline)
workflow.add_edge(START, "load_document")
workflow.add_edge("load_document", "naive_chunker")
workflow.add_edge("naive_chunker", "slm_footnote_stitcher")
workflow.add_edge("slm_footnote_stitcher", "enriched_chunker")
workflow.add_edge("enriched_chunker", "summarize_raw")
workflow.add_edge("summarize_raw", "summarize_enriched")
workflow.add_edge("summarize_enriched", "generate_report")
workflow.add_edge("generate_report", "generate_audit")
workflow.add_edge("generate_audit", END)

# Compile
app = workflow.compile()


# ---------------------------------------------------------------------------
# 11. State Serialization Helpers
# ---------------------------------------------------------------------------
_STATE_SERIALIZABLE_KEYS = [
    "source_file", "raw_text", "enriched_text", "footnotes_registry",
    "raw_chunks", "enriched_chunks", "raw_summary", "enriched_summary",
    "report_path", "heatmap_path", "audit_report_path",
]


def _save_state(state: dict, output_dir: Path, stem: str, ts_tag: str) -> str:
    """Persist pipeline state to a JSON file for later re-rendering."""
    data = {k: state.get(k, "") for k in _STATE_SERIALIZABLE_KEYS}
    state_file = output_dir / f"state_{stem}_{ts_tag}.json"
    state_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[save_state] Saved pipeline state to {state_file}")
    return str(state_file)


def _load_state(state_path: Path) -> dict:
    """Load a previously saved pipeline state from JSON."""
    data = json.loads(state_path.read_text(encoding="utf-8"))
    return data


def _rerender(state: dict) -> None:
    """Re-generate only the report, heatmap, and audit HTML from saved state."""
    # Re-run generate_report
    report_result = generate_report(state)
    state.update(report_result)

    # Re-run generate_audit
    audit_result = generate_audit(state)
    state.update(audit_result)

    # Save updated state
    source_path = Path(state["source_file"])
    ts_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
    _save_state(state, source_path.parent, source_path.stem, ts_tag)


# ---------------------------------------------------------------------------
# 12. CLI Entry Point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # --rerender mode: regenerate outputs from saved state JSON
    if len(sys.argv) > 1 and sys.argv[1] == "--rerender":
        if len(sys.argv) < 3:
            print("Usage: python src/LangGraph_Footnote_RAG_Advanced.py --rerender <state.json>")
            sys.exit(1)
        state_path = Path(sys.argv[2])
        if not state_path.is_absolute():
            state_path = _PROJECT_ROOT / state_path
        if not state_path.exists():
            print(f"Error: State file not found — {state_path}")
            sys.exit(1)

        print("=" * 60)
        print("  Footnote-Aware RAG Pipeline — Re-render Mode")
        print(f"  State: {state_path.name}")
        print("=" * 60)

        saved = _load_state(state_path)
        _rerender(saved)

        print("\n" + "=" * 60)
        print("  Re-render complete!")
        print(f"  Report:       {saved['report_path']}")
        print(f"  Heatmap:      {saved['heatmap_path']}")
        print(f"  Audit Report: {saved['audit_report_path']}")
        print(f"  Footnotes:    {len(saved.get('footnotes_registry', []))}")
        print("=" * 60)
        sys.exit(0)

    # Normal mode: full pipeline run
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
        "heatmap_path": "",
        "audit_report_path": "",
    }

    result = app.invoke(initial_state)

    # Save state for future re-rendering
    ts_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
    state_file = _save_state(result, input_path.parent, input_path.stem, ts_tag)

    print("\n" + "=" * 60)
    print("  Pipeline complete!")
    print(f"  Report:       {result['report_path']}")
    print(f"  Heatmap:      {result['heatmap_path']}")
    print(f"  Audit Report: {result['audit_report_path']}")
    print(f"  State:        {state_file}")
    print(f"  Footnotes found: {len(result['footnotes_registry'])}")
    print("=" * 60)
    print(f"\n  To re-render outputs without re-running the pipeline:")
    print(f"  python3 src/LangGraph_Footnote_RAG_Advanced.py --rerender {state_file}")
