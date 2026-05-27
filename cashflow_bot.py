#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Касовий звіт бот для Instasport.ua
deal=4  → Готівка сальдо
deal=55 → Термінал сальдо
Фільтр: date_effective_after / date_effective_before
Відправляє в Telegram о 21:50
"""

import sys
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
import logging
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

INSTASPORT_URL = "https://instasport.ua"
CLUB_SLUG = "planetfitness"
HALL_ID = "1376"
EMAIL = "m-g-r@gmx.de"
PASSWORD = "Prepremium1990--"
API_KEY = "3q8hnVD33+HCZdDenynXq85oD0m8rhqHE/hSQbi2JxY="
BOT_TOKEN = "8826656917:AAHRDxS_q_vgWJ3sjvs67zY4V1Iqoq4sJDs"
CHAT_ID = "438857354"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
TIMEZONE = pytz.timezone('Europe/Kyiv')

DEAL_CASH     = 4   # Готівка сальдо
DEAL_TERMINAL = 55  # Термінал сальдо

class InstasportBot:
    def __init__(self):
        self.token = None

    def login(self):
        """Логін через API"""
        try:
            logger.info("📌 Логін через API...")
            r = requests.post(
                f"{INSTASPORT_URL}/admin/club/{CLUB_SLUG}/api/v2/auth/token/",
                headers={'X-API-Key': API_KEY},
                json={'username': EMAIL, 'password': PASSWORD},
                timeout=10
            )
            if r.status_code == 200:
                self.token = r.json().get('token')
                logger.info("✅ Успішний логін!")
                return True
            logger.error(f"❌ Помилка логіну: {r.status_code} - {r.text}")
            return False
        except Exception as e:
            logger.error(f"❌ Помилка: {e}")
            return False

    def get_deal_value(self, deal_id, date_str):
        """Отримує суму для конкретного deal за день"""
        try:
            headers = {
                'Authorization': f'Bearer {self.token}',
                'X-API-Key': API_KEY
            }

            # Правильний фільтр дати
            date_next = (datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")

            url = (
                f"{INSTASPORT_URL}/admin/club/{CLUB_SLUG}/api/v2/manager/transaction/"
                f"?deal={deal_id}&hall={HALL_ID}"
                f"&date_effective_after={date_str}"
                f"&date_effective_before={date_next}"
            )

            r = requests.get(url, headers=headers, timeout=10)

            if r.status_code == 200:
                results = r.json().get('results', [])
                total = sum(float(t.get('value', 0)) for t in results)
                logger.info(f"   deal={deal_id}: {total:,.2f} грн ({len(results)} записів)")
                return total
            else:
                logger.error(f"❌ Помилка deal={deal_id}: {r.status_code}")
                return 0

        except Exception as e:
            logger.error(f"❌ Помилка: {e}")
            return 0

    def fetch_cashflow(self, date_str):
        """Витягує касовий звіт за день"""
        logger.info(f"📌 Витягування касового звіту за {date_str}...")

        cash_balance     = self.get_deal_value(DEAL_CASH, date_str)
        terminal_balance = self.get_deal_value(DEAL_TERMINAL, date_str)
        total_balance    = cash_balance + terminal_balance

        logger.info(f"✅ Готівка: {cash_balance:,.2f} грн")
        logger.info(f"✅ Термінал: {terminal_balance:,.2f} грн")
        logger.info(f"✅ Всього: {total_balance:,.2f} грн")

        return {
            'cash': cash_balance,
            'terminal': terminal_balance,
            'total': total_balance
        }

    def format_message(self, cashflow, date_str):
        """Форматує звіт для Telegram"""
        date_fmt = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d.%m.%Y")
        return (
            f"📊 КАСОВИЙ ЗВІТ — {date_fmt}\n\n"
            f"💵 ГОТІВКА (сальдо): {cashflow['cash']:,.2f} грн\n"
            f"📱 ТЕРМІНАЛ (сальдо): {cashflow['terminal']:,.2f} грн\n\n"
            f"✅ ЗАГАЛЬНЕ САЛЬДО: {cashflow['total']:,.2f} грн"
        )

    def send_to_telegram(self, message):
        """Відправляє звіт в Telegram"""
        try:
            logger.info("📌 Відправка в Telegram...")
            r = requests.post(
                TELEGRAM_API_URL,
                json={'chat_id': CHAT_ID, 'text': message},
                timeout=10
            )
            if r.status_code == 200:
                logger.info("✅ Звіт відправлено!")
                return True
            logger.error(f"❌ Помилка: {r.text}")
            return False
        except Exception as e:
            logger.error(f"❌ Помилка: {e}")
            return False

    def run_report(self):
        """Запускає генерацію звіту"""
        logger.info("\n" + "="*60)
        logger.info("🚀 ЗАПУСК КАСОВОГО ЗВІТУ")
        logger.info("="*60)

        self.token = None

        if not self.login():
            return

        today = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
        cashflow = self.fetch_cashflow(today)

        message = self.format_message(cashflow, today)
        logger.info(f"\n📋 Звіт:\n{message}\n")

        self.send_to_telegram(message)
        logger.info("="*60 + "\n")


def main():
    logger.info("🤖 Запуск бота касового звіту")
    logger.info(f"📍 Клуб: {CLUB_SLUG}, Зал: {HALL_ID}")
    logger.info(f"⏰ Звіт о 21:50 (UTC+3)\n")

    bot = InstasportBot()
    scheduler = BackgroundScheduler(timezone=TIMEZONE)
    scheduler.add_job(
        bot.run_report,
        CronTrigger(hour=21, minute=50),
        id='cashflow_report'
    )
    scheduler.start()
    logger.info("✅ Scheduler запущений\n")

    try:
        logger.info("🧪 ТЕСТОВА ГЕНЕРАЦІЯ...")
        bot.run_report()
        logger.info("🔄 Бот працює. Натисни Ctrl+C для завершення.\n")
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("⛔ Зупинка...")
        scheduler.shutdown()
        sys.exit(0)

if __name__ == '__main__':
    main()
