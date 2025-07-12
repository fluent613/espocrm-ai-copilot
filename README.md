# EspoCRM AI Copilot 🤖

An intelligent AI assistant that transforms your EspoCRM into a natural language interface with resume parsing, contact management, and natural language processing.

**Built by a consulting business that donates excess profits to Feed My Starving Children (FMSC)**

## Features

- **OpenAI-powered natural language processing** - Talk to your CRM in plain English
- **Automatic resume parsing** - Upload resumes to auto-create contacts with extracted info
- **Enterprise-grade security** - Rate limiting, honeypot protection, session management
- **Mobile-responsive design** - Works on desktop and mobile devices
- **Real-time contact context switching** - Automatically switches context when you mention contacts
- **Smart note management** - Add notes to contacts using natural language
- **Account management** - Manage companies and link them to contacts
- **Calendar integration** - View and create calendar events for users
- **Easy EspoCRM integration** - Open alongside your CRM or add to navigation menu

## Quick Start

### Option 1: Docker (Recommended)

```bash
git clone https://github.com/yourusername/espocrm-ai-copilot
cd espocrm-ai-copilot
cp .env.example .env
# Edit .env with your configuration
docker-compose up -d
```

### Option 2: Manual Installation

```bash
git clone https://github.com/yourusername/espocrm-ai-copilot
cd espocrm-ai-copilot
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your configuration
python app.py
```

Visit `http://localhost:5000` and use your access token to log in.

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key-here

# EspoCRM Configuration  
ESPOCRM_URL=http://your-espocrm-url/api/v1
ESPO_API_KEY=your-espocrm-api-key

# Security
FLUENCY_AUTH_TOKEN=your-secure-access-token
FLASK_SECRET_KEY=your-flask-secret-key

# Optional: Custom iframe domains
ALLOWED_IFRAME_DOMAINS=https://crm.yourcompany.com,http://localhost:8080
```

## EspoCRM Setup

### 1. **Create API User in EspoCRM**

**Step 1:** Create the API User
- Go to **Administration → Users**
- Click **Create User**
- Username: `copilot` (recommended)
- User Type: **API**
- Is Active: **Yes**
- Generate and save the **API Key** (you'll need this for your .env file)

**Step 2:** Configure User Permissions
Create or assign a role with these **specific permissions**:

**Contacts:**
- Read: Yes
- Create: Yes  
- Edit: Yes
- Delete: No (optional - for safety)
- Stream: Yes (for notes)

**Accounts:**
- Read: Yes
- Create: Yes
- Edit: Yes  
- Delete: No (recommended for safety)

**Notes/Stream:**
- Read: Yes
- Create: Yes
- Edit: Yes
- Delete: Yes (for note management)

**Optional Entities:**
- **Calendar/Events:** Read, Create, Edit (if using calendar features)
- **Users:** Read (needed for calendar user lookup)

### 2. **Required Custom Fields (if not already present)**
Add these custom fields to **Contacts** entity:
- `cCurrentTitle` (Text) - Current job title
- `cSkills` (Text) - Technical skills  
- `cCurrentCompany` (Text) - Current company
- `cLinkedInURL` (Url) - LinkedIn profile

### 3. **Integration with EspoCRM**

**Option A: Navigation Menu**
- Go to **Administration → User Interface → Navigation**
- Add new tab: **"AI Copilot"**
- URL: `http://your-copilot-url:5000`
- Open in: **New Tab/Window**

**Option B: Quick Bookmark**
- Bookmark your Copilot URL
- Keep it open alongside EspoCRM for seamless workflow

## Usage Examples

### Basic Contact Operations
```
"search for John Smith"
"create contact: John Doe, john@example.com, 555-1234"
"update email to newemail@company.com"
"add note: Called about project, very interested"
```

### Resume Processing
- Upload PDF, DOC, or TXT resume files
- Automatically extracts name, email, phone, skills, experience
- Creates or updates contacts with parsed information

### Natural Language Queries
```
"find contacts in Minneapolis"
"show me all notes for Sarah Johnson"
"create meeting with John tomorrow at 2pm"
"link John Smith to Acme Corporation"
```

## Security Features

- **Rate limiting** - Prevents brute force login attempts
- **Honeypot protection** - Blocks automated bot attacks  
- **Session management** - Secure, persistent sessions (7-30 days)
- **Input sanitization** - Prevents XSS and injection attacks
- **Environment-based configuration** - No hardcoded secrets

## Requirements

- Python 3.8+
- OpenAI API key
- EspoCRM instance with API access
- Optional: Docker for containerized deployment

## Development

### Local Development Setup
```bash
git clone <repository>
cd espocrm-ai-copilot
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Configure .env
python app.py
```

### Project Structure
```
espocrm-ai-copilot/
├── app.py              # Main Flask application
├── crm_functions.py    # EspoCRM API integration
├── resume_parser.py    # Resume parsing logic
├── security.py         # Security middleware
├── templates.py        # HTML templates
├── utils.py           # Utility functions
├── requirements.txt   # Python dependencies
├── .env.example       # Environment template
├── docker-compose.yml # Docker setup
└── README.md         # This file
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Supporting Feed My Starving Children

This project was created by a consulting business that donates excess profits to [Feed My Starving Children](https://fmsc.org), a nonprofit organization that feeds hungry children around the world.

By using and improving this tool, you're indirectly supporting efforts to feed children in need. Consider donating directly to FMSC if this tool helps your business!

## Acknowledgments

- OpenAI for providing the AI capabilities
- EspoCRM for the excellent open-source CRM platform
- The open-source community for inspiration and tools

## Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/espocrm-ai-copilot/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/espocrm-ai-copilot/discussions)
- **Email**: For security issues or business inquiries

---

**If this project helps you, please give it a star on GitHub!**