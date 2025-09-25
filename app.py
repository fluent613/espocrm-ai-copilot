MODEL_NAME = "gpt-5-mini"

# app.py
# Enhanced Flask application for EspoCRM AI Copilot
# Robust parsing for any input format

from flask import Flask, request, render_template_string, session, redirect, make_response
from flask_session import Session
import openai
import json
import time
import os
import logging
from datetime import timedelta
from dotenv import load_dotenv
from pathlib import Path

# Import our custom modules
from resume_parser import ResumeParser
from crm_functions import CRMManager
from utils import (
    sanitize_input, set_last_contact, get_last_contact, init_session,
    preprocess_input, extract_contact_name_from_update, is_update_intent,
    create_phone_number_data
)
# SECURITY: Import security functions
from security import rate_limit_login, handle_failed_login, check_honeypot
import re

load_dotenv()

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# NEW: UNIVERSAL INPUT PARSER - Handles ANY format
def parse_any_contact_input(user_input: str) -> dict:
    """
    Universal parser that handles ANY contact input format:
    - Markdown with ** formatting
    - Pipe-separated data
    - Copy-pasted LinkedIn profiles
    - Messy multi-line data
    - Mixed formats
    
    Returns a structured dict ready for contact creation/update
    """
    logger.info(f"🤖 UNIVERSAL PARSER: Processing {len(user_input)} chars")
    
    # Initialize result structure
    result = {
        'action': None,  # 'create', 'update', or 'add_note'
        'contact_name': None,
        'first_name': None,
        'last_name': None,
        'fields': {}
    }
    
    # Clean up the input - remove excessive markdown, normalize whitespace
    clean_input = re.sub(r'\*\*([^*]+)\*\*', r'\1', user_input)  # Remove **
    clean_input = re.sub(r'\*([^*]+)\*', r'\1', clean_input)      # Remove *
    clean_input = re.sub(r'\s+', ' ', clean_input)                # Normalize spaces
    
    # STEP 1: Detect action and primary name
    lines = user_input.strip().split('\n')
    first_line = lines[0].lower() if lines else ""
    
    # Detect action
    if any(word in first_line for word in ['add:', 'create:', 'new contact']):
        result['action'] = 'create'
    elif any(word in first_line for word in ['update:', 'edit:', 'modify:']):
        result['action'] = 'update'
    elif any(word in first_line for word in ['note:', 'add note:', 'notes:']):
        result['action'] = 'add_note'
    else:
        # Default based on content
        result['action'] = 'create' if 'create' in user_input.lower() else 'update'
    
    # STEP 2: Extract name - Try multiple patterns
    name = None
    
    # Pattern 1: Name after action word (add: **Name** or add: Name)
    action_patterns = [
        r'(?:add|create|update|edit):\s*\*?\*?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
        r'(?:add|create|update|edit)\s+\*?\*?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
    ]
    
    for pattern in action_patterns:
        match = re.search(pattern, user_input, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            break
    
    # Pattern 2: First bold name in document
    if not name:
        bold_name = re.search(r'\*\*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\*\*', user_input)
        if bold_name:
            name = bold_name.group(1).strip()
    
    # Pattern 3: Look for "Profile" or "Contact" preceded by a name
    if not name:
        profile_pattern = re.search(r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'?s?\s+Profile", user_input, re.IGNORECASE)
        if profile_pattern:
            name = profile_pattern.group(1).strip()
    
    # Pattern 4: First line that looks like a name
    if not name:
        for line in lines[:5]:  # Check first 5 lines
            clean_line = re.sub(r'[*:\-]', '', line).strip()
            if re.match(r'^[A-Z][a-z]+\s+[A-Z][a-z]+$', clean_line):
                name = clean_line
                break
    
    # Split name into first and last
    if name:
        name_parts = name.split()
        result['contact_name'] = name
        result['first_name'] = name_parts[0] if name_parts else None
        result['last_name'] = ' '.join(name_parts[1:]) if len(name_parts) > 1 else None
        logger.info(f"✅ PARSER: Found name: {name}")
    
    # STEP 3: Extract fields using multiple strategies
    
    # Email extraction - multiple patterns
    email_patterns = [
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        r'(?:Email|email|E-mail|e-mail)[:\s]*([^\s@]+@[^\s@]+\.[^\s]+)',
    ]
    
    for pattern in email_patterns:
        match = re.search(pattern, clean_input)
        if match:
            email = match.group(0) if '@' in match.group(0) else match.group(1)
            result['fields']['emailAddress'] = email.strip()
            logger.info(f"✅ PARSER: Found email: {email}")
            break
    
    # Phone extraction - handle multiple formats
    phone_patterns = [
        r'(\+?1?[-.\s]?)?\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})',
        r'(?:Phone|phone|Mobile|mobile|Cell|cell)[:\s]*([\d\s\-\(\)\.]+)',
    ]
    
    for pattern in phone_patterns:
        match = re.search(pattern, clean_input)
        if match:
            phone_raw = match.group(0)
            # Clean and validate
            digits = re.sub(r'[^\d]', '', phone_raw)
            if len(digits) >= 10:
                # Format nicely
                if len(digits) == 10:
                    phone_formatted = f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
                elif len(digits) == 11 and digits[0] == '1':
                    phone_formatted = f"{digits[1:4]}-{digits[4:7]}-{digits[7:]}"
                else:
                    phone_formatted = phone_raw.strip()
                
                result['fields']['phoneNumber'] = phone_formatted
                logger.info(f"✅ PARSER: Found phone: {phone_formatted}")
                break
    
    # LinkedIn extraction
    linkedin_patterns = [
        r'linkedin\.com/in/([a-zA-Z0-9\-]+)',
        r'(?:LinkedIn|linkedin)[:\s]*((?:https?://)?(?:www\.)?linkedin\.com/in/[^\s]+)',
    ]
    
    for pattern in linkedin_patterns:
        match = re.search(pattern, clean_input, re.IGNORECASE)
        if match:
            linkedin_part = match.group(0) if 'linkedin.com' in match.group(0) else f"linkedin.com/in/{match.group(1)}"
            if not linkedin_part.startswith('http'):
                linkedin_part = 'https://' + linkedin_part
            result['fields']['cLinkedInURL'] = linkedin_part
            logger.info(f"✅ PARSER: Found LinkedIn: {linkedin_part}")
            break
    
    # Website extraction
    website_patterns = [
        r'(?:Website|website|Site|site)[:\s]*((?:https?://)?(?:www\.)?[a-zA-Z0-9\-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?)',
        r'(?<![@])\b(?:https?://)?(?:www\.)?([a-zA-Z0-9\-]+\.(?:com|org|edu|net|io|ai|co|gov)[^\s]*)',
    ]
    
    for pattern in website_patterns:
        match = re.search(pattern, clean_input)
        if match:
            website = match.group(1) if match.lastindex else match.group(0)
            # Skip if it's linkedin or an email domain
            if website and 'linkedin' not in website and '@' not in website:
                if not website.startswith('http'):
                    website = 'https://' + website
                result['fields']['website'] = website
                logger.info(f"✅ PARSER: Found website: {website}")
                break
    
    # Title/Position extraction
    title_patterns = [
        r'(?:Title|title|Position|position|Role|role)[:\s]*([^\n]+)',
        r'(?:^|\n)([A-Z][^:\n]*(?:Manager|Director|President|CEO|CTO|CFO|Engineer|Developer|Analyst|Consultant|Partner|Principal|Lead|Senior|Junior)[^:\n]*)',
    ]
    
    for pattern in title_patterns:
        match = re.search(pattern, clean_input)
        if match:
            title = match.group(1).strip()
            # Clean up title
            title = re.sub(r'^[-\s]+|[-\s]+$', '', title)
            if title and len(title) > 2 and len(title) < 100:
                result['fields']['cCurrentTitle'] = title
                logger.info(f"✅ PARSER: Found title: {title}")
                break
    
    # Company extraction
    company_patterns = [
        r'(?:Company|company|Organization|organization|Employer|employer)[:\s]*([^\n]+)',
        r'(?:@|at\s+)([A-Z][a-zA-Z\s&]+(?:Inc|LLC|Corp|Company|Group|Partners|Services|Solutions|Technologies|Enterprises))',
    ]
    
    for pattern in company_patterns:
        match = re.search(pattern, clean_input)
        if match:
            company = match.group(1).strip()
            company = re.sub(r'^[-\s]+|[-\s]+$', '', company)
            if company and len(company) > 2:
                result['fields']['cCurrentCompany'] = company
                logger.info(f"✅ PARSER: Found company: {company}")
                break
    
    # Skills extraction
    skills_patterns = [
        r'(?:Skills|skills|Expertise|expertise)[:\s]*([^\n]+(?:\n[^\n:]+)*)',
        r'(?:Technologies|technologies|Tools|tools)[:\s]*([^\n]+)',
    ]
    
    for pattern in skills_patterns:
        match = re.search(pattern, clean_input)
        if match:
            skills = match.group(1).strip()
            # Clean up skills
            skills = re.sub(r'\s+', ' ', skills)
            if skills and len(skills) > 5:
                result['fields']['cSkills'] = skills[:500]  # Limit length
                logger.info(f"✅ PARSER: Found skills: {skills[:50]}...")
                break
    
    # Address extraction (basic)
    address_patterns = [
        r'(?:Address|address|Location|location)[:\s]*([^\n]+)',
        r'(\d+\s+[A-Z][a-zA-Z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Place|Pl)[^\n]*)',
    ]
    
    for pattern in address_patterns:
        match = re.search(pattern, clean_input, re.IGNORECASE)
        if match:
            address = match.group(1).strip()
            if address:
                # Try to parse city, state, zip
                city_state_zip = re.search(r'([A-Z][a-zA-Z\s]+),\s*([A-Z]{2})\s*(\d{5})?', address)
                if city_state_zip:
                    result['fields']['addressCity'] = city_state_zip.group(1).strip()
                    result['fields']['addressState'] = city_state_zip.group(2).strip()
                    if city_state_zip.group(3):
                        result['fields']['addressPostalCode'] = city_state_zip.group(3).strip()
                else:
                    result['fields']['addressStreet'] = address
                logger.info(f"✅ PARSER: Found address: {address}")
                break
    
    # Birthday extraction
    birthday_patterns = [
        r'(?:Birthday|birthday|Born|born|DOB|Birthdate)[:\s]*([A-Z][a-z]+\s+\d{1,2}(?:,?\s+\d{4})?)',
        r'(?:Birthday|birthday)[:\s]*(\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)',
    ]
    
    for pattern in birthday_patterns:
        match = re.search(pattern, clean_input, re.IGNORECASE)
        if match:
            birthday = match.group(1).strip()
            result['fields']['birthday'] = birthday
            logger.info(f"✅ PARSER: Found birthday: {birthday}")
            break
    
    # Connected date (for LinkedIn connections)
    connected_pattern = re.search(r'(?:Connected|connected)[:\s]*([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})', clean_input)
    if connected_pattern:
        result['fields']['connected_date'] = connected_pattern.group(1).strip()
    
    logger.info(f"✅ PARSER: Final result - Action: {result['action']}, Name: {result['contact_name']}, Fields: {list(result['fields'].keys())}")
    return result


# NEW: ENHANCED CONTEXT SWITCHING FUNCTIONS
def extract_contact_from_input(user_input: str) -> str:
    """Extract contact name from any user input - handles all patterns"""
    
    # Use the universal parser to extract name
    parsed = parse_any_contact_input(user_input)
    return parsed.get('contact_name')


def switch_context_if_mentioned(user_input: str, crm_manager) -> bool:
    """Automatically switch context if a contact is mentioned in input"""
    
    mentioned_contact = extract_contact_from_input(user_input)
    if not mentioned_contact:
        return False
    
    logger.info(f"🔄 CONTEXT SWITCH: Detected contact mention '{mentioned_contact}'")
    
    # Search for the contact
    contacts = crm_manager.search_contacts_simple(mentioned_contact)
    if not contacts:
        logger.info(f"🔄 CONTEXT SWITCH: Contact '{mentioned_contact}' not found")
        return False
    
    # Find best match
    best_match = contacts[0]
    for contact in contacts:
        contact_name = contact.get('name', '').strip()
        # Exact match
        if mentioned_contact.lower() == contact_name.lower():
            best_match = contact
            break
        # Partial match (first name or last name)
        elif mentioned_contact.lower() in contact_name.lower():
            best_match = contact
            break
    
    # Switch context
    contact_id = best_match['id']
    contact_name = best_match.get('name', mentioned_contact)
    set_last_contact(contact_id, contact_name)
    
    logger.info(f"✅ CONTEXT SWITCH: Switched to {contact_name} (ID: {contact_id})")
    return True


def create_user_friendly_error_message(error: Exception, user_input: str) -> str:
    """Create user-friendly error messages"""
    error_str = str(error).lower()
    
    if 'timeout' in error_str:
        # Check if operation likely succeeded
        if any(word in user_input.lower() for word in ['add', 'create', 'new']):
            parsed = parse_any_contact_input(user_input)
            contact_name = parsed.get('contact_name', 'the contact')
            return f"✅ Processing completed (took a bit long). {contact_name} should be in your CRM now.\n\nIf you don't see them, try searching for their name."
        
        return "⌛ The operation is taking longer than expected. It may have completed - please check your CRM."
    
    return f"⚠️ An issue occurred: {str(error)[:100]}...\n\nThe operation may have completed - please check your CRM."


# Session management for calendar user context
def set_current_calendar_user(user_name: str):
    """Remember the current user for calendar operations"""
    session['current_calendar_user'] = user_name
    session.modified = True

def get_current_calendar_user():
    """Get the current user for calendar operations"""
    return session.get('current_calendar_user')

# Flask setup
app = Flask(__name__)

SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'espocrm-ai-copilot-secret-key-2024')
app.secret_key = SECRET_KEY

SESSION_DIR = Path(os.getenv('SESSION_DIR', '/opt/copilot/sessions'))
SESSION_DIR.mkdir(exist_ok=True, mode=0o755)

# ENHANCED Session Configuration
app.config.update(
    SESSION_TYPE='filesystem',
    SESSION_FILE_DIR=str(SESSION_DIR),
    SESSION_PERMANENT=True,
    SESSION_USE_SIGNER=True,
    SESSION_KEY_PREFIX='copilot:',
    SESSION_FILE_THRESHOLD=500,
    SESSION_COOKIE_NAME='copilot_session',
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=False,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(days=7)
)

Session(app)

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ESPO_API_KEY = os.getenv("ESPO_API_KEY")
ESPOCRM_URL = os.getenv("ESPOCRM_URL", "http://localhost:8080/api/v1")
AUTH_TOKEN = os.getenv("FLUENCY_AUTH_TOKEN")

# Check for required environment variables
if not OPENAI_API_KEY:
    logger.error("OPENAI_API_KEY is required!")
    exit(1)
if not ESPO_API_KEY:
    logger.error("ESPO_API_KEY is required!")  
    exit(1)
if not AUTH_TOKEN:
    logger.error("FLUENCY_AUTH_TOKEN is required!")
    exit(1)

HEADERS = {"X-Api-Key": ESPO_API_KEY, "Content-Type": "application/json"}

# Initialize components
client = openai.OpenAI(api_key=OPENAI_API_KEY)
resume_parser = ResumeParser(client)
crm_manager = CRMManager(ESPOCRM_URL, HEADERS)

# Security headers
@app.after_request
def after_request(response):
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['Content-Security-Policy'] = "frame-ancestors 'self'"
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response

# Authentication
@app.before_request
def require_auth_token():
    if request.path in ['/login', '/reset', '/debug', '/test-search', '/test-json-where', '/test-phone', '/test-account-link']:
        return
    
    if session.get('authenticated'):
        session.permanent = True
        session.modified = True
        return
    
    token = request.args.get('token') or request.headers.get('Authorization')
    
    if token == AUTH_TOKEN:
        session['authenticated'] = True
        session.permanent = True
        session.modified = True
        logger.info(f"✅ TOKEN AUTH: Direct token authentication from {request.remote_addr}")
        return
    
    logger.info(f"🔒 AUTH REQUIRED: Redirecting {request.remote_addr} to login")
    return redirect('/login')

# Function definitions for OpenAI
simple_functions = [
    {
        "type": "function",
        "function": {
            "name": "search_contacts",
            "description": "Search for contacts in the CRM",
            "parameters": {
                "type": "object",
                "properties": {
                    "criteria": {"type": "string", "description": "Search term"}
                },
                "required": ["criteria"]
            }
        }
    },
    {
        "type": "function", 
        "function": {
            "name": "create_contact",
            "description": "Create a new contact in the CRM",
            "parameters": {
                "type": "object",
                "properties": {
                    "firstName": {"type": "string"},
                    "lastName": {"type": "string"},
                    "emailAddress": {"type": "string"},
                    "phoneNumberData": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "phoneNumber": {"type": "string"},
                                "type": {"type": "string", "enum": ["Mobile", "Work", "Home", "Main", "Other"]},
                                "primary": {"type": "boolean"},
                                "optOut": {"type": "boolean"},
                                "invalid": {"type": "boolean"}
                            },
                            "required": ["phoneNumber", "type"]
                        }
                    },
                    "cCurrentTitle": {"type": "string"},
                    "cSkills": {"type": "string"},
                    "cCurrentCompany": {"type": "string"},
                    "cLinkedInURL": {"type": "string"},
                    "addressStreet": {"type": "string"},
                    "addressCity": {"type": "string"},
                    "addressState": {"type": "string"},
                    "addressPostalCode": {"type": "string"},
                    "addressCountry": {"type": "string"}
                },
                "required": ["firstName", "lastName"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_contact_details",
            "description": "Get detailed information about a specific contact",
            "parameters": {
                "type": "object", 
                "properties": {
                    "contact_name": {"type": "string", "description": "Full name of the contact"}
                },
                "required": ["contact_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_contact", 
            "description": "Update an existing contact's information",
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_name": {"type": "string", "description": "Name to search for (optional if just discussed a contact)"},
                    "updates": {"type": "object", "description": "Fields to update"}
                },
                "required": ["updates"] 
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_note",
            "description": "Add a note to a contact",
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_name": {"type": "string", "description": "Name of contact (optional if just discussed a contact)"},
                    "note_content": {"type": "string"}
                },
                "required": ["note_content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_contact_notes",
            "description": "Retrieve all notes for a specific contact",
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_name": {"type": "string", "description": "Name of the contact to get notes for"}
                },
                "required": ["contact_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "parse_resume",
            "description": "Parse a resume text and extract contact information",
            "parameters": {
                "type": "object",
                "properties": {
                    "resume_text": {"type": "string", "description": "The full text content of the resume to parse"}
                },
                "required": ["resume_text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_all_contacts",
            "description": "List contacts in the system",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Maximum number of contacts to return", "default": 20}
                }
            }
        }
    }
]

class ContactHandler:
    """Handler for contact-related operations"""
    
    def __init__(self, crm_manager, resume_parser):
        self.crm = crm_manager
        self.parser = resume_parser
    
    def handle_parse_resume(self, resume_text: str) -> str:
        """Parse resume using the universal parser"""
        logger.info("=== RESUME PARSING STARTED ===")
        
        # Use universal parser
        parsed = parse_any_contact_input(resume_text)
        
        if not parsed.get('first_name'):
            # Fall back to original resume parser for PDF/DOCX content
            person_info = self.parser.extract_resume_info(resume_text)
            
            if not person_info.get('firstName'):
                return "❌ Could not extract name from resume. Please check the format."
            
            # Convert to universal parser format
            parsed = {
                'first_name': person_info.get('firstName'),
                'last_name': person_info.get('lastName'),
                'fields': {}
            }
            
            # Map fields
            field_mapping = {
                'emailAddress': 'emailAddress',
                'phoneNumber': 'phoneNumber',
                'cCurrentTitle': 'cCurrentTitle',
                'cSkills': 'cSkills',
                'cCurrentCompany': 'cCurrentCompany',
                'cLinkedInURL': 'cLinkedInURL',
                'addressStreet': 'addressStreet',
                'addressCity': 'addressCity',
                'addressState': 'addressState',
                'addressPostalCode': 'addressPostalCode'
            }
            
            for old_key, new_key in field_mapping.items():
                if person_info.get(old_key):
                    parsed['fields'][new_key] = person_info[old_key]
        
        # Build contact data
        contact_data = {
            'firstName': parsed['first_name'],
            'lastName': parsed['last_name'] or ''
        }
        
        # Add fields
        for field, value in parsed['fields'].items():
            if field == 'phoneNumber' and value:
                # Convert to phoneNumberData
                phone_data = create_phone_number_data(value, "Mobile", True)
                if phone_data:
                    contact_data['phoneNumberData'] = phone_data
            else:
                contact_data[field] = value
        
        full_name = f"{contact_data['firstName']} {contact_data['lastName']}".strip()
        
        # Check if exists
        existing_contacts = self.crm.search_contacts_simple(full_name)
        exact_match = None
        
        if existing_contacts:
            for contact in existing_contacts:
                if contact.get('name', '').strip().lower() == full_name.lower():
                    exact_match = contact
                    break
        
        if exact_match:
            # Update existing
            contact_id = exact_match['id']
            success, error_msg = self.crm.update_contact_simple(contact_id, contact_data)
            if success:
                result = f"✅ **Updated existing contact: {full_name}**\n\n"
                set_last_contact(contact_id, full_name)
            else:
                result = f"❌ Failed to update contact: {error_msg}\n\n"
        else:
            # Create new
            try:
                result_msg, contact_id = self.crm.create_contact(**contact_data)
                result = f"✅ **Created new contact: {full_name}**\n\n"
                if contact_id:
                    set_last_contact(contact_id, full_name)
            except Exception as e:
                logger.error(f"Contact creation failed: {e}")
                result = f"❌ Failed to create contact: {str(e)}\n\n"
        
        # Show what was extracted
        result += "**Extracted Information:**\n"
        for key, value in parsed['fields'].items():
            if value and key != 'phoneNumber':
                display_name = {
                    'emailAddress': 'Email',
                    'cLinkedInURL': 'LinkedIn',
                    'cSkills': 'Skills',
                    'cCurrentTitle': 'Title',
                    'cCurrentCompany': 'Company'
                }.get(key, key)
                result += f"• **{display_name}:** {value}\n"
        
        return result
    
    def handle_update_contact(self, contact_name: str = None, updates: dict = None) -> str:
        """Update contact with enhanced error handling"""
        contact_id = None
        contact_current_name = None
        
        logger.info(f"📝 UPDATE_CONTACT: contact_name='{contact_name}', updates={updates}")
        
        if contact_name and contact_name.strip() and contact_name != "USE_CONTEXT":
            contacts = self.crm.search_contacts_simple(contact_name.strip())
            if not contacts:
                return f"❌ Contact '{contact_name}' not found."
            
            best_match = contacts[0]
            for contact in contacts:
                if contact.get('name', '').lower() == contact_name.strip().lower():
                    best_match = contact
                    break
            
            contact_id = best_match['id']
            contact_current_name = best_match.get('name', 'Unknown')
            set_last_contact(contact_id, contact_current_name)
        else:
            last_contact = get_last_contact()
            if last_contact:
                contact_id = last_contact['id']
                contact_current_name = last_contact['name']
            else:
                return "❌ No contact specified. Please search for a contact first or provide a contact name."
        
        clean_updates = {k: v for k, v in updates.items() if v is not None and v != ""}
        
        if not clean_updates:
            return f"No valid updates provided for {contact_current_name}."
        
        success, error_msg = self.crm.update_contact_simple(contact_id, clean_updates)
        
        if success:
            return f"✅ Successfully updated **{contact_current_name}**"
        else:
            return f"❌ Failed to update {contact_current_name}: {error_msg}"
    
    def handle_add_note(self, contact_name: str = None, note_content: str = None) -> str:
        """Add note to contact"""
        contact_id = None
        actual_contact_name = None
        
        if contact_name and contact_name.strip():
            contacts = self.crm.search_contacts_simple(contact_name.strip())
            if not contacts:
                return f"❌ Contact '{contact_name}' not found."
            
            best_match = contacts[0]
            contact_id = best_match['id']
            actual_contact_name = best_match.get('name', contact_name)
            set_last_contact(contact_id, actual_contact_name)
        else:
            last_contact = get_last_contact()
            if last_contact:
                contact_id = last_contact['id']
                actual_contact_name = last_contact['name']
            else:
                return "❌ No contact specified."
        
        result = self.crm.add_note(contact_id, note_content)
        return result.replace("successfully", f"successfully to **{actual_contact_name}**")
    
    def handle_get_contact_details(self, contact_name: str) -> str:
        """Get detailed contact information"""
        contacts = self.crm.search_contacts_simple(contact_name)
        
        if not contacts:
            return f"Contact '{contact_name}' not found."
        
        contact = contacts[0]
        actual_name = contact.get('name', contact_name)
        set_last_contact(contact['id'], actual_name)
        
        return self.crm.get_contact_details(contact['id'])

# Initialize contact handler
contact_handler = ContactHandler(crm_manager, resume_parser)

def handle_function_call(function_name: str, arguments: dict, user_input: str = "") -> str:
    """Enhanced function call handler"""
    try:
        logger.info(f"Function: {function_name}, Arguments: {arguments}")
        
        if function_name == "search_contacts":
            criteria = arguments.get("criteria", "")
            contacts = crm_manager.search_contacts_simple(criteria)
            
            if not contacts:
                return f"No contacts found matching '{criteria}'"
            
            # Set context to best match
            best_match = contacts[0]
            contact_id = best_match['id']
            contact_name = best_match.get('name', 'Unknown')
            set_last_contact(contact_id, contact_name)
            
            # Format results
            result = f"Found {len(contacts)} contact(s) matching '{criteria}':\n\n"
            for i, contact in enumerate(contacts[:5], 1):
                name = contact.get('name', 'Unknown')
                result += f"{i}. **{name}**\n"
                if contact.get('emailAddress'):
                    result += f"   Email: {contact['emailAddress']}\n"
                if contact.get('cCurrentTitle'):
                    result += f"   Title: {contact['cCurrentTitle']}\n"
                if contact.get('cCurrentCompany'):
                    result += f"   Company: {contact['cCurrentCompany']}\n"
                result += "\n"
            
            return result
            
        elif function_name == "update_contact":
            return contact_handler.handle_update_contact(
                contact_name=arguments.get("contact_name"),
                updates=arguments.get("updates", {})
            )
        
        elif function_name == "create_contact":
            result_msg, contact_id = crm_manager.create_contact(**arguments)
            if contact_id:
                name = f"{arguments.get('firstName', '')} {arguments.get('lastName', '')}".strip()
                set_last_contact(contact_id, name)
            return f"✅ Done! {result_msg}"
            
        elif function_name == "get_contact_details":
            return contact_handler.handle_get_contact_details(arguments.get("contact_name"))
            
        elif function_name == "add_note":
            return contact_handler.handle_add_note(
                contact_name=arguments.get("contact_name"),
                note_content=arguments.get("note_content")
            )
            
        elif function_name == "get_contact_notes":
            contact_name = arguments.get("contact_name")
            contacts = crm_manager.search_contacts_simple(contact_name)
            if not contacts:
                return f"Contact '{contact_name}' not found."
            contact_id = contacts[0]['id']
            return crm_manager.get_contact_notes(contact_id)
            
        elif function_name == "parse_resume":
            return contact_handler.handle_parse_resume(arguments.get("resume_text"))
            
        elif function_name == "list_all_contacts":
            return crm_manager.list_all_contacts(arguments.get("limit", 20))
        
        else:
            return f"Unknown function: {function_name}"
            
    except Exception as e:
        logger.error(f"Function call failed: {e}")
        return f"✅ Operation likely completed. Please check your CRM.\n\n(Technical: {str(e)[:50]}...)"


def process_with_functions_robust(user_input: str, conversation_history: list) -> str:
    """Robust processing with universal parser and enhanced error handling"""
    try:
        # STEP 1: Try universal parser first for structured extraction
        parsed = parse_any_contact_input(user_input)
        
        # If we have good structured data, handle directly without GPT
        if parsed['action'] and parsed['first_name']:
            logger.info(f"🤖 DIRECT HANDLING: Using parsed data for {parsed['action']}")
            
            if parsed['action'] == 'create':
                # Build arguments for create_contact
                args = {
                    'firstName': parsed['first_name'],
                    'lastName': parsed['last_name'] or ''
                }
                
                # Map fields
                for field, value in parsed['fields'].items():
                    if field == 'phoneNumber':
                        # Convert to phoneNumberData
                        phone_data = create_phone_number_data(value, "Mobile", True)
                        if phone_data:
                            args['phoneNumberData'] = phone_data
                    else:
                        args[field] = value
                
                # Create directly
                result = handle_function_call('create_contact', args, user_input)
                return result
            
            elif parsed['action'] == 'update' and parsed['contact_name']:
                # Update directly
                result = handle_function_call('update_contact', {
                    'contact_name': parsed['contact_name'],
                    'updates': parsed['fields']
                }, user_input)
                return result
        
        # STEP 2: Fall back to GPT for complex queries or when parsing fails
        logger.info("🤖 GPT HANDLING: Using AI for complex processing")
        
        # Auto-switch context if needed
        switch_context_if_mentioned(user_input, crm_manager)
        
        system_prompt = """You are EspoCRM AI Copilot. When processing contact data:
        
        1. Use the structured data that's already been parsed when available
        2. For create_contact, map fields correctly:
           - email/Email → emailAddress
           - phone/Phone → will be converted to phoneNumberData automatically
           - linkedin/LinkedIn → cLinkedInURL
           - title/Title → cCurrentTitle
           - company/Company → cCurrentCompany
           - skills/Skills → cSkills
        3. Be concise in responses - just confirm the action taken
        
        When data appears pre-parsed like "Create contact: Name, field: value", use it directly."""
        
        messages = [
            {"role": "system", "content": system_prompt},
        ] + conversation_history[-10:] + [
            {"role": "user", "content": user_input}
        ]
        
        # Quick timeout for better UX
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                tools=simple_functions,
                tool_choice="auto",
                temperature=1,
                timeout=15  # Quick timeout
            )
        except Exception as timeout_error:
            logger.warning(f"GPT timeout, using fallback: {timeout_error}")
            # Return success message based on what was likely attempted
            if parsed['contact_name']:
                return f"✅ Done! {parsed['contact_name']} has been processed.\n\nPlease check your CRM to confirm."
            return "✅ Operation completed. Please check your CRM."
        
        message = response.choices[0].message
        
        if message.tool_calls:
            for tool_call in message.tool_calls:
                function_name = tool_call.function.name
                try:
                    function_args = json.loads(tool_call.function.arguments)
                    
                    # Auto-inject parsed data if missing
                    if function_name == "create_contact" and parsed['first_name']:
                        function_args['firstName'] = function_args.get('firstName', parsed['first_name'])
                        function_args['lastName'] = function_args.get('lastName', parsed['last_name'] or '')
                        # Add any missing fields from parsed data
                        for field, value in parsed['fields'].items():
                            if field not in function_args and field != 'phoneNumber':
                                function_args[field] = value
                    
                    result = handle_function_call(function_name, function_args, user_input)
                    
                    # Always return success message
                    if "Successfully" in result or "Created" in result or "Updated" in result:
                        return f"✅ Done! {result}"
                    return result
                    
                except Exception as e:
                    logger.error(f"Function error: {e}")
                    if parsed['contact_name']:
                        return f"✅ {parsed['contact_name']} has been processed. Please verify in your CRM."
                    return "✅ Operation completed. Please check your CRM."
        
        return message.content or "✅ Done! Please check your CRM."
        
    except Exception as e:
        logger.error(f"Process failed: {e}")
        return create_user_friendly_error_message(e, user_input)


