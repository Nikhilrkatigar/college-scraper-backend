from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
import requests
import pandas as pd
import uuid
import os
import re
from typing import Dict, Set
from threading import Thread
from concurrent.futures import ThreadPoolExecutor, as_completed
from database import colleges_collection
from scraper.scrape_utils import scrape_html, extract_emails, extract_phones
from auth.auth_utils import get_current_user

router = APIRouter(prefix="/extract", tags=["Extraction"])

SERPAPI_KEY = os.getenv("SERPAPI_KEY") or "67e72844152500a7746da205e6f5cecd2309f794d78c2e7a6c8ddb384f5de84d"
EXTRACTION_JOBS: Dict[str, dict] = {}
PROCESSED_DATA: Dict[str, dict] = {}

PHONE_PATTERN = re.compile(r'\+?91[-.\s]?\d{10}|\d{10}')
EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')

# MUST contain these patterns (at least one)
REQUIRED_PATTERNS = [
    r'\bcollege\s+of\s+engineering\b',
    r'\binstitute\s+of\s+technology\b',
    r'\bpolytechnic\b',
    r'\b(engineering|technical)\s+college\b',
    r'\buniversity\b.*\b(engineering|technology)\b',
    r'\b(iit|nit|iiit)\b'
]

# AUTO-REJECT if title contains these
BLACKLIST_PATTERNS = [
    r'^(manufacturing|unit\s+address)',  # Manufacturing/Unit Address
    r'\b(amul|dairy|milk|food|product)\b',  # Food companies
    r'\btop\s+\d*\s*(college|university|engineering)',  # Top colleges
    r'\bbest\s+\d*\s*(college|university)',  # Best colleges  
    r'\blist\s+of\s+(college|private|government)',  # Lists
    r'\d+\s*\+\s*(college|engineering|government)',  # "20+ colleges"
    r'\b(near\s+me|in\s+\w+\s+20\d{2})\b',  # "near me", "in City 2026"
    r'\b(how\s+to|why|what|compare|vs)\b',  # Question/comparison words
    r'\b(connect\s+with|get\s+in\s+touch)\b',  # Contact prompts
    r'\b(admission|entrance|exam|result|cutoff|rank)\b',  # Admission-related
    r'\b(placement|fee|course|eligibility)\b',  # Info pages
    r'\b(master\s+of|bachelor\s+of)\s+arts\b',  # Wrong degrees
    r'\.(png|jpg|jpeg|webp|gif)(@\dx)?',  # Image files
    r'\bcollege\s+of\s+(commerce|arts|science|medicine)\b',  # Non-engineering
    r'\bmedical\s+college\b',  # Medical colleges
    r'\b(facebook|twitter|instagram|youtube|wikipedia)\b',  # Social media
]


def normalize_name(name: str) -> str:
    """Normalize for duplicate detection"""
    # Remove location suffixes
    name = re.sub(r',?\s*\b(solapur|mumbai|pune|nashik)\b.*$', '', name, flags=re.IGNORECASE)
    # Remove common words
    name = re.sub(r'\b(college|institute|university|polytechnic|of|the)\b', '', name, flags=re.IGNORECASE)
    # Clean
    name = re.sub(r'[^\w\s]', '', name)
    name = re.sub(r'\s+', '', name).strip().lower()
    return name


def is_duplicate_name(name: str, location_key: str) -> bool:
    """Check if college name exists"""
    if location_key not in PROCESSED_DATA:
        return False
    
    normalized = normalize_name(name)
    
    for existing in PROCESSED_DATA[location_key].get('names', set()):
        existing_norm = normalize_name(existing)
        
        # Exact match
        if normalized == existing_norm:
            return True
        
        # Substring match (only if both > 8 chars)
        if len(normalized) > 8 and len(existing_norm) > 8:
            if normalized in existing_norm or existing_norm in normalized:
                return True
    
    return False


def is_valid_college(title: str, college_type: str) -> bool:
    """Ultra-strict validation"""
    title_lower = title.lower()
    
    # Check blacklist first (immediate reject)
    for pattern in BLACKLIST_PATTERNS:
        if re.search(pattern, title_lower):
            return False
    
    # Must match at least one required pattern
    if not any(re.search(pattern, title_lower) for pattern in REQUIRED_PATTERNS):
        return False
    
    # For engineering type, must have engineering/technology/polytechnic
    if college_type.lower() == 'engineering':
        if not any(word in title_lower for word in ['engineering', 'technology', 'polytechnic', 'iit', 'nit']):
            return False
    
    # No questions
    if '?' in title:
        return False
    
    # Digit limit
    if sum(c.isdigit() for c in title) > 6:
        return False
    
    # Length check
    if len(title) < 20 or len(title) > 100:
        return False
    
    # Word count
    words = [w for w in title.split() if len(w) > 1]
    if len(words) < 3 or len(words) > 12:
        return False
    
    # Must start with a letter or quote
    if not title[0].isalpha() and title[0] not in ['"', "'"]:
        return False
    
    return True


