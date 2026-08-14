# app_v3.py
# Version: 3.1.4b - pending test: full pagination loop on /sessions, label/custom-field search
#                    + truncated display, Split Transcript endpoint (WSS "split", confirmed
#                    working via bystander connect), bulk select + Split/End toolbar,
#                    simplified "asdf" confirm on End/Split
# Discovery: REST 1.11.0 | Termination: Endpoint Services 1.3

import os, subprocess, json, asyncio, webbrowser, signal, sys
from flask import Flask, jsonify, render_template_string, request
from threading import Timer

app = Flask(__name__)

# --- CONFIGURATION ---
REST_BASE = "https://api.wordly.ai"
WS_ENDPOINT = "wss://endpoint.wordly.ai/session"

@app.route('/api/sessions')
def get_sessions():
    """Discovery via REST v1.11.0. API key now comes from the browser (masked field), not a file.
    Wordly paginates /sessions at a default of 10/page — loop pages (limit=100 each) using the
    response's "total" field until every session has been collected."""
    key = request.headers.get('X-Wordly-Api-Key')
    if not key:
        return jsonify({"error": "MISSING_KEY"}), 401

    try:
        all_sessions = []
        page = 1
        while True:
            cmd = ['curl', '-s', '-H', f'x-wordly-api-key: {key}',
                   f'{REST_BASE}/sessions?page={page}&limit=100']
            result = subprocess.run(cmd, capture_output=True, text=True)
            if not result.stdout:
                break
            data = json.loads(result.stdout)
            sessions = data.get('sessions', [])
            all_sessions.extend(sessions)
            total = data.get('total', len(all_sessions))
            if not sessions or len(all_sessions) >= total:
                break
            page += 1
        return jsonify({"sessions": all_sessions})
    except Exception as e:
        return jsonify({"error": "CMD_FAILED", "message": str(e)}), 500

@app.route('/api/shutdown', methods=['POST'])
def shutdown():
    """Kills the Python process to close the terminal."""
    print("\n🛑 SHUTDOWN SIGNAL RECEIVED. CLOSING MISSION CONTROL...")
    def kill_process():
        import time
        time.sleep(1) # Allow UI to render the "Offline" message
        os.kill(os.getpid(), signal.SIGINT)

    Timer(0.5, kill_process).start()
    return jsonify({"status": "server_shutting_down"})

async def ws_kill_logic(session_id, passcode):
    """Signals 'disconnect' with end:true via WebSocket (Endpoint Services 1.3)"""
    import websockets
    try:
        async with websockets.connect(WS_ENDPOINT) as ws:
            # 1. Connect Handshake
            await ws.send(json.dumps({
                "type": "connect",
                "presentationCode": session_id,
                "accessKey": passcode
            }))
            await ws.recv()
            # 2. Live Termination for all participants
            await ws.send(json.dumps({"type": "disconnect", "end": True}))
            return True
    except Exception as e:
        print(f"WS KILL ERROR: {e}")
        return False

