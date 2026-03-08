# SASEHacks :D

## Requirements

To run the software, you must install the following Python packages via pip:
```bash
pip install PyQt6 pdfplumber python-docx google-generativeai python-dotenv requests
```

Copied Code: 
- CSS Flip animation for flashcards
https://animista.net/play/entrances/flip-in/flip-in-ver-left

## Built With

This project is built using the following technologies:
* **[Python](https://www.python.org/)** - Core programming language
* **[Pygame](https://www.pygame.org/)** - Used for the game engine, rendering, and window management
* **[PyQt6](https://riverbankcomputing.com/software/pyqt/)** - Used for configuring the flashcard deck selector and UI elements
* **[Google Gemini API](https://ai.google.dev/)** - Powered by `google-generativeai` for dynamic flashcard generation
* **[pdfplumber](https://github.com/jsvine/pdfplumber) & [python-docx](https://python-docx.readthedocs.io/)** - Used for extracting text from uploaded study documents
* **[python-dotenv](https://saurabh-kumar.com/python-dotenv/)** - For managing environment variables securely
* **[Requests](https://requests.readthedocs.io/)** - HTTP library for making API calls