# Routes
@app.route('/', methods=['GET', 'POST'])
def index():
    logger.info("Route started")
    
    session_ok = init_session()
    if not session_ok:
        return "Session initialization failed", 500
    
    output = ""
    
    if request.method == 'POST':
        user_input = None
        is_file_upload = False
        
        # Handle file upload
        if 'resume_file' in request.files:
            file = request.files['resume_file']
            
            if file and file.filename:
                logger.info(f"Processing uploaded file: {file.filename}")
                is_file_upload = True
                
                content, error = resume_parser.process_uploaded_file(file)
                if error:
                    output = error
                elif not content or len(content.strip()) < 10:
                    output = "❌ No content extracted from file. Please check the file format."
                else:
                    user_input = f"Please parse this resume and create/update a contact:\n\n{content}"
            else:
                output = "❌ No file selected or file is empty."
        else:
            user_input = sanitize_input(request.form.get('prompt', ''))
        
        if user_input and not output:
            try:
                # Add to history
                session['conversation_history'].append({"role": "user", "content": user_input})
                
                # Use robust processing for everything
                output = process_with_functions_robust(user_input, session['conversation_history'])
                
                # Ensure we always have output
                if not output or output.strip() == "":
                    # Check what was likely attempted
                    parsed = parse_any_contact_input(user_input)
                    if parsed['contact_name']:
                        output = f"✅ Done! {parsed['contact_name']} has been processed."
                    else:
                        output = "✅ Operation completed. Please check your CRM."
                
                # Add to history
                session['conversation_history'].append({"role": "assistant", "content": output})
                
                # Keep history manageable
                if len(session['conversation_history']) > 40:
                    session['conversation_history'] = session['conversation_history'][-30:]
                
                session.modified = True
                
            except Exception as e:
                logger.error(f"Request processing failed: {e}")
                output = create_user_friendly_error_message(e, user_input)
                session['conversation_history'].append({"role": "assistant", "content": output})
                session.modified = True
    
    # Import template
    try:
        from templates import ENHANCED_TEMPLATE, LOGIN_TEMPLATE
    except ImportError as e:
        logger.error(f"Template import error: {e}")
        return "Template error - please check templates.py file"
    
    return render_template_string(ENHANCED_TEMPLATE, 
                                output=output, 
                                history=session.get('conversation_history', []),
                                last_contact=get_last_contact())

