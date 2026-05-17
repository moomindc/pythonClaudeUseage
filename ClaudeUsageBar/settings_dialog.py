import config as cfg_mod
from PyQt6.QtCore import QTime
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTimeEdit,
    QVBoxLayout,
)


class SettingsDialog(QDialog):
    def __init__(self, cfg: dict, parent=None) -> None:
        super().__init__(parent)
        self._cfg = cfg
        self._colors: dict[str, str] = dict(cfg.get("colors", {}))
        self.setWindowTitle("Claude Usage Bar — Settings")
        self.setFixedWidth(680)
        self.setModal(True)
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        # ---- Two-column body ----
        columns = QHBoxLayout()
        columns.setSpacing(0)

        left = QVBoxLayout()
        left.setSpacing(10)
        right = QVBoxLayout()
        right.setSpacing(10)

        # Left: General
        left.addWidget(self._section_header("General"))
        left.addLayout(self._row_spinbox(
            "Poll interval (minutes)", "poll_interval_minutes",
            1, 60, self._cfg.get("poll_interval_minutes", 5),
        ))
        left.addLayout(self._row_spinbox(
            "Bar width (pixels)", "window_width",
            50, 400, self._cfg.get("window", {}).get("width", 123),
        ))
        left.addLayout(self._row_reset_display())

        left.addWidget(self._separator())
        left.addWidget(self._section_header("Colours"))
        left.addLayout(self._row_color("Fill colour", "fill", "#14532D"))
        left.addLayout(self._row_color("Background colour", "background", "#030A05"))
        left.addLayout(self._row_color("Text colour", "text", "#86EFAC"))

        left.addWidget(self._separator())
        left.addWidget(self._section_header("Triple Session"))
        left.addLayout(self._row_triple())

        left.addStretch()

        # Vertical divider
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.VLine)
        divider.setFrameShadow(QFrame.Shadow.Sunken)

        # Right: RAG Mode first so signals can wire to notification labels
        right.addWidget(self._section_header("RAG Mode"))
        right.addLayout(self._row_rag())

        right.addWidget(self._separator())
        right.addWidget(self._section_header("Notifications"))
        right.addLayout(self._row_notifications())

        right.addStretch()

        # Wire RAG spinboxes → notification label updates
        self._rag_amber.valueChanged.connect(self._update_notif_labels)
        self._rag_red.valueChanged.connect(self._update_notif_labels)

        columns.addLayout(left, stretch=1)
        columns.addSpacing(16)
        columns.addWidget(divider)
        columns.addSpacing(16)
        columns.addLayout(right, stretch=1)

        root.addLayout(columns)
        root.addWidget(self._separator())
        root.addLayout(self._buttons())

    # ------------------------------------------------------------------ #
    # Section helpers
    # ------------------------------------------------------------------ #

    def _section_header(self, text: str) -> QLabel:
        lbl = QLabel(text)
        f = QFont()
        f.setBold(True)
        lbl.setFont(f)
        return lbl

    def _separator(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        return sep

    def _row_spinbox(self, label: str, attr: str, lo: int, hi: int, val: int) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        row.addStretch()
        spin = QSpinBox()
        spin.setRange(lo, hi)
        spin.setValue(int(val))
        spin.setFixedWidth(90)
        setattr(self, f"_{attr}", spin)
        row.addWidget(spin)
        return row

    def _row_color(self, label: str, key: str, fallback: str) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        row.addStretch()
        current = self._colors.get(key, fallback)
        btn = QPushButton()
        btn.setFixedSize(60, 22)
        self._apply_color_btn(btn, current)
        btn.clicked.connect(lambda _checked, b=btn, k=key: self._pick_color(b, k))
        setattr(self, f"_color_btn_{key}", btn)
        row.addWidget(btn)
        return row

    def _row_reset_display(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(QLabel("Reset countdown style"))
        row.addStretch()
        self._reset_clock = QCheckBox("Clock time (HH:MM)")
        self._reset_clock.setChecked(self._cfg.get("reset_display", "countdown") == "clock")
        row.addWidget(self._reset_clock)
        return row

    def _row_triple(self) -> QVBoxLayout:
        ts = self._cfg.get("triple_session", {})
        col = QVBoxLayout()
        col.setSpacing(8)

        self._triple_enabled = QCheckBox("Enabled")
        self._triple_enabled.setChecked(ts.get("enabled", False))
        col.addWidget(self._triple_enabled)

        time_row = QHBoxLayout()
        time_row.addWidget(QLabel("First session starts at"))
        time_row.addStretch()
        self._triple_time = QTimeEdit()
        self._triple_time.setDisplayFormat("HH:mm")
        h, m = map(int, ts.get("work_start", "07:00").split(":"))
        self._triple_time.setTime(QTime(h, m))
        self._triple_time.setFixedWidth(90)
        time_row.addWidget(self._triple_time)
        col.addLayout(time_row)

        prompt_row = QHBoxLayout()
        prompt_row.addWidget(QLabel("Trigger prompt"))
        prompt_row.addStretch()
        self._triple_prompt = QLineEdit()
        self._triple_prompt.setText(ts.get("prompt", "Hi"))
        self._triple_prompt.setFixedWidth(90)
        prompt_row.addWidget(self._triple_prompt)
        col.addLayout(prompt_row)

        return col

    def _row_rag(self) -> QVBoxLayout:
        t = self._cfg.get("rag_thresholds", {"amber": 80, "red": 90})
        col = QVBoxLayout()
        col.setSpacing(8)

        self._rag_enabled = QCheckBox("Enabled")
        self._rag_enabled.setChecked(self._cfg.get("rag_mode", False))
        col.addWidget(self._rag_enabled)

        amber_row = QHBoxLayout()
        amber_row.addWidget(QLabel("Amber threshold"))
        amber_row.addStretch()
        self._rag_amber = QSpinBox()
        self._rag_amber.setRange(1, 99)
        self._rag_amber.setValue(t.get("amber", 80))
        self._rag_amber.setSuffix("%")
        self._rag_amber.setFixedWidth(90)
        amber_row.addWidget(self._rag_amber)
        col.addLayout(amber_row)

        red_row = QHBoxLayout()
        red_row.addWidget(QLabel("Red threshold"))
        red_row.addStretch()
        self._rag_red = QSpinBox()
        self._rag_red.setRange(1, 100)
        self._rag_red.setValue(t.get("red", 90))
        self._rag_red.setSuffix("%")
        self._rag_red.setFixedWidth(90)
        red_row.addWidget(self._rag_red)
        col.addLayout(red_row)

        return col

    def _row_notifications(self) -> QVBoxLayout:
        notif = self._cfg.get("notifications", {})
        thresholds = notif.get("thresholds", [80, 90])
        t = self._cfg.get("rag_thresholds", {"amber": 80, "red": 90})
        amber_val = t.get("amber", 80)
        red_val = t.get("red", 90)

        col = QVBoxLayout()
        col.setSpacing(8)

        self._notif_enabled = QCheckBox("Enabled")
        self._notif_enabled.setChecked(notif.get("enabled", True))
        col.addWidget(self._notif_enabled)

        self._notif_amber = QCheckBox(f"Amber ({amber_val}%)")
        self._notif_amber.setChecked(amber_val in thresholds)
        col.addWidget(self._notif_amber)

        self._notif_red = QCheckBox(f"Red ({red_val}%)")
        self._notif_red.setChecked(red_val in thresholds)
        col.addWidget(self._notif_red)

        return col

    def _update_notif_labels(self) -> None:
        self._notif_amber.setText(f"Amber ({self._rag_amber.value()}%)")
        self._notif_red.setText(f"Red ({self._rag_red.value()}%)")

    def _buttons(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addStretch()
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        row.addWidget(cancel)
        save = QPushButton("Save")
        save.setDefault(True)
        save.clicked.connect(self._save)
        row.addWidget(save)
        return row

    # ------------------------------------------------------------------ #
    # Colour picking
    # ------------------------------------------------------------------ #

    def _apply_color_btn(self, btn: QPushButton, hex_color: str) -> None:
        btn.setStyleSheet(
            f"background-color: {hex_color}; border: 1px solid #888; border-radius: 3px;"
        )
        btn.setText("")

    def _pick_color(self, btn: QPushButton, key: str) -> None:
        current = QColor(self._colors.get(key, "#000000"))
        chosen = QColorDialog.getColor(current, self, "Choose colour")
        if chosen.isValid():
            hex_val = chosen.name()
            self._colors[key] = hex_val
            self._apply_color_btn(btn, hex_val)

    # ------------------------------------------------------------------ #
    # Save
    # ------------------------------------------------------------------ #

    def _save(self) -> None:
        self._cfg["poll_interval_minutes"] = self._poll_interval_minutes.value()
        self._cfg.setdefault("window", {})["width"] = self._window_width.value()
        self._cfg["colors"] = dict(self._colors)
        self._cfg["reset_display"] = "clock" if self._reset_clock.isChecked() else "countdown"
        ts = self._cfg.setdefault("triple_session", {})
        ts["enabled"] = self._triple_enabled.isChecked()
        t = self._triple_time.time()
        ts["work_start"] = f"{t.hour():02d}:{t.minute():02d}"
        ts["prompt"] = self._triple_prompt.text().strip() or "Hi"
        self._cfg["rag_mode"] = self._rag_enabled.isChecked()
        self._cfg.setdefault("rag_thresholds", {})["amber"] = self._rag_amber.value()
        self._cfg["rag_thresholds"]["red"] = self._rag_red.value()
        thresholds = []
        if self._notif_amber.isChecked():
            thresholds.append(self._rag_amber.value())
        if self._notif_red.isChecked():
            thresholds.append(self._rag_red.value())
        self._cfg.setdefault("notifications", {})["enabled"] = self._notif_enabled.isChecked()
        self._cfg["notifications"]["thresholds"] = thresholds
        cfg_mod.save(self._cfg)
        self.accept()
