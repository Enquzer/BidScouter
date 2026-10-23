"""
BidScouter - MerTender.com Crawler
URL: https://mertender.com
"""
import logging
from typing import List
from .base import (
    BaseCrawler, BidData, is_garment_related, detect_category,
    extract_amount, extract_security_type, extract_phones,
    extract_emails, parse_date
)

logger = logging.getLogger("bidscouter.crawler.mertender")


class MerTenderCrawler(BaseCrawler):
    site_id = "mertender"
    site_name = "MerTender"
    base_url = "https://mertender.com"

    SEARCH_TERMS = ["uniform", "garment", "clothing", "textile", "sportswear", "apparel"]
    LIST_PATHS = ["/tenders", "/ethiopia/tenders", "/procurement/ethiopia"]

    def crawl(self) -> List[BidData]:
        results = []
        with self.get_client() as client:
            if self.username and self.password:
                self._login(client)

            for path in self.LIST_PATHS:
                url = self.base_url + path
                soup = self.fetch(client, url)
                if soup:
                    bids = self._parse_list(soup, client)
                    results.extend(bids)

            for term in self.SEARCH_TERMS:
                for search_path in [
                    f"/search?q={term}&country=ET",
                    f"/tenders/search?keyword={term}",
                    f"/?s={term}",
                ]:
                    url = self.base_url + search_path
                    soup = self.fetch(client, url)
                    if soup:
                        bids = self._parse_list(soup, client)
                        results.extend(bids)

        return self._deduplicate(results)

    def _login(self, client):
        try:
            r = client.get(f"{self.base_url}/login")
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(r.text, "lxml")
            token_inp = soup.find("input", {"name": "_token"})
            token = token_inp["value"] if token_inp else ""
            client.post(f"{self.base_url}/login", data={
                "email": self.username,
                "password": self.password,
                "_token": token,
            })
        except Exception as e:
            logger.warning(f"[{self.site_id}] Login failed: {e}")

    def _parse_list(self, soup, client) -> List[BidData]:
        bids = []
        items = (
            soup.select(".tender-card") or
            soup.select(".tender-item") or
            soup.select("article") or
            soup.select(".post") or
            soup.select("table tbody tr")
        )
        for item in items:
            text = item.get_text(" ", strip=True)
            if not is_garment_related(text):
                continue
            bid = self._build_bid(item, client, text)
            if bid:
                bids.append(bid)
        return bids

    def _build_bid(self, item, client, text: str) -> BidData:
        bid = BidData()
        bid.source_site = self.site_name
        bid.source_site_id = self.site_id
        bid.category = detect_category(text)
        bid.raw_text = text[:2000]

        link = item.select_one("a[href]")
        if link:
            bid.title = link.get_text(strip=True)
            href = link.get("href", "")
            bid.source_url = href if href.startswith("http") else self.base_url + href

        if not bid.title:
            bid.title = text[:120]

        if bid.source_url:
            detail = self.fetch(client, bid.source_url)
            if detail:
                full = detail.get_text(" ", strip=True)
                bid.raw_text = full[:3000]
                bid.company = self._find_field(detail, ["organization", "procuring", "company", "entity"])
                deadline_str = self._find_field(detail, ["closing", "deadline", "submission"])
                if deadline_str:
                    bid.deadline = parse_date(deadline_str)
                bid.location = self._find_field(detail, ["address", "location", "venue"])
                bid.contact_phone = extract_phones(full)
                bid.contact_email = extract_emails(full)
                bid.bid_security_type = extract_security_type(full)
                bid.bid_security_amount = extract_amount(full)
        else:
            bid.contact_phone = extract_phones(text)
            bid.contact_email = extract_emails(text)
            bid.bid_security_type = extract_security_type(text)

        return bid

    def _find_field(self, soup, labels: list) -> str:
        for label in labels:
            el = soup.find(string=lambda t: t and label in t.lower())
            if el and el.parent:
                sib = el.parent.find_next_sibling()
                if sib:
                    return sib.get_text(strip=True)[:200]
        return ""

    def _deduplicate(self, bids: List[BidData]) -> List[BidData]:
        seen = set()
        unique = []
        for b in bids:
            key = b.source_url or b.title
            if key not in seen:
                seen.add(key)
                unique.append(b)
        return unique
