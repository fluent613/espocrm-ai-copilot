# templates.py
# Smooth, sticky, compact. Subtle thinking chip; partial updates via fetch.

LOGIN_TEMPLATE = '''
<!doctype html>
<html>
<head>
    <title>EspoCRM AI Copilot - Welcome</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        :root { --card-pad: 48px; }
        html, body { height:100%; }
        body.no-anim * { animation:none !important; transition:none !important; }

        body{
            font-family:-apple-system, BlinkMacSystemFont,'Segoe UI',Roboto,Oxygen,Ubuntu,sans-serif;
            background:linear-gradient(180deg,#2B4C7E 0%,#4BA3C3 50%,#F5F6FA 100%);
            min-height:100vh; display:flex; align-items:center; justify-content:center;
            padding:20px; position:relative; overflow:hidden;
        }
        body.ready::before{
            animation: float 20s ease-in-out infinite;
        }
        body::before{
            content:''; position:absolute; width:200%; height:200%;
            background:
              radial-gradient(circle at 20% 80%, rgba(43,76,126,.08) 0%, transparent 50%),
              radial-gradient(circle at 80% 20%, rgba(75,163,195,.08) 0%, transparent 50%),
              radial-gradient(circle at 40% 40%, rgba(43,76,126,.04) 0%, transparent 50%);
            z-index:0;
        }
        @keyframes float{ 0%,100%{transform:translate(0,0)} 33%{transform:translate(-16px,-14px)} 66%{transform:translate(14px,-8px)} }

        .login-card{
            background:rgba(255,255,255,.98); backdrop-filter:blur(20px);
            border-radius:24px; padding:var(--card-pad); max-width:440px; width:100%;
            position:relative; z-index:1;
            box-shadow:0 12px 36px rgba(16,24,40,.12);
        }

        .logo-section{ text-align:center; margin-bottom:28px; }
        .logo{ display:inline-block; width:60px; height:60px; background:linear-gradient(135deg,#2B4C7E,#4BA3C3);
               border-radius:16px; position:relative; margin-bottom:16px; will-change:transform; }
        .logo::after{ content:'✨'; position:absolute; inset:0; display:grid; place-items:center; color:#fff; font-size:28px; }

        h1{ font-size:28px; font-weight:700; color:#1E1E1E; margin-bottom:6px; letter-spacing:-.3px; }
        .subtitle{ color:#64748B; font-size:14px; margin-bottom:2px; }
        .by-line{ font-size:11px; color:#94A3B8; }
        .by-line a{ color:#4BA3C3; text-decoration:none; font-weight:500; }

        .mission-card{ background:linear-gradient(135deg,#F0FDF4,#DCFCE7); border-radius:16px; padding:14px; margin-bottom:22px; }
        .mission-text{ font-size:13px; color:#15803D; line-height:1.55; }
        .mission-text strong{ color:#166534; }

        .form-container{ margin-bottom:18px; }
        .input-wrapper{ position:relative; margin-bottom:14px; }
        .input-wrapper::before{ content:'→'; position:absolute; left:14px; top:50%; transform:translateY(-50%); color:#CBD5E1; font-size:16px; z-index:1; }
        input[type="password"], input[type="text"]#token{
            width:100%; padding:14px 50px 14px 42px; border:2px solid #E2E8F0; border-radius:12px; font-size:15px; background:#FAFAFA;
            transition:border-color .2s, box-shadow .2s, background .2s;
        }
        input[type="password"]:focus, input[type="text"]#token:focus{ outline:none; border-color:#4BA3C3; background:#fff; box-shadow:0 0 0 3px rgba(75,163,195,.1); }
        .eye-toggle{ position:absolute; right:14px; top:50%; transform:translateY(-50%); background:none; border:none; cursor:pointer; font-size:1.2em; padding:5px; z-index:2; }

        .remember-section{ display:flex; align-items:center; gap:10px; margin-bottom:16px; padding:10px; background:#F8FAFC; border-radius:10px; cursor:pointer; }
        .checkbox-wrapper{ position:relative; width:20px; height:20px; }
        .checkbox-wrapper input{ opacity:0; position:absolute; inset:0; cursor:pointer; }
        .checkbox-custom{ position:absolute; inset:0; border:2px solid #CBD5E1; border-radius:6px; background:#fff; }
        .checkbox-wrapper input:checked ~ .checkbox-custom{ background:linear-gradient(135deg,#2B4C7E,#4BA3C3); border-color:#2B4C7E; }
        .checkbox-wrapper input:checked ~ .checkbox-custom::after{ content:'✓'; position:absolute; inset:0; display:grid; place-items:center; color:#fff; font-size:12px; }
        .remember-label{ font-size:13px; color:#475569; user-select:none; flex:1; }

        .submit-btn{
            width:100%; padding:14px; background:linear-gradient(135deg,#2B4C7E,#4BA3C3); color:#fff; border:none; border-radius:12px;
            font-size:15px; font-weight:600; cursor:pointer;
        }
        .submit-btn:disabled{ opacity:.55; cursor:not-allowed; }
        .loading{ position:relative; color:transparent !important; }
        .loading::after{
            content:''; position:absolute; width:18px; height:18px; top:50%; left:50%; margin:-9px 0 0 -9px;
            border:2px solid transparent; border-top-color:#fff; border-radius:50%; animation:spin .8s linear infinite;
        }
        @keyframes spin{ to{ transform:rotate(360deg) } }

        .error-box{ background:#FEF2F2; border:1px solid #FCA5A5; border-radius:12px; padding:12px; margin-bottom:14px; }
        .error-text{ color:#DC2626; font-size:13px; }

        .security-badge{ display:flex; align-items:center; justify-content:center; gap:8px; padding:10px; background:#F0F9FF; border-radius:10px; margin-bottom:16px; font-size:12px; color:#0284C7; }
        .footer{ text-align:center; padding-top:16px; border-top:1px solid #E2E8F0; }
        .footer-text{ font-size:11px; color:#94A3B8; line-height:1.6; }
        .footer-text a{ color:#4BA3C3; text-decoration:none; font-weight:500; }
        .charity-banner{ background:linear-gradient(135deg,#FEF3C7,#FDE68A); border-radius:10px; padding:10px; margin-top:12px; font-size:11px; color:#92400E; text-align:center; }

        @media (max-width:480px){
            :root{ --card-pad: 32px; }
            h1{ font-size:24px; }
        }
        @media (prefers-reduced-motion: reduce){ *{ animation:none !important; transition:none !important; } }
    </style>
</head>
<body class="no-anim">
    <div class="login-card">
        <div class="logo-section">
            <div class="logo"></div>
            <h1>EspoCRM AI Copilot</h1>
            <p class="subtitle">Intelligent CRM Assistant</p>
            <p class="by-line">by <a href="https://fluencydigital.io" target="_blank">Fluency Digital</a></p>
        </div>

        <div class="mission-card">
            <p class="mission-text"><strong>Open Source CRM Enhancement</strong><br>Making EspoCRM smarter with AI-powered natural language and resume parsing</p>
        </div>

        {% if error %}
            <div class="error-box"><p class="error-text">{{ error }}</p></div>
        {% endif %}

        <form method="post" id="loginForm" class="form-container">
            <div style="position:absolute; left:-10000px; top:-10000px;">
                <input type="email" name="email" tabindex="-1" autocomplete="off">
                <input type="url" name="website" tabindex="-1" autocomplete="off">
                <input type="tel" name="phone" tabindex="-1" autocomplete="off">
                <input type="text" name="company" tabindex="-1" autocomplete="off">
            </div>

            <div class="input-wrapper">
                <input type="password" name="token" id="token" placeholder="Enter your access token" autofocus required autocomplete="off">
                <button type="button" class="eye-toggle" onclick="togglePasswordVisibility()" title="Toggle password visibility">
                    <span id="eyeIcon">👁️</span>
                </button>
            </div>

            <label class="remember-section" for="remember_me">
                <div class="checkbox-wrapper">
                    <input type="checkbox" id="remember_me" name="remember_me" checked>
                    <div class="checkbox-custom"></div>
                </div>
                <span class="remember-label">Keep me logged in for 30 days</span>
            </label>

            <button type="submit" class="submit-btn" id="loginBtn">Access AI Copilot →</button>
        </form>

        <div class="security-badge">★ Protected by rate limiting and security measures</div>

        <div class="footer">
            <p class="footer-text">Secure access to your AI-powered CRM assistant<br>Open source project by <a href="https://fluencydigital.io" target="_blank">Fluency Digital</a></p>
            <div class="charity-banner">★ Supporting Feed My Starving Children</div>
        </div>
    </div>

    <script>
        // Password visibility toggle
        function togglePasswordVisibility() {
            const passwordInput = document.getElementById('token');
            const eyeIcon = document.getElementById('eyeIcon');

            if (passwordInput.type === 'password') {
                passwordInput.type = 'text';
                eyeIcon.textContent = '🙈';
            } else {
                passwordInput.type = 'password';
                eyeIcon.textContent = '👁️';
            }
        }

        // Kill first-paint jitter: remove no-anim after two frames, then start ambient bg
        requestAnimationFrame(()=>requestAnimationFrame(()=>{
            document.body.classList.remove('no-anim');
            document.body.classList.add('ready');
        }));

        document.getElementById('loginForm').addEventListener('submit', function(e){
            const btn = document.getElementById('loginBtn');
            const token = document.getElementById('token').value.trim();
            if (token.length < 3){ e.preventDefault(); alert('Please enter a valid access token'); return; }
            btn.disabled = true; btn.classList.add('loading'); btn.textContent = '';
        });
        if (document.querySelector('.error-box')){ const t=document.getElementById('token'); if(t) t.value=''; }
    </script>
</body>
</html>
'''

