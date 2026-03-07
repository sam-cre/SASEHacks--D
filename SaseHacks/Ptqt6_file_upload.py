from PyQt6.QtWidgets import (QApplication, QPushButton, QWidget, QVBoxLayout, 
                              QMessageBox, QFileDialog, QTextEdit, QInputDialog)
import sys
import os
import json
import pdfplumber
from docx import Document
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
API_KEYS=[
    os.getenv('OPENROUTER_API_KEY_1'),
]
def get_working_client():
    for key in API_KEYS:
        if not key:
            continue
        try:
            client = OpenAI(api_key=key, base_url="https://openrouter.ai/api/v1")
            # Test the key with a minimal request
            client.chat.completions.create(
                model="openai/gpt-4o",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            print(f"Working key found: {key[:8]}...")
            return client
        except Exception as e:
            print(f"Key failed: {key[:8]}... -> {e}")
            continue
    return None

client = get_working_client()
if client is None:
    print("ERROR: No working API keys found. Check your .env file.")
    sys.exit(1)

FLASHCARD_DIR = "FlashcardUploads"

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        os.makedirs(FLASHCARD_DIR, exist_ok=True)  # Creates FlashcardUploads folder if it doesn't exist

    def init_ui(self):
        layout = QVBoxLayout()

        self.game_btn = QPushButton("Game")
        self.game_btn.clicked.connect(self.dummy_message)

        self.learn_btn = QPushButton("Learn")
        self.learn_btn.clicked.connect(self.dummy_message)

        self.upload_btn = QPushButton("Upload PDF / Word Doc")
        self.upload_btn.clicked.connect(self.upload_file)

        layout.addWidget(self.game_btn)
        layout.addWidget(self.learn_btn)
        layout.addWidget(self.upload_btn)
        self.setLayout(layout)

    def upload_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select a PDF or Word Document",
            "",
            "Documents (*.pdf *.docx)"
        )

        if not file_path:
            return

        extracted_text = ""

        if file_path.endswith(".pdf"):
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    extracted_text += page.extract_text() or ""

        elif file_path.endswith(".docx"):
            doc = Document(file_path)
            for para in doc.paragraphs:
                extracted_text += para.text + "\n"

        if not extracted_text.strip():
            QMessageBox.warning(self, "Empty File", "No text could be extracted from this file.")
            return

        # Ask user to name their flashcard set
        name, ok = QInputDialog.getText(self, "Name Your Flashcard Set", "Enter a name for this flashcard set:")
        if not ok or not name.strip():
            return

        QMessageBox.information(self, "Generating...", "Sending to AI, please wait a moment.")

        flashcards = self.generate_flashcards(extracted_text)

        if flashcards:
            self.save_flashcards(name.strip(), flashcards)
        else:
            QMessageBox.warning(self, "Error", "Failed to generate flashcards from the document.")

    def generate_flashcards(self, text):
        try:
            response = client.chat.completions.create(
                model="openai/gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a flashcard generator. Given text, extract key terms and their definitions "
                            "and return ONLY a JSON array in this exact format with no extra text:\n"
                            '[{"term": "...", "answer": "..."}, {"term": "...", "answer": "..."}]'
                        )
                    },
                    {
                        "role": "user",
                        "content": f"Generate flashcards from this text:\n\n{text[:6000]}"  # cap to avoid token limits
                    }
                ]
            )

            raw = response.choices[0].message.content.strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            flashcards = json.loads(raw)
            return flashcards

        except Exception as e:
            print("FULL ERROR:", e)
            QMessageBox.critical(self, "AI Error", f"Something went wrong with OpenAI:\n{str(e)}")
            return None

    def save_flashcards(self, name, flashcards):
        file_path = os.path.join(FLASHCARD_DIR, f"{name}.json")

        with open(file_path, "w") as f:
            json.dump(flashcards, f, indent=4)

        QMessageBox.information(
            self,
            "Saved!",
            f"Flashcard set '{name}' saved with {len(flashcards)} cards.\n\nLocation: {file_path}"
        )

    def dummy_message(self):
        msg = QMessageBox()
        msg.setText("Feature coming soon!")
        msg.exec()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())