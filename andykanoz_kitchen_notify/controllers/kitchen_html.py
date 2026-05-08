"""Kitchen Display HTML page, served directly from the controller.

Placeholders (Python str.format style):
  {vapid_public_key} — VAPID public key for Push subscription
  {user_name}        — currently logged in Odoo user name
  {sw_version}       — bumped whenever SW source changes, for cache-busting

NOTE: any literal { or } in CSS/JS must be doubled ({{ }}).

DEBUG MODE
----------
Append ?debug=1 to the URL (e.g. /kitchen?debug=1) to reveal the debug log
panel and the "Reset SW" troubleshooting button. In normal use the UI is
kept clean for kitchen staff. Push notification dbg() calls still log to
the browser console regardless of debug mode.
"""

KITCHEN_DISPLAY_HTML = r"""<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="theme-color" content="#0f172a">
    <title>Gopokaja Kitchen</title>
    <link rel="manifest" href="/kitchen/manifest.json">
    <link rel="icon" type="image/png" href="/andykanoz_kitchen_notify/static/description/icon.png">
    <link rel="apple-touch-icon" href="/andykanoz_kitchen_notify/static/description/icon.png">
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }}
        html, body {{
            background: #0f172a;
            color: #e2e8f0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            min-height: 100vh;
            overscroll-behavior: none;
        }}
        body {{ padding: 12px; padding-bottom: 80px; }}

        .topbar {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 10px 14px;
            background: #1e293b;
            border-radius: 12px;
            margin-bottom: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.3);
        }}
        .topbar h1 {{ font-size: 18px; font-weight: 700; color: #f1f5f9; }}
        .topbar .user {{ font-size: 12px; color: #94a3b8; }}
        .sw-tag {{ display: none; }}
        .debug-mode .sw-tag {{ display: inline; }}

        .actions {{ display: flex; gap: 8px; margin-bottom: 14px; flex-wrap: wrap; }}
        .btn {{
            flex: 1;
            min-width: 120px;
            padding: 10px 12px;
            border: none;
            border-radius: 10px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.1s, opacity 0.2s;
        }}
        .btn:active {{ transform: scale(0.97); }}
        .btn-primary {{ background: #3b82f6; color: white; }}
        .btn-muted {{ background: #334155; color: #cbd5e1; }}
        .btn-danger {{ background: #7f1d1d; color: #fecaca; }}
        .btn[disabled] {{ opacity: 0.5; cursor: not-allowed; }}

        /* Debug-only elements: hidden by default, revealed via .debug-mode on body */
        #btn-reset {{ display: none; }}
        .debug-mode #btn-reset {{ display: block; }}
        .debug-log {{
            display: none;
            background: #1e293b;
            border-radius: 8px;
            padding: 8px 12px;
            font-size: 10px;
            color: #94a3b8;
            margin-bottom: 10px;
            font-family: monospace;
            max-height: 120px;
            overflow-y: auto;
        }}
        .debug-mode .debug-log {{ display: block; }}
        .debug-log .err {{ color: #f87171; }}
        .debug-log .ok {{ color: #34d399; }}

        .status-bar {{ font-size: 11px; color: #64748b; text-align: center; margin-bottom: 10px; }}
        .status-bar .dot {{
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #10b981;
            margin-right: 4px;
            vertical-align: middle;
            animation: pulse 2s infinite;
        }}
        @keyframes pulse {{ 0%,100% {{ opacity: 1; }} 50% {{ opacity: 0.4; }} }}

        .columns {{ display: grid; grid-template-columns: 1fr; gap: 12px; }}
        @media (min-width: 768px) {{ .columns {{ grid-template-columns: 1fr 1fr 1fr; }} }}

        .col {{
            background: #1e293b;
            border-radius: 12px;
            padding: 12px;
            min-height: 120px;
        }}
        .col-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding-bottom: 10px;
            margin-bottom: 10px;
            border-bottom: 2px solid #334155;
        }}
        .col-header h2 {{
            font-size: 14px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .col-header .count {{
            background: #334155;
            padding: 2px 10px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }}
        .col-waiting .col-header h2 {{ color: #fbbf24; }}
        .col-waiting .col-header {{ border-bottom-color: #fbbf24; }}
        .col-cooking .col-header h2 {{ color: #60a5fa; }}
        .col-cooking .col-header {{ border-bottom-color: #60a5fa; }}
        .col-done .col-header h2 {{ color: #34d399; }}
        .col-done .col-header {{ border-bottom-color: #34d399; }}

        .card {{
            background: #0f172a;
            border-radius: 10px;
            padding: 12px;
            margin-bottom: 10px;
            border-left: 4px solid #475569;
            animation: slideIn 0.25s ease-out;
        }}
        @keyframes slideIn {{ from {{ opacity: 0; transform: translateY(-6px); }} to {{ opacity: 1; transform: translateY(0); }} }}
        .col-waiting .card {{ border-left-color: #fbbf24; }}
        .col-cooking .card {{ border-left-color: #60a5fa; }}
        .col-done .card {{ border-left-color: #34d399; opacity: 0.7; }}

        .card-product {{ font-size: 15px; font-weight: 700; color: #f1f5f9; margin-bottom: 4px; }}
        .card-meta {{
            display: flex;
            justify-content: space-between;
            font-size: 11px;
            color: #94a3b8;
            margin-bottom: 8px;
        }}
        .card-meta .qty {{ color: #fbbf24; font-weight: 700; font-size: 13px; }}
        .card-note {{ font-size: 11px; color: #f87171; font-style: italic; margin-bottom: 8px; }}
        .card-actions {{ display: flex; gap: 6px; }}
        .card-actions button {{
            flex: 1;
            padding: 10px;
            border: none;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 700;
            cursor: pointer;
        }}
        .btn-start {{ background: #3b82f6; color: white; }}
        .btn-done {{ background: #10b981; color: white; }}

        .empty {{ text-align: center; padding: 24px 12px; color: #475569; font-size: 12px; }}

        .toast {{
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: #1e293b;
            color: #f1f5f9;
            padding: 10px 18px;
            border-radius: 8px;
            font-size: 13px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.4);
            z-index: 1000;
            display: none;
            max-width: 90vw;
            text-align: center;
        }}
        .toast.show {{ display: block; animation: toastIn 0.3s ease-out; }}
        @keyframes toastIn {{ from {{ opacity: 0; transform: translate(-50%, 10px); }} to {{ opacity: 1; transform: translate(-50%, 0); }} }}
    </style>
</head>
<body>
    <div class="topbar">
        <div>
            <h1>🍳 Gopokaja Kitchen</h1>
            <div class="user">{user_name}<span class="sw-tag"> · SW v{sw_version}</span></div>
        </div>
        <div class="status-bar" style="margin: 0;">
            <span class="dot"></span>
            <span id="conn-status">Live</span>
        </div>
    </div>

    <div class="actions">
        <button id="btn-notify" class="btn btn-primary">🔔 Izinkan Notifikasi</button>
        <button id="btn-install" class="btn btn-muted" disabled>📲 Install App</button>
        <button id="btn-reset" class="btn btn-danger">♻ Reset SW</button>
    </div>

    <div class="debug-log" id="debug-log"></div>

    <div class="status-bar">
        Update otomatis tiap 10 detik — terakhir: <span id="last-update">-</span>
    </div>

    <div class="columns">
        <div class="col col-waiting">
            <div class="col-header">
                <h2>Menunggu</h2>
                <span class="count" id="count-waiting">0</span>
            </div>
            <div id="list-waiting"><div class="empty">Belum ada order</div></div>
        </div>
        <div class="col col-cooking">
            <div class="col-header">
                <h2>Sedang Dimasak</h2>
                <span class="count" id="count-cooking">0</span>
            </div>
            <div id="list-cooking"><div class="empty">Belum ada</div></div>
        </div>
        <div class="col col-done">
            <div class="col-header">
                <h2>Selesai (10 menit)</h2>
                <span class="count" id="count-done">0</span>
            </div>
            <div id="list-done"><div class="empty">Belum ada</div></div>
        </div>
    </div>

    <div class="toast" id="toast"></div>

    <script>
        const VAPID_PUBLIC_KEY = "{vapid_public_key}";
        const SW_VERSION = "{sw_version}";
        const SW_URL = '/kitchen/sw.js?v=' + SW_VERSION;
        const SW_SCOPE = '/kitchen';  // no trailing slash — matches /kitchen and /kitchen/...
        const POLL_INTERVAL_MS = 10000;
        let deferredPrompt = null;

        // Debug mode is enabled by ?debug=1 in the URL.
        // It reveals the debug log panel and the Reset SW button.
        const DEBUG_MODE = new URLSearchParams(location.search).get('debug') === '1';
        if (DEBUG_MODE) {{
            document.body.classList.add('debug-mode');
        }}

        function toast(msg) {{
            const el = document.getElementById('toast');
            el.textContent = msg;
            el.classList.add('show');
            setTimeout(() => el.classList.remove('show'), 3500);
        }}

        // dbg() always logs to the console, but only appends to the on-page
        // log panel when debug mode is on. This keeps the staff UI clean
        // while preserving full troubleshooting info for admins.
        function dbg(msg, kind) {{
            console.log('[kitchen]', msg);
            if (!DEBUG_MODE) return;
            const el = document.getElementById('debug-log');
            const line = document.createElement('div');
            line.className = kind || '';
            const t = new Date().toLocaleTimeString('id-ID');
            line.textContent = '[' + t + '] ' + msg;
            el.appendChild(line);
            while (el.children.length > 12) el.removeChild(el.firstChild);
            el.scrollTop = el.scrollHeight;
        }}

        function urlBase64ToUint8Array(base64String) {{
            const padding = '='.repeat((4 - base64String.length % 4) % 4);
            const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
            const rawData = window.atob(base64);
            const outputArray = new Uint8Array(rawData.length);
            for (let i = 0; i < rawData.length; i++) {{
                outputArray[i] = rawData.charCodeAt(i);
            }}
            return outputArray;
        }}

        function formatTime(isoStr) {{
            if (!isoStr) return '';
            try {{
                const d = new Date(isoStr.replace(' ', 'T') + 'Z');
                return d.toLocaleTimeString('id-ID', {{ hour: '2-digit', minute: '2-digit' }});
            }} catch (e) {{ return ''; }}
        }}

        async function odooJsonRpc(url, params) {{
            const res = await fetch(url, {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                credentials: 'same-origin',
                body: JSON.stringify({{
                    jsonrpc: '2.0',
                    method: 'call',
                    params: params || {{}},
                }}),
            }});
            const data = await res.json();
            return data.result;
        }}

        function escapeHtml(s) {{
            return String(s || '').replace(/[&<>"']/g, c => ({{
                '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
            }})[c]);
        }}

        // ==============================================================
        // Order polling
        // ==============================================================
        async function fetchOrders() {{
            try {{
                const res = await fetch('/kitchen/orders', {{ credentials: 'same-origin' }});
                if (!res.ok) throw new Error('HTTP ' + res.status);
                const data = await res.json();
                renderColumn('waiting', data.waiting);
                renderColumn('cooking', data.cooking);
                renderColumn('done', data.done);
                document.getElementById('last-update').textContent =
                    new Date().toLocaleTimeString('id-ID');
                document.getElementById('conn-status').textContent = 'Live';
            }} catch (e) {{
                console.error('[kitchen] fetch failed', e);
                document.getElementById('conn-status').textContent = 'Offline';
            }}
        }}
        window.fetchOrders = fetchOrders;

        function renderColumn(status, items) {{
            const listEl = document.getElementById('list-' + status);
            const countEl = document.getElementById('count-' + status);
            countEl.textContent = items.length;
            if (items.length === 0) {{
                listEl.innerHTML = '<div class="empty">Kosong</div>';
                return;
            }}
            listEl.innerHTML = items.map(item => cardHtml(item, status)).join('');
        }}

        // Linear flow: waiting -> [Mulai Masak] -> cooking -> [Selesai] -> done
        function cardHtml(item, status) {{
            const qtyStr = Number.isInteger(item.qty) ? item.qty : item.qty.toFixed(1);
            const note = item.note ? '<div class="card-note">📝 ' + escapeHtml(item.note) + '</div>' : '';
            let actions = '';
            if (status === 'waiting') {{
                actions = '<button class="btn-start" onclick="updateStatus(' + item.id + ',\'cooking\')">▶ Mulai Masak</button>';
            }} else if (status === 'cooking') {{
                actions = '<button class="btn-done" onclick="updateStatus(' + item.id + ',\'done\')">✓ Selesai</button>';
            }}
            const actionsHtml = actions ? '<div class="card-actions">' + actions + '</div>' : '';
            return (
                '<div class="card">' +
                '<div class="card-product">' + escapeHtml(item.product_name) + '</div>' +
                '<div class="card-meta"><span>#' + escapeHtml(item.pos_ref) + ' · ' + formatTime(item.order_time) + '</span><span class="qty">×' + qtyStr + '</span></div>' +
                note +
                actionsHtml +
                '</div>'
            );
        }}

        window.updateStatus = async function(id, newStatus) {{
            try {{
                const result = await odooJsonRpc('/kitchen/update-status', {{
                    id: id,
                    status: newStatus,
                }});
                if (result && result.success) {{
                    fetchOrders();
                }} else {{
                    toast('Gagal update: ' + ((result && result.error) || 'unknown'));
                }}
            }} catch (e) {{
                toast('Error: ' + e.message);
            }}
        }};

        // ==============================================================
        // Service Worker registration
        // ==============================================================
        async function unregisterOldKitchenWorkers() {{
            if (!('serviceWorker' in navigator)) return;
            const regs = await navigator.serviceWorker.getRegistrations();
            for (const reg of regs) {{
                if (reg.scope.includes('/kitchen') &&
                    !(reg.active && reg.active.scriptURL.includes('v=' + SW_VERSION))) {{
                    dbg('Unregister old SW: ' + reg.scope);
                    try {{ await reg.unregister(); }} catch (e) {{}}
                }}
            }}
        }}

        async function registerSW() {{
            if (!('serviceWorker' in navigator)) {{
                dbg('SW tidak support di browser ini', 'err');
                return null;
            }}
            try {{
                dbg('Register SW: ' + SW_URL + ' scope=' + SW_SCOPE);
                const reg = await navigator.serviceWorker.register(SW_URL, {{ scope: SW_SCOPE }});
                dbg('SW registered: scope=' + reg.scope, 'ok');
                return reg;
            }} catch (e) {{
                dbg('SW register GAGAL: ' + e.message, 'err');
                return null;
            }}
        }}

        async function waitForActiveSW(timeoutMs) {{
            const start = Date.now();
            while (Date.now() - start < timeoutMs) {{
                const reg = await navigator.serviceWorker.getRegistration(SW_SCOPE);
                if (reg && reg.active && reg.active.state === 'activated') {{
                    return reg;
                }}
                await new Promise(r => setTimeout(r, 250));
            }}
            throw new Error('SW not active after ' + timeoutMs + 'ms');
        }}

        async function checkExistingSubscription() {{
            try {{
                if (!('serviceWorker' in navigator) || !('PushManager' in window)) {{
                    dbg('Push API tidak support (butuh HTTPS)', 'err');
                    return;
                }}
                const reg = await waitForActiveSW(5000);
                const existing = await reg.pushManager.getSubscription();
                if (existing) {{
                    document.getElementById('btn-notify').textContent = '🔔 Notifikasi Aktif';
                    document.getElementById('btn-notify').disabled = true;
                    dbg('Sudah subscribed', 'ok');
                }} else {{
                    dbg('Belum subscribe — klik tombol Izinkan Notifikasi');
                }}
            }} catch (e) {{
                dbg('Check sub GAGAL: ' + e.message, 'err');
            }}
        }}

        async function subscribePush() {{
            dbg('Mulai subscribe...');
            if (!VAPID_PUBLIC_KEY) {{
                dbg('VAPID public key KOSONG!', 'err');
                toast('VAPID public key kosong');
                return;
            }}
            dbg('VAPID key OK (' + VAPID_PUBLIC_KEY.length + ' chars)');

            if (!('serviceWorker' in navigator) || !('PushManager' in window)) {{
                dbg('Browser tidak support Push (butuh HTTPS)', 'err');
                toast('Browser tidak support Push');
                return;
            }}
            if (location.protocol !== 'https:' && location.hostname !== 'localhost') {{
                dbg('HALAMAN BUKAN HTTPS', 'err');
                toast('Buka via HTTPS untuk push');
                return;
            }}

            try {{
                dbg('Tunggu SW active...');
                const reg = await waitForActiveSW(5000);
                dbg('SW active OK', 'ok');

                dbg('Minta izin notifikasi...');
                const permission = await Notification.requestPermission();
                dbg('Permission: ' + permission, permission === 'granted' ? 'ok' : 'err');
                if (permission !== 'granted') {{
                    toast('Izin notifikasi ditolak');
                    return;
                }}

                dbg('pushManager.subscribe...');
                const sub = await reg.pushManager.subscribe({{
                    userVisibleOnly: true,
                    applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY),
                }});
                dbg('Subscribe OK', 'ok');

                const subJson = sub.toJSON();
                dbg('POST /kitchen/subscribe...');
                const result = await odooJsonRpc('/kitchen/subscribe', {{
                    endpoint: subJson.endpoint,
                    keys: subJson.keys,
                    deviceName: navigator.userAgent.slice(0, 60),
                }});

                if (result && result.success) {{
                    dbg('SIMPAN OK (id=' + result.id + ')', 'ok');
                    toast('✅ Notifikasi aktif');
                    document.getElementById('btn-notify').textContent = '🔔 Notifikasi Aktif';
                    document.getElementById('btn-notify').disabled = true;
                }} else {{
                    dbg('Simpan GAGAL: ' + JSON.stringify(result), 'err');
                    toast('Gagal simpan subscription');
                }}
            }} catch (e) {{
                dbg('EXCEPTION: ' + e.name + ': ' + e.message, 'err');
                console.error('[kitchen] Push subscribe failed', e);
                toast('Gagal subscribe: ' + e.message);
            }}
        }}
        window.subscribePush = subscribePush;

        // Reset button — only shown in debug mode. Nukes all SW
        // registrations and subscriptions for /kitchen, then reloads.
        async function resetServiceWorker() {{
            dbg('Reset SW...');
            try {{
                if ('serviceWorker' in navigator) {{
                    const regs = await navigator.serviceWorker.getRegistrations();
                    for (const reg of regs) {{
                        if (reg.scope.includes('/kitchen')) {{
                            const sub = await reg.pushManager.getSubscription();
                            if (sub) {{
                                try {{ await sub.unsubscribe(); }} catch (e) {{}}
                            }}
                            await reg.unregister();
                            dbg('Unregistered: ' + reg.scope, 'ok');
                        }}
                    }}
                }}
                dbg('Reset selesai. Reload 2s...', 'ok');
                setTimeout(() => location.reload(), 2000);
            }} catch (e) {{
                dbg('Reset GAGAL: ' + e.message, 'err');
            }}
        }}

        // ==============================================================
        // PWA install
        // ==============================================================
        const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) ||
                      (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
        const isInStandalone = window.matchMedia('(display-mode: standalone)').matches
                               || window.navigator.standalone === true;

        window.addEventListener('beforeinstallprompt', (e) => {{
            e.preventDefault();
            deferredPrompt = e;
            const btn = document.getElementById('btn-install');
            btn.disabled = false;
            btn.classList.remove('btn-muted');
            btn.classList.add('btn-primary');
            dbg('beforeinstallprompt fired — Install button enabled', 'ok');
        }});

        window.addEventListener('appinstalled', () => {{
            dbg('App installed!', 'ok');
            toast('✅ App berhasil terinstall!');
            const btn = document.getElementById('btn-install');
            btn.textContent = '✅ Terinstall';
            btn.disabled = true;
            btn.classList.remove('btn-primary');
            btn.classList.add('btn-muted');
            deferredPrompt = null;
        }});

        // If already running as installed PWA, update button
        if (isInStandalone) {{
            const btn = document.getElementById('btn-install');
            btn.textContent = '✅ Terinstall';
            btn.disabled = true;
            dbg('Running as installed PWA', 'ok');
        }} else if (isIOS) {{
            // iOS Safari doesn't support beforeinstallprompt
            const btn = document.getElementById('btn-install');
            btn.disabled = false;
            btn.textContent = '📲 Add to Home Screen';
            btn.classList.remove('btn-muted');
            btn.classList.add('btn-primary');
            dbg('iOS detected — showing manual install hint');
        }}

        document.getElementById('btn-install').addEventListener('click', async () => {{
            if (deferredPrompt) {{
                deferredPrompt.prompt();
                const {{ outcome }} = await deferredPrompt.userChoice;
                dbg('Install prompt outcome: ' + outcome, outcome === 'accepted' ? 'ok' : 'err');
                if (outcome === 'accepted') {{
                    toast('✅ App terinstall!');
                }}
                deferredPrompt = null;
                return;
            }}
            if (isIOS) {{
                toast('Tap ikon Share (↑) lalu pilih "Add to Home Screen"');
                return;
            }}
            toast('Gunakan menu browser (⋮) → "Install app" atau "Add to Home Screen"');
        }});

        document.getElementById('btn-notify').addEventListener('click', subscribePush);
        document.getElementById('btn-reset').addEventListener('click', resetServiceWorker);

        // ==============================================================
        // Boot
        // ==============================================================
        console.log('[kitchen] booting SW v' + SW_VERSION + (DEBUG_MODE ? ' (debug mode)' : ''));
        dbg('Boot SW v' + SW_VERSION);
        fetchOrders();
        setInterval(fetchOrders, POLL_INTERVAL_MS);
        (async () => {{
            try {{
                await unregisterOldKitchenWorkers();
                await registerSW();
                await checkExistingSubscription();
            }} catch (e) {{
                console.warn('[kitchen] SW setup failed (polling still works):', e);
                dbg('Setup error: ' + e.message, 'err');
            }}
        }})();
    </script>
</body>
</html>
"""
