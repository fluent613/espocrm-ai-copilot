MODEL_NAME = "gpt-5-mini"

# app.py
# Main Flask application for EspoCRM AI Copilot

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

# NEW: CONTEXT SWITCHING FUNCTIONS
def extract_contact_from_input(user_input: str) -> str:
    """Extract contact name from any user input - handles all patterns"""
    
    # Common patterns where users mention contacts
    patterns = [
        # Direct mentions with actions
        r"(?:add|update|note|notes|contact)\s+(?:to|for|about)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
        
        # Name followed by colon or action
        r"([A-Z][a-z]+\s+[A-Z][a-z]+)(?:\s*[:\-]|\s+profile|\s+info)",
        
        # Name followed by possessive
        r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'?s?\s+(?:profile|info|contact|notes?|phone|email|skills|address|company)",
        
        # "for/to/about [Name]"
        r"(?:for|to|about)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
        
        # Direct name mentions (first and last name)
        r"\b([A-Z][a-z]+\s+[A-Z][a-z]+)\b",
        
        # Single first names when clearly referring to a person
        r"(?:update|note|add|contact|call|email)\s+([A-Z][a-z]+)\b"
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, user_input)
        for match in matches:
            # Skip common false positives
            if match.lower() not in ['add this', 'add note', 'add contact', 'new contact', 'create contact', 'this contact']:
                logger.info(f"🔍 EXTRACT: Found contact mention '{match}' in input")
                return match.strip()
    
    return None

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

# ENHANCED Session Configuration - Much longer sessions, more persistent
app.config.update(
    SESSION_TYPE='filesystem',
    SESSION_FILE_DIR=str(SESSION_DIR),
    SESSION_PERMANENT=True,  # Make sessions permanent by default
    SESSION_USE_SIGNER=True,
    SESSION_KEY_PREFIX='copilot:',
    SESSION_FILE_THRESHOLD=500,  # Allow more session files
    SESSION_COOKIE_NAME='copilot_session',
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=False,  # Set True if using HTTPS
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(days=7)  # Stay logged in for 7 DAYS by default!
)

Session(app)

# Configuration - Use environment variables with reasonable defaults
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ESPO_API_KEY = os.getenv("ESPO_API_KEY")
ESPOCRM_URL = os.getenv("ESPOCRM_URL", "http://localhost:8080/api/v1")
AUTH_TOKEN = os.getenv("FLUENCY_AUTH_TOKEN")  # No default - must be set

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

# SIMPLIFIED SECURITY HEADERS - No iframe complexity
@app.after_request
def after_request(response):
    # Simple security headers
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['Content-Security-Policy'] = "frame-ancestors 'self'"
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response

# SECURE Authentication
@app.before_request
def require_auth_token():
    # Skip auth for login page and public routes
    if request.path in ['/login', '/reset', '/debug', '/test-search', '/test-json-where', '/test-phone', '/test-account-link']:
        return
    
    # Check if user is already authenticated via session
    if session.get('authenticated'):
        # Refresh session to prevent timeout
        session.permanent = True
        session.modified = True
        return
    
    # Check for token in URL parameters or headers (for API access)
    token = request.args.get('token') or request.headers.get('Authorization')
    
    if token == AUTH_TOKEN:
        session['authenticated'] = True
        session.permanent = True
        session.modified = True
        logger.info(f"✅ TOKEN AUTH: Direct token authentication from {request.remote_addr}")
        return
    
    # If no valid authentication found, redirect to login
    logger.info(f"🔒 AUTH REQUIRED: Redirecting {request.remote_addr} to login (Path: {request.path})")
    return redirect('/login')

