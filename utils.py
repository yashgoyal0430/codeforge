import smtplib
import dns.resolver
import pandas as pd
import logging
import random
import string
import socket
from pypdf import PdfReader

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_permutations(first_name, last_name, domain):
    """
    Generate standard email permutations for a given name and domain.
    """
    fn = first_name.lower().strip()
    ln = last_name.lower().strip()
    d = domain.lower().strip()
    
    if not fn or not ln or not d:
        return []

    permutations = [
        f"{fn}.{ln}@{d}",       # first.last
        f"{fn}@{d}",            # first
        f"{fn}{ln}@{d}",        # firstlast
        f"{fn[0]}.{ln}@{d}",    # f.last
        f"{fn[0]}{ln}@{d}",     # flast
        f"{fn}_{ln}@{d}",       # first_last
        f"{ln}.{fn}@{d}",       # last.first
        f"{ln}@{d}",            # last
        f"{fn[0]}_{ln}@{d}",    # f_last
    ]
    return permutations

def get_mx_record(domain):
    """Get the primary MX record for a domain."""
    try:
        answers = dns.resolver.resolve(domain, 'MX')
        # Sort by preference and return the first one
        mx_record = sorted([(r.preference, r.exchange.to_text()) for r in answers])[0][1]
        return mx_record.rstrip('.')
    except Exception as e:
        logger.error(f"DNS Lookup failed for {domain}: {e}")
        return None

def check_dns_txt(domain, prefix):
    """Check for existence of TXT records starting with prefix (e.g., v=spf1)."""
    try:
        answers = dns.resolver.resolve(domain, 'TXT')
        for rdata in answers:
            txt_record = rdata.to_text().strip('"')
            if txt_record.startswith(prefix):
                return True
    except:
        pass
    return False

def verify_email_smtp(email, sender_email="test@example.com"):
    """
    Verify email and return detailed analysis.
    Returns: Dict with status, mx, banner, and other metadata.
    """
    domain = email.split('@')[-1]
    local_part = email.split('@')[0]
    
    # FREE PROVIDER CHECK
    free_providers = {'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com', 'icloud.com'}
    is_free = domain in free_providers
    
    # ROLE ACCOUNT CHECK
    role_accounts = {'admin', 'support', 'info', 'sales', 'contact', 'hello', 'jobs', 'billing'}
    is_role = local_part in role_accounts

    # DNS CHECKS
    mx_record = get_mx_record(domain)
    has_spf = check_dns_txt(domain, "v=spf1")
    has_dmarc = check_dns_txt(f"_dmarc.{domain}", "v=DMARC1")

    details = {
        "status": "Unknown",
        "mx_record": mx_record,
        "smtp_banner": None,
        "has_spf": has_spf,
        "has_dmarc": has_dmarc,
        "is_role_account": is_role,
        "is_free_provider": is_free,
        "reason": ""
    }

    if not mx_record:
        details["status"] = "Unknown (No MX)"
        details["reason"] = "No MX records found for domain."
        return details

    try:
        # Create SMTP connection
        server = smtplib.SMTP(timeout=10)
        server.set_debuglevel(0)
        
        # Connect to MX server
        code, banner = server.connect(mx_record, 25)
        details["smtp_banner"] = str(banner) # Convert bytes or varying format to string
        
        if code != 220:
            server.quit()
            details["status"] = "Unknown (Connect Fail)"
            details["reason"] = f"Server returned code {code} on connect."
            return details

        server.helo(server.local_hostname or 'localhost')
        server.mail(sender_email)
        
        # Check the specific email
        code, message = server.rcpt(email)
        server.quit()

        if code == 250:
            # Email accepted, now check for Catch-All
            if is_catch_all(domain, mx_record, sender_email):
                details["status"] = "Risky (Catch-All)"
                details["reason"] = "Server accepts all emails (Catch-All)."
            else:
                details["status"] = "Valid"
                details["reason"] = "SMTP handshake successful."
        elif code == 550:
            details["status"] = "Invalid"
            details["reason"] = "User unknown (550 Error)."
        else:
            details["status"] = f"Unknown ({code})"
            details["reason"] = f"Unexpected SMTP response: {code}"

    except socket.timeout:
        details["status"] = "Unknown (Timeout)"
        details["reason"] = "Connection timed out."
    except socket.error as e:
        logger.error(f"Socket error for {email}: {e}")
        details["status"] = "Unknown (Connection Error)"
        details["reason"] = str(e)
    except Exception as e:
        logger.error(f"Validation error for {email}: {e}")
        details["status"] = "Unknown"
        details["reason"] = str(e)
        
    return details

def is_catch_all(domain, mx_record, sender_email="test@example.com"):
    """
    Check if a domain has a catch-all configuration by testing a random invalid user.
    """
    random_user = ''.join(random.choices(string.ascii_lowercase + string.digits, k=15))
    test_email = f"{random_user}@{domain}"
    
    try:
        server = smtplib.SMTP(timeout=10)
        server.connect(mx_record, 25)
        server.helo(server.local_hostname or 'localhost')
        server.mail(sender_email)
        code, _ = server.rcpt(test_email)
        server.quit()
        return code == 250
    except:
        return False

def extract_text_from_pdf(uploaded_file):
    """
    Extract text from a PyPDF2 reader object or stream.
    """
    try:
        reader = PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            content = page.extract_text()
            if content:
                text += content + "\n"
        return text.strip()
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        return ""
