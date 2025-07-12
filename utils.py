# utils.py
# Utility functions for FluencyCare Copilot

import re
import html
import logging
import time
import requests
from typing import List, Dict, Any, Optional, Tuple
from flask import session

logger = logging.getLogger(__name__)

# Input processing
def sanitize_input(text):
    """Sanitize user input"""
    if not text:
        return text
    return html.escape(str(text).strip())

# Phone number formatting functions
def format_phone_for_crm(phone_string: str) -> str:
    """Format phone number for EspoCRM Phone field validation - try multiple formats"""
    if not phone_string:
        return ""
    
    # Extract digits only
    digits_only = re.sub(r'[^\d]', '', str(phone_string))
    
    if len(digits_only) == 10:
        # Return the dash format (most common)
        return f"{digits_only[:3]}-{digits_only[3:6]}-{digits_only[6:]}"
    elif len(digits_only) == 11 and digits_only.startswith('1'):
        # Remove country code and format
        digits_only = digits_only[1:]
        return f"{digits_only[:3]}-{digits_only[3:6]}-{digits_only[6:]}"
    elif len(digits_only) >= 10:
        # For longer numbers, try to format the last 10 digits
        last_10 = digits_only[-10:]
        return f"{last_10[:3]}-{last_10[3:6]}-{last_10[6:]}"
    else:
        # If less than 10 digits, return digits only
        return digits_only

def create_phone_number_data(phone_string: str, phone_type: str = "Mobile", is_primary: bool = True) -> List[Dict[str, Any]]:
    """Create EspoCRM phoneNumberData structure"""
    if not phone_string:
        return []
    
    # Clean the phone number
    phone_clean = str(phone_string).strip()
    digits_only = re.sub(r'[^\d]', '', phone_clean)
    
    logger.info(f"Creating phoneNumberData from: '{phone_string}' -> digits: '{digits_only}'")
    
    if len(digits_only) >= 10:
        # Use a clean, standard format
        if len(digits_only) == 10:
            formatted_phone = f"{digits_only[:3]}-{digits_only[3:6]}-{digits_only[6:]}"
        elif len(digits_only) == 11 and digits_only.startswith('1'):
            # Remove country code
            digits_only = digits_only[1:]
            formatted_phone = f"{digits_only[:3]}-{digits_only[3:6]}-{digits_only[6:]}"
        else:
            formatted_phone = phone_clean  # Keep original if unusual format
        
        phone_data = {
            "phoneNumber": formatted_phone,
            "type": phone_type,
            "primary": is_primary,
            "optOut": False,
            "invalid": False
        }
        
        logger.info(f"Created phoneNumberData: {phone_data}")
        return [phone_data]
    
    logger.warning(f"Phone number too short: {len(digits_only)} digits")
    return []

