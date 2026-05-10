# wizard.py
# Provides the three-page setup wizard shown on first run and whenever the user chooses
# "Reconfigure". The wizard walks the user through pasting their browser session key,
# tests the connection, and saves the credentials to the config file.

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

import claude_client
import config as cfg_mod


# WizardDialog
# A modal dialog that guides the user through configuring the app. It uses a
# QStackedWidget to show one of three pages at a time: Welcome (0), Key entry (1),
# and Done (2).
class WizardDialog(QDialog):
    # __init__
    # Initialises the dialog with a fixed width, marks it as modal (blocks the rest
    # of the UI while open), and builds the page stack.
    def __init__(self, cfg: dict, parent=None) -> None:
        super().__init__(parent)
        self._cfg = cfg
        self.setWindowTitle("Claude Usage Bar — Setup")
        self.setFixedWidth(500)
        self.setModal(True)
        self._build()

    # _build
    # Creates the QStackedWidget that holds all three pages and adds it to the dialog
    # layout. Pages are referenced by index: 0 = Welcome, 1 = Key, 2 = Done.
    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        self._stack = QStackedWidget()
        self._stack.addWidget(self._page_welcome())   # 0
        self._stack.addWidget(self._page_key())       # 1
        self._stack.addWidget(self._page_done())      # 2
        root.addWidget(self._stack)

    # ------------------------------------------------------------------ #
    # Page 0 — Welcome
    # ------------------------------------------------------------------ #

    # _page_welcome
    # Builds the first page shown to the user: a brief explanation of what the app
    # does and a "Get Started" button that advances to the key-entry page.
    def _page_welcome(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(12)

        title = QLabel("Claude Usage Bar")
        f = QFont(); f.setPointSize(15); f.setBold(True)
        title.setFont(f)
        lay.addWidget(title)

        lay.addWidget(QLabel(
            "This tool shows a compact floating bar with your Claude.ai\n"
            "5-hour session usage and time until the next reset.\n\n"
            "Setup takes about 30 seconds — you'll paste one cookie value\n"
            "from your browser."
        ))
        lay.addStretch()

        btn = QPushButton("Get Started  →")
        btn.setDefault(True)
        btn.clicked.connect(lambda: self._stack.setCurrentIndex(1))
        lay.addWidget(btn)
        return page

    # ------------------------------------------------------------------ #
    # Page 1 — Session key
    # ------------------------------------------------------------------ #

    # _page_key
    # Builds the second page where the user pastes their browser session cookie value.
    # Shows step-by-step instructions for finding the cookie in Chrome DevTools, a
    # password-masked input field, and a "Test & Connect" button.
    def _page_key(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(8)

        f = QFont(); f.setBold(True)
        hdr = QLabel("Paste your browser session key")
        hdr.setFont(f)
        lay.addWidget(hdr)

        steps = QLabel(
            "1.  Open  https://claude.ai  and confirm you're logged in\n"
            "2.  Press F12  →  Application tab  →  Cookies  →  https://claude.ai\n"
            "3.  Find the cookie named  sessionKey  and copy its  Value"
            "4. in (Chrome / Edge) go to the Application tab or (Firefox) Storage tab.\n"
            "5. The cookie is named `sessionKey` its value starts with `sk - ant - sid01 - `\n"
            "6. Copy the entire value (it's long — use Ctrl+A to select all in the Value field)\n"
        )
        steps.setWordWrap(True)
        lay.addWidget(steps)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        lay.addWidget(sep)

        lay.addWidget(QLabel("sessionKey value:"))
        self._key_field = QLineEdit()
        self._key_field.setPlaceholderText("sk-ant-sid01-…")
        self._key_field.setEchoMode(QLineEdit.EchoMode.Password)
        lay.addWidget(self._key_field)

        self._status = QLabel("")
        self._status.setWordWrap(True)
        lay.addWidget(self._status)

        lay.addStretch()

        row = QHBoxLayout()
        back = QPushButton("←  Back")
        back.clicked.connect(lambda: self._stack.setCurrentIndex(0))
        row.addWidget(back)

        self._test_btn = QPushButton("Test && Connect")
        self._test_btn.setDefault(True)
        self._test_btn.clicked.connect(self._test)
        row.addWidget(self._test_btn)
        lay.addLayout(row)
        return page

    # _test
    # Called when the user clicks "Test & Connect". Validates that the field is not
    # empty, disables the button to prevent double-clicks, then calls the claude.ai API
    # to verify the key and discover the organisation ID. On success the credentials
    # are saved and the wizard advances to the Done page. On failure a descriptive
    # error message is shown in the status label.
    def _test(self) -> None:
        key = self._key_field.text().strip()
        if not key:
            self._status.setText("Please paste your sessionKey value first.")
            return

        self._test_btn.setEnabled(False)
        self._status.setText("Testing connection…")
        QApplication.processEvents()   # flush the label update before blocking

        try:
            orgs = claude_client.get_organizations(key)
            if not orgs:
                raise ValueError(
                    "Connected, but no organizations were returned.\n"
                    "Check that you copied the full sessionKey value."
                )
            org = orgs[0]
            org_id = org.get("uuid") or org.get("id") or org.get("org_id")
            if not org_id:
                raise ValueError(
                    f"Could not find an organization ID in the response.\n"
                    f"Got: {list(org.keys())}"
                )
            self._cfg["session_key"] = key
            self._cfg["org_id"] = org_id
            cfg_mod.save(self._cfg)
            self._status.setText("")
            self._stack.setCurrentIndex(2)

        except claude_client.AuthError as exc:
            self._status.setText(
                f"✗  Authentication failed: {exc}\n\n"
                "Make sure you copied the complete sessionKey value from the browser cookie."
            )
            self._test_btn.setEnabled(True)
        except Exception as exc:
            self._status.setText(f"✗  {exc}")
            self._test_btn.setEnabled(True)

    # ------------------------------------------------------------------ #
    # Page 2 — Done
    # ------------------------------------------------------------------ #

    # _page_done
    # Builds the final confirmation page shown after a successful connection test.
    # Tells the user their key has been saved and provides a "Start Monitoring" button
    # that closes the dialog with an Accepted result, triggering the main app to start.
    def _page_done(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(12)

        f = QFont(); f.setPointSize(15); f.setBold(True)
        title = QLabel("All set!")
        title.setFont(f)
        lay.addWidget(title)

        lay.addWidget(QLabel(
            "Your session key has been saved.\n"
            "The usage bar will appear in a moment.\n\n"
            "Right-click the bar or the system tray icon to reconfigure."
        ))
        lay.addStretch()

        btn = QPushButton("Start Monitoring")
        btn.setDefault(True)
        btn.clicked.connect(self.accept)
        lay.addWidget(btn)
        return page
