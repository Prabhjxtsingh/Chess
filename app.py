import webbrowser
import os
import sys
import time
from http.server import SimpleHTTPRequestHandler
import socketserver
import threading
import subprocess
import shutil
import platform

# Check for pywebview for Desktop App experience
try:
    import webview
    HAS_WEBVIEW = True
    # Handle deprecation warning for SAVE_DIALOG
    if hasattr(webview, 'FileDialog'):
        SAVE_DIALOG_TYPE = webview.FileDialog.SAVE
    else:
        SAVE_DIALOG_TYPE = getattr(webview, 'SAVE_DIALOG', 2)
except ImportError:
    HAS_WEBVIEW = False
    SAVE_DIALOG_TYPE = 2

# --- Python-JavaScript Bridge API ---
class JsApi:
    def log_event(self, message):
        """Receives logs from JS and prints to Python console"""
        print(f"[Game Event] {message}")

    def save_content(self, content, filename):
        if not HAS_WEBVIEW: 
            return "Error: PyWebView not active."
        try:
            active_window = webview.windows[0]
            result = active_window.create_file_dialog(
                SAVE_DIALOG_TYPE, 
                save_filename=filename, 
                file_types=('JSON Files (*.json)', 'All files (*.*)')
            )
            if result:
                save_path = result if isinstance(result, str) else result[0]
                with open(save_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return True
            return False
        except Exception as e:
            return str(e)

# --- The Complete HTML/JS/CSS Game Content ---
GAME_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Python Chess Pro</title>
    <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@700&family=Lato:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --light-square: #e8d0aa;
            --dark-square: #a67049;
            --bg-image: url('https://images.unsplash.com/photo-1586165368502-1bad197a6461?q=80&w=2658&auto=format&fit=crop');
            --highlight: rgba(255, 255, 0, 0.6);
            --capture: rgba(255, 50, 50, 0.6);
            --last-move: rgba(155, 199, 0, 0.5);
            --panel-bg: rgba(0, 0, 0, 0.75);
        }
        body.theme-ocean { --light-square: #d0e8f0; --dark-square: #4988a6; --bg-image: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); }
        body.theme-forest { --light-square: #e0f2d8; --dark-square: #5c8a62; --bg-image: url('https://images.unsplash.com/photo-1448375240586-dfd8d395ea6c?q=80&w=2670&auto=format&fit=crop'); }
        body.theme-dark { --light-square: #b0b0b0; --dark-square: #505050; --bg-image: linear-gradient(to bottom, #232526, #414345); }

        body {
            font-family: 'Lato', sans-serif;
            background: var(--bg-image) no-repeat center center fixed;
            background-size: cover;
            color: #fff;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
            overflow: hidden;
        }
        
        .game-container {
            backdrop-filter: blur(10px);
            background: rgba(255, 255, 255, 0.1);
            padding: 20px;
            border-radius: 20px;
            border: 1px solid rgba(255, 255, 255, 0.15);
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.5);
            max-width: 98vw;
            max-height: 98vh;
        }

        .main-layout { display: flex; flex-direction: row; gap: 20px; align-items: flex-start; }
        .sidebar { display: flex; flex-direction: column; width: 300px; gap: 10px; max-height: 90vh; overflow-y: auto; padding-right: 5px; }

        .logo-area h1 { font-family: 'Cinzel', serif; font-size: 1.8rem; margin: 0; text-shadow: 2px 2px 4px black; text-align: center; }
        
        .player-card {
            background: var(--panel-bg); padding: 10px; border-radius: 10px;
            border: 1px solid rgba(255,255,255,0.1); transition: all 0.3s;
        }
        .player-card.active-turn { border-color: #9bc700; box-shadow: 0 0 10px rgba(155, 199, 0, 0.3); }
        .player-header { display: flex; justify-content: space-between; margin-bottom: 5px; }
        .player-name-input { background: transparent; border: none; color: white; font-weight: bold; width: 120px; border-bottom: 1px solid #555; }
        .timer { font-family: monospace; font-size: 1.4rem; font-weight: bold; }

        .game-info-panel { text-align: center; background: rgba(0,0,0,0.4); padding: 10px; border-radius: 8px; }
        .eval-bar-bg { width: 100%; height: 10px; background: #eee; border-radius: 5px; margin-top:5px; overflow:hidden; }
        .eval-bar-fill { height: 100%; background: #222; width: 50%; transition: width 0.5s; }
        .eval-labels { display:flex; justify-content:space-between; font-size:0.75rem; color:#ccc; }

        #board {
            display: grid;
            grid-template-columns: repeat(8, minmax(0, 1fr));
            grid-template-rows: repeat(8, minmax(0, 1fr));
            width: 75vmin; height: 75vmin;
            max-width: 680px; max-height: 680px;
            min-width: 300px; min-height: 300px;
            border: 8px solid #2b1d0e; border-radius: 4px;
            user-select: none;
        }
        .square { width: 100%; height: 100%; display: flex; justify-content: center; align-items: center; font-size: 4rem; position: relative; }
        @media (max-width: 600px) { .square { font-size: 9vmin; } }

        .light { background-color: var(--light-square); color: black; }
        .dark { background-color: var(--dark-square); color: black; }
        .square.selected { background-color: rgba(100, 255, 100, 0.7) !important; }
        .square.highlight { background-color: var(--highlight) !important; }
        .square.capture-highlight { background-color: var(--capture) !important; }
        .square.last-move { background-color: var(--last-move) !important; }
        .square.check { background-color: rgba(255, 0, 0, 0.6) !important; box-shadow: inset 0 0 10px red; }
        
        /* Heatmap */
        .square.heatmap-w { box-shadow: inset 0 0 0 3px rgba(255,255,255,0.3); }
        .square.heatmap-b { box-shadow: inset 0 0 0 3px rgba(0,0,0,0.3); }

        .piece { cursor: grab; z-index: 2; text-shadow: 0 0 2px black; filter: drop-shadow(2px 4px 2px rgba(0,0,0,0.5)); }
        .piece.white { color: #fff; }
        .piece.black { color: #111; text-shadow: 0 0 1px #fff; }

        /* Overlay & Menu */
        .overlay { position: absolute; top:0; left:0; right:0; bottom:0; background: rgba(10,10,10,0.95); z-index:100; display:flex; flex-direction:column; align-items:center; justify-content:center; }
        .menu-content { background: #222; padding: 25px; border-radius: 10px; width: 320px; border: 1px solid #444; max-height: 90vh; overflow-y: auto;}
        .menu-group { margin-bottom: 15px; width: 100%; }
        .menu-label { display: block; color: #aaa; margin-bottom: 5px; font-size: 0.9rem; text-transform: uppercase; }
        .option-row { display: flex; gap: 5px; }
        .option-btn { flex: 1; padding: 8px; background: #333; border: 1px solid #555; color: #eee; cursor: pointer; border-radius: 4px; }
        .option-btn.selected { background: #4a6fa5; border-color: #6b8cce; font-weight: bold; }
        
        .start-btn { width: 100%; padding: 12px; background: #2e7d32; color: white; border: none; border-radius: 5px; font-size: 1.1rem; cursor: pointer; margin-top: 10px; }
        .start-btn:hover { background: #388e3c; }
        
        select, input[type="text"] { width: 100%; padding: 8px; background: #333; border: 1px solid #555; color: white; border-radius: 4px; }
        
        .history-panel { height: 100px; overflow-y: auto; background: rgba(0,0,0,0.3); border: 1px solid #444; margin-top: 10px; font-family: monospace; font-size: 0.85rem; padding: 5px; }
        .history-move { cursor: pointer; margin-right: 5px; }
        .history-move:hover { text-decoration: underline; color: #4a6fa5; }

        @media (max-width: 900px) {
            .main-layout { flex-direction: column-reverse; align-items: center; }
            .sidebar { width: 100%; max-width: 600px; flex-direction: row; flex-wrap: wrap; }
            .player-card { flex: 1; }
            #board { width: 92vw; height: 92vw; }
        }
    </style>
</head>
<body class="theme-wood">

    <div class="game-container">
        <!-- Main Menu Overlay -->
        <div id="menu-overlay" class="overlay">
            <h1>Chess Master</h1>
            <div class="menu-content">
                <div class="menu-group">
                    <span class="menu-label">Mode</span>
                    <div class="option-row">
                        <button id="btn-mode-pvp" onclick="selectMode('pvp')" class="option-btn selected">2 Players</button>
                        <button id="btn-mode-bot" onclick="selectMode('bot')" class="option-btn">Vs Bot</button>
                    </div>
                </div>
                
                <div class="menu-group" id="diff-section" style="display:none;">
                    <span class="menu-label">Bot Level</span>
                    <div class="option-row">
                        <button id="btn-lvl-1" onclick="selectLevel(1)" class="option-btn selected">1</button>
                        <button id="btn-lvl-2" onclick="selectLevel(2)" class="option-btn">2</button>
                        <button id="btn-lvl-3" onclick="selectLevel(3)" class="option-btn">3</button>
                        <button id="btn-lvl-4" onclick="selectLevel(4)" class="option-btn" style="background:#6a1b9a;">GM</button>
                    </div>
                </div>

                <div class="menu-group" id="pers-section" style="display:none;">
                    <span class="menu-label">Bot Style</span>
                    <select id="bot-style" onchange="logAction('Changed Bot Style: '+this.value)">
                        <option value="standard">Standard</option>
                        <option value="aggressive">Aggressive (Attacks)</option>
                        <option value="defensive">Defensive (Solid)</option>
                        <option value="gambit">Gambit (Risky)</option>
                    </select>
                </div>

                <div class="menu-group">
                    <span class="menu-label">Time Control</span>
                    <select id="time-select" onchange="logAction('Changed Time Control')">
                        <option value="60">1 Min</option>
                        <option value="180">3 Min</option>
                        <option value="300">5 Min</option>
                        <option value="600" selected>10 Min</option>
                        <option value="1800">30 Min</option>
                    </select>
                </div>

                <div class="menu-group">
                    <span class="menu-label">Theme</span>
                    <select id="theme-select" onchange="changeTheme(this.value)">
                        <option value="theme-wood">Classic Wood</option>
                        <option value="theme-ocean">Ocean Breeze</option>
                        <option value="theme-forest">Forest Glade</option>
                        <option value="theme-dark">Midnight Slate</option>
                    </select>
                </div>

                <button class="start-btn" onclick="launchGame()">Start Game</button>
                <div style="display:flex; gap:5px; margin-top:8px;">
                    <button class="option-btn" onclick="openSaveLoad()">Load Game</button>
                </div>
            </div>
        </div>

        <!-- Save/Load Modal -->
        <div id="save-modal" class="overlay" style="display:none;">
            <div class="menu-content">
                <h3>Save / Load</h3>
                <div class="menu-group">
                    <span class="menu-label">Save Filename</span>
                    <input type="text" id="save-name" placeholder="chess_game">
                    <button class="start-btn" style="margin-top:5px; background:#4a6fa5;" onclick="doSave()">Download Save</button>
                </div>
                <div class="menu-group">
                    <span class="menu-label">Load File</span>
                    <button class="start-btn" style="background:#555;" onclick="document.getElementById('file-input').click()">Select File</button>
                </div>
                <button class="option-btn" onclick="document.getElementById('save-modal').style.display='none'; logAction('Closed Save Menu')" style="width:100%">Close</button>
            </div>
        </div>
        <input type="file" id="file-input" style="display:none" onchange="doLoad(this)" accept=".json">

        <!-- Game Interface -->
        <div class="main-layout">
            <div id="board"></div>

            <div class="sidebar">
                <div class="logo-area">
                    <h1 style="font-size:1.5rem; margin-bottom:5px;">Python Chess</h1>
                    <span id="clock" style="font-family:monospace; color:#aaa;">00:00</span>
                </div>

                <!-- Opponent -->
                <div class="player-card" id="card-b">
                    <div class="player-header">
                        <input type="text" id="name-b" class="player-name-input" value="Black">
                        <span class="timer" id="time-b">10:00</span>
                    </div>
                    <small class="score-display">Mat: <span id="mat-b">0</span></small>
                </div>

                <!-- Info -->
                <div class="game-info-panel">
                    <div id="status-text" style="color:#ffd700; font-weight:bold;">White's Turn</div>
                    <div class="eval-bar-bg">
                        <div id="eval-fill" class="eval-bar-fill"></div>
                    </div>
                    <div class="eval-labels">
                        <span>White</span><span id="win-pct">50%</span><span>Black</span>
                    </div>
                    <div id="bot-msg" style="margin-top:8px; font-size:0.8rem; font-style:italic; color:#aaa; min-height:1.2em;"></div>
                </div>

                <!-- History -->
                <div class="history-panel" id="pgn-container"></div>

                <!-- Player -->
                <div class="player-card active-turn" id="card-w">
                    <div class="player-header">
                        <input type="text" id="name-w" class="player-name-input" value="White">
                        <span class="timer" id="time-w">10:00</span>
                    </div>
                    <small class="score-display">Mat: <span id="mat-w">0</span></small>
                </div>

                <!-- Controls -->
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:5px;">
                    <button class="option-btn" onclick="toggleHeatmap()">Heatmap</button>
                    <button class="option-btn" onclick="undoMove()">Undo</button>
                    <button class="option-btn" onclick="openSaveLoad()">Save</button>
                    <button class="option-btn" style="background:#b71c1c;" onclick="confirmQuit()">Quit</button>
                    <button class="option-btn" style="grid-column:span 2; background:#2e7d32;" onclick="showMenu()">New Game</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        // --- LOGGING ---
        function logAction(msg) {
            if(window.pywebview) {
                window.pywebview.api.log_event(msg);
            } else {
                fetch('/log_action', {method:'POST', body:msg}).catch(e=>{});
            }
        }

        // --- CONSTANTS & CONFIG ---
        const pieces = { w: { k:'♔', q:'♕', r:'♖', b:'♗', n:'♘', p:'♙' }, b: { k:'♚', q:'♛', r:'♜', b:'♝', n:'♞', p:'♟' } };
        const vals = { p:100, n:320, b:330, r:500, q:900, k:20000 };
        // PST (Simplified)
        const pst = {
            p: [ [0,0,0,0,0,0,0,0],[50,50,50,50,50,50,50,50],[10,10,20,30,30,20,10,10],[5,5,10,25,25,10,5,5],[0,0,0,20,20,0,0,0],[5,-5,-10,0,0,-10,-5,5],[5,10,10,-20,-20,10,10,5],[0,0,0,0,0,0,0,0] ],
            n: [ [-50,-40,-30,-30,-30,-30,-40,-50],[-40,-20,0,0,0,0,-20,-40],[-30,0,10,15,15,10,0,-30],[-30,5,15,20,20,15,5,-30],[-30,0,15,20,20,15,0,-30],[-30,5,10,15,15,10,5,-30],[-40,-20,0,5,5,0,-20,-40],[-50,-40,-30,-30,-30,-30,-40,-50] ]
        };
        
        // Opening Book (Source-Target Coordinates)
        // e2e4 -> 6,4 to 4,4
        const book = {
            "": [{r:6,c:4, tr:4,tc:4}, {r:6,c:3, tr:4,tc:3}, {r:7,c:6, tr:5,tc:5}], // e4, d4, Nf3
            "e2e4": [{r:1,c:4, tr:3,tc:4}, {r:1,c:2, tr:3,tc:2}], // e5, c5
            "d2d4": [{r:1,c:3, tr:3,tc:3}, {r:0,c:6, tr:2,tc:5}], // d5, Nf6
        };

        // --- STATE ---
        let board = [], turn = 'w', mode = 'pvp', level = 1, style = 'standard';
        let history = [], pgn = [], moveStr = "";
        let tW = 600, tB = 600, timer = null, active = false;
        let selected = null, lastMove = null;
        let showHM = false;

        // --- INIT ---
        setInterval(() => document.getElementById('clock').innerText = new Date().toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'}), 1000);
        
        function showMenu() { 
            stopTimer();
            logAction("Opened Main Menu");
            document.getElementById('menu-overlay').style.display = 'flex'; 
        }

        function changeTheme(themeClass) {
            document.body.className = themeClass;
            logAction("Changed Theme to " + themeClass);
        }

        function selectMode(m) {
            mode = m;
            logAction("Selected Mode: " + m);
            document.getElementById('btn-mode-pvp').className = m==='pvp'?'option-btn selected':'option-btn';
            document.getElementById('btn-mode-bot').className = m==='bot'?'option-btn selected':'option-btn';
            document.getElementById('diff-section').style.display = m==='bot'?'block':'none';
            document.getElementById('pers-section').style.display = m==='bot'?'block':'none';
        }

        function selectLevel(l) {
            level = l;
            logAction("Selected Bot Level: " + l);
            for(let i=1; i<=4; i++) document.getElementById('btn-lvl-'+i).className = i===l?'option-btn selected':'option-btn';
        }

        function launchGame() {
            style = document.getElementById('bot-style').value;
            const t = parseInt(document.getElementById('time-select').value);
            tW = t; tB = t;
            
            document.getElementById('name-w').value = (mode==='bot') ? "You" : "Player 1";
            document.getElementById('name-b').value = (mode==='bot') ? `Bot (${style})` : "Player 2";
            
            logAction(`Game Started: ${mode}, Level ${level}, Time ${t}s`);
            resetBoard();
            document.getElementById('menu-overlay').style.display = 'none';
            active = true;
            render(); updateUI(); startTimer();
        }

        function resetBoard() {
            board = [
                ['br','bn','bb','bq','bk','bb','bn','br'],
                ['bp','bp','bp','bp','bp','bp','bp','bp'],
                ...Array(4).fill(null).map(()=>Array(8).fill('')),
                ['wp','wp','wp','wp','wp','wp','wp','wp'],
                ['wr','wn','wb','wq','wk','wb','wn','wr']
            ];
            turn = 'w'; history = []; pgn = []; moveStr = ""; lastMove = null; selected = null;
        }

        // --- CORE ENGINE ---
        function onBoard(r,c) { return r>=0 && r<8 && c>=0 && c<8; }

        function getMoves(b, r, c) {
            const p = b[r][c], type = p[1], col = p[0];
            const m = [];
            const add = (nr,nc) => { if(onBoard(nr,nc) && (!b[nr][nc] || b[nr][nc][0]!==col)) m.push({r:nr, c:nc}); };
            
            if(type==='p') {
                const d = col==='w'?-1:1;
                if(onBoard(r+d,c) && !b[r+d][c]) {
                    m.push({r:r+d, c:c});
                    if((col==='w' && r===6) || (col==='b' && r===1)) if(!b[r+d*2][c]) m.push({r:r+d*2, c:c});
                }
                if(onBoard(r+d,c-1) && b[r+d][c-1] && b[r+d][c-1][0]!==col) m.push({r:r+d, c:c-1});
                if(onBoard(r+d,c+1) && b[r+d][c+1] && b[r+d][c+1][0]!==col) m.push({r:r+d, c:c+1});
            } else {
                const dirs = {
                    n:[[2,1],[2,-1],[-2,1],[-2,-1],[1,2],[1,-2],[-1,2],[-1,-2]],
                    b:[[1,1],[1,-1],[-1,1],[-1,-1]],
                    r:[[0,1],[0,-1],[1,0],[-1,0]],
                    q:[[0,1],[0,-1],[1,0],[-1,0],[1,1],[1,-1],[-1,1],[-1,-1]],
                    k:[[0,1],[0,-1],[1,0],[-1,0],[1,1],[1,-1],[-1,1],[-1,-1]]
                };
                if(type==='n' || type==='k') {
                    for(let d of dirs[type]) add(r+d[0], c+d[1]);
                } else {
                    for(let d of dirs[type]) {
                        for(let i=1; i<8; i++) {
                            const nr=r+d[0]*i, nc=c+d[1]*i;
                            if(!onBoard(nr,nc)) break;
                            if(b[nr][nc]) { if(b[nr][nc][0]!==col) m.push({r:nr, c:nc}); break; }
                            m.push({r:nr, c:nc});
                        }
                    }
                }
            }
            return m;
        }

        function getLegalMoves(b, col) {
            let moves = [];
            for(let r=0; r<8; r++) {
                for(let c=0; c<8; c++) {
                    if(b[r][c] && b[r][c][0]===col) {
                        const ms = getMoves(b, r, c);
                        for(let m of ms) {
                            // Virtual move
                            const saved = b[m.r][m.c]; b[m.r][m.c] = b[r][c]; b[r][c] = '';
                            if(!inCheck(b, col)) moves.push({from:{r,c}, to:m});
                            b[r][c] = b[m.r][m.c]; b[m.r][m.c] = saved;
                        }
                    }
                }
            }
            return moves;
        }

        function inCheck(b, col) {
            let kr, kc;
            for(let r=0; r<8; r++) for(let c=0; c<8; c++) if(b[r][c]===col+'k') { kr=r; kc=c; break; }
            if(kr==null) return true; // King missing (shouldnt happen)
            const opp = col==='w'?'b':'w';
            
            // Check attacks (simplified inverse)
            for(let r=0; r<8; r++) {
                for(let c=0; c<8; c++) {
                    if(b[r][c] && b[r][c][0]===opp) {
                        // Optimizing: only generate moves for pieces that could hit king
                        const ms = getMoves(b, r, c);
                        if(ms.some(m => m.r===kr && m.c===kc)) return true;
                    }
                }
            }
            return false;
        }

        // --- GAMEPLAY ---
        function handleClick(r, c) {
            if(!active || (mode==='bot' && turn==='b')) return;
            logAction("Clicked square " + r + "," + c);
            
            // Move
            if(selected) {
                const legals = getLegalMoves(board, turn).filter(m => m.from.r===selected.r && m.from.c===selected.c);
                const move = legals.find(m => m.to.r===r && m.to.c===c);
                if(move) { executeMove(move); return; }
            }
            
            // Select
            if(board[r][c] && board[r][c][0]===turn) {
                selected = {r,c};
                highlightBoard(); // Call Highlight instead of render
            } else {
                selected = null;
                highlightBoard();
            }
        }

        function highlightBoard() {
            // Clear existing
            document.querySelectorAll('.square').forEach(el => {
                el.classList.remove('selected', 'highlight', 'capture-highlight');
            });
            
            if(!selected) return;

            // Highlight source
            const srcIdx = selected.r * 8 + selected.c;
            const squares = document.getElementById('board').children;
            if(squares[srcIdx]) squares[srcIdx].classList.add('selected');

            // Highlight moves
            const moves = getLegalMoves(board, turn).filter(m => m.from.r===selected.r && m.from.c===selected.c);
            moves.forEach(m => {
                const idx = m.to.r * 8 + m.to.c;
                if(squares[idx]) {
                    squares[idx].classList.add(board[m.to.r][m.to.c] ? 'capture-highlight' : 'highlight');
                }
            });
        }

        function executeMove(move) {
            // Save state
            history.push({board:JSON.parse(JSON.stringify(board)), turn, tW, tB, pgn:[...pgn], moveStr});
            
            const p = board[move.from.r][move.from.c];
            const cap = board[move.to.r][move.to.c];
            
            // Update board
            board[move.to.r][move.to.c] = p;
            board[move.from.r][move.from.c] = '';
            
            // Promotion
            if(p[1]==='p' && (move.to.r===0 || move.to.r===7)) board[move.to.r][move.to.c] = p[0]+'q';
            
            // Update PGN
            const cols='abcdefgh', rows='87654321';
            const san = (p[1]==='p'?'':p[1].toUpperCase()) + (cap?'x':'') + cols[move.to.c] + rows[move.to.r];
            pgn.push(san);
            
            // Update Book string
            moveStr += cols[move.from.c] + rows[move.from.r] + cols[move.to.c] + rows[move.to.r];

            lastMove = move;
            selected = null;
            turn = turn==='w'?'b':'w';
            
            logAction(`Move executed: ${san}`);
            
            // Check End
            const nextMoves = getLegalMoves(board, turn);
            if(nextMoves.length === 0) {
                active = false; stopTimer();
                if(inCheck(board, turn)) {
                    logAction("Checkmate");
                    alert("Checkmate!"); 
                } else {
                    logAction("Stalemate");
                    alert("Stalemate!");
                }
            }
            
            render(); updateUI();
            
            // Bot Turn
            if(active && mode==='bot' && turn==='b') {
                document.getElementById('bot-msg').innerText = "Thinking...";
                setTimeout(botMove, 100);
            }
        }

        function undoMove() {
            logAction("User clicked Undo");
            if(history.length === 0) return;
            // Undo 2 if bot
            const steps = (mode==='bot' && turn==='w' && history.length > 1) ? 2 : 1;
            
            for(let i=0; i<steps; i++) {
                const s = history.pop();
                board = s.board; turn = s.turn; tW = s.tW; tB = s.tB; pgn = s.pgn; moveStr = s.moveStr;
            }
            lastMove = null; selected = null; active = true;
            render(); updateUI();
        }

        // --- BOT ---
        function botMove() {
            // 1. Opening Book
            if(book[moveStr]) {
                const opts = book[moveStr];
                const bm = opts[Math.floor(Math.random()*opts.length)];
                // Verify legal (book moves should be legal but safe check)
                const move = {from:{r:bm.r, c:bm.c}, to:{r:bm.tr, c:bm.tc}};
                document.getElementById('bot-msg').innerText = "Playing from Opening Book";
                executeMove(move);
                return;
            }

            // 2. Search
            const moves = getLegalMoves(board, 'b');
            if(moves.length === 0) return;

            // Move Ordering: Captures first
            moves.sort((a,b) => {
                const vA = vals[board[a.to.r][a.to.c]?.[1]] || 0;
                const vB = vals[board[b.to.r][b.to.c]?.[1]] || 0;
                return vB - vA;
            });

            let bestMove = moves[0];
            let bestScore = -Infinity;
            const depth = level; 

            // Simple Minimax
            for(let m of moves) {
                const saved = board[m.to.r][m.to.c]; board[m.to.r][m.to.c] = board[m.from.r][m.from.c]; board[m.from.r][m.from.c] = '';
                const score = -minimax(depth-1, -100000, 100000, false);
                board[m.from.r][m.from.c] = board[m.to.r][m.to.c]; board[m.to.r][m.to.c] = saved;
                
                if(score > bestScore) { bestScore = score; bestMove = m; }
            }
            
            // Explain
            const pName = {'p':'Pawn','n':'Knight','b':'Bishop','r':'Rook','q':'Queen','k':'King'};
            const p = board[bestMove.from.r][bestMove.from.c];
            document.getElementById('bot-msg').innerText = `Bot moved ${pName[p[1]]} to improve position.`;

            executeMove(bestMove);
        }

        function minimax(depth, alpha, beta, isMax) {
            if(depth===0) return evaluate();
            
            const moves = getLegalMoves(board, isMax?'b':'w');
            if(moves.length===0) return inCheck(board, isMax?'b':'w') ? -20000 : 0;

            for(let m of moves) {
                const saved = board[m.to.r][m.to.c]; board[m.to.r][m.to.c] = board[m.from.r][m.from.c]; board[m.from.r][m.from.c] = '';
                const score = -minimax(depth-1, -beta, -alpha, !isMax);
                board[m.from.r][m.from.c] = board[m.to.r][m.to.c]; board[m.to.r][m.to.c] = saved;
                
                if(score >= beta) return beta;
                if(score > alpha) alpha = score;
            }
            return alpha;
        }

        function evaluate() {
            let score = 0;
            for(let r=0; r<8; r++) for(let c=0; c<8; c++) {
                const p = board[r][c];
                if(p) {
                    let v = vals[p[1]];
                    // PST Tweak (simplified)
                    if(p[1]==='p' || p[1]==='n') {
                        if(p[0]==='w') v += (pst.p[r][c] || 0)/10;
                        else v += (pst.p[7-r][c] || 0)/10;
                    }
                    score += (p[0]==='b' ? v : -v);
                }
            }
            // Personality
            if(style==='aggressive') score *= 1.1;
            return score;
        }

        // --- SAVE/LOAD ---
        function openSaveLoad() {
            logAction("Opened Save/Load Menu");
            // Default filename
            const d = new Date();
            const name = `chess_${d.getFullYear()}-${d.getMonth()+1}-${d.getDate()}_${d.getHours()}-${d.getMinutes()}`;
            document.getElementById('save-name').value = name;
            document.getElementById('save-modal').style.display = 'flex';
        }

        async function doSave() {
            logAction("Initiated Game Save");
            let name = document.getElementById('save-name').value || 'chess_save';
            if(!name.endsWith('.json')) name += '.json';
            
            const data = JSON.stringify({board, turn, history, pgn, mode, level, style, tW, tB});
            
            // Desktop Save
            if(window.pywebview) {
                const res = await window.pywebview.api.save_content(data, name);
                if(res === true) alert("Saved!"); else alert("Save Error");
            } 
            // Browser Save (Native or Blob)
            else if(window.showSaveFilePicker) {
                try {
                    const handle = await showSaveFilePicker({suggestedName: name});
                    const w = await handle.createWritable();
                    await w.write(data); await w.close();
                    alert("Saved!");
                } catch(e) {}
            } else {
                // Blob Fallback
                const blob = new Blob([data], {type:'application/json'});
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a'); a.href = url; a.download = name; a.click();
            }
            document.getElementById('save-modal').style.display = 'none';
        }

        function doLoad(input) {
            logAction("Loading Game from File...");
            const f = input.files[0];
            if(!f) return;
            const r = new FileReader();
            r.onload = (e) => {
                try {
                    const d = JSON.parse(e.target.result);
                    board = d.board; turn = d.turn; history = d.history;
                    pgn = d.pgn; mode = d.mode; level = d.level; style = d.style;
                    tW = d.tW; tB = d.tB;
                    
                    // Restore UI
                    if(mode==='bot') document.getElementById('name-b').value = `Bot (${style})`;
                    
                    active = true; lastMove=null; selected=null;
                    render(); updateUI(); startTimer();
                    document.getElementById('save-modal').style.display = 'none';
                    logAction("Game Loaded Successfully");
                } catch(err) { alert("Invalid File"); }
            };
            r.readAsText(f);
            input.value = "";
        }

        // --- UI ---
        function render() {
            const el = document.getElementById('board');
            el.innerHTML = '';
            
            const hm = showHM ? getHeatmap() : null;

            for(let r=0; r<8; r++) for(let c=0; c<8; c++) {
                const sq = document.createElement('div');
                const isDark = (r+c)%2===1;
                sq.className = `square ${isDark?'dark':'light'}`;
                sq.onclick = () => handleClick(r,c);
                sq.ondragover = (e) => e.preventDefault();
                sq.ondrop = (e) => {
                    e.preventDefault();
                    logAction("Drop at " + r + "," + c);
                    if(selected) {
                        const moves = getLegalMoves(board, turn).filter(m => m.from.r===selected.r && m.from.c===selected.c);
                        const move = moves.find(m => m.to.r===r && m.to.c===c);
                        if(move) executeMove(move);
                    }
                };

                if(selected && selected.r===r && selected.c===c) sq.classList.add('selected');
                if(lastMove && ((lastMove.from.r===r && lastMove.from.c===c) || (lastMove.to.r===r && lastMove.to.c===c))) sq.classList.add('last-move');
                
                // Highlights
                if(selected) {
                    const moves = getLegalMoves(board, turn).filter(m => m.from.r===selected.r && m.from.c===selected.c);
                    if(moves.some(m => m.to.r===r && m.to.c===c)) sq.classList.add(board[r][c]?'capture-highlight':'highlight');
                }
                
                // Check
                if(inCheck(board, turn) && board[r][c]===turn+'k') sq.classList.add('check');

                // Heatmap
                if(hm) {
                    if(hm[r][c] > 0) sq.classList.add('heatmap-w');
                    if(hm[r][c] < 0) sq.classList.add('heatmap-b');
                }

                if(board[r][c]) {
                    const p = document.createElement('span');
                    p.className = `piece ${board[r][c][0]==='w'?'white':'black'}`;
                    p.innerText = pieces[board[r][c][0]][board[r][c][1]];
                    if(board[r][c][0] === turn && !(mode==='bot' && turn==='b')) {
                        p.draggable = true;
                        p.ondragstart = (e) => { 
                            logAction("Drag Start " + r + "," + c); 
                            selected = {r,c}; 
                            // Important: Don't re-render, just highlight
                            highlightBoard(); 
                            e.dataTransfer.effectAllowed = 'move';
                            e.dataTransfer.setData('text/plain', JSON.stringify({r,c}));
                        };
                    }
                    sq.appendChild(p);
                }
                el.appendChild(sq);
            }
        }

        function highlightBoard() {
            // Clear existing
            document.querySelectorAll('.square').forEach(el => {
                el.classList.remove('selected', 'highlight', 'capture-highlight');
            });
            
            if(!selected) return;

            // Highlight source
            const srcIdx = selected.r * 8 + selected.c;
            const squares = document.getElementById('board').children;
            if(squares[srcIdx]) squares[srcIdx].classList.add('selected');

            // Highlight moves
            const moves = getLegalMoves(board, turn).filter(m => m.from.r===selected.r && m.from.c===selected.c);
            moves.forEach(m => {
                const idx = m.to.r * 8 + m.to.c;
                if(squares[idx]) {
                    squares[idx].classList.add(board[m.to.r][m.to.c] ? 'capture-highlight' : 'highlight');
                }
            });
        }

        function updateUI() {
            // Timer
            const f = t => { const m=Math.floor(t/60), s=t%60; return `${m}:${s<10?'0'+s:s}`; };
            document.getElementById('time-w').innerText = f(tW);
            document.getElementById('time-b').innerText = f(tB);
            document.getElementById('card-w').className = `player-card ${turn==='w'?'active-turn':''}`;
            document.getElementById('card-b').className = `player-card ${turn==='b'?'active-turn':''}`;
            document.getElementById('status-text').innerText = turn==='w' ? "White's Turn" : "Black's Turn";
            
            // Score
            let matW=0, matB=0;
            for(let r=0; r<8; r++) for(let c=0; c<8; c++) if(board[r][c]) {
                const v = vals[board[r][c][1]];
                if(board[r][c][0]==='w') matW+=v; else matB+=v;
            }
            document.getElementById('mat-w').innerText = (matW/100).toFixed(1);
            document.getElementById('mat-b').innerText = (matB/100).toFixed(1);
            
            // Eval Bar
            const diff = matB - matW; // Basic material eval for bar visual
            const pct = 50 + (diff / 2000 * 50); // Scale
            document.getElementById('eval-fill').style.width = Math.min(Math.max(pct, 5), 95) + "%";
            document.getElementById('win-pct').innerText = (diff > 0 ? "Black " : "White ") + Math.abs(diff/100).toFixed(1);

            // History
            const h = document.getElementById('pgn-container');
            let html = "";
            for(let i=0; i<pgn.length; i++) {
                if(i%2===0) html += `<span style='color:#888'>${(i/2)+1}.</span> `;
                html += `<span class='history-move'>${pgn[i]}</span> `;
            }
            h.innerHTML = html;
            h.scrollTop = h.scrollHeight;
        }

        function startTimer() {
            if(timer) clearInterval(timer);
            timer = setInterval(() => {
                if(!active) return;
                if(turn==='w') { tW--; if(tW<=0) { active=false; alert("Black Wins!"); } }
                else { tB--; if(tB<=0) { active=false; alert("White Wins!"); } }
                updateUI();
            }, 1000);
        }
        function stopTimer() { if(timer) clearInterval(timer); }

        function toggleHeatmap() { showHM = !showHM; logAction("Toggled Heatmap"); render(); }
        function getHeatmap() {
            // Count attacks for simplistic heatmap
            const map = Array(8).fill().map(()=>Array(8).fill(0));
            // Just simulate attack density
            for(let r=0; r<8; r++) for(let c=0; c<8; c++) if(board[r][c]) {
                const ms = getMoves(board, r, c);
                const v = board[r][c][0]==='w' ? 1 : -1;
                for(let m of ms) map[m.r][m.c] += v;
            }
            return map;
        }
        function confirmQuit() {
            logAction("User clicked Quit");
            if(confirm("Quit?")) {
                active = false; stopTimer();
                window.close();
                document.body.innerHTML = "<h1 style='color:white;text-align:center;margin-top:20%'>Game Closed</h1>";
            }
        }
    </script>
</body>
</html>
"""

# --- Custom Log Handler ---
class LogHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass # Suppress default logging
    
    def do_POST(self):
        if self.path == '/log_action':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            print(f"[Game Event] {post_data}")
            self.send_response(200)
            self.end_headers()
        else:
            self.send_error(404)

# --- Python Launcher Logic ---

def run_server():
    # 2. Setup Local Server
    filename = "chess_game_ui.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(GAME_HTML)

    PORT = 8000

    try:
        # Start server
        server = socketserver.TCPServer(("", PORT), LogHandler)
        url = f"http://localhost:{PORT}/{filename}"
        print(f"\n--- CHESS GAME LAUNCHED ---")
        print(f"Server running on port {PORT}")
        
        # --- NEW: Cloud/Notebook Embedding ---
        try:
            from IPython.display import display, HTML
            if os.path.exists("/content") or "google.colab" in sys.modules:
                display(HTML(GAME_HTML))
        except ImportError:
            pass
        # -------------------------------------
        
        def start_server():
            server.serve_forever()

        def launch_browser_tab():
            time.sleep(1.5)
            if os.path.exists("/content") or os.environ.get("HEADLESS") == "1": return
            webbrowser.open(url)

        if HAS_WEBVIEW and not (os.path.exists("/content") or os.environ.get("HEADLESS") == "1"):
            print("Launching Desktop App via PyWebView...")
            t = threading.Thread(target=start_server, daemon=True)
            t.start()
            
            webview.create_window('Python Chess Pro', url, width=1100, height=850, resizable=True, js_api=JsApi())
            webview.start()
            sys.exit(0)
        else:
            threading.Thread(target=launch_browser_tab, daemon=True).start()
            try:
                print("Press Ctrl+C to stop the server.")
                server.serve_forever()
            except KeyboardInterrupt:
                print("\nServer stopped.")
                server.server_close()

    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()
    except OSError as e:
        print(f"Could not start server on port {PORT}: {e}")
        abs_path = os.path.abspath(filename)
        webbrowser.open(f"file://{abs_path}")

if __name__ == "__main__":
    run_server()