# ENHANCED Function definitions for OpenAI - with notes, accounts, and contact-account linking
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
            "name": "search_notes",
            "description": "Search notes by content, optionally filtered by contact",
            "parameters": {
                "type": "object",
                "properties": {
                    "search_term": {"type": "string", "description": "Text to search for in notes"},
                    "contact_name": {"type": "string", "description": "Optional: limit search to specific contact"}
                },
                "required": ["search_term"]
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
    },
    {
        "type": "function",
        "function": {
            "name": "search_accounts",
            "description": "Search for accounts in the CRM",
            "parameters": {
                "type": "object",
                "properties": {
                    "criteria": {"type": "string", "description": "Search term (name, email, or website)"}
                },
                "required": ["criteria"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_account",
            "description": "Create a new account in the CRM",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Account name"},
                    "emailAddress": {"type": "string"},
                    "phoneNumber": {"type": "string"},
                    "website": {"type": "string"},
                    "industry": {"type": "string"},
                    "type": {"type": "string"},
                    "description": {"type": "string"},
                    "billingAddressStreet": {"type": "string"},
                    "billingAddressCity": {"type": "string"},
                    "billingAddressState": {"type": "string"},
                    "billingAddressPostalCode": {"type": "string"},
                    "billingAddressCountry": {"type": "string"},
                    "shippingAddressStreet": {"type": "string"},
                    "shippingAddressCity": {"type": "string"},
                    "shippingAddressState": {"type": "string"},
                    "shippingAddressPostalCode": {"type": "string"},
                    "shippingAddressCountry": {"type": "string"},
                    "sicCode": {"type": "string"}
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_account_details",
            "description": "Get detailed information about a specific account",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_name": {"type": "string", "description": "Name of the account"}
                },
                "required": ["account_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_account",
            "description": "Update an existing account's information",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_name": {"type": "string", "description": "Name of account to update"},
                    "updates": {"type": "object", "description": "Fields to update"}
                },
                "required": ["account_name", "updates"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_all_accounts",
            "description": "List accounts in the system",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Maximum number of accounts to return", "default": 50}
                }
            }
        }
    },
    # Contact-Account Relationship Functions
    {
        "type": "function",
        "function": {
            "name": "link_contact_to_account",
            "description": "Link a contact to an account (set as primary account or add to accounts collection)",
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_name": {"type": "string", "description": "Name of the contact to link"},
                    "account_name": {"type": "string", "description": "Name of the account to link to"},
                    "primary": {"type": "boolean", "description": "Set as primary account (default: true)", "default": True}
                },
                "required": ["contact_name", "account_name"]
            }
        }
    },
    {
        "type": "function", 
        "function": {
            "name": "unlink_contact_from_account",
            "description": "Remove contact-account relationship",
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_name": {"type": "string", "description": "Name of the contact"},
                    "account_name": {"type": "string", "description": "Name of account to remove from (optional - if not provided, clears primary account)"}
                },
                "required": ["contact_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_contact_accounts", 
            "description": "Get all accounts associated with a contact",
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_name": {"type": "string", "description": "Name of the contact"}
                },
                "required": ["contact_name"]
            }
        }
    },
    # Calendar Functions
    {
        "type": "function",
        "function": {
            "name": "get_calendar_events",
            "description": "Get calendar events for a user",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_name": {"type": "string", "description": "Name of user whose calendar to show"},
                    "date_start": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                    "date_end": {"type": "string", "description": "End date (YYYY-MM-DD)"}
                }
            }
        }
    },
    {
        "type": "function", 
        "function": {
            "name": "create_calendar_event",
            "description": "Create a calendar event",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Event name"},
                    "date_start": {"type": "string", "description": "Start datetime (YYYY-MM-DD HH:MM:SS)"},
                    "date_end": {"type": "string", "description": "End datetime (YYYY-MM-DD HH:MM:SS)"},
                    "user_name": {"type": "string", "description": "User to assign event to"},
                    "description": {"type": "string", "description": "Event description"},
                    "contact_id": {"type": "string", "description": "Contact ID if meeting with contact"}
                },
                "required": ["name", "date_start", "date_end"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_availability",
            "description": "Check user availability for a specific date",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_name": {"type": "string", "description": "Name of user to check availability for"},
                    "date": {"type": "string", "description": "Date to check (YYYY-MM-DD)"}
                },
                "required": ["user_name", "date"]
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
        """Parse resume and create/update contact - FIXED to handle missing phone numbers"""
        logger.info("=== RESUME PARSING STARTED ===")
        
        # Clear any existing contact context
        session.pop('last_contact', None)
        session.modified = True
        
        person_info = self.parser.extract_resume_info(resume_text)
        logger.info(f"Extracted person info: {person_info}")
        
        if not person_info.get('firstName'):
            return "❌ Could not extract name from resume. Please check the format."
        
        full_name = f"{person_info.get('firstName', '')} {person_info.get('lastName', '')}".strip()
        
        # Prepare contact data - CRITICAL: Handle both phoneNumber and _phoneDisplay
        contact_data = {}
        phone_status = ""
        
        logger.info(f"🔍 PHONE DEBUG: Starting phone processing...")
        logger.info(f"🔍 PHONE DEBUG: person_info keys: {list(person_info.keys())}")
        logger.info(f"🔍 PHONE DEBUG: phoneNumber='{person_info.get('phoneNumber')}', _phoneDisplay='{person_info.get('_phoneDisplay')}'")
        
        # Process all fields EXCEPT phone fields first
        for key, value in person_info.items():
            if value and str(value).strip() and key not in ['phoneNumber', '_phoneDisplay']:
                contact_data[key] = str(value).strip()
                logger.info(f"🔍 PROCESSING: Added {key}='{value}' to contact_data")
        
        # Now handle phone separately and ONLY add phoneNumberData
        phone_value = person_info.get('phoneNumber') or person_info.get('_phoneDisplay')
        if phone_value:
            logger.info(f"🔍 PHONE DEBUG: Found phone value: '{phone_value}'")
            digits_only = re.sub(r'[^\d]', '', str(phone_value))
            logger.info(f"🔍 PHONE DEBUG: Digits only: '{digits_only}' (length: {len(digits_only)})")
            
            if len(digits_only) >= 10:
                phone_data = create_phone_number_data(phone_value, "Mobile", True)
                if phone_data:
                    contact_data['phoneNumberData'] = phone_data
                    phone_status = f"• **Phone:** {phone_value} ✅\n"
                    logger.info(f"✅ PHONE DEBUG: Successfully created phoneNumberData: {phone_data}")
                else:
                    phone_status = f"• **Phone:** {phone_value} ⚠️ (format error)\n"
                    logger.error(f"❌ PHONE DEBUG: Failed to create phoneNumberData from '{phone_value}'")
            else:
                phone_status = f"• **Phone:** {phone_value} ⚠️ (too short, skipped)\n"
                logger.warning(f"⚠️ PHONE DEBUG: Phone too short: '{phone_value}' ({len(digits_only)} digits)")
        else:
            logger.info(f"🔍 PHONE DEBUG: No phone value found in person_info")
        
        # CRITICAL: Final verification - absolutely NO phoneNumber field allowed
        if 'phoneNumber' in contact_data:
            logger.error(f"🚨 CRITICAL ERROR: phoneNumber field found in contact_data - REMOVING IT!")
            del contact_data['phoneNumber']
        
        logger.info(f"🔍 FINAL contact_data keys: {list(contact_data.keys())}")
        logger.info(f"🔍 FINAL contact_data: {contact_data}")
        
        # Check if contact already exists
        existing_contacts = self.crm.search_contacts_simple(full_name)
        exact_match = None
        
        if existing_contacts:
            for contact in existing_contacts:
                contact_name = contact.get('name', '').strip().lower()
                if contact_name == full_name.lower():
                    exact_match = contact
                    break
        
        if exact_match:
            # Update existing contact
            contact_id = exact_match['id']
            success, error_msg = self.crm.update_contact_simple(contact_id, contact_data)
            if success:
                result = f"✅ **Updated existing contact: {full_name}**\n\n"
                set_last_contact(contact_id, full_name)
            else:
                result = f"❌ Failed to update contact: {error_msg}\n\n"
        else:
            # Create new contact
            try:
                result_msg, contact_id = self.crm.create_contact(**contact_data)
                result = result_msg + "\n\n"
                if contact_id:
                    set_last_contact(contact_id, full_name)
            except Exception as e:
                logger.error(f"Contact creation failed: {e}")
                result = f"❌ Failed to create contact: {str(e)}\n\n"
        
        # Show extracted information
        result += "**Extracted Information:**\n"
        for key, value in person_info.items():
            if value and key not in ['phoneNumber']:  # Don't show raw phoneNumber (will show processed version)
                result += f"• **{key.title()}:** {value}\n"
        
        # Add phone status separately if we have one
        if phone_status:
            result += phone_status
        
        return result
    
    def handle_update_contact(self, contact_name: str = None, updates: dict = None) -> str:
        """Update contact using explicit name or context - ENHANCED with auto context switching"""
        contact_id = None
        contact_current_name = None
        
        logger.info(f"🔍 UPDATE_CONTACT: contact_name='{contact_name}', updates={updates}")
        
        if contact_name and contact_name.strip() and contact_name != "USE_CONTEXT":
            # Explicit contact name provided (not pronoun reference)
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
            logger.info(f"✅ UPDATE_CONTACT: Found explicit contact {contact_current_name} (ID: {contact_id})")
        else:
            # Use current context (either no name provided or USE_CONTEXT)
            last_contact = get_last_contact()
            if last_contact:
                contact_id = last_contact['id']
                contact_current_name = last_contact['name']
                logger.info(f"✅ UPDATE_CONTACT: Using context contact {contact_current_name} (ID: {contact_id})")
            else:
                return "❌ No contact specified. Please search for a contact first or provide a contact name."
        
        clean_updates = {k: v for k, v in updates.items() if v is not None and v != ""}
        
        if not clean_updates:
            return f"No valid updates provided for {contact_current_name}."
        
        success, error_msg = self.crm.update_contact_simple(contact_id, clean_updates)
        
        if success:
            display_updates = []
            for k, v in clean_updates.items():
                if k == 'phoneNumberData':
                    continue  # Skip displaying phoneNumberData structure
                display_name = {
                    'phoneNumber': 'Phone', 'emailAddress': 'Email', 
                    'cLinkedInURL': 'LinkedIn', 'cSkills': 'Skills',
                    'cCurrentTitle': 'Title', 'addressStreet': 'Street Address',
                    'addressCity': 'City', 'addressState': 'State',
                    'addressPostalCode': 'ZIP Code', 'cCurrentCompany': 'Company'
                }.get(k, k)
                display_updates.append(f"{display_name}: {v}")
            
            update_summary = ", ".join(display_updates)
            return f"✅ Successfully updated **{contact_current_name}**\n\nUpdated fields: {update_summary}"
        else:
            return f"❌ Failed to update {contact_current_name}\n\n**Error Details:** {error_msg}"
    
    def handle_add_note(self, contact_name: str = None, note_content: str = None) -> str:
        """Add note to contact - ENHANCED with automatic context switching"""
        contact_id = None
        actual_contact_name = None
        
        logger.info(f"🎯 ADD_NOTE: contact_name='{contact_name}', note_content preview='{note_content[:50] if note_content else None}...'")
        
        if contact_name and contact_name.strip():
            # EXPLICIT contact name provided - ALWAYS use this, ignore context
            logger.info(f"🎯 EXPLICIT NOTE TARGET: Searching for '{contact_name}'")
            contacts = self.crm.search_contacts_simple(contact_name.strip())
            if not contacts:
                return f"❌ Contact '{contact_name}' not found."
            
            # Find best match
            best_match = contacts[0]
            for contact in contacts:
                contact_full_name = contact.get('name', '').strip()
                if contact_full_name.lower() == contact_name.strip().lower():
                    best_match = contact
                    break
                # Also check if search term matches part of the name
                elif contact_name.lower() in contact_full_name.lower():
                    best_match = contact
                    break
            
            contact_id = best_match['id']
            actual_contact_name = best_match.get('name', contact_name)
            
            # Update context to this contact
            set_last_contact(contact_id, actual_contact_name)
            logger.info(f"✅ EXPLICIT NOTE: Set target to {actual_contact_name} (ID: {contact_id})")
            
        else:
            # No explicit name - use context
            last_contact = get_last_contact()
            if last_contact:
                contact_id = last_contact['id']
                actual_contact_name = last_contact['name']
                logger.info(f"📝 CONTEXT NOTE: Using {actual_contact_name}")
            else:
                return "❌ No contact specified. Please search for a contact first or specify a contact name."
        
        logger.info(f"🎯 FINAL TARGET: Adding note to {actual_contact_name} (ID: {contact_id})")
        
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
    """Enhanced function call handler with automatic context switching"""
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
            logger.info(f"🎯 SEARCH: Set last_contact to {contact_name} (ID: {contact_id})")
            
            # Format results (keeping original emojis in search results since they're functional)
            result = f"Found {len(contacts)} contact(s) matching '{criteria}':\n\n"
            for i, contact in enumerate(contacts[:5], 1):
                name = contact.get('name', 'Unknown')
                result += f"{i}. **{name}**\n"
                if contact.get('emailAddress'):
                    result += f"   📧 Email: {contact['emailAddress']}\n"
                
                # Handle phoneNumberData structure
                phone_data = contact.get('phoneNumberData')
                if phone_data and isinstance(phone_data, list) and len(phone_data) > 0:
                    primary_phone = None
                    mobile_phone = None
                    for phone_entry in phone_data:
                        if phone_entry.get('primary'):
                            primary_phone = phone_entry
                            break
                        elif phone_entry.get('type') == 'Mobile':
                            mobile_phone = phone_entry
                    
                    phone_to_show = primary_phone or mobile_phone or phone_data[0]
                    if phone_to_show:
                        phone_num = phone_to_show.get('phoneNumber', '')
                        phone_type = phone_to_show.get('type', '')
                        result += f"   📱 Phone: {phone_num} ({phone_type})\n"
                
                if contact.get('cCurrentTitle'):
                    result += f"   💼 Title: {contact['cCurrentTitle']}\n"
                if contact.get('cLinkedInURL'):
                    result += f"   🔗 LinkedIn: {contact['cLinkedInURL']}\n"
                if contact.get('cSkills'):
                    result += f"   🛠️ Skills: {contact['cSkills']}\n"
                    
                # Display address if available
                address_parts = []
                if contact.get('addressStreet'):
                    address_parts.append(contact['addressStreet'])
                if contact.get('addressCity'):
                    address_parts.append(contact['addressCity'])
                if contact.get('addressState'):
                    address_parts.append(contact['addressState'])
                if contact.get('addressPostalCode'):
                    address_parts.append(contact['addressPostalCode'])
                
                if address_parts:
                    result += f"   🏠 Address: {', '.join(address_parts)}\n"
                
                result += "\n"
            
            if len(contacts) > 5:
                result += f"... and {len(contacts) - 5} more contacts.\n\n"
            
            result += f"💡 I'm focusing on **{contact_name}** for any follow-up actions."
            return result
            
        elif function_name == "update_contact":
            contact_name_arg = arguments.get("contact_name")
            updates_arg = arguments.get("updates", {})
            
            # AUTO-DETECT: If updating "company" field, check if it's an actual Account entity
            if "company" in updates_arg:
                company_name = updates_arg["company"]
                logger.info(f"🔍 COMPANY UPDATE: Checking if '{company_name}' is an Account entity")
                
                # Search for this company as an Account
                accounts = crm_manager.search_accounts(company_name)
                if accounts:
                    # Found matching account - use account linking instead
                    account_match = accounts[0]
                    account_name = account_match.get('name', company_name)
                    logger.info(f"🔗 AUTO-LINK: Found Account '{account_name}', switching to link_contact_to_account")
                    
                    # Remove company from updates and fix field name for any remaining
                    updates_without_company = {}
                    for k, v in updates_arg.items():
                        if k != "company":
                            # Fix common field name issues
                            if k == "title":
                                updates_without_company["cCurrentTitle"] = v
                            elif k == "skills":
                                updates_without_company["cSkills"] = v
                            elif k == "linkedin":
                                updates_without_company["cLinkedInURL"] = v
                            else:
                                updates_without_company[k] = v
                    
                    # Link to account
                    link_result = crm_manager.link_contact_to_account(contact_name_arg, account_name, primary=True)
                    
                    # If there are other updates, apply them too
                    if updates_without_company:
                        logger.info(f"🔧 ADDITIONAL UPDATES: Applying remaining updates: {updates_without_company}")
                        update_result = contact_handler.handle_update_contact(
                            contact_name=contact_name_arg,
                            updates=updates_without_company
                        )
                        return f"{link_result}\n\n{update_result}"
                    else:
                        return link_result
                else:
                    # No matching account found - treat as company text field with correct field name
                    logger.info(f"📝 TEXT COMPANY: No Account found for '{company_name}', treating as text field")
                    updates_arg["cCurrentCompany"] = updates_arg.pop("company")
            
            # Fix other common field name issues
            field_fixes = {
                "title": "cCurrentTitle",
                "skills": "cSkills", 
                "linkedin": "cLinkedInURL"
            }
            for old_field, new_field in field_fixes.items():
                if old_field in updates_arg:
                    updates_arg[new_field] = updates_arg.pop(old_field)
                    logger.info(f"🔧 FIELD FIX: Renamed '{old_field}' to '{new_field}'")
            
            # Auto-inject contact name if missing but mentioned in input
            if not contact_name_arg and user_input:
                mentioned = extract_contact_from_input(user_input)
                if mentioned:
                    contact_name_arg = mentioned
                    logger.info(f"🔧 AUTO-INJECTED contact_name for update: {mentioned}")
            
            return contact_handler.handle_update_contact(
                contact_name=contact_name_arg,
                updates=updates_arg
            )
        
        elif function_name == "create_contact":
            # GUARDRAIL 1: Prevent accidental contact creation when user wants to add notes
            note_keywords = r'\b(note|notes|ad note|add note|recap|summary|log|comment|memo|follow.?up|remember|jot|write)\b'
            if re.search(note_keywords, user_input, re.IGNORECASE):
                logger.warning(f"🚫 GUARDRAIL: Blocked create_contact for note-like input: {user_input[:100]}")
                # Try to auto-route to add_note instead
                mentioned_contact = extract_contact_from_input(user_input)
                if mentioned_contact:
                    # Extract the note content (everything after the contact name)
                    note_content = user_input
                    # Remove common prefixes
                    for prefix in ["ad note to", "add note to", "note for", "add to", "log for"]:
                        if prefix in user_input.lower():
                            parts = user_input.lower().split(prefix, 1)
                            if len(parts) > 1:
                                remaining = parts[1].strip()
                                # Remove the contact name from the beginning
                                if remaining.lower().startswith(mentioned_contact.lower()):
                                    note_content = remaining[len(mentioned_contact):].strip()
                                    # Remove leading colon or punctuation
                                    note_content = re.sub(r'^[:\-\s]+', '', note_content)
                                    break
                    
                    logger.info(f"🔄 AUTO-ROUTING: Converting to add_note for {mentioned_contact}")
                    return contact_handler.handle_add_note(mentioned_contact, note_content)
                else:
                    return "⚠️ It looks like you want to add a note. Please specify which contact: 'add note to [Name]: your note content'"
            
            # GUARDRAIL 2: Check for obvious placeholder names
            first_name = arguments.get('firstName', '').lower()
            last_name = arguments.get('lastName', '').lower()
            
            if first_name in ['contact', 'person', 'unknown', 'user'] or last_name in ['contact', 'person', 'unknown', 'user']:
                logger.warning(f"🚫 GUARDRAIL: Placeholder names detected: {first_name} {last_name}")
                return "⚠️ Cannot create contact with placeholder names. Please provide real first and last names."
            
            # OPTIONAL: Suggest adding more info if contact seems minimal (but don't block it)
            email = arguments.get('emailAddress', '')
            phone_data = arguments.get('phoneNumberData', [])
            skills = arguments.get('cSkills', '')
            company = arguments.get('cCurrentCompany', '')
            title = arguments.get('cCurrentTitle', '')
            
            has_additional_info = any([
                email and '@' in email,
                phone_data,
                skills and len(skills) > 3,
                company and len(company) > 2,
                title and len(title) > 2
            ])
            
            # All guardrails passed - proceed with creation
            result_msg, contact_id = crm_manager.create_contact(**arguments)
            if contact_id:
                name = f"{arguments.get('firstName', '')} {arguments.get('lastName', '')}".strip()
                set_last_contact(contact_id, name)
                logger.info(f"🎯 CREATE_CONTACT: Set context to newly created contact: {name} (ID: {contact_id})")
                
                # Friendly suggestion if minimal info
                if not has_additional_info and "✅ Successfully created contact:" in result_msg:
                    result_msg += "\n\n💡 *Tip: You can add more details like email, phone, company, or skills by saying 'update [name]' or 'add note to [name]'*"
            
            return result_msg
        
            
        elif function_name == "get_contact_details":
            return contact_handler.handle_get_contact_details(arguments.get("contact_name"))
            
        elif function_name == "add_note":
            contact_name_arg = arguments.get("contact_name")
            note_content_arg = arguments.get("note_content")
            
            # Auto-inject contact name if missing but mentioned in input
            if not contact_name_arg and user_input:
                mentioned = extract_contact_from_input(user_input)
                if mentioned:
                    contact_name_arg = mentioned
                    logger.info(f"🔧 AUTO-INJECTED contact_name for note: {mentioned}")
            
            return contact_handler.handle_add_note(
                contact_name=contact_name_arg,
                note_content=note_content_arg
            )
            
        elif function_name == "get_contact_notes":
            contact_name = arguments.get("contact_name")
            contacts = crm_manager.search_contacts_simple(contact_name)
            if not contacts:
                return f"Contact '{contact_name}' not found."
            contact_id = contacts[0]['id']
            return crm_manager.get_contact_notes(contact_id)
            
        elif function_name == "search_notes":
            return crm_manager.search_notes(
                search_term=arguments.get("search_term"),
                contact_name=arguments.get("contact_name")
            )
            
        elif function_name == "parse_resume":
            return contact_handler.handle_parse_resume(arguments.get("resume_text"))
            
        elif function_name == "list_all_contacts":
            return crm_manager.list_all_contacts(arguments.get("limit", 20))
        
        elif function_name == "search_accounts":
            criteria = arguments.get("criteria", "")
            accounts = crm_manager.search_accounts(criteria)
            
            if not accounts:
                return f"No accounts found matching '{criteria}'"
            
            result = f"Found {len(accounts)} account(s) matching '{criteria}':\n\n"
            for i, account in enumerate(accounts[:5], 1):
                name = account.get('name', 'Unknown')
                result += f"{i}. **{name}**\n"
                if account.get('emailAddress'):
                    result += f"   📧 Email: {account['emailAddress']}\n"
                if account.get('phoneNumber'):
                    result += f"   📱 Phone: {account['phoneNumber']}\n"
                if account.get('website'):
                    result += f"   🌐 Website: {account['website']}\n"
                if account.get('industry'):
                    result += f"   🏭 Industry: {account['industry']}\n"
                if account.get('billingAddressCity') and account.get('billingAddressState'):
                    result += f"   📍 Location: {account['billingAddressCity']}, {account['billingAddressState']}\n"
                result += "\n"
            
            if len(accounts) > 5:
                result += f"... and {len(accounts) - 5} more accounts.\n"
            
            return result
            
        elif function_name == "create_account":
            result_msg, account_id = crm_manager.create_account(**arguments)
            return result_msg
            
        elif function_name == "get_account_details":
            account_name = arguments.get("account_name")
            accounts = crm_manager.search_accounts(account_name)
            if not accounts:
                return f"Account '{account_name}' not found."
            account_id = accounts[0]['id']
            return crm_manager.get_account_details(account_id)
            
        elif function_name == "update_account":
            account_name = arguments.get("account_name")
            updates = arguments.get("updates", {})
            
            accounts = crm_manager.search_accounts(account_name)
            if not accounts:
                return f"Account '{account_name}' not found."
            
            account_id = accounts[0]['id']
            success, error_msg = crm_manager.update_account(account_id, updates)
            
            if success:
                display_updates = [f"{k}: {v}" for k, v in updates.items()]
                return f"✅ Successfully updated **{account_name}**\n\nUpdated fields: {', '.join(display_updates)}"
            else:
                return f"❌ Failed to update {account_name}: {error_msg}"
            
        elif function_name == "list_all_accounts":
            return crm_manager.list_all_accounts(arguments.get("limit", 50))
        
        # Contact-Account Relationship Handlers
        elif function_name == "link_contact_to_account":
            contact_name = arguments.get("contact_name")
            account_name = arguments.get("account_name") 
            primary = arguments.get("primary", True)
            return crm_manager.link_contact_to_account(contact_name, account_name, primary)

        elif function_name == "unlink_contact_from_account":
            contact_name = arguments.get("contact_name")
            account_name = arguments.get("account_name")
            return crm_manager.unlink_contact_from_account(contact_name, account_name)

        elif function_name == "get_contact_accounts":
            contact_name = arguments.get("contact_name")
            return crm_manager.get_contact_accounts(contact_name)
        
        elif function_name == "get_calendar_events":
            user_name = arguments.get("user_name")
            date_start = arguments.get("date_start")
            date_end = arguments.get("date_end")
            
            # Remember user choice for this session
            if user_name:
                set_current_calendar_user(user_name)
            
            return crm_manager.get_calendar_events(user_name, date_start, date_end)
        
        elif function_name == "create_calendar_event":
            name = arguments.get("name")
            date_start = arguments.get("date_start")
            date_end = arguments.get("date_end")
            user_name = arguments.get("user_name")
            description = arguments.get("description")
            contact_id = arguments.get("contact_id")
            
            # Use remembered user if no user specified
            if not user_name:
                user_name = get_current_calendar_user()
            
            # Remember user choice for this session
            if user_name:
                set_current_calendar_user(user_name)
            
            return crm_manager.create_calendar_event(name, date_start, date_end, user_name, description, contact_id)
        
        elif function_name == "get_user_availability":
            user_name = arguments.get("user_name")
            date = arguments.get("date")
            
            # Remember user choice for this session
            if user_name:
                set_current_calendar_user(user_name)
            
            return crm_manager.get_user_availability(user_name, date)
        
        else:
            return f"Unknown function: {function_name}"
            
    except Exception as e:
        logger.error(f"Function call failed: {e}")
        return f"Error executing {function_name}: {str(e)}"

def process_with_functions(user_input: str, conversation_history: list) -> str:
    """Process input with automatic context switching and enhanced function calling"""
    try:
        # STEP 1: AUTO-SWITCH CONTEXT if contact mentioned
        context_switched = switch_context_if_mentioned(user_input, crm_manager)
        if context_switched:
            current_contact = get_last_contact()
            logger.info(f"🎯 AUTO-SWITCHED to: {current_contact['name'] if current_contact else 'None'}")
        
        # STEP 2: Enhanced system prompt with explicit context handling
        system_prompt = """You are EspoCRM AI Copilot, an intelligent CRM assistant that enhances EspoCRM with AI capabilities.
        
        CRITICAL: DISTINGUISH BETWEEN ADDING NOTES vs CREATING CONTACTS
        
        ADD NOTE PATTERNS (use add_note function):
        - ANY variation of "add/note/log/recap/memo" + contact name + content
        - Examples: "add note to John:", "ad note to John:", "note for John:", "log this for John:", "add to John's file:"
        - ALWAYS use add_note(contact_name="[NAME]", note_content="...") for these patterns
        - Look for: note, notes, ad note, add note, log, recap, memo, comment, follow-up, remember
        
        CREATE CONTACT PATTERNS (use create_contact function):
        - ONLY when explicitly asked to "create contact", "add contact", "new contact", "add this person"
        - ONLY when parsing resume content or structured contact information
        - NEVER use create_contact if the input contains note/log/recap keywords
        
        CONTACT UPDATE PATTERNS (use update_contact function):
        - "[NAME]'s [field] is [value]"
        - "update [NAME]:" followed by field updates
        - "change [NAME]'s [field] to [value]"
        
        ACCOUNT ASSOCIATION RULES:
        - When user says "associate [CONTACT] with [ACCOUNT]" or "link [CONTACT] to [ACCOUNT]" → use link_contact_to_account function
        - When user says "[CONTACT] works at [COMPANY]" → First search if COMPANY exists as Account entity, if yes use link_contact_to_account, else use update_contact with cCurrentCompany
        - When setting company as text field only → use update_contact with cCurrentCompany field (not "company")
        - ALWAYS search for the account first before deciding between link_contact_to_account vs update_contact

        CORRECT FIELD NAMES for update_contact:
        - Company: cCurrentCompany (not "company") 
        - Current Title: cCurrentTitle (not "title")
        - Skills: cSkills (not "skills") 
        - LinkedIn: cLinkedInURL (not "linkedin")

        EXAMPLES:
        ✅ CORRECT: "associate Jeremy with Eleven" → link_contact_to_account(contact_name="Jeremy Wolfe", account_name="Eleven")
        ✅ CORRECT: "Jeremy works at Eleven" → search_accounts("Eleven") first, then link_contact_to_account if found
        ❌ WRONG: "associate Jeremy with Eleven" → update_contact(updates={"company":"Eleven"})
        
        CONTEXT SWITCHING RULES:
        - When user mentions ANY contact name, ALWAYS use that contact explicitly in function calls
        - Extract names from patterns like "John Smith", "John", "Smith", even with typos
        - For ambiguous inputs, prefer add_note over create_contact
        
        EXAMPLES OF CORRECT FUNCTION SELECTION:
        ❌ WRONG: "Ad this note to Brendan: follow up" → create_contact
        ✅ CORRECT: "Ad this note to Brendan: follow up" → add_note(contact_name="Brendan", note_content="follow up")
        
        ❌ WRONG: "note for Spencer: he does AI" → create_contact  
        ✅ CORRECT: "note for Spencer: he does AI" → add_note(contact_name="Spencer", note_content="he does AI")
        
        ✅ CORRECT: "create contact John Smith with email john@test.com" → create_contact
        ✅ CORRECT: "add new contact Sarah Johnson" → create_contact
        
        NEVER CREATE CONTACTS ACCIDENTALLY - when in doubt, ask for clarification!
        
        CRITICAL CONTEXT SWITCHING RULES:
        - When user mentions ANY contact name (first+last or just first name), ALWAYS use that contact explicitly in function calls
        - For "add note to [NAME]:" → add_note(contact_name="[NAME]", note_content="...")
        - For "add notes to [NAME]:" → add_note(contact_name="[NAME]", note_content="...")
        - For "update [NAME]:" → update_contact(contact_name="[NAME]", updates={...})
        - For "[NAME]'s phone is..." → update_contact(contact_name="[NAME]", updates={"phoneNumber": "..."})
        - For "note for [NAME]:" → add_note(contact_name="[NAME]", note_content="...")
        - NEVER rely on context when an explicit name is mentioned in the input
        
        CRITICAL RULES FOR CONTACT CREATION vs UPDATES:
        - When user says "add this contact", "add contact", "create contact", "new contact", "add this person" → ALWAYS use create_contact function
        - When user provides contact info WITHOUT a clear "add" keyword and we have a current contact in context → use update_contact function
        - When user says "update [SPECIFIC NAME]" → use update_contact with that contact_name
        - NEVER confuse adding new contacts with updating existing ones!
        
        ALWAYS extract and pass the contact_name parameter when a name is mentioned."""

        messages = [
            {"role": "system", "content": system_prompt},
        ] + conversation_history[-10:] + [
            {"role": "user", "content": user_input}
        ]
        
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            tools=simple_functions,
            tool_choice="auto",
            temperature=1,
            timeout=30
        )
        
        message = response.choices[0].message
        
        if message.tool_calls:
            # Execute function calls
            messages.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                    } for tc in message.tool_calls
                ]
            })
            
            for tool_call in message.tool_calls:
                function_name = tool_call.function.name
                try:
                    function_args = json.loads(tool_call.function.arguments)
                    
                    # STEP 3: Auto-inject contact name if missing but mentioned in input
                    if function_name in ["add_note", "update_contact"] and not function_args.get("contact_name"):
                        mentioned_contact = extract_contact_from_input(user_input)
                        if mentioned_contact:
                            function_args["contact_name"] = mentioned_contact
                            logger.info(f"🔧 AUTO-INJECTED contact_name: {mentioned_contact}")
                    
                    result = handle_function_call(function_name, function_args, user_input)
                    
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": result
                    })
                except Exception as e:
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": f"Error: {str(e)}"
                    })
            
            # Get final response
            final_response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                temperature=1,
                timeout=30
            )
            
            return final_response.choices[0].message.content
        else:
            return message.content
        
    except Exception as e:
        logger.error(f"Process with functions failed: {e}")
        return f"❌ Error processing request: {str(e)}"

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
                    logger.error(f"📄 FILE UPLOAD ERROR: {error}")
                elif not content or len(content.strip()) < 10:
                    output = "❌ No content extracted from file. Please check the file format."
                    logger.error(f"📄 FILE CONTENT TOO SHORT: {len(content) if content else 0} characters")
                else:
                    logger.info(f"📄 FILE CONTENT LENGTH: {len(content)} characters")
                    logger.info(f"📄 FILE CONTENT PREVIEW: {content[:200]}...")
                    user_input = f"Please parse this resume and create/update a contact:\n\n{content}"
            else:
                output = "❌ No file selected or file is empty."
                logger.warning("📄 FILE UPLOAD: No file or empty filename")
        else:
            user_input = sanitize_input(request.form.get('prompt', ''))
        
        if user_input and not output:  # Only process if we have input and no error from file upload
            try:
                # Add user message to history
                session['conversation_history'].append({"role": "user", "content": user_input})
                
                # Check for resume content (either uploaded file or EXPLICIT resume parsing requests)
                is_resume = is_file_upload or any(keyword in user_input.lower() for keyword in [
                    'parse this resume', 'please parse this resume', 'extract from resume',
                    'resume parsing', 'parse resume content', 'create contact from resume'
                ])
                
                # Check for explicit "add" or "create" keywords
                is_add_request = any(keyword in user_input.lower() for keyword in [
                    'add this contact', 'add contact', 'create contact', 'new contact',
                    'add this person', 'create this contact', 'add new contact'
                ])
                
                logger.info(f"🔍 PROCESSING: is_file_upload={is_file_upload}, is_resume={is_resume}, is_add_request={is_add_request}")
                
                if is_resume:
                    # Handle resume parsing WITHOUT context switching (resume contains names we don't want to switch to)
                    logger.info("📄 RESUME PARSING: Processing resume content")
                    try:
                        output = contact_handler.handle_parse_resume(user_input)
                        logger.info(f"📄 RESUME RESULT: {output[:100]}...")
                    except Exception as resume_error:
                        logger.error(f"📄 RESUME ERROR: {resume_error}")
                        output = f"❌ Resume parsing failed: {str(resume_error)}"
                elif is_add_request:
                    # Force AI function calling for new contact creation
                    logger.info("✅ ADD REQUEST: Forcing AI function calling to create new contact")
                    output = process_with_functions(user_input, session['conversation_history'])
                else:
                    # ONLY auto-switch context for non-resume, non-add requests
                    context_switched = switch_context_if_mentioned(user_input, crm_manager)
                    if context_switched:
                        current_contact = get_last_contact()
                        logger.info(f"🎯 AUTO-SWITCHED to: {current_contact['name'] if current_contact else 'None'}")
                    
                    # Use AI with function calling for everything else
                    output = process_with_functions(user_input, session['conversation_history'])
                
                # Add response to history
                session['conversation_history'].append({"role": "assistant", "content": output})
                
                # Keep history manageable
                if len(session['conversation_history']) > 40:
                    session['conversation_history'] = session['conversation_history'][-30:]
                
                session.modified = True
                
            except Exception as e:
                logger.error(f"Request processing failed: {e}")
                output = f"❌ Error: {str(e)}"
                session['conversation_history'].append({"role": "assistant", "content": output})
                session.modified = True
    
    # Import the template
    try:
        from templates import ENHANCED_TEMPLATE, LOGIN_TEMPLATE
    except ImportError as e:
        logger.error(f"Template import error: {e}")
        return "Template error - please check templates.py file"
    
    return render_template_string(ENHANCED_TEMPLATE, 
                                output=output, 
                                history=session.get('conversation_history', []),
                                last_contact=get_last_contact())

