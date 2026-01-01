# ♟️ Python Chess Pro

A **fully-featured Chess game** built using **Python + HTML/CSS/JavaScript**, supporting:

- Web browser gameplay
- Desktop app experience using **PyWebView**
- Player vs Player & Player vs Bot
- Built-in Chess engine (Minimax + Alpha-Beta)
- Game save/load (JSON)
- Multiple themes & time controls
- Heatmap visualization
- Opening book support

---

## 🚀 Features

### 🎮 Gameplay
- PvP and PvE (Bot levels 1–4, including GM mode)
- Drag & drop pieces
- Legal move validation
- Check, checkmate & stalemate detection
- Undo moves (smart undo for bot games)

### 🤖 Chess Engine
- Minimax with Alpha-Beta pruning
- Opening book support
- Personality modes:
  - Standard
  - Aggressive
  - Defensive
  - Gambit

### 🎨 UI / UX
- Responsive chessboard
- Multiple board themes:
  - Classic Wood
  - Ocean Breeze
  - Forest Glade
  - Midnight Slate
- Move highlights
- Last-move indicator
- Heatmap (attack visualization)
- Evaluation bar

### 💾 Save & Load
- Save games as `.json`
- Load saved games anytime
- Desktop save dialog via PyWebView
- Browser-based save fallback

### 🖥 Desktop + Web
- Runs in:
  - Web browser
  - Desktop window (PyWebView)
  - Google Colab / Jupyter notebooks

---

## 🛠 Tech Stack

- **Python 3.8+**
- **HTML5 / CSS3**
- **Vanilla JavaScript**
- **PyWebView** (optional desktop mode)
- **HTTP Server (SimpleHTTPRequestHandler)**

---

## 📦 Installation

### 1️⃣ Clone the repository
```bash
git clone https://github.com/your-username/python-chess-pro.git
cd python-chess-pro
2️⃣ Install dependencies
bash
Copy code
pip install -r requirements.txt
💡 PyWebView is optional.
If not installed, the game runs in the browser automatically.

▶️ Run the Game
bash
Copy code
python main.py
What happens?
Starts a local server on localhost:8000

Opens the game in:

Browser (default)

Desktop window if PyWebView is installed

🧪 Supported Environments
Environment	Supported
Windows	✅
macOS	✅
Linux	✅
Google Colab	✅
Jupyter Notebook	✅

🧠 Future Improvements
Online multiplayer

PGN export/import

Stockfish integration

Opening explorer

Mobile touch optimizations

📜 License
MIT License — free to use, modify, and distribute.

🙌 Author
Prabhjot Singh
Python Developer | Web Developer | AI & Automation Enthusiast