ENHANCED_TEMPLATE = '''
<!doctype html>
<html>
<head>
    <title>EspoCRM AI Copilot</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        *{ margin:0; padding:0; box-sizing:border-box; }
        :root{ --header-h:64px; }
        html{ scroll-padding-top: var(--header-h); }
        html, body{ height:100%; }
        body{
            font-family:-apple-system, BlinkMacSystemFont,'Segoe UI',Roboto,Oxygen,Ubuntu,sans-serif;
            background:#2B4C7E; color:#1E1E1E; height:100vh; display:flex; flex-direction:column;
            position:relative; overflow:hidden;
        }
        body::before{
            content:''; position:absolute; width:200%; height:200%;
            background:
              radial-gradient(circle at 20% 50%, rgba(75,163,195,.07) 0%, transparent 50%),
              radial-gradient(circle at 80% 80%, rgba(43,76,126,.07) 0%, transparent 50%);
            z-index:0; /* no animation to avoid scroll jank */
        }

        .container{ position:relative; z-index:1; height:100%; display:flex; flex-direction:column; max-width:1200px; margin:0 auto; width:100%; }

        /* Sticky header (no slide animation to avoid jitter) */
        .header{
            position:sticky; top:0; z-index:1000;
            background:rgba(255,255,255,.98); -webkit-backdrop-filter:blur(18px); backdrop-filter:blur(18px);
            border-bottom:1px solid rgba(226,232,240,.85);
            min-height:var(--header-h); padding:12px 32px;
            display:flex; align-items:center; justify-content:space-between;
            will-change:transform; transform:translateZ(0);
        }
        .header-left{ display:flex; align-items:center; gap:14px; }
        .logo-badge{ width:40px; height:40px; background:linear-gradient(135deg,#2B4C7E,#4BA3C3); border-radius:12px; display:grid; place-items:center; color:#fff; font-size:18px; font-weight:700; }
        .header-title{ display:flex; flex-direction:column; }
        .header-title h1{ font-size:19px; font-weight:700; color:#1E1E1E; letter-spacing:-.2px; }
        .header-subtitle{ font-size:12px; color:#64748B; }
        .header-subtitle a{ color:#4BA3C3; text-decoration:none; font-weight:500; }
        .header-right{ display:flex; align-items:center; gap:10px; }
        .status-badge{ padding:6px 10px; border-radius:16px; font-size:11px; font-weight:500; display:flex; align-items:center; gap:6px; white-space:nowrap; }
        .status-secure{ background:#DCFCE7; color:#16A34A; }
        .status-session{ background:#E6F4F7; color:#2B4C7E; }
        .logout-btn{ padding:8px 14px; background:#F1F5F9; color:#475569; border:1px solid #E2E8F0; border-radius:10px; text-decoration:none; font-size:13px; font-weight:500; }

        .mission-banner{
            background:linear-gradient(135deg,#E6F4F7,#B8E4F0);
            padding:10px 24px; display:flex; align-items:center; justify-content:center; gap:10px;
        }
        .mission-text{ font-size:13px; color:#2B4C7E; text-align:center; }
        .mission-text strong{ color:#1E1E1E; }

        .chat-container{ flex:1; display:flex; flex-direction:column; background:#F5F6FA; overflow:hidden; }
        .messages-wrapper{
            flex:1; overflow-y:auto; padding:20px 32px; display:flex; flex-direction:column; gap:14px;
            scroll-behavior:smooth; overscroll-behavior:contain;
            min-height:0; /* prevents sticky header jump on some browsers */
            contain: content; /* reduces reflow when swapping inner HTML */
        }

        /* Welcome + compressed training */
        .welcome-state{ max-width:980px; margin:0 auto; padding:16px 16px 32px; text-align:center; }
        .welcome-hero{ padding:40px 0 24px; }
        .welcome-title{ font-size:30px; font-weight:700; color:#1E1E1E; margin-bottom:12px; }
        .welcome-subtitle{ font-size:15px; color:#64748B; margin-bottom:20px; }

        .quick-commands{
            display:flex; flex-wrap:wrap; gap:8px; justify-content:center; margin:8px 0 18px;
        }
        .quick-commands button{
            border:1px solid #E2E8F0; background:#fff; border-radius:999px; padding:6px 10px; font-size:12px; color:#334155; cursor:pointer;
        }

        .instructions-section{ width:100%; padding:24px 12px 40px; }
        .instructions-head{
            display:flex; align-items:center; justify-content:space-between; gap:12px; max-width:980px; margin:0 auto 12px;
        }
        .instructions-label{ font-size:15px; font-weight:600; color:#1E1E1E; }
        .instructions-actions{ display:flex; gap:8px; }
        .instructions-actions button{
            border:1px solid #E2E8F0; background:#fff; border-radius:8px; padding:6px 10px; font-size:12px; color:#334155; cursor:pointer;
        }

        /* Two-column compact accordion */
        .features-accordion{
            max-width:980px; margin:0 auto;
            display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px;
        }
        .accordion-item{
            background:#fff; border:1px solid #E2E8F0; border-radius:12px; overflow:hidden;
        }
        .accordion-header{
            padding:12px 14px; background:#FAFAFA; cursor:pointer;
            display:flex; align-items:center; justify-content:space-between;
        }
        .accordion-title{ display:flex; align-items:center; gap:10px; font-size:14px; font-weight:600; color:#111827; }
        .accordion-icon{ width:22px; height:22px; background:linear-gradient(135deg,#2B4C7E,#4BA3C3); border-radius:6px; position:relative; flex-shrink:0; }
        .accordion-icon::after{ content:'→'; position:absolute; inset:0; display:grid; place-items:center; color:#fff; font-size:12px; }
        .accordion-arrow{ width:18px; height:18px; position:relative; }
        .accordion-arrow::after{ content:'▼'; position:absolute; inset:0; display:grid; place-items:center; font-size:10px; color:#64748B; transition:transform .2s; }
        .accordion-header.active .accordion-arrow::after{ transform:rotate(180deg); }

        .accordion-content{ max-height:0; overflow:hidden; transition:max-height .22s ease; background:#fff; }
        .accordion-content.active{ max-height:160px; }
        .accordion-body{ padding:12px 14px; font-size:13px; color:#64748B; line-height:1.55; }
        .accordion-body code{ background:#F5F6FA; padding:1px 5px; border-radius:4px; font-family:'SF Mono',Monaco,monospace; font-size:12px; color:#2B4C7E; }

        /* Compact mode tightens spacing */
        .features-accordion.compact .accordion-header{ padding:10px 12px; }
        .features-accordion.compact .accordion-body{ padding:10px 12px; font-size:12.5px; }
        .features-accordion.compact .accordion-content.active{ max-height:120px; }

        /* Messages */
        .message{ max-width:72%; }
        .message-user{ align-self:flex-end; }
        .message-assistant{ align-self:flex-start; }
        .message-bubble{ padding:12px 14px; border-radius:18px; font-size:14px; line-height:1.55; }
        .message-user .message-bubble{ background:#007AFF; color:#fff; border-bottom-right-radius:4px; }
        .message-assistant .message-bubble{ background:#fff; color:#111827; border:1px solid #E2E8F0; border-bottom-left-radius:4px; }
        .message-label{ font-size:11px; color:#94A3B8; margin-bottom:3px; padding:0 2px; }

        /* Thinking chip + typing bubble */
        .thinking-row{ display:none; align-items:center; gap:8px; font-size:12px; color:#64748B; margin-bottom:6px; }
        .spinner-star{ width:18px; height:18px; border-radius:50%; display:inline-grid; place-items:center; border:1px solid #CBD5E1; }
        .spinner-star::before{ content:'★'; font-size:12px; color:#4BA3C3; animation:spin 1.2s linear infinite; }
        @keyframes spin{ to{ transform:rotate(360deg) } }
        .typing .message-bubble{ background:#fff; border:1px dashed #CBD5E1; color:#64748B; }
        .typing-dots span{ display:inline-block; width:4px; height:4px; border-radius:50%; background:#94A3B8; margin:0 2px; animation:blink 1.2s infinite; }
        .typing-dots span:nth-child(2){ animation-delay:.2s; }
        .typing-dots span:nth-child(3){ animation-delay:.4s; }
        @keyframes blink{ 0%,80%,100%{opacity:.25} 40%{opacity:1} }

        /* Input */
        .input-area{ background:#fff; border-top:1px solid #E2E8F0; padding:16px 32px; }
        .input-container{ max-width:980px; margin:0 auto; }
        .input-form{ display:flex; gap:10px; margin-bottom:10px; }
        .input-field{ flex:1; padding:12px 14px; border:2px solid #E2E8F0; border-radius:12px; font-size:14px; background:#FAFAFA; transition:border-color .2s, box-shadow .2s, background .2s; }
        .input-field:focus{ outline:none; border-color:#4BA3C3; background:#fff; box-shadow:0 0 0 3px rgba(75,163,195,.1); }
        .send-btn{ padding:12px 20px; background:linear-gradient(135deg,#2B4C7E,#4BA3C3); color:#fff; border:none; border-radius:12px; font-size:14px; font-weight:600; cursor:pointer; }
        .send-btn:disabled{ opacity:.55; cursor:not-allowed; }

        /* Upload */
        .divider{ text-align:center; margin:12px 0; position:relative; }
        .divider::before,.divider::after{ content:''; position:absolute; top:50%; width:calc(50% - 30px); height:1px; background:#E2E8F0; }
        .divider::before{ left:0; } .divider::after{ right:0; }
        .divider-text{ font-size:11px; color:#94A3B8; background:#fff; padding:0 12px; position:relative; }
        .file-upload-zone{ border:2px dashed #CBD5E1; border-radius:12px; padding:20px; text-align:center; background:#FAFAFA; transition:all .2s; cursor:pointer; }
        .file-upload-zone:hover{ border-color:#4BA3C3; background:#F0F8FA; }
        .file-upload-zone.dragover{ border-color:#4BA3C3; background:#E6F4F7; transform:scale(1.01); }
        .file-upload-zone input[type="file"]{ display:none; }
        .upload-icon{ display:inline-block; width:44px; height:44px; background:linear-gradient(135deg,#E2E8F0,#CBD5E1); border-radius:12px; margin-bottom:10px; position:relative; }
        .upload-icon::after{ content:'↑'; position:absolute; inset:0; display:grid; place-items:center; font-size:22px; color:#64748B; }
        .upload-text{ font-size:14px; color:#475569; margin-bottom:2px; }
        .upload-subtext{ font-size:12px; color:#94A3B8; }
        .file-selected{ background:#F0FDF4; border-color:#86EFAC; }
        .file-selected .upload-icon{ background:linear-gradient(135deg,#86EFAC,#22C55E); }
        .file-selected .upload-icon::after{ content:'✓'; color:#fff; }

        /* Footer */
        .footer-bar{ background:#fff; border-top:1px solid #E2E8F0; padding:10px 32px; display:flex; align-items:center; justify-content:space-between; font-size:11px; color:#94A3B8; }
        .footer-links{ display:flex; gap:16px; }
        .footer-links a{ color:#64748B; text-decoration:none; }
        .charity-note{ color:#92400E; background:#FEF3C7; padding:4px 8px; border-radius:6px; }

        @media (max-width: 900px){
            .features-accordion{ grid-template-columns:1fr; }
        }
        @media (max-width: 768px){
            .header{ padding:10px 20px; }
            .status-badge{ display:none; }
            .messages-wrapper{ padding:16px 20px; }
            .message{ max-width:88%; }
            .input-area{ padding:14px 20px; }
            .input-form{ flex-direction:column; }
            .footer-bar{ flex-direction:column; gap:8px; text-align:center; padding:10px 20px; }
            .welcome-title{ font-size:24px; }
            .welcome-subtitle{ font-size:14px; }
        }
        @media (prefers-reduced-motion: reduce){ *{ animation:none !important; transition:none !important; } }
    </style>
</head>
<body>
    <div class="container">
        <!-- Sticky Header -->
        <div class="header">
            <div class="header-left">
                <div class="logo-badge">✨</div>
                <div class="header-title">
                    <h1>EspoCRM AI Copilot</h1>
                    <p class="header-subtitle">by <a href="https://fluencydigital.io" target="_blank">Fluency Digital</a></p>
                </div>
            </div>
            <div class="header-right">
                <span class="status-badge status-secure">→ Secured</span>
                <span class="status-badge status-session">→ Extended Session</span>
                <a href="{{ request.script_root }}/logout" class="logout-btn">Sign Out</a>
            </div>
        </div>

        <!-- Mission -->
        <div class="mission-banner">
            <p class="mission-text"><strong>→ Open Source AI for EspoCRM:</strong> Natural language, contact ops, resume parsing</p>
        </div>

        <!-- Chat -->
        <div class="chat-container">
            <div class="messages-wrapper" id="messagesWrapper">
                {% if history %}
                    {% for msg in history %}
                        <div class="message message-{{ msg.role }}{% if msg.role == 'assistant' and msg.content.startswith('❌') %} message-error{% elif msg.role == 'assistant' and msg.content.startswith('✅') %} message-success{% endif %}">
                            <div class="message-label">{% if msg.role == 'user' %}You{% else %}AI Assistant{% endif %}</div>
                            <div class="message-bubble">
                                {{ msg.content | replace('**','<strong>') | replace('**','</strong>') | safe }}
                            </div>
                        </div>
                    {% endfor %}
                {% else %}
                    <div class="welcome-state">
                        <div class="welcome-hero">
                            <h2 class="welcome-title">→ Welcome to Your AI Assistant</h2>
                            <p class="welcome-subtitle">Work faster in EspoCRM with natural language</p>

                            <div class="quick-commands" id="quickCommands">
                                <button data-fill="search for John">search for John</button>
                                <button data-fill="create contact Jane Doe">create contact Jane Doe</button>
                                <button data-fill="link John to Acme Corp">link John to Acme Corp</button>
                                <button data-fill="add note: called, left voicemail">add note: called, left voicemail</button>
                                <button data-fill="show contacts from Chicago">show contacts from Chicago</button>
                            </div>
                        </div>

                        <div class="instructions-section" id="instructionsSection">
                            <div class="instructions-head">
                                <div class="instructions-label">→ Feature Guide</div>
                                <div class="instructions-actions">
                                    <button id="compactToggle">Compact</button>
                                    <button id="expandAll">Expand all</button>
                                    <button id="collapseAll">Collapse all</button>
                                </div>
                            </div>

                            <div class="features-accordion" id="featuresAccordion">
                                <div class="accordion-item">
                                    <div class="accordion-header" onclick="toggleAccordion(this)">
                                        <div class="accordion-title"><span class="accordion-icon"></span>Smart Contact Search</div>
                                        <div class="accordion-arrow"></div>
                                    </div>
                                    <div class="accordion-content">
                                        <div class="accordion-body">
                                            Find people by name, email, or parts of either. Try <code>search for John Smith</code> or <code>find john@acme.com</code>.
                                        </div>
                                    </div>
                                </div>

                                <div class="accordion-item">
                                    <div class="accordion-header" onclick="toggleAccordion(this)">
                                        <div class="accordion-title"><span class="accordion-icon"></span>Quick Updates</div>
                                        <div class="accordion-arrow"></div>
                                    </div>
                                    <div class="accordion-content">
                                        <div class="accordion-body">
                                            After a search, set fields fast: <code>phone 555-1234</code>, <code>email jane@acme.com</code>, <code>title Sr. Developer</code>.
                                        </div>
                                    </div>
                                </div>

                                <div class="accordion-item">
                                    <div class="accordion-header" onclick="toggleAccordion(this)">
                                        <div class="accordion-title"><span class="accordion-icon"></span>Resume Parser</div>
                                        <div class="accordion-arrow"></div>
                                    </div>
                                    <div class="accordion-content">
                                        <div class="accordion-body">
                                            Drop in PDF/DOC/TXT resumes. The AI extracts info and creates/updates the contact automatically.
                                        </div>
                                    </div>
                                </div>

                                <div class="accordion-item">
                                    <div class="accordion-header" onclick="toggleAccordion(this)">
                                        <div class="accordion-title"><span class="accordion-icon"></span>Natural Language Filters</div>
                                        <div class="accordion-arrow"></div>
                                    </div>
                                    <div class="accordion-content">
                                        <div class="accordion-body">
                                            Ask it plainly: <code>show contacts from Chicago</code>, <code>who works at Acme?</code>, <code>list contacts without email</code>.
                                        </div>
                                    </div>
                                </div>

                                <div class="accordion-item">
                                    <div class="accordion-header" onclick="toggleAccordion(this)">
                                        <div class="accordion-title"><span class="accordion-icon"></span>Account Management</div>
                                        <div class="accordion-arrow"></div>
                                    </div>
                                    <div class="accordion-content">
                                        <div class="accordion-body">
                                            Create/link accounts: <code>create account Acme Corp</code>, <code>link John to Acme Corp</code>, <code>show all at Microsoft</code>.
                                        </div>
                                    </div>
                                </div>

                                <div class="accordion-item">
                                    <div class="accordion-header" onclick="toggleAccordion(this)">
                                        <div class="accordion-title"><span class="accordion-icon"></span>Notes & Activities</div>
                                        <div class="accordion-arrow"></div>
                                    </div>
                                    <div class="accordion-content">
                                        <div class="accordion-body">
                                            Log interactions: <code>add note: meeting Friday</code>, <code>show notes for Jane</code>, <code>add note to current: LM</code>.
                                        </div>
                                    </div>
                                </div>
                            </div><!-- /features-accordion -->
                        </div><!-- /instructions-section -->
                    </div><!-- /welcome-state -->
                {% endif %}
            </div><!-- /messages-wrapper -->

            <!-- Input -->
            <div class="input-area">
                <div class="input-container">
                    <div class="thinking-row" id="thinkingRow">
                        <span class="spinner-star" aria-hidden="true"></span>
                        <span>AI is thinking...</span>
                    </div>

                    <form method="post" class="input-form" id="textForm">
                        <input type="text" name="prompt" class="input-field" placeholder="Type a message... (try: 'search for John' or 'create contact')" autofocus>
                        <button type="submit" class="send-btn" id="sendBtn">Send</button>
                    </form>

                    <div class="divider"><span class="divider-text">or upload a resume</span></div>

                    <form method="post" enctype="multipart/form-data" id="fileForm">
                        <div class="file-upload-zone" id="fileUploadZone">
                            <label for="resume_file">
                                <div class="upload-icon"></div>
                                <div class="upload-text" id="uploadText">Drop a resume here or click to browse</div>
                                <div class="upload-subtext" id="uploadSubtext">PDF, DOC, DOCX, TXT files supported</div>
                            </label>
                            <input type="file" id="resume_file" name="resume_file" accept=".pdf,.doc,.docx,.txt,.rtf">
                        </div>
                    </form>
                </div>
            </div>
        </div><!-- /chat-container -->

        <!-- Footer -->
        <div class="footer-bar">
            <div class="footer-links">
                <a href="{{ request.script_root }}/">→ Refresh</a>
                <a href="{{ request.script_root }}/reset">→ Reset Session</a>
                <a href="{{ request.script_root }}/debug">→ Debug Info</a>
            </div>
            <div class="charity-note">★ Supporting Feed My Starving Children</div>
        </div>
    </div><!-- /container -->
    <script>
        // Keep a live reference to the messages wrapper
        let messagesWrapper = document.getElementById('messagesWrapper');
    
        // Escape HTML for security
        function escapeHtml(str) {
            const div = document.createElement('div');
            div.textContent = str;
            return div.innerHTML;
        }
    
        // Smooth scroll to bottom
        function scrollToBottom() {
            if (messagesWrapper) {
                messagesWrapper.scrollTop = messagesWrapper.scrollHeight;
            }
        }
    
        // Initial scroll positioning
        if (messagesWrapper) {
            const hasMessages = messagesWrapper.querySelector('.message');
            messagesWrapper.scrollTop = hasMessages ? messagesWrapper.scrollHeight : 0;
        }
    
        function toggleAccordion(header) {
            const content = header.nextElementSibling;
            const active = header.classList.contains('active');
            // Close others
            document.querySelectorAll('.accordion-header').forEach(h => {
                h.classList.remove('active');
                if (h.nextElementSibling) h.nextElementSibling.classList.remove('active');
            });
            if (!active) { 
                header.classList.add('active'); 
                content.classList.add('active'); 
            }
        }
    
        // Compact/expand controls
        const featuresAccordion = document.getElementById('featuresAccordion');
        const compactToggle = document.getElementById('compactToggle');
        const expandAllBtn = document.getElementById('expandAll');
        const collapseAllBtn = document.getElementById('collapseAll');
    
        if (compactToggle) {
            compactToggle.addEventListener('click', () => {
                featuresAccordion.classList.toggle('compact');
            });
        }
        if (expandAllBtn) {
            expandAllBtn.addEventListener('click', () => {
                document.querySelectorAll('.accordion-header').forEach(h => {
                    h.classList.add('active');
                    if (h.nextElementSibling) h.nextElementSibling.classList.add('active');
                });
            });
        }
        if (collapseAllBtn) {
            collapseAllBtn.addEventListener('click', () => {
                document.querySelectorAll('.accordion-header').forEach(h => {
                    h.classList.remove('active');
                    if (h.nextElementSibling) h.nextElementSibling.classList.remove('active');
                });
            });
        }
    
        // Quick command chips
        const quick = document.getElementById('quickCommands');
        const textForm = document.getElementById('textForm');
        const sendBtn = document.getElementById('sendBtn');
        
        if (quick && textForm) {
            quick.addEventListener('click', (e) => {
                const b = e.target.closest('button[data-fill]');
                if (!b) return;
                const input = textForm.querySelector('input[name="prompt"]');
                if (input) { 
                    input.value = b.dataset.fill; 
                    input.focus(); 
                }
            });
        }
    
        // Hide welcome state if there are messages
        function hideWelcomeState() {
            const welcomeState = document.querySelector('.welcome-state');
            if (welcomeState) {
                welcomeState.style.display = 'none';
            }
        }
    
        // Main form submission with immediate feedback
        if (textForm) {
            textForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const input = textForm.querySelector('input[name="prompt"]');
                const userMessage = input.value.trim();
                if (!userMessage) return;
    
                // Hide welcome state on first message
                hideWelcomeState();
    
                // Disable send button
                sendBtn.disabled = true;
    
                // Append user message immediately
                const userMsgHtml = `
                    <div class="message message-user">
                        <div class="message-label">You</div>
                        <div class="message-bubble">${escapeHtml(userMessage)}</div>
                    </div>
                `;
                messagesWrapper.insertAdjacentHTML('beforeend', userMsgHtml);
                scrollToBottom();
    
                // Clear input & show typing indicator
                input.value = '';
                const thinkingRow = document.getElementById('thinkingRow');
                if (thinkingRow) thinkingRow.style.display = 'flex';
                
                const typingHtml = `
                    <div class="message message-assistant typing">
                        <div class="message-label">AI Assistant</div>
                        <div class="message-bubble">
                            <span class="typing-dots">
                                <span></span><span></span><span></span>
                            </span>
                        </div>
                    </div>
                `;
                messagesWrapper.insertAdjacentHTML('beforeend', typingHtml);
                scrollToBottom();
    
                // Send fetch request
                const formData = new FormData(textForm);
                formData.set('prompt', userMessage); // Ensure the message is in formData
                
                try {
                    const res = await fetch(window.location.href, { 
                        method: 'POST', 
                        body: formData,
                        headers: { 'X-Requested-With': 'fetch' },
                        credentials: 'same-origin'
                    });
                    const html = await res.text();
                    
                    // Parse response and replace entire messages wrapper content
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(html, 'text/html');
                    const newMessagesWrapper = doc.querySelector('#messagesWrapper');
                    
                    if (newMessagesWrapper) {
                        messagesWrapper.innerHTML = newMessagesWrapper.innerHTML;
                        messagesWrapper = document.getElementById('messagesWrapper'); // Re-get reference
                        scrollToBottom();
                    } else {
                        // Fallback: reload if structure changed
                        window.location.reload();
                    }
                } catch (err) {
                    console.error('Error submitting message:', err);
                    // Remove typing indicator and show error
                    const typingMsg = messagesWrapper.querySelector('.message-assistant.typing');
                    if (typingMsg) typingMsg.remove();
                    
                    const errorHtml = `
                        <div class="message message-assistant">
                            <div class="message-label">AI Assistant</div>
                            <div class="message-bubble">❌ Sorry, an error occurred. Please try again.</div>
                        </div>
                    `;
                    messagesWrapper.insertAdjacentHTML('beforeend', errorHtml);
                    scrollToBottom();
                } finally {
                    // Re-enable send button and hide thinking row
                    sendBtn.disabled = false;
                    if (thinkingRow) thinkingRow.style.display = 'none';
                    input.focus();
                }
            });
        }
    
        // Upload handling
        const fileZone = document.getElementById('fileUploadZone');
        const fileInput = document.getElementById('resume_file');
        const uploadText = document.getElementById('uploadText');
        const uploadSubtext = document.getElementById('uploadSubtext');
        const fileForm = document.getElementById('fileForm');
    
        function preventDefaults(e) { 
            e.preventDefault(); 
            e.stopPropagation(); 
        }
    
        if (fileZone) {
            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(evt => 
                fileZone.addEventListener(evt, preventDefaults)
            );
            ['dragenter', 'dragover'].forEach(evt => 
                fileZone.addEventListener(evt, () => fileZone.classList.add('dragover'))
            );
            ['dragleave', 'drop'].forEach(evt => 
                fileZone.addEventListener(evt, () => fileZone.classList.remove('dragover'))
            );
            fileZone.addEventListener('drop', e => {
                const files = e.dataTransfer.files;
                if (files.length > 0) { 
                    fileInput.files = files; 
                    startFileUpload(); 
                }
            });
        }
    
        if (fileInput) { 
            fileInput.addEventListener('change', startFileUpload); 
        }
    
        async function startFileUpload() {
            const f = fileInput.files && fileInput.files[0];
            if (!f) return;
    
            // Hide welcome state
            hideWelcomeState();
    
            // Update UI
            fileZone.classList.add('file-selected');
            if (uploadText) uploadText.textContent = f.name;
            if (uploadSubtext) uploadSubtext.textContent = 'Parsing and creating contact...';
    
            // Add user message about file upload
            const uploadMsgHtml = `
                <div class="message message-user">
                    <div class="message-label">You</div>
                    <div class="message-bubble">📎 Uploaded: ${escapeHtml(f.name)}</div>
                </div>
            `;
            messagesWrapper.insertAdjacentHTML('beforeend', uploadMsgHtml);
            scrollToBottom();
    
            // Show thinking indicator
            const thinkingRow = document.getElementById('thinkingRow');
            if (thinkingRow) thinkingRow.style.display = 'flex';
            
            const typingHtml = `
                <div class="message message-assistant typing">
                    <div class="message-label">AI Assistant</div>
                    <div class="message-bubble">
                        <span class="typing-dots">
                            <span></span><span></span><span></span>
                        </span>
                    </div>
                </div>
            `;
            messagesWrapper.insertAdjacentHTML('beforeend', typingHtml);
            scrollToBottom();
    
            // Submit file
            const formData = new FormData(fileForm);
            try {
                const res = await fetch(window.location.href, { 
                    method: 'POST', 
                    body: formData,
                    headers: { 'X-Requested-With': 'fetch' },
                    credentials: 'same-origin'
                });
                const html = await res.text();
                
                // Parse and update messages
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, 'text/html');
                const newMessagesWrapper = doc.querySelector('#messagesWrapper');
                
                if (newMessagesWrapper) {
                    messagesWrapper.innerHTML = newMessagesWrapper.innerHTML;
                    messagesWrapper = document.getElementById('messagesWrapper'); // Re-get reference
                    scrollToBottom();
                } else {
                    window.location.reload();
                }
            } catch (err) {
                console.error('Error uploading file:', err);
                // Remove typing indicator and show error
                const typingMsg = messagesWrapper.querySelector('.message-assistant.typing');
                if (typingMsg) typingMsg.remove();
                
                const errorHtml = `
                    <div class="message message-assistant">
                        <div class="message-label">AI Assistant</div>
                        <div class="message-bubble">❌ Sorry, file upload failed. Please try again.</div>
                    </div>
                `;
                messagesWrapper.insertAdjacentHTML('beforeend', errorHtml);
                scrollToBottom();
            } finally {
                // Reset upload UI
                fileInput.value = '';
                fileZone.classList.remove('file-selected');
                if (uploadText) uploadText.textContent = 'Drop a resume here or click to browse';
                if (uploadSubtext) uploadSubtext.textContent = 'PDF, DOC, DOCX, TXT files supported';
                if (thinkingRow) thinkingRow.style.display = 'none';
            }
        }
    </script>
</body>
</html>
'''

