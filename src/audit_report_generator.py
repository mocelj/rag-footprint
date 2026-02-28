"""
Interactive Audit Report Generator
===================================
Generates a self-contained HTML report that highlights exactly where
footnotes were "stitched" into the main text by the SLM pre-processor.

Features:
  - Side-by-side raw vs enriched text with syntax highlighting
  - Inline footnote annotations highlighted in color
  - Chunk boundary visualization
  - Footnote completeness scorecard
  - Embedded heatmap image (base64)
"""

import base64
import html
import re
from datetime import datetime
from pathlib import Path
from typing import List


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

  <- LivePlatformView.tsx: nodeStyle uses var(--surface); edge labelBgStyle uses Scorecard -->
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

  <- LivePlatformView.tsx: nodeStyle uses var(--surface); edge labelBgStyle uses Heatmap -->
  <div class="section">
    <h2>Retrieval Heatmap</h2>
    <p>Color-coded map showing which chunks contain footnote context.
       <strong style="color:#ef4444">Red/Amber</strong> = blind spots in standard RAG.
       <strong style="color:#22c55e">Green</strong> = SLM-stitched.
       <strong style="color:#3b82f6">Blue diamonds</strong> = recovered footnotes.</p>
    {heatmap_html if heatmap_html else '<p style="color:#9ca3af"><em>Heatmap not available</em></p>'}
  </div>

  <- LivePlatformView.tsx: nodeStyle uses var(--surface); edge labelBgStyle uses Summaries -->
  <div class="section">
    <h2>Summary Comparison</h2>
    <div class="columns">
      <div>
        <h3 style="color:var(--amber)">Baseline (Without SLM)</h3>
        <div class="summary-box">{html.escape(raw_summary)}</div>
      </div>
      <div>
        <h3 style="color:var(--green)">Enriched (With SLM)</h3>
        <div class="summary-box">{html.escape(enriched_summary)}</div>
      </div>
    </div>
  </div>

  <- LivePlatformView.tsx: nodeStyle uses var(--surface); edge labelBgStyle uses Chunk Inspector -->
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

  <- LivePlatformView.tsx: nodeStyle uses var(--surface); edge labelBgStyle uses Footnotes Table -->
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
