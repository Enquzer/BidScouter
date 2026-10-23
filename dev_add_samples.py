"""
BidScouter - Seed realistic sample bids with genuine portal links and varied tracking statuses.
Run: python dev_add_samples.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.database import init_db, SessionLocal, Bid
from backend.linkchecker import check_all_links
from datetime import datetime, timedelta
import uuid

SAMPLES = [
    {
        "title": "Supply of 15,000 Pieces Primary School Uniforms (Shirts, Skirts, Trousers)",
        "company": "Addis Ababa City Administration Education Bureau",
        "category": "School Uniform",
        "bid_number": "AAB/EDU/UNIF/2026/014",
        "posted_date": datetime.utcnow() - timedelta(days=2),
        "deadline": datetime.utcnow() + timedelta(hours=22),  # Urgent (<30h)
        "registration_fee": 500.0,
        "bid_security_type": "CPO",
        "bid_security_amount": 150000.0,
        "location": "Addis Ababa, Education Bureau, Kazanchis near UNECA",
        "contact_name": "Ato Kebede Alemu (Procurement Director)",
        "contact_phone": "+251 911 234 567",
        "contact_email": "procurement@aacedu.gov.et",
        "source_url": "https://www.ppa.gov.et",
        "source_site": "Ethiopian Public Procurement Agency (PPA)",
        "source_site_id": "ppaa",
        "is_new": True,
        "application_status": "cpo_delivered",
        "application_notes": "CPO issued from CBE Kazanchis branch. Document purchased for 500 ETB. Preparing final sealed envelope.",
        "doc_purchased_date": datetime.utcnow() - timedelta(days=2),
        "cpo_delivered_date": datetime.utcnow() - timedelta(days=1),
        "link_status": "valid",
    },
    {
        "title": "Procurement of Doctor Scrubs, Nurse Uniforms and Surgeon Gowns",
        "company": "Tikur Anbessa (Black Lion) Specialized Hospital",
        "category": "Medical Uniform",
        "bid_number": "TASH/NCB/MED/09/2026",
        "posted_date": datetime.utcnow() - timedelta(days=4),
        "deadline": datetime.utcnow() + timedelta(days=6),
        "registration_fee": 800.0,
        "bid_security_type": "CPO",
        "bid_security_amount": 200000.0,
        "location": "Tikur Anbessa Specialized Hospital, Procurement Directorate, Addis Ababa",
        "contact_name": "W/ro Selamawit Tadesse",
        "contact_phone": "+251 115 517 100",
        "contact_email": "tenders@tash.edu.et",
        "source_url": "https://tender.2merkato.com",
        "source_site": "2Merkato Tenders",
        "source_site_id": "mercato",
        "is_new": True,
        "application_status": "sample_delivered",
        "application_notes": "Delivered 2 fabric lab samples to the technical evaluation committee on Tuesday.",
        "doc_purchased_date": datetime.utcnow() - timedelta(days=4),
        "cpo_delivered_date": datetime.utcnow() - timedelta(days=3),
        "applied_date": datetime.utcnow() - timedelta(days=2),
        "sample_delivered_date": datetime.utcnow() - timedelta(days=1),
        "link_status": "valid",
    },
    {
        "title": "Tender for Security Forces Winter Jackets, Heavy Combat Trousers & Raincoats",
        "company": "Federal Police Commission Procurement & Logistics Directorate",
        "category": "Military/Security Uniform",
        "bid_number": "FPC/LOG/041/2026",
        "posted_date": datetime.utcnow() - timedelta(days=10),
        "deadline": datetime.utcnow() - timedelta(days=2),  # Concluded / Failed
        "registration_fee": 1500.0,
        "bid_security_type": "CPO",
        "bid_security_amount": 350000.0,
        "location": "Mexico Square, Federal Police HQ, Addis Ababa",
        "contact_name": "Major Desta Girma",
        "contact_phone": "+251 115 512 888",
        "contact_email": "logistics@fedpolice.gov.et",
        "source_url": "https://www.ethiopianreporter.com",
        "source_site": "Ethiopian Reporter",
        "source_site_id": "ethiopianreporter",
        "is_new": False,
        "application_status": "failed",
        "application_notes": "Competitor won on delivery timeline. Need to collect 350,000 ETB CPO back from procurement office!",
        "doc_purchased_date": datetime.utcnow() - timedelta(days=9),
        "cpo_delivered_date": datetime.utcnow() - timedelta(days=8),
        "applied_date": datetime.utcnow() - timedelta(days=7),
        "result_date": datetime.utcnow() - timedelta(days=2),
        "cpo_refund_collected": False,
        "link_status": "valid",
    },
    {
        "title": "Supply of Branded Polo Shirts & Sportswear T-Shirts for Annual Sports Festival",
        "company": "Ethiopian Airlines Group - Commercial & HR",
        "category": "T-Shirt / Polo",
        "bid_number": "ET/HR/SPORTS/2026/08",
        "posted_date": datetime.utcnow() - timedelta(days=15),
        "deadline": datetime.utcnow() - timedelta(days=5),
        "registration_fee": 300.0,
        "bid_security_type": "Bank Guarantee",
        "bid_security_amount": 100000.0,
        "location": "Bole International Airport, Ethiopian Airlines Head Office, Addis Ababa",
        "contact_name": "Ato Yonas Bekele",
        "contact_phone": "+251 116 179 900",
        "contact_email": "strategicprocurement@ethiopianairlines.com",
        "source_url": "https://www.ungm.org/Public/Notice",
        "source_site": "UN Global Marketplace",
        "source_site_id": "ungm",
        "is_new": False,
        "application_status": "secured",
        "application_notes": "Won the award for 8,500 polo shirts! Contract signed, bulk production starting next week.",
        "doc_purchased_date": datetime.utcnow() - timedelta(days=14),
        "cpo_delivered_date": datetime.utcnow() - timedelta(days=13),
        "applied_date": datetime.utcnow() - timedelta(days=10),
        "sample_delivered_date": datetime.utcnow() - timedelta(days=8),
        "result_date": datetime.utcnow() - timedelta(days=5),
        "cpo_refund_collected": True,
        "link_status": "valid",
    },
    {
        "title": "Procurement of High-Visibility Safety Overalls & Flame-Retardant Workwear",
        "company": "Ethiopian Electric Utility (EEU)",
        "category": "Workwear/PPE",
        "bid_number": "EEU/WB/PPE/01/2026",
        "posted_date": datetime.utcnow() - timedelta(days=1),
        "deadline": datetime.utcnow() + timedelta(days=18),
        "registration_fee": 1000.0,
        "bid_security_type": "Bank Guarantee",
        "bid_security_amount": 400000.0,
        "location": "Degafi Building, Head Office, Addis Ababa",
        "contact_name": "EEU Procurement Department",
        "contact_phone": "+251 111 560 041",
        "contact_email": "tenders@eeu.gov.et",
        "source_url": "https://www.ppa.gov.et",
        "source_site": "Ethiopian Public Procurement Agency (PPA)",
        "source_site_id": "ppaa",
        "is_new": True,
        "application_status": "doc_purchased",
        "application_notes": "Purchased bid specification document. Technical team currently reviewing fabric GSM specs.",
        "doc_purchased_date": datetime.utcnow() - timedelta(hours=12),
        "link_status": "valid",
    },
    {
        "title": "Supply of Blankets, Emergency Tents and Heavy Duty Textile Canvas",
        "company": "Ethiopian Disaster Risk Management Commission (EDRMC)",
        "category": "Fabric / Textile",
        "bid_number": "EDRMC/RELIEF/TEX/003/2026",
        "posted_date": datetime.utcnow() - timedelta(days=3),
        "deadline": datetime.utcnow() + timedelta(days=12),
        "registration_fee": 500.0,
        "bid_security_type": "CPO",
        "bid_security_amount": 250000.0,
        "location": "Nifas Silk Lafto Sub-city, Near Gotera, Addis Ababa",
        "contact_name": "Relief Logistics Desk",
        "contact_phone": "+251 115 528 111",
        "contact_email": "info@edrmc.gov.et",
        "source_url": "https://eprocurement.gov.et/expired-tender-archive-404-broken",
        "source_site": "Ethiopian e-Procurement Portal",
        "source_site_id": "eprocurement",
        "is_new": True,
        "application_status": "not_applied",
        "application_notes": "Noticed link appears broken/moved. Must contact Gotera office directly for paper copy.",
        "link_status": "dead",
    },
]

def seed():
    init_db()
    db = SessionLocal()
    try:
        # Clear existing old sample data so clean new schema and real links are used
        db.query(Bid).delete()
        db.commit()

        for s in SAMPLES:
            bid = Bid(id=str(uuid.uuid4()), **s)
            db.add(bid)
        db.commit()
        print(f"Successfully seeded {len(SAMPLES)} fresh bids with application tracking & link status.")
    finally:
        db.close()

    # Run link health check
    print("Running link health check on seeded items...")
    check_all_links(limit=20)
    print("Link check completed.")

if __name__ == "__main__":
    seed()
