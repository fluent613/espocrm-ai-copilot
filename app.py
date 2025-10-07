MODEL_NAME = "gpt-4o-mini"

# app.py
# AI-First CRM Copilot - Intelligence-driven approach
# Let AI understand intent, then execute simple clean functions

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


# AI-FIRST PROCESSING - Simple and Intelligent
def process_user_request(user_input: str, conversation_history: list) -> str:
    """
    Simple flow:
    1. Ask AI to understand what user wants
    2. AI returns structured intent
    3. Execute the intent
    """
    try:
        # Get last contact context for AI
        last_contact = get_last_contact()
        context_info = ""
        if last_contact:
            context_info = f"\n\nCurrent contact context: {last_contact['name']} (ID: {last_contact['id']})"
        
        # Enhanced system prompt - AI does the heavy lifting
        system_prompt = f"""You are an intelligent CRM assistant. Your job is to understand what the user wants and call the appropriate function.

CURRENT CONTEXT:{context_info}

IMPORTANT RULES:
1. If a contact was just discussed and user gives an update command without a name, use that contact (don't require contact_name parameter)
2. For phone updates: extract the phone number and pass it as phoneNumber - the system will format it correctly
3. For creating contacts: extract all relevant fields from any format (LinkedIn profiles, resumes, casual text, etc.)
4. Always use available context intelligently
5. When user is frustrated, check conversation history to understand what they want and help them

AVAILABLE FUNCTIONS:
- search_contacts: Find contacts by any criteria
- get_contact_details: Get full details of a contact
- create_contact: Create a new contact with firstName, lastName, and optional fields (emailAddress, phoneNumber, cCurrentTitle, cCurrentCompany, cLinkedInURL, cSkills, etc.)
- update_contact: Update a contact (contact_name optional if in context, updates dict required)
- add_note: Add a note to a contact (contact_name optional if in context)
- get_contact_notes: Get all notes for a contact
- parse_resume: Parse resume text and create/update contact
- list_all_contacts: List contacts

EXAMPLES OF SMART CONTEXT USE:
User: "find john smith"
You: Call search_contacts with "john smith"

User: "phone: 555-1234" (after searching for John)
You: Call update_contact with updates={{"phoneNumber": "555-1234"}} - NO contact_name needed since John is in context

User: "add note: called, left voicemail" (after searching for John)
You: Call add_note with note_content="called, left voicemail" - NO contact_name needed

User: "update his email to john@acme.com" (after searching for John)
You: Call update_contact with updates={{"emailAddress": "john@acme.com"}}

User: "I just told you his phone number is 555-1234" (after mentioning a phone)
You: Look at conversation history, extract the phone number mentioned, call update_contact

User: "create contact Jane Doe, email jane@example.com, phone 555-9999"
You: Call create_contact with all the extracted data

User pastes LinkedIn profile data:
You: Extract firstName, lastName, emailAddress, cLinkedInURL, cCurrentTitle, cCurrentCompany, etc. and call create_contact

Be smart. Use context. Don't over-complicate. When in doubt, try to help."""

        # Build messages for AI
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Add recent conversation history for context (last 6 messages)
        messages.extend(conversation_history[-6:])
        
        # Add current user input
        messages.append({"role": "user", "content": user_input})
        
        logger.info(f"🤖 AI PROCESSING: {user_input[:100]}...")
        
        # Let AI figure out what to do
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            tools=simple_functions,
            tool_choice="auto",
            temperature=0.7,  # Slightly lower for more consistent behavior
            timeout=20
        )
        
        message = response.choices[0].message
        
        # If AI wants to call a function, do it
        if message.tool_calls:
            results = []
            
            for tool_call in message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                logger.info(f"📞 AI CALLED: {function_name}")
                logger.info(f"📋 ARGS: {function_args}")
                
                # Execute the function
                result = handle_function_call(function_name, function_args, user_input)
                results.append(result)
            
            # Return the results
            return "\n\n".join(results)
        
        # If AI just wants to respond with text (for clarifications)
        if message.content:
            return message.content
        
        # Fallback
        return "I understood your request but couldn't determine how to help. Could you rephrase?"
        
    except Exception as e:
        logger.error(f"❌ Error processing request: {e}")
        return f"⚠️ Something went wrong: {str(e)}\n\nPlease try rephrasing your request."


