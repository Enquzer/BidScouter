"""
BidScouter - Link Health Checker
Validates source_url for each bid to detect dead / broken links.
"""
import logging
import httpx
from datetime import datetime
from sqlalchemy.orm import Session
from .database import SessionLocal, Bid

logger = logging.getLogger("bidscouter.linkchecker")

DEAD_CODES = {404, 410, 403, 500, 502, 503}
VALID_CODES = {200, 201, 301, 302, 303, 307, 308}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124",
    "Accept": "text/html,application/xhtml+xml,*/*",
}


def check_all_links(limit: int = 50):
    """
    Check up to `limit` bids whose links haven't been verified recently.
    Run as a background task; safe to call repeatedly.
    """
    db: Session = SessionLocal()
    try:
        from sqlalchemy import or_
        # Prioritise: unknown first, then dead (re-verify), then oldest checked
        bids = (
            db.query(Bid)
            .filter(Bid.source_url != "", Bid.source_url != None)
            .filter(or_(Bid.link_status == "unknown", Bid.link_status == None))
            .limit(limit)
            .all()
        )
        if not bids:
            # Re-check dead links too
            bids = (
                db.query(Bid)
                .filter(Bid.source_url != "", Bid.source_url != None, Bid.link_status == "dead")
                .limit(limit // 2)
                .all()
            )

        logger.info(f"[LinkChecker] Checking {len(bids)} links…")
        with httpx.Client(headers=HEADERS, timeout=10, follow_redirects=True, verify=False) as client:
            for bid in bids:
                status, code = _check_url(client, bid.source_url)
                bid.link_status = status
                bid.link_http_code = code
                bid.link_checked_at = datetime.utcnow()

        db.commit()
        logger.info("[LinkChecker] Done.")
    except Exception as e:
        logger.error(f"[LinkChecker] Error: {e}")
    finally:
        db.close()


def _check_url(client: httpx.Client, url: str):
    """Returns (status_label, http_code)."""
    try:
        r = client.head(url, timeout=8)
        code = r.status_code
        if code in DEAD_CODES:
            # Try GET as fallback for HEAD-refusing servers
            try:
                r2 = client.get(url, timeout=10)
                code = r2.status_code
            except Exception:
                pass
        if code == 404 or code == 410:
            return "dead", code
        if code >= 400:
            return "dead", code
        if code in (301, 302, 303, 307, 308):
            return "redirect", code
        if 200 <= code < 300:
            return "valid", code
        return "unknown", code
    except httpx.ConnectError:
        return "dead", 0
    except httpx.TimeoutException:
        return "timeout", 0
    except Exception as e:
        logger.debug(f"Link check error for {url}: {e}")
        return "unknown", 0