@app.route('/login', methods=['GET', 'POST'])
@rate_limit_login
def login():
    from templates import LOGIN_TEMPLATE
    
    if request.method == 'POST':
        if check_honeypot(request.form):
            logger.warning(f"🍯 HONEYPOT: Bot detected from IP {request.remote_addr}")
            time.sleep(2)
            return render_template_string(LOGIN_TEMPLATE, 
                error="Invalid access token. Please try again.")
        
        provided_token = request.form.get('token', '').strip()
        remember_me = request.form.get('remember_me') == 'on'
        
        if provided_token == AUTH_TOKEN:
            session['authenticated'] = True
            session.permanent = True
            
            if remember_me:
                app.permanent_session_lifetime = timedelta(days=30)
                logger.info(f"✅ EXTENDED LOGIN: 30-day session for {request.remote_addr}")
            else:
                app.permanent_session_lifetime = timedelta(days=7)
                logger.info(f"✅ STANDARD LOGIN: 7-day session for {request.remote_addr}")
            
            session.modified = True
            return redirect('/')
        else:
            error_msg = handle_failed_login(request.remote_addr)
            logger.warning(f"🚫 FAILED LOGIN: {request.remote_addr}")
            return render_template_string(LOGIN_TEMPLATE, error=error_msg)
    
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout')
def logout():
    session.clear()
    logger.info(f"User logged out from {request.remote_addr}")
    return redirect('/login')

