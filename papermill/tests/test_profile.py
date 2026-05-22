"""Tests for papermill.profile and papermill.live_tree."""

import json
import pytest
import nbformat

from papermill.profile import (
    CellProfile,
    SectionProfile,
    build_sections,
    build_profile,
    profile_notebook,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_nb(cells):
    """Build a minimal NotebookNode from a list of (type, source, pm_meta) tuples."""
    nb = nbformat.v4.new_notebook()
    nb.cells = []
    for cell_type, source, pm_meta in cells:
        if cell_type == "markdown":
            cell = nbformat.v4.new_markdown_cell(source)
        else:
            cell = nbformat.v4.new_code_cell(source)
            cell.metadata["papermill"] = pm_meta or {
                "start_time": None, "end_time": None,
                "duration": None, "status": "pending", "exception": False,
            }
        nb.cells.append(cell)
    return nb


def _executed_cell_meta(duration, status="completed", exception=False):
    return {
        "start_time": "2026-01-01T00:00:00+00:00",
        "end_time": "2026-01-01T00:00:01+00:00",
        "duration": duration,
        "status": status,
        "exception": exception,
    }


# ── build_sections ────────────────────────────────────────────────────────────

class TestBuildSections:
    def test_no_headings_creates_preamble(self):
        nb = _make_nb([("code", "x = 1", None), ("code", "y = 2", None)])
        sections = build_sections(nb)
        assert len(sections) == 1
        assert sections[0].title == "[preamble]"
        assert sections[0].number == ""
        assert len(sections[0].cells) == 2

    def test_single_heading(self):
        nb = _make_nb([
            ("markdown", "# Data Loading", None),
            ("code", "import pandas", None),
        ])
        sections = build_sections(nb)
        assert len(sections) == 1
        assert sections[0].number == "1"
        assert sections[0].display_label == "Section 1"

    def test_sequential_numbering(self):
        nb = _make_nb([
            ("markdown", "# First", None), ("code", "a=1", None),
            ("markdown", "# Second", None), ("code", "b=2", None),
            ("markdown", "# Third", None), ("code", "c=3", None),
        ])
        sections = build_sections(nb)
        assert [s.number for s in sections] == ["1", "2", "3"]
        assert [s.display_label for s in sections] == ["Section 1", "Section 2", "Section 3"]

    def test_nested_sub_sections(self):
        nb = _make_nb([
            ("markdown", "# Analysis", None), ("code", "x=1", None),
            ("markdown", "## Cleaning", None), ("code", "y=2", None),
            ("markdown", "## Feature Engineering", None), ("code", "z=3", None),
            ("markdown", "# Results", None), ("code", "w=4", None),
        ])
        sections = build_sections(nb)
        labels = [s.display_label for s in sections]
        assert labels == ["Section 1", "Sub-section 1.1", "Sub-section 1.2", "Section 2"]

    def test_sub_section_counter_resets_across_top_sections(self):
        nb = _make_nb([
            ("markdown", "# A", None), ("code", "a=1", None),
            ("markdown", "## A1", None), ("code", "b=2", None),
            ("markdown", "# B", None), ("code", "c=3", None),
            ("markdown", "## B1", None), ("code", "d=4", None),
        ])
        sections = build_sections(nb)
        numbers = [s.number for s in sections]
        # After # B the sub-counter resets, so ## B1 becomes 2.1 not 1.2
        assert numbers == ["1", "1.1", "2", "2.1"]

    def test_heading_cells_not_added_to_cell_list(self):
        nb = _make_nb([
            ("markdown", "# Title", None),
            ("markdown", "Some prose (no heading)", None),
            ("code", "x=1", None),
        ])
        sections = build_sections(nb)
        assert len(sections) == 1
        # Only the prose markdown + code cell should be in cells
        assert len(sections[0].cells) == 2


# ── SectionProfile ────────────────────────────────────────────────────────────

class TestSectionProfile:
    def test_display_label_preamble(self):
        s = SectionProfile(title="[preamble]", level=0, number="")
        assert s.display_label == "[preamble]"

    def test_display_label_section(self):
        s = SectionProfile(title="Data", level=1, number="3")
        assert s.display_label == "Section 3"

    def test_display_label_subsection(self):
        s = SectionProfile(title="Cleaning", level=2, number="1.2")
        assert s.display_label == "Sub-section 1.2"

    def test_duration_sums_cells(self):
        s = SectionProfile(title="T", level=1, number="1")
        s.cells = [
            CellProfile(0, 1, "", "code", duration_s=1.0),
            CellProfile(1, 2, "", "code", duration_s=2.5),
        ]
        assert s.duration_s == pytest.approx(3.5)

    def test_status_failed_takes_priority(self):
        s = SectionProfile(title="T", level=1, number="1")
        s.cells = [
            CellProfile(0, 1, "", "code", status="completed"),
            CellProfile(1, 2, "", "code", status="failed"),
        ]
        assert s.status == "failed"

    def test_to_dict_contains_label_and_title(self):
        s = SectionProfile(title="Data Loading", level=1, number="1")
        d = s.to_dict()
        assert d["label"] == "Section 1"
        assert d["title"] == "Data Loading"
        assert d["number"] == "1"


# ── build_profile ─────────────────────────────────────────────────────────────

class TestBuildProfile:
    def _make_executed_nb(self):
        nb = _make_nb([
            ("markdown", "# Imports", None),
            ("code", "import numpy as np", _executed_cell_meta(0.1)),
            ("markdown", "## Heavy computation", None),
            ("code", "result = np.sum(range(1000))", _executed_cell_meta(5.0)),
            ("markdown", "# Results", None),
            ("code", "print(result)", _executed_cell_meta(0.05)),
        ])
        nb.metadata["papermill"] = {
            "start_time": "2026-01-01T00:00:00+00:00",
            "end_time": "2026-01-01T00:00:06+00:00",
            "duration": 5.15,
            "exception": False,
        }
        return nb

    def test_profile_keys(self):
        nb = self._make_executed_nb()
        profile = build_profile("test.ipynb", nb)
        assert "notebook" in profile
        assert "total_duration_s" in profile
        assert "sections" in profile
        assert "bottleneck" in profile
        assert "slowest_cells" in profile

    def test_bottleneck_points_to_slowest_cell(self):
        nb = self._make_executed_nb()
        profile = build_profile("test.ipynb", nb)
        assert profile["bottleneck"]["duration_s"] == pytest.approx(5.0)
        assert "Sub-section" in profile["bottleneck"]["section"]

    def test_section_labels_in_profile(self):
        nb = self._make_executed_nb()
        profile = build_profile("test.ipynb", nb)
        labels = [s["label"] for s in profile["sections"]]
        assert "Section 1" in labels
        assert "Sub-section 1.1" in labels
        assert "Section 2" in labels

    def test_n_errors_zero_when_no_exceptions(self):
        nb = self._make_executed_nb()
        assert build_profile("test.ipynb", nb)["n_errors"] == 0

    def test_n_errors_counts_exceptions(self):
        nb = self._make_executed_nb()
        nb.cells[1].metadata["papermill"]["exception"] = True
        nb.cells[1].metadata["papermill"]["status"] = "failed"
        assert build_profile("test.ipynb", nb)["n_errors"] == 1


# ── profile_notebook ──────────────────────────────────────────────────────────

class TestProfileNotebook:
    def test_returns_dict(self, tmp_path):
        nb = nbformat.v4.new_notebook()
        cell = nbformat.v4.new_code_cell("x = 1")
        cell.metadata["papermill"] = _executed_cell_meta(0.1)
        nb.cells = [cell]
        nb.metadata["papermill"] = {"duration": 0.1, "exception": False}
        nb_path = tmp_path / "test.ipynb"
        nbformat.write(nb, str(nb_path))

        profile = profile_notebook(str(nb_path))
        assert isinstance(profile, dict)
        assert profile["n_code_cells"] == 1

    def test_writes_json_file(self, tmp_path):
        nb = nbformat.v4.new_notebook()
        cell = nbformat.v4.new_code_cell("x = 1")
        cell.metadata["papermill"] = _executed_cell_meta(0.2)
        nb.cells = [cell]
        nb.metadata["papermill"] = {"duration": 0.2, "exception": False}
        nb_path = tmp_path / "test.ipynb"
        out_path = tmp_path / "test.profile.json"
        nbformat.write(nb, str(nb_path))

        profile_notebook(str(nb_path), output=str(out_path))
        assert out_path.exists()
        with open(out_path) as f:
            data = json.load(f)
        assert data["n_code_cells"] == 1


# ── live_tree availability guard ──────────────────────────────────────────────

class TestLiveTreeAvailability:
    def test_is_available_returns_bool(self):
        from papermill.live_tree import is_available
        assert isinstance(is_available(), bool)
