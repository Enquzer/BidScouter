"""
BidScouter - Base crawler class
All site-specific crawlers inherit from this.
"""
import logging
import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger("bidscouter.crawler")


class BidData:
    """Structured bid data extracted from a site."""

    def __init__(self):
        self.title: str = ""
        self.company: str = ""
        self.category: str = ""
        self.bid_number: str = ""
        self.posted_date: Optional[datetime] = None
        self.deadline: Optional[datetime] = None
        self.registration_fee: Optional[float] = None
        self.registration_fee_currency: str = "ETB"
        self.bid_security_type: str = ""
        self.bid_security_amount: Optional[float] = None
        self.bid_security_currency: str = "ETB"
        self.location: str = ""
        self.contact_name: str = ""
        self.contact_phone: str = ""
        self.contact_email: str = ""
        self.source_url: str = ""
        self.source_site: str = ""
        self.source_site_id: str = ""
        self.raw_text: str = ""

    def to_dict(self):
        return {
            "title": self.title,
            "company": self.company,
            "category": self.category,
            "bid_number": self.bid_number,
            "posted_date": self.posted_date,
            "deadline": self.deadline,
            "registration_fee": self.registration_fee,
            "registration_fee_currency": self.registration_fee_currency,
            "bid_security_type": self.bid_security_type,
            "bid_security_amount": self.bid_security_amount,
            "bid_security_currency": self.bid_security_currency,
            "location": self.location,
            "contact_name": self.contact_name,
            "contact_phone": self.contact_phone,
            "contact_email": self.contact_email,
            "source_url": self.source_url,
            "source_site": self.source_site,
            "source_site_id": self.source_site_id,
            "raw_text": self.raw_text,
        }


GARMENT_KEYWORDS = [
    r"\buniforms?\b", r"\bt-?shirts?\b", r"\bpolos?\b", r"\btrousers?\b",
    r"\bsportswears?\b", r"\bsport\s?wears?\b", r"\bworkwears?\b",
    r"\bwork\s?wears?\b", r"\boveralls?\b", r"\bcoveralls?\b",
    r"\bgarments?\b", r"\bapparels?\b", r"\bclothings?\b", r"\btextiles?\b",
    r"\bfabrics?\b", r"\bwearables?\b", r"\bhospital\s?gowns?\b", r"\bscrubs?\b",
    r"\bmedical\s?uniforms?\b", r"\bschool\s?uniforms?\b",
    r"\bmilitary\s?uniforms?\b", r"\bsecurity\s?uniforms?\b",
    r"\bjackets?\b", r"\bvests?\b", r"\baprons?\b", r"\bshirts?\b",
    r"\bblouses?\b", r"\bdress(?:es)?\b", r"\bshorts?\b", r"\bleggings?\b",
    r"\bsocks?\b", r"\bprotective\s?cloth(?:es|ing)?\b", r"\bppe\b",
    r"\bhi.?vis\b", r"\bhigh.?visibility\b", r"\bblankets?\b",
    r"\bbedsheets?\b", r"\blinens?\b", r"\bcurtains?\b",
    # Amharic
    r"ልብስ", r"ዩኒፎርም", r"ጨርቅ", r"አለባበስ",
]

COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in GARMENT_KEYWORDS]


def is_garment_related(text: str) -> bool:
    """Return True if text matches any garment keyword."""
    for pattern in COMPILED_PATTERNS:
        if pattern.search(text):
            return True
    return False


def detect_category(text: str) -> str:
    """Best-guess garment category from text."""
    text_lower = text.lower()
    if any(k in text_lower for k in ["hospital gown", "scrub", "medical"]):
        return "Medical Uniform"
    if any(k in text_lower for k in ["school uniform"]):
        return "School Uniform"
    if any(k in text_lower for k in ["military", "security uniform", "police"]):
        return "Military/Security Uniform"
    if any(k in text_lower for k in ["sportswear", "sport wear", "sport shirt"]):
        return "Sportswear"
    if any(k in text_lower for k in ["overall", "coverall", "workwear", "work wear", "ppe", "protective"]):
        return "Workwear/PPE"
    if any(k in text_lower for k in ["t-shirt", "tshirt", "polo"]):
        return "T-Shirt / Polo"
    if any(k in text_lower for k in ["trouser", "shorts", "legging"]):
        return "Trousers / Bottoms"
    if any(k in text_lower for k in ["uniform"]):
        return "General Uniform"
    if any(k in text_lower for k in ["fabric", "textile", "cloth"]):
        return "Fabric / Textile"
    return "Garment"


def extract_amount(text: str) -> Optional[float]:
    """Extract first monetary amount from text."""
    patterns = [
        r"ETB\s*([0-9,]+(?:\.[0-9]+)?)",
        r"Birr\s*([0-9,]+(?:\.[0-9]+)?)",
        r"([0-9,]+(?:\.[0-9]+)?)\s*(?:ETB|Birr|birr)",
        r"([0-9,]+(?:\.[0-9]+)?)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1).replace(",", ""))
            except ValueError:
                pass
    return None


def extract_security_type(text: str) -> str:
    """Detect bid security type."""
    text_lower = text.lower()
    if "bank guarantee" in text_lower or "bank guaranty" in text_lower:
        return "Bank Guarantee"
    if "cpo" in text_lower or "certified personal" in text_lower:
        return "CPO"
    if "cash" in text_lower:
        return "Cash"
    if "bond" in text_lower:
        return "Bond"
    return ""


def extract_phones(text: str) -> str:
    """Extract Ethiopian phone numbers from text."""
    phones = re.findall(r"(?:\+251|0)[\d\s\-]{8,12}", text)
    return ", ".join(phones[:3]) if phones else ""


def extract_emails(text: str) -> str:
    emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
    return ", ".join(emails[:3]) if emails else ""


def parse_date(text: str) -> Optional[datetime]:
    """Try multiple date formats."""
    formats = [
        "%B %d, %Y", "%d %B %Y", "%d/%m/%Y", "%Y-%m-%d",
        "%d-%m-%Y", "%m/%d/%Y", "%Y/%m/%d",
    ]
    text = text.strip()
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    return None


class BaseCrawler(ABC):
    site_id: str = ""
    site_name: str = ""
    base_url: str = ""

    def __init__(self, credentials: dict, settings: dict):
        self.username = credentials.get("username", "")
        self.password = credentials.get("password", "")
        self.settings = settings
        self.timeout = settings.get("timeout_seconds", 30)
        self.headers = {
            "User-Agent": settings.get("user_agent", "BidScouter/1.0"),
            "Accept-Language": "en-US,en;q=0.9",
        }

    def get_client(self) -> httpx.Client:
        return httpx.Client(
            headers=self.headers,
            timeout=self.timeout,
            follow_redirects=True,
            verify=False,
        )

    def fetch(self, client: httpx.Client, url: str) -> Optional[BeautifulSoup]:
        try:
            r = client.get(url)
            r.raise_for_status()
            return BeautifulSoup(r.text, "lxml")
        except Exception as e:
            logger.warning(f"[{self.site_id}] Failed to fetch {url}: {e}")
            return None

    @abstractmethod
    def crawl(self) -> List[BidData]:
        """Crawl the site and return list of garment-related BidData."""
        pass
