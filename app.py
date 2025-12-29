MODEL_NAME = "gpt-4.1"

# app.py
# AI-First CRM Copilot - Intelligence-driven approach
# Let AI understand intent, then execute simple clean functions

from flask import Flask, request, render_template_string, session, redirect, make_response, url_for, send_file
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
import uuid

load_dotenv()

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Email memory storage - rolling list of last 5 sent emails
RECENT_EMAILS_FILE = Path(__file__).parent / 'recent_emails.json'
MAX_RECENT_EMAILS = 5

# Persistent AI context notes
AI_CONTEXT_FILE = Path(__file__).parent / 'ai_context.txt'

# Email templates storage
EMAIL_TEMPLATES_FILE = Path(__file__).parent / 'email_templates.json'

def get_recent_emails():
    """Load recent emails from storage"""
    try:
        if RECENT_EMAILS_FILE.exists():
            return json.loads(RECENT_EMAILS_FILE.read_text())
    except Exception as e:
        logger.error(f"Error loading recent emails: {e}")
    return []

def save_sent_email(to_email, subject, body, sender):
    """Save a sent email to the rolling list (max 5)"""
    try:
        recent = get_recent_emails()
        recent.insert(0, {
            'to': to_email,
            'subject': subject,
            'body': body[:500],  # Truncate body
            'sender': sender,
            'timestamp': time.strftime('%Y-%m-%d %H:%M')
        })
        # Keep only last 5
        recent = recent[:MAX_RECENT_EMAILS]
        RECENT_EMAILS_FILE.write_text(json.dumps(recent, indent=2))
    except Exception as e:
        logger.error(f"Error saving sent email: {e}")

def get_ai_context():
    """Load persistent AI context notes"""
    try:
        if AI_CONTEXT_FILE.exists():
            return AI_CONTEXT_FILE.read_text().strip()
    except Exception as e:
        logger.error(f"Error loading AI context: {e}")
    return ""

def save_ai_context(context):
    """Save persistent AI context notes"""
    try:
        AI_CONTEXT_FILE.write_text(context)
        return True
    except Exception as e:
        logger.error(f"Error saving AI context: {e}")
        return False

def get_email_templates():
    """Load email templates from JSON storage"""
    try:
        if EMAIL_TEMPLATES_FILE.exists():
            return json.loads(EMAIL_TEMPLATES_FILE.read_text())
    except Exception as e:
        logger.error(f"Error loading email templates: {e}")
    return []

def save_email_template(template):
    """Add or update an email template"""
    try:
        templates = get_email_templates()
        # If template has id, update existing; otherwise create new
        if template.get('id'):
            templates = [t for t in templates if t['id'] != template['id']]
        else:
            template['id'] = str(uuid.uuid4())
        template['created'] = time.strftime('%Y-%m-%d')
        templates.append(template)
        EMAIL_TEMPLATES_FILE.write_text(json.dumps(templates, indent=2))
        return template
    except Exception as e:
        logger.error(f"Error saving email template: {e}")
        return None

