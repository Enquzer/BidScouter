"""
BidScouter - Generic/Newspaper sites crawler (Addis Zemen, Reporter, EthioTender, etc.)
Handles simple HTML tender listing pages.
"""
import logging
from typing import List
from .base import (
    BaseCrawler, BidData, is_garment_related, detect_category,
    extract_amount, extract_security_type, extract_phones,
    extract_emails, parse_date
)

logger = logging.getLogger("bidscouter.crawler.generic")


class GenericNewsCrawler(BaseCrawler):
    """Crawler for newspaper and simple listing sites."""

    SELECTORS = [
        "article", ".tender", ".bid", ".post", ".entry",
        "table tbody tr", "li.item", ".listing-item",
        ".content-item", ".notice",
    ]

    def crawl(self) -> List[BidData]:
        results = []
        with self.get_client() as client:
            soup = self.fetch(client, self.base_url)
            if not soup:
                return []
            bids = self._parse(soup, client)
            results.extend(bids)

            # Follow pagination (up to 5 pages)
            for page in range(2, 6):
                for pg_url in [
                    f"{self.base_url}?page={page}",
                    f"{self.base_url}/page/{page}",
                    f"{self.base_url}?p={page}",
                ]:
                    s = self.fetch(client, pg_url)
                    if s:
                        extra = self._parse(s, client)
                        if not extra:
                            break
                        results.extend(extra)
                        break

        return self._deduplicate(results)

    def _parse(self, soup, client) -> List[BidData]:
        bids = []
        items = []
        for sel in self.SELECTORS:
            items = soup.select(sel)
            if items:
                break

        if not items:
            # Fallback: look for links containing garment keywords
            links = soup.find_all("a", href=True)
            for a in links:
                text = a.get_text(strip=True)
                if is_garment_related(text):
                    bid = BidData()
                    bid.title = text[:200]
                    href = a["href"]
                    bid.source_url = href if href.startswith("http") else self.base_url + href
                    bid.source_site = self.site_name
                    bid.source_site_id = self.site_id
                    bid.category = detect_category(text)
                    bid.raw_text = text
                    detail = self.fetch(client, bid.source_url)
                    if detail:
                        self._enrich(bid, detail)
                    bids.append(bid)
            return bids

        for item in items:
            text = item.get_text(" ", strip=True)
            if not is_garment_related(text):
                continue
            bid = BidData()
            bid.source_site = self.site_name
            bid.source_site_id = self.site_id
            bid.category = detect_category(text)
            bid.raw_text = text[:2000]

            link = item.select_one("a[href]")
            if link:
                bid.title = link.get_text(strip=True)[:200]
                href = link.get("href", "")
                bid.source_url = href if href.startswith("http") else self.base_url + href

            if not bid.title:
                bid.title = text[:120]

            if bid.source_url:
                detail = self.fetch(client, bid.source_url)
                if detail:
                    self._enrich(bid, detail)
            else:
                bid.contact_phone = extract_phones(text)
                bid.contact_email = extract_emails(text)
                bid.bid_security_type = extract_security_type(text)

            if bid.title:
                bids.append(bid)

        return bids

    def _enrich(self, bid: BidData, soup):
        full = soup.get_text(" ", strip=True)
        bid.raw_text = full[:3000]
        bid.contact_phone = extract_phones(full)
        bid.contact_email = extract_emails(full)
        bid.bid_security_type = extract_security_type(full)
        bid.bid_security_amount = extract_amount(full)

        for label in ["deadline", "closing date", "submission", "last date"]:
            el = soup.find(string=lambda t: t and label in t.lower())
            if el and el.parent:
                s = el.parent.find_next_sibling()
                if s:
                    d = parse_date(s.get_text(strip=True))
                    if d:
                        bid.deadline = d
                        break

        for label in ["address", "location", "venue", "apply at"]:
            el = soup.find(string=lambda t: t and label in t.lower())
            if el and el.parent:
                s = el.parent.find_next_sibling()
                if s:
                    bid.location = s.get_text(strip=True)[:200]
                    break

        for label in ["organization", "procuring", "company", "institution", "ministry"]:
            el = soup.find(string=lambda t: t and label in t.lower())
            if el and el.parent:
                s = el.parent.find_next_sibling()
                if s:
                    bid.company = s.get_text(strip=True)[:200]
                    break

        for label in ["registration fee", "document fee", "bid document price"]:
            el = soup.find(string=lambda t: t and label in t.lower())
            if el:
                bid.registration_fee = extract_amount(str(el))

    def _deduplicate(self, bids: List[BidData]) -> List[BidData]:
        seen = set()
        unique = []
        for b in bids:
            key = b.source_url or b.title
            if key not in seen:
                seen.add(key)
                unique.append(b)
        return unique


# ─── Concrete site classes ──────────────────────────────────────────────────

class AddisZemenCrawler(GenericNewsCrawler):
    site_id = "addiszemen"
    site_name = "Addis Zemen"
    base_url = "https://www.addiszemen.com/tenders"


class EthiopianReporterCrawler(GenericNewsCrawler):
    site_id = "ethiopianreporter"
    site_name = "Ethiopian Reporter"
    base_url = "https://www.ethiopianreporter.com/category/tenders"


class EthioTenderCrawler(GenericNewsCrawler):
    site_id = "ethiotender"
    site_name = "EthioTender"
    base_url = "https://ethiotender.com"


class MercatoCrawler(GenericNewsCrawler):
    site_id = "mercato"
    site_name = "Mercato Tenders"
    base_url = "https://mercato.com.et/tenders"


class PPAACrawler(GenericNewsCrawler):
    site_id = "ppaa"
    site_name = "PPAA Portal"
    base_url = "https://www.ppaa.gov.et/procurement-notices"


class UNGMCrawler(GenericNewsCrawler):
    site_id = "ungm"
    site_name = "UN Global Marketplace"
    base_url = "https://www.ungm.org/Public/Notice?noticeTypeIds=0&memberBodyIds=29"  # Ethiopia

    def crawl(self) -> List[BidData]:
        # UNGM uses JS rendering - attempt basic HTTP scrape
        results = []
        with self.get_client() as client:
            soup = self.fetch(client, self.base_url)
            if soup:
                bids = self._parse(soup, client)
                results.extend(bids)
        return self._deduplicate(results)
