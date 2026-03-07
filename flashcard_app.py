"""
Flashcard App — Unified Study Tool
Merges file upload (PDF/DOCX → Gemini AI flashcards) with the 3D-flip flashcard
study experience and adds an inline deck editor. All features live in one window
with a navigable start page.
"""

import sys
import os
import json
import tempfile

import requests
import pdfplumber
from docx import Document
import google.generativeai as genai
from dotenv import load_dotenv

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStackedWidget, QListWidget, QMessageBox,
    QFileDialog, QInputDialog, QScrollArea, QLineEdit, QSizePolicy,
    QFrame, QProgressBar
)
from PyQt6.QtCore import (
    Qt, QUrl, pyqtSignal, pyqtProperty,
    QPropertyAnimation, QEasingCurve, QRectF
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtGui import (
    QFont, QPainter, QTransform, QPen, QColor, QTextOption,
    QLinearGradient
)

# ── Configuration ──────────────────────────────────────────────────────────────
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "YOUR_API_KEY_HERE")
FLASHCARD_DIR = "FlashcardUploads"

# ── Colour Palette ─────────────────────────────────────────────────────────────
BG_DARK       = "#0f0f1a"
BG_CARD       = "#1a1a2e"
ACCENT        = "#6c63ff"
ACCENT_HOVER  = "#847dff"
TEXT_PRIMARY   = "#e8e8ff"
TEXT_SECONDARY = "#a0a0c0"
CARD_BG       = "#23234a"
CARD_BORDER   = "#3a3a6e"
DANGER        = "#ff6b6b"
SUCCESS       = "#51cf66"