def test_phone_formats_with_crm(phone_string: str, contact_id: str, espocrm_url: str, headers: Dict[str, str]) -> Tuple[Optional[str], str]:
    """Test different phone formats with actual CRM"""
    if not phone_string or not contact_id:
        return None, "No phone or contact ID provided"
    
    digits_only = re.sub(r'[^\d]', '', str(phone_string))
    if len(digits_only) < 10:
        return None, f"Invalid phone number length: {len(digits_only)} digits"
    
    # Test formats for simple phoneNumber field first
    test_formats = [
        f"{digits_only[:3]}-{digits_only[3:6]}-{digits_only[6:]}",  # 612-875-4460
        f"({digits_only[:3]}) {digits_only[3:6]}-{digits_only[6:]}",  # (612) 875-4460
        f"{digits_only[:3]}.{digits_only[3:6]}.{digits_only[6:]}",  # 612.875.4460
        f"{digits_only}",  # 6128754460
        f"+1{digits_only}",  # +16128754460
        f"+1-{digits_only[:3]}-{digits_only[3:6]}-{digits_only[6:]}",  # +1-612-875-4460
        f"1-{digits_only[:3]}-{digits_only[3:6]}-{digits_only[6:]}",  # 1-612-875-4460
    ]
    
    logger.info(f"Testing {len(test_formats)} simple phone formats for contact {contact_id}")
    
    # Test simple phoneNumber field first
    for i, test_format in enumerate(test_formats):
        try:
            logger.info(f"Trying simple format {i+1}: '{test_format}'")
            test_update = {'phoneNumber': test_format}
            
            response = requests.put(f"{espocrm_url}/Contact/{contact_id}", 
                                  json=test_update, headers=headers, timeout=10)
            
            if response.status_code in [200, 204]:
                logger.info(f"SUCCESS! Simple format '{test_format}' worked!")
                return test_format, f"Success with simple phoneNumber field: {test_format}"
            else:
                logger.info(f"Simple format '{test_format}' failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error testing simple format '{test_format}': {e}")
            continue
    
    # If simple phoneNumber failed, try phoneNumberData structure
    logger.info("Simple phoneNumber field failed, trying phoneNumberData structure...")
    
    phone_types = ["Mobile", "Work", "Home", "Main", "Other"]
    
    for phone_type in phone_types:
        for test_format in test_formats[:4]:  # Try fewer formats for complex structure
            try:
                logger.info(f"Trying phoneNumberData with type '{phone_type}' and format '{test_format}'")
                
                phone_data = create_phone_number_data(test_format, phone_type, True)
                test_update = {'phoneNumberData': phone_data}
                
                response = requests.put(f"{espocrm_url}/Contact/{contact_id}", 
                                      json=test_update, headers=headers, timeout=10)
                
                if response.status_code in [200, 204]:
                    logger.info(f"SUCCESS! phoneNumberData with type '{phone_type}' and format '{test_format}' worked!")
                    return f"phoneNumberData: {test_format} ({phone_type})", f"Success with phoneNumberData structure: {test_format} as {phone_type}"
                else:
                    logger.info(f"phoneNumberData format failed: {response.status_code}")
                    
            except Exception as e:
                logger.error(f"Error testing phoneNumberData: {e}")
                continue
    
    return None, f"All phone formats failed (tried both phoneNumber and phoneNumberData structures)"

