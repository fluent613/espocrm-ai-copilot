# templates.py
# Simplified templates without iframe complexity

LOGIN_TEMPLATE = '''
<!doctype html>
<html>
<head>
    <title>EspoCRM AI Copilot - Login</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { 
            font-family: Arial, sans-serif; 
            max-width: 400px; 
            margin: 100px auto; 
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .login-container {
            background: white;
            padding: 40px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            text-align: center;
        }
        .header { 
            color: #333; 
            margin-bottom: 30px; 
        }
        
        .mission { 
            background: #e8f5e8; 
            padding: 15px; 
            border-radius: 8px; 
            margin: 20px 0; 
            border-left: 4px solid #28a745; 
            font-size: 14px;
        }
        
        input[type="password"] { 
            width: 100%; 
            padding: 15px; 
            border: 2px solid #ddd; 
            border-radius: 8px; 
            font-size: 16px;
            margin: 20px 0 10px 0;
            box-sizing: border-box;
        }
        
        input[type="password"]:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        /* Remember Me Checkbox Styling */
        .remember-me {
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 15px 0 20px 0;
            font-size: 14px;
            color: #555;
        }
        .remember-me input[type="checkbox"] {
            margin-right: 8px;
            transform: scale(1.2);
        }
        .remember-me label {
            cursor: pointer;
            user-select: none;
        }
        
        button { 
            width: 100%;
            padding: 15px 20px; 
            background: #667eea; 
            color: white; 
            border: none; 
            border-radius: 8px; 
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
            transition: background 0.3s;
        }
        button:hover { background: #5a6fd8; }
        button:disabled { 
            background: #ccc; 
            cursor: not-allowed; 
            opacity: 0.6;
        }
        
        .error { 
            color: #d32f2f; 
            margin: 15px 0; 
            padding: 10px;
            background: #ffebee;
            border-radius: 5px;
            border-left: 4px solid #d32f2f;
            font-size: 14px;
        }
        
        .warning {
            color: #f57c00;
            margin: 15px 0;
            padding: 10px;
            background: #fff3e0;
            border-radius: 5px;
            border-left: 4px solid #f57c00;
            font-size: 13px;
        }
        
        .footer {
            margin-top: 30px;
            font-size: 12px;
            color: #666;
        }
        
        .security-notice {
            background: #e3f2fd;
            border-left: 4px solid #2196f3;
            padding: 10px;
            margin: 15px 0;
            border-radius: 5px;
            font-size: 12px;
            color: #1976d2;
        }
        
        .session-info {
            background: #f0f8ff;
            border-left: 4px solid #667eea;
            padding: 8px;
            margin: 10px 0;
            border-radius: 5px;
            font-size: 11px;
            color: #667eea;
        }
        
        .rate-limit-info {
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 8px;
            margin: 10px 0;
            border-radius: 5px;
            font-size: 12px;
            color: #856404;
        }
        
        /* Honeypot fields - completely hidden */
        .honeypot { 
            position: absolute !important;
            left: -10000px !important;
            top: -10000px !important;
            width: 1px !important;
            height: 1px !important;
            overflow: hidden !important;
            clip: rect(1px, 1px, 1px, 1px) !important;
            white-space: nowrap !important;
        }
        
        /* Loading state for button */
        .loading {
            position: relative;
            color: transparent;
        }
        .loading::after {
            content: '';
            position: absolute;
            width: 16px;
            height: 16px;
            top: 50%;
            left: 50%;
            margin-left: -8px;
            margin-top: -8px;
            border-radius: 50%;
            border: 2px solid transparent;
            border-top-color: #ffffff;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        /* Mobile Responsive */
        @media (max-width: 480px) {
            body { 
                margin: 20px auto; 
                padding: 10px;
            }
            .login-container {
                padding: 30px 20px;
            }
            .header h1 {
                font-size: 1.5em;
            }
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="header">
            <h1>🤖 EspoCRM AI Copilot</h1>
            <p>AI Assistant for EspoCRM</p>
            <p style="font-size: 11px; opacity: 0.7;">by <a href="https://fluencydigital.io" target="_blank" style="color: #667eea; text-decoration: none;">Fluency Digital</a></p>
        </div>
        
        <div class="mission">
            <p><strong>💡 Open Source CRM Enhancement:</strong> Making EspoCRM smarter with AI-powered natural language processing and resume parsing!</p>
        </div>
        
        {% if error %}
            <div class="error">{{ error }}</div>
            {% if "attempts remaining" in error %}
                <div class="rate-limit-info">
                    <strong>⚠️ Security Notice:</strong> Multiple failed attempts detected. Please verify your access token.
                </div>
            {% endif %}
            {% if "temporarily locked" in error or "try again" in error %}
                <div class="warning">
                    <strong>🔒 Account Locked:</strong> Too many failed attempts. Please wait before trying again.
                </div>
            {% endif %}
        {% endif %}
        
        <form method="post" id="loginForm">
            <!-- Honeypot fields - hidden from real users but visible to bots -->
            <div class="honeypot">
                <label for="email">Email (leave blank)</label>
                <input type="email" id="email" name="email" tabindex="-1" autocomplete="off">
            </div>
            <div class="honeypot">
                <label for="website">Website (leave blank)</label>
                <input type="url" id="website" name="website" tabindex="-1" autocomplete="off">
            </div>
            <div class="honeypot">
                <label for="phone">Phone (leave blank)</label>
                <input type="tel" id="phone" name="phone" tabindex="-1" autocomplete="off">
            </div>
            <div class="honeypot">
                <label for="company">Company (leave blank)</label>
                <input type="text" id="company" name="company" tabindex="-1" autocomplete="off">
            </div>
            
            <!-- Real login fields -->
            <input type="password" 
                   name="token" 
                   id="token" 
                   placeholder="Enter access token" 
                   autofocus 
                   required
                   autocomplete="off">
            
            <!-- Remember Me Checkbox -->
            <div class="remember-me">
                <input type="checkbox" id="remember_me" name="remember_me" checked>
                <label for="remember_me">🕐 Keep me logged in for 30 days</label>
            </div>
            
            <button type="submit" id="loginBtn">🚀 Access Copilot</button>
        </form>
        
        <div class="session-info" id="sessionInfo">
            <strong>📝 Session Options:</strong><br>
            ✅ <strong>Checked:</strong> Stay logged in for 30 days<br>
            ⬜ <strong>Unchecked:</strong> Stay logged in for 7 days
        </div>
        
        <div class="security-notice">
            <strong>🔐 Security:</strong> Protected by rate limiting and honeypot security measures
        </div>
        
        <div class="footer">
            <p>Secure access to your AI-powered CRM assistant</p>
            <p style="font-size: 10px; color: #999; margin-top: 5px;">
                Open source project by <a href="https://fluencydigital.io" target="_blank" style="color: #667eea; text-decoration: none;">Fluency Digital</a> - supporting Feed My Starving Children
            </p>
        </div>
    </div>
    
    <script>
        // Clear form on page load if there was an error
        document.addEventListener('DOMContentLoaded', function() {
            const tokenInput = document.getElementById('token');
            const hasError = document.querySelector('.error');
            
            if (hasError && tokenInput) {
                tokenInput.value = '';
                tokenInput.focus();
                setTimeout(() => { tokenInput.value = ''; }, 100);
            }
        });
        
        document.getElementById('loginForm').addEventListener('submit', function(e) {
            const btn = document.getElementById('loginBtn');
            const token = document.getElementById('token').value;
            
            if (!token || token.length < 3) {
                e.preventDefault();
                alert('Please enter a valid access token');
                return false;
            }
            
            btn.disabled = true;
            btn.classList.add('loading');
            btn.textContent = 'Authenticating...';
            
            setTimeout(() => {
                btn.disabled = false;
                btn.classList.remove('loading');
                btn.textContent = '🚀 Access Copilot';
            }, 5000);
        });
        
        // Prevent form resubmission
        let submitted = false;
        document.getElementById('loginForm').addEventListener('submit', function(e) {
            if (submitted) {
                e.preventDefault();
                return false;
            }
            submitted = true;
        });
        
        // Clear honeypot fields on focus
        document.querySelectorAll('.honeypot input').forEach(input => {
            input.addEventListener('focus', function() {
                this.value = '';
            });
        });
        
        // Show session duration info
        const checkbox = document.getElementById('remember_me');
        const sessionInfo = document.getElementById('sessionInfo');
        
        if (checkbox && sessionInfo) {
            checkbox.addEventListener('change', function() {
                if (this.checked) {
                    sessionInfo.innerHTML = '<strong>📝 Selected:</strong> 30-day extended session - you won\\'t need to log in again for a month! 🎉';
                } else {
                    sessionInfo.innerHTML = '<strong>📝 Selected:</strong> 7-day standard session - you\\'ll stay logged in for a week.';
                }
            });
        }
        
        // Force clear field on any error display
        const errorElement = document.querySelector('.error');
        if (errorElement) {
            const tokenField = document.getElementById('token');
            if (tokenField) {
                tokenField.value = '';
                tokenField.removeAttribute('value');
                setTimeout(() => {
                    tokenField.value = '';
                    tokenField.focus();
                }, 200);
            }
        }
    </script>
</body>
</html>
'''