# ── Shared Stylesheet ─────────────────────────────────────────────────────────
STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color: {BG_DARK};
    color: {TEXT_PRIMARY};
}}
QLabel {{
    color: {TEXT_PRIMARY};
}}
QPushButton {{
    background-color: {ACCENT};
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 12px 24px;
    font-size: 14px;
    font-weight: 600;
    font-family: 'Segoe UI', 'Arial', sans-serif;
}}
QPushButton:hover {{
    background-color: {ACCENT_HOVER};
}}
QPushButton:pressed {{
    background-color: #5a52e0;
}}
QPushButton#danger {{
    background-color: {DANGER};
}}
QPushButton#danger:hover {{
    background-color: #ff8787;
}}
QPushButton#secondary {{
    background-color: transparent;
    border: 2px solid {ACCENT};
    color: {ACCENT};
}}
QPushButton#secondary:hover {{
    background-color: rgba(108, 99, 255, 0.15);
}}
QListWidget {{
    background-color: {BG_CARD};
    border: 1px solid {CARD_BORDER};
    border-radius: 10px;
    padding: 8px;
    color: {TEXT_PRIMARY};
    font-size: 14px;
    font-family: 'Segoe UI', 'Arial', sans-serif;
    outline: none;
}}
QListWidget::item {{
    padding: 12px;
    border-radius: 6px;
    margin-bottom: 4px;
}}
QListWidget::item:hover {{
    background-color: rgba(108, 99, 255, 0.2);
}}
QListWidget::item:selected {{
    background-color: {ACCENT};
    color: #ffffff;
}}
QLineEdit {{
    background-color: {BG_CARD};
    border: 1px solid {CARD_BORDER};
    border-radius: 6px;
    padding: 8px 12px;
    color: {TEXT_PRIMARY};
    font-size: 13px;
    font-family: 'Segoe UI', 'Arial', sans-serif;
}}
QLineEdit:focus {{
    border-color: {ACCENT};
}}
QScrollArea {{
    background-color: transparent;
    border: none;
}}
QProgressBar {{
    background-color: {BG_CARD};
    border: 1px solid {CARD_BORDER};
    border-radius: 6px;
    text-align: center;
    color: {TEXT_PRIMARY};
    font-weight: 600;
    height: 22px;
}}
QProgressBar::chunk {{
    background-color: {ACCENT};
    border-radius: 5px;
}}
"""


# ── Gemini Init ────────────────────────────────────────────────────────────────
def init_gemini():
    """Configure and test the Gemini API key. Returns True on success."""
    if not GEMINI_API_KEY:
        return False
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-2.5-flash")
        model.generate_content("test")
        print("[OK] Gemini API key verified.")
        return True
    except Exception as e:
        print(f"[FAIL] Gemini key failed: {e}")
        return False


# ══════════════════════════════════════════════════════════════════════════════
#  Flashcard Widget (3D flip animation)
# ══════════════════════════════════════════════════════════════════════════════

class FlashcardWidget(QWidget):
    """A card that shows text and does a 3D flip animation when toggled."""
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.text = ""
        self._rotation_y = 0.0

        self.anim = QPropertyAnimation(self, b"rotationY")
        self.anim.setDuration(250)
        self.anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.anim.finished.connect(self._on_anim_finished)

        self._is_animating_out = False
        self._next_text = ""

    # -- Qt property for animation --
    @pyqtProperty(float)
    def rotationY(self):
        return self._rotation_y

    @rotationY.setter
    def rotationY(self, value):
        self._rotation_y = value
        self.update()

    def setText(self, text):
        self.text = text
        self.update()

    def flip_to_text(self, text):
        if text == self.text:
            return
        self._next_text = text
        self._is_animating_out = True
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(80.0)
        self.anim.start()

    def _on_anim_finished(self):
        if self._is_animating_out:
            self.text = self._next_text
            self._is_animating_out = False
            self.anim.setStartValue(80.0)
            self.anim.setEndValue(0.0)
            self.anim.start()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

    def paintEvent(self, event):
        try:
            import math
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            angle_rad = math.radians(self._rotation_y)
            scale_x = max(abs(math.cos(angle_rad)), 0.01)

            transform = QTransform()
            cw = self.width() / 2.0
            transform.translate(cw, 0)
            transform.scale(scale_x, 1.0)
            transform.translate(-cw, 0)
            painter.setTransform(transform)

            rect = self.rect().adjusted(10, 10, -10, -10)
            shadow_rect = rect.adjusted(4, 4, 4, 4)
            
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, 60))
            painter.drawRoundedRect(shadow_rect, 16, 16)

            grad = QLinearGradient(float(rect.topLeft().x()), float(rect.topLeft().y()), float(rect.bottomRight().x()), float(rect.bottomRight().y()))
            grad.setColorAt(0, QColor(CARD_BG))
            grad.setColorAt(1, QColor("#1e1e42"))
            painter.setBrush(grad)
            painter.setPen(QPen(QColor(CARD_BORDER), 2))
            painter.drawRoundedRect(rect, 16, 16)

            accent_rect = rect.adjusted(0, 0, 0, -(rect.height() - 4))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(ACCENT))
            painter.drawRoundedRect(accent_rect, 16, 16)

            painter.setPen(QColor(TEXT_PRIMARY))
            font = QFont("Segoe UI", 22)
            painter.setFont(font)
            text_option = QTextOption(Qt.AlignmentFlag.AlignCenter)
            text_option.setWrapMode(QTextOption.WrapMode.WordWrap)
            text_rect = QRectF(float(rect.x() + 30), float(rect.y() + 30),
                               float(rect.width() - 60), float(rect.height() - 60))
            painter.drawText(text_rect, self.text, text_option)
        except Exception as e:
            import traceback; traceback.print_exc()
            print(f"CRASH IN paintEvent: {e}")


# ══════════════════════════════════════════════════════════════════════════════
#  Main Application Window
# ══════════════════════════════════════════════════════════════════════════════

class FlashcardApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FlashForge — AI Flashcard Studio")
        self.resize(750, 550)
        self.setStyleSheet(STYLESHEET)

        self.flashcards = []
        self.current_card_index = 0
        self.is_front = True

        # Audio (for Read-Aloud)
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.temp_audio_file = None

        os.makedirs(FLASHCARD_DIR, exist_ok=True)

        # Stacked pages
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self._build_start_page()       # 0
        self._build_upload_page()      # 1
        self._build_select_page()      # 2
        self._build_study_page()       # 3
        self._build_end_page()         # 4
        self._build_editor_page()      # 5

        self.stack.setCurrentIndex(0)

    # ─── helpers ──────────────────────────────────────────────────────────
    def _heading(self, text, size=26):
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setFont(QFont("Segoe UI", size, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {TEXT_PRIMARY};")
        return lbl

    def _subtitle(self, text):
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setFont(QFont("Segoe UI", 12))
        lbl.setStyleSheet(f"color: {TEXT_SECONDARY};")
        return lbl

    def _back_btn(self, label="← Back to Home"):
        btn = QPushButton(label)
        btn.setObjectName("secondary")
        btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        return btn

    def _nav(self, index):
        """Return a slot that switches to *index* (reloads decks if needed)."""
        def go():
            if index == 2:
                self._load_decks(self.study_deck_list)
            elif index == 5:
                self._load_decks(self.editor_deck_list)
            self.stack.setCurrentIndex(index)
        return go

    # ─── page 0: Start / Home ────────────────────────────────────────────
    def _build_start_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(60, 40, 60, 40)
        layout.setSpacing(16)

        layout.addStretch()
        layout.addWidget(self._heading("⚡ FlashForge", 32))
        layout.addWidget(self._subtitle("AI-powered flashcard studio"))
        layout.addSpacing(30)

        btn_upload = QPushButton("📄  Upload PDF / Word Doc")
        btn_upload.clicked.connect(self._nav(1))

        btn_study = QPushButton("📖  Study Flashcards")
        btn_study.clicked.connect(self._nav(2))

        btn_edit = QPushButton("✏️  Edit Flashcard Decks")
        btn_edit.clicked.connect(self._nav(5))

        btn_quit = QPushButton("✕  Quit")
        btn_quit.setObjectName("danger")
        btn_quit.clicked.connect(self.close)

        for b in (btn_upload, btn_study, btn_edit):
            b.setMinimumHeight(48)
            layout.addWidget(b)

        layout.addSpacing(10)
        btn_quit.setMinimumHeight(42)
        layout.addWidget(btn_quit)
        layout.addStretch()

        self.stack.addWidget(page)

    # ─── page 1: Upload ──────────────────────────────────────────────────
    def _build_upload_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(50, 30, 50, 30)
        layout.setSpacing(14)

        layout.addWidget(self._heading("Upload a Document"))
        layout.addWidget(self._subtitle(
            "Select a PDF or Word document and we'll generate flashcards with AI."
        ))
        layout.addSpacing(10)

        self.upload_status = QLabel("")
        self.upload_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.upload_status.setWordWrap(True)
        layout.addWidget(self.upload_status)

        btn_pick = QPushButton("📂  Choose File")
        btn_pick.setMinimumHeight(48)
        btn_pick.clicked.connect(self._upload_file)
        layout.addWidget(btn_pick)

        layout.addStretch()
        layout.addWidget(self._back_btn())

        self.stack.addWidget(page)

    # ─── page 2: Deck selection (for study) ──────────────────────────────
    def _build_select_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(50, 30, 50, 30)
        layout.setSpacing(14)

        layout.addWidget(self._heading("Select a Deck to Study"))
        layout.addWidget(self._subtitle("Click any deck below to start reviewing."))

        self.study_deck_list = QListWidget()
        self.study_deck_list.itemClicked.connect(self._start_study)
        layout.addWidget(self.study_deck_list, stretch=1)

        layout.addWidget(self._back_btn())
        self.stack.addWidget(page)

    # ─── page 3: Study (flashcard viewer) ────────────────────────────────
    def _build_study_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(10)

        # Deck name label
        self.study_deck_name = QLabel("")
        self.study_deck_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.study_deck_name.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        layout.addWidget(self.study_deck_name)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

        # Flashcard widget
        self.card_widget = FlashcardWidget()
        self.card_widget.clicked.connect(self._flip_card)
        layout.addWidget(self.card_widget, stretch=1)

        # Side label (front / back)
        self.side_label = QLabel("FRONT")
        self.side_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.side_label.setFont(QFont("Segoe UI", 11))
        self.side_label.setStyleSheet(f"color: {TEXT_SECONDARY};")
        layout.addWidget(self.side_label)

        # Controls
        ctrl = QHBoxLayout()
        self.btn_prev = QPushButton("◀ Prev")
        self.btn_prev.clicked.connect(self._prev_card)
        self.btn_flip = QPushButton("Flip")
        self.btn_flip.clicked.connect(self._flip_card)
        self.btn_read = QPushButton("🔊 Read")
        self.btn_read.clicked.connect(self._read_aloud)
        self.btn_next = QPushButton("Next ▶")
        self.btn_next.clicked.connect(self._next_card)

        for b in (self.btn_prev, self.btn_flip, self.btn_read, self.btn_next):
            b.setMinimumHeight(42)
            ctrl.addWidget(b)
        layout.addLayout(ctrl)

        # Back button
        layout.addWidget(self._back_btn())
        self.stack.addWidget(page)

    # ─── page 4: End of deck ─────────────────────────────────────────────
    def _build_end_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(60, 40, 60, 40)
        layout.setSpacing(16)

        layout.addStretch()
        layout.addWidget(self._heading("🎉 Deck Complete!"))
        layout.addWidget(self._subtitle("You reviewed every card in this deck."))
        layout.addSpacing(20)

        btn_restart = QPushButton("🔄  Restart Deck")
        btn_restart.setMinimumHeight(44)
        btn_restart.clicked.connect(self._restart_deck)
        layout.addWidget(btn_restart)

        btn_home = QPushButton("🏠  Back to Home")
        btn_home.setObjectName("secondary")
        btn_home.setMinimumHeight(44)
        btn_home.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        layout.addWidget(btn_home)

        layout.addStretch()
        self.stack.addWidget(page)

    # ─── page 5: Deck editor ────────────────────────────────────────────
    def _build_editor_page(self):
        # Outer page with two sub-pages: deck list → card editor
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(50, 30, 50, 30)
        layout.setSpacing(14)

        # Sub-stack: 0 = deck list, 1 = card editor
        self.editor_sub_stack = QStackedWidget()

        # -- sub 0: deck list --
        sub0 = QWidget()
        sub0_layout = QVBoxLayout(sub0)
        sub0_layout.setContentsMargins(0, 0, 0, 0)
        sub0_layout.addWidget(self._heading("Edit a Deck"))
        sub0_layout.addWidget(self._subtitle("Select a deck to edit its flashcards."))

        self.editor_deck_list = QListWidget()
        self.editor_deck_list.itemClicked.connect(self._open_editor)
        sub0_layout.addWidget(self.editor_deck_list, stretch=1)

        # Delete deck button
        btn_delete_deck = QPushButton("🗑  Delete Selected Deck")
        btn_delete_deck.setObjectName("danger")
        btn_delete_deck.clicked.connect(self._delete_deck)
        sub0_layout.addWidget(btn_delete_deck)

        sub0_layout.addWidget(self._back_btn())
        self.editor_sub_stack.addWidget(sub0)

        # -- sub 1: card editor --
        sub1 = QWidget()
        sub1_layout = QVBoxLayout(sub1)
        sub1_layout.setContentsMargins(0, 0, 0, 0)

        self.editor_title = QLabel("")
        self.editor_title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.editor_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub1_layout.addWidget(self.editor_title)

        # Scrollable card rows
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.editor_container = QWidget()
        self.editor_cards_layout = QVBoxLayout(self.editor_container)
        self.editor_cards_layout.setSpacing(10)
        scroll.setWidget(self.editor_container)
        sub1_layout.addWidget(scroll, stretch=1)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_add = QPushButton("＋ Add Card")
        btn_add.clicked.connect(self._editor_add_card)
        btn_save = QPushButton("💾  Save Changes")
        btn_save.setStyleSheet(f"background-color: {SUCCESS};")
        btn_save.clicked.connect(self._editor_save)
        btn_back_editor = QPushButton("← Back")
        btn_back_editor.setObjectName("secondary")
        btn_back_editor.clicked.connect(lambda: self.editor_sub_stack.setCurrentIndex(0))

        for b in (btn_add, btn_save, btn_back_editor):
            b.setMinimumHeight(40)
            btn_row.addWidget(b)
        sub1_layout.addLayout(btn_row)

        self.editor_sub_stack.addWidget(sub1)

        layout.addWidget(self.editor_sub_stack)
        self.stack.addWidget(page)

    # ══════════════════════════════════════════════════════════════════════
    #  Deck helpers
    # ══════════════════════════════════════════════════════════════════════
    def _load_decks(self, list_widget: QListWidget):
        list_widget.clear()
        files = sorted(
            f for f in os.listdir(FLASHCARD_DIR) if f.endswith(".json")
        )
        if not files:
            QMessageBox.information(
                self, "No Decks",
                "No flashcard decks found. Upload a document first!"
            )
        for f in files:
            list_widget.addItem(f)

    # ══════════════════════════════════════════════════════════════════════
    #  Upload logic (from Ptqt6_file_upload.py)
    # ══════════════════════════════════════════════════════════════════════
    def _upload_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select a PDF or Word Document",
            "",
            "Documents (*.pdf *.docx)"
        )
        if not file_path:
            return

        # Extract text
        extracted = ""
        if file_path.endswith(".pdf"):
            with pdfplumber.open(file_path) as pdf:
                for pg in pdf.pages:
                    extracted += pg.extract_text() or ""
        elif file_path.endswith(".docx"):
            doc = Document(file_path)
            for para in doc.paragraphs:
                extracted += para.text + "\n"

        if not extracted.strip():
            QMessageBox.warning(self, "Empty File",
                                "No text could be extracted from this file.")
            return

        name, ok = QInputDialog.getText(
            self, "Name Your Flashcard Set",
            "Enter a name for this flashcard set:"
        )
        if not ok or not name.strip():
            return

        self.upload_status.setText("⏳ Sending to Gemini AI — please wait…")
        self.upload_status.repaint()
        QApplication.processEvents()

        flashcards = self._generate_flashcards(extracted)
        if flashcards:
            self._save_flashcards(name.strip(), flashcards)
            self.upload_status.setText(
                f"\u2705 Saved '{name.strip()}' with {len(flashcards)} cards!"

            )
        else:
            self.upload_status.setText("❌ Failed to generate flashcards.")

    def _generate_flashcards(self, text):
        try:
            model = genai.GenerativeModel(
                "gemini-2.5-flash",
                system_instruction=(
                    "You are a flashcard generator. Given text, extract key terms "
                    "and their definitions and return ONLY a JSON array in this "
                    'exact format with no extra text:\n'
                    '[{"term": "...", "answer": "..."}, '
                    '{"term": "...", "answer": "..."}]'
                )
            )
            response = model.generate_content(
                f"Generate flashcards from this text:\n\n{text[:6000]}"
            )
            raw = response.text.strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            return json.loads(raw)
        except Exception as e:
            print(f"AI Error: {e}")
            QMessageBox.critical(
                self, "AI Error",
                f"Something went wrong with Gemini API:\n{e}"
            )
            return None

    def _save_flashcards(self, name, flashcards):
        path = os.path.join(FLASHCARD_DIR, f"{name}.json")
        with open(path, "w") as f:
            json.dump(flashcards, f, indent=4)

    # ══════════════════════════════════════════════════════════════════════
    #  Study logic (from testlearn.py)
    def _start_study(self, item):
        filename = item.text()
        filepath = os.path.join(FLASHCARD_DIR, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                self.flashcards = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "Error",
                                 f"Failed to load deck:\n{e}")
            return

        if not self.flashcards:
            QMessageBox.warning(self, "Empty Deck",
                                "This deck has no flashcards.")
            return

        self.study_deck_name.setText(f"📚  {filename.replace('.json', '')}")
        self.current_card_index = 0
        self.is_front = True
        self._update_study_display(animate=False)
        self.stack.setCurrentIndex(3)

    def _update_study_display(self, animate=True):
        card = self.flashcards[self.current_card_index]
        text = card.get("term", "") if self.is_front else card.get("answer", "")

        # Progress
        total = len(self.flashcards)
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(self.current_card_index + 1)
        self.progress_bar.setFormat(
            f"Card {self.current_card_index + 1} / {total}"
        )

        self.side_label.setText("FRONT — Term" if self.is_front else "BACK — Answer")

        if animate:
            self.card_widget.flip_to_text(text)
        else:
            self.card_widget.setText(text)

    def _flip_card(self):
        self.is_front = not self.is_front
        self._update_study_display(animate=True)

    def _next_card(self):
        self.current_card_index += 1
        if self.current_card_index >= len(self.flashcards):
            self.stack.setCurrentIndex(4)
        else:
            self.is_front = True
            self._update_study_display(animate=False)

    def _prev_card(self):
        if self.current_card_index > 0:
            self.current_card_index -= 1
            self.is_front = True
            self._update_study_display(animate=False)

    def _restart_deck(self):
        self.current_card_index = 0
        self.is_front = True
        self._update_study_display(animate=False)
        self.stack.setCurrentIndex(3)

    def _read_aloud(self):
        if ELEVENLABS_API_KEY == "YOUR_API_KEY_HERE":
            QMessageBox.information(
                self, "API Key Needed",
                "Set ELEVENLABS_API_KEY in your .env to use Read Aloud."
            )
            return

        card = self.flashcards[self.current_card_index]
        text = card.get("term", "") if self.is_front else card.get("answer", "")

        url = "https://api.elevenlabs.io/v1/text-to-speech/21m00Tcm4TlvDq8ikWAM"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": ELEVENLABS_API_KEY,
        }
        data = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.5},
        }
        try:
            resp = requests.post(url, json=data, headers=headers)
            if resp.status_code == 200:
                fd, path = tempfile.mkstemp(suffix=".mp3")
                with os.fdopen(fd, "wb") as f:
                    f.write(resp.content)
                self.temp_audio_file = path
                self.player.setSource(QUrl.fromLocalFile(path))
                self.player.play()
            else:
                QMessageBox.warning(self, "API Error",
                                    f"ElevenLabs error: {resp.text}")
        except Exception as e:
            QMessageBox.critical(self, "Error",
                                 f"Could not reach ElevenLabs:\n{e}")

    # ══════════════════════════════════════════════════════════════════════
    #  Editor logic (new feature)
    # ══════════════════════════════════════════════════════════════════════
    def _open_editor(self, item):
        filename = item.text()
        self._editor_filename = filename
        filepath = os.path.join(FLASHCARD_DIR, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                cards = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Cannot open deck:\n{e}")
            return

        self.editor_title.setText(f"Editing: {filename.replace('.json', '')}")
        self._editor_rows = []

        # Clear old rows
        while self.editor_cards_layout.count():
            child = self.editor_cards_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        for i, card in enumerate(cards):
            self._add_editor_row(card.get("term", ""), card.get("answer", ""))

        # Spacer at end
        self.editor_cards_layout.addStretch()
        self.editor_sub_stack.setCurrentIndex(1)

    def _add_editor_row(self, term="", answer=""):
        """Add one editable card row to the editor."""
        frame = QFrame()
        frame.setStyleSheet(
            f"QFrame {{ background-color: {BG_CARD}; "
            f"border: 1px solid {CARD_BORDER}; border-radius: 8px; "
            f"padding: 10px; }}"
        )
        row_layout = QVBoxLayout(frame)
        row_layout.setSpacing(6)

        label_term = QLabel("Term")
        label_term.setFont(QFont("Segoe UI", 10))
        label_term.setStyleSheet(f"color: {TEXT_SECONDARY}; border: none;")
        term_edit = QLineEdit(term)

        label_ans = QLabel("Answer")
        label_ans.setFont(QFont("Segoe UI", 10))
        label_ans.setStyleSheet(f"color: {TEXT_SECONDARY}; border: none;")
        ans_edit = QLineEdit(answer)

        btn_del = QPushButton("🗑 Remove")
        btn_del.setObjectName("danger")
        btn_del.setMaximumWidth(120)
        btn_del.clicked.connect(lambda checked, f=frame: self._editor_remove_row(f))

        row_layout.addWidget(label_term)
        row_layout.addWidget(term_edit)
        row_layout.addWidget(label_ans)
        row_layout.addWidget(ans_edit)
        row_layout.addWidget(btn_del, alignment=Qt.AlignmentFlag.AlignRight)

        self._editor_rows.append((frame, term_edit, ans_edit))

        # Insert before stretch if it exists
        idx = max(0, self.editor_cards_layout.count() - 1)
        self.editor_cards_layout.insertWidget(idx, frame)

    def _editor_remove_row(self, frame):
        self._editor_rows = [
            (f, t, a) for f, t, a in self._editor_rows if f is not frame
        ]
        frame.deleteLater()

    def _editor_add_card(self):
        self._add_editor_row()

    def _editor_save(self):
        cards = []
        for _, term_edit, ans_edit in self._editor_rows:
            t = term_edit.text().strip()
            a = ans_edit.text().strip()
            if t or a:
                cards.append({"term": t, "answer": a})

        filepath = os.path.join(FLASHCARD_DIR, self._editor_filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(cards, f, indent=4)

        QMessageBox.information(
            self, "Saved!",
            f"Saved {len(cards)} card(s) to {self._editor_filename}."
        )

    def _delete_deck(self):
        item = self.editor_deck_list.currentItem()
        if not item:
            QMessageBox.warning(self, "No Selection",
                                "Select a deck first.")
            return
        filename = item.text()
        reply = QMessageBox.question(
            self, "Delete Deck?",
            f"Are you sure you want to permanently delete '{filename}'?",

            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            os.remove(os.path.join(FLASHCARD_DIR, filename))
            self._load_decks(self.editor_deck_list)

    # ── cleanup ───────────────────────────────────────────────────────────
    def closeEvent(self, event):
        if self.temp_audio_file and os.path.exists(self.temp_audio_file):
            try:
                os.remove(self.temp_audio_file)
            except OSError:
                pass
        super().closeEvent(event)


# ══════════════════════════════════════════════════════════════════════════════
#  Entry point
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    gemini_ok = init_gemini()
    if not gemini_ok:
        print("[WARNING] Gemini API key not set or invalid. "
              "Upload feature will not work.")

    app = QApplication(sys.argv)
    window = FlashcardApp()
    window.show()
    sys.exit(app.exec())