def delete_email_template(template_id):
    """Remove an email template by ID"""
    try:
        templates = get_email_templates()
        templates = [t for t in templates if t['id'] != template_id]
        EMAIL_TEMPLATES_FILE.write_text(json.dumps(templates, indent=2))
        return True
    except Exception as e:
        logger.error(f"Error deleting email template: {e}")
        return False


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
            context_info = f"\nCurrent contact context: {last_contact['name']} (ID: {last_contact['id']})"

        # Get current date for AI
        from datetime import datetime, timedelta
        today = datetime.now()
        today_str = today.strftime("%Y-%m-%d")
        day_of_week = today.strftime("%A")

        # Calculate upcoming dates for natural language
        tomorrow = (today + timedelta(days=1)).strftime("%Y-%m-%d")
        next_week = (today + timedelta(days=7)).strftime("%Y-%m-%d")

        # Enhanced system prompt - AI does the heavy lifting
        system_prompt = f"""You are an intelligent CRM assistant. Your job is to understand what the user wants and call the appropriate function.

CURRENT DATE: {today_str} ({day_of_week})
- Today: {today_str}
- Tomorrow: {tomorrow}
- Next week: {next_week}

When user says "today", "tomorrow", "Friday", "next week", etc., convert to YYYY-MM-DD format.

CURRENT CONTEXT:{context_info}

IMPORTANT RULES:
1. If a contact was just discussed and user gives an update command without a name, use that contact (don't require contact_name parameter)
2. For phone updates: extract the phone number and pass it as phoneNumber - the system will format it correctly
3. For creating contacts: extract ALL relevant fields from the user's message in ONE go (name, email, phone, title, company, address - everything mentioned)
4. Always use available context intelligently
5. When user is frustrated or uses profanity, understand they're trying to do something - figure out what and do it

BE PROACTIVE - ANTICIPATE NEXT STEPS:
6. If a search returns NO results and the user's intent suggests they want to work with that person, IMMEDIATELY offer to create the contact. Example: "No contact found for 'John Smith'. Would you like me to create them?"
7. If user says "find X or create them" / "check if X exists" / "add X if not there" - search first, then auto-create if not found
8. When creating a contact, if user provides partial info, create with what you have - don't ask for fields that weren't provided
9. If user gives you info about a contact right after searching (like an email), assume they want to UPDATE the found contact or ADD it to a new contact if search failed
10. CHAIN OPERATIONS: If user says "find Tony and add his email tony@test.com" - do BOTH: search, then update with email

AVAILABLE FUNCTIONS:
- search_contacts: Find contacts by any criteria
- get_contact_details: Get full details of a contact
- create_contact: Create a new contact with firstName, lastName, and optional fields (emailAddress, phoneNumber, cCurrentTitle, cCurrentCompany, cLinkedInURL, cSkills, etc.)
- update_contact: Update a contact (contact_name optional if in context, updates dict required)
- add_note: Add a note to a contact (contact_name optional if in context)
- get_contact_notes: Get all notes for a contact
- parse_resume: Parse resume text and create/update contact
- list_all_contacts: List contacts
- search_accounts: Search for accounts (companies) by name, email, or website
- create_account: Create a new account with name and optional fields (emailAddress, phoneNumber, website, industry, type, billingAddress, description)
- get_account_details: Get full details of an account
- link_contact_to_account: Associate a contact with an account (primary=true sets as main account)

TASK AND REMINDER FUNCTIONS:
- create_task: Create a task for a user (name required, assigned_to optional - will ask if not provided)
- create_reminder: Create a high-priority reminder task for a user
- get_user_tasks: Get tasks for a specific user or all users (status_filter: open, all, Completed)
- complete_task: Mark a task as completed
- list_users: List all users available for task assignment

EXAMPLES OF SMART CONTEXT USE:
User: "find john smith"
You: Call search_contacts with "john smith"

User: "find john smith or create him"
You: Call search_contacts first. If no results, IMMEDIATELY call create_contact with firstName="John", lastName="Smith"

User: "is tony hessburg in there? if not add him"
You: Call search_contacts. If not found, call create_contact. Don't just say "not found" and wait.

User: "add this contact: Brian Smith | Manager | Acme Corp | brian@acme.com | 555-1234"
You: Call create_contact with ALL fields extracted: firstName="Brian", lastName="Smith", cCurrentTitle="Manager", cCurrentCompany="Acme Corp", emailAddress="brian@acme.com", phoneNumber="555-1234"

User: "phone: 555-1234" (after searching for John)
You: Call update_contact with updates={{"phoneNumber": "555-1234"}} - NO contact_name needed since John is in context

User: "add note: called, left voicemail" (after searching for John)
You: Call add_note with note_content="called, left voicemail" - NO contact_name needed

User: "update his email to john@acme.com" (after searching for John)
You: Call update_contact with updates={{"emailAddress": "john@acme.com"}}

User: "fuck I just gave you his phone number" (after mentioning a phone)
You: Look at conversation history, extract the phone number mentioned, call update_contact

User: "create contact Jane Doe, email jane@example.com, phone 555-9999"
You: Call create_contact with all the extracted data

User pastes LinkedIn profile data:
You: Extract firstName, lastName, emailAddress, cLinkedInURL, cCurrentTitle, cCurrentCompany, etc. and call create_contact

User: "find or add Sarah Connor, sarah@skynet.com"
You: Search first, if not found create with the email included - don't create without the email!

TASK AND REMINDER EXAMPLES:
User: "remind Aaron to follow up with the client"
You: Call create_reminder with reminder_text="follow up with the client", for_user="Aaron"

User: "create a task for Esther to review the contract, due Friday"
You: Call create_task with name="Review the contract", assigned_to="Esther", due_date="2025-11-29" (convert "Friday" to actual date)

User: "what are my tasks?"
You: Call get_user_tasks - if user identity is known from context, include user_name

User: "show all open tasks"
You: Call get_user_tasks with status_filter="open"

User: "mark the follow up task as done"
You: Call complete_task with task_name="follow up"

User: "who can I assign tasks to?"
You: Call list_users

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
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                tools=simple_functions,
                tool_choice="auto",
                temperature=0.7,  # Slightly lower for more consistent behavior
                timeout=20
            )
        except openai.APITimeoutError as e:
            logger.error(f"❌ AI processing timeout: {e}")
            return "❌ Request timed out. Please try again with a simpler request."
        except openai.APIError as e:
            logger.error(f"❌ OpenAI API error: {e}")
            return f"❌ AI service error: {str(e)}\n\nPlease try again in a moment."
        
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
            resume_file = arguments.get("resume_file")  # File object if available

            # Use the same extract_resume_info method as the careers page
            logger.info("📄 Parsing resume with AI (using extract_resume_info)")

            try:
                # Extract structured data from resume text (pass filename for fallback extraction)
                filename = resume_file.filename if resume_file and hasattr(resume_file, 'filename') else None
                parsed_data = resume_parser.extract_resume_info(resume_text, filename=filename)

                if not parsed_data or not parsed_data.get('firstName') or not parsed_data.get('lastName'):
                    logger.error("Failed to extract required fields from resume")
                    return "❌ Could not extract contact information from resume. Please ensure the resume contains a name."

                logger.info(f"📋 Extracted contact data: {parsed_data}")

                # Log filename vs extracted name for debugging
                extracted_name = f"{parsed_data.get('firstName', '')} {parsed_data.get('lastName', '')}".strip()
                logger.info(f"🔍 UPLOADED FILE: {resume_file.filename if resume_file else 'N/A'}")
                logger.info(f"🔍 EXTRACTED NAME: {extracted_name}")
                if resume_file and resume_file.filename:
                    # Check if filename suggests a different person
                    filename_lower = resume_file.filename.lower()
                    if extracted_name.lower() not in filename_lower:
                        logger.warning(f"⚠️ MISMATCH: Filename '{resume_file.filename}' doesn't match extracted name '{extracted_name}'")

                # Set candidate flag to true (this is a resume upload, so they are a candidate)
                parsed_data['cIsCandidate'] = True
                logger.info("✅ Set cIsCandidate=True")

                # CRITICAL: Search for existing contact FIRST before trying to create
                # This prevents creating duplicate/wrong contacts
                name = f"{parsed_data.get('firstName', '')} {parsed_data.get('lastName', '')}".strip()
                email = parsed_data.get('emailAddress')

                logger.info(f"🔍 Searching for existing contact: {name}")
                existing_contact = crm_manager.search_contacts_simple(name)

                # If not found by name, try email
                if not existing_contact and email and email != 'Unknown':
                    logger.info(f"🔍 Searching by email: {email}")
                    existing_contact = crm_manager.search_contacts_simple(email)

                # If still not found and we have a filename, try searching by filename
                if not existing_contact and filename:
                    # Try to extract name from filename and search
                    filename_name_parts = resume_parser.extract_name_from_filename(filename)
                    if filename_name_parts:
                        filename_search_name = f"{filename_name_parts[0]} {filename_name_parts[1]}"
                        logger.info(f"🔍 Searching by filename-derived name: {filename_search_name}")
                        existing_contact = crm_manager.search_contacts_simple(filename_search_name)

                # If we found an existing contact, update it instead of creating
                if existing_contact:
                    contact_id = existing_contact[0]['id']
                    contact_name = existing_contact[0].get('name', name)
                    logger.info(f"✅ Found existing contact: {contact_name} (ID: {contact_id})")
                    logger.info(f"🔄 Will update instead of create")
                    set_last_contact(contact_id, contact_name)

                    # Prepare update data (exclude firstName, lastName to avoid changing identity)
                    update_data = {}
                    for key, value in parsed_data.items():
                        if key not in ['firstName', 'lastName']:
                            if isinstance(value, bool) or (value and str(value).strip() and str(value) != 'Unknown'):
                                update_data[key] = value

                    # Handle phone number conversion for update
                    if 'phoneNumber' in update_data and 'phoneNumberData' not in update_data:
                        phone_value = update_data['phoneNumber']
                        phone_data = create_phone_number_data(phone_value, "Mobile", True)
                        if phone_data:
                            update_data['phoneNumberData'] = phone_data
                        del update_data['phoneNumber']

                    # Execute update
                    success, error_msg = crm_manager.update_contact_simple(contact_id, update_data)

                    if success:
                        # Upload resume file
                        file_upload_msg = ""
                        if resume_file:
                            logger.info(f"📎 Uploading resume file: {resume_file.filename}")
                            upload_success, upload_result = crm_manager.upload_attachment(
                                'Contact', contact_id, resume_file, resume_file.filename, 'cResume'
                            )
                            if upload_success:
                                file_upload_msg = f"\n📎 Resume file uploaded: {resume_file.filename}"
                            else:
                                file_upload_msg = f"\n⚠️ Resume file upload failed: {upload_result}"

                        # Build update summary
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
                            elif key == 'cIsCandidate' and value:
                                updated_fields.append(f"✅ Marked as Candidate")

                        result = f"ℹ️ **Contact already exists: {contact_name}**\n\n✅ **Updated with new information:**\n"
                        result += "\n".join(updated_fields)
                        result += file_upload_msg

                        # Add warning if extracted name doesn't match contact name
                        if name.lower() != contact_name.lower():
                            result += f"\n\n⚠️ **Note:** Resume extracted name '{name}', but updated existing contact '{contact_name}'"

                        return result
                    else:
                        return f"ℹ️ **Contact already exists: {contact_name}**\n\n⚠️ Update failed: {error_msg}"

                # No existing contact found - proceed with creation
                logger.info(f"📝 No existing contact found, will create new contact")

                # Handle phone number conversion
                if 'phoneNumber' in parsed_data and not 'phoneNumberData' in parsed_data:
                    phone_value = parsed_data['phoneNumber']
                    phone_data = create_phone_number_data(phone_value, "Mobile", True)
                    if phone_data:
                        parsed_data['phoneNumberData'] = phone_data
                    del parsed_data['phoneNumber']

                # Try to create the contact
                result_msg, contact_id = crm_manager.create_contact(**parsed_data)

                # Check if contact already exists - if so, search and update
                if "already exists" in result_msg or contact_id is None:
                    name = f"{parsed_data.get('firstName', '')} {parsed_data.get('lastName', '')}".strip()
                    email = parsed_data.get('emailAddress')

                    logger.info(f"🔍 Contact creation conflict - searching for existing contact: {name}")

                    # Search by name first
                    existing = crm_manager.search_contacts_simple(name)

                    # If no match by name, try email
                    if not existing and email:
                        existing = crm_manager.search_contacts_simple(email)

                    if existing:
                        # Found existing contact - update with new data
                        contact_id = existing[0]['id']
                        contact_name = existing[0].get('name', name)
                        set_last_contact(contact_id, contact_name)

                        # Prepare update data (exclude name fields, but include cIsCandidate)
                        update_data = {}
                        for key, value in parsed_data.items():
                            if key not in ['firstName', 'lastName']:
                                # Include boolean values and non-empty string values
                                if isinstance(value, bool) or (value and str(value).strip()):
                                    update_data[key] = value
                                    logger.info(f"📝 Will update {key}: {value}")

                        if update_data:
                            logger.info(f"🔄 Updating existing contact {contact_name} with: {list(update_data.keys())}")
                            success, error_msg = crm_manager.update_contact_simple(contact_id, update_data)

                            if success:
                                # Upload resume file if available
                                file_upload_msg = ""
                                if resume_file:
                                    logger.info(f"📎 Uploading resume file: {resume_file.filename}")
                                    upload_success, upload_result = crm_manager.upload_attachment(
                                        'Contact', contact_id, resume_file, resume_file.filename, 'cResume'
                                    )
                                    if upload_success:
                                        file_upload_msg = f"\n📎 Resume file uploaded: {resume_file.filename}"
                                    else:
                                        file_upload_msg = f"\n⚠️ Resume file upload failed: {upload_result}"

                                # Build list of updated fields
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
                                    elif key == 'cIsCandidate' and value:
                                        updated_fields.append(f"✅ Marked as Candidate")
                                    else:
                                        updated_fields.append(f"• {key}: {value}")

                                result = f"ℹ️ **Contact already exists: {contact_name}**\n\n✅ **Updated with new information:**\n"
                                result += "\n".join(updated_fields)
                                result += file_upload_msg

                                # Add warning if filename doesn't match extracted name
                                if resume_file and resume_file.filename:
                                    filename_lower = resume_file.filename.lower()
                                    name_lower = contact_name.lower()
                                    if name_lower not in filename_lower:
                                        result += f"\n\n⚠️ **Note:** The uploaded file is named '{resume_file.filename}', but the resume contains information for '{contact_name}'. Please verify this is the correct file."

                                return result
                            else:
                                return f"ℹ️ **Contact already exists: {contact_name}**\n\n⚠️ Update failed: {error_msg}"
                        else:
                            return f"ℹ️ **Contact already exists: {contact_name}**\n\nNo new information to add."
                    else:
                        return result_msg
                else:
                    # Success - new contact created
                    if contact_id:
                        name = f"{parsed_data.get('firstName', '')} {parsed_data.get('lastName', '')}".strip()
                        set_last_contact(contact_id, name)

                        # Build a detailed summary of what was created
                        created_fields = []
                        if parsed_data.get('emailAddress'):
                            created_fields.append(f"📧 Email: {parsed_data['emailAddress']}")
                        if parsed_data.get('phoneNumberData') and isinstance(parsed_data['phoneNumberData'], list) and len(parsed_data['phoneNumberData']) > 0:
                            phone_num = parsed_data['phoneNumberData'][0].get('phoneNumber', '')
                            if phone_num:
                                created_fields.append(f"📞 Phone: {phone_num}")
                        if parsed_data.get('cCurrentTitle'):
                            created_fields.append(f"💼 Title: {parsed_data['cCurrentTitle']}")
                        if parsed_data.get('cCurrentCompany'):
                            created_fields.append(f"🏢 Company: {parsed_data['cCurrentCompany']}")
                        if parsed_data.get('cSkills'):
                            created_fields.append(f"🎯 Skills: {parsed_data['cSkills']}")
                        if parsed_data.get('cLinkedInURL'):
                            created_fields.append(f"🔗 LinkedIn: {parsed_data['cLinkedInURL']}")
                        if parsed_data.get('cIsCandidate'):
                            created_fields.append(f"✅ Marked as Candidate")

                        # Upload resume file if available
                        file_upload_msg = ""
                        if resume_file:
                            logger.info(f"📎 Uploading resume file: {resume_file.filename}")
                            upload_success, upload_result = crm_manager.upload_attachment(
                                'Contact', contact_id, resume_file, resume_file.filename, 'cResume'
                            )
                            if upload_success:
                                file_upload_msg = f"\n📎 Resume file uploaded: {resume_file.filename}"
                                logger.info(f"✅ Resume upload successful: {upload_result}")
                            else:
                                file_upload_msg = f"\n⚠️ Resume file upload failed: {upload_result}"
                                logger.error(f"❌ Resume upload failed: {upload_result}")

                        result = f"✅ **Created new contact: {name}**\n\n**Extracted information:**\n"
                        result += "\n".join(created_fields)
                        result += file_upload_msg

                        # Add warning if filename doesn't match extracted name
                        if resume_file and resume_file.filename:
                            filename_lower = resume_file.filename.lower()
                            name_lower = name.lower()
                            if name_lower not in filename_lower:
                                result += f"\n\n⚠️ **Note:** The uploaded file is named '{resume_file.filename}', but the resume contains information for '{name}'. Please verify this is the correct file."

                        return result
                    return result_msg

            except Exception as e:
                logger.error(f"❌ Unexpected resume parsing error: {e}", exc_info=True)
                return f"❌ Error parsing resume: {str(e)}\n\nPlease try again or contact support if the issue persists."
            
        elif function_name == "list_all_contacts":
            return crm_manager.list_all_contacts(arguments.get("limit", 20))

        elif function_name == "search_accounts":
            criteria = arguments.get("criteria", "")
            accounts = crm_manager.search_accounts(criteria)

            if not accounts:
                return f"❌ No accounts found matching '{criteria}'"

            result = f"**Found {len(accounts)} account(s):**\n\n"
            for i, account in enumerate(accounts[:10], 1):
                name = account.get('name', 'Unknown')
                result += f"{i}. **{name}**\n"
                if account.get('emailAddress'):
                    result += f"   📧 {account['emailAddress']}\n"
                if account.get('website'):
                    result += f"   🌐 {account['website']}\n"
                if account.get('industry'):
                    result += f"   🏭 {account['industry']}\n"
                result += "\n"

            return result

        elif function_name == "create_account":
            result_msg, account_id = crm_manager.create_account(**arguments)
            return result_msg

        elif function_name == "get_account_details":
            account_name = arguments.get("account_name", "")
            accounts = crm_manager.search_accounts(account_name)
            if not accounts:
                return f"❌ Account '{account_name}' not found"
            account_id = accounts[0]['id']
            return crm_manager.get_account_details(account_id)

        elif function_name == "link_contact_to_account":
            contact_name = arguments.get("contact_name", "")
            account_name = arguments.get("account_name", "")
            primary = arguments.get("primary", True)
            return crm_manager.link_contact_to_account(contact_name, account_name, primary)

        # TASK AND REMINDER FUNCTIONS
        elif function_name == "create_task":
            name = arguments.get("name", "")
            assigned_to = arguments.get("assigned_to")
            due_date = arguments.get("due_date")
            description = arguments.get("description")
            priority = arguments.get("priority", "Normal")
            related_contact = arguments.get("related_contact")

            return crm_manager.create_task(
                name=name,
                assigned_to=assigned_to,
                due_date=due_date,
                description=description,
                priority=priority,
                related_contact=related_contact
            )

        elif function_name == "create_reminder":
            reminder_text = arguments.get("reminder_text", "")
            for_user = arguments.get("for_user")
            due_date = arguments.get("due_date")
            related_contact = arguments.get("related_contact")

            return crm_manager.create_reminder(
                reminder_text=reminder_text,
                for_user=for_user,
                due_date=due_date,
                related_contact=related_contact
            )

        elif function_name == "get_user_tasks":
            user_name = arguments.get("user_name")
            status_filter = arguments.get("status_filter", "open")
            return crm_manager.get_user_tasks(user_name=user_name, status_filter=status_filter)

        elif function_name == "complete_task":
            task_name = arguments.get("task_name", "")
            user_name = arguments.get("user_name")
            return crm_manager.update_task_status(task_name, "Completed", user_name)

        elif function_name == "list_users":
            return crm_manager.list_users_for_assignment()

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

# Middleware to handle proxy subpath (for /copilot/ embedding)
class PrefixMiddleware(object):
    def __init__(self, app, prefix=''):
        self.app = app
        self.prefix = prefix

    def __call__(self, environ, start_response):
        # Check if X-Script-Name header is set by nginx
        script_name = environ.get('HTTP_X_SCRIPT_NAME', '')
        if script_name:
            environ['SCRIPT_NAME'] = script_name
            path_info = environ['PATH_INFO']
            if path_info.startswith(script_name):
                environ['PATH_INFO'] = path_info[len(script_name):]
        elif self.prefix:
            environ['SCRIPT_NAME'] = self.prefix
            path_info = environ['PATH_INFO']
            if path_info.startswith(self.prefix):
                environ['PATH_INFO'] = path_info[len(self.prefix):]

        return self.app(environ, start_response)

app.wsgi_app = PrefixMiddleware(app.wsgi_app)

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

    # Skip auth for static assets (don't save as next_url either)
    if request.path in ['/favicon.ico', '/robots.txt'] or request.path.startswith('/static/'):
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
    # Save the original URL so we can redirect back after login (only for actual pages)
    session['next_url'] = request.url
    session.modified = True
    return redirect(url_for('login'))

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
                    "addressCountry": {"type": "string"},
                    "cIsCandidate": {"type": "boolean", "description": "Set to true if this is a job candidate"},
                    "cCandidateStatus": {"type": "string", "description": "Candidate status - MUST be one of: New, Submitted, 1st Interview, 2nd Interview, 3rd Interview, Offer, Accepted, Rejected, Archived"}
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
                        "description": "Fields to update. For MULTIPLE PHONE NUMBERS, use phoneNumberData as an array: [{\"phoneNumber\": \"+1XXXXXXXXXX\", \"type\": \"Office|Mobile|Home|Other\", \"primary\": true/false}, ...]. Phone types: Office (for corporate/work), Mobile, Home (for personal), Other. For MULTIPLE EMAILS, use emailAddressData as an array: [{\"emailAddress\": \"email@example.com\", \"primary\": true/false}, ...]. First email should be primary. For single values use phoneNumber or emailAddress strings. Other fields: cCurrentTitle, cCurrentCompany, cLinkedInURL, cSkills, cIsCandidate (boolean true/false), cCandidateStatus (MUST be one of: New, Submitted, 1st Interview, 2nd Interview, 3rd Interview, Offer, Accepted, Rejected, Archived)"
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
    },
    {
        "type": "function",
        "function": {
            "name": "search_accounts",
            "description": "Search for accounts (companies) in the CRM",
            "parameters": {
                "type": "object",
                "properties": {
                    "criteria": {"type": "string", "description": "Search term - can be account name, email, or website"}
                },
                "required": ["criteria"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_account",
            "description": "Create a new account (company) in the CRM",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Company name"},
                    "emailAddress": {"type": "string"},
                    "phoneNumber": {"type": "string"},
                    "website": {"type": "string"},
                    "industry": {"type": "string"},
                    "type": {"type": "string"},
                    "billingAddressStreet": {"type": "string"},
                    "billingAddressCity": {"type": "string"},
                    "billingAddressState": {"type": "string"},
                    "billingAddressPostalCode": {"type": "string"},
                    "billingAddressCountry": {"type": "string"},
                    "description": {"type": "string"}
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
            "name": "link_contact_to_account",
            "description": "Associate a contact with an account (company)",
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_name": {"type": "string", "description": "Name of the contact"},
                    "account_name": {"type": "string", "description": "Name of the account"},
                    "primary": {"type": "boolean", "description": "Whether this is the primary account for the contact", "default": True}
                },
                "required": ["contact_name", "account_name"]
            }
        }
    },
    # TASK AND REMINDER FUNCTIONS
    {
        "type": "function",
        "function": {
            "name": "create_task",
            "description": "Create a task or to-do item for a user. Use this when someone says 'remind [person] to...', 'create task for...', 'add to-do...', 'schedule task...'",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Task title or description"},
                    "assigned_to": {"type": "string", "description": "Name of user to assign the task to (e.g., 'Aaron', 'Stephen', 'Esther'). If not specified, will ask."},
                    "due_date": {"type": "string", "description": "Due date in YYYY-MM-DD format (e.g., '2025-11-28')"},
                    "description": {"type": "string", "description": "Additional details or notes for the task"},
                    "priority": {"type": "string", "enum": ["Low", "Normal", "High", "Urgent"], "description": "Task priority level"},
                    "related_contact": {"type": "string", "description": "Name of contact to link this task to"}
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_reminder",
            "description": "Create a reminder for a user (high-priority task). Use this when someone says 'remind Aaron to...', 'set reminder for...', 'don't let me forget...'",
            "parameters": {
                "type": "object",
                "properties": {
                    "reminder_text": {"type": "string", "description": "What to remind about"},
                    "for_user": {"type": "string", "description": "Name of user to remind (e.g., 'Aaron', 'Stephen', 'Esther', 'me')"},
                    "due_date": {"type": "string", "description": "When to remind (YYYY-MM-DD format)"},
                    "related_contact": {"type": "string", "description": "Contact name to link the reminder to"}
                },
                "required": ["reminder_text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_tasks",
            "description": "Get tasks for a user or all users. Use when someone asks 'what are my tasks?', 'show Aaron's tasks', 'list all tasks'",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_name": {"type": "string", "description": "Name of user to get tasks for (optional - shows all if not specified)"},
                    "status_filter": {"type": "string", "enum": ["open", "all", "Completed", "Not Started", "Started"], "description": "Filter by status (default: open)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "complete_task",
            "description": "Mark a task as completed. Use when someone says 'mark task done', 'complete the follow up task', 'finished the reminder'",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_name": {"type": "string", "description": "Name or partial name of the task to complete"},
                    "user_name": {"type": "string", "description": "User whose task to complete (helps narrow search if multiple matches)"}
                },
                "required": ["task_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_users",
            "description": "List all users available for task assignment. Use when someone asks 'who can I assign tasks to?', 'show users', 'list team members'",
            "parameters": {
                "type": "object",
                "properties": {}
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
                try:
                    logger.info(f"📄 Processing uploaded file: {file.filename}")
                    logger.info(f"📄 File size: {file.content_length if hasattr(file, 'content_length') else 'unknown'} bytes")

                    # Read file into memory to preserve it
                    file_bytes = file.read()
                    file.seek(0)  # Reset file pointer for processing

                    content, error = resume_parser.process_uploaded_file(file)

                    logger.info(f"📋 File processing result - Content length: {len(content) if content else 0}, Error: {error}")
                    if content:
                        # Log first 500 chars to help debug name extraction
                        preview = content[:500].replace('\n', ' ')
                        logger.info(f"📋 Content preview: {preview}...")

                    if error:
                        output = error
                        logger.warning(f"⚠️ File processing error: {error}")
                        session['conversation_history'].append({"role": "assistant", "content": output})
                        session.modified = True
                    elif not content or len(content.strip()) < 10:
                        output = "❌ No content extracted from file. Please check the file format."
                        logger.warning(f"⚠️ Content too short: {len(content) if content else 0} characters")
                        session['conversation_history'].append({"role": "assistant", "content": output})
                        session.modified = True
                    else:
                        # Store file info in session temporarily
                        session['temp_resume_file'] = {
                            'filename': file.filename,
                            'data': file_bytes
                        }
                        session.modified = True

                        # Let AI extract and create contact directly via parse_resume
                        user_input = f"Parse this resume file: {file.filename}"
                        logger.info(f"✅ File content extracted successfully, length: {len(content)}")

                        # Add file info to conversation for context
                        session['conversation_history'].append({"role": "user", "content": f"📎 Uploaded resume: {file.filename}"})

                        # Process with parse_resume function
                        # Create a proper file-like object for upload
                        from io import BytesIO
                        file_obj = BytesIO(file_bytes)
                        file_obj.filename = file.filename
                        file_obj.name = file.filename

                        output = handle_function_call("parse_resume", {
                            "resume_text": content[:10000],
                            "resume_file": file_obj
                        })

                        # Add the assistant's detailed response to conversation history
                        if output:
                            session['conversation_history'].append({"role": "assistant", "content": output})
                            session.modified = True

                        # Clean up temp session data
                        if 'temp_resume_file' in session:
                            session.pop('temp_resume_file')
                            session.modified = True

                except Exception as e:
                    logger.error(f"❌ Unexpected file upload error: {e}", exc_info=True)
                    output = f"❌ Error processing file: {str(e)}\n\nPlease try again or use a different file format."
                    session['conversation_history'].append({"role": "assistant", "content": output})
                    session.modified = True
            else:
                output = "❌ No file selected or file is empty."
                logger.warning("⚠️ No file or filename provided")
                session['conversation_history'].append({"role": "user", "content": "Attempted to upload resume"})
                session['conversation_history'].append({"role": "assistant", "content": output})
                session.modified = True
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
            # Redirect to original URL if set, otherwise go to index
            next_url = session.pop('next_url', None)
            if next_url:
                logger.info(f"↩️ Redirecting to saved URL: {next_url}")
                return redirect(next_url)
            return redirect(url_for('index'))
        else:
            error_msg = handle_failed_login(request.remote_addr)
            logger.warning(f"🚫 FAILED LOGIN: {request.remote_addr}")
            return render_template_string(LOGIN_TEMPLATE, error=error_msg)
    
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout')
def logout():
    session.clear()
    logger.info(f"User logged out from {request.remote_addr}")
    return redirect(url_for('login'))

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
    return redirect(url_for('index'))

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

@app.route('/quickadd/extension')
def quickadd_extension():
    """Serve the Quick Add Chrome extension zip file"""
    if not session.get('authenticated'):
        return redirect(url_for('login'))
    return send_file(
        '/opt/copilot/quickadd-extension.zip',
        mimetype='application/zip',
        as_attachment=True,
        download_name='quickadd-extension.zip'
    )

@app.route('/quickadd', methods=['GET', 'POST'])
def quickadd():
    """Quick add contact from bookmarklet - parses highlighted text"""

    # Check authentication
    if not session.get('authenticated'):
        token = request.args.get('token')
        if token == AUTH_TOKEN:
            session['authenticated'] = True
            session.permanent = True
            session.modified = True
        else:
            return redirect(url_for('login'))

    result = None
    parsed_data = None
    error = None

    if request.method == 'POST':
        text = request.form.get('text', '')
        contact_type = request.form.get('contact_type', 'candidate')  # candidate or client
        action = request.form.get('action', 'parse')  # parse or create

        if action == 'parse' and text:
            # Use AI to parse the text
            try:
                parse_prompt = f"""Extract contact information from this text. Return JSON with these fields (use null for missing):
