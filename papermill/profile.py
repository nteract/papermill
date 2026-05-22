"""
papermill.profile
=================
Notebook profiling: per-cell timing, output analysis, and section grouping.

Public API
----------
profile_notebook(notebook_path, output=None)
    Profile an already-executed notebook and return a dict.

build_sections(nb)
    Parse a notebook's markdown headings into SectionProfile objects.

build_profile(notebook_path, nb)
    Build a profile dict from an nbformat node.

The profile dict schema::

    {
        "notebook": "path/to/notebook.ipynb",
        "total_duration_s": 42.1,
        "n_cells": 10,
        "n_code_cells": 8,
        "n_errors": 0,
        "notebook_start": "2026-...",
        "notebook_end": "2026-...",
        "sections": [
            {
                "label": "Section 1",        # auto-generated sequential number
                "title": "Data Loading",     # original markdown heading text
                "level": 1,
                "number": "1",
                "duration_s": 2.3,
                "status": "completed",
                "cells": [
                    {
                        "index": 2,
                        "execution_count": 3,
                        "source_preview": "import pandas as pd ...",
                        "cell_type": "code",
                        "duration_s": 0.12,
                        "status": "completed",
                        "exception": false,
                        "output_types": ["execute_result"],
                        "output_size_chars": 80,
                        "has_plot": false,
                        "n_outputs": 1,
                        "stdout_chars": 0,
                        "stderr_chars": 0
                    }
                ]
            }
        ],
        "slowest_cells": [...],
        "bottleneck": {
            "cell_index": 5,
            "section": "Sub-section 2.1",
            "duration_s": 18.0,
            "pct_of_total": 42.8
        }
    }

Section numbering follows the markdown heading depth:
  ``#``  → ``Section 1``, ``Section 2``, …
  ``##`` → ``Sub-section 1.1``, ``Sub-section 1.2``, …
  ``###``→ ``Sub-section 1.1.1``, …
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import nbformat

__all__ = [
    "CellProfile",
    "SectionProfile",
    "build_sections",
    "build_profile",
    "profile_notebook",
]

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)", re.MULTILINE)


# ── Data classes ──────────────────────────────────────────────────────────────


@dataclass
class CellProfile:
    """Timing and output metadata for a single notebook cell."""

    index: int
    execution_count: Optional[int]
    source_preview: str
    cell_type: str
    status: str = "pending"
    exception: bool = False
    duration_s: Optional[float] = None
    output_types: list = field(default_factory=list)
    output_size_chars: int = 0
    has_plot: bool = False
    n_outputs: int = 0
    stdout_chars: int = 0
    stderr_chars: int = 0
    start_time: Optional[str] = None
    end_time: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "execution_count": self.execution_count,
            "source_preview": self.source_preview,
            "cell_type": self.cell_type,
            "status": self.status,
            "exception": self.exception,
            "duration_s": round(self.duration_s, 4) if self.duration_s is not None else None,
            "output_types": self.output_types,
            "output_size_chars": self.output_size_chars,
            "has_plot": self.has_plot,
            "n_outputs": self.n_outputs,
            "stdout_chars": self.stdout_chars,
            "stderr_chars": self.stderr_chars,
        }


@dataclass
class SectionProfile:
    """A section of cells bounded by a markdown heading."""

    title: str     # original markdown heading text
    level: int
    number: str = ""  # e.g. "1", "1.2", "1.2.3"
    cells: list = field(default_factory=list)

    @property
    def display_label(self) -> str:
        """Human-readable sequential label (e.g. 'Section 1', 'Sub-section 1.2')."""
        if not self.number:
            return self.title
        depth = self.number.count(".") + 1
        return f"Section {self.number}" if depth == 1 else f"Sub-section {self.number}"

    @property
    def duration_s(self) -> float:
        return sum(c.duration_s or 0.0 for c in self.cells)

    @property
    def status(self) -> str:
        statuses = {c.status for c in self.cells if c.cell_type == "code"}
        if "failed" in statuses:
            return "failed"
        if "running" in statuses:
            return "running"
        if "pending" in statuses:
            return "pending"
        return "completed" if statuses else "skipped"

    def to_dict(self) -> dict:
        return {
            "label": self.display_label,
            "title": self.title,
            "level": self.level,
            "number": self.number,
            "duration_s": round(self.duration_s, 4),
            "status": self.status,
            "cells": [c.to_dict() for c in self.cells],
        }


# ── Section parser ────────────────────────────────────────────────────────────


def _heading_level(source: str):
    """Return (depth, title) if *source* starts with a markdown heading."""
    m = _HEADING_RE.match(source.strip())
    return (len(m.group(1)), m.group(2).strip()) if m else None


def _source_preview(source: str, max_chars: int = 60) -> str:
    first = source.strip().split("\n")[0]
    return first[:max_chars] + ("…" if len(first) > max_chars else "")


def build_sections(nb: nbformat.NotebookNode) -> list:
    """
    Group notebook cells into :class:`SectionProfile` objects by markdown headings.

    Cells before the first heading collect in an implicit preamble section.
    Section numbers are assigned sequentially per heading depth so the tree
    carries no text from the notebook source code::

        #  → Section 1, Section 2, …
        ## → Sub-section 1.1, Sub-section 1.2, …

    Parameters
    ----------
    nb : nbformat.NotebookNode

    Returns
    -------
    list[SectionProfile]
    """
    sections = []
    current = SectionProfile(title="[preamble]", level=0, number="")
    counters: dict = {}

    def _next_number(level: int) -> str:
        for deeper in [k for k in counters if k > level]:
            del counters[deeper]
        counters[level] = counters.get(level, 0) + 1
        return ".".join(str(counters[lvl]) for lvl in sorted(counters))

    for i, cell in enumerate(nb.cells):
        source = cell.get("source", "")
        cp = CellProfile(
            index=i,
            execution_count=cell.get("execution_count"),
            source_preview=_source_preview(source),
            cell_type=cell.cell_type,
        )
        if cell.cell_type == "markdown":
            heading = _heading_level(source)
            if heading:
                level, title = heading
                if current.cells or current.title != "[preamble]":
                    sections.append(current)
                current = SectionProfile(title=title, level=level, number=_next_number(level))
                continue
        current.cells.append(cp)

    if current.cells:
        sections.append(current)
    return sections


# ── Output analysis ───────────────────────────────────────────────────────────


def _analyze_outputs(cell: nbformat.NotebookNode) -> dict:
    outputs = cell.get("outputs", [])
    types, size, plot, stdout_c, stderr_c = [], 0, False, 0, 0
    for out in outputs:
        ot = out.get("output_type", "")
        types.append(ot)
        if ot == "stream":
            text = "".join(out.get("text", []))
            size += len(text)
            if out.get("name") == "stdout":
                stdout_c += len(text)
            else:
                stderr_c += len(text)
        elif ot in ("execute_result", "display_data"):
            data = out.get("data", {})
            if "image/png" in data or "image/svg+xml" in data:
                plot = True
            size += len(str(data.get("text/plain", "")))
        elif ot == "error":
            size += len(out.get("evalue", "")) + len("\n".join(out.get("traceback", [])))
    return {
        "output_types": types,
        "output_size_chars": size,
        "has_plot": plot,
        "n_outputs": len(outputs),
        "stdout_chars": stdout_c,
        "stderr_chars": stderr_c,
    }


def _populate_from_executed(
    nb: nbformat.NotebookNode,
    sections: list,
    cell_map: dict,
) -> None:
    """Fill CellProfile fields from papermill metadata stored in an executed notebook."""
    for i, cell in enumerate(nb.cells):
        if i not in cell_map:
            continue
        cp = cell_map[i]
        pm = cell.get("metadata", {}).get("papermill", {})
        cp.status = pm.get("status", "completed")
        cp.exception = bool(pm.get("exception", False))
        cp.duration_s = pm.get("duration")
        cp.start_time = pm.get("start_time")
        cp.end_time = pm.get("end_time")
        cp.execution_count = cell.get("execution_count")
        out = _analyze_outputs(cell)
        cp.output_types = out["output_types"]
        cp.output_size_chars = out["output_size_chars"]
        cp.has_plot = out["has_plot"]
        cp.n_outputs = out["n_outputs"]
        cp.stdout_chars = out["stdout_chars"]
        cp.stderr_chars = out["stderr_chars"]


# ── Profile builder ───────────────────────────────────────────────────────────


def build_profile(notebook_path: str, nb: nbformat.NotebookNode) -> dict:
    """
    Build a profile dict from an executed notebook node.

    Parameters
    ----------
    notebook_path : str
        Path to the notebook file (used only for the ``"notebook"`` key).
    nb : nbformat.NotebookNode
        The executed notebook (papermill metadata must be present for timing).

    Returns
    -------
    dict
        Profile report — see module docstring for the full schema.
    """
    sections = build_sections(nb)
    cell_map = {cp.index: cp for sec in sections for cp in sec.cells}
    _populate_from_executed(nb, sections, cell_map)

    pm_nb = nb.get("metadata", {}).get("papermill", {})
    all_code = [cp for sec in sections for cp in sec.cells if cp.cell_type == "code"]
    sorted_dur = sorted(
        [c for c in all_code if c.duration_s is not None],
        key=lambda c: c.duration_s or 0,
        reverse=True,
    )
    total_dur = pm_nb.get("duration") or sum(c.duration_s or 0 for c in all_code)
    n_errors = sum(1 for c in all_code if c.exception)

    def _label(idx: int) -> str:
        return next(
            (s.display_label for s in sections if any(x.index == idx for x in s.cells)), "?"
        )

    slowest = [{**c.to_dict(), "section": _label(c.index)} for c in sorted_dur[:5]]

    bottleneck = None
    if sorted_dur:
        b = sorted_dur[0]
        bottleneck = {
            "cell_index": b.index,
            "section": _label(b.index),
            "duration_s": round(b.duration_s, 4),
            "pct_of_total": round(100 * b.duration_s / total_dur, 1) if total_dur else 0,
        }

    return {
        "notebook": str(notebook_path),
        "total_duration_s": round(total_dur, 4) if total_dur else None,
        "n_cells": len(nb.cells),
        "n_code_cells": len(all_code),
        "n_errors": n_errors,
        "notebook_start": pm_nb.get("start_time"),
        "notebook_end": pm_nb.get("end_time"),
        "sections": [s.to_dict() for s in sections],
        "slowest_cells": slowest,
        "bottleneck": bottleneck,
    }


# ── Public API ────────────────────────────────────────────────────────────────


def profile_notebook(notebook_path: str, output: Optional[str] = None) -> dict:
    """
    Profile an already-executed notebook and return the profile as a dict.

    Parameters
    ----------
    notebook_path : str
        Path to an executed ``.ipynb`` file (must contain papermill metadata).
    output : str, optional
        If given, write the profile JSON to this path.

    Returns
    -------
    dict
        Profile report — see module docstring for the full schema.

    Examples
    --------
    >>> from papermill.profile import profile_notebook
    >>> profile = profile_notebook("executed_notebook.ipynb")
    >>> print(profile["total_duration_s"])
    42.1
    >>> print(profile["bottleneck"])
    {'cell_index': 5, 'section': 'Sub-section 2.1', 'duration_s': 18.0, 'pct_of_total': 42.8}
    """
    with open(notebook_path) as f:
        nb = nbformat.read(f, as_version=4)

    result = build_profile(notebook_path, nb)

    if output:
        with open(output, "w") as f:
            json.dump(result, f, indent=2)

    return result
