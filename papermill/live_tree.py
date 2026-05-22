"""
papermill.live_tree
===================
Optional Rich-based live tree display for notebook execution progress.

Shows a real-time tree of notebook sections and cells with per-cell timing,
replacing the default tqdm progress bar when ``rich`` is installed and
``--live-tree`` / ``live_tree=True`` is requested.

Requires the ``rich`` extra::

    pip install 'papermill[rich]'

Tree output during execution::

    notebook.ipynb  6/10 cells  60%
    ├── ✓  Section 1                           0.1s
    │   ├── ✓  [1] import numpy as np          0.1s
    │   └── ✓  [2] data = np.zeros((n, m))     0.0s
    ├── ⟳  Section 2                           4.2s…
    │   └── ⟳  [4] model.fit(X, y)             4.2s…
    └── ·  Section 3                           pending

The display hooks into :class:`~papermill.engines.NotebookExecutionManager`
via ``cell_start``, ``cell_complete``, and ``cell_exception`` callbacks and
is activated automatically when ``live_tree=True`` is passed to
:func:`~papermill.execute.execute_notebook`.
"""

from __future__ import annotations

import time
import threading
from typing import TYPE_CHECKING

from .profile import build_sections, CellProfile, SectionProfile

if TYPE_CHECKING:
    import nbformat

__all__ = ["LiveTreeDisplay", "is_available"]


def is_available() -> bool:
    """Return True if the ``rich`` package is installed."""
    try:
        import rich  # noqa: F401

        return True
    except ImportError:
        return False


# ── Glyph / colour helpers ────────────────────────────────────────────────────

_GLYPH = {
    "pending": ("·", "dim"),
    "running": ("⟳", "yellow bold"),
    "completed": ("✓", "green"),
    "failed": ("✗", "red bold"),
    "skipped": ("—", "dim"),
}


class LiveTreeDisplay:
    """
    Rich live tree display for papermill notebook execution.

    Instantiate before execution and call :meth:`attach` to register hooks
    on a :class:`~papermill.engines.NotebookExecutionManager`.

    Parameters
    ----------
    nb : nbformat.NotebookNode
        The notebook *before* execution starts (used to build the section tree).
    nb_name : str
        Display name shown at the top of the tree (typically the filename).
    refresh_per_second : int
        How often the live display refreshes. Default 4 Hz.

    Examples
    --------
    Papermill calls this automatically when ``live_tree=True``; you should not
    normally need to instantiate it yourself.
    """

    def __init__(self, nb: "nbformat.NotebookNode", nb_name: str, refresh_per_second: int = 4):
        if not is_available():
            raise ImportError(
                "The 'rich' package is required for live tree display. Install it with: pip install 'papermill[rich]'"
            )
        from rich.console import Console
        from rich.live import Live

        self._sections: list[SectionProfile] = build_sections(nb)
        self._cell_map: dict[int, CellProfile] = {cp.index: cp for sec in self._sections for cp in sec.cells}
        self._nb_name = nb_name
        self._n_total = sum(1 for c in nb.cells if c.cell_type == "code")
        self._n_done = 0
        self._lock = threading.Lock()

        self._console = Console(highlight=False)
        self._live = Live(console=self._console, refresh_per_second=refresh_per_second, transient=False)

    # ── Tree builder ──────────────────────────────────────────────────────────

    def _build_tree(self):
        from rich.text import Text
        from rich.tree import Tree

        pct = 100 * self._n_done / self._n_total if self._n_total else 0
        header = f"[bold]{self._nb_name}[/]  [dim]{self._n_done}/{self._n_total} cells  {pct:.0f}%[/]"
        root = Tree(header, guide_style="dim")
        level_nodes: dict = {0: root}

        for sec in self._sections:
            parent_level = sec.level - 1 if sec.level > 0 else 0
            parent_node = level_nodes.get(parent_level, root)

            code_cells = [c for c in sec.cells if c.cell_type == "code"]
            sec_status = sec.status
            is_running = sec_status == "running"
            live_start = (
                next(
                    (c._live_start for c in code_cells if getattr(c, "_live_start", None) and c.status == "running"),
                    None,
                )
                if is_running
                else None
            )

            glyph_ch, glyph_style = _GLYPH.get(sec_status, ("?", "dim"))
            glyph = Text(glyph_ch, style=glyph_style)
            dur_t = self._dur_text(sec.duration_s if sec.duration_s > 0 else None, is_running, live_start)

            sec_label = Text()
            sec_label.append_text(glyph)
            sec_label.append(f"  {sec.display_label:<38}", style="bold" if is_running else "")
            sec_label.append("  ")
            sec_label.append_text(dur_t)

            sec_node = parent_node.add(sec_label)
            level_nodes[sec.level] = sec_node
            for lvl in [k for k in level_nodes if k > sec.level]:
                del level_nodes[lvl]

            for cp in code_cells:
                r = cp.status == "running"
                g_ch, g_st = _GLYPH.get(cp.status, ("?", "dim"))
                g = Text(g_ch, style=g_st)
                d = self._dur_text(cp.duration_s, r, getattr(cp, "_live_start", None))
                preview = cp.source_preview[:45]
                cell_label = Text()
                cell_label.append_text(g)
                cell_label.append(f"  [{cp.index}] {preview:<45}", style="yellow" if r else "dim")
                cell_label.append("  ")
                cell_label.append_text(d)
                sec_node.add(cell_label)

        return root

    @staticmethod
    def _dur_text(dur, running: bool = False, live_start=None):
        from rich.text import Text

        if running and live_start is not None:
            elapsed = time.monotonic() - live_start
            return Text(f"{elapsed:.1f}s…", style="yellow")
        if dur is not None:
            style = "red" if dur > 30 else ("yellow" if dur > 5 else "green")
            return Text(f"{dur:.1f}s", style=style)
        return Text("", style="dim")

    def _refresh(self):
        with self._lock:
            self._live.update(self._build_tree())

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self):
        """Start the live display context."""
        self._live.start()
        self._refresh()

    def stop(self):
        """Stop the live display context."""
        self._refresh()
        self._live.stop()

    # ── Callbacks (called by NotebookExecutionManager hooks) ──────────────────

    def on_cell_start(self, cell_index: int) -> None:
        if cell_index in self._cell_map:
            cp = self._cell_map[cell_index]
            cp.status = "running"
            cp._live_start = time.monotonic()
        self._refresh()

    def on_cell_complete(self, cell, cell_index: int) -> None:
        if cell_index in self._cell_map:
            cp = self._cell_map[cell_index]
            pm = cell.get("metadata", {}).get("papermill", {})
            cp.status = pm.get("status", "completed")
            cp.exception = bool(pm.get("exception", False))
            cp.duration_s = pm.get("duration")
            if cell.cell_type == "code":
                with self._lock:
                    self._n_done += 1
        self._refresh()

    def on_cell_exception(self, cell_index: int) -> None:
        if cell_index in self._cell_map:
            self._cell_map[cell_index].status = "failed"
        self._refresh()