- firstName
- lastName
- emailAddress (PRIMARY email - use work email if available, otherwise first one found)
- phoneNumber (PRIMARY phone - use mobile if available, otherwise first one found)
- additionalEmails (array of any OTHER emails found, empty array if none)
- additionalPhones (array of any OTHER phones found, empty array if none)
- cCurrentTitle (job title)
- cCurrentCompany (company name)
- cLinkedInURL (if present)
- cSkills (comma-separated if mentioned)
- addressCity
- addressState

Text to parse:
{text}

Return ONLY valid JSON, no explanation."""

                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[{"role": "user", "content": parse_prompt}],
                    temperature=0.3,
                    timeout=15
                )

                json_str = response.choices[0].message.content.strip()
                # Clean up markdown code blocks if present
                if json_str.startswith('```'):
                    json_str = json_str.split('\n', 1)[1]
                    json_str = json_str.rsplit('```', 1)[0]

                parsed_data = json.loads(json_str)
                parsed_data['_original_text'] = text
                parsed_data['_contact_type'] = contact_type

            except Exception as e:
                logger.error(f"Parse error: {e}")
                error = f"Failed to parse text: {str(e)}"

        elif action == 'create':
            # Create the contact in CRM
            try:
                first_name = request.form.get('firstName', '').strip()
                last_name = request.form.get('lastName', '').strip()

                if not first_name or not last_name:
                    error = "First name and last name are required"
                else:
                    contact_data = {
                        'firstName': first_name,
                        'lastName': last_name,
                    }

                    # Add optional fields
                    if request.form.get('emailAddress'):
                        contact_data['emailAddress'] = request.form.get('emailAddress')
                    if request.form.get('phoneNumber'):
                        phone_data = create_phone_number_data(request.form.get('phoneNumber'), "Mobile", True)
                        if phone_data:
                            contact_data['phoneNumberData'] = phone_data
                    if request.form.get('cCurrentTitle'):
                        contact_data['cCurrentTitle'] = request.form.get('cCurrentTitle')
                    if request.form.get('cCurrentCompany'):
                        contact_data['cCurrentCompany'] = request.form.get('cCurrentCompany')
                    if request.form.get('cLinkedInURL'):
                        contact_data['cLinkedInURL'] = request.form.get('cLinkedInURL')
                    if request.form.get('cSkills'):
                        contact_data['cSkills'] = request.form.get('cSkills')
                    if request.form.get('addressCity'):
                        contact_data['addressCity'] = request.form.get('addressCity')
                    if request.form.get('addressState'):
                        contact_data['addressState'] = request.form.get('addressState')

                    # Set candidate/client flag
                    is_candidate = request.form.get('contact_type') == 'candidate'
                    contact_data['cIsCandidate'] = is_candidate

                    # Create or update contact
                    result_msg, contact_id = crm_manager.create_contact(**contact_data)

                    extra_actions = []

                    # Add note if provided
                    note_content = request.form.get('note', '').strip()
                    if note_content and contact_id:
                        try:
                            note_result = crm_manager.add_note(
                                contact_id=contact_id,
                                note_content=note_content
                            )
                            extra_actions.append("📝 Note added")
                        except Exception as e:
                            logger.error(f"Failed to add note: {e}")
                            extra_actions.append("⚠️ Note failed")

                    # Add additional emails/phones as note
                    additional_emails = request.form.get('additionalEmails', '').strip()
                    additional_phones = request.form.get('additionalPhones', '').strip()
                    if (additional_emails or additional_phones) and contact_id:
                        extras_note = []
                        if additional_emails:
                            extras_note.append(f"Additional emails:\n{additional_emails}")
                        if additional_phones:
                            extras_note.append(f"Additional phones:\n{additional_phones}")
                        if extras_note:
                            try:
                                crm_manager.add_note(
                                    contact_id=contact_id,
                                    note_content="\n\n".join(extras_note)
                                )
                                extra_actions.append("📱 Extra contact info added")
                            except Exception as e:
                                logger.error(f"Failed to add extras note: {e}")

                    # Auto-create/link company for CLIENT contacts only
                    company_name = request.form.get('cCurrentCompany', '').strip()
                    if not is_candidate and company_name and contact_id:
                        try:
                            # Search for existing account
                            accounts = crm_manager.search_accounts(company_name)

                            if accounts:
                                # Account exists - link contact to it
                                account_id = accounts[0]['id']
                                logger.info(f"Found existing account: {company_name} ({account_id})")
                            else:
                                # Create new account - returns (message, account_id) tuple
                                msg, new_account_id = crm_manager.create_account(name=company_name)
                                if new_account_id:
                                    account_id = new_account_id
                                    logger.info(f"Created new account: {company_name} ({account_id})")
                                    extra_actions.append(f"🏢 Created company: {company_name}")
                                else:
                                    account_id = None
                                    logger.error(f"Failed to create account: {company_name} - {msg}")

                            # Link contact to account
                            if account_id:
                                success, error_msg = crm_manager.update_contact_simple(contact_id, {'accountId': account_id})
                                if success:
                                    extra_actions.append(f"🔗 Linked to {company_name}")
                                else:
                                    logger.error(f"Failed to link contact to account: {error_msg}")
                        except Exception as e:
                            logger.error(f"Failed to process company association: {e}")

                    # Create task if provided
                    task_name = request.form.get('taskName', '').strip()
                    if task_name and contact_id:
                        try:
                            task_due = request.form.get('taskDueDate', '')
                            task_assign = request.form.get('taskAssignTo', 'Steve')
                            task_result = crm_manager.create_task(
                                name=task_name,
                                assigned_to=task_assign,
                                due_date=task_due if task_due else None,
                                related_contact=f"{first_name} {last_name}"
                            )
                            extra_actions.append(f"✅ Task assigned to {task_assign}")
                        except Exception as e:
                            logger.error(f"Failed to create task: {e}")
                            extra_actions.append("⚠️ Task failed")

                    # Build final message
                    final_msg = result_msg
                    if extra_actions:
                        final_msg += "\n\n" + " | ".join(extra_actions)

                    # Use the actual result message which includes duplicate/update info
                    # Include contact info for Quick Email button
                    result = {
                        'success': True,
                        'message': final_msg,
                        'contact_id': contact_id,
                        'first_name': first_name,
                        'last_name': last_name,
                        'email_address': request.form.get('emailAddress', ''),
                        'title': request.form.get('cCurrentTitle', ''),
                        'company': request.form.get('cCurrentCompany', ''),
                        'skills': request.form.get('cSkills', ''),
                        'contact_type': contact_type
                    }

            except Exception as e:
                logger.error(f"Create error: {e}")
                error = f"Failed to create contact: {str(e)}"

    # Get text from query param (from bookmarklet)
    initial_text = request.args.get('text', '')

    from templates import QUICKADD_TEMPLATE
    return render_template_string(QUICKADD_TEMPLATE,
                                  initial_text=initial_text,
                                  parsed_data=parsed_data,
                                  result=result,
                                  error=error,
                                  auth_token=AUTH_TOKEN)


@app.route('/quickemail', methods=['GET', 'POST'])
def quickemail():
    """Quick email composer with AI generation - sends through CRM"""

    # Check authentication
    if not session.get('authenticated'):
        token = request.args.get('token')
        if token == AUTH_TOKEN:
            session['authenticated'] = True
            session.permanent = True
            session.modified = True
        else:
            return redirect(url_for('login'))

    result = None
    error = None
    generated_email = None

    # Get contact info from query params
    contact_id = request.args.get('contact_id', '')
    first_name = request.args.get('firstName', '')
    last_name = request.args.get('lastName', '')
    email_address = request.args.get('email', '')
    title = request.args.get('title', '')
    company = request.args.get('company', '')
    skills = request.args.get('skills', '')
    contact_type = request.args.get('type', 'candidate')  # candidate or client

    if request.method == 'POST':
        action = request.form.get('action', 'generate')

        if action == 'generate':
            # Generate email with AI
            try:
                # Load the email generation prompt
                prompt_path = Path(__file__).parent / 'EMAIL_GENERATION_PROMPT.md'
                email_prompt_guide = ""
                if prompt_path.exists():
                    email_prompt_guide = prompt_path.read_text()

                # Get form values (may have been edited)
                first_name = request.form.get('firstName', first_name)
                last_name = request.form.get('lastName', last_name)
                email_address = request.form.get('email', email_address)
                title = request.form.get('title', title)
                company = request.form.get('company', company)
                skills = request.form.get('skills', skills)
                contact_type = request.form.get('contact_type', contact_type)
                custom_context = request.form.get('custom_context', '')
                send_as = request.form.get('send_as', 'staylor@fluencydigital.io')
                selected_template_id = request.form.get('selected_template_id', '')

                # Get recent emails for AI to learn from
                recent_emails = get_recent_emails()
                recent_emails_text = ""
                if recent_emails:
                    recent_emails_text = "\n\n--- RECENT EMAILS (use these as style examples) ---\n"
                    for i, email in enumerate(recent_emails[:5], 1):
                        recent_emails_text += f"\nExample {i}:\nTo: {email.get('to', 'N/A')}\nSubject: {email.get('subject', 'N/A')}\nBody: {email.get('body', 'N/A')[:300]}...\n"

                # Get persistent AI context
                ai_context = get_ai_context()
                ai_context_text = ""
                if ai_context:
                    ai_context_text = f"\n\n--- CURRENT CONTEXT (consider mentioning if relevant) ---\n{ai_context}\n"

                # Determine sender name for sign-off
                sender_names = {
                    'staylor@fluencydigital.io': ('Stephen', '-ST or -Stephen'),
                    'staylor@fluencycare.com': ('Steve', '-Steve'),
                    'aaron.black@fluencydigital.io': ('Aaron', '-Aaron')
                }
                sender_first, sender_signoff = sender_names.get(send_as, ('Stephen', '-Stephen'))

                generation_prompt = f"""You are writing an outreach email for Fluency Digital.
