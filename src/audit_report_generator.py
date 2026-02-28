"""
Interactive Audit Report Generator
===================================
Generates a self-contained HTML report that highlights exactly where
footnotes were "stitched" into the main text by the SLM pre-processor.

Features:
  - Side-by-side raw vs enriched text with syntax highlighting
  - Semantic diff: sentences with novel meaning are color-coded
  - Inline footnote annotations highlighted in color
  - Chunk boundary visualization
  - Footnote completeness scorecard
  - Embedded heatmap image (base64)
"""

import base64
import html
import math
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional


# ---------------------------------------------------------------------------
# Sentence splitting helper
# ---------------------------------------------------------------------------
_SENTENCE_RE = re.compile(
    r"(?<=[.!?;])\s+(?=[A-Z\"\u201c(])"
    r"|(?<=\n)\s*"
)


def _split_sentences(text: str) -> list[str]:
    """Split *text* into sentence-like segments for semantic comparison."""
    parts = _SENTENCE_RE.split(text.strip())
    merged: list[str] = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if merged and len(p) < 30:
            merged[-1] = merged[-1] + " " + p
        else:
            merged.append(p)
    return merged


# ---------------------------------------------------------------------------
# Cosine similarity (pure-Python, no numpy dependency)
# ---------------------------------------------------------------------------
def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


# ---------------------------------------------------------------------------
# Semantic diff: classify each sentence as "shared" or "novel"
# ---------------------------------------------------------------------------
def _compute_semantic_diff(
    sentences_a: list[str],
    sentences_b: list[str],
    embeddings_model,
    threshold: float = 0.82,
) -> tuple[list[bool], list[bool]]:
    """
    Embed both sentence lists and return boolean masks indicating which
    sentences are **novel** (no close semantic match on the other side).

    Returns:
        (novel_a, novel_b) \u2014 True means that sentence is semantically
        different from anything in the other summary.
    """
    all_texts = sentences_a + sentences_b
    if not all_texts:
        return [], []

    vecs = embeddings_model.embed_documents(all_texts)
    vecs_a = vecs[: len(sentences_a)]
    vecs_b = vecs[len(sentences_a) :]

    def _max_sim(vec: list[float], targets: list[list[float]]) -> float:
        if not targets:
            return 0.0
        return max(_cosine_similarity(vec, t) for t in targets)

    novel_a = [_max_sim(v, vecs_b) < threshold for v in vecs_a]
    novel_b = [_max_sim(v, vecs_a) < threshold for v in vecs_b]
    return novel_a, novel_b


# ---------------------------------------------------------------------------
# Apply highlights to markdown-converted HTML
# ---------------------------------------------------------------------------
def _apply_semantic_highlights(
    md_html: str,
    original_text: str,
    novel_mask: list[bool],
    sentences: list[str],
    css_class: str,
) -> str:
    """
    Find each *novel* sentence inside the rendered *md_html* and wrap it
    in a ``<span class="css_class">`` so it gets a colored left-border.
    """
    result = md_html
    for sent, is_novel in zip(sentences, novel_mask):
        if not is_novel:
            continue
        # Take a distinctive fragment (first 80 chars, HTML-escaped)
        fragment = html.escape(sent[:80])
        # Also handle **bold** \u2192 <strong>bold</strong> already applied
        fragment_bold = re.sub(
            r"\*\*(.+?)\*\*", r"<strong>\1</strong>", fragment
        )
        for needle in (fragment_bold, fragment):
            idx = result.find(needle)
            if idx != -1:
                end_idx = idx + len(needle)
                rest = result[end_idx:]
                m_end = re.search(r"(?<=[.!?])\s|</(?:p|li|h\d)>", rest)
                if m_end:
                    end_idx += m_end.start()
                span_open = f'<span class="{css_class}">'
                span_close = "</span>"
                result = (
                    result[:idx]
                    + span_open
                    + result[idx:end_idx]
                    + span_close
                    + result[end_idx:]
                )
                break
    return result


