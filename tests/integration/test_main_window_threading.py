"""Tests for the Phase 7 fixes: analysis runs off the GUI thread, the
original image displays before analysis finishes, and the splitter
layout can't be dragged to an invisible/unrecoverable state.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QSplitter

from app.gui.main_window import MainWindow

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_load_image_shows_original_before_analysis_completes(qapp_session):
    window = MainWindow()
    window.show()  # isVisible() on children is gated by the top-level window's own visibility
    window._load_image(FIXTURES / "sample_dots.png")

    # Immediately after _load_image returns (before the worker thread has
    # had a chance to finish), the original image must already be visible
    # and the busy indicator must be showing — this is the real fix for
    # "it took a long time before anything showed up on screen."
    assert window._viewer._pixmap_item is not None
    assert window._stage_selector.count() == 1
    assert window._stage_selector.itemText(0) == "Original"
    assert window._progress_bar.isVisible()
    assert not window._open_action.isEnabled()

    # Now let the worker actually finish and confirm the rest of the
    # pipeline's results land correctly, exactly as the synchronous
    # version used to produce.
    assert window._worker is not None
    window._worker.wait(10_000)
    qapp_session.processEvents()  # deliver the queued finished_analysis signal

    assert "Validated Spots" in window._stages
    assert not window._progress_bar.isVisible()
    assert window._open_action.isEnabled()
    assert "Validated:" in window._candidate_count_label.text()


def test_opening_a_second_image_while_busy_is_ignored(qapp_session):
    window = MainWindow()
    window._load_image(FIXTURES / "sample_dots.png")
    first_worker = window._worker

    # Attempting to load again while the first analysis is still running
    # must not start a second worker out from under the first.
    window._load_image(FIXTURES / "sample_dots.png")
    assert window._worker is first_worker

    first_worker.wait(10_000)
    qapp_session.processEvents()


def test_splitters_are_not_collapsible(qapp_session):
    window = MainWindow()
    for splitter in window.findChildren(QSplitter):
        assert splitter.childrenCollapsible() is False


def test_quality_and_results_panels_have_minimum_height(qapp_session):
    window = MainWindow()
    assert window._quality_panel.minimumHeight() > 0
    assert window._results_panel.minimumHeight() > 0
