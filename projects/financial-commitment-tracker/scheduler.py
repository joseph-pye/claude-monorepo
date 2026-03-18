"""Reminder scheduler — checks commitments and sends Telegram notifications."""

import os
from datetime import date

from apscheduler.schedulers.background import BackgroundScheduler

from database import SessionLocal, Commitment
from telegram_bot import send_telegram_message

scheduler = BackgroundScheduler()


def check_reminders():
    """Check all active commitments and send reminders at 90/30/7 day thresholds."""
    db = SessionLocal()
    try:
        commitments = db.query(Commitment).filter(Commitment.is_archived == False).all()
        today = date.today()

        for c in commitments:
            days = (c.expiry_date - today).days

            if days <= 7 and not c.reminder_7_sent:
                send_telegram_message(
                    f"🚨 *URGENT* — {c.name} expires in {days} day(s)!\n"
                    f"Provider: {c.provider or 'N/A'}\n"
                    f"Amount: {c.amount or 'N/A'}\n"
                    f"Expiry: {c.expiry_date}\n\n"
                    f"Time to renew — update the expiry date once done."
                )
                c.reminder_7_sent = True

            elif days <= 30 and not c.reminder_30_sent:
                send_telegram_message(
                    f"⚠️ *Coming soon* — {c.name} expires in {days} days.\n"
                    f"Provider: {c.provider or 'N/A'}\n"
                    f"Amount: {c.amount or 'N/A'}\n"
                    f"Expiry: {c.expiry_date}\n\n"
                    f"Start looking into renewal options."
                )
                c.reminder_30_sent = True

            elif days <= 90 and not c.reminder_90_sent:
                send_telegram_message(
                    f"📋 *Heads up* — {c.name} expires in {days} days.\n"
                    f"Provider: {c.provider or 'N/A'}\n"
                    f"Amount: {c.amount or 'N/A'}\n"
                    f"Expiry: {c.expiry_date}\n\n"
                    f"No action needed yet, just keeping you informed."
                )
                c.reminder_90_sent = True

            elif days < 0:
                send_telegram_message(
                    f"❌ *EXPIRED* — {c.name} expired {abs(days)} day(s) ago!\n"
                    f"Provider: {c.provider or 'N/A'}\n"
                    f"Expiry was: {c.expiry_date}\n\n"
                    f"Please renew and update the expiry date."
                )

        db.commit()
    finally:
        db.close()


def send_weekly_summary():
    """Send a reassurance summary every Monday morning."""
    db = SessionLocal()
    try:
        commitments = (
            db.query(Commitment)
            .filter(Commitment.is_archived == False)
            .order_by(Commitment.expiry_date.asc())
            .all()
        )
        today = date.today()

        if not commitments:
            send_telegram_message("✅ *Weekly Summary*\n\nNo commitments tracked yet. Add some!")
            return

        urgent = []
        upcoming = []
        all_good = []

        for c in commitments:
            days = (c.expiry_date - today).days
            line = f"• {c.name} — {c.expiry_date} ({days} days)"
            if days <= 7:
                urgent.append(line)
            elif days <= 90:
                upcoming.append(line)
            else:
                all_good.append(line)

        parts = ["📊 *Weekly Commitment Summary*\n"]

        if urgent:
            parts.append("🚨 *Needs attention:*")
            parts.extend(urgent)
            parts.append("")

        if upcoming:
            parts.append("📋 *Coming up (next 90 days):*")
            parts.extend(upcoming)
            parts.append("")

        if all_good:
            parts.append("✅ *All clear:*")
            parts.extend(all_good)
            parts.append("")

        if not urgent and not upcoming:
            parts.append("🎉 Nothing needs your attention. All commitments are well away from expiry!")

        send_telegram_message("\n".join(parts))
    finally:
        db.close()


def start_scheduler():
    interval = int(os.getenv("REMINDER_CHECK_INTERVAL", "60"))
    scheduler.add_job(check_reminders, "interval", minutes=interval, id="check_reminders")
    scheduler.add_job(send_weekly_summary, "cron", day_of_week="mon", hour=9, id="weekly_summary")
    scheduler.start()


def shutdown_scheduler():
    scheduler.shutdown(wait=False)
