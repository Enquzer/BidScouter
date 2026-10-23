"""
BidScouter - Database models and initialization
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, String, Float, Boolean,
    DateTime, Text, Integer
)
from sqlalchemy.orm import declarative_base, sessionmaker
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "bids.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ── Application status pipeline ─────────────────────────────────────────────
# Ordered statuses a bid can go through:
APPLICATION_STATUSES = [
    "not_applied",         # Default — haven't done anything yet
    "doc_purchased",       # Bid document purchased
    "cpo_delivered",       # CPO delivered to bidder/procurer
    "applied",             # Bid formally submitted
    "sample_delivered",    # Sample/prototype delivered
    "secured",             # Won the bid 🎉
    "failed",              # Lost the bid
    "cancelled",           # Bid was cancelled by procurer
]

# Statuses where a CPO refund reminder should fire
CPO_REFUND_STATUSES = {"failed", "cancelled"}


class Bid(Base):
    __tablename__ = "bids"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    company = Column(String, default="")
    category = Column(String, default="")
    bid_number = Column(String, default="")
    posted_date = Column(DateTime, nullable=True)
    deadline = Column(DateTime, nullable=True)
    registration_fee = Column(Float, nullable=True)
    registration_fee_currency = Column(String, default="ETB")
    bid_security_type = Column(String, default="")   # CPO, Bank Guarantee, etc.
    bid_security_amount = Column(Float, nullable=True)
    bid_security_currency = Column(String, default="ETB")
    location = Column(String, default="")            # Where to apply / purchase doc
    contact_name = Column(String, default="")
    contact_phone = Column(String, default="")
    contact_email = Column(String, default="")
    source_url = Column(String, default="")          # Direct link to posting
    source_site = Column(String, default="")         # Site name
    source_site_id = Column(String, default="")
    is_new = Column(Boolean, default=True)
    reminder_sent = Column(Boolean, default=False)
    raw_text = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ── Application tracking fields ──────────────────────────────────────────
    # Status pipeline: not_applied → doc_purchased → cpo_delivered → applied
    #                  → sample_delivered → secured | failed | cancelled
    application_status = Column(String, default="not_applied")
    application_notes = Column(Text, default="")         # Free-text notes per bid
    applied_date = Column(DateTime, nullable=True)       # When bid was submitted
    doc_purchased_date = Column(DateTime, nullable=True)
    cpo_delivered_date = Column(DateTime, nullable=True)
    sample_delivered_date = Column(DateTime, nullable=True)
    result_date = Column(DateTime, nullable=True)        # When result was known
    cpo_refund_collected = Column(Boolean, default=False) # CPO returned after fail/cancel
    cpo_refund_reminder_sent = Column(Boolean, default=False)
    prepared_documents = Column(Text, default="[]")      # JSON array of prepared doc IDs

    # ── Link health ──────────────────────────────────────────────────────────
    link_status = Column(String, default="unknown")      # unknown, valid, dead, redirect
    link_checked_at = Column(DateTime, nullable=True)
    link_http_code = Column(Integer, nullable=True)      # Last HTTP status code

    @property
    def required_docs_count(self) -> int:
        return 11

    @property
    def prepared_docs_count(self) -> int:
        import json
        try:
            return len(json.loads(self.prepared_documents or "[]"))
        except Exception:
            return 0

    @property
    def docs_summary(self) -> str:
        sec = f"{self.bid_security_currency} {self.bid_security_amount:,.2f}" if (self.bid_security_amount and self.bid_security_amount > 0) else "Check Doc"
        return f"CPO: {sec} • Sample • 5 Legal Docs"


class CrawlLog(Base):
    __tablename__ = "crawl_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    site_id = Column(String)
    site_name = Column(String)
    started_at = Column(DateTime)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String, default="running")   # running, success, error
    bids_found = Column(Integer, default=0)
    new_bids = Column(Integer, default=0)
    error_message = Column(Text, default="")


class AppSettings(Base):
    __tablename__ = "app_settings"

    key = Column(String, primary_key=True)
    value = Column(Text)


def init_db():
    Base.metadata.create_all(bind=engine)
    _migrate_existing()


def _migrate_existing():
    """Add new columns to existing DB without losing data."""
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    existing = {row[1] for row in cur.execute("PRAGMA table_info(bids)")}
    new_cols = {
        "application_status": "TEXT DEFAULT 'not_applied'",
        "application_notes": "TEXT DEFAULT ''",
        "applied_date": "DATETIME",
        "doc_purchased_date": "DATETIME",
        "cpo_delivered_date": "DATETIME",
        "sample_delivered_date": "DATETIME",
        "result_date": "DATETIME",
        "cpo_refund_collected": "INTEGER DEFAULT 0",
        "cpo_refund_reminder_sent": "INTEGER DEFAULT 0",
        "link_status": "TEXT DEFAULT 'unknown'",
        "link_checked_at": "DATETIME",
        "link_http_code": "INTEGER",
        "prepared_documents": "TEXT DEFAULT '[]'",
    }
    for col, coldef in new_cols.items():
        if col not in existing:
            cur.execute(f"ALTER TABLE bids ADD COLUMN {col} {coldef}")
    conn.commit()
    conn.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