# SIMPLIFIED LOGIN ROUTE
@app.route('/login', methods=['GET', 'POST'])
@rate_limit_login  # Apply rate limiting decorator
def login():
    from templates import LOGIN_TEMPLATE  # Import here to avoid circular issues
    
    if request.method == 'POST':
        # Security checks first
        if check_honeypot(request.form):
            logger.warning(f"🍯 HONEYPOT: Bot detected from IP {request.remote_addr}")
            time.sleep(2)  # Add delay to slow down bots
            return render_template_string(LOGIN_TEMPLATE, 
                error="Invalid access token. Please try again.")
        
        provided_token = request.form.get('token', '').strip()
        remember_me = request.form.get('remember_me') == 'on'  # Check remember me checkbox
        
        if provided_token == AUTH_TOKEN:
            session['authenticated'] = True
            session.permanent = True  # Always make permanent
            
            # Extended session for "Remember Me"
            if remember_me:
                session.permanent = True
                app.permanent_session_lifetime = timedelta(days=30)  # 30 days if remembered!
                logger.info(f"✅ EXTENDED LOGIN: 30-day session for {request.remote_addr}")
            else:
                app.permanent_session_lifetime = timedelta(days=7)   # 7 days normal
                logger.info(f"✅ STANDARD LOGIN: 7-day session for {request.remote_addr}")
            
            session.modified = True
            return redirect('/')
        else:
            # Handle failed login with progressive delays and rate limiting
            error_msg = handle_failed_login(request.remote_addr)
            logger.warning(f"🚫 FAILED LOGIN: {request.remote_addr}")
            return render_template_string(LOGIN_TEMPLATE, error=error_msg)
    
    # GET request - show login form
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout')
def logout():
    session.clear()
    logger.info(f"User logged out from {request.remote_addr}")
    return redirect('/login')

