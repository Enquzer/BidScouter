"""
BidScouter - Windows Notifier
Sends toast notifications and plays alert sound.
"""
import logging
import os
import sys

logger = logging.getLogger("bidscouter.notifier")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOUND_PATH = os.path.join(BASE_DIR, "sounds", "alert.wav")
ICON_PATH = os.path.join(BASE_DIR, "sounds", "icon.ico")


def _play_sound():
    try:
        import winsound
        if os.path.exists(SOUND_PATH):
            winsound.PlaySound(SOUND_PATH, winsound.SND_FILENAME | winsound.SND_ASYNC)
        else:
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
    except Exception as e:
        logger.warning(f"Sound error: {e}")


def notify_new_bids(count: int, site_name: str):
    """Toast notification for newly found bids."""
    import json
    settings_path = os.path.join(BASE_DIR, "config", "settings.json")
    try:
        with open(settings_path) as f:
            s = json.load(f)
        if not s.get("notifications", {}).get("enabled", True):
            return
        sound = s.get("notifications", {}).get("sound_enabled", True)
    except Exception:
        sound = True

    title = f"🎯 BidScouter — {count} New Bid{'s' if count > 1 else ''} Found!"
    msg = f"Found on {site_name}.\nClick to open BidScouter dashboard."

    try:
        from win10toast_click import ToastNotifier
        icon = ICON_PATH if os.path.exists(ICON_PATH) else None
        toaster = ToastNotifier()
        toaster.show_toast(
            title,
            msg,
            icon_path=icon,
            duration=8,
            threaded=True,
            callback_on_click=_open_dashboard,
        )
    except ImportError:
        # Fallback: use ctypes MessageBox
        _fallback_notify(title, msg)
    except Exception as e:
        logger.warning(f"Toast error: {e}")
        _fallback_notify(title, msg)

    if sound:
        _play_sound()


def notify_deadline_reminder(bid, hours_left: float):
    """Toast notification for upcoming deadline."""
    import json
    settings_path = os.path.join(BASE_DIR, "config", "settings.json")
    try:
        with open(settings_path) as f:
            s = json.load(f)
        if not s.get("notifications", {}).get("enabled", True):
            return
        sound = s.get("notifications", {}).get("sound_enabled", True)
    except Exception:
        sound = True

    h = int(hours_left)
    title = f"⏰ BidScouter — Deadline in {h} hours!"
    msg = f"{bid.title[:80]}\n{bid.company or ''}\nDeadline: {bid.deadline.strftime('%d %b %Y %H:%M') if bid.deadline else 'N/A'}"

    try:
        from win10toast_click import ToastNotifier
        icon = ICON_PATH if os.path.exists(ICON_PATH) else None
        toaster = ToastNotifier()
        toaster.show_toast(
            title,
            msg,
            icon_path=icon,
            duration=10,
            threaded=True,
            callback_on_click=_open_dashboard,
        )
    except ImportError:
        _fallback_notify(title, msg)
    except Exception as e:
        logger.warning(f"Toast error: {e}")
        _fallback_notify(title, msg)

    if sound:
        _play_sound()


def notify_cpo_refund(bid):
    """Remind user to collect CPO/security refund for failed/cancelled bid."""
    title = f"💰 BidScouter — Collect CPO Refund!"
    status = getattr(bid, 'application_status', 'failed').upper()
    amount = ""
    if bid.bid_security_amount:
        amount = f" — ETB {bid.bid_security_amount:,.0f}"
    msg = f"Bid {status}: {bid.title[:60]}\nPlease collect your CPO / bid security{amount}."
    try:
        from win10toast_click import ToastNotifier
        icon = ICON_PATH if os.path.exists(ICON_PATH) else None
        toaster = ToastNotifier()
        toaster.show_toast(title, msg, icon_path=icon, duration=12, threaded=True,
                           callback_on_click=_open_dashboard)
    except Exception:
        _fallback_notify(title, msg)
    _play_sound()


def _open_dashboard():
    import webbrowser
    webbrowser.open("http://127.0.0.1:7800")


def _fallback_notify(title: str, msg: str):
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, msg, title, 0x40 | 0x1000)
    except Exception:
        pass
