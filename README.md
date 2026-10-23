# 🎯 BidScouter — Ethiopian Garment Tender Tracker

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)]()
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D6.svg)]()

> **Automated procurement surveillance and application pipeline manager tailored for Ethiopian garment, apparel, and uniform manufacturers.**

---

## 🌟 Overview

**BidScouter** is a continuous procurement tracking intelligence tool designed specifically for garment factories operating in Ethiopia. It monitors national and international public tender portals—most critically the **Ethiopian Electronic Government Procurement portal ([e-GP](https://production.egp.gov.et))**—filters exclusively for textile, uniform, and garment opportunities, tracks submission deadlines, manages application progress, monitors CPO refund collections, and verifies required documentary evidence.

---

## 🚀 Key Features

* **Real-time Sourcing Crawler**:
  * Direct API integration with `production.egp.gov.et` (`cms-v2` Sourcing Gateway).
  * Fast batch retrieval with strict lot-level keyword classification (Uniforms, Workwear, Medical Scrubs, Military, School, Sportswear, Textiles).
  * Automatic exclusion filters to eliminate non-garment spills from multi-lot tender packages.
  * Filters out historical records to focus on **current and upcoming tenders**.

* **Direct Angular SPA Link Resolution**:
  * Reverse-engineered e-GP client routing to resolve exact Angular deep links (`/bids/all/{sourceApplication}/{id}/open`) so portal links never bounce back to `/egp/home`.

* **📋 Individual Bid Document Requirements Engine**:
  * Itemized, customized checklist generated dynamically per bid request.
  * **Legal & Statutory**: Renewed Trade License (2017 E.C.), Tax Clearance (MoR), VAT & TIN Certificates, PPAA Supplier Registration.
  * **Financial Securities**: Specific CPO / Bank Guarantee amounts with validity requirements and document purchase fee slips.
  * **Technical & Physical Samples**: Mandatory physical sample delivery instructions (with deadline and delivery location), fabric compliance matrices (GSM, composition, colorfastness), and past performance letters.
  * **One-Click Printable Checklist**: Formats a formal verification sheet for factory bid committees.

* **🗂 Application Pipeline & CPO Refund Tracker**:
  * 7-stage workflow: `Not Applied` ➔ `Doc Purchased` ➔ `CPO Delivered` ➔ `Applied` ➔ `Sample Delivered` ➔ `Secured 🎉` / `Failed ❌` / `Cancelled 🚫`.
  * Automatic reminders to collect **CPO Bank Guarantees** for failed or cancelled bids.

* **📊 Responsive Dashboard & Direct Excel Export**:
  * Zero-horizontal-overflow table layout with multi-line text wrapping.
  * Configurable page grouping (30, 50, 100, or Full List).
  * One-click formatted **Excel (`.xlsx`) export** with custom navy headers, auto-filters, clickable hyperlinks, and complete document requirement checklists.

* **🔔 Windows Background Desktop Notifications**:
  * Windows system toast alerts for newly discovered tenders and closing deadlines (≤30 hours).
  * One-click silent Windows desktop launcher (`BidScouter.lnk` / `Start_BidScouter.vbs`).

---

## 🛠️ Tech Stack

* **Backend**: Python, FastAPI, Uvicorn, SQLAlchemy, SQLite, APScheduler, HTTPX, OpenPyXL
* **Frontend**: Vanilla HTML5, CSS3 Modern Flex/Grid, JavaScript (SPA), Chart.js, Chartjs-Plugin-DataLabels
* **Desktop Integration**: Windows Script Host (VBScript), Windows Toast Notifier

---

## 📦 Installation & Setup

### Prerequisites
* Windows 10 or 11
* Python 3.10+ installed and added to `PATH`

### 1. Clone the Repository
```bash
git clone https://github.com/Enquzer/BidScouter.git
cd BidScouter
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Quick Start
Double-click `Start_BidScouter.vbs` or `start.bat`, or run manually:
```bash
python run_server.py
```
Open your browser and navigate to:
```
http://127.0.0.1:7800
```

### 4. Create Desktop Shortcut
Run the installer script:
```bash
install.bat
```
This generates a branded `BidScouter` shortcut with custom icons on your Windows Desktop for one-click startup.

---

## ⚙️ Configuration

Application settings, crawl intervals, and keywords can be modified directly within the **Settings** tab in the dashboard, or by editing `config/settings.json`:
* `crawler.interval_hours`: Crawler frequency (default: `5` hours).
* `notifications.reminder_hours_before`: Deadline alert threshold (default: `30` hours).
* `keywords.primary`: Monitored garment and textile search terms.

---

## 🏷️ Credits & Attribution

* **Powered by**: **Fashion-Flow 2026**
* **Created by**: **Enquzer Getachew**
