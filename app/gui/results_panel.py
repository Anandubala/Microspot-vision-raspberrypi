"""Results display panel (Phase 5).

Shows the real, computed validated count plus a breakdown of how many
candidates were rejected and why — never a bare final number with no
basis shown (Section 1, Section 9.3's reporting-honesty principle applied
here to counts generally, not just accuracy percentages).
"""
from __future__ import annotations

from collections import Counter

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from app.config.schemas import Candidate


class ResultsPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._label = QLabel("No image analyzed yet.")
        self._label.setWordWrap(True)
        self._label.setStyleSheet("font-family: monospace; padding: 6px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._label)

    def show_result(self, candidates: list[Candidate]) -> None:
        total = len(candidates)
        validated = [c for c in candidates if c.is_validated]
        rejected = [c for c in candidates if not c.is_validated]

        lines = [
            f"Validated count: {len(validated)}  "
            f"(image-based count — see docs/GLOSSARY.md)",
            f"Raw candidates: {total}  |  Rejected: {len(rejected)}",
        ]

        if rejected:
            reason_counts = Counter(c.rejection_reason for c in rejected)
            lines.append("Rejection breakdown:")
            for reason, count in sorted(reason_counts.items(), key=lambda kv: -kv[1]):
                lines.append(f"  {reason}: {count}")

        if total == 0:
            lines = ["NO VALID SPOTS DETECTED (0 raw candidates) — a valid result."]

        self._label.setText("\n".join(lines))

    def clear(self) -> None:
        self._label.setText("No image analyzed yet.")