@app.route('/api/sessions/end/<session_id>', methods=['POST'])
def end_session_action(session_id):
    passcode = request.args.get('passcode')
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success = loop.run_until_complete(ws_kill_logic(session_id, passcode))
        return jsonify({"status": "success" if success else "failed"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

async def ws_split_logic(session_id, passcode):
    """Sends {"type":"split"} over a bystander connect (no audio needed) —
    confirmed working via Endpoint Services even without a full connect handshake."""
    import websockets
    try:
        async with websockets.connect(WS_ENDPOINT) as ws:
            await ws.send(json.dumps({
                "type": "connect",
                "presentationCode": session_id,
                "accessKey": passcode
            }))
            await ws.recv()
            await ws.send(json.dumps({"type": "split"}))
            return True
    except Exception as e:
        print(f"WS SPLIT ERROR: {e}")
        return False

@app.route('/api/sessions/split/<session_id>', methods=['POST'])
def split_session_action(session_id):
    passcode = request.args.get('passcode')
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success = loop.run_until_complete(ws_split_logic(session_id, passcode))
        return jsonify({"status": "success" if success else "failed"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/')
def index():
    return render_template_string('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Wordly Mission Control</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .active-row { background-color: rgba(34, 197, 94, 0.08); border-left: 4px solid #16a34a; }
        .refreshing { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .header-link { transition: opacity 0.2s; }
        .header-link:hover { opacity: 0.7; }
    </style>
</head>
<body id="mainBody" class="bg-white text-slate-900 antialiased p-3">
    <nav class="flex justify-between items-center mb-4 pb-2 border-b border-slate-200">
        <a href="https://www.wordly.ai/" target="_blank" class="header-link block" style="width: 180px;">
            <svg xmlns="http://www.w3.org/2000/svg" width="100%" viewBox="0 0 108 33" fill="none" title="Wordly Logo" class="text-slate-900">
                <g clip-path="url(#clip0_2061_12667)">
                    <path d="M35.1107 5.03864L36.3379 0.364479H34.1934C30.8595 0.364479 27.9403 2.61779 27.0942 5.8428L24.4305 16.0288L20.5353 0.360291H15.7104L11.8362 15.966L9.18498 5.8428C8.34313 2.61779 5.42387 0.364479 2.08997 0.364479H0L1.22718 5.03864H2.08997C3.3004 5.03864 4.36004 5.85537 4.66579 7.0281L8.77872 22.8306H14.2068L18.127 7.75267L22.0473 22.8306H27.4754L31.6176 7.0281C31.9234 5.85955 32.983 5.03864 34.1934 5.03864H35.1107Z" fill="currentColor"></path>
                    <path d="M52.5254 13.7125V22.8263H57.1996V13.7125C57.1996 12.0581 58.5482 10.7095 60.2026 10.7095H62.3219L63.5449 6.03534H60.2026C55.9682 6.03534 52.5254 9.47814 52.5254 13.7125Z" fill="currentColor"></path>
                    <path d="M46.1003 7.11507C44.7726 6.36955 43.2942 6.00098 41.6691 6.00098C40.044 6.00098 38.5572 6.37374 37.2211 7.11507C35.885 7.86059 34.817 8.87416 34.0254 10.16C33.2296 11.4458 32.8359 12.9243 32.8359 14.5912C32.8359 16.2582 33.2338 17.7115 34.0254 19.0099C34.8212 20.3083 35.885 21.326 37.2211 22.0716C38.5572 22.8171 40.0398 23.1857 41.6691 23.1857C43.2984 23.1857 44.7768 22.8129 46.1003 22.0716C47.428 21.326 48.4877 20.3083 49.2835 19.0099C50.0793 17.7115 50.473 16.2414 50.473 14.5912C50.473 12.941 50.0751 11.4458 49.2835 10.16C48.4877 8.87416 47.428 7.8564 46.1003 7.11507ZM45.2711 16.9451C44.9192 17.6278 44.4376 18.1597 43.8219 18.545C43.2104 18.9261 42.49 19.1188 41.6649 19.1188C40.8398 19.1188 40.1152 18.9261 39.4954 18.545C38.8713 18.1639 38.3855 17.6319 38.0336 16.9451C37.6818 16.2624 37.5059 15.4791 37.5059 14.5912C37.5059 13.7033 37.6818 12.9285 38.0336 12.2541C38.3855 11.5798 38.8713 11.0479 39.4954 10.6542C40.1194 10.2605 40.8398 10.0678 41.6649 10.0678C42.49 10.0678 43.2062 10.2647 43.8219 10.6542C44.4334 11.0479 44.9192 11.5798 45.2711 12.2541C45.6229 12.9285 45.7988 13.7075 45.7988 14.5912C45.7988 15.475 45.6229 16.2624 45.2711 16.9451Z" fill="currentColor"></path>
                    <path d="M76.8053 7.76515C76.3739 7.33375 75.8713 6.96518 75.2808 6.68037C74.3468 6.22803 73.2746 6.00186 72.0683 6.00186C70.5019 6.00186 69.0821 6.383 67.8172 7.14946C66.5523 7.91174 65.5471 8.94206 64.8016 10.2404C64.0561 11.5388 63.6875 12.988 63.6875 14.5963C63.6875 16.2046 64.0561 17.6328 64.789 18.9396C65.522 20.2463 66.523 21.2809 67.7879 22.0473C69.0527 22.8096 70.4935 23.1949 72.1018 23.1949C73.2285 23.1949 74.2714 22.9897 75.2389 22.575C75.9802 22.2567 76.6043 21.8211 77.1069 21.2725V22.8347H81.3287V0H76.8053V7.76515ZM76.2734 16.9459C75.9216 17.6286 75.4357 18.1606 74.8117 18.5459C74.1876 18.927 73.463 19.1197 72.6421 19.1197C71.8212 19.1197 71.0799 18.927 70.4265 18.5459C69.7731 18.1647 69.2663 17.6328 68.902 16.9459C68.5418 16.2632 68.3575 15.48 68.3575 14.5921C68.3575 13.7042 68.5376 12.9293 68.902 12.255C69.2622 11.5807 69.7731 11.0488 70.4265 10.6551C71.0799 10.2614 71.817 10.0687 72.6421 10.0687C73.4672 10.0687 74.1918 10.2614 74.8117 10.6425C75.4357 11.0237 75.9216 11.5556 76.2734 12.2425C76.6252 12.9252 76.8011 13.7084 76.8011 14.5963C76.8011 15.4842 76.6252 16.2674 76.2734 16.9501V16.9459Z" fill="currentColor"></path>
                    <path d="M88.5214 0H83.998V22.8263H88.5214V0Z" fill="currentColor"></path>
                    <path d="M108.003 6.36133H103.148L99.9611 15.0395C99.7014 15.6301 99.4543 16.2248 99.2114 16.8237L95.3707 6.36133H90.5164L96.9748 22.746C96.4848 24.0821 95.8984 25.481 95.178 26.214C93.243 28.6976 88.64 28.5678 88.5395 24.9114H84.0371C83.9533 28.3668 86.6129 31.5289 89.9971 32.1446C94.8262 33.1791 99.1443 29.6526 100.594 25.2967L108.003 6.36133Z" fill="currentColor"></path>
                </g>
                <defs><clipPath id="clip0_2061_12667"><rect width="108" height="32.3296" fill="currentColor"></rect></clipPath></defs>
            </svg>
        </a>

        <div class="flex items-center gap-6">
            <a href="https://help.wordly.ai/" target="_blank" class="header-link block" style="width: 300px;">
                <img class="w-full h-auto" src="https://help.wordly.ai/hs-fs/hubfs/Knowledge%20Base%20Graphics/KB%20Header.png?width=667" alt="Knowledge Center">
            </a>
            <button onclick="logout()" title="Logout" class="bg-slate-900 text-white p-2.5 rounded-lg hover:bg-red-600 transition-colors shadow-sm">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                </svg>
            </button>
        </div>
    </nav>

    <header class="mb-3 flex flex-wrap gap-4 items-center bg-slate-100 p-2 rounded-xl border border-slate-200">
        <div class="w-full md:w-1/3">
            <input type="text" id="search" placeholder="Search Title, ID, or Label..." class="w-full px-4 py-2 border rounded-lg outline-none focus:ring-2 focus:ring-blue-500 shadow-inner text-base">
        </div>
        <div class="relative">
            <button type="button" onclick="toggleApiKeyPopover(event)" title="Wordly API Key" class="relative bg-white border p-2.5 rounded-lg shadow-inner hover:bg-slate-50">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-slate-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                </svg>
                <span id="apiKeyDot" class="hidden absolute top-1 right-1 h-2 w-2 rounded-full bg-green-500"></span>
            </button>
            <div id="apiKeyPopover" class="hidden absolute left-0 mt-2 z-50 bg-white border shadow-lg rounded-lg p-3" style="width: 260px;">
                <input type="password" id="apiKey" placeholder="Wordly API Key" autocomplete="off" class="w-full px-4 py-2 border rounded-lg outline-none focus:ring-2 focus:ring-blue-500 shadow-inner text-base font-mono">
            </div>
        </div>
        <div class="flex items-center gap-2 px-2"><input type="checkbox" id="filterActive" class="w-5 h-5 cursor-pointer"><label for="filterActive" class="text-sm font-black uppercase cursor-pointer">Live Only</label></div>
        <div class="flex items-center gap-2 px-2"><input type="checkbox" id="showUnused" class="w-5 h-5 cursor-pointer"><label for="showUnused" class="text-sm font-black uppercase cursor-pointer">Show Unused</label></div>
        <div class="flex gap-4 items-center ml-auto">
            <div class="bg-green-50 border border-green-200 px-4 py-2 rounded-lg text-center"><span class="text-sm font-black text-green-700 uppercase">Active</span><p id="activeCount" class="text-3xl font-black text-green-900 leading-none">0</p></div>
            <div class="bg-white border px-4 py-2 rounded-lg text-center"><span class="text-sm font-black text-slate-500 uppercase">Inactive</span><p id="inactiveCount" class="text-3xl font-black leading-none text-slate-900">0</p></div>
            <div class="flex flex-col items-center pl-4 border-l">
                <span id="timerText" class="text-sm font-mono font-bold text-slate-400">SYNC: 30S</span>
                <button onclick="manualRefresh()" class="bg-blue-600 text-white p-2 rounded-full shadow-md"><svg id="refreshIcon" xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg></button>
            </div>
        </div>
    </header>

    <div id="bulkToolbar" class="hidden mb-3 flex items-center gap-3 bg-slate-900 text-white px-4 py-2 rounded-xl">
        <span id="bulkCount" class="text-sm font-black uppercase">0 selected</span>
        <div class="flex gap-2 ml-auto">
            <button onclick="bulkSplit()" title="Split Transcript" class="flex items-center gap-1.5 bg-white/10 hover:bg-white/20 px-3 py-1.5 rounded-lg text-xs font-bold uppercase">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:14px;height:14px;">
                    <path d="M14 12H16M2 12H4M20 12H22M3 23C3 22.7374 3.05173 17.4773 3.15224 17.2346C3.25275 16.992 3.40007 16.7715 3.58579 16.5858C3.7715 16.4001 3.99198 16.2528 4.23463 16.1522C4.47728 16.0517 4.73736 16 5 16H19C19.2626 16 19.5227 16.0517 19.7654 16.1522C20.008 16.2528 20.2285 16.4001 20.4142 16.5858C20.5999 16.7715 20.7472 16.992 20.8478 17.2346C20.9483 17.4773 21 22.7374 21 23M3 1V6C3 6.53043 3.21071 7.03914 3.58579 7.41421C3.96086 7.78929 4.46957 8 5 8H19C19.5304 8 20.0391 7.78929 20.4142 7.41421C20.7893 7.03914 21 6.53043 21 6V1M8 12H10"/>
                </svg>
                Split
            </button>
            <button onclick="bulkEnd()" title="End Session" class="flex items-center gap-1.5 bg-red-600 hover:bg-red-700 px-3 py-1.5 rounded-lg text-xs font-bold uppercase">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:14px;height:14px;">
                    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>
                </svg>
                End
            </button>
        </div>
    </div>

    <div class="overflow-x-auto border border-slate-200 rounded-xl bg-white shadow-sm">
        <table class="w-full text-left" id="sessionTable">
            <thead class="bg-slate-900 text-slate-200 text-sm uppercase font-black tracking-widest">
                <tr><th class="px-2 py-3 w-10"><input type="checkbox" id="selectAllLive" onclick="toggleSelectAllLive(this)" class="w-4 h-4 cursor-pointer"></th><th class="px-2 py-3 w-16">Status</th><th class="px-4 py-3">Session Title</th><th class="px-4 py-3 text-right">Actions</th></tr>
            </thead>
            <tbody id="tableBody" class="divide-y divide-slate-100"></tbody>
        </table>
    </div>

    <script>
        let allSessions = [];
        let countdown = 30;
        let timerId = null;

        function getApiKey() {
            return sessionStorage.getItem('wordlyApiKey') || '';
        }

        function updateApiKeyDot() {
            document.getElementById('apiKeyDot').classList.toggle('hidden', !getApiKey());
        }

        function toggleApiKeyPopover(e) {
            e.stopPropagation();
            document.getElementById('apiKeyPopover').classList.toggle('hidden');
        }

        document.addEventListener('click', (e) => {
            const popover = document.getElementById('apiKeyPopover');
            if (!popover.classList.contains('hidden') && !popover.contains(e.target)) {
                popover.classList.add('hidden');
            }
        });

        document.getElementById('apiKey').value = getApiKey();
        updateApiKeyDot();
        document.getElementById('apiKey').addEventListener('change', (e) => {
            sessionStorage.setItem('wordlyApiKey', e.target.value.trim());
            updateApiKeyDot();
            document.getElementById('apiKeyPopover').classList.add('hidden');
            fetchData();
        });

        async function fetchData() {
            const icon = document.getElementById('refreshIcon');
            const body = document.getElementById('tableBody');
            if(icon) icon.classList.add('refreshing');

            try {
                const res = await fetch('/api/sessions', { headers: { 'X-Wordly-Api-Key': getApiKey() } });
                const data = await res.json();

                if (data.error === "MISSING_KEY") {
                    body.innerHTML = `<tr><td colspan="4" class="p-10 text-center bg-red-50 text-red-600 font-bold border-2 border-red-200 rounded-xl text-lg">
                        Enter your Wordly API key above to load sessions.
                    </td></tr>`;
                    updateCounters(true);
                    if(icon) icon.classList.remove('refreshing');
                    return;
                }

                allSessions = data.sessions || [];
                updateCounters(); render();
            } catch (e) {
                console.error("Sync Error:", e);
                body.innerHTML = '<tr><td colspan="4" class="p-10 text-center text-red-400 font-bold italic uppercase tracking-widest text-lg">Sync Error. Check Connection.</td></tr>';
            }
            if(icon) icon.classList.remove('refreshing');
        }

        function logout() {
            if (!confirm("Log out and clear your saved API key?")) return;
            sessionStorage.removeItem('wordlyApiKey');
            location.reload();
        }

        function scheduleMidnightClear() {
            const now = new Date();
            const nextMidnight = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1, 0, 0, 0);
            const msUntilMidnight = nextMidnight - now;
            setTimeout(() => {
                sessionStorage.removeItem('wordlyApiKey');
                location.reload();
            }, msUntilMidnight);
        }

        function updateCounters(isError = false) {
            if (isError) {
                document.getElementById('activeCount').textContent = '--';
                document.getElementById('inactiveCount').textContent = '--';
                document.title = "(! ERROR) Wordly Mission Control";
                return;
            }
            const active = allSessions.filter(s => (s.state || "").toLowerCase() === 'started').length;
            document.getElementById('activeCount').textContent = active;
            document.getElementById('inactiveCount').textContent = allSessions.length - active;
            document.title = (active > 0 ? `(${active}) ` : '') + "Wordly Mission Control";
        }

        let selectedSessions = {}; // sessionId -> passcode, for bulk actions

        function labelText(s) {
            const parts = [];
            if (s.label) parts.push(s.label);
            (s.labels || []).forEach(f => {
                if (f && f.name) parts.push(f.value ? `${f.name}: ${f.value}` : f.name);
            });
            return parts.join(' · ');
        }

        function render() {
            const body = document.getElementById('tableBody');
            const search = document.getElementById('search').value.toLowerCase();
            const activeOnly = document.getElementById('filterActive').checked;
            const showUnused = document.getElementById('showUnused').checked;
            const filtered = allSessions.filter(s => {
                const title = (s.title || "").toLowerCase();
                const sid = (s.sessionId || "").toLowerCase();
                const labels = labelText(s).toLowerCase();
                const state = (s.state || "").toLowerCase();
                const isLive = state === 'started';
                const isCreated = state === 'created';
                if (isCreated && !showUnused) return false;
                return (activeOnly ? isLive : true) && (title.includes(search) || sid.includes(search) || labels.includes(search));
            });
            filtered.sort((a, b) => {
                const aCreated = (a.state || "").toLowerCase() === 'created' ? 1 : 0;
                const bCreated = (b.state || "").toLowerCase() === 'created' ? 1 : 0;
                return aCreated - bCreated;
            });
            body.innerHTML = filtered.length === 0 ? '<tr><td colspan="4" class="p-10 text-center text-slate-400 italic font-bold uppercase tracking-widest text-lg">No matching sessions.</td></tr>' : '';
            filtered.forEach(s => {
                const state = (s.state || "").toLowerCase();
                const isLive = state === 'started';
                const isCreated = state === 'created';
                const badgeClass = isLive ? 'bg-green-100 text-green-700' : (isCreated ? 'bg-red-100 text-red-600' : 'bg-slate-100 text-slate-500');
                const badgeText = isLive ? 'LIVE' : (s.state || "").toUpperCase();
                const full = labelText(s);
                const truncated = full.length > 42 ? full.slice(0, 42) + '…' : full;
                const labelRow = full ? `<div class="text-xs text-slate-500 mt-1 cursor-pointer" onclick="toggleLabel(this)" data-full="${full.replace(/"/g,'&quot;')}" data-expanded="false">${truncated}</div>` : '';
                const isChecked = selectedSessions[s.sessionId] ? 'checked' : '';
                const row = `
                    <tr class="${isLive ? 'active-row' : ''}">
                        <td class="px-2 py-4">
                            ${isLive ? `<input type="checkbox" ${isChecked} onchange="toggleSelect('${s.sessionId}', '${s.passcode}', this)" class="w-4 h-4 cursor-pointer">` : ''}
                        </td>
                        <td class="px-2 py-4">
                            <span class="px-1.5 py-0.5 rounded text-xs font-black ${badgeClass}">
                                ${badgeText}
                            </span>
                        </td>
                        <td class="px-4 py-4">
                            <div class="font-bold text-lg text-slate-900">${s.title || 'Untitled'}</div>
                            <div class="text-sm text-blue-600 font-mono mt-1 uppercase tracking-tight">ID: ${s.sessionId} | PASS: ${s.passcode}</div>
                            ${labelRow}
                        </td>
                        <td class="px-4 py-4 text-right whitespace-nowrap">
                            <a href="https://attend.wordly.ai/enter/${s.sessionId}" target="_blank" class="text-blue-600 text-sm font-black uppercase tracking-tighter hover:underline">Attend</a>
                            <a href="https://join.wordly.ai/enter/${s.sessionId}?key=${s.passcode}" target="_blank" class="bg-slate-900 text-white px-2 py-1.5 rounded text-sm font-black uppercase tracking-tighter hover:bg-blue-600 ml-3">Present</a>
                            ${isLive ? `<button onclick="endSession('${s.sessionId}', '${s.passcode}')" class="border-2 border-red-600 text-red-600 px-2 py-1 rounded text-sm font-black uppercase ml-3 hover:bg-red-600 hover:text-white transition-all">End Session</button>` : ''}
                        </td>
                    </tr>`;
                body.insertAdjacentHTML('beforeend', row);
            });
        }

        function toggleLabel(el) {
            const full = el.dataset.full;
            const expanded = el.dataset.expanded === 'true';
            if (expanded) {
                el.textContent = full.length > 42 ? full.slice(0, 42) + '…' : full;
                el.dataset.expanded = 'false';
            } else {
                el.textContent = full;
                el.dataset.expanded = 'true';
            }
        }

        function confirmAction(promptText) {
            const check = prompt(promptText + ' Type "asdf" to confirm:');
            return (check || '').trim().toLowerCase() === 'asdf';
        }

        async function endSession(id, pass) {
            if (!confirmAction(`End the live session ${id} for everyone?`)) return;
            await fetch("/api/sessions/end/" + id + "?passcode=" + pass, { method: "POST" });
            fetchData();
        }

        function toggleSelect(id, pass, el) {
            if (el.checked) selectedSessions[id] = pass;
            else delete selectedSessions[id];
            updateBulkToolbar();
        }

        function toggleSelectAllLive(el) {
            document.querySelectorAll('#tableBody input[type=checkbox]').forEach(cb => {
                cb.checked = el.checked;
                cb.dispatchEvent(new Event('change'));
            });
        }

        function updateBulkToolbar() {
            const count = Object.keys(selectedSessions).length;
            document.getElementById('bulkToolbar').classList.toggle('hidden', count === 0);
            document.getElementById('bulkCount').textContent = `${count} selected`;
        }

        async function bulkEnd() {
            const ids = Object.keys(selectedSessions);
            if (!ids.length) return;
            if (!confirmAction(`End ${ids.length} live session(s) for everyone?`)) return;
            for (const id of ids) {
                await fetch("/api/sessions/end/" + id + "?passcode=" + selectedSessions[id], { method: "POST" });
            }
            selectedSessions = {};
            updateBulkToolbar();
            fetchData();
        }

        async function bulkSplit() {
            const ids = Object.keys(selectedSessions);
            if (!ids.length) return;
            if (!confirmAction(`Split the transcript for ${ids.length} session(s)?`)) return;
            for (const id of ids) {
                await fetch("/api/sessions/split/" + id + "?passcode=" + selectedSessions[id], { method: "POST" });
            }
            selectedSessions = {};
            updateBulkToolbar();
            fetchData();
        }

        function startTimer() {
            clearInterval(timerId); countdown = 30;
            timerId = setInterval(() => {
                countdown--; document.getElementById('timerText').textContent = "Sync: " + countdown + "s";
                if (countdown <= 0) { fetchData(); countdown = 30; }
            }, 1000);
        }

        function manualRefresh() { fetchData(); startTimer(); }
        document.getElementById('search').addEventListener('input', render);
        document.getElementById('filterActive').addEventListener('change', render);
        document.getElementById('showUnused').addEventListener('change', render);
        fetchData(); startTimer(); scheduleMidnightClear();
    </script>
</body>
</html>
''')

if __name__ == '__main__':
    PORT = 9192
    URL = f"http://127.0.0.1:{PORT}"

    def open_browser():
        webbrowser.open_new(URL)

    if not os.environ.get("WERKZEUG_RUN_MAIN"):
        Timer(1.5, open_browser).start()
        print(f"🚀 MISSION CONTROL LAUNCHING AT: {URL}")

    app.run(host='0.0.0.0', port=PORT, debug=True)