def _highlight_footnotes_html(text: str) -> str:
    """Convert {FOOTNOTE [n]: ...} blocks into styled HTML spans."""
    escaped = html.escape(text)
    # Highlight inline footnotes green
    escaped = re.sub(
        r"\{FOOTNOTE\s*\[(\d+)\]\s*:\s*(.+?)\}",
        r'<span class="fn-inline" title="Footnote [\1]">'
        r'<span class="fn-marker">[\1]</span> \2</span>',
        escaped,
        flags=re.DOTALL,
    )
    # Highlight bare [n] refs amber
    escaped = re.sub(
        r"(?<!</span>)\[(\d+)\](?!</span>)",
        r'<span class="fn-ref">[\1]</span>',
        escaped,
    )
    return escaped


def _md_to_html(text: str) -> str:
    """Lightweight Markdown-to-HTML converter for LLM summary output.

    Handles: **bold**, headings (## / ###), bullet lists (- ),
    numbered lists (1. ), blank-line paragraph breaks, and
    inline `code`.  Does NOT depend on any external library.
    """
    escaped = html.escape(text)
    lines = escaped.splitlines()
    out: list[str] = []
    in_ul = False
    in_ol = False

    def _close_lists() -> None:
        nonlocal in_ul, in_ol
        if in_ul:
            out.append("</ul>")
            in_ul = False
        if in_ol:
            out.append("</ol>")
            in_ol = False

    for line in lines:
        stripped = line.strip()

        # Blank line → close any open list, add paragraph break
        if not stripped:
            _close_lists()
            out.append("<br>")
            continue

        # Headings
        m_h = re.match(r"^(#{1,4})\s+(.*)", stripped)
        if m_h:
            _close_lists()
            level = len(m_h.group(1)) + 1  # ## → <h3>, ### → <h4>
            level = min(level, 6)
            out.append(f"<h{level} style='margin:0.6em 0 0.3em'>{m_h.group(2)}</h{level}>")
            continue

        # Unordered list item
        m_ul = re.match(r"^[-*]\s+(.*)", stripped)
        if m_ul:
            if not in_ul:
                _close_lists()
                out.append("<ul style='margin:0.3em 0;padding-left:1.4em'>")
                in_ul = True
            out.append(f"<li>{m_ul.group(1)}</li>")
            continue

        # Ordered list item
        m_ol = re.match(r"^\d+\.\s+(.*)", stripped)
        if m_ol:
            if not in_ol:
                _close_lists()
                out.append("<ol style='margin:0.3em 0;padding-left:1.4em'>")
                in_ol = True
            out.append(f"<li>{m_ol.group(1)}</li>")
            continue

        # Regular paragraph line
        _close_lists()
        out.append(f"<p style='margin:0.3em 0'>{stripped}</p>")

    _close_lists()
    result = "\n".join(out)

    # Inline formatting
    result = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", result)
    result = re.sub(r"`([^`]+)`",
                    r"<code style='background:#e5e7eb;padding:0.1em 0.3em;"
                    r"border-radius:3px;font-size:0.9em'>\1</code>", result)

    return result


def _chunk_to_html(chunks: List[str], mode: str) -> str:
    """Render a list of chunks as styled HTML blocks."""
    blocks = []
    for i, chunk in enumerate(chunks):
        css_class = "chunk-enriched" if mode == "enriched" else "chunk-raw"
        has_fn = bool(re.search(r"\{FOOTNOTE", chunk)) if mode == "enriched" else False
        badge = '<span class="badge badge-green">STITCHED</span>' if has_fn else ""
        content = _highlight_footnotes_html(chunk) if mode == "enriched" else html.escape(chunk)

        # Check for bare refs in raw mode
        if mode == "raw" and re.search(r"\[\d+\]", chunk):
            badge = '<span class="badge badge-amber">HAS REF</span>'
            content = re.sub(
                r"\[(\d+)\]",
                r'<span class="fn-ref">[\1]</span>',
                html.escape(chunk),
            )

        blocks.append(
            f'<div class="{css_class}">'
            f'<div class="chunk-header">Chunk {i+1} {badge}</div>'
            f'<div class="chunk-body">{content}</div>'
            f"</div>"
        )
    return "\n".join(blocks)