def clean_college_name(title: str, college_type: str) -> str:
    """Clean college name"""
    # Split and take first part
    title = re.split(r'\s*[|–—]\s*', title)[0]
    
    # Remove trailing location like "- Solapur" or ", Solapur"
    title = re.sub(r'[,\-]\s*\w+\s*$', '', title)
    
    # Remove years
    title = re.sub(r'\(.*?\d{4}.*?\)', '', title)
    title = re.sub(r'\b(est|established|since)\W*\d{4}\b', '', title, flags=re.IGNORECASE)
    
    # Remove image files
    title = re.sub(r'\b\w+\.(png|jpg|jpeg|webp|gif)(@\dx)?\b', '', title, flags=re.IGNORECASE)
    
    # Remove abbreviations in brackets at end
    title = re.sub(r'\s*[\[\(][A-Z]{2,10}[\]\)]\s*$', '', title)
    
    # Remove "..." at end
    title = re.sub(r'\s*\.{3,}\s*$', '', title)
    
    # Clean whitespace
    title = ' '.join(title.split()).strip()
    
    # Remove trailing punctuation
    title = re.sub(r'[.,;:]+$', '', title).strip()
    
    if not is_valid_college(title, college_type):
        return ""
    
    return title


def clean_phone(phone: str) -> str:
    """Validate phone"""
    digits = re.sub(r'\D', '', phone)
    
    if digits.startswith('91') and len(digits) == 12:
        digits = digits[2:]
    
    # 10-digit mobile (6-9)
    if len(digits) == 10 and digits[0] in '6789':
        return digits
    
    # 11-digit landline
    if len(digits) == 11 and digits[0] == '0':
        return digits
    
    return ""


def is_valid_email(email: str) -> bool:
    """Validate email"""
    email_lower = email.lower()
    
    # Blacklist
    invalid = ['noreply', 'example', 'test@', 'localhost', 'webmaster', 'postmaster']
    if any(x in email_lower for x in invalid):
        return False
    
    if '@' not in email or '.' not in email.split('@')[1]:
        return False
    
    if len(email) < 6 or len(email) > 80:
        return False
    
    return True


def extract_best_email(html: str) -> str:
    """Extract email with scoring"""
    emails = EMAIL_PATTERN.findall(html[:50000])
    
    if not emails:
        return "Not Mentioned"
    
    scored = []
    for email in set(emails):
        if not is_valid_email(email):
            continue
        
        score = 0
        el = email.lower()
        
        # .edu, .ac.in - highest priority
        if '.edu' in el or '.ac.in' in el:
            score += 30
        
        # Official prefixes
        if any(el.startswith(p) for p in ['info@', 'admission@', 'office@', 'principal@', 'contact@', 'admin@']):
            score += 20
        
        # Common providers
        if any(p in el for p in ['gmail.com', 'yahoo.com', 'rediffmail.com', 'outlook.com', 'hotmail.com']):
            score += 10
        
        # Domain matches college name patterns
        if any(w in el for w in ['college', 'university', 'institute', 'polytechnic']):
            score += 5
        
        # Penalize personal names
        if any(x in el for x in ['personal', 'private', 'shukla', 'kumar', 'sharma', 'gupta']):
            score -= 20
        
        scored.append((score, email))
    
    if not scored or max(s[0] for s in scored) < 5:
        return "Not Mentioned"
    
    scored.sort(reverse=True)
    return scored[0][1]


def extract_best_phone(html: str) -> str:
    """Extract phone"""
    phones = PHONE_PATTERN.findall(html[:50000])
    
    for phone in phones:
        cleaned = clean_phone(phone)
        if cleaned:
            return cleaned
    
    return "Not Mentioned"


def get_location_key(city: str, state: str, region: str) -> str:
    """Location key"""
    return f"{region}_{state}_{city}".lower().replace(" ", "_")


def init_tracking(location_key: str, city: str):
    """Initialize tracking"""
    if location_key in PROCESSED_DATA:
        return
    
    PROCESSED_DATA[location_key] = {
        'urls': set(),
        'names': set()
    }
    
    # Load from DB
    existing = colleges_collection.find(
        {"city": city},
        {"website": 1, "college_name": 1}
    )
    
    for doc in existing:
        if doc.get('website'):
            PROCESSED_DATA[location_key]['urls'].add(doc['website'].lower().rstrip('/'))
        if doc.get('college_name'):
            PROCESSED_DATA[location_key]['names'].add(doc['college_name'])


def is_duplicate(url: str, name: str, location_key: str) -> bool:
    """Check duplicates"""
    url_clean = url.lower().rstrip('/')
    
    # Check URL
    for existing_url in PROCESSED_DATA[location_key]['urls']:
        if url_clean == existing_url or url_clean in existing_url or existing_url in url_clean:
            return True
    
    # Check name
    if is_duplicate_name(name, location_key):
        return True
    
    return False


