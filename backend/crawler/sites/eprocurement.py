"""
BidScouter - Ethiopian Electronic Government Procurement (e-GP) Crawler
Portal: https://production.egp.gov.et/egp/home
API: https://production.egp.gov.et/po-gw/cms-v2/api/sourcing/get-grouped-sourcing
Auth: https://production.egp.gov.et/auth/connect/token
"""
import logging
from datetime import datetime
from typing import List, Optional
import httpx
from .base import (
    BaseCrawler, BidData, is_garment_related, detect_category,
    extract_amount, extract_security_type, extract_phones,
    extract_emails, parse_date
)

logger = logging.getLogger("bidscouter.crawler.eprocurement")


EXCLUDED_LOT_KEYWORDS = [
    "reagent", "chemical", "spare part", "stationery", "stationary",
    "furniture", "office equipment", "cleaning", "sanitary",
    "vehicle", "tyre", "tire", "computer", "printer", "network",
    "rent service", "maintenance service", "drug", "medicine",
    "building", "construction"
]


class EProcurementCrawler(BaseCrawler):
    site_id = "eprocurement"
    site_name = "Ethiopian e-GP Portal (production.egp.gov.et)"
    base_url = "https://production.egp.gov.et"
    api_gateway = "https://production.egp.gov.et/po-gw"
    auth_url = "https://production.egp.gov.et/auth/connect/token"

    def crawl(self) -> List[BidData]:
        results = []
        auth_headers = dict(self.headers)
        auth_headers.update({
            "Origin": "https://production.egp.gov.et",
            "Referer": "https://production.egp.gov.et/egp/home",
            "Accept": "application/json, text/plain, */*",
        })

        client = httpx.Client(
            headers=auth_headers,
            timeout=self.timeout,
            follow_redirects=True,
            verify=False,
        )

        token = None
        try:
            # 1. Login if user credentials provided
            if self.username and self.password:
                token = self._login(client)
                if token:
                    client.headers["Authorization"] = f"Bearer {token}"
                    logger.info(f"[{self.site_id}] Authenticated as {self.username}")
                else:
                    logger.warning(f"[{self.site_id}] Authentication failed for {self.username}")

            # 2. Fetch Published and Active tenders from live e-GP Gateway API
            api_endpoint = f"{self.api_gateway}/cms-v2/api/sourcing/get-grouped-sourcing"
            
            # Target current month and upcoming tenders
            now = datetime.utcnow()
            current_month_start = f"{now.year}-{now.month:02d}-01"
            page_size = 50
            max_pages = 25  # up to 1,250 active tenders

            # Pass 1: Active & upcoming tenders (submissionDeadline >= start of current month)
            # Ordered by newest invitation date first
            for page in range(max_pages):
                skip = page * page_size
                params = {
                    "skip": skip,
                    "top": page_size,
                    "type": "PublishedTender",
                    "orderBy[0].field": "invitationDate",
                    "orderBy[0].direction": "desc",
                    "filter[0][0].field": "submissionDeadline",
                    "filter[0][0].operator": ">=",
                    "filter[0][0].value": current_month_start,
                }
                try:
                    r = client.get(api_endpoint, params=params)
                    if r.status_code != 200:
                        logger.warning(f"[{self.site_id}] e-GP active query page {page} status {r.status_code}")
                        break
                    
                    data = r.json()
                    items = data.get("items", [])
                    if not items:
                        break

                    for pkg in items:
                        bids = self._parse_package(pkg, min_date_str=current_month_start)
                        results.extend(bids)

                except Exception as ex:
                    logger.warning(f"[{self.site_id}] Error fetching active page {page}: {ex}")
                    break

        finally:
            client.close()

        # Deduplicate
        seen = set()
        unique = []
        for b in results:
            key = (b.bid_number or b.title) + str(b.company)
            if key not in seen:
                seen.add(key)
                unique.append(b)

        logger.info(f"[{self.site_id}] Crawled {len(unique)} garment bids from e-GP.")
        return unique

    def _login(self, client: httpx.Client) -> Optional[str]:
        """Authenticate with e-GP IdentityServer4 endpoint."""
        try:
            data = {
                "grant_type": "password",
                "client_id": "skoruba_identity_admin",
                "client_secret": "skoruba_admin_client_secret",
                "username": self.username,
                "password": self.password,
                "scope": "openid profile",
            }
            r = client.post(self.auth_url, data=data, timeout=12)
            if r.status_code == 200:
                res = r.json()
                return res.get("access_token")
            else:
                logger.warning(f"[{self.site_id}] Login HTTP {r.status_code}: {r.text[:200]}")
                return None
        except Exception as e:
            logger.warning(f"[{self.site_id}] Login exception: {e}")
            return None

    def _parse_package(self, pkg: dict, min_date_str: Optional[str] = None) -> List[BidData]:
        """Extract garment-related BidData from an e-GP sourcing package."""
        bids = []
        pkg_id = pkg.get("packageId", "")
        pkg_inv_date = self._parse_iso_date(pkg.get("invitationDate"))
        
        results = pkg.get("result", [])
        for lot in results:
            lot_name = lot.get("lotName", "") or ""
            lot_desc = lot.get("lotDescription", "") or ""
            proc_cat = lot.get("procurementCategory", "") or ""

            # Skip explicitly non-garment lots
            lot_name_lower = lot_name.lower()
            if any(ex in lot_name_lower for ex in EXCLUDED_LOT_KEYWORDS):
                continue
            
            pkg_info = lot.get("packageInformation") or {}
            pkg_name = pkg_info.get("name", "") or ""
            pkg_desc = pkg_info.get("description", "") or ""

            # Filter garment related: check lot-level text first to avoid multi-lot spillover
            lot_text = f"{lot_name} {lot_desc}"
            if is_garment_related(lot_text):
                full_text = f"{lot_text} {pkg_name} {pkg_desc} {proc_cat}"
            elif is_garment_related(f"{pkg_name} {pkg_desc}") and (lot_name.strip().lower().startswith("lot") or len(lot_name.strip()) <= 10):
                full_text = f"{lot_text} {pkg_name} {pkg_desc} {proc_cat}"
            else:
                continue

            bid = BidData()
            bid.source_site = self.site_name
            bid.source_site_id = self.site_id
            bid.category = detect_category(full_text)
            bid.title = (lot_name or pkg_name or full_text[:120]).strip()
            bid.raw_text = full_text[:3000]

            # Reference No
            ref_no = (
                lot.get("procurementReferenceNo") or
                lot.get("lotReferenceNo") or
                pkg_info.get("reference_no") or ""
            )
            bid.bid_number = ref_no

            # Company / Procuring Entity
            entity = (
                lot.get("procuringEntity") or
                pkg_info.get("procuring_entity") or ""
            )
            if not entity:
                branch = pkg_info.get("branch", {}).get("name", {})
                if isinstance(branch, dict):
                    entity = branch.get("en") or branch.get("am") or ""
                elif isinstance(branch, str):
                    entity = branch
            bid.company = entity

            # Posted date
            inv_date = (
                lot.get("invitationDate") or
                pkg_info.get("invitation_date") or
                pkg.get("invitationDate")
            )
            bid.posted_date = self._parse_iso_date(inv_date) or pkg_inv_date

            # Deadline
            deadline_str = (
                lot.get("submissionDeadline") or
                pkg_info.get("submission_deadline")
            )
            bid.deadline = self._parse_iso_date(deadline_str)

            # Enforce current & upcoming month cutoff
            if min_date_str:
                try:
                    cutoff = datetime.fromisoformat(min_date_str)
                    if bid.deadline and bid.deadline < cutoff:
                        continue
                    if not bid.deadline and bid.posted_date and bid.posted_date < cutoff:
                        continue
                except Exception:
                    pass

            # Bid Security Amount
            sec_amt = pkg_info.get("bid_security_amount")
            if sec_amt is not None:
                try:
                    bid.bid_security_amount = float(sec_amt)
                except (ValueError, TypeError):
                    bid.bid_security_amount = extract_amount(str(sec_amt))

            # Bid Security Type
            forms = pkg_info.get("bid_security_form") or []
            if isinstance(forms, list) and forms:
                bid.bid_security_type = ", ".join(str(f) for f in forms if f)
            if not bid.bid_security_type:
                bid.bid_security_type = extract_security_type(full_text)
            if not bid.bid_security_type:
                bid.bid_security_type = "CPO / Bank Guarantee"

            # Address & Contact
            addr = pkg_info.get("address") or {}
            town = addr.get("town") or ""
            street = addr.get("street") or ""
            country = addr.get("country") or "Ethiopia"
            bid.location = f"{town}, {street}, {country}".strip(", ")

            tel = addr.get("telephone") or {}
            if isinstance(tel, dict):
                code = tel.get("code") or "+251"
                num = tel.get("number") or ""
                bid.contact_phone = f"{code} {num}".strip() if num else ""
            elif isinstance(tel, str):
                bid.contact_phone = tel

            bid.contact_email = addr.get("email") or ""

            # Direct URL to the bid on production e-GP Angular portal:
            # Route: /egp/bids/all/{sourceApplication}/{id}/{open|closed}
            source_app = (lot.get("sourceApplication") or "Purchasing").strip()
            source_app_slug = {
                "Tendering": "tendering",
                "Purchasing": "purchasing",
                "Auctioning": "auctioning",
                "Prequalification": "prequalification",
            }.get(source_app, source_app.lower())

            if source_app_slug == "purchasing":
                target_id = lot.get("sourceId") or lot.get("lotInPackageId") or lot.get("lotId") or pkg_id
            else:
                target_id = lot.get("lotInPackageId") or lot.get("lotId") or lot.get("sourceId") or pkg_id

            is_submittable = lot.get("isSubmittable")
            if is_submittable is None:
                is_open = (bid.deadline is None or bid.deadline > datetime.utcnow())
            else:
                is_open = bool(is_submittable)
            status_slug = "open" if is_open else "closed"

            if target_id and source_app_slug:
                bid.source_url = f"https://production.egp.gov.et/egp/bids/all/{source_app_slug}/{target_id}/{status_slug}"
            else:
                bid.source_url = "https://production.egp.gov.et/egp/bids/all"

            bids.append(bid)

        return bids

    def _parse_iso_date(self, s: Optional[str]) -> Optional[datetime]:
        if not s:
            return None
        # Clean ISO date like '2026-10-22T05:30:00Z' or '2022-11-17T10:00:00Z'
        try:
            cleaned = s.replace("Z", "+00:00")
            if "." in cleaned and "+" in cleaned:
                # remove fractional seconds
                base, rest = cleaned.split(".", 1)
                tz = rest[rest.find("+"):]
                cleaned = f"{base}{tz}"
            return datetime.fromisoformat(cleaned).replace(tzinfo=None)
        except Exception:
            return parse_date(str(s)[:10])