@app.route('/reset')
def reset():
    # Only clear conversation history, keep authentication
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
    last_contact = get_last_contact()
    return f'''
    <html>
    <head><title>EspoCRM AI Copilot Debug</title></head>
    <body style="font-family: Arial, sans-serif; max-width: 800px; margin: 20px auto; padding: 20px;">
        <h2>🔍 EspoCRM AI Copilot Debug Info</h2>
        
        <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <h3>Session Status</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr><td><strong>Authenticated:</strong></td><td>{session.get('authenticated', False)}</td></tr>
                <tr><td><strong>Session Keys:</strong></td><td>{list(session.keys())}</td></tr>
                <tr><td><strong>History Count:</strong></td><td>{len(session.get('conversation_history', []))}</td></tr>
                <tr><td><strong>Last Contact:</strong></td><td>{last_contact}</td></tr>
                <tr><td><strong>Current Calendar User:</strong></td><td>{session.get('current_calendar_user')}</td></tr>
                <tr><td><strong>Session Permanent:</strong></td><td>{session.permanent}</td></tr>
                <tr><td><strong>Session Lifetime:</strong></td><td>{app.permanent_session_lifetime}</td></tr>
            </table>
        </div>
        
        <div style="background: #e8f5e8; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <h3>🛡️ Security Status</h3>
            <p><strong>✅ Rate Limiting:</strong> Active</p>
            <p><strong>✅ Honeypot Protection:</strong> Active</p>
            <p><strong>✅ Progressive Delays:</strong> Active</p>
            <p><strong>✅ Session Persistence:</strong> 7-30 days</p>
        </div>
        
        <div style="background: #e9ecef; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <h3>Resume Parser Test</h3>
            <form method="post" action="/" enctype="multipart/form-data">
                <input type="file" name="resume_file" accept=".pdf,.docx,.txt,.doc">
                <button type="submit">Test Resume Upload</button>
            </form>
        </div>
        
        <p><a href="/">🏠 Main App</a> | <a href="/logout">🚪 Logout</a> | <a href="/reset">🔄 Reset</a> | <a href="/test-account-link">🔗 Test Account Linking</a></p>
    </body>
    </html>
    '''

