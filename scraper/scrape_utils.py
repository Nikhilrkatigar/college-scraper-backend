import re
import requests
from bs4 import BeautifulSoup


def scrape_html(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    res = requests.get(url, headers=headers, timeout=15)
    return res.text


def extract_emails(html: str):
    return list(set(re.findall(
        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        html
    )))


def is_valid_phone(raw: str) -> bool:
    digits = re.sub(r"\D", "", raw)

    # Reject dates like 14072025 or 20250714
    if re.match(r"^(19|20)\d{6}$", digits):
        return False

    # Indian mobile or landline (with STD)
    if len(digits) not in (10, 11):
        return False

    # Reject obvious junk
    if digits.startswith("000"):
        return False
    if digits == digits[0] * len(digits):
        return False

    return True


def extract_phones(html: str):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ")

    candidates = re.findall(
        r"\+91[\s\-]?\d{10}|0\d{2,4}[\s\-]?\d{6,8}|\d{10}",
        text
    )

    valid = []
    for c in candidates:
        if is_valid_phone(c):
            valid.append(re.sub(r"\D", "", c))

    return list(set(valid))
