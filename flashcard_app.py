"""
FlashQuest — Arcade Flashcard Studio
Arcade-cabinet themed study tool with Gemini AI flashcard generation,
3D-flip study mode, deck editor, and ElevenLabs TTS.
"""
import sys, os, json, math, tempfile
import requests
import pdfplumber
from docx import Document
import google.generativeai as genai
from dotenv import load_dotenv

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStackedWidget, QListWidget, QListWidgetItem, QListView,
    QMessageBox, QFileDialog, QScrollArea, QLineEdit, QSizePolicy,
    QFrame, QProgressBar, QGraphicsOpacityEffect, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import (
    Qt, QUrl, QSize, pyqtSignal, pyqtProperty,
    QPropertyAnimation, QEasingCurve, QRectF, QSequentialAnimationGroup, QTimer
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtGui import (
    QFont, QPainter, QTransform, QPen, QColor, QTextOption,
    QLinearGradient, QPixmap, QFontDatabase, QIcon
)

# ── Configuration ──────────────────────────────────────────────────────
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "YOUR_API_KEY_HERE")
FLASHCARD_DIR = "FlashcardUploads"
ASSET_DIR = os.path.dirname(os.path.abspath(__file__))

# ── CRT Green Palette ─────────────────────────────────────────────────
CRT_BG     = "#483D8B"
CRT_DARK   = "#071428"
CRT_DIM    = "#4a6a9a"
CRT_GREEN  = "#1e5fa8"
CRT_MED    = "#7aabdc"
CRT_BRIGHT = "#ffffff"
DANGER_RED = "#ff4444"
SUCCESS_GR = "#51cf66"

# ── Pixel Font ─────────────────────────────────────────────────────────
PIXEL_FONT = "Press Start 2P"
FALLBACK   = "Courier New"

SIZE_OFFSET = 3

def get_font(size=10, bold=False):
    f = QFont(PIXEL_FONT, size + SIZE_OFFSET)
    if not f.exactMatch():
        f = QFont(FALLBACK, size + SIZE_OFFSET)
    if bold:
        f.setBold(True)
    return f

# ── Gemini Init ────────────────────────────────────────────────────────
def init_gemini():
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


# ══ Scanline Overlay ══════════════════════════════════════════════════
class ScanlineOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 40))
        for y in range(0, self.height(), 4):
            p.drawRect(0, y, self.width(), 2)
        p.end()


# ══ Flashcard Widget (3D flip) ════════════════════════════════════════
class FlashcardWidget(QWidget):
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

    @pyqtProperty(float)
    def rotationY(self): return self._rotation_y

    @rotationY.setter
    def rotationY(self, v):
        self._rotation_y = v
        self.update()

    def setText(self, t):
        self.text = t; self.update()

    def flip_to_text(self, t):
        if t == self.text: return
        self._next_text = t
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

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

    def paintEvent(self, event):
        try:
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            s = max(abs(math.cos(math.radians(self._rotation_y))), 0.01)
            t = QTransform()
            cx = self.width() / 2.0
            t.translate(cx, 0); t.scale(s, 1.0); t.translate(-cx, 0)
            p.setTransform(t)
            r = self.rect().adjusted(6, 6, -6, -6)
            # Shadow
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(0, 0, 0, 80))
            p.drawRoundedRect(r.adjusted(3, 3, 3, 3), 10, 10)
            # Card body
            g = QLinearGradient(float(r.topLeft().x()), float(r.topLeft().y()),
                                float(r.bottomRight().x()), float(r.bottomRight().y()))
            g.setColorAt(0, QColor("#0a1a0a"))
            g.setColorAt(1, QColor("#061206"))
            p.setBrush(g)
            p.setPen(QPen(QColor(CRT_GREEN), 2))
            p.drawRoundedRect(r, 10, 10)
            # Accent line
            ar = r.adjusted(0, 0, 0, -(r.height() - 3))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(CRT_GREEN))
            p.drawRoundedRect(ar, 10, 10)
            # Text
            p.setPen(QColor(CRT_BRIGHT))
            p.setFont(get_font(11))
            to = QTextOption(Qt.AlignmentFlag.AlignCenter)
            to.setWrapMode(QTextOption.WrapMode.WordWrap)
            tr = QRectF(float(r.x()+15), float(r.y()+15),
                        float(r.width()-30), float(r.height()-30))
            p.drawText(tr, self.text, to)
        except Exception:
            import traceback; traceback.print_exc()


# ══ Main Application ══════════════════════════════════════════════════
class FlashcardApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FlashQuest — Arcade Flashcard Studio")
        self.resize(700, 850)
        self.setMinimumSize(500, 600)
        self.flashcards = []
        self.current_card_index = 0
        self.is_front = True

        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.temp_audio_file = None
        os.makedirs(FLASHCARD_DIR, exist_ok=True)
        self._load_pixel_font()

        # Central widget — absolute positioning
        self.central = QWidget()
        self.setCentralWidget(self.central)
        self.central.setStyleSheet("background: transparent;")

        # Base background (background.png, fills entire window)
        self.bg_back_label = QLabel(self.central)
        self.bg_back_label.setScaledContents(True)
        back_path = os.path.join(ASSET_DIR, "NONIMPORTEDASSETS", "background.png")
        self.bg_back_pixmap = QPixmap(back_path) if os.path.exists(back_path) else QPixmap()
        if not self.bg_back_pixmap.isNull():
            self.bg_back_label.setPixmap(self.bg_back_pixmap)

        # Arcade machine overlay (sits on top of background)
        self.bg_label = QLabel(self.central)
        self.bg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.bg_label.setScaledContents(False)
        self.bg_label.setStyleSheet("background: transparent;")
        bg_path = os.path.join(ASSET_DIR, "NONIMPORTEDASSETS", "arcade macine.png")
        self.bg_pixmap = QPixmap(bg_path) if os.path.exists(bg_path) else QPixmap()


        # Glow animation on arcade machine
        self._glow_effect = QGraphicsDropShadowEffect()
        self._glow_effect.setOffset(0, 0)
        self._glow_effect.setColor(QColor(255, 255, 255, 180))
        self._glow_effect.setBlurRadius(40)
        self.bg_label.setGraphicsEffect(self._glow_effect)
        glow_out = QPropertyAnimation(self._glow_effect, b"blurRadius")
        glow_out.setDuration(2000); glow_out.setStartValue(20); glow_out.setEndValue(80)
        glow_out.setEasingCurve(QEasingCurve.Type.InOutSine)
        glow_in = QPropertyAnimation(self._glow_effect, b"blurRadius")
        glow_in.setDuration(2000); glow_in.setStartValue(80); glow_in.setEndValue(20)
        glow_in.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._glow_anim = QSequentialAnimationGroup()
        self._glow_anim.addAnimation(glow_out)
        self._glow_anim.addAnimation(glow_in)
        self._glow_anim.setLoopCount(-1)
        self._glow_anim.start()

        # Marquee title label (sits in the black space above the CRT screen)
        self.marquee_lbl = QLabel("FLASHQUEST", self.central)
        self.marquee_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.marquee_lbl.setFont(get_font(18, bold=True))
        self.marquee_lbl.setStyleSheet(f"color: {CRT_BRIGHT}; background: transparent;")

        # CRT screen overlay
        self.crt_screen = QWidget(self.central)
        _forest = os.path.join(ASSET_DIR, "NONIMPORTEDASSETS", "breach.jpg").replace("\\", "/")
        self.crt_screen.setStyleSheet(
            f"border-image: url('{_forest}') 0 0 0 0 stretch stretch;"
            f"border-radius: 8px;"
        )
        crt_layout = QVBoxLayout(self.crt_screen)
        crt_layout.setContentsMargins(8, 8, 8, 8)
        self.stack = QStackedWidget()
        crt_layout.addWidget(self.stack)


        # Scanline overlay
        self.scanline = ScanlineOverlay(self.central)

        # Build pages: 0=START, 1=MainMenu, 2=FlashcardsMenu,
        #   3=Upload, 4=DeckSelect, 5=Study, 6=End, 7=Editor
        self._build_start_page()
        self._build_main_menu()
        self._build_flashcards_menu()
        self._build_upload_page()
        self._build_select_page()
        self._build_study_page()
        self._build_end_page()
        self._build_editor_page()
        self.stack.setCurrentIndex(0)


    def _load_pixel_font(self):
        global PIXEL_FONT
        fp = os.path.join(ASSET_DIR, "PressStart2P-Regular.ttf")
        if os.path.exists(fp):
            fid = QFontDatabase.addApplicationFont(fp)
            if fid >= 0:
                fams = QFontDatabase.applicationFontFamilies(fid)
                if fams:
                    PIXEL_FONT = fams[0]
                    return
        print("[INFO] Pixel font not found, using fallback")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w, h = self.central.width(), self.central.height()
        self.bg_back_label.setGeometry(0, 0, w, h)
        self.bg_label.setGeometry(0, 0, w, h)

        if not self.bg_pixmap.isNull():
            scaled = self.bg_pixmap.scaled(
                w, h, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation)
            self.bg_label.setPixmap(scaled)

            # Compute where the image is actually rendered (centered in the label)
            img_w, img_h = scaled.width(), scaled.height()
            img_x = (w - img_w) // 2
            img_y = (h - img_h) // 2
        else:
            img_x, img_y, img_w, img_h = 0, 0, w, h

        # These fractions describe where the white CRT area sits within the arcade image
        # (tune these if the overlay is still slightly off)
        cx = img_x + int(img_w * 0.33) + 1
        cy = img_y + int(img_h * 0.29) + 3
        cw = int(img_w * 0.34)
        ch = int(img_h * 0.37)

        self.crt_screen.setGeometry(cx, cy, cw, ch)
        self.scanline.setGeometry(cx, cy, cw, ch)
        self.scanline.raise_()


        # Marquee sits in the top blue header of the cabinet
        mx = img_x + int(img_w * 0.20)
        my = img_y + int(img_h * 0.04)
        mw = int(img_w * 0.60)
        mh = int(img_h * 0.18)
        self.marquee_lbl.setGeometry(mx, my, mw, mh)
        self.marquee_lbl.raise_()

    # ─── UI helpers ────────────────────────────────────────────────────
    def _lbl(self, text, sz=9, color=CRT_BRIGHT):
        l = QLabel(text)
        l.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.setFont(get_font(sz))
        l.setStyleSheet(f"QLabel{{color: {color}; background-color: {CRT_BG}; border-image: none; border: 1px solid black; border-radius: 3px; padding: 2px 4px;}}"
                        f"QLabel:hover{{border: 1px solid white;}}")
        l.setWordWrap(True)
        return l

    def _mbtn(self, text, sz=8):
        b = QPushButton(f"  {text}")
        b.setFont(get_font(sz))
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b._slide_p = 0.0
        b._slide_tgt = 0.0

        def _apply(btn):
            pl = 6 + btn._slide_p * 14
            btn.setStyleSheet(
                f"QPushButton{{background-color:{CRT_BG};color:{CRT_BRIGHT};"
                f"border-image:none;border:none;padding:3px 6px 3px {pl:.1f}px;"
                f"text-align:left;border-radius:4px;}}"
                f"QPushButton:hover{{background-color:{CRT_GREEN};color:#ffffff;}}")

        def _tick():
            b._slide_p += (b._slide_tgt - b._slide_p) * 0.12
            _apply(b)

        timer = QTimer(b)
        timer.setInterval(16)
        timer.timeout.connect(_tick)
        timer.start()

        b.enterEvent = lambda e: setattr(b, '_slide_tgt', 1.0)
        b.leaveEvent = lambda e: setattr(b, '_slide_tgt', 0.0)
        _apply(b)
        return b

    def _abtn(self, text, sz=7):
        b = QPushButton(text)
        b.setFont(get_font(sz))
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setStyleSheet(f"QPushButton{{background-color:{CRT_BG};color:{CRT_BRIGHT};"
                         f"border-image:none;border:1px solid {CRT_MED};border-radius:4px;padding:4px 8px;}}"
                         f"QPushButton:hover{{color:#ffffff;border-color:#ffffff;"
                         f"background-color:{CRT_GREEN};}}")
        return b

    def _bbtn(self, target=0):
        b = self._mbtn("< BACK", 9)
        b.setText("< BACK")
        # Remove slide animation from back button
        for child in b.findChildren(QTimer):
            child.stop()
        b.enterEvent = lambda e: None
        b.leaveEvent = lambda e: None
        b.setStyleSheet(f"QPushButton{{background-color:{CRT_BG};color:{CRT_BRIGHT};"
                         f"border-image:none;border:1px solid {CRT_MED};border-radius:4px;padding:6px 14px;"
                         f"text-align:center;margin-top:8px;}}"
                         f"QPushButton:hover{{color:#ffffff;border-color:#ffffff;"
                         f"background-color:{CRT_GREEN};}}")
        b.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)
        b.clicked.connect(lambda: self.stack.setCurrentIndex(target))
        return b

    _LS = (f"QListWidget{{background-color:{CRT_DARK};border:1px solid {CRT_GREEN};"
           f"border-radius:4px;padding:4px;color:{CRT_BRIGHT};outline:none;}}"
           f"QListWidget::item{{padding:4px;border-radius:3px;}}"
           f"QListWidget::item:hover{{background:rgba(58,122,58,0.2);color:{CRT_BRIGHT};}}"
           f"QListWidget::item:selected{{background:{CRT_GREEN};color:{CRT_BG};}}")

    def _page(self):
        p = QWidget()
        p.setStyleSheet("background-color: transparent; border-image: none;")
        return p

    # ─── page 0: START ─────────────────────────────────────────────────
    def _build_start_page(self):
        pg = self._page()
        ly = QVBoxLayout(pg); ly.setContentsMargins(10,10,10,10)

        # Floating container — START label is absolutely positioned inside
        float_widget = QWidget()
        float_widget.setFixedHeight(100)
        float_widget.setStyleSheet("background: transparent; border-image: none;")
        self.start_lbl = QLabel("START", float_widget)
        self.start_lbl.setFont(get_font(20, bold=True))
        self.start_lbl.setStyleSheet(
            "color: #ffffff; background-color: #483D8B; border-image: none;"
            "border: 2px solid #1e5fa8; border-radius: 6px; padding: 8px 24px;"
        )
        self.start_lbl.adjustSize()

        self.start_lbl.setCursor(Qt.CursorShape.PointingHandCursor)

        ly.addStretch()
        ly.addWidget(float_widget)
        ly.addStretch()

        # PRESS START TO BEGIN at the bottom, no background
        press_lbl = QLabel("PRESS START TO BEGIN")
        press_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        press_lbl.setFont(get_font(6))
        press_lbl.setStyleSheet(f"color: {CRT_BRIGHT}; background: transparent; border-image: none;")
        ly.addWidget(press_lbl)

        # Hover tracking
        self._hover_p = 0.0   # 0=normal, 1=hovered
        self._hover_tgt = 0.0
        def on_enter(e): self._hover_tgt = 1.0
        def on_leave(e): self._hover_tgt = 0.0
        self.start_lbl.enterEvent = on_enter
        self.start_lbl.leaveEvent = on_leave

        # Combined float + smooth hover timer (~60fps)
        self._float_t = 0.0
        def do_float():
            self._float_t += 0.025

            # Smooth lerp hover progress
            self._hover_p += (self._hover_tgt - self._hover_p) * 0.06

            # Font stays fixed — only padding grows (smooth, no integer jumps)
            pad_v = 8  + self._hover_p * 12
            pad_h = 24 + self._hover_p * 22

            self.start_lbl.setFont(get_font(20, bold=True))
            self.start_lbl.setStyleSheet(
                f"color: #ffffff; background-color: #483D8B; border-image: none;"
                f"border: 2px solid #1e5fa8; border-radius: 6px;"
                f"padding: {pad_v:.1f}px {pad_h:.1f}px;"
            )

            offset = int(math.sin(self._float_t) * 8)
            self.start_lbl.adjustSize()
            x = max(0, (float_widget.width() - self.start_lbl.width()) // 2)
            y = (float_widget.height() - self.start_lbl.height()) // 2 + offset
            self.start_lbl.move(x, y)

        self._float_timer = QTimer()
        self._float_timer.setInterval(16)
        self._float_timer.timeout.connect(do_float)
        self._float_timer.start()

        pg.mousePressEvent = lambda e: self.stack.setCurrentIndex(1)
        self.start_lbl.mousePressEvent = lambda e: self.stack.setCurrentIndex(1)
        self.stack.addWidget(pg)

    # ─── page 1: Main Menu ─────────────────────────────────────────────
    def _build_main_menu(self):
        pg = self._page()
        ly = QVBoxLayout(pg); ly.setContentsMargins(10,10,10,10); ly.setSpacing(4)
        ly.addStretch()
        lbl_sel = self._lbl("- SELECT -", 8, CRT_MED)
        lbl_sel.setStyleSheet(lbl_sel.styleSheet().replace("border: 1px solid black;", "border: none;").replace("QLabel:hover{border: 1px solid white;}", ""))
        ly.addWidget(lbl_sel)
        ly.addSpacing(8)
        for txt, cb in [("FLASHCARDS", lambda: self.stack.setCurrentIndex(2)),
                        ("ENTER THE DUNGEON", lambda: QMessageBox.information(
                            self, "Coming Soon", "The Dungeon is under construction!")),
                        ("SETTINGS", lambda: QMessageBox.information(
                            self, "Settings", "Settings coming soon!"))]:
            b = self._mbtn(txt, 8); b.clicked.connect(cb)
            b.setStyleSheet(b.styleSheet().replace("padding:3px 6px", "padding:5px 6px"))
            ly.addWidget(b)
        ly.addSpacing(8)
        ly.addWidget(self._bbtn(0), alignment=Qt.AlignmentFlag.AlignCenter)
        ly.addStretch()
        self.stack.addWidget(pg)

    # ─── page 2: Flashcards Sub-Menu ───────────────────────────────────
    def _build_flashcards_menu(self):
        pg = self._page()
        ly = QVBoxLayout(pg); ly.setContentsMargins(10,10,10,10); ly.setSpacing(4)
        ly.addStretch()
        lbl_fc = self._lbl("- FLASHCARDS -", 8, CRT_MED)
        lbl_fc.setStyleSheet(lbl_fc.styleSheet().replace("border: 1px solid black;", "border: none;").replace("QLabel:hover{border: 1px solid white;}", ""))
        ly.addWidget(lbl_fc)
        ly.addSpacing(8)
        for txt, cb in [("UPLOAD DOC", lambda: self.stack.setCurrentIndex(3)),
                        ("STUDY DECK", self._go_study),
                        ("EDIT DECK", self._go_editor)]:
            b = self._mbtn(txt, 8); b.clicked.connect(cb)
            b.setStyleSheet(b.styleSheet().replace("padding:3px 6px", "padding:5px 6px"))
            ly.addWidget(b)
        ly.addSpacing(8)
        ly.addWidget(self._bbtn(1), alignment=Qt.AlignmentFlag.AlignCenter)
        ly.addStretch()
        self.stack.addWidget(pg)

    def _go_study(self):
        self._load_decks(self.study_deck_list); self.stack.setCurrentIndex(4)

    def _go_editor(self):
        self._load_decks(self.editor_deck_list); self.stack.setCurrentIndex(7)

    # ─── page 3: Upload ────────────────────────────────────────────────
    def _build_upload_page(self):
        pg = self._page()
        ly = QVBoxLayout(pg); ly.setContentsMargins(8,8,8,8); ly.setSpacing(6)
        lbl_upload = self._lbl("UPLOAD DOC", 9)
        lbl_upload.setStyleSheet(lbl_upload.styleSheet().replace("padding: 2px 4px", "padding: 5px 4px"))
        ly.addWidget(lbl_upload)
        lbl_sub = self._lbl("Select PDF or DOCX\nto generate flashcards", 6, CRT_DIM)
        lbl_sub.setStyleSheet(lbl_sub.styleSheet().replace("padding: 2px 4px", "padding: 5px 4px"))
        ly.addWidget(lbl_sub)
        self.upload_status = self._lbl("", 6, CRT_MED)
        ly.addWidget(self.upload_status)
        self.upload_choose_btn = self._abtn("CHOOSE FILE", 7)
        self.upload_choose_btn.clicked.connect(self._upload_file)
        ly.addWidget(self.upload_choose_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # Inline name entry (hidden until file selected)
        self.upload_name_label = self._lbl("NAME YOUR FLASHCARDS:", 6, CRT_DIM)
        self.upload_name_label.hide()
        ly.addWidget(self.upload_name_label)

        LE_SS = (f"QLineEdit{{background:{CRT_BG};border:1px solid {CRT_GREEN};"
                 f"border-radius:3px;padding:4px;color:{CRT_BRIGHT};}}"
                 f"QLineEdit:focus{{border-color:{CRT_BRIGHT};}}")
        self.upload_name_input = QLineEdit()
        self.upload_name_input.setFont(get_font(7))
        self.upload_name_input.setStyleSheet(LE_SS)
        self.upload_name_input.setPlaceholderText("e.g. Biology Chapter 3")
        self.upload_name_input.returnPressed.connect(self._upload_confirm)
        self.upload_name_input.hide()
        ly.addWidget(self.upload_name_input)

        self.upload_confirm_btn = self._abtn("GENERATE", 7)
        self.upload_confirm_btn.clicked.connect(self._upload_confirm)
        self.upload_confirm_btn.hide()
        ly.addWidget(self.upload_confirm_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        ly.addStretch()
        back = self._bbtn(2)
        back.clicked.connect(self._reset_upload_page)
        ly.addWidget(back, alignment=Qt.AlignmentFlag.AlignCenter)
        self.stack.addWidget(pg)
        self._pending_extracted = ""

    # ─── page 4: Deck Select ──────────────────────────────────────────
    def _build_select_page(self):
        pg = self._page()
        ly = QVBoxLayout(pg); ly.setContentsMargins(8,8,8,8); ly.setSpacing(4)
        ly.addStretch()
        lbl_select = self._lbl("SELECT DECK", 9)
        lbl_select.setStyleSheet(lbl_select.styleSheet().replace("padding: 2px 4px", "padding: 8px 4px").replace("border: 1px solid black;", "border: none;").replace("QLabel:hover{border: 1px solid white;}", ""))
        lbl_select.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ly.addWidget(lbl_select)
        ly.addStretch()
        self.study_deck_list = QListWidget()
        self.study_deck_list.setFont(get_font(7))
        self.study_deck_list.setStyleSheet(self._LS)
        self.study_deck_list.setViewMode(QListView.ViewMode.IconMode)
        self.study_deck_list.setIconSize(QSize(64, 64))
        self.study_deck_list.setGridSize(QSize(90, 90))
        self.study_deck_list.setResizeMode(QListView.ResizeMode.Adjust)
        self.study_deck_list.setWordWrap(True)
        self.study_deck_list.setSpacing(8)
        self.study_deck_list.itemClicked.connect(self._start_study)
        ly.addWidget(self.study_deck_list, stretch=1)
        ly.addWidget(self._bbtn(2), alignment=Qt.AlignmentFlag.AlignCenter)
        self.stack.addWidget(pg)

    # ─── page 5: Study ────────────────────────────────────────────────
    def _build_study_page(self):
        pg = self._page()
        ly = QVBoxLayout(pg); ly.setContentsMargins(6,4,6,4); ly.setSpacing(3)
        self.study_deck_name = self._lbl("", 7, CRT_MED)
        ly.addWidget(self.study_deck_name)
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFont(get_font(6))
        self.progress_bar.setFixedHeight(16)
        self.progress_bar.setStyleSheet(
            f"QProgressBar{{background:{CRT_DARK};border:1px solid {CRT_GREEN};"
            f"border-radius:3px;text-align:center;color:{CRT_BRIGHT};}}"
            f"QProgressBar::chunk{{background:{CRT_GREEN};border-radius:2px;}}")
        ly.addWidget(self.progress_bar)
        self.card_widget = FlashcardWidget()
        self.card_widget.clicked.connect(self._flip_card)
        ly.addWidget(self.card_widget, stretch=1)
        self.side_label = self._lbl("FRONT", 6, CRT_DIM)
        ly.addWidget(self.side_label)
        ctrl = QHBoxLayout(); ctrl.setSpacing(4)
        self.btn_prev = self._abtn("< PREV", 6); self.btn_prev.clicked.connect(self._prev_card)
        self.btn_flip = self._abtn("FLIP", 6); self.btn_flip.clicked.connect(self._flip_card)
        self.btn_read = self._abtn("READ", 6); self.btn_read.clicked.connect(self._read_aloud)
        self.btn_next = self._abtn("NEXT >", 6); self.btn_next.clicked.connect(self._next_card)
        for b in (self.btn_prev, self.btn_flip, self.btn_read, self.btn_next):
            ctrl.addWidget(b)
        ly.addLayout(ctrl)
        ly.addWidget(self._bbtn(2), alignment=Qt.AlignmentFlag.AlignCenter)
        self.stack.addWidget(pg)

    # ─── page 6: End ──────────────────────────────────────────────────
    def _build_end_page(self):
        pg = self._page()
        ly = QVBoxLayout(pg); ly.setContentsMargins(10,10,10,10); ly.setSpacing(6)
        ly.addStretch()
        ly.addWidget(self._lbl("DECK COMPLETE!", 10))
        ly.addWidget(self._lbl("All cards reviewed.", 7, CRT_MED))
        ly.addSpacing(10)
        br = self._abtn("RESTART", 7); br.clicked.connect(self._restart_deck)
        ly.addWidget(br, alignment=Qt.AlignmentFlag.AlignCenter)
        bh = self._abtn("HOME", 7); bh.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        ly.addWidget(bh, alignment=Qt.AlignmentFlag.AlignCenter)
        ly.addStretch()
        self.stack.addWidget(pg)

    # ─── page 7: Editor ──────────────────────────────────────────────
    def _build_editor_page(self):
        pg = self._page()
        ly = QVBoxLayout(pg); ly.setContentsMargins(6,6,6,6); ly.setSpacing(4)
        self.editor_sub_stack = QStackedWidget()

        # sub0: deck list
        s0 = self._page(); s0l = QVBoxLayout(s0); s0l.setContentsMargins(0,0,0,0); s0l.setSpacing(4)
        s0l.addWidget(self._lbl("EDIT DECK", 9))
        self.editor_deck_list = QListWidget()
        self.editor_deck_list.setFont(get_font(7))
        self.editor_deck_list.setStyleSheet(self._LS)
        self.editor_deck_list.setViewMode(QListView.ViewMode.IconMode)
        self.editor_deck_list.setIconSize(QSize(64, 64))
        self.editor_deck_list.setGridSize(QSize(90, 90))
        self.editor_deck_list.setResizeMode(QListView.ResizeMode.Adjust)
        self.editor_deck_list.setWordWrap(True)
        self.editor_deck_list.setSpacing(8)
        self.editor_deck_list.itemClicked.connect(self._open_editor)
        s0l.addWidget(self.editor_deck_list, stretch=1)
        bd = self._abtn("DELETE DECK", 6)
        bd.setStyleSheet(f"QPushButton{{background-color:{CRT_BG};color:{CRT_BRIGHT};"
                          f"border-image:none;border:1px solid {CRT_MED};border-radius:4px;padding:3px 6px;}}"
                          f"QPushButton:hover{{color:#ffffff;border-color:#ffffff;background-color:{CRT_GREEN};}}")
        bd.setFont(get_font(6)); bd.clicked.connect(self._delete_deck)
        s0l.addWidget(bd)
        s0l.addWidget(self._bbtn(2))
        self.editor_sub_stack.addWidget(s0)

        # sub1: card editor
        s1 = self._page(); s1l = QVBoxLayout(s1); s1l.setContentsMargins(0,0,0,0); s1l.setSpacing(3)
        self.editor_title = self._lbl("", 7, CRT_MED)
        s1l.addWidget(self.editor_title)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            f"QScrollArea{{background:transparent;border:none;}}"
            f"QScrollBar:vertical{{background:{CRT_DARK};width:8px;border-radius:4px;}}"
            f"QScrollBar::handle:vertical{{background:{CRT_GREEN};border-radius:4px;min-height:20px;}}"
            f"QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{{height:0;}}")
        self.editor_container = QWidget(); self.editor_container.setStyleSheet("background:transparent;")
        self.editor_cards_layout = QVBoxLayout(self.editor_container); self.editor_cards_layout.setSpacing(6)
        scroll.setWidget(self.editor_container)
        s1l.addWidget(scroll, stretch=1)
        br2 = QHBoxLayout(); br2.setSpacing(4)
        ba = self._abtn("+ ADD", 6); ba.clicked.connect(self._editor_add_card)
        bs = self._abtn("SAVE", 6)
        bs.setStyleSheet(f"QPushButton{{background:transparent;color:{SUCCESS_GR};"
                          f"border:1px solid {SUCCESS_GR};border-radius:4px;padding:3px 6px;}}"
                          f"QPushButton:hover{{background:rgba(81,207,102,0.15);}}")
        bs.setFont(get_font(6)); bs.clicked.connect(self._editor_save)
        be = self._abtn("< BACK", 6); be.clicked.connect(lambda: self.editor_sub_stack.setCurrentIndex(0))
        for b in (ba, bs, be): br2.addWidget(b)
        s1l.addLayout(br2)
        self.editor_sub_stack.addWidget(s1)

        ly.addWidget(self.editor_sub_stack)
        self.stack.addWidget(pg)

    # ══ Deck helpers ══════════════════════════════════════════════════
    def _load_decks(self, lw):
        lw.clear()
        files = sorted(f for f in os.listdir(FLASHCARD_DIR) if f.endswith(".json"))
        if not files:
            QMessageBox.information(self, "No Decks",
                                    "No flashcard decks found. Upload a document first!")
        icon_path = os.path.join(ASSET_DIR, "NONIMPORTEDASSETS", "file-full.png")
        icon = QIcon(icon_path)
        lw.setIconSize(QSize(64, 64))
        for f in files:
            item = QListWidgetItem(icon, f)
            lw.addItem(item)

    # ══ Upload logic ══════════════════════════════════════════════════
    def _upload_file(self):
        fp, _ = QFileDialog.getOpenFileName(self, "Select a PDF or Word Document", "",
                                            "Documents (*.pdf *.docx)")
        if not fp: return
        extracted = ""
        if fp.endswith(".pdf"):
            with pdfplumber.open(fp) as pdf:
                for pg in pdf.pages: extracted += pg.extract_text() or ""
        elif fp.endswith(".docx"):
            doc = Document(fp)
            for para in doc.paragraphs: extracted += para.text + "\n"
        if not extracted.strip():
            QMessageBox.warning(self, "Empty File", "No text could be extracted.")
            return
        self._pending_extracted = extracted
        self.upload_status.setText(f"File loaded. Enter a name below.")
        self.upload_choose_btn.hide()
        self.upload_name_label.show()
        self.upload_name_input.clear()
        self.upload_name_input.show()
        self.upload_name_input.setFocus()
        self.upload_confirm_btn.show()

    def _reset_upload_page(self):
        self.upload_choose_btn.show()
        self.upload_name_label.hide()
        self.upload_name_input.hide()
        self.upload_confirm_btn.hide()
        self.upload_status.setText("")
        self._pending_extracted = ""

    def _upload_confirm(self):
        name = self.upload_name_input.text().strip()
        if not name:
            self.upload_status.setText("Please enter a name.")
            return
        self.upload_name_label.hide()
        self.upload_name_input.hide()
        self.upload_confirm_btn.hide()
        self.upload_status.setText("Generating...")
        self.upload_status.repaint(); QApplication.processEvents()
        cards = self._generate_flashcards(self._pending_extracted)
        if cards:
            self._save_flashcards(name, cards)
            self.upload_status.setText(f"Saved '{name}'\n{len(cards)} cards!")
        else:
            self.upload_status.setText("Failed.")
        self._pending_extracted = ""
        self.upload_choose_btn.show()

    def _generate_flashcards(self, text):
        try:
            model = genai.GenerativeModel("gemini-2.5-flash", system_instruction=(
                "You are a flashcard generator. Given text, extract key terms "
                "and their definitions and return ONLY a JSON array in this "
                'exact format with no extra text:\n'
                '[{"term": "...", "answer": "..."}, {"term": "...", "answer": "..."}]'))
            resp = model.generate_content(f"Generate flashcards from this text:\n\n{text[:6000]}")
            raw = resp.text.strip().replace("```json", "").replace("```", "").strip()
            return json.loads(raw)
        except Exception as e:
            print(f"AI Error: {e}")
            QMessageBox.critical(self, "AI Error", f"Gemini API error:\n{e}")
            return None

    def _save_flashcards(self, name, cards):
        with open(os.path.join(FLASHCARD_DIR, f"{name}.json"), "w") as f:
            json.dump(cards, f, indent=4)

    # ══ Study logic ═══════════════════════════════════════════════════
    def _start_study(self, item):
        fp = os.path.join(FLASHCARD_DIR, item.text())
        try:
            with open(fp, "r", encoding="utf-8") as f: self.flashcards = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load deck:\n{e}"); return
        if not self.flashcards:
            QMessageBox.warning(self, "Empty Deck", "This deck has no flashcards."); return
        self.study_deck_name.setText(item.text().replace('.json', ''))
        self.current_card_index = 0; self.is_front = True
        self._update_study(animate=False); self.stack.setCurrentIndex(5)

    def _update_study(self, animate=True):
        c = self.flashcards[self.current_card_index]
        txt = c.get("term", "") if self.is_front else c.get("answer", "")
        n = len(self.flashcards)
        self.progress_bar.setMaximum(n)
        self.progress_bar.setValue(self.current_card_index + 1)
        self.progress_bar.setFormat(f"{self.current_card_index + 1} / {n}")
        self.side_label.setText("FRONT" if self.is_front else "BACK")
        if animate: self.card_widget.flip_to_text(txt)
        else: self.card_widget.setText(txt)

    def _flip_card(self):
        self.is_front = not self.is_front; self._update_study(animate=True)

    def _next_card(self):
        self.current_card_index += 1
        if self.current_card_index >= len(self.flashcards): self.stack.setCurrentIndex(6)
        else: self.is_front = True; self._update_study(animate=False)

    def _prev_card(self):
        if self.current_card_index > 0:
            self.current_card_index -= 1; self.is_front = True
            self._update_study(animate=False)

    def _restart_deck(self):
        self.current_card_index = 0; self.is_front = True
        self._update_study(animate=False); self.stack.setCurrentIndex(5)

    def _read_aloud(self):
        if ELEVENLABS_API_KEY == "YOUR_API_KEY_HERE":
            QMessageBox.information(self, "API Key Needed",
                                    "Set ELEVENLABS_API_KEY in .env to use Read Aloud.")
            return
        c = self.flashcards[self.current_card_index]
        txt = c.get("term", "") if self.is_front else c.get("answer", "")
        url = "https://api.elevenlabs.io/v1/text-to-speech/21m00Tcm4TlvDq8ikWAM"
        headers = {"Accept": "audio/mpeg", "Content-Type": "application/json",
                   "xi-api-key": ELEVENLABS_API_KEY}
        data = {"text": txt, "model_id": "eleven_multilingual_v2",
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.5}}
        try:
            r = requests.post(url, json=data, headers=headers)
            if r.status_code == 200:
                fd, path = tempfile.mkstemp(suffix=".mp3")
                with os.fdopen(fd, "wb") as f: f.write(r.content)
                self.temp_audio_file = path
                self.player.setSource(QUrl.fromLocalFile(path)); self.player.play()
            else:
                QMessageBox.warning(self, "API Error", f"ElevenLabs error: {r.text}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not reach ElevenLabs:\n{e}")

    # ══ Editor logic ══════════════════════════════════════════════════
    def _open_editor(self, item):
        fn = item.text(); self._editor_filename = fn
        fp = os.path.join(FLASHCARD_DIR, fn)
        try:
            with open(fp, "r", encoding="utf-8") as f: cards = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Cannot open deck:\n{e}"); return
        self.editor_title.setText(f"Editing: {fn.replace('.json', '')}")
        self._editor_rows = []
        while self.editor_cards_layout.count():
            ch = self.editor_cards_layout.takeAt(0)
            if ch.widget(): ch.widget().deleteLater()
        for c in cards:
            self._add_editor_row(c.get("term", ""), c.get("answer", ""))
        self.editor_cards_layout.addStretch()
        self.editor_sub_stack.setCurrentIndex(1)

    def _add_editor_row(self, term="", answer=""):
        fr = QFrame()
        fr.setStyleSheet(f"QFrame{{background:{CRT_DARK};border:1px solid {CRT_GREEN};"
                          f"border-radius:4px;padding:4px;}}")
        rl = QVBoxLayout(fr); rl.setSpacing(3); rl.setContentsMargins(4,4,4,4)
        LE_SS = (f"QLineEdit{{background:{CRT_BG};border:1px solid {CRT_GREEN};"
                 f"border-radius:3px;padding:3px;color:{CRT_BRIGHT};}}"
                 f"QLineEdit:focus{{border-color:{CRT_BRIGHT};}}")
        lt = QLabel("TERM"); lt.setFont(get_font(5))
        lt.setStyleSheet(f"color:{CRT_DIM};border:none;")
        te = QLineEdit(term); te.setFont(get_font(6)); te.setStyleSheet(LE_SS)
        la = QLabel("ANSWER"); la.setFont(get_font(5))
        la.setStyleSheet(f"color:{CRT_DIM};border:none;")
        ae = QLineEdit(answer); ae.setFont(get_font(6)); ae.setStyleSheet(LE_SS)
        bd = QPushButton("X"); bd.setFont(get_font(5))
        bd.setStyleSheet(f"QPushButton{{background:transparent;color:{DANGER_RED};"
                          f"border:1px solid {DANGER_RED};border-radius:3px;padding:2px 6px;}}"
                          f"QPushButton:hover{{background:rgba(255,68,68,0.15);}}")
        bd.setMaximumWidth(40)
        bd.clicked.connect(lambda checked, f=fr: self._editor_remove_row(f))
        rl.addWidget(lt); rl.addWidget(te); rl.addWidget(la); rl.addWidget(ae)
        rl.addWidget(bd, alignment=Qt.AlignmentFlag.AlignRight)
        self._editor_rows.append((fr, te, ae))
        idx = max(0, self.editor_cards_layout.count() - 1)
        self.editor_cards_layout.insertWidget(idx, fr)

    def _editor_remove_row(self, frame):
        self._editor_rows = [(f,t,a) for f,t,a in self._editor_rows if f is not frame]
        frame.deleteLater()

    def _editor_add_card(self): self._add_editor_row()

    def _editor_save(self):
        cards = []
        for _, te, ae in self._editor_rows:
            t, a = te.text().strip(), ae.text().strip()
            if t or a: cards.append({"term": t, "answer": a})
        fp = os.path.join(FLASHCARD_DIR, self._editor_filename)
        with open(fp, "w", encoding="utf-8") as f: json.dump(cards, f, indent=4)
        QMessageBox.information(self, "Saved!", f"Saved {len(cards)} card(s).")

    def _delete_deck(self):
        item = self.editor_deck_list.currentItem()
        if not item:
            QMessageBox.warning(self, "No Selection", "Select a deck first."); return
        fn = item.text()
        reply = QMessageBox.question(self, "Delete Deck?",
            f"Permanently delete '{fn}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            os.remove(os.path.join(FLASHCARD_DIR, fn))
            self._load_decks(self.editor_deck_list)

    def closeEvent(self, event):
        if self.temp_audio_file and os.path.exists(self.temp_audio_file):
            try: os.remove(self.temp_audio_file)
            except OSError: pass
        super().closeEvent(event)


# ══ Entry point ═══════════════════════════════════════════════════════
if __name__ == "__main__":
    gemini_ok = init_gemini()
    if not gemini_ok:
        print("[WARNING] Gemini API key not set or invalid. Upload feature will not work.")
    app = QApplication(sys.argv)
    window = FlashcardApp()
    window.show()
    sys.exit(app.exec())