def process_result(item: dict, city: str, state: str, region: str,
                   college_type: str, done_by: str, location_key: str) -> bool:
    """Process result"""
    try:
        raw_title = item.get("title", "")
        title = clean_college_name(raw_title, college_type)
        
        if not title:
            return False
        
        link = item.get("link", "").strip()
        if not link or not link.startswith('http'):
            return False
        
        # Duplicate check
        if is_duplicate(link, title, location_key):
            return False
        
        # Extract contacts
        email = "Not Mentioned"
        mobile = "Not Mentioned"
        
        try:
            html = scrape_html(link)
            email = extract_best_email(html)
            mobile = extract_best_phone(html)
        except:
            pass
        
        # Insert
        colleges_collection.insert_one({
            "college_name": title,
            "email": email,
            "mobile": mobile,
            "city": city,
            "state": state,
            "region": region,
            "type": college_type,
            "website": link,
            "completed": False,
            "done_by": done_by
        })
        
        # Mark processed
        PROCESSED_DATA[location_key]['urls'].add(link.lower().rstrip('/'))
        PROCESSED_DATA[location_key]['names'].add(title)
        
        return True
    
    except Exception:
        return False


def fetch_all_results(query: str, max_results: int = 200) -> list:
    """Fetch ALL pages until no more results"""
    all_results = []
    consecutive_empty = 0
    
    for start in range(0, max_results, 10):
        try:
            r = requests.get(
                "https://serpapi.com/search",
                params={
                    "engine": "google",
                    "q": query,
                    "api_key": SERPAPI_KEY,
                    "google_domain": "google.co.in",
                    "gl": "in",
                    "hl": "en",
                    "num": 10,
                    "start": start
                },
                timeout=15
            )
            
            if r.status_code != 200:
                consecutive_empty += 1
                if consecutive_empty >= 2:
                    break
                continue
            
            results = r.json().get("organic_results", [])
            
            if not results:
                consecutive_empty += 1
                if consecutive_empty >= 2:  # Stop after 2 consecutive empty pages
                    break
                continue
            
            consecutive_empty = 0
            all_results.extend(results)
            
        except Exception:
            consecutive_empty += 1
            if consecutive_empty >= 2:
                break
    
    return all_results


def extraction_worker(job_id: str, region: str, state: str, city: str,
                      college_type: str, done_by: str):
    """Worker - fetches ALL pages"""
    try:
        location_key = get_location_key(city, state, region)
        init_tracking(location_key, city)
        
        # Build query
        if college_type.lower() == "all":
            query = f'"{city}" "{state}" college official website'
        else:
            query = f'"{city}" "{state}" {college_type} college official website'
        
        # Fetch ALL results
        EXTRACTION_JOBS[job_id]["status"] = "fetching"
        all_results = fetch_all_results(query, max_results=200)
        
        EXTRACTION_JOBS[job_id]["total_found"] = len(all_results)
        
        if not all_results:
            EXTRACTION_JOBS[job_id]["status"] = "completed"
            EXTRACTION_JOBS[job_id]["message"] = "No results found"
            return
        
        EXTRACTION_JOBS[job_id]["status"] = "processing"
        
        # Process in parallel
        inserted = 0
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(
                    process_result,
                    item, city, state, region, college_type, done_by, location_key
                ): item for item in all_results
            }
            
            for future in as_completed(futures):
                EXTRACTION_JOBS[job_id]["processed"] += 1
                if future.result():
                    inserted += 1
                    EXTRACTION_JOBS[job_id]["inserted"] = inserted
        
        EXTRACTION_JOBS[job_id]["status"] = "completed"
        EXTRACTION_JOBS[job_id]["message"] = f"Scanned {len(all_results)} results, found {inserted} colleges"
    
    except Exception as e:
        EXTRACTION_JOBS[job_id]["status"] = "failed"
        EXTRACTION_JOBS[job_id]["error"] = str(e)


@router.post("/run")
def run_extraction(
    region: str,
    state: str,
    city: str,
    college_type: str,
    current_user=Depends(get_current_user)
):
    """Start extraction - fetches ALL pages"""
    if not SERPAPI_KEY:
        raise HTTPException(500, "SERPAPI_KEY not configured")
    
    job_id = uuid.uuid4().hex
    
    EXTRACTION_JOBS[job_id] = {
        "status": "starting",
        "total_found": 0,
        "processed": 0,
        "inserted": 0
    }
    
    Thread(
        target=extraction_worker,
        args=(job_id, region, state, city, college_type, current_user["username"]),
        daemon=True
    ).start()
    
    return {"job_id": job_id}


@router.get("/status/{job_id}")
def get_status(job_id: str):
    """Status"""
    return EXTRACTION_JOBS.get(job_id, {"status": "not_found"})


@router.post("/export")
def export_extracted_data(data: list):
    """Export"""
    if not data:
        raise HTTPException(400, "No data to export")
    
    df = pd.DataFrame(data)
    filename = f"extracted_{uuid.uuid4().hex}.xlsx"
    df.to_excel(filename, index=False)
    
    return FileResponse(
        path=filename,
        filename="extracted_colleges.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )