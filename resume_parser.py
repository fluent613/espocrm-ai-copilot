# resume_parser.py
# Resume parsing functionality for FluencyCare Copilot

import re
import json
import logging
from typing import Tuple, Optional, Dict, Any
import openai
from utils import format_phone_for_crm, create_phone_number_data

logger = logging.getLogger(__name__)

class ResumeParser:
    def __init__(self, openai_client):
        self.client = openai_client
    
    def manual_name_extraction(self, resume_text: str) -> Optional[Tuple[str, str]]:
        """Manual name extraction with better patterns"""
        lines = resume_text.strip().split('\n')
        
        # Check first 10 lines for name patterns
        for line in lines[:10]:
            line = line.strip()
            if not line or len(line) < 3:
                continue
                
            # Remove common prefixes/suffixes and clean line
            clean_line = re.sub(r'\b(Mr\.?|Ms\.?|Mrs\.?|Dr\.?)\s+', '', line, flags=re.IGNORECASE)
            clean_line = re.sub(r'\s+(Jr\.?|Sr\.?|II|III)$', '', clean_line, flags=re.IGNORECASE)
            clean_line = clean_line.strip()
            
            # Look for simple "FirstName LastName" pattern (2-20 chars each)
            name_match = re.match(r'^([A-Z][a-z]{1,20})\s+([A-Z][a-z]{1,20})$', clean_line)
            if name_match:
                return name_match.group(1), name_match.group(2)
            
            # Look for "FIRSTNAME LASTNAME" pattern
            caps_match = re.match(r'^([A-Z]{2,20})\s+([A-Z]{2,20})$', clean_line)
            if caps_match:
                return caps_match.group(1).capitalize(), caps_match.group(2).capitalize()
            
            # Look for "First Last" with possible middle initial
            middle_match = re.match(r'^([A-Z][a-z]{1,20})\s+[A-Z]\.?\s+([A-Z][a-z]{1,20})$', clean_line)
            if middle_match:
                return middle_match.group(1), middle_match.group(2)
        
        return None

    def extract_resume_info(self, resume_text: str) -> Dict[str, Any]:
        """Extract structured information from resume text with improved parsing"""
        prompt = f"""
        Please extract the following information from this resume and return it as JSON:
        - firstName: First name only
        - lastName: Last name only (REQUIRED - if you cannot find a clear last name, use "Unknown" or extract from email)
        - emailAddress: Email address (must contain @ symbol)
        - phoneNumber: Phone number (10+ digits, format: (XXX) XXX-XXXX or similar)
        - cCurrentTitle: Most recent job title or current position
        - cSkills: Array of relevant technical skills and technologies
        - cCurrentCompany: Most recent company name
        - cLinkedInURL: LinkedIn profile URL if found
        - addressStreet: Street address (number and street name)
        - addressCity: City name
        - addressState: State (2-letter code or full name)
        - addressPostalCode: ZIP/Postal code
        - addressCountry: Country (default to USA for US addresses)
        
        CRITICAL PARSING RULES FOR NAMES:
        - Look VERY carefully at the first 3-5 lines for names
        - Names are usually at the very top, often the first line
        - Look for patterns like "John Smith", "JOHN SMITH", or "John A. Smith"
        - If you find "john.smith@company.com", extract "John" and "Smith"
        - Be AGGRESSIVE about finding actual names - don't give up easily
        - Only use fallbacks if you absolutely cannot find any name anywhere
        - Check for names in headers, contact sections, or signature areas
        
        CRITICAL PHONE NUMBER RULES:
        - Phone numbers can appear in many formats: (303) 555-1234, 303-555-1234, 303.555.1234, 303 555 1234
        - Look for patterns like XXX-XXX-XXXX, (XXX) XXX-XXXX, XXX.XXX.XXXX in contact headers
        - Common locations: after name in header (NAME | PHONE | EMAIL), after "Phone:", in contact sections
        - DO NOT confuse phone numbers with addresses - phone numbers have 10 digits total
        - Examples of phone patterns to look for:
          * "JOHN SMITH | 303-808-3814 | email@domain.com" → phoneNumber: "303-808-3814"
          * "Phone: (720) 708-9496" → phoneNumber: "(720) 708-9496"
          * "555.123.4567" → phoneNumber: "555.123.4567"
        
        ADDRESS vs PHONE RULES:
        - Phone numbers are 10 digits (XXX-XXX-XXXX pattern)
        - Street addresses have house numbers AND street names (like "123 Main Street")
        - City names are words, not number patterns
        - Don't put phone numbers in address fields!
        
        Resume text: {resume_text}
        
        Return only valid JSON with these exact field names. Try very hard to find real names and identify phone numbers correctly.
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                timeout=30
            )
            
            result = json.loads(response.choices[0].message.content)
            logger.info(f"OpenAI extracted: {result}")
            
            # Post-process and validate the results
            cleaned_result = {}
            
            # Clean and validate names
            firstName = str(result.get('firstName', '')).strip() if result.get('firstName') else ""
            lastName = str(result.get('lastName', '')).strip() if result.get('lastName') else ""
            
            # If AI didn't find good names, try manual extraction first
            if (not firstName or not lastName or 
                firstName.lower() in ['unknown', 'resume', 'contact'] or 
                lastName.lower() in ['professional', 'unknown', 'contact']):
                
                logger.info("AI name extraction poor, trying manual extraction...")
                manual_names = self.manual_name_extraction(resume_text)
                if manual_names:
                    firstName, lastName = manual_names
                    logger.info(f"Manual extraction found: {firstName} {lastName}")
            
            # If still no lastName, try to extract from email
            if not lastName and result.get('emailAddress'):
                email = str(result['emailAddress'])
                if '.' in email.split('@')[0]:  # Has dot in username part
                    email_parts = email.split('@')[0].split('.')
                    if len(email_parts) >= 2:
                        if not firstName:
                            firstName = email_parts[0].capitalize()
                        lastName = email_parts[-1].capitalize()
                        logger.info(f"Extracted names from email: {firstName} {lastName}")
            
            # ONLY use these fallbacks if everything else completely fails
            if not firstName:
                firstName = "Contact"
            if not lastName:
                lastName = "Person"
            
            cleaned_result['firstName'] = firstName
            cleaned_result['lastName'] = lastName
                
            # Validate and clean other fields
            if result.get('emailAddress') and '@' in str(result['emailAddress']):
                cleaned_result['emailAddress'] = str(result['emailAddress']).strip()
                
            if result.get('phoneNumber'):
                cleaned_result['phoneNumber'] = str(result['phoneNumber']).strip()
                
            # Clean other fields
            for field in ['cCurrentTitle', 'cCurrentCompany', 'cLinkedInURL', 
                         'addressStreet', 'addressCity', 'addressState', 
                         'addressPostalCode', 'addressCountry']:
                if result.get(field):
                    cleaned_result[field] = str(result[field]).strip()
            
            # Handle skills (can be array or string)
            if result.get('cSkills'):
                if isinstance(result['cSkills'], list):
                    cleaned_result['cSkills'] = ', '.join(result['cSkills'])
                else:
                    cleaned_result['cSkills'] = str(result['cSkills']).strip()
                    
            logger.info(f"Cleaned result: {cleaned_result}")
            return cleaned_result
            
        except Exception as e:
            logger.error(f"Resume parsing error: {e}")
            return self._fallback_parsing(resume_text)

    def _fallback_parsing(self, resume_text: str) -> Dict[str, Any]:
        """Enhanced fallback parsing using regex"""
        # Clean the text first - remove garbled characters
        clean_text = re.sub(r'[^\x00-\x7F]+', ' ', resume_text)
        clean_text = re.sub(r'\s+', ' ', clean_text)
        
        # Try manual extraction first
        manual_names = self.manual_name_extraction(resume_text)
        if manual_names:
            firstName, lastName = manual_names
        else:
            firstName = "Contact"
            lastName = "Person"
        
        # Find email
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', clean_text)
        
        # Find phone number
        phone_match = re.search(r'\(?\d{3}\)?[\s\-\.]?\d{3}[\s\-\.]?\d{4}', clean_text)
        
        # Find address components
        address_match = re.search(r'(\d+\s+[^,\n]+),?\s*([^,\n]+),?\s*([A-Z]{2})\s+(\d{5}(?:-\d{4})?)', clean_text)
        
        result = {
            "firstName": firstName,
            "lastName": lastName,
            "emailAddress": email_match.group(0) if email_match else "",
            "phoneNumber": phone_match.group(0) if phone_match else "",
            "cSkills": "",
            "cCurrentTitle": "",
            "cCurrentCompany": "",
            "cLinkedInURL": ""
        }
        
        # Add address components if found
        if address_match:
            result.update({
                "addressStreet": address_match.group(1).strip(),
                "addressCity": address_match.group(2).strip(),
                "addressState": address_match.group(3).strip(),
                "addressPostalCode": address_match.group(4).strip(),
                "addressCountry": "USA"
            })
        else:
            result.update({
                "addressStreet": "",
                "addressCity": "",
                "addressState": "",
                "addressPostalCode": "",
                "addressCountry": ""
            })
        
        return result

    def process_uploaded_file(self, file) -> Tuple[Optional[str], Optional[str]]:
        """Process uploaded file and extract text content with better error handling"""
        try:
            filename = file.filename.lower()
            logger.info(f"Processing file: {filename}")
            
            if filename.endswith('.txt'):
                content = file.read().decode('utf-8')
                logger.info(f"Read TXT file, content length: {len(content)}")
                
            elif filename.endswith('.docx'):
                try:
                    from docx import Document
                    doc = Document(file)
                    content = "\n".join([para.text for para in doc.paragraphs])
                    logger.info(f"Read DOCX file, content length: {len(content)}")
                except ImportError:
                    logger.error("DOCX support not installed")
                    return None, "❌ DOCX support not installed. Please install python-docx: pip install python-docx"
                    
            elif filename.endswith('.pdf'):
                try:
                    import fitz  # PyMuPDF
                    pdf_bytes = file.read()
                    logger.info(f"Read PDF file, size: {len(pdf_bytes)} bytes")
                    
                    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
                        content = "\n".join([page.get_text() for page in doc])
                        logger.info(f"Extracted PDF content, length: {len(content)}")
                except ImportError:
                    logger.error("PDF support not installed")
                    return None, "❌ PDF support not installed. Please install PyMuPDF: pip install PyMuPDF"
            else:
                # Try to read as text with error handling
                content = file.read().decode('utf-8', errors='replace')
                logger.info(f"Read as text file, content length: {len(content)}")
            
            # Validate content
            if not content or len(content.strip()) < 50:
                logger.warning(f"Content too short: {len(content)} characters")
                return None, "❌ File appears to be empty or too short. Please check the file content."
            
            # Limit content size for processing
            if len(content) > 10000:
                content = content[:10000] + "\n\n[Content truncated for processing]"
                logger.info("Content truncated to 10000 characters")
            
            # Basic validation - check if it looks like a resume
            if not any(keyword in content.lower() for keyword in ['experience', 'education', 'skills', 'employment', 'work', 'resume', 'cv']):
                logger.warning("Content doesn't appear to be a resume")
                return content, "⚠️ Warning: This doesn't appear to be a resume, but I'll try to process it anyway."
            
            logger.info("File processing completed successfully")
            return content, None
            
        except UnicodeDecodeError as e:
            logger.error(f"Unicode decode error: {e}")
            return None, "❌ Could not read file - it may be corrupted or in an unsupported format."
        except Exception as e:
            logger.error(f"File processing error: {e}")
            return None, f"❌ Error reading file: {str(e)}"