QUICKADD_TEMPLATE = '''
<!doctype html>
<html>
<head>
    <title>✨ Quick Add Contact</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #2B4C7E 0%, #4BA3C3 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 500px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #2B4C7E, #4BA3C3);
            color: white;
            padding: 20px;
            text-align: center;
        }
        .header h1 {
            font-size: 20px;
            font-weight: 600;
        }
        .header p {
            font-size: 13px;
            opacity: 0.9;
            margin-top: 4px;
        }
        .content {
            padding: 20px;
        }
        .form-group {
            margin-bottom: 16px;
        }
        label {
            display: block;
            font-size: 12px;
            font-weight: 600;
            color: #64748B;
            margin-bottom: 6px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        textarea, input[type="text"], input[type="email"], input[type="tel"] {
            width: 100%;
            padding: 12px;
            border: 2px solid #E2E8F0;
            border-radius: 8px;
            font-size: 14px;
            transition: border-color 0.2s;
        }
        textarea:focus, input:focus {
            outline: none;
            border-color: #4BA3C3;
        }
        textarea {
            min-height: 100px;
            resize: vertical;
        }
        .type-toggle {
            display: flex;
            gap: 10px;
            margin-bottom: 16px;
        }
        .type-btn {
            flex: 1;
            padding: 12px;
            border: 2px solid #E2E8F0;
            border-radius: 8px;
            background: white;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.2s;
        }
        .type-btn:hover {
            border-color: #4BA3C3;
        }
        .type-btn.active {
            border-color: #4BA3C3;
            background: #E6F4F7;
            color: #2B4C7E;
        }
        .type-btn.candidate.active {
            border-color: #22C55E;
            background: #DCFCE7;
            color: #166534;
        }
        .type-btn.client.active {
            border-color: #3B82F6;
            background: #DBEAFE;
            color: #1E40AF;
        }
        .btn {
            width: 100%;
            padding: 14px;
            border: none;
            border-radius: 8px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }
        .btn-primary {
            background: linear-gradient(135deg, #2B4C7E, #4BA3C3);
            color: white;
        }
        .btn-primary:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(43, 76, 126, 0.3);
        }
        .btn-success {
            background: linear-gradient(135deg, #22C55E, #16A34A);
            color: white;
        }
        .parsed-fields {
            background: #F8FAFC;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 16px;
        }
        .parsed-fields .form-group {
            margin-bottom: 12px;
        }
        .parsed-fields .form-group:last-child {
            margin-bottom: 0;
        }
        .parsed-fields input {
            padding: 10px;
            font-size: 13px;
        }
        .field-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }
        .result-box {
            padding: 16px;
            border-radius: 8px;
            margin-bottom: 16px;
            text-align: center;
        }
        .result-success {
            background: #DCFCE7;
            color: #166534;
        }
        .result-error {
            background: #FEE2E2;
            color: #DC2626;
        }
        .result-box p {
            font-size: 15px;
            font-weight: 500;
        }
        .close-btn {
            display: block;
            text-align: center;
            padding: 12px;
            color: #64748B;
            text-decoration: none;
            font-size: 13px;
        }
        .close-btn:hover {
            color: #1E1E1E;
        }
        .loading {
            opacity: 0.6;
            pointer-events: none;
        }
        .spinner {
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 2px solid transparent;
            border-top-color: currentColor;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin-right: 8px;
            vertical-align: middle;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .optional-section {
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            margin-bottom: 12px;
            overflow: hidden;
        }
        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 16px;
            background: #F8FAFC;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            color: #475569;
        }
        .section-header:hover {
            background: #F1F5F9;
        }
        .toggle-icon {
            font-size: 18px;
            font-weight: bold;
            color: #94A3B8;
        }
        .section-content {
            padding: 16px;
            border-top: 1px solid #E2E8F0;
        }
        .section-content .form-group {
            margin-bottom: 12px;
        }
        .section-content .form-group:last-child {
            margin-bottom: 0;
        }
        select {
            width: 100%;
            padding: 10px 12px;
            border: 2px solid #E2E8F0;
            border-radius: 8px;
            font-size: 14px;
            background: white;
            cursor: pointer;
        }
        select:focus {
            outline: none;
            border-color: #4BA3C3;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>✨ Quick Add Contact</h1>
            <p>Paste or review contact info, then add to CRM</p>
        </div>

        <div class="content">
            {% if result %}
                <div class="result-box result-success">
                    <p>{{ result.message }}</p>
                </div>

                <!-- Add Task Section -->
                <div class="optional-section" style="margin-bottom: 12px;">
                    <div class="section-header" onclick="toggleSection('successTaskSection')" style="background: #FEF3C7; border-color: #F59E0B;">
                        <span>✅ Add Task</span>
                        <span class="toggle-icon" id="successTaskToggle">+</span>
                    </div>
                    <div class="section-content" id="successTaskSection" style="display: none;">
                        <div id="taskForm">
                            <div class="form-group">
                                <label>Task</label>
                                <input type="text" id="successTaskName" placeholder="e.g., Follow up, Schedule interview...">
                            </div>
                            <div class="field-row">
                                <div class="form-group">
                                    <label>Due Date</label>
                                    <input type="date" id="successTaskDueDate">
                                </div>
                                <div class="form-group">
                                    <label>Assign To</label>
                                    <select id="successTaskAssignTo">
                                        <option value="Stephen">Stephen</option>
                                        <option value="Aaron">Aaron</option>
                                        <option value="Steve">Steve</option>
                                    </select>
                                </div>
                            </div>
                            <button type="button" class="btn btn-primary" onclick="createTask()" id="createTaskBtn" style="background: linear-gradient(135deg, #F59E0B, #D97706);">
                                ✅ Create Task
                            </button>
                        </div>
                        <div id="taskSuccess" style="display: none; color: #166534; font-weight: 500; padding: 10px; background: #DCFCE7; border-radius: 8px; text-align: center;">
                            ✅ Task created!
                        </div>
                    </div>
                </div>

                {% if result.email_address %}
                <a href="{{ request.script_root }}/quickemail?contact_id={{ result.contact_id }}&firstName={{ result.first_name|urlencode }}&lastName={{ result.last_name|urlencode }}&email={{ result.email_address|urlencode }}&title={{ result.title|urlencode }}&company={{ result.company|urlencode }}&skills={{ result.skills|urlencode }}&type={{ result.contact_type }}"
                   class="btn btn-success" style="margin-bottom: 10px;"
                   onclick="window.open(this.href, 'quickemail', 'popup=yes,width=650,height=700'); return false;">
                    📧 Quick Email
                </a>
                {% endif %}
                <a href="{{ request.script_root }}/quickadd" class="btn btn-primary">+ Add Another</a>
                <a href="javascript:window.close()" class="close-btn">Close Window</a>

                <script>
                function createTask() {
                    var taskName = document.getElementById('successTaskName').value.trim();
                    if (!taskName) {
                        alert('Please enter a task name');
                        return;
                    }
                    var btn = document.getElementById('createTaskBtn');
                    btn.innerHTML = 'Creating...';
                    btn.disabled = true;

                    fetch('{{ request.script_root }}/quickadd/task', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            taskName: taskName,
                            taskDueDate: document.getElementById('successTaskDueDate').value,
                            taskAssignTo: document.getElementById('successTaskAssignTo').value,
                            contactName: '{{ result.first_name }} {{ result.last_name }}'
                        })
                    })
                    .then(function(r) { return r.json(); })
                    .then(function(data) {
                        if (data.success) {
                            document.getElementById('taskForm').style.display = 'none';
                            document.getElementById('taskSuccess').style.display = 'block';
                            document.getElementById('taskSuccess').textContent = '✅ ' + data.message;
                        } else {
                            alert('Failed: ' + (data.error || 'Unknown error'));
                            btn.innerHTML = '✅ Create Task';
                            btn.disabled = false;
                        }
                    })
                    .catch(function(e) {
                        alert('Error: ' + e);
                        btn.innerHTML = '✅ Create Task';
                        btn.disabled = false;
                    });
                }
                </script>

            {% elif parsed_data %}
                <!-- Show parsed fields for editing -->
                <form method="POST" id="createForm">
                    <input type="hidden" name="action" value="create">
                    <input type="hidden" name="contact_type" id="contact_type" value="{{ parsed_data._contact_type or 'candidate' }}">

                    <div class="type-toggle">
                        <button type="button" class="type-btn candidate {% if parsed_data._contact_type != 'client' %}active{% endif %}" onclick="setType('candidate')">
                            👤 Candidate
                        </button>
                        <button type="button" class="type-btn client {% if parsed_data._contact_type == 'client' %}active{% endif %}" onclick="setType('client')">
                            🏢 Client
                        </button>
                    </div>

                    <div class="parsed-fields">
                        <div class="field-row">
                            <div class="form-group">
                                <label>First Name *</label>
                                <input type="text" name="firstName" value="{{ parsed_data.firstName or '' }}" required>
                            </div>
                            <div class="form-group">
                                <label>Last Name *</label>
                                <input type="text" name="lastName" value="{{ parsed_data.lastName or '' }}" required>
                            </div>
                        </div>

                        <div class="form-group">
                            <label>Email</label>
                            <input type="email" name="emailAddress" value="{{ parsed_data.emailAddress or '' }}">
                        </div>

                        <div class="form-group">
                            <label>Phone</label>
                            <input type="tel" name="phoneNumber" value="{{ parsed_data.phoneNumber or '' }}">
                        </div>

                        <div class="field-row">
                            <div class="form-group">
                                <label>Title</label>
                                <input type="text" name="cCurrentTitle" value="{{ parsed_data.cCurrentTitle or '' }}">
                            </div>
                            <div class="form-group">
                                <label>Company</label>
                                <input type="text" name="cCurrentCompany" value="{{ parsed_data.cCurrentCompany or '' }}">
                            </div>
                        </div>

                        <div class="form-group">
                            <label>LinkedIn URL</label>
                            <input type="text" name="cLinkedInURL" value="{{ parsed_data.cLinkedInURL or '' }}">
                        </div>

                        <div class="form-group">
                            <label>Skills</label>
                            <input type="text" name="cSkills" value="{{ parsed_data.cSkills or '' }}" placeholder="Comma-separated">
                        </div>

                        <div class="field-row">
                            <div class="form-group">
                                <label>City</label>
                                <input type="text" name="addressCity" value="{{ parsed_data.addressCity or '' }}">
                            </div>
                            <div class="form-group">
                                <label>State</label>
                                <input type="text" name="addressState" value="{{ parsed_data.addressState or '' }}">
                            </div>
                        </div>

                        {% if parsed_data.additionalEmails or parsed_data.additionalPhones %}
                        <div style="background: #FEF3C7; border: 1px solid #F59E0B; border-radius: 8px; padding: 12px; margin-top: 12px;">
                            <div style="font-size: 12px; font-weight: 600; color: #92400E; margin-bottom: 8px;">📱 Additional Contact Info (will be added as note)</div>
                            {% if parsed_data.additionalEmails %}
                            <div style="font-size: 13px; color: #78350F; margin-bottom: 4px;">
                                <strong>Extra emails:</strong> {{ parsed_data.additionalEmails | join(', ') }}
                            </div>
                            {% endif %}
                            {% if parsed_data.additionalPhones %}
                            <div style="font-size: 13px; color: #78350F;">
                                <strong>Extra phones:</strong> {{ parsed_data.additionalPhones | join(', ') }}
                            </div>
                            {% endif %}
                        </div>
                        <input type="hidden" name="additionalEmails" value="{{ parsed_data.additionalEmails | join(', ') if parsed_data.additionalEmails else '' }}">
                        <input type="hidden" name="additionalPhones" value="{{ parsed_data.additionalPhones | join(', ') if parsed_data.additionalPhones else '' }}">
                        {% endif %}
                    </div>

                    <!-- Optional Note Section -->
                    <div class="optional-section">
                        <div class="section-header" onclick="toggleSection('noteSection')">
                            <span>📝 Add Note</span>
                            <span class="toggle-icon" id="noteToggle">+</span>
                        </div>
                        <div class="section-content" id="noteSection" style="display: none;">
                            <div class="form-group">
                                <textarea name="note" placeholder="Add a note about this contact..." rows="3"></textarea>
                            </div>
                        </div>
                    </div>

                    <!-- Optional Task Section -->
                    <div class="optional-section">
                        <div class="section-header" onclick="toggleSection('taskSection')">
                            <span>✅ Add Task</span>
                            <span class="toggle-icon" id="taskToggle">+</span>
                        </div>
                        <div class="section-content" id="taskSection" style="display: none;">
                            <div class="form-group">
                                <label>Task</label>
                                <input type="text" name="taskName" placeholder="e.g., Follow up, Schedule interview...">
                            </div>
                            <div class="field-row">
                                <div class="form-group">
                                    <label>Due Date</label>
                                    <input type="date" name="taskDueDate">
                                </div>
                                <div class="form-group">
                                    <label>Assign To</label>
                                    <select name="taskAssignTo">
                                        <option value="Stephen">Stephen</option>
                                        <option value="Aaron">Aaron</option>
                                        <option value="Steve">Steve</option>
                                    </select>
                                </div>
                            </div>
                        </div>
                    </div>

                    <button type="submit" class="btn btn-success" id="submitBtn">
                        ✓ Add to CRM
                    </button>
                </form>

                <a href="{{ request.script_root }}/quickadd" class="close-btn">← Start Over</a>

            {% else %}
                <!-- Initial form to paste text -->
                {% if error %}
                    <div class="result-box result-error">
                        <p>{{ error }}</p>
                    </div>
                {% endif %}

                <form method="POST" id="parseForm">
                    <input type="hidden" name="action" value="parse">
                    <input type="hidden" name="contact_type" id="contact_type" value="candidate">

                    <div class="type-toggle">
                        <button type="button" class="type-btn candidate active" onclick="setType('candidate')">
                            👤 Candidate
                        </button>
                        <button type="button" class="type-btn client" onclick="setType('client')">
                            🏢 Client
                        </button>
                    </div>

                    <div class="form-group">
                        <label>Paste Contact Info</label>
                        <textarea name="text" id="textInput" placeholder="Paste any text containing contact information...&#10;&#10;Examples:&#10;• LinkedIn profile text&#10;• Email signature&#10;• Business card info&#10;• Any text with name, email, phone, etc.">{{ initial_text }}</textarea>
                        <button type="button" id="pasteBtn" onclick="pasteFromClipboard()" style="margin-top: 8px; padding: 8px 16px; background: #6366F1; color: white; border: none; border-radius: 6px; font-size: 13px; font-weight: 500; cursor: pointer;">
                            📋 Paste from Clipboard
                        </button>
                    </div>

                    <button type="submit" class="btn btn-primary" id="submitBtn">
                        ✨ Parse with AI
                    </button>
                </form>

                <a href="javascript:window.close()" class="close-btn">Cancel</a>

                <!-- Tools Section -->
                <div class="optional-section" style="margin-top: 20px;">
                    <div class="section-header" onclick="toggleSection('toolsSection')">
                        <span>🔧 Tools</span>
                        <span class="toggle-icon" id="toolsToggle">+</span>
                    </div>
                    <div class="section-content" id="toolsSection" style="display: none;">
                        <div style="margin-bottom: 16px;">
                            <label style="margin-bottom: 8px;">Bookmarklet</label>
                            <p style="font-size: 12px; color: #64748B; margin-bottom: 8px;">Drag this to your bookmarks bar:</p>
                            <a href="javascript:(function(){var t=window.getSelection().toString()||'';if(!t){var a=document.activeElement;if(a&amp;&amp;(a.value||a.textContent)){t=(a.selectionStart!==undefined?a.value.substring(a.selectionStart,a.selectionEnd):'')||'';}}var u='https://crm.fluencydigital.io/copilot/quickadd?token={{ auth_token }}';if(t)u+='&amp;text='+encodeURIComponent(t);window.open(u,'quickadd','width=550,height=700,scrollbars=yes,resizable=yes');})();"
                               style="display: inline-block; padding: 10px 20px; background: linear-gradient(135deg, #22C55E, #16A34A); color: white; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 13px; cursor: grab;">
                                ⚡ Quick Add
                            </a>
                            <p style="font-size: 11px; color: #94A3B8; margin-top: 8px;">
                                💡 Tip: If highlight doesn't work, copy text first (Ctrl+C). Chrome Extension is more reliable.
                            </p>
                        </div>
                        <div style="margin-bottom: 16px;">
                            <label style="margin-bottom: 8px;">Chrome Extension</label>
                            <p style="font-size: 12px; color: #64748B; margin-bottom: 8px;">Right-click menu + keyboard shortcut (Ctrl+Shift+Q)</p>
                            <a href="{{ request.script_root }}/quickadd/extension"
                               style="display: inline-block; padding: 10px 20px; background: linear-gradient(135deg, #3B82F6, #1D4ED8); color: white; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 13px;">
                                📦 Download Extension
                            </a>
                            <p style="font-size: 11px; color: #94A3B8; margin-top: 8px;">
                                Install: chrome://extensions → Developer mode → Load unpacked
                            </p>
                        </div>
                        <div style="margin-bottom: 16px;">
                            <label style="margin-bottom: 8px;">Email Templates</label>
                            <p style="font-size: 12px; color: #64748B; margin-bottom: 8px;">View and delete saved email templates</p>
                            <a href="{{ request.script_root }}/quickemail/templates/manage"
                               onclick="window.open(this.href, 'templates', 'popup=yes,width=550,height=600'); return false;"
                               style="display: inline-block; padding: 10px 20px; background: linear-gradient(135deg, #7C3AED, #A78BFA); color: white; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 13px;">
                                📝 Manage Templates
                            </a>
                        </div>
                    </div>
                </div>
            {% endif %}
        </div>
    </div>

    <script>
        // Paste from clipboard button
        async function pasteFromClipboard() {
            const textarea = document.getElementById('textInput');
            const btn = document.getElementById('pasteBtn');
            try {
                const text = await navigator.clipboard.readText();
                if (text) {
                    textarea.value = text;
                    textarea.focus();
                    btn.textContent = '✓ Pasted!';
                    btn.style.background = '#22C55E';
                    setTimeout(() => {
                        btn.innerHTML = '📋 Paste from Clipboard';
                        btn.style.background = '#6366F1';
                    }, 2000);
                } else {
                    btn.textContent = 'Clipboard empty';
                    setTimeout(() => {
                        btn.innerHTML = '📋 Paste from Clipboard';
                    }, 2000);
                }
            } catch (err) {
                // Clipboard access denied - show manual paste hint
                btn.textContent = 'Use Ctrl+V';
                textarea.focus();
                setTimeout(() => {
                    btn.innerHTML = '📋 Paste from Clipboard';
                }, 2000);
            }
        }

        function setType(type) {
            document.getElementById('contact_type').value = type;
            document.querySelectorAll('.type-btn').forEach(btn => {
                btn.classList.remove('active');
                if (btn.classList.contains(type)) {
                    btn.classList.add('active');
                }
            });
        }

        function toggleSection(sectionId) {
            const section = document.getElementById(sectionId);
            const toggleId = sectionId.replace('Section', 'Toggle');
            const toggle = document.getElementById(toggleId);

            if (section.style.display === 'none') {
                section.style.display = 'block';
                if (toggle) toggle.textContent = '−';
            } else {
                section.style.display = 'none';
                if (toggle) toggle.textContent = '+';
            }
        }

        // Add loading state on form submit
        document.querySelectorAll('form').forEach(form => {
            form.addEventListener('submit', function() {
                const btn = this.querySelector('#submitBtn');
                if (btn) {
                    btn.innerHTML = '<span class="spinner"></span> Processing...';
                    btn.disabled = true;
                }
            });
        });

        // Auto-focus textarea if empty
        const textarea = document.querySelector('textarea');
        if (textarea && !textarea.value) {
            textarea.focus();
        }
    </script>
</body>
</html>
'''

QUICKEMAIL_TEMPLATE = '''
<!doctype html>
<html>
<head>
    <title>📧 Quick Email</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <script>
        function setType(type) {
            document.getElementById('contact_type').value = type;
            document.querySelectorAll('.type-btn').forEach(function(btn) {
                btn.classList.remove('active');
                if (btn.classList.contains(type)) {
                    btn.classList.add('active');
                }
            });
        }

        function applyTemplate() {
            var select = document.getElementById('templateSelect');
            if (!select) return;
            var option = select.options[select.selectedIndex];

            // Update hidden field with selected template ID
            var hiddenField = document.getElementById('selected_template_id');
            if (hiddenField) {
                hiddenField.value = option && option.value ? option.value : '';
            }

            if (!option || !option.value) return;

            var type = option.dataset.type;
            var subject = option.dataset.subject || '';
            var body = option.dataset.body || '';
            var prompt = option.dataset.prompt || '';

            if (type === 'full') {
                var contextField = document.querySelector('textarea[name="custom_context"]');
                if (contextField) {
                    contextField.value = 'USE THIS EXACT TEMPLATE:\\n\\nSubject: ' + subject + '\\n\\nBody:\\n' + body;
                }
                alert('Template loaded into context. Click Generate to use it.');
            } else if (type === 'prompt') {
                var contextField = document.querySelector('textarea[name="custom_context"]');
                if (contextField) {
                    contextField.value = prompt;
                }
            }
        }

        function showSaveTemplateModal() {
            var modal = document.getElementById('saveTemplateModal');
            if (modal) {
                modal.style.display = 'flex';
            } else {
                alert('Error: Modal not found');
            }
        }

        function hideSaveTemplateModal() {
            var modal = document.getElementById('saveTemplateModal');
            if (modal) modal.style.display = 'none';
        }

        function updateTemplate() {
            var templateId = '{{ selected_template_id }}';
            if (!templateId) {
                alert('No template selected to update');
                return;
            }

            var subjectEl = document.querySelector('input[name="subject"]');
            var bodyEl = document.querySelector('textarea[name="body"]');

            if (!subjectEl || !bodyEl) {
                alert('Error: Subject or body field not found');
                return;
            }

            // Show update modal
            showUpdateTemplateModal(templateId, subjectEl.value, bodyEl.value);
        }

        var currentUpdateTemplateId = null;
        var currentUpdateSubject = '';
        var currentUpdateBody = '';

        // Embed templates data to avoid API call issues
        var allTemplates = [
            {% for tmpl in email_templates %}
            { id: "{{ tmpl.id }}", name: "{{ tmpl.name|e }}", type: "{{ tmpl.type }}", contact_type: "{{ tmpl.contact_type }}" }{% if not loop.last %},{% endif %}
            {% endfor %}
        ];

        function showUpdateTemplateModal(templateId, subject, body) {
            currentUpdateTemplateId = templateId;
            currentUpdateSubject = subject;
            currentUpdateBody = body;

            var tmpl = allTemplates.find(function(t) { return t.id === templateId; });
            if (!tmpl) {
                alert('Template not found');
                return;
            }

            document.getElementById('updateTemplateName').value = tmpl.name || '';
            document.getElementById('updateTemplateType').value = tmpl.type || 'full';
            document.getElementById('updateTemplateContactType').value = tmpl.contact_type || 'any';
            document.getElementById('updateTemplateModal').style.display = 'flex';
        }

        function hideUpdateTemplateModal() {
            document.getElementById('updateTemplateModal').style.display = 'none';
        }

        function saveUpdateTemplate() {
            var name = document.getElementById('updateTemplateName').value.trim();
            var type = document.getElementById('updateTemplateType').value;
            var contactType = document.getElementById('updateTemplateContactType').value;

            if (!name) {
                alert('Please enter a template name');
                return;
            }

            var data = {
                id: currentUpdateTemplateId,
                name: name,
                type: type,
                contact_type: contactType,
                subject: type === 'full' ? currentUpdateSubject : '',
                body: type === 'full' ? currentUpdateBody : '',
                prompt: type === 'prompt' ? currentUpdateBody : ''
            };

            fetch('{{ request.script_root }}/quickemail/templates?token={{ auth_token }}', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify(data)
            })
            .then(function(r) {
                if (!r.ok) throw new Error('HTTP ' + r.status);
                return r.json();
            })
            .then(function(result) {
                if (result.id) {
                    alert('Template updated!');
                    hideUpdateTemplateModal();
                } else {
                    alert('Failed to update: ' + (result.error || 'Unknown error'));
                }
            })
            .catch(function(e) {
                alert('Error: ' + e);
            });
        }

        function saveTemplate() {
            var nameInput = document.getElementById('templateName');
            if (!nameInput) {
                alert('Error: Template name input not found');
                return;
            }
            var name = nameInput.value.trim();
            if (!name) {
                alert('Please enter a template name');
                return;
            }

            var typeEl = document.getElementById('templateType');
            var contactTypeEl = document.getElementById('templateContactType');
            var subjectEl = document.querySelector('input[name="subject"]');
            var bodyEl = document.querySelector('textarea[name="body"]');

            if (!subjectEl || !bodyEl) {
                alert('Error: Subject or body field not found');
                return;
            }

            var type = typeEl ? typeEl.value : 'full';
            var contactType = contactTypeEl ? contactTypeEl.value : 'any';
            var subject = subjectEl.value;
            var body = bodyEl.value;

            var data = {
                name: name,
                type: type,
                contact_type: contactType,
                subject: subject,
                body: body,
                prompt: type === 'prompt' ? body : ''
            };

            fetch('{{ request.script_root }}/quickemail/templates', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify(data)
            })
            .then(function(r) {
                if (!r.ok) {
                    throw new Error('Server returned ' + r.status);
                }
                return r.json();
            })
            .then(function(result) {
                if (result.id) {
                    alert('Template saved: ' + name);
                    hideSaveTemplateModal();
                } else {
                    alert('Error: ' + (result.error || 'Unknown error'));
                }
            })
            .catch(function(err) {
                alert('Error saving template: ' + err);
            });
        }
    </script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #2B4C7E 0%, #4BA3C3 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #4BA3C3, #2B4C7E);
            color: white;
            padding: 20px;
            text-align: center;
        }
        .header h1 { font-size: 20px; font-weight: 600; }
        .header p { font-size: 13px; opacity: 0.9; margin-top: 4px; }
        .content { padding: 20px; }
        .form-group { margin-bottom: 16px; }
        label {
            display: block;
            font-size: 12px;
            font-weight: 600;
            color: #64748B;
            margin-bottom: 6px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        input[type="text"], input[type="email"], textarea {
            width: 100%;
            padding: 12px;
            border: 2px solid #E2E8F0;
            border-radius: 8px;
            font-size: 14px;
            transition: border-color 0.2s;
        }
        input:focus, textarea:focus {
            outline: none;
            border-color: #4BA3C3;
        }
        textarea { min-height: 150px; resize: vertical; font-family: inherit; }
        .btn {
            width: 100%;
            padding: 14px;
            border: none;
            border-radius: 8px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            margin-bottom: 10px;
        }
        .btn-primary {
            background: linear-gradient(135deg, #2B4C7E, #4BA3C3);
            color: white;
        }
        .btn-primary:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(43, 76, 126, 0.3);
        }
        .btn-success {
            background: linear-gradient(135deg, #22C55E, #16A34A);
            color: white;
        }
        .btn-success:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(34, 197, 94, 0.3);
        }
        .btn-outline {
            background: white;
            border: 2px solid #E2E8F0;
            color: #475569;
        }
        .btn-outline:hover {
            border-color: #4BA3C3;
            color: #2B4C7E;
        }
        .contact-info {
            background: #F8FAFC;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 16px;
        }
        .contact-info h3 {
            font-size: 14px;
            font-weight: 600;
            color: #1E293B;
            margin-bottom: 8px;
        }
        .contact-info p {
            font-size: 13px;
            color: #64748B;
            margin: 4px 0;
        }
        .contact-info strong { color: #334155; }
        .type-toggle {
            display: flex;
            gap: 10px;
            margin-bottom: 16px;
        }
        .type-btn {
            flex: 1;
            padding: 10px;
            border: 2px solid #E2E8F0;
            border-radius: 8px;
            background: white;
            cursor: pointer;
            font-size: 13px;
            font-weight: 500;
            transition: all 0.2s;
        }
        .type-btn:hover { border-color: #4BA3C3; }
        .type-btn.active {
            border-color: #4BA3C3;
            background: #E6F4F7;
            color: #2B4C7E;
        }
        .type-btn.candidate.active {
            border-color: #22C55E;
            background: #DCFCE7;
            color: #166534;
        }
        .type-btn.client.active {
            border-color: #3B82F6;
            background: #DBEAFE;
            color: #1E40AF;
        }
        .result-box {
            padding: 16px;
            border-radius: 8px;
            margin-bottom: 16px;
            text-align: center;
        }
        .result-success {
            background: #DCFCE7;
            color: #166534;
        }
        .result-error {
            background: #FEE2E2;
            color: #DC2626;
        }
        .result-box p { font-size: 15px; font-weight: 500; }
        .close-btn {
            display: block;
            text-align: center;
            padding: 12px;
            color: #64748B;
            text-decoration: none;
            font-size: 13px;
        }
        .close-btn:hover { color: #1E1E1E; }
        .loading { opacity: 0.6; pointer-events: none; }
        .spinner {
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 2px solid transparent;
            border-top-color: currentColor;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin-right: 8px;
            vertical-align: middle;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .preview-box {
            background: #FFFBEB;
            border: 2px solid #FCD34D;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 16px;
        }
        .preview-box h4 {
            font-size: 13px;
            color: #92400E;
            margin-bottom: 8px;
        }
        .preview-subject {
            font-weight: 600;
            color: #1E293B;
            margin-bottom: 8px;
            font-size: 14px;
        }
        .preview-body {
            color: #475569;
            font-size: 13px;
            line-height: 1.6;
            white-space: pre-wrap;
        }
        .hidden { display: none !important; }
        .field-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }
        .help-text {
            font-size: 11px;
            color: #94A3B8;
            margin-top: 4px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📧 Quick Email</h1>
            <p>AI-powered outreach email composer</p>
        </div>

        <div class="content">
            {% if result %}
                <div class="result-box result-success">
                    <p>✅ {{ result.message }}</p>
                </div>
                <a href="javascript:window.close()" class="btn btn-primary">Close Window</a>
                <a href="{{ request.script_root }}/quickadd" class="close-btn">← Add Another Contact</a>

            {% elif generated_email %}
                <!-- Show generated email for review/edit before sending -->
                <div class="preview-box">
                    <h4>✨ AI Generated Email - Review & Edit</h4>
                </div>

                {% if error %}
                    <div class="result-box result-error">
                        <p>{{ error }}</p>
                    </div>
                {% endif %}

                <form method="POST" id="sendForm">
                    <input type="hidden" name="action" value="send">
                    <input type="hidden" name="contact_id" value="{{ contact_id }}">
                    <input type="hidden" name="to_email" value="{{ email_address }}">

                    <div class="contact-info">
                        <h3>📤 Sending to:</h3>
                        <p><strong>{{ first_name }} {{ last_name }}</strong></p>
                        <p>{{ email_address }}</p>
                    </div>

                    <div class="form-group">
                        <label>Send As</label>
                        <select name="send_as" style="width: 100%; padding: 10px 12px; border: 2px solid #E2E8F0; border-radius: 8px; font-size: 14px;">
                            <option value="staylor@fluencydigital.io">Stephen Taylor (staylor@fluencydigital.io)</option>
                            <option value="staylor@fluencycare.com">Steve Taylor (staylor@fluencycare.com) - FluencyCare</option>
                            <option value="aaron.black@fluencydigital.io">Aaron Black (aaron.black@fluencydigital.io)</option>
                        </select>
                    </div>

                    <div class="form-group">
                        <label>Subject</label>
                        <input type="text" name="subject" value="{{ generated_email.subject|e }}" required>
                    </div>

                    <div class="form-group">
                        <label>Email Body</label>
                        <textarea name="body" required>{{ generated_email.body|e }}</textarea>
                        <p class="help-text">Edit as needed. Signature will be added automatically based on sender.</p>
                    </div>

                    <button type="submit" class="btn btn-success" id="sendBtn">
                        📤 Send Email
                    </button>

                    <div style="display: flex; gap: 10px; margin-top: 10px;">
                        <button type="button" class="btn btn-outline" style="flex: 1;" onclick="showSaveTemplateModal()">
                            💾 Save as Template
                        </button>
                        {% if selected_template_id %}
                        <button type="button" class="btn btn-outline" style="flex: 1; background: #E0E7FF; border-color: #6366F1;" onclick="updateTemplate()">
                            🔄 Update Template
                        </button>
                        {% endif %}
                    </div>
                </form>

                <form method="POST" style="margin-top: 10px;">
                    <input type="hidden" name="action" value="generate">
                    <input type="hidden" name="firstName" value="{{ first_name|e }}">
                    <input type="hidden" name="lastName" value="{{ last_name|e }}">
                    <input type="hidden" name="email" value="{{ email_address|e }}">
                    <input type="hidden" name="title" value="{{ title|e }}">
                    <input type="hidden" name="company" value="{{ company|e }}">
                    <input type="hidden" name="skills" value="{{ skills|e }}">
                    <input type="hidden" name="contact_type" value="{{ contact_type|e }}">
                    <input type="hidden" name="selected_template_id" value="{{ selected_template_id }}">
                    <button type="submit" class="btn btn-outline">🔄 Regenerate</button>
                </form>

                <a href="javascript:window.close()" class="close-btn">Cancel</a>

            {% else %}
                <!-- Initial form to generate email -->
                {% if error %}
                    <div class="result-box result-error">
                        <p>{{ error }}</p>
                    </div>
                {% endif %}

                <form method="POST" id="generateForm">
                    <input type="hidden" name="action" value="generate">
                    <input type="hidden" name="contact_id" value="{{ contact_id }}">
                    <input type="hidden" name="selected_template_id" id="selected_template_id" value="">

                    <div class="contact-info">
                        <h3>📧 Email to:</h3>
                        <p><strong>{{ first_name }} {{ last_name }}</strong></p>
                        <p>{{ email_address }}</p>
                        {% if title %}<p>{{ title }}{% if company %} at {{ company }}{% endif %}</p>{% endif %}
                    </div>

                    <div class="type-toggle">
                        <button type="button" class="type-btn candidate {% if contact_type != 'client' %}active{% endif %}" onclick="setType('candidate')">
                            👤 Candidate
                        </button>
                        <button type="button" class="type-btn client {% if contact_type == 'client' %}active{% endif %}" onclick="setType('client')">
                            🏢 Client
                        </button>
                    </div>
                    <input type="hidden" name="contact_type" id="contact_type" value="{{ contact_type }}">

                    <!-- Hidden fields for contact info -->
                    <input type="hidden" name="firstName" value="{{ first_name|e }}">
                    <input type="hidden" name="lastName" value="{{ last_name|e }}">
                    <input type="hidden" name="email" value="{{ email_address|e }}">
                    <input type="hidden" name="title" value="{{ title|e }}">
                    <input type="hidden" name="company" value="{{ company|e }}">
                    <input type="hidden" name="skills" value="{{ skills|e }}">

                    <div class="form-group">
                        <label>Template</label>
                        <select id="templateSelect" style="width: 100%; padding: 10px 12px; border: 2px solid #E2E8F0; border-radius: 8px; font-size: 14px;" onchange="applyTemplate()">
                            <option value="">-- No Template --</option>
                            {% for tmpl in email_templates %}
                                <option value="{{ tmpl.id }}"
                                        data-type="{{ tmpl.type }}"
                                        data-subject="{{ tmpl.subject|e }}"
                                        data-body="{{ tmpl.body|e }}"
                                        data-prompt="{{ tmpl.prompt|e }}"
                                        data-contact-type="{{ tmpl.contact_type }}"
                                        {% if tmpl.contact_type != 'any' and tmpl.contact_type != contact_type %}class="hidden-template" style="display: none;"{% endif %}>
                                    {{ tmpl.name }}{% if tmpl.type == 'prompt' %} (AI){% endif %}{% if tmpl.contact_type == 'candidate' %} [Cand]{% elif tmpl.contact_type == 'client' %} [Client]{% endif %}
                                </option>
                            {% endfor %}
                        </select>
                        <div style="margin-top: 6px;">
                            <label style="display: inline-flex; align-items: center; font-size: 12px; color: #64748B; cursor: pointer;">
                                <input type="checkbox" id="showAllTemplates" onchange="toggleAllTemplates()" style="margin-right: 6px;">
                                Show all templates (including other contact types)
                            </label>
                        </div>
                    </div>

                    <div class="form-group">
                        <label>Send As</label>
                        <select name="send_as" style="width: 100%; padding: 10px 12px; border: 2px solid #E2E8F0; border-radius: 8px; font-size: 14px;">
                            <option value="staylor@fluencydigital.io">Stephen Taylor (@stephen)</option>
                            <option value="staylor@fluencycare.com">Steve Taylor (@steve) - FluencyCare</option>
                            <option value="aaron.black@fluencydigital.io">Aaron Black (@aaron)</option>
                        </select>
                        <p class="help-text">AI will match the sender's writing style</p>
                    </div>

                    <div class="form-group">
                        <label>Additional Context (Optional)</label>
                        <textarea name="custom_context" rows="3" placeholder="Add any context to personalize the email...&#10;&#10;Examples:&#10;• Met at conference last week&#10;• Referred by John Smith&#10;• Looking for ML engineers"></textarea>
                        <p class="help-text">AI will use this + their title/company to personalize the email</p>
                    </div>

                    <div class="form-group" style="display: flex; gap: 10px;">
                        <a href="{{ request.script_root }}/quickcontext"
                           onclick="window.open(this.href, 'quickcontext', 'popup=yes,width=550,height=600'); return false;"
                           style="flex: 1; padding: 10px; background: linear-gradient(135deg, #7C3AED, #A78BFA); color: white; text-decoration: none; border-radius: 8px; font-size: 13px; font-weight: 500; text-align: center;">
                            📝 Edit AI Context {% if ai_context %}(active){% endif %}
                        </a>
                    </div>

                    {% if recent_emails %}
                    <div class="form-group">
                        <details style="background: #F8FAFC; padding: 12px; border-radius: 8px; border: 1px solid #E2E8F0;">
                            <summary style="cursor: pointer; font-size: 12px; font-weight: 600; color: #64748B;">📝 RECENT EMAILS ({{ recent_emails|length }}) - AI will learn from these</summary>
                            <div style="margin-top: 10px; max-height: 200px; overflow-y: auto;">
                                {% for email in recent_emails %}
                                <div style="padding: 8px; margin-bottom: 8px; background: white; border-radius: 6px; border-left: 3px solid #4BA3C3;">
                                    <div style="font-size: 11px; color: #64748B;">To: {{ email.to|e }}</div>
                                    <div style="font-size: 12px; font-weight: 600; color: #1E293B;">{{ email.subject|e }}</div>
                                    <div style="font-size: 11px; color: #475569; margin-top: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{{ email.body[:100]|e }}...</div>
                                </div>
                                {% endfor %}
                            </div>
                        </details>
                    </div>
                    {% endif %}

                    <button type="submit" class="btn btn-primary" id="generateBtn">
                        ✨ Generate Email with AI
                    </button>
                </form>

                <a href="javascript:window.close()" class="close-btn">Cancel</a>
            {% endif %}
        </div>
    </div>

    <!-- Save Template Modal -->
    <div id="saveTemplateModal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000; align-items: center; justify-content: center;">
        <div style="background: white; padding: 24px; border-radius: 12px; max-width: 400px; width: 90%; box-shadow: 0 10px 40px rgba(0,0,0,0.3);">
            <h3 style="margin-bottom: 16px; font-size: 18px;">💾 Save as Template</h3>
            <div style="margin-bottom: 16px;">
                <label style="display: block; font-size: 12px; font-weight: 600; color: #64748B; margin-bottom: 6px;">Template Name</label>
                <input type="text" id="templateName" placeholder="e.g., ML Engineer Outreach" style="width: 100%; padding: 10px; border: 2px solid #E2E8F0; border-radius: 8px; font-size: 14px;">
            </div>
            <div style="margin-bottom: 16px;">
                <label style="display: block; font-size: 12px; font-weight: 600; color: #64748B; margin-bottom: 6px;">Type</label>
                <select id="templateType" style="width: 100%; padding: 10px; border: 2px solid #E2E8F0; border-radius: 8px; font-size: 14px;">
                    <option value="full">Full Email (subject + body)</option>
                    <option value="prompt">AI Prompt (instructions for AI)</option>
                </select>
            </div>
            <div style="margin-bottom: 16px;">
                <label style="display: block; font-size: 12px; font-weight: 600; color: #64748B; margin-bottom: 6px;">Use For</label>
                <select id="templateContactType" style="width: 100%; padding: 10px; border: 2px solid #E2E8F0; border-radius: 8px; font-size: 14px;">
                    <option value="any">Any (Candidate & Client)</option>
                    <option value="candidate">Candidates Only</option>
                    <option value="client">Clients Only</option>
                </select>
            </div>
            <div style="display: flex; gap: 10px;">
                <button onclick="saveTemplate()" style="flex: 1; padding: 12px; background: linear-gradient(135deg, #22C55E, #16A34A); color: white; border: none; border-radius: 8px; font-weight: 600; cursor: pointer;">Save</button>
                <button onclick="hideSaveTemplateModal()" style="flex: 1; padding: 12px; background: #E2E8F0; color: #475569; border: none; border-radius: 8px; font-weight: 600; cursor: pointer;">Cancel</button>
            </div>
        </div>
    </div>

    <!-- Update Template Modal -->
    <div id="updateTemplateModal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000; align-items: center; justify-content: center;">
        <div style="background: white; padding: 24px; border-radius: 12px; max-width: 400px; width: 90%; box-shadow: 0 10px 40px rgba(0,0,0,0.3);">
            <h3 style="margin-bottom: 16px; font-size: 18px;">🔄 Update Template</h3>
            <div style="margin-bottom: 16px;">
                <label style="display: block; font-size: 12px; font-weight: 600; color: #64748B; margin-bottom: 6px;">Template Name</label>
                <input type="text" id="updateTemplateName" style="width: 100%; padding: 10px; border: 2px solid #E2E8F0; border-radius: 8px; font-size: 14px;">
            </div>
            <div style="margin-bottom: 16px;">
                <label style="display: block; font-size: 12px; font-weight: 600; color: #64748B; margin-bottom: 6px;">Type</label>
                <select id="updateTemplateType" style="width: 100%; padding: 10px; border: 2px solid #E2E8F0; border-radius: 8px; font-size: 14px;">
                    <option value="full">Full Email (subject + body)</option>
                    <option value="prompt">AI Prompt (instructions for AI)</option>
                </select>
                <p style="font-size: 11px; color: #94A3B8; margin-top: 4px;">Change to AI Prompt to save body as instructions</p>
            </div>
            <div style="margin-bottom: 16px;">
                <label style="display: block; font-size: 12px; font-weight: 600; color: #64748B; margin-bottom: 6px;">Use For</label>
                <select id="updateTemplateContactType" style="width: 100%; padding: 10px; border: 2px solid #E2E8F0; border-radius: 8px; font-size: 14px;">
                    <option value="any">Any (Candidate & Client)</option>
                    <option value="candidate">Candidates Only</option>
                    <option value="client">Clients Only</option>
                </select>
            </div>
            <div style="display: flex; gap: 10px;">
                <button onclick="saveUpdateTemplate()" style="flex: 1; padding: 12px; background: linear-gradient(135deg, #6366F1, #4F46E5); color: white; border: none; border-radius: 8px; font-weight: 600; cursor: pointer;">Update</button>
                <button onclick="hideUpdateTemplateModal()" style="flex: 1; padding: 12px; background: #E2E8F0; color: #475569; border: none; border-radius: 8px; font-weight: 600; cursor: pointer;">Cancel</button>
            </div>
        </div>
    </div>

    <script>
        // Toggle showing all templates regardless of contact type
        function toggleAllTemplates() {
            var showAll = document.getElementById('showAllTemplates').checked;
            var options = document.querySelectorAll('#templateSelect option.hidden-template');
            options.forEach(function(opt) {
                opt.style.display = showAll ? '' : 'none';
            });
        }

        // Add loading state on form submit
        document.querySelectorAll('form').forEach(function(form) {
            form.addEventListener('submit', function() {
                var btn = this.querySelector('button[type="submit"]');
                if (btn) {
                    if (btn.id === 'generateBtn') {
                        btn.innerHTML = '<span class="spinner"></span> Generating...';
                    } else if (btn.id === 'sendBtn') {
                        btn.innerHTML = '<span class="spinner"></span> Sending...';
                    } else {
                        btn.innerHTML = '<span class="spinner"></span> Processing...';
                    }
                    btn.disabled = true;
                }
            });
        });
    </script>
</body>
</html>
'''