@app.route('/test-account-link')
def test_account_link():
    """Test account linking functionality"""
    try:
        # Test 1: Search for Jeremy
        jeremy_contacts = crm_manager.search_contacts_simple("Jeremy Wolfe")
        jeremy_result = f"Jeremy search: {len(jeremy_contacts)} results - {[c.get('name') for c in jeremy_contacts]}" if jeremy_contacts else "Jeremy not found"
        
        # Test 2: Search for Eleven account
        eleven_accounts = crm_manager.search_accounts("Eleven")
        eleven_result = f"Eleven search: {len(eleven_accounts)} results - {[a.get('name') for a in eleven_accounts]}" if eleven_accounts else "Eleven account not found"
        
        # Test 3: Try linking if both exist
        link_result = "Not attempted - missing entities"
        if jeremy_contacts and eleven_accounts:
            link_result = crm_manager.link_contact_to_account("Jeremy Wolfe", "Eleven", primary=True)
        
        # Test 4: Check current association
        current_accounts = "No Jeremy found"
        if jeremy_contacts:
            current_accounts = crm_manager.get_contact_accounts("Jeremy Wolfe")
        
        return f"""
        <html>
        <head><title>Account Linking Test</title></head>
        <body style="font-family: Arial; margin: 20px;">
        <h2>🔗 Account Linking Test</h2>
        <div style="background: #f5f5f5; padding: 15px; margin: 10px 0;">
            <p><strong>Jeremy Search:</strong> {jeremy_result}</p>
            <p><strong>Eleven Account Search:</strong> {eleven_result}</p>
            <p><strong>Link Attempt Result:</strong> {link_result}</p>
        </div>
        <hr>
        <h3>Current Jeremy → Account Associations:</h3>
        <pre style="background: #eee; padding: 10px;">{current_accounts}</pre>
        <p><a href="/">🏠 Back to Main</a> | <a href="/debug">🔍 Debug Info</a></p>
        </body>
        </html>
        """
    except Exception as e:
        return f"""
        <html><body>
        <h2>❌ Test Error</h2>
        <p>Error: {str(e)}</p>
        <p><a href="/">Back to Main</a></p>
        </body></html>
        """

if __name__ == '__main__':
    print("🚀 Starting EspoCRM AI Copilot")
    print(f"🌐 Visit: http://localhost:5000")
    print(f"🔒 Use login form with access token")
    print("🛡️ SECURED: Rate limiting, honeypot protection")
    print("⏰ SESSION PERSISTENCE: 7 days standard, 30 days with 'Remember Me'")
    app.run(host="0.0.0.0", port=5000, debug=True)
