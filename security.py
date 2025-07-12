# security.py
from functools import wraps
from flask import request, render_template, redirect, url_for
from collections import defaultdict
from datetime import datetime, timedelta
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RateLimiter:
    def __init__(self):
        self.failed_attempts = defaultdict(list)
        self.blocked_ips = {}
    
    def is_ip_blocked(self, ip):
        if ip in self.blocked_ips:
            if datetime.now() < self.blocked_ips[ip]:
                return True
            else:
                del self.blocked_ips[ip]
        return False
    
    def add_failed_attempt(self, ip):
        now = datetime.now()
        # Clean old attempts (older than 15 minutes)
        self.failed_attempts[ip] = [
            attempt for attempt in self.failed_attempts[ip] 
            if now - attempt < timedelta(minutes=15)
        ]
        
        self.failed_attempts[ip].append(now)
        
        # Log the attempt
        logger.warning(f"Failed login attempt from IP: {ip} (Total: {len(self.failed_attempts[ip])})")
        
        # Block if too many attempts
        if len(self.failed_attempts[ip]) >= 5:
            self.blocked_ips[ip] = now + timedelta(minutes=15)
            logger.error(f"IP blocked due to too many attempts: {ip}")
            return True
        
        return False
    
    def get_attempt_count(self, ip):
        now = datetime.now()
        self.failed_attempts[ip] = [
            attempt for attempt in self.failed_attempts[ip] 
            if now - attempt < timedelta(minutes=15)
        ]
        return len(self.failed_attempts[ip])

# Global rate limiter instance
rate_limiter = RateLimiter()

def check_honeypot(form_data):
    """Check for honeypot field - bots often fill these out"""
    honeypot_fields = ['email', 'website', 'url', 'phone']
    for field in honeypot_fields:
        if form_data.get(field):
            return True
    return False

def rate_limit_login(f):
    """Decorator to add rate limiting to login routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method == 'POST':
            ip = request.remote_addr
            
            # Check if IP is blocked
            if rate_limiter.is_ip_blocked(ip):
                logger.warning(f"Blocked IP attempted login: {ip}")
                return render_template('login.html', 
                    error="Too many failed attempts. Please try again in 15 minutes.")
            
            # Check honeypot
            if check_honeypot(request.form):
                logger.warning(f"Honeypot triggered from IP: {ip}")
                rate_limiter.add_failed_attempt(ip)
                # Don't reveal it was a honeypot
                time.sleep(2)
                return render_template('login.html', 
                    error="Invalid access token.")
        
        return f(*args, **kwargs)
    return decorated_function

def handle_failed_login(ip):
    """Handle failed login attempt with progressive delays"""
    attempt_count = rate_limiter.get_attempt_count(ip)
    
    # Progressive delay: 1s, 2s, 4s, 8s (max)
    if attempt_count > 0:
        delay = min(2 ** (attempt_count - 1), 8)
        time.sleep(delay)
    
    # Add the failed attempt
    is_blocked = rate_limiter.add_failed_attempt(ip)
    
    if is_blocked:
        return "Account temporarily locked due to too many failed attempts. Please try again in 15 minutes."
    else:
        remaining = 5 - len(rate_limiter.failed_attempts[ip])
        return f"Invalid access token. {remaining} attempts remaining."