def generate_audit_report(
    raw_text: str,
    enriched_text: str,
    raw_chunks: List[str],
    enriched_chunks: List[str],
    footnotes_registry: List[dict],
    raw_summary: str,
    enriched_summary: str,
    heatmap_path: str | None,
    output_path,
    source_name: str = "Document",
    slm_model: str = "",
    llm_model: str = "",
    embeddings_model=None,
) -> str:
    """
    Generate a self-contained interactive HTML audit report.

    Returns:
        Absolute path to the generated HTML file.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Embed heatmap as base64 if available
    heatmap_html = ""
    if heatmap_path and Path(heatmap_path).exists():
        img_data = Path(heatmap_path).read_bytes()
        b64 = base64.b64encode(img_data).decode("utf-8")
        heatmap_html = f'<img src="data:image/png;base64,{b64}" alt="Retrieval Heatmap" class="heatmap-img">'

    # Footnote scorecard
    total_fn = len(footnotes_registry)
    linked = sum(1 for fn in footnotes_registry if fn.get("status") == "linked")
    score_pct = int((linked / total_fn * 100) if total_fn > 0 else 0)
    score_color = "#22c55e" if score_pct == 100 else "#f59e0b" if score_pct >= 50 else "#ef4444"

    fn_table_rows = ""
    for fn in footnotes_registry:
        status_icon = "&#10003;" if fn.get("status") == "linked" else "&#10007;"
        status_class = "status-ok" if fn.get("status") == "linked" else "status-fail"
        fn_table_rows += (
            f'<tr><td>[{fn["marker"]}]</td>'
            f'<td>{html.escape(fn.get("text", "N/A"))}</td>'
            f'<td class="{status_class}">{status_icon} {fn.get("status", "unknown")}</td></tr>'
        )

    # --- Semantic diff of summaries ---
    raw_diff_html = _md_to_html(raw_summary)
    enriched_diff_html = _md_to_html(enriched_summary)
    diff_legend = ""

    if embeddings_model and raw_summary and enriched_summary:
        try:
            raw_sents = _split_sentences(raw_summary)
            enr_sents = _split_sentences(enriched_summary)
            novel_raw, novel_enr = _compute_semantic_diff(
                raw_sents, enr_sents, embeddings_model
            )
            raw_diff_html = _apply_semantic_highlights(
                raw_diff_html, raw_summary, novel_raw, raw_sents, "sem-diff-baseline"
            )
            enriched_diff_html = _apply_semantic_highlights(
                enriched_diff_html, enriched_summary, novel_enr, enr_sents, "sem-diff-enriched"
            )
            n_raw = sum(novel_raw)
            n_enr = sum(novel_enr)
            diff_legend = (
                f'<div style="margin-top:1rem;font-size:0.85rem;color:var(--gray);'
                f'line-height:1.7">'
                f'<strong>Semantic Diff Legend</strong><br>'
                f'<span class="sem-diff-baseline" style="padding:2px 6px">'
                f"Amber border</span> = claim appears <em>only</em> in baseline — "
                f"information not surfaced by footnote stitching ({n_raw} sentences)<br>"
                f'<span class="sem-diff-enriched" style="padding:2px 6px">'
                f"Green border</span> = insight appears <em>only</em> in enriched — "
                f"new context added by footnote stitching ({n_enr} sentences)<br>"
                f"No border = semantically shared by both summaries</div>"
            )
            print(f"[audit_report] Semantic diff: {n_raw} novel baseline, {n_enr} novel enriched sentences")
        except Exception as e:
            print(f"[audit_report] Semantic diff skipped: {e}")

    raw_chunks_html = _chunk_to_html(raw_chunks, "raw")
    enriched_chunks_html = _chunk_to_html(enriched_chunks, "enriched")

    report_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Footnote RAG Audit Report \u2014 {html.escape(source_name)}</title>
<style>
  :root {{
    --green: #22c55e; --red: #ef4444; --amber: #f59e0b;
    --blue: #3b82f6; --gray: #6b7280; --bg: #f9fafb;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
         background: var(--bg); color: #1f2937; line-height: 1.6; }}
  .container {{ max-width: 1400px; margin: 0 auto; padding: 2rem; }}
  header {{ background: linear-gradient(135deg, #1e3a5f, #2563eb); color: white;
           padding: 2rem; border-radius: 12px; margin-bottom: 2rem; }}
  header h1 {{ font-size: 1.8rem; margin-bottom: 0.5rem; }}
  header .meta {{ opacity: 0.85; font-size: 0.9rem; }}
  .scorecard {{ display: flex; gap: 1.5rem; margin-bottom: 2rem; flex-wrap: wrap; }}
  .score-card {{ background: white; border-radius: 10px; padding: 1.5rem;
                flex: 1; min-width: 200px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                border-left: 4px solid var(--blue); }}
  .score-card h3 {{ font-size: 0.85rem; color: var(--gray); text-transform: uppercase;
                   letter-spacing: 0.05em; margin-bottom: 0.5rem; }}
  .score-card .value {{ font-size: 2rem; font-weight: 700; }}
  .section {{ background: white; border-radius: 10px; padding: 1.5rem;
             margin-bottom: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
  .section h2 {{ font-size: 1.3rem; margin-bottom: 1rem; padding-bottom: 0.5rem;
                border-bottom: 2px solid #e5e7eb; }}
  .heatmap-img {{ width: 100%; border-radius: 8px; margin-top: 1rem; }}
  .columns {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; }}
  @media (max-width: 900px) {{ .columns {{ grid-template-columns: 1fr; }} }}
  .chunk-raw, .chunk-enriched {{ border-radius: 8px; padding: 1rem; margin-bottom: 0.75rem;
                                font-family: 'Cascadia Code', 'Fira Code', monospace;
                                font-size: 0.82rem; white-space: pre-wrap;
                                word-wrap: break-word; }}
  .chunk-raw {{ background: #fef3c7; border: 1px solid #f59e0b; }}
  .chunk-enriched {{ background: #dcfce7; border: 1px solid #22c55e; }}
  .chunk-header {{ font-weight: 700; margin-bottom: 0.5rem; font-family: 'Segoe UI', sans-serif;
                  font-size: 0.85rem; color: var(--gray); }}
  .chunk-body {{ line-height: 1.5; }}
  .fn-inline {{ background: #bbf7d0; padding: 2px 6px; border-radius: 4px;
               border: 1px solid #86efac; font-weight: 500; }}
  .fn-marker {{ background: var(--blue); color: white; padding: 1px 5px;
               border-radius: 3px; font-weight: 700; font-size: 0.8em; }}
  .fn-ref {{ background: #fde68a; padding: 1px 4px; border-radius: 3px;
            font-weight: 700; color: #92400e; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 10px;
           font-size: 0.7rem; font-weight: 700; text-transform: uppercase;
           letter-spacing: 0.05em; margin-left: 0.5rem; }}
  .badge-green {{ background: #dcfce7; color: #166534; }}
  .badge-amber {{ background: #fef3c7; color: #92400e; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; }}
  th, td {{ padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid #e5e7eb; }}
  th {{ background: #f3f4f6; font-size: 0.85rem; text-transform: uppercase;
      letter-spacing: 0.05em; color: var(--gray); }}
  .status-ok {{ color: var(--green); font-weight: 700; }}
  .status-fail {{ color: var(--red); font-weight: 700; }}
  .summary-box {{ background: #f3f4f6; border-radius: 8px; padding: 1.25rem;
                 margin-top: 1rem; line-height: 1.7; }}
  .sem-diff-baseline {{ border-left: 3px solid #f59e0b; background: #fffbeb;
                        padding: 2px 6px; display: inline; }}
  .sem-diff-enriched {{ border-left: 3px solid #22c55e; background: #f0fdf4;
                        padding: 2px 6px; display: inline; }}
  .tab-container {{ display: flex; gap: 0; margin-bottom: 0; }}
  .tab {{ padding: 0.75rem 1.5rem; cursor: pointer; background: #e5e7eb;
         border: none; font-weight: 600; font-size: 0.9rem; border-radius: 8px 8px 0 0;
         color: var(--gray); transition: all 0.2s; }}
  .tab.active {{ background: white; color: #1f2937; box-shadow: 0 -2px 4px rgba(0,0,0,0.05); }}
  .tab-panel {{ display: none; }}
  .tab-panel.active {{ display: block; }}
  footer {{ text-align: center; padding: 2rem; color: var(--gray); font-size: 0.85rem; }}
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>Footnote RAG Audit Report</h1>
    <div class="meta">
      Source: <strong>{html.escape(source_name)}</strong> &nbsp;|&nbsp;
      Generated: {timestamp} &nbsp;|&nbsp;
      SLM: {html.escape(slm_model)} &nbsp;|&nbsp;
      LLM: {html.escape(llm_model)}
    </div>
  </header>

  <!-- Scorecard -->
  <div class="scorecard">
    <div class="score-card">
      <h3>Footnotes Found</h3>
      <div class="value">{total_fn}</div>
    </div>
    <div class="score-card">
      <h3>Successfully Linked</h3>
      <div class="value" style="color: {score_color}">{linked}/{total_fn}</div>
    </div>
    <div class="score-card">
      <h3>Completeness Score</h3>
      <div class="value" style="color: {score_color}">{score_pct}%</div>
    </div>
    <div class="score-card">
      <h3>Raw Chunks</h3>
      <div class="value">{len(raw_chunks)}</div>
    </div>
    <div class="score-card">
      <h3>Enriched Chunks</h3>
      <div class="value">{len(enriched_chunks)}</div>
    </div>
  </div>

  <!-- Heatmap -->
  <div class="section">
    <h2>Retrieval Heatmap</h2>
    <p>Color-coded map showing which chunks contain footnote context.
       <strong style="color:#ef4444">Red/Amber</strong> = blind spots in standard RAG.
       <strong style="color:#22c55e">Green</strong> = SLM-stitched.
       <strong style="color:#3b82f6">Blue diamonds</strong> = recovered footnotes.</p>
    {heatmap_html if heatmap_html else '<p style="color:#9ca3af"><em>Heatmap not available</em></p>'}
  </div>

  <!-- Summaries -->
  <div class="section">
    <h2>Summary Comparison</h2>
    <div class="columns">
      <div>
        <h3 style="color:var(--amber)">Baseline (Without SLM)</h3>
        <div class="summary-box">{raw_diff_html}</div>
      </div>
      <div>
        <h3 style="color:var(--green)">Enriched (With SLM)</h3>
        <div class="summary-box">{enriched_diff_html}</div>
      </div>
    </div>
    {diff_legend}
  </div>

  <!-- Chunk Inspector -->
  <div class="section">
    <h2>Chunk Inspector</h2>
    <div class="tab-container">
      <button class="tab active" onclick="switchTab(event, 'raw-panel')">Raw Chunks</button>
      <button class="tab" onclick="switchTab(event, 'enriched-panel')">Enriched Chunks</button>
    </div>
    <div id="raw-panel" class="tab-panel active" style="background:white;padding:1rem;border-radius:0 0 8px 8px;">
      {raw_chunks_html}
    </div>
    <div id="enriched-panel" class="tab-panel" style="background:white;padding:1rem;border-radius:0 0 8px 8px;">
      {enriched_chunks_html}
    </div>
  </div>

  <!-- Footnotes Table -->
  <div class="section">
    <h2>Footnote Registry</h2>
    <table>
      <thead><tr><th>Marker</th><th>Footnote Text</th><th>Status</th></tr></thead>
      <tbody>{fn_table_rows if fn_table_rows else '<tr><td colspan="3">No footnotes detected</td></tr>'}</tbody>
    </table>
  </div>

  <footer>
    Generated by <strong>Footnote-Aware RAG Pipeline</strong> &mdash;
    SLM Pre-processing + LangGraph + FAISS
  </footer>
</div>

<script>
function switchTab(e, panelId) {{
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  e.target.classList.add('active');
  document.getElementById(panelId).classList.add('active');
}}
</script>
</body>
</html>"""

    output = Path(output_path)
    output.write_text(report_html, encoding="utf-8")
    print(f"[audit_report] Saved interactive audit report to {output}")
    return str(output.resolve())