# Input preprocessing
def preprocess_input(user_input: str) -> Dict[str, Any]:
    """
    Extract structured data from natural language input
    FIXED: Don't extract data from 'add' requests (let AI handle those)
    """
    user_input_lower = user_input.lower()
    
    # Skip preprocessing for explicit add requests - let AI handle them
    add_keywords = [
        'add this contact', 'add contact', 'create contact', 'new contact',
        'add this person', 'create this contact', 'add new contact'
    ]
    
    for keyword in add_keywords:
        if keyword in user_input_lower:
            logger.info(f"🔍 PREPROCESS: Detected '{keyword}' - skipping extraction, letting AI handle")
            return {}  # Return empty dict, let AI function calling handle it
    
    logger.info(f"=== PREPROCESS_INPUT DEBUG ===")
    logger.info(f"Input text: {user_input[:100]}...")
    
    updates = {}
    
    # Enhanced phone number patterns
    phone_patterns = [
        r'Phone\s+(\+?[\d\s\-\(\)\.]{10,})\s*\(Mobile\)',  # "Phone 612.875.4460 (Mobile)"
        r'Mobile[:\s]+(\+?[\d\s\-\(\)\.]{10,})',           # "Mobile: 612.875.4460"
        r'Phone[:\s]+(\+?[\d\s\-\(\)\.]{10,})',            # "Phone: 612.875.4460" 
        r'(\+?1?\s*\(?[2-9]\d{2}\)?\s*[\.\-\s]?\d{3}[\.\-\s]?\d{4})'  # General phone pattern
    ]
    
    for pattern in phone_patterns:
        phone_match = re.search(pattern, user_input, re.IGNORECASE)
        if phone_match:
            phone_raw = phone_match.group(1)
            formatted_phone = format_phone_for_crm(phone_raw)
            if formatted_phone and len(re.sub(r'[^\d]', '', formatted_phone)) >= 10:
                updates['phoneNumber'] = formatted_phone
                updates['phoneNumberData'] = create_phone_number_data(formatted_phone, "Mobile", True)
                logger.info(f"Extracted phone - will try both formats: simple='{formatted_phone}' and phoneNumberData structure")
                break
    
    # Enhanced email patterns
    email_patterns = [
        r'Email\s+([\w\.-]+@[\w\.-]+\.\w+)',  # "Email tommoreimi@yahoo.com"
        r'([\w\.-]+@[\w\.-]+\.\w+)',          # General email pattern
    ]
    
    for pattern in email_patterns:
        email_match = re.search(pattern, user_input, re.IGNORECASE)
        if email_match:
            updates['emailAddress'] = email_match.group(1).strip()
            logger.info(f"Extracted email: {email_match.group(1).strip()}")
            break
    
    # Extract LinkedIn URL
    linkedin_match = re.search(r'linkedin\.com/in/([\w\-]+)', user_input, re.IGNORECASE)
    if linkedin_match:
        updates['cLinkedInURL'] = f"https://linkedin.com/in/{linkedin_match.group(1)}"
        logger.info(f"Extracted LinkedIn: https://linkedin.com/in/{linkedin_match.group(1)}")
    
    # Extract title/position
    title_patterns = [
        r'Title[:\s]+(.*?)(?:\n|$)',
        r'Position[:\s]+(.*?)(?:\n|$)',
        r'Role[:\s]+(.*?)(?:\n|$)',
        r'Job[:\s]+(.*?)(?:\n|$)'
    ]
    
    for pattern in title_patterns:
        title_match = re.search(pattern, user_input, re.IGNORECASE)
        if title_match:
            updates['cCurrentTitle'] = title_match.group(1).strip()
            logger.info(f"Extracted title: {title_match.group(1).strip()}")
            break
    
    # Extract address components
    address_match = re.search(r'(\d+\s+[^,\n]+),?\s*([^,\n]+),?\s*([A-Z]{2})\s+(\d{5}(?:-\d{4})?)', user_input)
    if address_match:
        updates['addressStreet'] = address_match.group(1).strip()
        updates['addressCity'] = address_match.group(2).strip()
        updates['addressState'] = address_match.group(3).strip()
        updates['addressPostalCode'] = address_match.group(4).strip()
        updates['addressCountry'] = 'USA'
        logger.info(f"Extracted full address components: {address_match.groups()}")
    else:
        # Try to extract city, state pattern
        city_state_match = re.search(r'(?:address(?:\s+to)?|city)[:;\s]+([A-Za-z\s]+),\s*([A-Z]{2})\b', user_input, re.IGNORECASE)
        if city_state_match:
            updates['addressCity'] = city_state_match.group(1).strip()
            updates['addressState'] = city_state_match.group(2).strip()
            logger.info(f"Extracted city/state: {city_state_match.group(1).strip()}, {city_state_match.group(2).strip()}")
    
    # Extract skills
    skills_patterns = [
        r'Skills?[:\s]+([^\n\r]+)',
        r'Technologies?[:\s]+([^\n\r]+)',
        r'Expertise[:\s]+([^\n\r]+)'
    ]
    
    for pattern in skills_patterns:
        skills_match = re.search(pattern, user_input, re.IGNORECASE)
        if skills_match:
            updates['cSkills'] = skills_match.group(1).strip()
            logger.info(f"Extracted skills: {skills_match.group(1).strip()}")
            break
    
    logger.info(f"Final extracted updates: {updates}")
    return updates