Sender: {sender_first} ({send_as})

{email_prompt_guide}
{recent_emails_text}{ai_context_text}
---

Generate an email for this contact:
- Name: {first_name} {last_name}
- Email: {email_address}
- Title: {title}
- Company: {company}
- Skills: {skills}
- Type: {contact_type} (candidate = job seeker, client = potential hiring client)
{f"- Additional context: {custom_context}" if custom_context else ""}

Generate a personalized outreach email. Use their title/company/skills to make it relevant.
IMPORTANT: Match the style/tone of the recent emails above if provided.

Return JSON only:
{{
  "subject": "Short subject line",
  "body": "Email body with proper line breaks. Use their first name. Keep it under 100 words. Sign off as {sender_signoff}"
}}"""

                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[{"role": "user", "content": generation_prompt}],
                    temperature=0.7,
                    timeout=20
                )

                json_str = response.choices[0].message.content.strip()
                # Clean up markdown code blocks if present
                if json_str.startswith('```'):
                    json_str = json_str.split('\n', 1)[1]
                    json_str = json_str.rsplit('```', 1)[0]

                generated_email = json.loads(json_str)

            except Exception as e:
                logger.error(f"Email generation error: {e}")
                error = f"Failed to generate email: {str(e)}"

        elif action == 'send':
            # Send the email through CRM
            try:
                subject = request.form.get('subject', '').strip()
                body = request.form.get('body', '').strip()
                to_email = request.form.get('to_email', '').strip()
                contact_id = request.form.get('contact_id', '').strip()

                if not subject or not body or not to_email:
                    error = "Subject, body, and recipient email are required"
                else:
                    # Convert plain text body to HTML
                    html_body = body.replace('\n', '<br>\n')
                    html_body = f"<p>{html_body}</p>"

                    # Get selected sender
                    send_as = request.form.get('send_as', 'staylor@fluencydigital.io')

                    # Email signatures for each sender
                    signatures = {
                        'staylor@fluencydigital.io': '''<table style="font-family: Arial, sans-serif; font-size: 14px; color: #222;">
  <tbody><tr>
    <td style="border-left: 3px solid #21a0e7; padding-left: 8px;">
      <div style="font-size: 16px; font-weight: bold; color: #4a90e2;">Stephen Taylor</div>
      <div style="margin-bottom: 8px;">Fluency Digital Inc.</div>
      <div><a href="tel:+16126182291" style="color: #333; text-decoration: none;">612-618-2291</a></div>
      <div><a href="mailto:staylor@fluencydigital.io" style="color: #333; font-weight: bold; text-decoration: none;">staylor@fluencydigital.io</a></div>
      <div><a href="https://www.linkedin.com/in/stephentaylor" style="color: #333; font-weight: bold;">LinkedIn</a></div>
    </td></tr></tbody></table>''',
                        'staylor@fluencycare.com': '''<table style="font-family: Arial, sans-serif; font-size: 14px; color: #222;">
  <tbody><tr>
    <td style="border-left: 3px solid #21a0e7; padding-left: 8px;">
      <div style="font-size: 16px; font-weight: bold; color: #4a90e2;">Steve Taylor</div>
      <div style="margin-bottom: 8px;">FluencyCare</div>
      <div><a href="tel:+16126182291" style="color: #333; text-decoration: none;">612-618-2291</a></div>
      <div><a href="mailto:staylor@fluencycare.com" style="color: #333; font-weight: bold; text-decoration: none;">staylor@fluencycare.com</a></div>
      <div><a href="https://www.linkedin.com/in/stephentaylor" style="color: #333; font-weight: bold;">LinkedIn</a></div>
    </td></tr></tbody></table>''',
                        'aaron.black@fluencydigital.io': '''<table style="font-family: Arial, sans-serif; font-size: 14px; color: #222;">
  <tbody><tr>
    <td style="border-left: 3px solid #21a0e7; padding-left: 8px;">
      <div style="font-size: 16px; font-weight: bold; color: #4a90e2;">Aaron Black</div>
      <div style="margin-bottom: 8px;">Fluency Digital Inc.</div>
      <div><a href="mailto:aaron.black@fluencydigital.io" style="color: #333; font-weight: bold; text-decoration: none;">aaron.black@fluencydigital.io</a></div>
      <div><a href="https://www.linkedin.com/in/aaronblack" style="color: #333; font-weight: bold;">LinkedIn</a></div>
    </td></tr></tbody></table>'''
                    }

                    signature_html = signatures.get(send_as, signatures['staylor@fluencydigital.io'])
                    html_body = html_body + "<br>\n" + signature_html

                    # Create email in CRM as draft
                    email_data = {
                        "status": "Draft",
                        "to": to_email,
                        "subject": subject,
                        "body": html_body,
                        "isHtml": True,
                        "from": send_as
                    }

                    # Link to contact if we have the ID
                    if contact_id:
                        email_data["parentId"] = contact_id
                        email_data["parentType"] = "Contact"

                    # Create the email using direct API call
                    import requests as req
                    api_url = crm_manager.espocrm_url
                    api_headers = crm_manager.headers

                    create_resp = req.post(f"{api_url}/Email", json=email_data, headers=api_headers)
                    create_result = create_resp.json() if create_resp.ok else None

                    if create_result and 'id' in create_result:
                        email_id = create_result['id']

                        # Send the email by setting status to Sending
                        send_resp = req.put(f"{api_url}/Email/{email_id}", json={"status": "Sending"}, headers=api_headers)
                        send_result = send_resp.json() if send_resp.ok else None

                        if send_result and send_result.get('status') == 'Sent':
                            result = {
                                'success': True,
                                'message': f"Email sent to {to_email}",
                                'email_id': email_id
                            }
                            # Save to email memory for AI learning
                            save_sent_email(to_email, subject, body, send_as)
                        else:
                            error = "Email created but failed to send"
                    else:
                        error = "Failed to create email in CRM"

            except Exception as e:
                logger.error(f"Send email error: {e}")
                error = f"Failed to send email: {str(e)}"

    from templates import QUICKEMAIL_TEMPLATE
    recent_emails = get_recent_emails()
    ai_context = get_ai_context()
    email_templates = get_email_templates()
    selected_template_id = request.form.get('selected_template_id', '') if request.method == 'POST' else ''
    return render_template_string(QUICKEMAIL_TEMPLATE,
                                  contact_id=contact_id,
                                  first_name=first_name,
                                  last_name=last_name,
                                  email_address=email_address,
                                  title=title,
                                  company=company,
                                  skills=skills,
                                  contact_type=contact_type,
                                  generated_email=generated_email,
                                  result=result,
                                  error=error,
                                  recent_emails=recent_emails,
                                  ai_context=ai_context,
                                  email_templates=email_templates,
                                  selected_template_id=selected_template_id,
                                  auth_token=AUTH_TOKEN)


@app.route('/quickemail/templates', methods=['GET', 'POST', 'PUT', 'DELETE'])
def email_templates_api():
    """API for managing email templates"""

    # Check authentication - check session, query params, form data, or JSON body
    if not session.get('authenticated'):
        token = request.args.get('token') or request.form.get('token')
        # Also check JSON body for token
        if not token and request.is_json:
            try:
                token = request.get_json().get('token')
            except:
                pass
        if token == AUTH_TOKEN:
            session['authenticated'] = True
        else:
            return json.dumps({'error': 'Unauthorized'}), 401, {'Content-Type': 'application/json'}

    if request.method == 'GET':
        # Return all templates
        templates = get_email_templates()
        return json.dumps(templates), 200, {'Content-Type': 'application/json'}

    elif request.method == 'POST':
        # Save new template
        try:
            data = request.get_json() if request.is_json else request.form.to_dict()
            template = {
                'name': data.get('name', 'Untitled'),
                'type': data.get('type', 'full'),  # 'full' or 'prompt'
                'subject': data.get('subject', ''),
                'body': data.get('body', ''),
                'prompt': data.get('prompt', ''),
                'contact_type': data.get('contact_type', 'any')  # 'candidate', 'client', or 'any'
            }
            saved = save_email_template(template)
            if saved:
                return json.dumps(saved), 200, {'Content-Type': 'application/json'}
            return json.dumps({'error': 'Failed to save'}), 500, {'Content-Type': 'application/json'}
        except Exception as e:
            return json.dumps({'error': str(e)}), 500, {'Content-Type': 'application/json'}

    elif request.method == 'PUT':
        # Update existing template
        try:
            data = request.get_json() if request.is_json else request.form.to_dict()
            template = {
                'id': data.get('id'),
                'name': data.get('name', 'Untitled'),
                'type': data.get('type', 'full'),
                'subject': data.get('subject', ''),
                'body': data.get('body', ''),
                'prompt': data.get('prompt', ''),
                'contact_type': data.get('contact_type', 'any')
            }
            if not template['id']:
                return json.dumps({'error': 'Template ID required'}), 400, {'Content-Type': 'application/json'}
            saved = save_email_template(template)
            if saved:
                return json.dumps(saved), 200, {'Content-Type': 'application/json'}
            return json.dumps({'error': 'Failed to update'}), 500, {'Content-Type': 'application/json'}
        except Exception as e:
            return json.dumps({'error': str(e)}), 500, {'Content-Type': 'application/json'}

    elif request.method == 'DELETE':
        # Delete template
        template_id = request.args.get('id') or (request.get_json() or {}).get('id')
        if template_id and delete_email_template(template_id):
            return json.dumps({'success': True}), 200, {'Content-Type': 'application/json'}
        return json.dumps({'error': 'Template not found'}), 404, {'Content-Type': 'application/json'}


@app.route('/quickadd/task', methods=['POST'])
def quickadd_task():
    """API to create a task for a contact"""

    # Check authentication
    if not session.get('authenticated'):
        token = request.form.get('token') or (request.get_json() or {}).get('token')
        if token == AUTH_TOKEN:
            session['authenticated'] = True
        else:
            return json.dumps({'error': 'Unauthorized'}), 401, {'Content-Type': 'application/json'}

    try:
        data = request.get_json() if request.is_json else request.form.to_dict()
        task_name = data.get('taskName', '').strip()
        task_due = data.get('taskDueDate', '')
        task_assign = data.get('taskAssignTo', 'Stephen')
        contact_name = data.get('contactName', '')

        if not task_name:
            return json.dumps({'error': 'Task name required'}), 400, {'Content-Type': 'application/json'}

        task_result = crm_manager.create_task(
            name=task_name,
            assigned_to=task_assign,
            due_date=task_due if task_due else None,
            related_contact=contact_name if contact_name else None
        )

        return json.dumps({'success': True, 'message': f'Task assigned to {task_assign}'}), 200, {'Content-Type': 'application/json'}
    except Exception as e:
        logger.error(f"Failed to create task: {e}")
        return json.dumps({'error': str(e)}), 500, {'Content-Type': 'application/json'}


@app.route('/quickemail/templates/manage', methods=['GET'])
def manage_templates():
    """Simple UI for viewing and deleting email templates"""

    # Check authentication
    if not session.get('authenticated'):
        token = request.args.get('token')
        if token == AUTH_TOKEN:
            session['authenticated'] = True
            session.permanent = True
        else:
            return redirect(f'/quickadd?token={request.args.get("token", "")}')

    templates = get_email_templates()

    html = '''
<!doctype html>
<html>
<head>
    <title>Email Templates</title>
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
            max-width: 600px;
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
        .header h1 { font-size: 20px; font-weight: 600; }
        .content { padding: 20px; }
        .template-card {
            background: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 12px;
        }
        .template-card:hover { border-color: #4BA3C3; }
        .template-name { font-weight: 600; color: #1E293B; }
        .template-meta { font-size: 12px; color: #64748B; margin-top: 4px; }
        .template-preview { font-size: 12px; color: #475569; margin-top: 8px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 500;
        }
        .badge-candidate { background: #DCFCE7; color: #166534; }
        .badge-client { background: #DBEAFE; color: #1E40AF; }
        .badge-any { background: #F3E8FF; color: #7C3AED; }
        .badge-prompt { background: #FEF3C7; color: #92400E; }
        .btn-group { float: right; }
        .edit-btn, .delete-btn {
            background: #E0E7FF;
            color: #4338CA;
            border: none;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 12px;
            cursor: pointer;
            margin-left: 4px;
        }
        .edit-btn:hover { background: #C7D2FE; }
        .delete-btn { background: #FEE2E2; color: #DC2626; }
        .delete-btn:hover { background: #FECACA; }
        .empty { text-align: center; color: #64748B; padding: 40px; }
        .close-btn { display: block; text-align: center; color: #64748B; margin-top: 16px; text-decoration: none; }
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000; align-items: center; justify-content: center; }
        .modal-content { background: white; padding: 24px; border-radius: 12px; max-width: 500px; width: 90%; max-height: 90vh; overflow-y: auto; }
        .modal h3 { margin-bottom: 16px; font-size: 18px; }
        .form-group { margin-bottom: 14px; }
        .form-group label { display: block; font-size: 12px; font-weight: 600; color: #64748B; margin-bottom: 6px; }
        .form-group input, .form-group select, .form-group textarea {
            width: 100%; padding: 10px; border: 2px solid #E2E8F0; border-radius: 8px; font-size: 14px;
        }
        .form-group textarea { min-height: 80px; resize: vertical; }
        .modal-buttons { display: flex; gap: 10px; margin-top: 16px; }
        .modal-buttons button { flex: 1; padding: 12px; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; }
        .save-btn { background: linear-gradient(135deg, #22C55E, #16A34A); color: white; }
        .cancel-btn { background: #E2E8F0; color: #475569; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Email Templates</h1>
        </div>
        <div class="content">
            <div id="templateList"></div>
            <a href="javascript:window.close()" class="close-btn">Close</a>
        </div>
    </div>

    <div class="modal" id="editModal">
        <div class="modal-content">
            <h3>Edit Template</h3>
            <input type="hidden" id="editId">
            <div class="form-group">
                <label>Name</label>
                <input type="text" id="editName">
            </div>
            <div class="form-group">
                <label>Type</label>
                <select id="editType" onchange="toggleEditFields()">
                    <option value="full">Full Email (subject + body)</option>
                    <option value="prompt">AI Prompt (instructions)</option>
                </select>
            </div>
            <div class="form-group">
                <label>Use For</label>
                <select id="editContactType">
                    <option value="any">Any (Candidate & Client)</option>
                    <option value="candidate">Candidates Only</option>
                    <option value="client">Clients Only</option>
                </select>
            </div>
            <div id="fullFields">
                <div class="form-group">
                    <label>Subject</label>
                    <input type="text" id="editSubject">
                </div>
                <div class="form-group">
                    <label>Body</label>
                    <textarea id="editBody" rows="6"></textarea>
                </div>
            </div>
            <div id="promptFields" style="display:none;">
                <div class="form-group">
                    <label>AI Prompt</label>
                    <textarea id="editPrompt" rows="6" placeholder="Instructions for AI..."></textarea>
                </div>
            </div>
            <div class="modal-buttons">
                <button class="save-btn" onclick="saveEdit()">Save</button>
                <button class="cancel-btn" onclick="hideEditModal()">Cancel</button>
            </div>
        </div>
    </div>

    <script>
        var templates = ''' + json.dumps(templates) + ''';

        function renderTemplates() {
            var container = document.getElementById('templateList');
            if (templates.length === 0) {
                container.innerHTML = '<div class="empty">No templates saved yet.<br>Save templates from Quick Email.</div>';
                return;
            }
            var html = '';
            templates.forEach(function(t, idx) {
                var typeBadge = t.contact_type === 'candidate' ? '<span class="badge badge-candidate">Candidate</span>' :
                               t.contact_type === 'client' ? '<span class="badge badge-client">Client</span>' :
                               '<span class="badge badge-any">Any</span>';
                var promptBadge = t.type === 'prompt' ? ' <span class="badge badge-prompt">AI Prompt</span>' : '';
                var preview = t.type === 'prompt' ? t.prompt : t.subject;
                html += '<div class="template-card" id="tmpl-' + t.id + '">' +
                    '<div class="btn-group">' +
                    '<button class="edit-btn" onclick="editTemplate(' + idx + ')">Edit</button>' +
                    '<button class="delete-btn" onclick="deleteTemplate(\\'' + t.id + '\\')">Delete</button>' +
                    '</div>' +
                    '<div class="template-name">' + escapeHtml(t.name) + '</div>' +
                    '<div class="template-meta">' + typeBadge + promptBadge + '</div>' +
                    '<div class="template-preview">' + escapeHtml(preview || '(no preview)') + '</div>' +
                    '</div>';
            });
            container.innerHTML = html;
        }

        function escapeHtml(str) {
            if (!str) return '';
            return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        }

        function editTemplate(idx) {
            var t = templates[idx];
            document.getElementById('editId').value = t.id;
            document.getElementById('editName').value = t.name || '';
            document.getElementById('editType').value = t.type || 'full';
            document.getElementById('editContactType').value = t.contact_type || 'any';
            document.getElementById('editSubject').value = t.subject || '';
            document.getElementById('editBody').value = t.body || '';
            document.getElementById('editPrompt').value = t.prompt || '';
            toggleEditFields();
            document.getElementById('editModal').style.display = 'flex';
        }

        function toggleEditFields() {
            var isPrompt = document.getElementById('editType').value === 'prompt';
            document.getElementById('fullFields').style.display = isPrompt ? 'none' : 'block';
            document.getElementById('promptFields').style.display = isPrompt ? 'block' : 'none';
        }

        function hideEditModal() {
            document.getElementById('editModal').style.display = 'none';
        }

        function saveEdit() {
            var data = {
                id: document.getElementById('editId').value,
                name: document.getElementById('editName').value,
                type: document.getElementById('editType').value,
                contact_type: document.getElementById('editContactType').value,
                subject: document.getElementById('editSubject').value,
                body: document.getElementById('editBody').value,
                prompt: document.getElementById('editPrompt').value
            };
            fetch('/quickemail/templates', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            })
            .then(function(r) { return r.json(); })
            .then(function(saved) {
                if (saved.id) {
                    templates = templates.map(function(t) { return t.id === saved.id ? saved : t; });
                    renderTemplates();
                    hideEditModal();
                } else {
                    alert('Failed to save: ' + (saved.error || 'Unknown error'));
                }
            });
        }

        function deleteTemplate(id) {
            if (!confirm('Delete this template?')) return;
            fetch('/quickemail/templates?id=' + id, { method: 'DELETE' })
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    if (data.success) {
                        document.getElementById('tmpl-' + id).remove();
                        templates = templates.filter(function(t) { return t.id !== id; });
                        if (templates.length === 0) renderTemplates();
                    } else {
                        alert('Failed to delete: ' + (data.error || 'Unknown error'));
                    }
                });
        }

        renderTemplates();
    </script>
</body>
</html>
'''
    return html


@app.route('/quickcontext', methods=['GET', 'POST'])
def quickcontext():
    """Edit persistent AI context notes"""

    # Check authentication
    if not session.get('authenticated'):
        token = request.args.get('token')
        if token == AUTH_TOKEN:
            session['authenticated'] = True
            session.permanent = True
            session.modified = True
        else:
            return redirect(url_for('login'))

    saved = False
    if request.method == 'POST':
        context = request.form.get('context', '')
        if save_ai_context(context):
            saved = True

    current_context = get_ai_context()

    CONTEXT_TEMPLATE = '''
<!doctype html>
<html>
<head>
    <title>📝 AI Context Notes</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #7C3AED 0%, #A78BFA 100%);
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
            background: linear-gradient(135deg, #7C3AED, #A78BFA);
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
        }
        textarea {
            width: 100%;
            padding: 12px;
            border: 2px solid #E2E8F0;
            border-radius: 8px;
            font-size: 14px;
            min-height: 200px;
            resize: vertical;
            font-family: inherit;
            line-height: 1.5;
        }
        textarea:focus {
            outline: none;
            border-color: #7C3AED;
        }
        .btn {
            width: 100%;
            padding: 14px;
            border: none;
            border-radius: 8px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            background: linear-gradient(135deg, #7C3AED, #A78BFA);
            color: white;
            margin-bottom: 10px;
        }
        .btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(124, 58, 237, 0.3);
        }
        .success {
            background: #DCFCE7;
            color: #166534;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 16px;
            text-align: center;
            font-weight: 500;
        }
        .help-text {
            font-size: 12px;
            color: #64748B;
            margin-top: 8px;
            line-height: 1.5;
        }
        .close-btn {
            display: block;
            text-align: center;
            padding: 12px;
            color: #64748B;
            text-decoration: none;
            font-size: 13px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📝 AI Context Notes</h1>
            <p>Persistent notes the AI always sees when generating emails</p>
        </div>
        <div class="content">
            {% if saved %}
            <div class="success">✅ Context saved!</div>
            {% endif %}

            <form method="POST">
                <div class="form-group">
                    <label>Context Notes</label>
                    <textarea name="context" placeholder="Add context the AI should always know about...

Examples:
• We just released our Winter 2025 newsletter
• Currently hiring for 3 ML Engineer roles
• New partnership with TechCorp announced
• Holiday office closure Dec 23-Jan 2
• Mention our new AI recruiting tools">{{ current_context }}</textarea>
                    <p class="help-text">
                        These notes are included in EVERY email generation. Use for current events,
                        campaigns, talking points, or anything you want the AI to potentially reference.
                    </p>
                </div>

                <button type="submit" class="btn">💾 Save Context</button>
            </form>

            <a href="javascript:window.close()" class="close-btn">Close Window</a>
        </div>
    </div>
</body>
</html>
'''
    return render_template_string(CONTEXT_TEMPLATE, current_context=current_context, saved=saved)


if __name__ == '__main__':
    print("🚀 Starting EspoCRM AI Copilot - AI-FIRST VERSION")
    print("✨ Features: Intelligent intent understanding")
    print("🤖 Approach: Let AI do the thinking, we do the executing")
    print(f"🌐 Visit: http://localhost:5000")
    print(f"🔒 Use login form with access token")
    app.run(host="0.0.0.0", port=5000, debug=True)
