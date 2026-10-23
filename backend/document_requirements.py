"""
BidScouter - Bid Document Requirements Engine
Generates tailored, bid-specific document checklists for Ethiopian garment/uniform tenders.
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
import json


def get_required_documents_for_bid(bid, prepared_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Generate the itemized checklist of required documents specifically tailored
    for an individual bid request.
    """
    if prepared_ids is None:
        try:
            prepared_ids = json.loads(getattr(bid, "prepared_documents", "[]") or "[]")
        except Exception:
            prepared_ids = []

    prep_set = set(prepared_ids)
    docs = []

    company = getattr(bid, "company", "") or "Procuring Entity"
    bid_num = getattr(bid, "bid_number", "") or "N/A"
    deadline = getattr(bid, "deadline", None)
    deadline_str = deadline.strftime("%b %d, %Y at %I:%M %p") if deadline else "Submission Deadline"
    sec_amount = getattr(bid, "bid_security_amount", None)
    sec_curr = getattr(bid, "bid_security_currency", "ETB") or "ETB"
    reg_fee = getattr(bid, "registration_fee", None)
    reg_curr = getattr(bid, "registration_fee_currency", "ETB") or "ETB"
    location = getattr(bid, "location", "") or company
    category = getattr(bid, "category", "") or "Garments & Uniforms"

    # 1. LEGAL & STATUTORY COMPLIANCE
    docs.append({
        "id": "trade_license",
        "title": "Renewed Trade / Business License",
        "title_am": "የታደሰ የንግድ ስራ ፈቃድ",
        "category": "legal_statutory",
        "category_label": "Legal & Statutory Compliance",
        "mandatory": True,
        "description": "Valid commercial business license renewed for fiscal year 2017 E.C. (2024–2026 G.C.) covering garment/apparel manufacturing, sewing, or textile supply.",
        "tips": "Verify that your license category includes garment/uniform manufacturing or wholesale supply.",
        "is_prepared": "trade_license" in prep_set,
    })

    docs.append({
        "id": "tax_clearance",
        "title": "Tax Clearance Certificate",
        "title_am": "የግብር ክሊራንስ ምስክር ወረቀት",
        "category": "legal_statutory",
        "category_label": "Legal & Statutory Compliance",
        "mandatory": True,
        "description": f"Valid Tax Clearance Certificate issued by the Ministry of Revenues (MoR) confirming zero outstanding tax liabilities, valid at bid closing ({deadline_str}).",
        "tips": "Must be valid on the submission date. Check expiration date from MoR portal before submission.",
        "is_prepared": "tax_clearance" in prep_set,
    })

    docs.append({
        "id": "vat_tin_certificate",
        "title": "VAT & TIN Registration Certificates",
        "title_am": "የተጨማሪ እሴት ታክስ (VAT) እና የግብር ከፋይ መለያ (TIN) ሰነዶች",
        "category": "legal_statutory",
        "category_label": "Legal & Statutory Compliance",
        "mandatory": True,
        "description": "Value Added Tax (VAT) Registration Certificate and Taxpayer Identification Number (TIN) certificate issued by the Ethiopian Revenues Authority.",
        "tips": "Ensure company registered name matches exactly across VAT, TIN, and bank accounts.",
        "is_prepared": "vat_tin_certificate" in prep_set,
    })

    docs.append({
        "id": "ppa_registration",
        "title": "Public Procurement Agency (PPAA) Supplier Registration",
        "title_am": "በመንግስት ግዥ እና ንብረት ባለስልጣን (PPAA) የአቅራቢዎች ዝርዝር ምዝገባ",
        "category": "legal_statutory",
        "category_label": "Legal & Statutory Compliance",
        "mandatory": True,
        "description": "Certificate of registration on the Federal Public Procurement and Property Administration Agency (PPAA) or regional electronic supplier list.",
        "tips": "Ensure your profile on production.egp.gov.et / ppa.gov.et is active with renewed license details.",
        "is_prepared": "ppa_registration" in prep_set,
    })

    # 2. FINANCIAL SECURITIES & BID FEES
    if sec_amount and sec_amount > 0:
        cpo_desc = (
            f"Certified Payment Order (CPO) or unconditional bank guarantee for exactly "
            f"{sec_curr} {sec_amount:,.2f} issued in favor of '{company}'. "
            f"Must be valid for a minimum of 90–120 days beyond the closing date ({deadline_str})."
        )
    else:
        cpo_desc = (
            f"Bid Security (CPO / Unconditional Bank Guarantee) as prescribed in the tender schedule, "
            f"payable to '{company}'. (If exempted under threshold, verify in quotation document)."
        )

    docs.append({
        "id": "bid_security_cpo",
        "title": "Bid Security / CPO Guarantee",
        "title_am": "የጨረታ ማስከበሪያ (CPO ወይም የባንክ ዋስትና)",
        "category": "financial_security",
        "category_label": "Financial Securities",
        "mandatory": True if (sec_amount and sec_amount > 0) else False,
        "amount": sec_amount,
        "currency": sec_curr,
        "description": cpo_desc,
        "tips": f"Double check bank spelling of '{company}'. CPO refund must be tracked if bid is not awarded.",
        "is_prepared": "bid_security_cpo" in prep_set,
    })

    if reg_fee and reg_fee > 0:
        fee_desc = f"Official bank deposit slip / receipt confirming payment of non-refundable document fee of {reg_curr} {reg_fee:,.2f}."
    else:
        fee_desc = "e-GP portal free registration confirmation or official document purchase receipt if required by the procuring entity."

    docs.append({
        "id": "doc_fee_receipt",
        "title": "Bid Document Purchase Receipt / Portal Confirmation",
        "title_am": "የጨረታ ሰነድ መግዣ ደረሰኝ ወይም የፖርታል ማረጋገጫ",
        "category": "financial_security",
        "category_label": "Financial Securities",
        "mandatory": True if (reg_fee and reg_fee > 0) else False,
        "amount": reg_fee,
        "currency": reg_curr,
        "description": fee_desc,
        "tips": "Keep the physical bank deposit receipt or digital confirmation attached to the proposal.",
        "is_prepared": "doc_fee_receipt" in prep_set,
    })

    # 3. TECHNICAL SPECIFICATIONS & SAMPLES
    docs.append({
        "id": "physical_sample",
        "title": "Physical Sample Submission",
        "title_am": "የናሙና ማቅረቢያ (Sample Submission)",
        "category": "technical_sample",
        "category_label": "Technical Specifications & Samples",
        "mandatory": True,
        "description": (
            f"1 finished physical sample or fabric prototype matching the specifications of the requested {category.lower()}, "
            f"labeled with bidder name and Bid Ref No. '{bid_num}', delivered to {company} at {location} on or before {deadline_str}."
        ),
        "tips": "Obtain an official signed sample receipt acknowledgment from the procuring entity's procurement committee.",
        "is_prepared": "physical_sample" in prep_set,
    })

    docs.append({
        "id": "tech_compliance_matrix",
        "title": "Technical Specification & Compliance Sheet",
        "title_am": "የቴክኒክ ዝርዝር መስፈርቶች ማረጋገጫ (Technical Compliance Matrix)",
        "category": "technical_sample",
        "category_label": "Technical Specifications & Samples",
        "mandatory": True,
        "description": (
            f"Item-by-item technical compliance sheet for '{getattr(bid, 'title', '')}', "
            f"confirming exact fabric composition (e.g., 100% Cotton, Poly-Cotton), fabric weight (GSM), colorfastness, sizing chart, and stitching standards."
        ),
        "tips": "Attach laboratory test reports or fabric manufacturer datasheets to gain maximum technical evaluation score.",
        "is_prepared": "tech_compliance_matrix" in prep_set,
    })

    docs.append({
        "id": "past_performance",
        "title": "Past Performance / Experience Proof",
        "title_am": "ተመሳሳይ የስራ ልምድ ማስረጃዎች",
        "category": "technical_sample",
        "category_label": "Technical Specifications & Samples",
        "mandatory": False,
        "description": "At least 2–3 copies of completed contracts, delivery acceptance certificates, or recommendation letters for similar garment/uniform supplies executed in the past 2–3 years.",
        "tips": "Official testimonial letters from government agencies or large organizations carry high weight.",
        "is_prepared": "past_performance" in prep_set,
    })

    # 4. SUBMISSION FORMS & DECLARATIONS
    docs.append({
        "id": "bid_submission_form",
        "title": "Signed Bid Submission Form & Declaration",
        "title_am": "የጨረታ ማመልከቻ ቅጽ እና ማረጋገጫ",
        "category": "submission_forms",
        "category_label": "Forms & Authorizations",
        "mandatory": True,
        "description": f"Completed and officially signed Tender Submission Form on factory letterhead addressed to '{company}', sealed with authorized company stamp.",
        "tips": "Must be signed by the General Manager or legal representative holding a power of attorney.",
        "is_prepared": "bid_submission_form" in prep_set,
    })

    docs.append({
        "id": "financial_offer_sheet",
        "title": "Financial Proposal & Price Schedule",
        "title_am": "የዋጋ ማቅረቢያ ሰነድ (Financial Offer / Bill of Quantities)",
        "category": "submission_forms",
        "category_label": "Forms & Authorizations",
        "mandatory": True,
        "description": (
            f"Priced Schedule of Requirements / quotation sheet showing unit rate, total price, "
            f"and 15% VAT clearly itemized in {sec_curr}. Signed and stamped on every page."
        ),
        "tips": "Verify all unit rate calculations to eliminate arithmetic errors that could cause bid rejection.",
        "is_prepared": "financial_offer_sheet" in prep_set,
    })

    docs.append({
        "id": "power_of_attorney",
        "title": "Power of Attorney (if applicable)",
        "title_am": "ህጋዊ የውክልና ማስረጃ (ካለ)",
        "category": "submission_forms",
        "category_label": "Forms & Authorizations",
        "mandatory": False,
        "description": "Authenticated Power of Attorney from the Documents Authentication and Registration Agency (DARA) if documents or CPO are submitted/signed by an authorized representative.",
        "tips": "Required only if someone other than the legal General Manager is signing or submitting the tender.",
        "is_prepared": "power_of_attorney" in prep_set,
    })

    return docs


def get_docs_summary_for_bid(bid) -> Dict[str, Any]:
    """Return lightweight summary counts and headline for tables/excel."""
    docs = get_required_documents_for_bid(bid)
    total_docs = len(docs)
    mandatory_docs = sum(1 for d in docs if d["mandatory"])
    prepared_docs = sum(1 for d in docs if d.get("is_prepared"))
    
    sec_amount = getattr(bid, "bid_security_amount", None)
    sec_curr = getattr(bid, "bid_security_currency", "ETB") or "ETB"
    cpo_text = f"CPO: {sec_curr} {sec_amount:,.2f}" if sec_amount and sec_amount > 0 else "CPO: Check Doc"
    
    summary_text = f"{total_docs} Required Docs ({cpo_text} • Physical Sample • Trade License & Tax Clearance)"
    
    return {
        "total_docs": total_docs,
        "mandatory_docs": mandatory_docs,
        "prepared_docs": prepared_docs,
        "summary_text": summary_text,
    }
