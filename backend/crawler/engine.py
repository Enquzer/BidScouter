"""
BidScouter - Crawler Engine
Orchestrates all site crawlers, saves to DB, triggers notifications.
"""
import logging
import json
import os
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session
from ..database import SessionLocal, Bid, CrawlLog
from .sites import SITE_CRAWLERS
from .sites.base import BidData

logger = logging.getLogger("bidscouter.engine")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SETTINGS_PATH = os.path.join(BASE_DIR, "config", "settings.json")


def load_settings() -> dict:
    with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def run_all_crawlers(notify_callback=None) -> dict:
    """Run all enabled site crawlers. Returns summary dict."""
    settings = load_settings()
    crawler_cfg = settings.get("crawler", {})
    credentials_list = settings.get("credentials", {}).get("sites", [])
    creds_map = {c["id"]: c for c in credentials_list}

    total_new = 0
    summary = {"sites": [], "total_new": 0, "errors": []}

    db: Session = SessionLocal()
    try:
        # 0. Clean out legacy/outdated bids from past months/years
        now = datetime.utcnow()
        current_month_start = datetime(now.year, now.month, 1)
        purged = db.query(Bid).filter(
            Bid.deadline != None,
            Bid.deadline < current_month_start
        ).delete(synchronize_session=False)
        if purged:
            db.commit()
            logger.info(f"Purged {purged} outdated bids from prior periods.")

        for site_id, CrawlerClass in SITE_CRAWLERS.items():
            cred = creds_map.get(site_id, {})
            if not cred.get("enabled", True):
                continue

            log = CrawlLog(
                site_id=site_id,
                site_name=CrawlerClass.site_name,
                started_at=datetime.utcnow(),
                status="running",
            )
            db.add(log)
            db.commit()
            db.refresh(log)

            try:
                crawler = CrawlerClass(cred, crawler_cfg)
                bids: List[BidData] = crawler.crawl()
                new_count = _save_bids(db, bids)
                total_new += new_count

                log.finished_at = datetime.utcnow()
                log.status = "success"
                log.bids_found = len(bids)
                log.new_bids = new_count
                db.commit()

                summary["sites"].append({
                    "site": CrawlerClass.site_name,
                    "found": len(bids),
                    "new": new_count,
                })
                logger.info(f"[{site_id}] Found {len(bids)} bids, {new_count} new.")

                if new_count > 0 and notify_callback:
                    notify_callback(new_count, CrawlerClass.site_name)

            except Exception as e:
                log.finished_at = datetime.utcnow()
                log.status = "error"
                log.error_message = str(e)
                db.commit()
                logger.error(f"[{site_id}] Crawler error: {e}", exc_info=True)
                summary["errors"].append({"site": site_id, "error": str(e)})

        summary["total_new"] = total_new
    finally:
        db.close()

    return summary


def _save_bids(db: Session, bids: List[BidData]) -> int:
    """Save bids to DB, return count of newly inserted."""
    new_count = 0
    for bid_data in bids:
        # Check for duplicate by bid_number, source_url, or (title + company)
        existing = None
        if bid_data.bid_number:
            existing = db.query(Bid).filter(Bid.bid_number == bid_data.bid_number).first()
        if not existing and bid_data.source_url:
            existing = db.query(Bid).filter(Bid.source_url == bid_data.source_url).first()
        if not existing and bid_data.title:
            existing = db.query(Bid).filter(
                Bid.title == bid_data.title,
                Bid.company == bid_data.company,
            ).first()

        if existing:
            changed = False
            # Update deadline if changed
            if bid_data.deadline and existing.deadline != bid_data.deadline:
                existing.deadline = bid_data.deadline
                changed = True
            # Update source_url to latest Angular route
            if bid_data.source_url and existing.source_url != bid_data.source_url:
                existing.source_url = bid_data.source_url
                existing.link_status = "ok"
                changed = True
            if changed:
                db.commit()
            continue

        # Insert new bid
        new_bid = Bid(**bid_data.to_dict(), is_new=True, reminder_sent=False, link_status="valid")
        db.add(new_bid)
        new_count += 1

    if new_count > 0:
        db.commit()

    return new_count


def check_reminders(notify_callback=None):
    """Check for bids whose deadline is within 30 hours and send reminder."""
    from datetime import timedelta
    db: Session = SessionLocal()
    try:
        settings = load_settings()
        hours = settings.get("notifications", {}).get("reminder_hours_before", 30)
        now = datetime.utcnow()
        threshold = now + timedelta(hours=hours)

        due_bids = db.query(Bid).filter(
            Bid.deadline != None,
            Bid.deadline <= threshold,
            Bid.deadline >= now,
            Bid.reminder_sent == False,
        ).all()

        for bid in due_bids:
            if notify_callback:
                hours_left = (bid.deadline - now).total_seconds() / 3600
                notify_callback(bid, hours_left)
            bid.reminder_sent = True

        if due_bids:
            db.commit()
    finally:
        db.close()