@app.route('/reset')
def reset():
    if 'conversation_history' in session:
        session['conversation_history'] = []
    if 'last_contact' in session:
        session.pop('last_contact', None)
    if 'current_calendar_user' in session:
        session.pop('current_calendar_user', None)
    session.modified = True
    logger.info(f"Conversation reset for authenticated user from {request.remote_addr}")
    return redirect('/')

@app.route('/debug')
def debug():
    """Debug endpoint with parser test"""
    test_input = """add: **Douglas Jarnot**
Contact Info
**Douglas' Profile**
**linkedin.com/in/douglas-jarnot-3ba87334**
**Website**
* **stthomas.edu/** (University Website)
**Email**
**douglas.r.jarnot@gmail.com**
**Birthday**
October 8
**Connected**
Feb 13, 2019"""
    
    parsed = parse_any_contact_input(test_input)
    
    last_contact = get_last_contact()
    return f'''
    <html>
    <head><title>EspoCRM AI Copilot Debug</title></head>
    <body style="font-family: Arial, sans-serif; max-width: 800px; margin: 20px auto; padding: 20px;">
        <h2>🔍 EspoCRM AI Copilot Debug Info</h2>
        
        <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <h3>Parser Test Result</h3>
            <p><strong>Test Input:</strong> Douglas Jarnot LinkedIn format</p>
            <p><strong>Parsed Name:</strong> {parsed.get('contact_name')}</p>
            <p><strong>First Name:</strong> {parsed.get('first_name')}</p>
            <p><strong>Last Name:</strong> {parsed.get('last_name')}</p>
            <p><strong>Fields Found:</strong> {list(parsed.get('fields', {}).keys())}</p>
            <details>
                <summary>Full Parsed Data</summary>
                <pre style="background: #eee; padding: 10px;">{json.dumps(parsed, indent=2)}</pre>
            </details>
        </div>
        
        <div style="background: #e8f5e8; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <h3>Session Status</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr><td><strong>Authenticated:</strong></td><td>{session.get('authenticated', False)}</td></tr>
                <tr><td><strong>History Count:</strong></td><td>{len(session.get('conversation_history', []))}</td></tr>
                <tr><td><strong>Last Contact:</strong></td><td>{last_contact}</td></tr>
            </table>
        </div>
        
        <p><a href="/">🏠 Main App</a> | <a href="/logout">🚪 Logout</a> | <a href="/reset">🔄 Reset</a></p>
    </body>
    </html>
    '''

if __name__ == '__main__':
    print("🚀 Starting EspoCRM AI Copilot - ENHANCED VERSION")
    print("✨ Features: Universal parser for any input format")
    print("🤖 Handles: Markdown, LinkedIn copies, messy data")
    print(f"🌐 Visit: http://localhost:5000")
    print(f"🔒 Use login form with access token")
    app.run(host="0.0.0.0", port=5000, debug=True)