def extract_contact_name_from_update(user_input: str) -> Optional[str]:
    """
    Extract explicit contact name from update requests
    FIXED: Return None for explicit 'add' requests
    """
    user_input_lower = user_input.lower()
    
    # Don't extract names from add requests
    add_keywords = [
        'add this contact', 'add contact', 'create contact', 'new contact',
        'add this person', 'create this contact', 'add new contact'
    ]
    
    for keyword in add_keywords:
        if keyword in user_input_lower:
            logger.info(f"🔍 EXTRACT_NAME: Detected '{keyword}' - not extracting name from add request")
            return None  # Don't extract name from add requests
    
    # Enhanced pronoun patterns
    pronoun_patterns = [
        r'update\s+(?:his|her|their|this)\s+(?:contact|phone|email|linkedin|url|address)',
        r'update\s+(?:him|her|them|this)',
        r'(?:his|her|their)\s+(?:phone|email|contact|linkedin|url|address)',
        r'^(?:his|her|their)\s+(?:phone|email|linkedin|url|address)',
        r'update\s+(?:his|her|their)\s+\w+',
        r'^(?:his|her|their)\s+\w+:',
    ]
    
    for pattern in pronoun_patterns:
        if re.search(pattern, user_input, re.IGNORECASE):
            logger.info("Detected pronoun reference - using current context")
            return "USE_CONTEXT"
    
    # Look for explicit names
    name_patterns = [
        r'update\s+(?:contact\s+)?([A-Za-z\s]+?):\s*',
        r'update\s+([A-Za-z\s]+?)\s*(?:with|to|phone|email|Profile)',
        r'Update\s+([A-Za-z\s]+?):\s*',
        r"([A-Za-z\s]+)'s\s+(?:phone|email|linkedin|address|contact)",
        r'([A-Za-z\s]+)\s+(?:phone|email|linkedin|address):',
    ]
    
    for pattern in name_patterns:
        match = re.search(pattern, user_input, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            if name.lower() not in ['contact', 'the', 'this', 'his', 'her', 'their', 'info', 'profile', 'update']:
                logger.info(f"Extracted explicit contact name: {name}")
                return name
    
    return None

def is_update_intent(user_input: str) -> bool:
    """
    Check if user input indicates update intent
    FIXED: Never return True for explicit 'add' requests
    """
    user_input_lower = user_input.lower()
    
    # CRITICAL: If user explicitly wants to add/create, this is NOT an update
    add_keywords = [
        'add this contact', 'add contact', 'create contact', 'new contact',
        'add this person', 'create this contact', 'add new contact',
        'add:', 'create:', 'new:'
    ]
    
    for keyword in add_keywords:
        if keyword in user_input_lower:
            logger.info(f"🔍 UPDATE_INTENT: Detected '{keyword}' - this is NOT an update")
            return False  # Explicitly NOT an update
    
    # Look for update indicators
    update_keywords = ['update', 'change', 'set', 'add phone', 'add email', 'phone is', 'email is', 'linkedin', 'skills', 'title', 'address', 'street', 'city', 'state', 'zip']
    result = any(keyword in user_input_lower for keyword in update_keywords)
    
    if result:
        logger.info(f"🔍 UPDATE_INTENT: Detected update intent - returning True")
    else:
        logger.info(f"🔍 UPDATE_INTENT: No update intent detected - returning False")
    
    return result

# Session management
def set_last_contact(contact_id: str, name: str):
    """Set the last contact in session"""
    session['last_contact'] = {
        'id': contact_id,
        'name': name,
        'timestamp': time.time()
    }
    session.modified = True
    logger.info(f"Set last contact to: {name} (ID: {contact_id})")

def get_last_contact() -> Optional[Dict[str, Any]]:
    """Get the last contact from session"""
    last_contact = session.get('last_contact')
    if not last_contact:
        return None
    
    # Clear if older than 30 minutes
    if time.time() - last_contact.get('timestamp', 0) > 1800:
        session['last_contact'] = None
        session.modified = True
        return None
    
    return last_contact

def init_session() -> bool:
    """Initialize session"""
    try:
        session.permanent = True
        if 'conversation_history' not in session:
            session['conversation_history'] = []
        if 'last_contact' not in session:
            session['last_contact'] = None
        session['session_test'] = f"Active at {time.time()}"
        session.modified = True
        return True
    except Exception as e:
        logger.error(f"Session init failed: {e}")
        return False
