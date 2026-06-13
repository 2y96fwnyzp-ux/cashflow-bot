#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Касовий звіт бот для Instasport.ua
deal=4  → Готівка сальдо
deal=55 → Термінал сальдо
Фільтр: date_effective_after / date_effective_before
Відправляє в Telegram о 21:50

Усі секрети читаються зі змінних оточення (Railway Variables):
  TELEGRAM_BOT_TOKEN, CHAT_ID, INSTASPORT_API_KEY,
  INSTASPORT_EMAIL, INSTASPORT_PASSWORD, CLUB_SLUG, HALL_ID
"""

import os
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
CLUB_SLUG = os.getenv("CLUB_SLUG", "planetfitness")
HALL_ID   = os.getenv("HALL_ID", "1376")
EMAIL     = os.getenv("INSTASPORT_EMAIL", "")
PASSWORD  = os.getenv("INSTASPORT_PASSWORD", "")
API_KEY   = os.getenv("INSTASPORT_API_KEY", "")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID   = os.getenv("CHAT_ID", "")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
TIMEZONE = pytz.timezone('Europe/Kyiv')

ACCOUNT_CASH     = 3   # debit_account=3 → Готівка
ACCOUNT_TERMINAL = 7   # debit_account=7 → Термінал

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

    def fetch_transactions(self, date_str):
        """Тягне ВСІ транзакції за день (з усіх сторінок)"""
        headers = {
            'Authorization': f'Bearer {self.token}',
            'X-API-Key': API_KEY
        }
        date_next = (datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
        url = (
            f"{INSTASPORT_URL}/admin/club/{CLUB_SLUG}/api/v2/manager/transaction/"
            f"?hall={HALL_ID}"
            f"&date_effective_after={date_str}"
            f"&date_effective_before={date_next}"
            f"&page_size=200"
        )
        results = []
        try:
            while url:
                r = requests.get(url, headers=headers, timeout=20)
                if r.status_code != 200:
                    logger.error(f"❌ Помилка транзакцій: {r.status_code}")
                    break
                d = r.json()
                results.extend(d.get('results', []))
                url = d.get('next')
        except Exception as e:
            logger.error(f"❌ Помилка: {e}")
        return results

    def fetch_cashflow(self, date_str):
        """Витягує касовий звіт за день.
        Готівка = сума value де debit_account=3
        Термінал = сума value де debit_account=7
        """
        logger.info(f"📌 Витягування касового звіту за {date_str}...")

        txs = self.fetch_transactions(date_str)
        logger.info(f"   Отримано транзакцій: {len(txs)}")

        cash_balance = 0.0
        terminal_balance = 0.0
        for t in txs:
            try:
                val = float(t.get('value', 0) or 0)
            except (TypeError, ValueError):
                continue
            acc = t.get('debit_account')
            if acc == ACCOUNT_CASH:
                cash_balance += val
            elif acc == ACCOUNT_TERMINAL:
                terminal_balance += val

        total_balance = cash_balance + terminal_balance

        logger.info(f"✅ Готівка (debit={ACCOUNT_CASH}): {cash_balance:,.2f} грн")
        logger.info(f"✅ Термінал (debit={ACCOUNT_TERMINAL}): {terminal_balance:,.2f} грн")
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

    # Перевірка що секрети задані
    if not BOT_TOKEN or not API_KEY or not EMAIL or not PASSWORD:
        logger.error("❌ Не задані змінні оточення! Перевір Railway Variables: "
                     "TELEGRAM_BOT_TOKEN, CHAT_ID, INSTASPORT_API_KEY, INSTASPORT_EMAIL, INSTASPORT_PASSWORD")

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
