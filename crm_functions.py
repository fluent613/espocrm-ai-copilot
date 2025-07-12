# crm_functions.py
# Core CRM operations for FluencyCare Copilot

import requests
import logging
import time
import json
import re
from typing import List, Dict, Any, Tuple, Optional
from utils import format_phone_for_crm, create_phone_number_data, test_phone_formats_with_crm

logger = logging.getLogger(__name__)

class CRMManager:
    def __init__(self, espocrm_url: str, headers: Dict[str, str]):
        self.espocrm_url = espocrm_url
        self.headers = headers
    
    def search_contacts_simple(self, criteria: str) -> List[Dict[str, Any]]:
        """Fixed contact search using correct EspoCRM URL parameter format and field names"""
        try:
            logger.info(f"Searching for: '{criteria}' using URL parameter WHERE format")
            
            # Build URL parameters instead of JSON
            params = {
                "select": "id,name,firstName,lastName,emailAddress,phoneNumberData,cSkills,cCurrentTitle,cLinkedInURL,addressStreet,addressCity,addressState,addressPostalCode,addressCountry,cCurrentCompany",
                "maxSize": 20,
                "orderBy": "name"
            }
            
            if "@" in criteria:
                # Email search using URL parameter format
                params.update({
                    "where[0][field]": "emailAddress",
                    "where[0][type]": "contains", 
                    "where[0][value]": criteria
                })
            else:
                name_criteria = criteria.strip()
                parts = name_criteria.split()
                
                if len(parts) == 2:
                    # Search by first AND last name using URL parameters
                    params.update({
                        "where[0][type]": "and",
                        "where[0][value][0][field]": "firstName",
                        "where[0][value][0][type]": "contains",
                        "where[0][value][0][value]": parts[0],
                        "where[0][value][1][field]": "lastName", 
                        "where[0][value][1][type]": "contains",
                        "where[0][value][1][value]": parts[1]
                    })
                else:
                    # Single name - search firstName OR lastName using URL parameters
                    params.update({
                        "where[0][type]": "or",
                        "where[0][value][0][field]": "firstName",
                        "where[0][value][0][type]": "contains",
                        "where[0][value][0][value]": name_criteria,
                        "where[0][value][1][field]": "lastName",
                        "where[0][value][1][type]": "contains", 
                        "where[0][value][1][value]": name_criteria
                    })
            
            full_url = f"{self.espocrm_url}/Contact"
            logger.info(f"Making request to: {full_url}")
            
            response = requests.get(full_url, params=params, headers=self.headers, timeout=10)
            
            logger.info(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                contacts = data.get("list", [])
                total = data.get("total", len(contacts))
                
                logger.info(f"API returned {len(contacts)} contacts (total: {total})")
                return contacts
                
            else:
                logger.error(f"CRM search failed: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []

    def update_contact_simple(self, contact_id: str, updates: Dict[str, Any]) -> Tuple[bool, str]:
        """Simple contact update with detailed debugging and EspoCRM phoneNumberData support"""
        try:
            logger.info(f"=== UPDATE_CONTACT_SIMPLE DEBUG ===")
            logger.info(f"Contact ID: {contact_id}")
            logger.info(f"Updates being sent to CRM: {updates}")
            
            # Special handling for phone number updates - try both approaches
            if 'phoneNumber' in updates or 'phoneNumberData' in updates:
                logger.info(f"Phone number update detected, testing formats...")
                
                # Extract the phone value for testing
                phone_value = updates.get('phoneNumber', '')
                if not phone_value and 'phoneNumberData' in updates:
                    phone_data = updates['phoneNumberData']
                    if phone_data and isinstance(phone_data, list) and len(phone_data) > 0:
                        phone_value = phone_data[0].get('phoneNumber', '')
                
                if phone_value:
                    # Test the phone format testing first
                    working_format, result_msg = test_phone_formats_with_crm(phone_value, contact_id, self.espocrm_url, self.headers)
                    
                    if working_format:
                        logger.info(f"Found working phone format: {working_format}")
                        return True, f"Phone updated successfully: {result_msg}"
                    else:
                        logger.error(f"All phone formats failed: {result_msg}")
                        return False, f"Phone number validation failed: {result_msg}"
                else:
                    return False, "No phone number provided in update"
            
            # For non-phone updates, proceed with normal update
            clean_updates = {k: v for k, v in updates.items() if k != 'phoneNumberData'}
            
            # Validate that we have the contact ID and updates
            if not contact_id:
                logger.error("No contact ID provided!")
                return False, "No contact ID provided"
            
            if not clean_updates:
                logger.error("No updates provided!")
                return False, "No updates provided"
            
            response = requests.put(f"{self.espocrm_url}/Contact/{contact_id}", 
                                  json=clean_updates, headers=self.headers, timeout=10)
            
            logger.info(f"CRM Response Status: {response.status_code}")
            
            if response.status_code not in [200, 204]:
                logger.error(f"CRM Response Error: {response.text}")
                
                try:
                    error_data = response.json()
                    logger.error(f"CRM Error Details: {error_data}")
                    return False, f"CRM Error {response.status_code}: {error_data}"
                except:
                    return False, f"CRM Error {response.status_code}: {response.text}"
            else:
                logger.info("Update successful!")
                return True, "Success"
            
        except requests.exceptions.Timeout:
            error_msg = "CRM request timed out"
            logger.error(error_msg)
            return False, error_msg
        except requests.exceptions.ConnectionError:
            error_msg = "Failed to connect to CRM"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Update error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def create_contact(self, **kwargs) -> Tuple[str, Optional[str]]:
        """Create contact with validation - FIXED to use phoneNumberData for creation (per EspoCRM docs)"""
        if not kwargs.get('firstName') or not kwargs.get('lastName'):
            return "❌ Both first name and last name are required to create a contact.", None
        
        logger.info(f"🔍 CREATE_CONTACT DEBUG: Received kwargs keys: {list(kwargs.keys())}")
        
        contact_data = {}
        for key, value in kwargs.items():
            if value and str(value).strip():
                if key == 'phoneNumberData':  
                    # Use phoneNumberData structure for creation (per EspoCRM documentation)
                    if isinstance(value, list) and len(value) > 0:
                        # Test different phone number formats to find what works
                        phone_entry = value[0].copy()  # Copy to avoid modifying original
                        original_phone = phone_entry.get('phoneNumber', '')
                        
                        if original_phone:
                            digits_only = re.sub(r'[^\d]', '', original_phone)
                            logger.info(f"🔍 PHONE FORMAT TEST: Original='{original_phone}', Digits='{digits_only}'")
                            
                            # Try formats that have worked in updates
                            if len(digits_only) == 10:
                                # Test different formats - same as Tom's successful update
                                test_formats = [
                                    f"{digits_only[:3]}-{digits_only[3:6]}-{digits_only[6:]}",  # 240-421-1073
                                    f"({digits_only[:3]}) {digits_only[3:6]}-{digits_only[6:]}",  # (240) 421-1073
                                    f"{digits_only[:3]}.{digits_only[3:6]}.{digits_only[6:]}",  # 240.421.1073
                                    f"{digits_only}",  # 2404211073
                                    f"+1{digits_only}",  # +12404211073
                                ]
                                
                                # Use the dash format that worked for Tom
                                formatted_phone = test_formats[0]  # XXX-XXX-XXXX format
                                phone_entry['phoneNumber'] = formatted_phone
                                logger.info(f"🔍 PHONE FORMAT: Using dash format like Tom's update: '{formatted_phone}'")
                            
                            contact_data['phoneNumberData'] = [phone_entry]
                            logger.info(f"✅ CREATE_CONTACT: Added phoneNumberData: {[phone_entry]}")
                        else:
                            logger.warning(f"⚠️ CREATE_CONTACT: No phoneNumber found in phoneNumberData")
                    else:
                        logger.warning(f"⚠️ CREATE_CONTACT: Invalid phoneNumberData structure: {value}")
                else:
                    contact_data[key] = str(value).strip()
                    logger.info(f"🔍 CREATE_CONTACT: Added {key}='{value}'")
        
        logger.info(f"🔍 CREATE_CONTACT: Final contact_data keys: {list(contact_data.keys())}")
        logger.info(f"🔍 CREATE_CONTACT: Final contact_data being sent to CRM: {contact_data}")
        
        try:
            response = requests.post(f"{self.espocrm_url}/Contact", 
                                   json=contact_data, headers=self.headers, timeout=10)
            
            name = f"{kwargs.get('firstName', '')} {kwargs.get('lastName', '')}".strip()
            
            logger.info(f"🔍 CREATE_CONTACT: CRM response status: {response.status_code}")
            
            if response.status_code in [200, 201]:
                created_contact = response.json()
                logger.info(f"✅ CREATE_CONTACT: Successfully created contact: {name}")
                return f"✅ Successfully created contact: **{name}**", created_contact.get('id')
            elif response.status_code == 409:
                # Conflict detected - likely email duplication
                logger.info(f"🔍 CONFLICT: Contact creation conflict detected for {name}")
                
                # Try to find existing contact by email first
                email = kwargs.get('emailAddress')
                if email:
                    logger.info(f"🔍 CONFLICT: Searching for existing contact with email: {email}")
                    existing_contacts = self.search_contacts_simple(email)
                    
                    if existing_contacts:
                        existing_contact = existing_contacts[0]
                        existing_name = existing_contact.get('name', 'Unknown')
                        existing_id = existing_contact.get('id')
                        
                        logger.info(f"🔍 CONFLICT: Found existing contact: {existing_name} (ID: {existing_id})")
                        logger.info(f"🔍 CONFLICT: Original contact_data keys: {list(contact_data.keys())}")
                        logger.info(f"🔍 CONFLICT: Original contact_data: {contact_data}")
                        
                        # Get full details of existing contact
                        details = self.get_contact_details(existing_id)
                        
                        # Prepare update data (exclude firstName/lastName to avoid conflicts)
                        update_data = {}
                        for key, value in contact_data.items():
                            if key not in ['firstName', 'lastName', 'emailAddress'] and value:
                                update_data[key] = value
                                logger.info(f"🔍 CONFLICT: Added to update_data: {key} = {value}")
                        
                        # Add name update if it's different
                        if existing_name.lower() != name.lower():
                            update_data['firstName'] = kwargs.get('firstName', '')
                            update_data['lastName'] = kwargs.get('lastName', '')
                            logger.info(f"🔍 CONFLICT: Added name updates: firstName={update_data['firstName']}, lastName={update_data['lastName']}")
                        
                        logger.info(f"🔍 CONFLICT: Final update_data: {update_data}")
                        
                        if update_data:
                            logger.info(f"🔄 CONFLICT: Attempting to update existing contact with new data: {update_data}")
                            update_success, update_msg = self.update_contact_simple(existing_id, update_data)
                            
                            if update_success:
                                return f"✅ **Found existing contact and updated:** {name}\n\n**Previous name:** {existing_name}\n**Updated with new information**\n\n**Details:**\n{details}", existing_id
                            else:
                                return f"⚠️ **Found existing contact:** {existing_name}\n\n**Could not auto-update:** {update_msg}\n\n**Details:**\n{details}\n\n*You can manually update this contact if needed.*", existing_id
                        else:
                            return f"ℹ️ **Contact already exists:** {existing_name}\n\n**Details:**\n{details}", existing_id
                
                # Fallback to generic conflict message
                existing = self.search_contacts_simple(name)
                contact_id = existing[0]['id'] if existing else None
                return f"ℹ️ Contact **{name}** already exists in the system", contact_id
            else:
                logger.error(f"❌ CREATE_CONTACT: CRM rejected request: {response.status_code}")
                logger.error(f"❌ CREATE_CONTACT: CRM error response: {response.text}")
                
                # If phone validation fails, ALWAYS try creating without phone first
                if 'phoneNumber' in response.text and 'valid' in response.text:
                    logger.info(f"🔄 RETRY: Phone validation failed, creating without phone first...")
                    
                    # Extract phone data before removing it
                    phone_data_to_add = contact_data.get('phoneNumberData')
                    
                    # Create contact without phone
                    contact_data_no_phone = {k: v for k, v in contact_data.items() if k != 'phoneNumberData'}
                    
                    retry_response = requests.post(f"{self.espocrm_url}/Contact", 
                                                 json=contact_data_no_phone, headers=self.headers, timeout=10)
                    
                    if retry_response.status_code in [200, 201]:
                        created_contact = retry_response.json()
                        contact_id = created_contact.get('id')
                        logger.info(f"✅ CREATE_CONTACT: Created without phone: {name} (ID: {contact_id})")
                        
                        # Now try to add phone via update (which we know works)
                        if phone_data_to_add:
                            logger.info(f"🔄 RETRY: Now attempting to add phone via update...")
                            update_success, update_msg = self.update_contact_simple(contact_id, {'phoneNumberData': phone_data_to_add})
                            if update_success:
                                logger.info(f"✅ PHONE UPDATE: Successfully added phone via update")
                                return f"✅ Successfully created contact: **{name}** (phone added automatically)", contact_id
                            else:
                                logger.warning(f"⚠️ PHONE UPDATE: Failed to add phone: {update_msg}")
                                return f"✅ Successfully created contact: **{name}** (phone will need to be added manually: {update_msg})", contact_id
                        else:
                            return f"✅ Successfully created contact: **{name}**", contact_id
                    else:
                        logger.error(f"❌ RETRY: Even creating without phone failed: {retry_response.status_code}")
                        return f"❌ Failed to create contact even without phone: {retry_response.text}", None
                
                return f"❌ Failed to create contact: Server returned error {response.status_code} - {response.text}", None
                
        except Exception as e:
            logger.error(f"❌ CREATE_CONTACT: Exception occurred: {e}")
            return f"❌ Error creating contact: {str(e)}", None

    def add_note(self, contact_id: str, note_content: str) -> str:
        """Add note to contact stream - FIXED to use proper Stream API format"""
        try:
            # Use the Stream API format for posting notes
            note_data = {
                "type": "Post",  # Required for stream posts
                "parentId": contact_id,
                "parentType": "Contact", 
                "post": note_content
            }
            
            logger.info(f"Adding stream note with data: {note_data}")
            
            response = requests.post(f"{self.espocrm_url}/Note", 
                                   json=note_data, headers=self.headers, timeout=10)
            
            logger.info(f"Add note response status: {response.status_code}")
            
            if response.status_code in [200, 201]:
                return f"✅ Note added successfully to contact stream\n\nNote: {note_content}"
            else:
                error_msg = f"Failed to add note: Status {response.status_code}, {response.text}"
                logger.error(error_msg)
                return f"❌ {error_msg}"
        except Exception as e:
            error_msg = f"Error adding note: {str(e)}"
            logger.error(error_msg)
            return f"❌ {error_msg}"

    def get_contact_notes(self, contact_id: str) -> str:
        """Retrieve all stream notes for a specific contact - FIXED to use Stream API"""
        try:
            # Use the Stream API endpoint for getting notes of a specific record
            params = {
                "maxSize": 50,
                "offset": 0
            }
            
            logger.info(f"Getting stream notes for contact {contact_id} using Stream API")
            
            # Use the Stream API endpoint: GET Contact/{id}/stream
            response = requests.get(f"{self.espocrm_url}/Contact/{contact_id}/stream", 
                                  params=params, headers=self.headers, timeout=10)
            
            logger.info(f"Stream API response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                stream_records = data.get("list", [])
                
                logger.info(f"Found {len(stream_records)} stream records")
                
                # Filter for actual posts/notes (type: "Post")
                notes = [record for record in stream_records if record.get('type') == 'Post']
                
                logger.info(f"Found {len(notes)} actual notes/posts")
                
                if not notes:
                    return "📝 No notes found for this contact."
                
                result_text = f"**📝 Notes ({len(notes)}):**\n\n"
                
                for note in notes:
                    post = note.get('post', 'No content')
                    created_at = note.get('createdAt', 'Unknown date')
                    created_by_name = note.get('createdByName', 'Unknown user')
                    
                    # Format date if available
                    if created_at and created_at != 'Unknown date':
                        try:
                            from datetime import datetime
                            # Handle both Z and +00:00 timezone formats
                            if created_at.endswith('Z'):
                                date_obj = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            else:
                                date_obj = datetime.fromisoformat(created_at)
                            created_at = date_obj.strftime('%Y-%m-%d %H:%M')
                        except Exception as date_error:
                            logger.warning(f"Date parsing error: {date_error}")
                            pass
                    
                    result_text += f"**{created_at}** by {created_by_name}\n{post}\n\n---\n\n"
                
                return result_text
            else:
                error_msg = f"Stream API returned status {response.status_code}: {response.text}"
                logger.error(f"Stream API error: {error_msg}")
                return f"❌ Failed to retrieve notes: {error_msg}"
                
        except Exception as e:
            error_msg = f"Error retrieving stream notes: {str(e)}"
            logger.error(error_msg)
            return f"❌ {error_msg}"

    def search_notes(self, search_term: str, contact_name: str = None) -> str:
        """Search stream notes by content - FIXED to use Stream API"""
        try:
            if contact_name:
                # If searching for a specific contact, get their stream first
                contacts = self.search_contacts_simple(contact_name)
                if not contacts:
                    return f"❌ Contact '{contact_name}' not found."
                
                contact_id = contacts[0]['id']
                logger.info(f"Searching notes for specific contact: {contact_name} (ID: {contact_id})")
                
                # Get the contact's stream
                params = {"maxSize": 100, "offset": 0}
                response = requests.get(f"{self.espocrm_url}/Contact/{contact_id}/stream", 
                                      params=params, headers=self.headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    stream_records = data.get("list", [])
                    
                    # Filter for posts that contain the search term
                    matching_notes = []
                    for record in stream_records:
                        if (record.get('type') == 'Post' and 
                            record.get('post') and 
                            search_term.lower() in record.get('post', '').lower()):
                            matching_notes.append(record)
                    
                    if not matching_notes:
                        return f"📝 No notes found containing '{search_term}' for contact '{contact_name}'."
                    
                    result_text = f"**📝 Found {len(matching_notes)} note(s) containing '{search_term}' for {contact_name}:**\n\n"
                    
                    for note in matching_notes:
                        post = note.get('post', 'No content')
                        created_at = note.get('createdAt', 'Unknown date')
                        created_by_name = note.get('createdByName', 'Unknown user')
                        
                        # Truncate long notes
                        if len(post) > 200:
                            post = post[:200] + "..."
                        
                        result_text += f"**{created_at}** by {created_by_name}\n{post}\n\n---\n\n"
                    
                    return result_text
                else:
                    return f"❌ Failed to get stream for contact: {response.status_code}"
            else:
                # Search across all stream records for the current user
                logger.info(f"Searching all stream notes for term: {search_term}")
                
                params = {"maxSize": 100, "offset": 0}
                response = requests.get(f"{self.espocrm_url}/Stream", 
                                      params=params, headers=self.headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    stream_records = data.get("list", [])
                    
                    # Filter for posts that contain the search term and are related to contacts
                    matching_notes = []
                    for record in stream_records:
                        if (record.get('type') == 'Post' and 
                            record.get('post') and 
                            search_term.lower() in record.get('post', '').lower() and
                            record.get('parentType') == 'Contact'):
                            matching_notes.append(record)
                    
                    if not matching_notes:
                        return f"📝 No notes found containing '{search_term}' across all contacts."
                    
                    result_text = f"**📝 Found {len(matching_notes)} note(s) containing '{search_term}' across all contacts:**\n\n"
                    
                    for note in matching_notes:
                        post = note.get('post', 'No content')
                        created_at = note.get('createdAt', 'Unknown date')
                        created_by_name = note.get('createdByName', 'Unknown user')
                        parent_name = note.get('parentName', 'Unknown contact')
                        
                        # Truncate long notes
                        if len(post) > 200:
                            post = post[:200] + "..."
                        
                        result_text += f"**{parent_name}** - {created_at} by {created_by_name}\n{post}\n\n---\n\n"
                    
                    return result_text
                else:
                    error_msg = f"Stream API returned status {response.status_code}: {response.text}"
                    logger.error(f"Stream search error: {error_msg}")
                    return f"❌ Failed to search stream notes: {error_msg}"
                
        except Exception as e:
            error_msg = f"Error searching stream notes: {str(e)}"
            logger.error(error_msg)
            return f"❌ {error_msg}"

    def get_contact_details(self, contact_id: str) -> str:
        """Get detailed contact information"""
        try:
            response = requests.get(f"{self.espocrm_url}/Contact/{contact_id}", 
                                  headers=self.headers, timeout=10)
            
            if response.status_code != 200:
                return f"❌ Failed to get contact details: {response.status_code}"
            
            contact = response.json()
            actual_name = contact.get('name', 'Unknown')
            
            result_text = f"**Contact Details: {actual_name}**\n\n"
            
            fields = [
                ('Email', 'emailAddress'),
                ('Phone', 'phoneNumberData'),
                ('Title', 'cCurrentTitle'),
                ('Current Company', 'cCurrentCompany'),
                ('Skills', 'cSkills'),
                ('LinkedIn', 'cLinkedInURL'),
                ('Street Address', 'addressStreet'),
                ('City', 'addressCity'),
                ('State', 'addressState'),
                ('Postal Code', 'addressPostalCode'),
                ('Country', 'addressCountry'),
                ('Created', 'createdAt'),
                ('Modified', 'modifiedAt')
            ]
            
            for label, field in fields:
                if contact.get(field):
                    if field == 'phoneNumberData':
                        # Handle phone number data structure
                        phone_data = contact[field]
                        if isinstance(phone_data, list) and len(phone_data) > 0:
                            result_text += f"**{label}:**\n"
                            for phone_entry in phone_data:
                                phone_num = phone_entry.get('phoneNumber', '')
                                phone_type = phone_entry.get('type', 'Unknown')
                                is_primary = phone_entry.get('primary', False)
                                primary_text = " (Primary)" if is_primary else ""
                                result_text += f"  • {phone_num} ({phone_type}){primary_text}\n"
                    else:
                        result_text += f"**{label}:** {contact[field]}\n"
            
            return result_text
            
        except Exception as e:
            return f"❌ Error getting contact details: {str(e)}"

    def list_all_contacts(self, limit: int = 100) -> str:
        """List contacts with proper pagination"""
        try:
            params = {
                "select": "id,name,firstName,lastName,emailAddress,phoneNumberData,cCurrentTitle,cCurrentCompany,addressCity,addressState",
                "maxSize": min(limit, 50),
                "orderBy": "name"
            }
            
            response = requests.get(f"{self.espocrm_url}/Contact", 
                                  params=params, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                contacts = data.get("list", [])
                total = data.get("total", len(contacts))
                
                if not contacts:
                    return "No contacts found in the system."
                
                result_text = f"**Contacts ({len(contacts)} of {total} total):**\n\n"
                
                for contact in contacts:
                    result_text += f"• **{contact.get('name', 'Unknown')}**"
                    if contact.get('emailAddress'):
                        result_text += f" - {contact['emailAddress']}"
                    if contact.get('cCurrentTitle'):
                        result_text += f" ({contact['cCurrentTitle']})"
                    if contact.get('cCurrentCompany'):
                        result_text += f" at {contact['cCurrentCompany']}"
                    result_text += "\n"
                
                if len(contacts) < total:
                    result_text += f"\n... and {total - len(contacts)} more contacts (use pagination to see more)"
                
                return result_text
            else:
                return f"❌ Failed to list contacts: {response.status_code}"
                
        except Exception as e:
            return f"❌ Error retrieving contacts: {str(e)}"

    # ACCOUNT MANAGEMENT METHODS
    
    def search_accounts(self, criteria: str) -> List[Dict[str, Any]]:
        """Search for accounts in the CRM"""
        try:
            logger.info(f"Searching accounts for: '{criteria}'")
            
            params = {
                "select": "id,name,emailAddress,phoneNumber,website,industry,type,billingAddressCity,billingAddressState,description",
                "maxSize": 20,
                "orderBy": "name"
            }
            
            if "@" in criteria:
                # Email search
                params.update({
                    "where[0][field]": "emailAddress",
                    "where[0][type]": "contains",
                    "where[0][value]": criteria
                })
            elif criteria.lower().startswith("http") or "." in criteria and len(criteria.split(".")) > 1:
                # Website search
                params.update({
                    "where[0][field]": "website", 
                    "where[0][type]": "contains",
                    "where[0][value]": criteria
                })
            else:
                # Name search
                params.update({
                    "where[0][field]": "name",
                    "where[0][type]": "contains",
                    "where[0][value]": criteria
                })
            
            response = requests.get(f"{self.espocrm_url}/Account", 
                                  params=params, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                accounts = data.get("list", [])
                logger.info(f"Found {len(accounts)} accounts")
                return accounts
            else:
                logger.error(f"Account search failed: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Account search error: {e}")
            return []

    def create_account(self, **kwargs) -> Tuple[str, Optional[str]]:
        """Create a new account - ENHANCED with better error handling"""
        if not kwargs.get('name'):
            return "❌ Account name is required.", None
        
        logger.info(f"Creating account: {kwargs.get('name')}")
        logger.info(f"Account data received: {kwargs}")
        
        # Clean the account data
        account_data = {}
        for key, value in kwargs.items():
            if value and str(value).strip():
                clean_value = str(value).strip()
                account_data[key] = clean_value
                logger.info(f"Added to account_data: {key} = {clean_value}")
        
        logger.info(f"Final account_data being sent: {account_data}")
        
        try:
            response = requests.post(f"{self.espocrm_url}/Account", 
                                   json=account_data, headers=self.headers, timeout=10)
            
            name = kwargs.get('name', 'Unknown')
            
            logger.info(f"Account creation response status: {response.status_code}")
            logger.info(f"Account creation response text: {response.text}")
            
            if response.status_code in [200, 201]:
                created_account = response.json()
                logger.info(f"Successfully created account: {name}")
                return f"✅ Successfully created account: **{name}**", created_account.get('id')
            elif response.status_code == 409:
                # Account already exists
                logger.info(f"Account {name} already exists")
                existing = self.search_accounts(name)
                account_id = existing[0]['id'] if existing else None
                return f"ℹ️ Account **{name}** already exists", account_id
            elif response.status_code == 400:
                # Bad request - likely validation error
                try:
                    error_data = response.json()
                    logger.error(f"Account validation error: {error_data}")
                    return f"❌ Validation error creating account: {error_data}", None
                except:
                    logger.error(f"Account creation bad request: {response.text}")
                    return f"❌ Invalid data for account creation: {response.text}", None
            elif response.status_code == 403:
                logger.error("Account creation forbidden - check API permissions")
                return f"❌ Permission denied: Check API user permissions for Account creation", None
            else:
                logger.error(f"Account creation failed: {response.status_code} - {response.text}")
                return f"❌ Failed to create account (Status {response.status_code}): {response.text}", None
                
        except requests.exceptions.Timeout:
            error_msg = "Account creation request timed out"
            logger.error(error_msg)
            return f"❌ {error_msg}", None
        except requests.exceptions.ConnectionError:
            error_msg = "Failed to connect to CRM for account creation"
            logger.error(error_msg)
            return f"❌ {error_msg}", None
        except Exception as e:
            error_msg = f"Account creation error: {str(e)}"
            logger.error(error_msg)
            return f"❌ {error_msg}", None

    def get_account_details(self, account_id: str) -> str:
        """Get detailed account information"""
        try:
            response = requests.get(f"{self.espocrm_url}/Account/{account_id}", 
                                  headers=self.headers, timeout=10)
            
            if response.status_code != 200:
                return f"❌ Failed to get account details: {response.status_code}"
            
            account = response.json()
            name = account.get('name', 'Unknown')
            
            result_text = f"**🏢 Account Details: {name}**\n\n"
            
            # Basic info
            basic_fields = [
                ('Industry', 'industry'),
                ('Type', 'type'), 
                ('Email', 'emailAddress'),
                ('Phone', 'phoneNumber'),
                ('Website', 'website'),
                ('SIC Code', 'sicCode'),
                ('Description', 'description')
            ]
            
            for label, field in basic_fields:
                if account.get(field):
                    result_text += f"**{label}:** {account[field]}\n"
            
            # Billing Address
            billing_parts = []
            if account.get('billingAddressStreet'):
                billing_parts.append(account['billingAddressStreet'])
            if account.get('billingAddressCity'):
                billing_parts.append(account['billingAddressCity'])
            if account.get('billingAddressState'):
                billing_parts.append(account['billingAddressState'])
            if account.get('billingAddressPostalCode'):
                billing_parts.append(account['billingAddressPostalCode'])
            if account.get('billingAddressCountry'):
                billing_parts.append(account['billingAddressCountry'])
            
            if billing_parts:
                result_text += f"**Billing Address:** {', '.join(billing_parts)}\n"
            
            # Shipping Address  
            shipping_parts = []
            if account.get('shippingAddressStreet'):
                shipping_parts.append(account['shippingAddressStreet'])
            if account.get('shippingAddressCity'):
                shipping_parts.append(account['shippingAddressCity'])
            if account.get('shippingAddressState'):
                shipping_parts.append(account['shippingAddressState'])
            if account.get('shippingAddressPostalCode'):
                shipping_parts.append(account['shippingAddressPostalCode'])
            if account.get('shippingAddressCountry'):
                shipping_parts.append(account['shippingAddressCountry'])
            
            if shipping_parts:
                result_text += f"**Shipping Address:** {', '.join(shipping_parts)}\n"
            
            # Timestamps
            if account.get('createdAt'):
                result_text += f"**Created:** {account['createdAt']}\n"
            if account.get('modifiedAt'):
                result_text += f"**Modified:** {account['modifiedAt']}\n"
            
            return result_text
            
        except Exception as e:
            return f"❌ Error getting account details: {str(e)}"

    def update_account(self, account_id: str, updates: Dict[str, Any]) -> Tuple[bool, str]:
        """Update account information - ENHANCED based on EspoCRM docs"""
        try:
            logger.info(f"Updating account {account_id} with: {updates}")
            
            clean_updates = {}
            for k, v in updates.items():
                if v is not None and str(v).strip():
                    clean_updates[k] = str(v).strip()
            
            if not clean_updates:
                return False, "No valid updates provided"
            
            logger.info(f"Clean updates being sent: {clean_updates}")
            
            # Use PUT method as specified in EspoCRM docs
            response = requests.put(f"{self.espocrm_url}/Account/{account_id}", 
                                  json=clean_updates, headers=self.headers, timeout=10)
            
            logger.info(f"Account update response status: {response.status_code}")
            logger.info(f"Account update response: {response.text}")
            
            if response.status_code in [200, 204]:
                logger.info("Account update successful")
                return True, "Success"
            elif response.status_code == 404:
                return False, f"Account with ID {account_id} not found"
            elif response.status_code == 403:
                return False, "Permission denied: Check API user permissions for Account updates"
            elif response.status_code == 400:
                try:
                    error_data = response.json()
                    return False, f"Validation error: {error_data}"
                except:
                    return False, f"Bad request: {response.text}"
            else:
                logger.error(f"Account update failed: {response.status_code} - {response.text}")
                return False, f"Update failed (Status {response.status_code}): {response.text}"
            
        except Exception as e:
            error_msg = f"Account update error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def list_all_accounts(self, limit: int = 50) -> str:
        """List accounts with pagination"""
        try:
            params = {
                "select": "id,name,emailAddress,phoneNumber,website,industry,type,billingAddressCity,billingAddressState",
                "maxSize": min(limit, 50),
                "orderBy": "name"
            }
            
            response = requests.get(f"{self.espocrm_url}/Account", 
                                  params=params, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                accounts = data.get("list", [])
                total = data.get("total", len(accounts))
                
                if not accounts:
                    return "No accounts found in the system."
                
                result_text = f"**🏢 Accounts ({len(accounts)} of {total} total):**\n\n"
                
                for account in accounts:
                    result_text += f"• **{account.get('name', 'Unknown')}**"
                    if account.get('industry'):
                        result_text += f" ({account['industry']})"
                    if account.get('billingAddressCity') and account.get('billingAddressState'):
                        result_text += f" - {account['billingAddressCity']}, {account['billingAddressState']}"
                    if account.get('website'):
                        result_text += f" - {account['website']}"
                    result_text += "\n"
                
                if len(accounts) < total:
                    result_text += f"\n... and {total - len(accounts)} more accounts"
                
                return result_text
            else:
                return f"❌ Failed to list accounts: {response.status_code}"
                
        except Exception as e:
            return f"❌ Error retrieving accounts: {str(e)}"

    # NEW: CONTACT-ACCOUNT RELATIONSHIP METHODS
    
    def link_contact_to_account(self, contact_name: str, account_name: str, primary: bool = True) -> str:
        """Link a contact to an account using EspoCRM relationship fields"""
        try:
            # Find contact
            contacts = self.search_contacts_simple(contact_name)
            if not contacts:
                return f"❌ Contact '{contact_name}' not found"
            contact = contacts[0]
            contact_id = contact['id']
            
            # Find account  
            accounts = self.search_accounts(account_name)
            if not accounts:
                return f"❌ Account '{account_name}' not found"
            account = accounts[0]
            account_id = account['id']
            account_display_name = account.get('name', account_name)
            
            if primary:
                # Set as primary account using Many-to-One relationship
                update_data = {'accountId': account_id}  # EspoCRM typically uses accountId for the foreign key
                success, error_msg = self.update_contact_simple(contact_id, update_data)
                
                if success:
                    return f"✅ Successfully set **{account_display_name}** as primary account for **{contact_name}**"
                else:
                    # Try alternative field name based on relationship table
                    update_data = {'account': account_id}
                    success, error_msg = self.update_contact_simple(contact_id, update_data)
                    
                    if success:
                        return f"✅ Successfully set **{account_display_name}** as primary account for **{contact_name}**"
                    else:
                        return f"❌ Failed to set primary account: {error_msg}"
            else:
                # Add to accounts collection using Many-to-Many relationship
                # This typically requires a different API endpoint
                try:
                    # Use the relationship API endpoint
                    response = requests.post(
                        f"{self.espocrm_url}/Contact/{contact_id}/accounts",
                        json={"id": account_id},
                        headers=self.headers,
                        timeout=10
                    )
                    
                    if response.status_code in [200, 201]:
                        return f"✅ Successfully added **{contact_name}** to **{account_display_name}** accounts"
                    else:
                        return f"❌ Failed to add to accounts: Status {response.status_code}"
                        
                except Exception as e:
                    return f"❌ Error adding to accounts collection: {str(e)}"
                
        except Exception as e:
            return f"❌ Error linking contact to account: {str(e)}"

    def unlink_contact_from_account(self, contact_name: str, account_name: str = None) -> str:
        """Remove contact-account relationship"""
        try:
            # Find contact
            contacts = self.search_contacts_simple(contact_name)
            if not contacts:
                return f"❌ Contact '{contact_name}' not found"
            contact_id = contacts[0]['id']
            
            if account_name:
                # Remove from specific account (Many-to-Many)
                accounts = self.search_accounts(account_name)
                if not accounts:
                    return f"❌ Account '{account_name}' not found"
                account_id = accounts[0]['id']
                
                try:
                    response = requests.delete(
                        f"{self.espocrm_url}/Contact/{contact_id}/accounts/{account_id}",
                        headers=self.headers,
                        timeout=10
                    )
                    
                    if response.status_code in [200, 204]:
                        return f"✅ Removed **{contact_name}** from **{account_name}**"
                    else:
                        return f"❌ Failed to remove from account: Status {response.status_code}"
                except Exception as e:
                    return f"❌ Error removing from account: {str(e)}"
            else:
                # Clear primary account
                update_data = {'accountId': None}
                success, error_msg = self.update_contact_simple(contact_id, update_data)
                
                if success:
                    return f"✅ Cleared primary account for **{contact_name}**"
                else:
                    # Try alternative field name
                    update_data = {'account': None}
                    success, error_msg = self.update_contact_simple(contact_id, update_data)
                    
                    if success:
                        return f"✅ Cleared primary account for **{contact_name}**"
                    else:
                        return f"❌ Failed to clear primary account: {error_msg}"
                        
        except Exception as e:
            return f"❌ Error unlinking contact from account: {str(e)}"

    def get_contact_accounts(self, contact_name: str) -> str:
        """Get all accounts associated with a contact"""
        try:
            # Find contact
            contacts = self.search_contacts_simple(contact_name)
            if not contacts:
                return f"❌ Contact '{contact_name}' not found"
            contact = contacts[0]
            contact_id = contact['id']
            
            result = f"**🏢 Accounts for {contact_name}:**\n\n"
            
            # Check primary account
            primary_account_id = contact.get('accountId') or contact.get('account')
            if primary_account_id:
                try:
                    account_details = self.get_account_details(primary_account_id)
                    result += f"**Primary Account:**\n{account_details}\n\n"
                except:
                    result += f"**Primary Account:** ID {primary_account_id}\n\n"
            
            # Get associated accounts (Many-to-Many)
            try:
                response = requests.get(
                    f"{self.espocrm_url}/Contact/{contact_id}/accounts",
                    headers=self.headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    accounts = data.get("list", [])
                    
                    if accounts:
                        result += f"**Associated Accounts ({len(accounts)}):**\n"
                        for account in accounts:
                            name = account.get('name', 'Unknown')
                            result += f"• {name}\n"
                    else:
                        if not primary_account_id:
                            result += "No associated accounts found."
                else:
                    if not primary_account_id:
                        result += "No account associations found."
                        
            except Exception as e:
                if not primary_account_id:
                    result += f"Could not retrieve account associations: {str(e)}"
            
            return result
            
        except Exception as e:
            return f"❌ Error getting contact accounts: {str(e)}"

    # CALENDAR MANAGEMENT METHODS
    
    def get_all_users(self) -> List[Dict[str, Any]]:
        """Get list of all users for calendar operations"""
        try:
            params = {
                "select": "id,name,userName,emailAddress",
                "where[0][field]": "isActive",
                "where[0][type]": "equals",
                "where[0][value]": True,
                "maxSize": 100,
                "orderBy": "name"
            }
            
            response = requests.get(f"{self.espocrm_url}/User", 
                                  params=params, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return data.get("list", [])
            else:
                logger.error(f"Failed to get users: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error getting users: {e}")
            return []

    def find_user_by_name(self, user_name: str) -> Optional[str]:
        """Find user ID by name"""
        users = self.get_all_users()
        for user in users:
            if (user.get('name', '').lower() == user_name.lower() or 
                user.get('userName', '').lower() == user_name.lower()):
                return user.get('id')
        return None

    def get_calendar_events(self, user_name: str = None, date_start: str = None, date_end: str = None) -> str:
        """Get calendar events for specified user or ask for clarification"""
        try:
            # If no user specified, we need to ask
            if not user_name:
                users = self.get_all_users()
                user_list = [f"• **{user.get('name', 'Unknown')}**" for user in users[:10]]
                return f"📅 **Whose calendar would you like to see?**\n\n{chr(10).join(user_list)}\n\nPlease specify: *'Show [Name]'s calendar'*"
            
            # Find the user
            user_id = self.find_user_by_name(user_name)
            if not user_id:
                return f"❌ User '{user_name}' not found. Please check the name and try again."
            
            # Build calendar query
            params = {
                "select": "id,name,dateStart,dateEnd,description,status",
                "where[0][field]": "assignedUserId", 
                "where[0][type]": "equals",
                "where[0][value]": user_id,
                "maxSize": 50,
                "orderBy": "dateStart",
                "order": "asc"
            }
            
            # Add date filters if provided
            if date_start:
                params.update({
                    "where[1][field]": "dateStart",
                    "where[1][type]": "greaterThanOrEqual", 
                    "where[1][value]": date_start
                })
            
            if date_end:
                filter_index = 2 if date_start else 1
                params.update({
                    f"where[{filter_index}][field]": "dateEnd",
                    f"where[{filter_index}][type]": "lessThanOrEqual",
                    f"where[{filter_index}][value]": date_end
                })
            
            logger.info(f"Getting calendar events for user {user_name} (ID: {user_id})")
            
            # Note: EspoCRM might use 'Event' or 'Meeting' entity instead of 'Calendar'
            # Try both endpoints
            endpoints_to_try = ['Event', 'Meeting', 'Call']
            
            all_events = []
            for endpoint in endpoints_to_try:
                try:
                    response = requests.get(f"{self.espocrm_url}/{endpoint}", 
                                          params=params, headers=self.headers, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        events = data.get("list", [])
                        for event in events:
                            event['_entity_type'] = endpoint  # Track which entity type
                        all_events.extend(events)
                        logger.info(f"Found {len(events)} events in {endpoint} entity")
                except Exception as e:
                    logger.warning(f"Could not access {endpoint} entity: {e}")
                    continue
            
            if not all_events:
                date_info = ""
                if date_start or date_end:
                    date_info = f" for the specified date range"
                return f"📅 No calendar events found for **{user_name}**{date_info}."
            
            # Sort all events by date
            all_events.sort(key=lambda x: x.get('dateStart', ''))
            
            result_text = f"**📅 Calendar for {user_name} ({len(all_events)} events):**\n\n"
            
            for event in all_events:
                name = event.get('name', 'Untitled Event')
                date_start = event.get('dateStart', 'No start time')
                date_end = event.get('dateEnd', 'No end time')
                description = event.get('description', '')
                status = event.get('status', 'Not Set')
                entity_type = event.get('_entity_type', 'Event')
                
                # Format date/time
                try:
                    from datetime import datetime
                    if date_start != 'No start time':
                        start_dt = datetime.fromisoformat(date_start.replace('Z', '+00:00'))
                        formatted_start = start_dt.strftime('%m/%d %H:%M')
                    else:
                        formatted_start = date_start
                    
                    if date_end != 'No end time':
                        end_dt = datetime.fromisoformat(date_end.replace('Z', '+00:00'))
                        formatted_end = end_dt.strftime('%H:%M')
                    else:
                        formatted_end = date_end
                except:
                    formatted_start = date_start
                    formatted_end = date_end
                
                result_text += f"**{name}** ({entity_type})\n"
                result_text += f"📅 {formatted_start} - {formatted_end}\n"
                if status and status != 'Not Set':
                    result_text += f"Status: {status}\n"
                if description:
                    desc_preview = description[:100] + "..." if len(description) > 100 else description
                    result_text += f"📝 {desc_preview}\n"
                result_text += "\n"
            
            return result_text
            
        except Exception as e:
            error_msg = f"Error getting calendar events: {str(e)}"
            logger.error(error_msg)
            return f"❌ {error_msg}"

    def create_calendar_event(self, name: str, date_start: str, date_end: str, 
                             user_name: str = None, description: str = None, 
                             contact_id: str = None) -> str:
        """Create a calendar event for specified user"""
        try:
            # If no user specified, ask for clarification
            if not user_name:
                users = self.get_all_users()
                user_list = [f"• **{user.get('name', 'Unknown')}**" for user in users[:10]]
                return f"📅 **Whose calendar should I add this event to?**\n\n**Event:** {name}\n**Time:** {date_start} - {date_end}\n\n**Available users:**\n{chr(10).join(user_list)}\n\nPlease specify: *'Add to [Name]'s calendar'*"
            
            # Find the user
            user_id = self.find_user_by_name(user_name)
            if not user_id:
                return f"❌ User '{user_name}' not found. Please check the name and try again."
            
            # Prepare event data
            event_data = {
                "name": name,
                "dateStart": date_start,
                "dateEnd": date_end,
                "assignedUserId": user_id,
                "status": "Planned"
            }
            
            if description:
                event_data["description"] = description
            
            # If contact provided, link to contact
            if contact_id:
                event_data["parentId"] = contact_id
                event_data["parentType"] = "Contact"
            
            logger.info(f"Creating calendar event for user {user_name}: {event_data}")
            
            # Try different entity types for calendar events
            endpoints_to_try = ['Event', 'Meeting', 'Call']
            
            for endpoint in endpoints_to_try:
                try:
                    response = requests.post(f"{self.espocrm_url}/{endpoint}", 
                                           json=event_data, headers=self.headers, timeout=10)
                    
                    if response.status_code in [200, 201]:
                        created_event = response.json()
                        logger.info(f"Successfully created {endpoint} for user {user_name}")
                        return f"✅ **Calendar event created for {user_name}**\n\n**Event:** {name}\n**Time:** {date_start} - {date_end}\n**Type:** {endpoint}"
                    
                except Exception as e:
                    logger.warning(f"Failed to create {endpoint}: {e}")
                    continue
            
            return f"❌ Failed to create calendar event. Please check entity permissions and try again."
            
        except Exception as e:
            error_msg = f"Error creating calendar event: {str(e)}"
            logger.error(error_msg)
            return f"❌ {error_msg}"

    def get_user_availability(self, user_name: str, date: str) -> str:
        """Check user availability for a specific date"""
        try:
            user_id = self.find_user_by_name(user_name)
            if not user_id:
                return f"❌ User '{user_name}' not found."
            
            # Get events for the specified date
            date_start = f"{date} 00:00:00"
            date_end = f"{date} 23:59:59"
            
            events_result = self.get_calendar_events(user_name, date_start, date_end)
            
            if "No calendar events found" in events_result:
                return f"✅ **{user_name} is available all day on {date}**\n\nNo scheduled events found."
            else:
                return f"📅 **{user_name}'s schedule for {date}:**\n\n{events_result}"
                
        except Exception as e:
            error_msg = f"Error checking availability: {str(e)}"
            logger.error(error_msg)
            return f"❌ {error_msg}"
