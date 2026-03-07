# SASEHacks :D

## Requirements

To run the software, you must install the following Python packages via pip:
```bash
pip install PyQt6 pdfplumber python-docx google-generativeai python-dotenv requests
```

Copied Code: 
- CSS Flip animation for flashcards
https://animista.net/play/entrances/flip-in/flip-in-ver-left

app.css                                                                                                                                    
  Styles specifically for App.jsx. This is where the arcade room, cabinet, CRT screen, START button, and pixel menu styles live. Think of it  
  as the "skin" for the main app component.

  ---
  index.css

  Global styles that apply to the entire app — things like body margin, default fonts, root sizing. It's loaded once in main.jsx and affects   
  everything. I added the Google Fonts import here so "Press Start 2P" is available everywhere.

  ---
  App.jsx

  The main React component — the heart of the app. It holds the state (showMenu, selected), renders the arcade room, cabinet, CRT screen,     
  START button, and the popup menu. All the UI logic lives here.

  ---
  public/ folder

  Static files served as-is directly to the browser. The arcade-bg.png lives here, which is why I can reference it as /arcade-bg.png in CSS.
   Files here are NOT processed by Vite — they're just copied straight to the final build.

  ---
  src/assets/

  Static files that are processed by Vite (like the react.svg). The difference from public/ is Vite can optimize, hash, and bundle these. For  
  images are import directly in JS/JSX, put them here. For images referenced in CSS or HTML, use public/.

  ---
  main.jsx

  The entry point of the app. It's the first file that runs — it imports React, App.jsx, and index.css, then mounts the entire app into the    
  <div id="root"> in the index.html. Rarely need to edit this file.

  ---
  Flow summary:
  index.html
    └── main.jsx        ← mounts the app
          ├── index.css ← global styles
          └── App.jsx   ← your UI
                └── App.css ← component styles