def handle_function_call(function_name: str, arguments: dict, user_input: str = "") -> str:
    """
    Simplified function handler - just executes what AI decided
    """
    try:
        logger.info(f"⚡ EXECUTING: {function_name} with {arguments}")
        
        if function_name == "search_contacts":
            criteria = arguments.get("criteria", "")
            contacts = crm_manager.search_contacts_simple(criteria)
            
            if not contacts:
                return f"❌ No contacts found matching '{criteria}'"
            
            # Set context to best match
            best_match = contacts[0]
            set_last_contact(best_match['id'], best_match.get('name', 'Unknown'))
            
            # Format results
            result = f"**Found {len(contacts)} contact(s):**\n\n"
            for i, contact in enumerate(contacts[:5], 1):
                name = contact.get('name', 'Unknown')
                result += f"{i}. **{name}**\n"
                if contact.get('emailAddress'):
                    result += f"   📧 {contact['emailAddress']}\n"
                if contact.get('cCurrentTitle'):
                    result += f"   💼 {contact['cCurrentTitle']}\n"
                if contact.get('cCurrentCompany'):
                    result += f"   🏢 {contact['cCurrentCompany']}\n"
                result += "\n"
            
            return result
            
        elif function_name == "update_contact":
            updates = arguments.get("updates", {})
            contact_name = arguments.get("contact_name")
            
            # If no contact_name provided, use context
            if not contact_name:
                last_contact = get_last_contact()
                if not last_contact:
                    return "❌ No contact in context. Please search for a contact first."
                contact_id = last_contact['id']
                contact_name = last_contact['name']
            else:
                # Find the contact
                contacts = crm_manager.search_contacts_simple(contact_name)
                if not contacts:
                    return f"❌ Contact '{contact_name}' not found"
                contact_id = contacts[0]['id']
                contact_name = contacts[0].get('name', contact_name)
                set_last_contact(contact_id, contact_name)
            
            # Handle phone number specially - convert to phoneNumberData
            if 'phoneNumber' in updates:
                phone_value = updates['phoneNumber']
                phone_data = create_phone_number_data(phone_value, "Mobile", True)
                if phone_data:
                    updates['phoneNumberData'] = phone_data
                    del updates['phoneNumber']
                else:
                    return f"❌ Invalid phone number format: {phone_value}"
            
            # Clean updates
            clean_updates = {k: v for k, v in updates.items() if v is not None and str(v).strip() != ""}
            
            if not clean_updates:
                return f"No valid updates provided for {contact_name}"
            
            # Execute update
            success, error_msg = crm_manager.update_contact_simple(contact_id, clean_updates)
            
            if success:
                # Show what was updated
                updated_items = []
                for key, value in clean_updates.items():
                    if key == 'phoneNumberData' and isinstance(value, list) and len(value) > 0:
                        phone_num = value[0].get('phoneNumber', '')
                        updated_items.append(f"📞 Phone: {phone_num}")
                    elif key == 'emailAddress':
                        updated_items.append(f"📧 Email: {value}")
                    elif key == 'cCurrentTitle':
                        updated_items.append(f"💼 Title: {value}")
                    elif key == 'cCurrentCompany':
                        updated_items.append(f"🏢 Company: {value}")
                    elif key == 'cLinkedInURL':
                        updated_items.append(f"🔗 LinkedIn: {value}")
                    else:
                        updated_items.append(f"{key}: {value}")
                
                result = f"✅ **Updated {contact_name}**"
                if updated_items:
                    result += "\n\n" + "\n".join(updated_items)
                return result
            else:
                return f"❌ Failed to update {contact_name}: {error_msg}"
        
        elif function_name == "create_contact":
            # Handle phone number conversion
            if 'phoneNumber' in arguments and not 'phoneNumberData' in arguments:
                phone_value = arguments['phoneNumber']
                phone_data = create_phone_number_data(phone_value, "Mobile", True)
                if phone_data:
                    arguments['phoneNumberData'] = phone_data
                del arguments['phoneNumber']
            
            # Try to create the contact
            result_msg, contact_id = crm_manager.create_contact(**arguments)
            
            # Check if it's a conflict (already exists)
            if "already exists" in result_msg or contact_id is None:
                # Contact might already exist - try to find and update instead
                name = f"{arguments.get('firstName', '')} {arguments.get('lastName', '')}".strip()
                email = arguments.get('emailAddress')
                
                logger.info(f"🔍 Contact creation conflict - searching for existing contact: {name}")
                
                # Search by name first
                existing = crm_manager.search_contacts_simple(name)
                
                # If no match by name, try email
                if not existing and email:
                    existing = crm_manager.search_contacts_simple(email)
                
                if existing:
                    # Found existing contact - offer to update
                    contact_id = existing[0]['id']
                    contact_name = existing[0].get('name', name)
                    set_last_contact(contact_id, contact_name)
                    
                    # Prepare update data (exclude name fields to avoid conflicts)
                    # IMPORTANT: Include ALL fields including skills, title, company, etc.
                    update_data = {}
                    for key, value in arguments.items():
                        if key not in ['firstName', 'lastName'] and value and str(value).strip():
                            update_data[key] = value
                            logger.info(f"📝 Will update {key}: {value}")
                    
                    if update_data:
                        logger.info(f"🔄 Updating existing contact {contact_name} with: {list(update_data.keys())}")
                        
                        # Update the existing contact
                        success, error_msg = crm_manager.update_contact_simple(contact_id, update_data)
                        
                        if success:
                            # Get updated details to show what changed
                            details = crm_manager.get_contact_details(contact_id)
                            
                            # Build list of what was updated
                            updated_fields = []
                            for key, value in update_data.items():
                                if key == 'phoneNumberData' and isinstance(value, list) and len(value) > 0:
                                    updated_fields.append(f"📞 Phone: {value[0].get('phoneNumber', '')}")
                                elif key == 'emailAddress':
                                    updated_fields.append(f"📧 Email: {value}")
                                elif key == 'cCurrentTitle':
                                    updated_fields.append(f"💼 Title: {value}")
                                elif key == 'cCurrentCompany':
                                    updated_fields.append(f"🏢 Company: {value}")
                                elif key == 'cSkills':
                                    updated_fields.append(f"🎯 Skills: {value}")
                                elif key == 'cLinkedInURL':
                                    updated_fields.append(f"🔗 LinkedIn: {value}")
                                else:
                                    updated_fields.append(f"• {key}: {value}")
                            
                            result = f"ℹ️ **Contact already exists: {contact_name}**\n\n✅ **Updated with new information:**\n"
                            result += "\n".join(updated_fields)
                            result += f"\n\n**Full details:**\n{details}"
                            return result
                        else:
                            details = crm_manager.get_contact_details(contact_id)
                            return f"ℹ️ **Contact already exists: {contact_name}**\n\n⚠️ Update failed: {error_msg}\n\n**Current details:**\n{details}"
                    else:
                        details = crm_manager.get_contact_details(contact_id)
                        return f"ℹ️ **Contact already exists: {contact_name}**\n\nNo new information to add.\n\n**Current details:**\n{details}"
                else:
                    # Couldn't find existing contact, return original error
                    return result_msg
            else:
                # Success - set context
                if contact_id:
                    name = f"{arguments.get('firstName', '')} {arguments.get('lastName', '')}".strip()
                    set_last_contact(contact_id, name)
                return result_msg
            
        elif function_name == "get_contact_details":
            contact_name = arguments.get("contact_name")
            contacts = crm_manager.search_contacts_simple(contact_name)
            if not contacts:
                return f"❌ Contact '{contact_name}' not found"
            contact_id = contacts[0]['id']
            set_last_contact(contact_id, contacts[0].get('name', contact_name))
            return crm_manager.get_contact_details(contact_id)
            
        elif function_name == "add_note":
            note_content = arguments.get("note_content")
            contact_name = arguments.get("contact_name")
            
            # Use context if no name provided
            if not contact_name:
                last_contact = get_last_contact()
                if not last_contact:
                    return "❌ No contact in context"
                contact_id = last_contact['id']
                contact_name = last_contact['name']
            else:
                contacts = crm_manager.search_contacts_simple(contact_name)
                if not contacts:
                    return f"❌ Contact '{contact_name}' not found"
                contact_id = contacts[0]['id']
                contact_name = contacts[0].get('name', contact_name)
                set_last_contact(contact_id, contact_name)
            
            result = crm_manager.add_note(contact_id, note_content)
            return result.replace("contact", f"**{contact_name}**")
            
        elif function_name == "get_contact_notes":
            contact_name = arguments.get("contact_name")
            contacts = crm_manager.search_contacts_simple(contact_name)
            if not contacts:
                return f"❌ Contact '{contact_name}' not found"
            return crm_manager.get_contact_notes(contacts[0]['id'])
            
        elif function_name == "parse_resume":
            resume_text = arguments.get("resume_text")
            
            # Use AI to extract structured data from resume
            logger.info("📄 Parsing resume with AI")
            
            extraction_prompt = f"""Extract contact information from this resume and return a structured response.

Resume content:
{resume_text[:3000]}

IMPORTANT - Extract ALL of these fields if present:
- firstName (required)
- lastName (required)
- emailAddress
- phoneNumber (any format)
- cCurrentTitle (most recent job title)
- cCurrentCompany (most recent/current company)
- cLinkedInURL (LinkedIn profile URL)
- cSkills (IMPORTANT: extract ALL skills, technologies, tools, languages mentioned - be comprehensive, comma-separated list)
- addressCity, addressState, addressPostalCode, addressCountry

For skills, include:
- Programming languages
- Frameworks and libraries
- Tools and platforms
- Soft skills
- Domain expertise
- Certifications

Return the data as if you're calling create_contact function."""

            try:
                extract_response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": "You are a resume parser. Extract contact information and call create_contact."},
                        {"role": "user", "content": extraction_prompt}
                    ],
                    tools=[simple_functions[1]],  # Just the create_contact function
                    tool_choice={"type": "function", "function": {"name": "create_contact"}},
                    temperature=0.3,
                    timeout=15
                )
                
                extract_message = extract_response.choices[0].message
                
                if extract_message.tool_calls:
                    tool_call = extract_message.tool_calls[0]
                    contact_data = json.loads(tool_call.function.arguments)
                    
                    logger.info(f"📋 Extracted contact data: {contact_data}")
                    
                    # Create the contact
                    return handle_function_call("create_contact", contact_data, resume_text)
                else:
                    return "❌ Could not extract contact information from resume"
                    
            except Exception as e:
                logger.error(f"Resume parsing error: {e}")
                return f"❌ Error parsing resume: {str(e)}"
            
        elif function_name == "list_all_contacts":
            return crm_manager.list_all_contacts(arguments.get("limit", 20))
        
        else:
            return f"❌ Unknown function: {function_name}"
            
    except Exception as e:
        logger.error(f"❌ Function execution error: {e}")
        return f"⚠️ Error executing {function_name}: {str(e)}"


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
    if request.path in ['/login', '/reset', '/debug']:
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
                    "phoneNumber": {"type": "string", "description": "Phone number in any format - will be converted automatically"},
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
            "description": "Update an existing contact's information. If a contact was just discussed, contact_name is optional.",
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_name": {"type": "string", "description": "Name to search for (optional if contact just discussed)"},
                    "updates": {
                        "type": "object", 
                        "description": "Fields to update - can include phoneNumber, emailAddress, cCurrentTitle, cCurrentCompany, cLinkedInURL, etc."
                    }
                },
                "required": ["updates"] 
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_note",
            "description": "Add a note to a contact. If a contact was just discussed, contact_name is optional.",
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_name": {"type": "string", "description": "Name of contact (optional if just discussed)"},
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
        
        # Handle file upload
        if 'resume_file' in request.files:
            file = request.files['resume_file']
            
            if file and file.filename:
                logger.info(f"📄 Processing uploaded file: {file.filename}")
                
                content, error = resume_parser.process_uploaded_file(file)
                if error:
                    output = error
                elif not content or len(content.strip()) < 10:
                    output = "❌ No content extracted from file. Please check the file format."
                else:
                    # Let AI extract and create contact directly
                    user_input = f"This is a resume. Extract the contact information and create a new contact:\n\n{content[:4000]}"
            else:
                output = "❌ No file selected or file is empty."
        else:
            user_input = sanitize_input(request.form.get('prompt', ''))
        
        if user_input and not output:
            try:
                # Add to history
                session['conversation_history'].append({"role": "user", "content": user_input})
                
                # Process with AI-first approach
                output = process_user_request(user_input, session['conversation_history'])
                
                # Ensure we always have output
                if not output or output.strip() == "":
                    output = "✅ Operation completed. Please check your CRM."
                
                # Add to history
                session['conversation_history'].append({"role": "assistant", "content": output})
                
                # Keep history manageable
                if len(session['conversation_history']) > 40:
                    session['conversation_history'] = session['conversation_history'][-30:]
                
                session.modified = True
                
            except Exception as e:
                logger.error(f"Request processing failed: {e}")
                output = f"⚠️ Something went wrong: {str(e)}\n\nPlease try again."
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
    """Simple debug endpoint"""
    last_contact = get_last_contact()
    return f'''
    <html>
    <head><title>EspoCRM AI Copilot Debug</title></head>
    <body style="font-family: Arial, sans-serif; max-width: 800px; margin: 20px auto; padding: 20px;">
        <h2>🔍 EspoCRM AI Copilot Debug Info</h2>
        
        <div style="background: #e8f5e8; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <h3>Session Status</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr><td><strong>Authenticated:</strong></td><td>{session.get('authenticated', False)}</td></tr>
                <tr><td><strong>History Count:</strong></td><td>{len(session.get('conversation_history', []))}</td></tr>
                <tr><td><strong>Last Contact:</strong></td><td>{last_contact}</td></tr>
            </table>
        </div>
        
        <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <h3>Architecture</h3>
            <p><strong>Processing Mode:</strong> AI-First Intelligence</p>
            <p><strong>Approach:</strong> AI understands intent → Execute simple functions</p>
            <p><strong>Benefits:</strong> Natural language, context-aware, self-learning</p>
        </div>
        
        <p><a href="/">🏠 Main App</a> | <a href="/logout">🚪 Logout</a> | <a href="/reset">🔄 Reset</a></p>
    </body>
    </html>
    '''

if __name__ == '__main__':
    print("🚀 Starting EspoCRM AI Copilot - AI-FIRST VERSION")
    print("✨ Features: Intelligent intent understanding")
    print("🤖 Approach: Let AI do the thinking, we do the executing")
    print(f"🌐 Visit: http://localhost:5000")
    print(f"🔒 Use login form with access token")
    app.run(host="0.0.0.0", port=5000, debug=True)