# Keep your existing ENHANCED_TEMPLATE - it doesn't need changes for the iframe removal
ENHANCED_TEMPLATE = '''
<!doctype html>
<html>
<head>
    <title>EspoCRM AI Copilot</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        
        /* Responsive Design */
        @media (max-width: 768px) {
            body { padding: 10px; }
            .header { padding: 15px; }
            .logout-btn { position: static; display: block; margin: 10px auto 0; width: fit-content; }
            .security-status, .session-status { 
                position: static; 
                display: inline-block; 
                margin: 5px 2px; 
                font-size: 9px;
            }
            .website-link {
                position: static;
                display: block;
                margin: 10px auto 0;
                width: fit-content;
            }
            .chat-history { max-height: 300px; }
            .message { margin-left: 5% !important; margin-right: 5% !important; }
            .input-form { flex-direction: column; gap: 10px; }
            .input-form input[type="text"] { margin-bottom: 10px; }
            .file-upload-area { padding: 15px; }
        }
        
        @media (max-width: 480px) {
            .header h1 { font-size: 1.5em; }
            .input-area { padding: 15px; }
            .message { font-size: 14px; }
            .empty-state { padding: 20px; }
            .empty-state ul { font-size: 13px; }
        }
        
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; text-align: center; position: relative; }
        .logout-btn { 
            position: absolute; 
            top: 15px; 
            right: 20px; 
            background: rgba(255,255,255,0.2); 
            color: white; 
            padding: 8px 15px; 
            border: 1px solid rgba(255,255,255,0.3); 
            border-radius: 5px; 
            text-decoration: none; 
            font-size: 12px;
            transition: background 0.3s;
        }
        .logout-btn:hover { background: rgba(255,255,255,0.3); color: white; }
        .mission { background: #e8f5e8; padding: 15px; border-radius: 8px; margin: 10px 0; text-align: center; border-left: 4px solid #28a745; }
        .chat-history { max-height: 400px; overflow-y: auto; border: 1px solid #ddd; padding: 15px; margin: 20px 0; }
        .message { margin: 10px 0; padding: 10px; border-radius: 8px; }
        .user-message { background: #e3f2fd; margin-left: 20%; }
        .assistant-message { background: #f8f9fa; margin-right: 20%; }
        .error-message { background: #f8d7da !important; color: #721c24; }
        .success-message { background: #d4edda !important; color: #155724; }
        .input-area { padding: 20px; background: #f8f9fa; border-radius: 10px; }
        .input-form { display: flex; gap: 10px; margin-bottom: 15px; }
        input[type="text"] { flex: 1; padding: 12px; border: 2px solid #ddd; border-radius: 5px; }
        button { padding: 12px 20px; background: #667eea; color: white; border: none; border-radius: 5px; cursor: pointer; }
        button:hover { background: #5a6fd8; }
        .empty-state { text-align: center; padding: 40px; color: #666; }
        
        /* File upload styles */
        .file-upload-area { 
            border: 2px dashed #ddd; 
            border-radius: 10px; 
            padding: 20px; 
            text-align: center; 
            margin: 10px 0;
            background: #fafafa;
            transition: all 0.3s ease;
        }
        .file-upload-area:hover { border-color: #667eea; background: #f0f4ff; }
        .file-upload-area.dragover { border-color: #667eea; background: #e8f2ff; }
        .file-upload-area input[type="file"] { display: none; }
        .file-upload-label { cursor: pointer; color: #666; }
        .file-upload-label:hover { color: #667eea; }
        .upload-button { background: #28a745; margin-top: 10px; }
        .upload-button:hover { background: #218838; }
        .selected-file { background: #e8f5e8; border-color: #28a745; color: #155724; }
        
        .divider { text-align: center; margin: 15px 0; color: #999; }
        .divider::before, .divider::after { 
            content: ''; 
            display: inline-block; 
            width: 30%; 
            height: 1px; 
            background: #ddd; 
            vertical-align: middle; 
            margin: 0 10px; 
        }
        
        /* Loading Spinner Styles */
        .loading-spinner {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.7);
            z-index: 9999;
            align-items: center;
            justify-content: center;
        }
        
        .spinner-content {
            background: white;
            padding: 40px;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            max-width: 350px;
        }
        
        .spinner {
            width: 50px;
            height: 50px;
            margin: 0 auto 20px;
            border: 5px solid #f3f3f3;
            border-top: 5px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .spinner-text {
            color: #333;
            font-weight: 600;
            margin-bottom: 10px;
            font-size: 18px;
        }
        
        .spinner-subtext {
            color: #666;
            font-size: 14px;
            line-height: 1.4;
        }
        
        .processing-message {
            color: #667eea;
            font-weight: 500;
            margin-top: 15px;
            font-size: 13px;
        }
        
        /* Security indicator */
        .security-status {
            position: absolute;
            top: 15px;
            left: 20px;
            background: rgba(40, 167, 69, 0.2);
            color: white;
            padding: 4px 8px;
            border-radius: 3px;
            font-size: 10px;
            border: 1px solid rgba(40, 167, 69, 0.3);
            z-index: 10;
        }
        
        /* Session indicator */
        .session-status {
            position: absolute;
            top: 15px;
            left: 120px;
            background: rgba(102, 126, 234, 0.2);
            color: white;
            padding: 4px 8px;
            border-radius: 3px;
            font-size: 10px;
            border: 1px solid rgba(102, 126, 234, 0.3);
            z-index: 10;
        }
        
        /* Website link */
        .website-link {
            position: absolute;
            bottom: 15px;
            right: 20px;
            background: rgba(255, 255, 255, 0.2);
            color: white;
            padding: 4px 8px;
            border-radius: 3px;
            font-size: 10px;
            text-decoration: none;
            border: 1px solid rgba(255, 255, 255, 0.3);
            transition: background 0.3s;
        }
        
        .website-link:hover {
            background: rgba(255, 255, 255, 0.3);
            color: white;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="security-status">🔒 Secured</div>
        <div class="session-status">⏰ Extended Session</div>
        <a href="/logout" class="logout-btn">🚪 Logout</a>
        <a href="https://fluencydigital.io" target="_blank" class="website-link">🌐 fluencydigital.io</a>
        <h1>🤖 EspoCRM AI Copilot</h1>
        <p>AI Assistant with Resume Parser & Natural Language Interface</p>
        <p style="font-size: 12px; opacity: 0.8;">by <a href="https://fluencydigital.io" target="_blank" style="color: white; text-decoration: none;">Fluency Digital</a></p>
    </div>
    
    <div class="mission">
        <p><strong>🚀 Open Source AI for EspoCRM:</strong> This tool enhances your EspoCRM with intelligent contact management, resume parsing, and natural language processing. Created by Fluency Digital.</p>
    </div>
    
    <div class="chat-history">
        {% if history %}
            {% for msg in history %}
                {% set message_class = 'user-message' if msg.role == 'user' else 'assistant-message' %}
                {% if msg.role == 'assistant' and msg.content.startswith('❌') %}
                    {% set message_class = message_class + ' error-message' %}
                {% elif msg.role == 'assistant' and msg.content.startswith('✅') %}
                    {% set message_class = message_class + ' success-message' %}
                {% endif %}
                
                <div class="message {{ message_class }}">
                    <strong>{{ msg.role.title() }}:</strong> 
                    {{ msg.content | replace('**', '<strong>') | replace('**', '</strong>') | safe }}
                </div>
            {% endfor %}
        {% else %}
            <div class="empty-state">
                <h3>👋 Welcome to EspoCRM AI Copilot!</h3>
                <p><strong>🚀 Ready to enhance your EspoCRM:</strong></p>
                <ul style="text-align: left; display: inline-block;">
                    <li>🔍 <strong>Smart contact search:</strong> "search for John Smith" or "find john@example.com"</li>
                    <li>📱 <strong>Quick updates:</strong> Search someone, then type "phone 555-1234" to update</li>
                    <li>📄 <strong>Resume parser:</strong> Upload PDF, DOC, or TXT files to auto-create contacts</li>
                    <li>💬 <strong>Natural conversation:</strong> Ask questions about your contacts and CRM</li>
                    <li>🏢 <strong>Account management:</strong> "create account Acme Corp" or "link John to Acme Corp"</li>
                    <li>📝 <strong>Add notes:</strong> "add note to John: Meeting scheduled for Friday"</li>
                    <li>📋 <strong>View notes:</strong> "show notes for John" or "notes for current contact"</li>
                </ul>
                <p><em>Try: "search for John Smith" then "title Senior Developer" or upload a resume file below</em></p>
                <p><em>Current contact: {{ last_contact.name if last_contact else "None" }}</em></p>
            </div>
        {% endif %}
    </div>
    
    <div class="input-area">
        <!-- Text Input Form -->
        <form method="post" class="input-form" id="textForm" onsubmit="showSpinner('Processing your request...')">
            <input type="text" name="prompt" placeholder="Search contacts, ask questions, or update contact info..." autofocus>
            <button type="submit">Send</button>
        </form>
        
        <div class="divider">OR</div>
        
        <!-- File Upload Form -->
        <form method="post" enctype="multipart/form-data" id="fileForm" onsubmit="showSpinner('Parsing resume and creating contact...')">
            <div class="file-upload-area" id="fileUploadArea">
                <label for="resume_file" class="file-upload-label">
                    📄 Click to upload a resume file (PDF, DOC, TXT)<br>
                    <small>Or drag and drop here</small><br>
                    <small style="color: #666; font-size: 10px;">Will automatically create/update contact with extracted info</small>
                </label>
                <input type="file" id="resume_file" name="resume_file" 
                       accept=".pdf,.doc,.docx,.txt,.rtf"
                       onchange="handleFileSelect(this)">
                <button type="submit" class="upload-button" id="uploadBtn" style="display:none;">
                    📤 Upload & Parse Resume
                </button>
            </div>
        </form>
    </div>
    
    <!-- Loading Spinner -->
    <div class="loading-spinner" id="loadingSpinner">
        <div class="spinner-content">
            <div class="spinner"></div>
            <div class="spinner-text" id="spinnerText">Processing...</div>
            <div class="spinner-subtext">
                Please wait while we process your request.<br>
                This may take a few moments for complex operations.
            </div>
            <div class="processing-message" id="processingMessage"></div>
        </div>
    </div>
    
    <div style="text-align: center; margin-top: 20px;">
        <a href="/" style="color: #666; text-decoration: none; margin-right: 15px;">🔄 Refresh</a>
        <a href="/reset" style="color: #666; text-decoration: none; margin-right: 15px;">🗑️ Reset Session</a>
        <a href="/debug" style="color: #666; text-decoration: none; margin-right: 15px;">🔍 Debug Info</a>
        <div style="font-size: 11px; color: #999; margin-top: 5px;">
            EspoCRM AI Copilot - Open Source CRM Enhancement by <a href="https://fluencydigital.io" target="_blank" style="color: #667eea; text-decoration: none;">Fluency Digital</a>
        </div>
        <div style="font-size: 10px; color: #666; margin-top: 8px; padding: 8px; background: #f9f9f9; border-radius: 5px; display: inline-block;">
            💝 <strong>Supporting a Good Cause:</strong> This tool was created by a consulting business that donates excess profits to 
            <a href="https://fmsc.org" target="_blank" style="color: #28a745; text-decoration: none;">Feed My Starving Children</a>. 
            Consider supporting their mission to feed hungry children worldwide.
        </div>
    </div>
    
    <script>
        // Auto-scroll chat to bottom
        const chatHistory = document.querySelector('.chat-history');
        if (chatHistory) {
            chatHistory.scrollTop = chatHistory.scrollHeight;
        }
        
        // Loading spinner functions
        function showSpinner(message) {
            const spinner = document.getElementById('loadingSpinner');
            const spinnerText = document.getElementById('spinnerText');
            const processingMessage = document.getElementById('processingMessage');
            
            if (spinner && spinnerText) {
                spinnerText.textContent = message || 'Processing...';
                processingMessage.textContent = 'Working with OpenAI and your EspoCRM...';
                spinner.style.display = 'flex';
                
                const buttons = document.querySelectorAll('button[type="submit"]');
                buttons.forEach(btn => {
                    btn.disabled = true;
                    btn.style.opacity = '0.6';
                });
            }
        }
        
        function hideSpinner() {
            const spinner = document.getElementById('loadingSpinner');
            if (spinner) {
                spinner.style.display = 'none';
                
                const buttons = document.querySelectorAll('button[type="submit"]');
                buttons.forEach(btn => {
                    btn.disabled = false;
                    btn.style.opacity = '1';
                });
            }
        }
        
        // Enhanced file upload handling
        function handleFileSelect(input) {
            const uploadArea = document.getElementById('fileUploadArea');
            const uploadBtn = document.getElementById('uploadBtn');
            const label = uploadArea.querySelector('.file-upload-label');
            
            if (input.files && input.files[0]) {
                const file = input.files[0];
                const fileSize = (file.size / 1024 / 1024).toFixed(2);
                
                label.innerHTML = `📄 Selected: ${file.name} (${fileSize} MB)<br><small>Ready to parse and create contact</small>`;
                uploadArea.classList.add('selected-file');
                uploadBtn.style.display = 'block';
                uploadBtn.innerHTML = '🚀 Upload & Parse Resume';
                
                setTimeout(() => {
                    showSpinner('Uploading and parsing resume...');
                    document.getElementById('fileForm').submit();
                }, 500);
            }
        }
        
        // Drag and drop functionality
        const fileUploadArea = document.getElementById('fileUploadArea');
        const fileInput = document.getElementById('resume_file');
        
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            fileUploadArea.addEventListener(eventName, preventDefaults, false);
        });
        
        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }
        
        ['dragenter', 'dragover'].forEach(eventName => {
            fileUploadArea.addEventListener(eventName, highlight, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            fileUploadArea.addEventListener(eventName, unhighlight, false);
        });
        
        function highlight(e) {
            fileUploadArea.classList.add('dragover');
        }
        
        function unhighlight(e) {
            fileUploadArea.classList.remove('dragover');
        }
        
        fileUploadArea.addEventListener('drop', handleDrop, false);
        
        function handleDrop(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            
            if (files.length > 0) {
                fileInput.files = files;
                handleFileSelect(fileInput);
            }
        }
        
        // Enhanced form submission
        document.getElementById('textForm').addEventListener('submit', function(e) {
            const input = this.querySelector('input[name="prompt"]');
            if (!input.value.trim()) {
                e.preventDefault();
                alert('Please enter a message first');
                return false;
            }
            
            const message = input.value.length > 50 ? 'Processing your request...' : 'Searching and updating...';
            showSpinner(message);
        });
    </script>
</body>
</html>
'''
