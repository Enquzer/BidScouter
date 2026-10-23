"""
BidScouter - APScheduler setup
Runs crawlers and reminders on configured intervals.
"""
import logging
import json
import os
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger("bidscouter.scheduler")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTINGS_PATH = os.path.join(BASE_DIR, "config", "settings.json")

_scheduler: BackgroundScheduler = None


def _load_interval() -> int:
    try:
        with open(SETTINGS_PATH) as f:
            s = json.load(f)
        return int(s.get("crawler", {}).get("interval_hours", 6))
    except Exception:
        return 6


def start_scheduler():
    global _scheduler
    from .crawler.engine import run_all_crawlers, check_reminders
    from .notifier import notify_new_bids, notify_deadline_reminder, notify_cpo_refund
    from .linkchecker import check_all_links
    from .database import SessionLocal, Bid, CPO_REFUND_STATUSES
    from sqlalchemy import or_

    def crawl_job():
        logger.info("Scheduler: starting crawl job")
        run_all_crawlers(notify_callback=notify_new_bids)
        # Also check links after crawl
        check_all_links(limit=40)

    def reminder_job():
        logger.info("Scheduler: checking reminders")
        check_reminders(notify_callback=notify_deadline_reminder)
        _check_cpo_refunds(notify_cpo_refund)

    def link_check_job():
        logger.info("Scheduler: checking links")
        check_all_links(limit=50)

    def _check_cpo_refunds(callback):
        db = SessionLocal()
        try:
            pending = db.query(Bid).filter(
                Bid.application_status.in_(list(CPO_REFUND_STATUSES)),
                Bid.cpo_refund_collected == False,
                Bid.cpo_refund_reminder_sent == False,
                or_(Bid.bid_security_type.ilike("%cpo%"), Bid.bid_security_type.ilike("%bond%")),
            ).all()
            for bid in pending:
                callback(bid)
                bid.cpo_refund_reminder_sent = True
            if pending:
                db.commit()
        finally:
            db.close()

    hours = _load_interval()
    _scheduler = BackgroundScheduler(timezone="Africa/Addis_Ababa")
    _scheduler.add_job(crawl_job, IntervalTrigger(hours=hours), id="crawl", replace_existing=True)
    _scheduler.add_job(reminder_job, IntervalTrigger(minutes=30), id="reminders", replace_existing=True)
    _scheduler.add_job(link_check_job, IntervalTrigger(hours=2), id="links", replace_existing=True)
    _scheduler.start()
    logger.info(f"Scheduler started. Crawl every {hours}h, reminders every 30m, links every 2h.")
    return _scheduler


def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown()
        logger.info("Scheduler stopped.")


def update_interval(hours: int):
    global _scheduler
    if _scheduler:
        _scheduler.reschedule_job("crawl", trigger=IntervalTrigger(hours=hours))
        logger.info(f"Crawl interval updated to {hours}h")
