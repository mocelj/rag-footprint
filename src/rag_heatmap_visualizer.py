"""
RAG Heatmap Visualizer
=======================
Generates a color-coded "Retrieval Map" showing how footnotes were handled
across document chunks — comparing standard RAG (naive) vs SLM-Hybrid
(enriched) approaches.

Color coding:
  - Green: SLM successfully linked a footnote to its source paragraph
  - Red:   Standard RAG chunk with no footnote context (potential blind spot)
  - Blue:  Individual footnote markers recovered by the SLM-Hybrid system
"""

import re
from pathlib import Path
from typing import List

import matplotlib
matplotlib.use("Agg")  # non-interactive backend for headless environments
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import seaborn as sns


def _classify_chunks(
    raw_chunks: List[str],
    enriched_chunks: List[str],
) -> dict:
    """
    Analyze both chunk sets and build classification data for the heatmap.

    Returns a dict with:
      - raw_labels:      list of labels per raw chunk
      - enriched_labels: list of labels per enriched chunk
      - footnote_positions: list of (chunk_index, marker_number) for blue markers
    """
    footnote_ref_pattern = re.compile(r"\[\d+\]")
    footnote_inline_pattern = re.compile(r"\{FOOTNOTE\s*\[\d+\]")
    footnote_section_pattern = re.compile(r"FOOTNOTE|Notes:|NOTES:", re.IGNORECASE)

    # --- Classify raw chunks ---
    raw_labels = []
    for chunk in raw_chunks:
        if footnote_section_pattern.search(chunk):
            raw_labels.append("footnote_section")
        elif footnote_ref_pattern.search(chunk):
            raw_labels.append("has_footnote_ref")
        else:
            raw_labels.append("no_footnote")

    # --- Classify enriched chunks ---
    enriched_labels = []
    footnote_positions = []
    for i, chunk in enumerate(enriched_chunks):
        markers = footnote_inline_pattern.findall(chunk)
        if markers:
            enriched_labels.append("stitched")
            for m in re.finditer(r"\{FOOTNOTE\s*\[(\d+)\]", chunk):
                footnote_positions.append((i, int(m.group(1))))
        else:
            enriched_labels.append("no_footnote")

    return {
        "raw_labels": raw_labels,
        "enriched_labels": enriched_labels,
        "footnote_positions": footnote_positions,
    }


def _label_to_color(label: str, mode: str) -> float:
    """Map a chunk label to a numeric value for the heatmap colormap."""
    if mode == "raw":
        return {
            "no_footnote": 0.0,
            "has_footnote_ref": 0.4,
            "footnote_section": 0.8,
        }.get(label, 0.0)
    else:
        return {
            "no_footnote": 0.0,
            "stitched": 1.0,
        }.get(label, 0.0)


def generate_heatmap(
    raw_chunks: List[str],
    enriched_chunks: List[str],
    output_path,
    source_name: str = "Document",
) -> str:
    """
    Generate a side-by-side heatmap PNG comparing naive vs enriched chunk
    coverage.

    Returns:
        Absolute path to the generated PNG file.
    """
    classification = _classify_chunks(raw_chunks, enriched_chunks)

    cols = 5
    max_chunks = max(len(raw_chunks), len(enriched_chunks))
    rows = max(1, (max_chunks + cols - 1) // cols)

    # Build heatmap matrices
    raw_matrix = np.full((rows, cols), np.nan)
    for i, label in enumerate(classification["raw_labels"]):
        r, c = divmod(i, cols)
        raw_matrix[r, c] = _label_to_color(label, "raw")

    enriched_matrix = np.full((rows, cols), np.nan)
    for i, label in enumerate(classification["enriched_labels"]):
        r, c = divmod(i, cols)
        enriched_matrix[r, c] = _label_to_color(label, "enriched")

    # --- Plot ---
    sns.set_theme(style="whitegrid", font_scale=0.9)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, max(4, rows * 0.8 + 2)))
    fig.suptitle(f"Retrieval Heatmap \u2014 {source_name}", fontsize=14, fontweight="bold", y=0.98)

    raw_cmap = matplotlib.colors.LinearSegmentedColormap.from_list(
        "raw", ["#e0e0e0", "#f59e0b", "#ef4444"], N=256
    )
    enriched_cmap = matplotlib.colors.LinearSegmentedColormap.from_list(
        "enriched", ["#e0e0e0", "#22c55e"], N=256
    )

    # Raw heatmap (left)
    sns.heatmap(
        raw_matrix, ax=ax1, cmap=raw_cmap, vmin=0, vmax=1,
        cbar=False, linewidths=1.5, linecolor="white",
        xticklabels=False, yticklabels=False,
        mask=np.isnan(raw_matrix),
    )
    ax1.set_title("Standard RAG (Naive Chunks)", fontsize=11, pad=10)

    for i in range(len(raw_chunks)):
        r, c = divmod(i, cols)
        color = "white" if classification["raw_labels"][i] == "footnote_section" else "black"
        ax1.text(c + 0.5, r + 0.5, f"C{i+1}", ha="center", va="center",
                 fontsize=8, fontweight="bold", color=color)

    # Enriched heatmap (right)
    sns.heatmap(
        enriched_matrix, ax=ax2, cmap=enriched_cmap, vmin=0, vmax=1,
        cbar=False, linewidths=1.5, linecolor="white",
        xticklabels=False, yticklabels=False,
        mask=np.isnan(enriched_matrix),
    )
    ax2.set_title("SLM-Hybrid (Enriched Chunks)", fontsize=11, pad=10)

    for i in range(len(enriched_chunks)):
        r, c = divmod(i, cols)
        ax2.text(c + 0.5, r + 0.5, f"C{i+1}", ha="center", va="center",
                 fontsize=8, fontweight="bold",
                 color="white" if classification["enriched_labels"][i] == "stitched" else "black")

    # Blue footnote markers (diamonds)
    for chunk_idx, marker_num in classification["footnote_positions"]:
        r, c = divmod(chunk_idx, cols)
        ax2.plot(c + 0.85, r + 0.15, marker="D", markersize=7,
                 color="#3b82f6", markeredgecolor="white", markeredgewidth=0.8)
        ax2.text(c + 0.85, r + 0.15, str(marker_num), ha="center", va="center",
                 fontsize=5, fontweight="bold", color="white")

    # Legend
    legend_elements = [
        mpatches.Patch(facecolor="#e0e0e0", edgecolor="gray", label="No footnote content"),
        mpatches.Patch(facecolor="#f59e0b", edgecolor="gray", label="Has [n] ref but no context (naive)"),
        mpatches.Patch(facecolor="#ef4444", edgecolor="gray", label="Isolated footnote section (naive)"),
        mpatches.Patch(facecolor="#22c55e", edgecolor="gray", label="Footnote stitched in-place (SLM)"),
        plt.Line2D([0], [0], marker="D", color="w", markerfacecolor="#3b82f6",
                   markersize=8, label="Recovered footnote marker"),
    ]
    fig.legend(
        handles=legend_elements, loc="lower center", ncol=3,
        fontsize=8, frameon=True, fancybox=True,
        bbox_to_anchor=(0.5, -0.02),
    )

    plt.tight_layout(rect=[0, 0.06, 1, 0.95])
    output = Path(output_path)
    fig.savefig(output, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    print(f"[heatmap] Saved retrieval heatmap to {output}")
    return str(output.resolve())
