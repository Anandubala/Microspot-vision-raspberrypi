"""Results display panel.

Phase 5: validated count plus a breakdown of how many candidates were
rejected and why — never a bare final number with no basis shown
(Section 1, Section 9.3's reporting-honesty principle applied here to
counts generally, not just accuracy percentages).

Phase 5 addendum (2026-10-05): added a per-spot pixel-size listing. The
lab assistant's own requirement is to report each spot's size in pixels
(e.g. "this one is 2 pixels, that one is 3 pixels") — area and
equivalent_diameter were already computed per candidate since Phase 5,
just never shown anywhere. Numbers here match the "Validated Spots"
overlay's numbering exactly (same detection order, same 1..N sequence).

Phase 6: shows whether touching-spot (watershed) separation actually ran
this session — Section 7.5's "record whether it was used."
"""
from __future__ import annotations

from collections import Counter

from PySide6.QtWidgets import QPlainTextEdit, QVBoxLayout, QWidget

from app.config.schemas import Candidate


class ResultsPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._text = QPlainTextEdit(self)
        self._text.setReadOnly(True)
        self._text.setStyleSheet("font-family: monospace;")
        self._text.setPlainText("No image analyzed yet.")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._text)

    def show_result(self, candidates: list[Candidate], separation_applied: bool = False) -> None:
        total = len(candidates)
        validated = [c for c in candidates if c.is_validated]
        rejected = [c for c in candidates if not c.is_validated]

        if total == 0:
            note = " Touching-spot separation ran but found nothing to split." if separation_applied else ""
            self._text.setPlainText(
                f"NO VALID SPOTS DETECTED (0 raw candidates) — a valid result.{note}"
            )
            return

        separation_note = (
            "yes — at least one merged blob was split into separate spots"
            if separation_applied
            else "no — no merged blobs were found this run"
        )
        lines = [
            f"Validated count: {len(validated)}  "
            f"(image-based count — see docs/GLOSSARY.md)",
            f"Raw candidates: {total}  |  Rejected: {len(rejected)}",
            f"Touching-spot separation applied: {separation_note}",
        ]

        if rejected:
            reason_counts = Counter(c.rejection_reason for c in rejected)
            lines.append("Rejection breakdown:")
            for reason, count in sorted(reason_counts.items(), key=lambda kv: -kv[1]):
                lines.append(f"  {reason}: {count}")

        if validated:
            lines.append("")
            lines.append("Per-spot pixel size (matches overlay numbering):")
            for number, c in enumerate(validated, start=1):
                lines.append(
                    f"  #{number}: area={c.area:.1f} px²  "
                    f"diameter≈{c.equivalent_diameter:.1f} px  "
                    f"(pixels, not microns — no spatial calibration yet)"
                )

        self._text.setPlainText("\n".join(lines))

    def clear(self) -> None:
        self._text.setPlainText("No image analyzed yet.")
