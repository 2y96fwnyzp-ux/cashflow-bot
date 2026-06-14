#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Розвідник: шукає правильний endpoint Instasport для розділу "Рух коштів".
Логіниться і пробує різні URL, показує що повертає кожен.
"""
import os, json, requests
from datetime import datetime, timedelta

INSTASPORT_URL = "https://instasport.ua"
CLUB_SLUG = "planetfitness"
HALL_ID   = "1376"
EMAIL     = os.getenv("INSTASPORT_EMAIL", "m-g-r@gmx.de")
PASSWORD  = os.getenv("INSTASPORT_PASSWORD", "Prepremium1990--")
API_KEY   = os.getenv("INSTASPORT_API_KEY", "3q8hnVD33+HCZdDenynXq85oD0m8rhqHE/hSQbi2JxY=")

base = f"{INSTASPORT_URL}/admin/club/{CLUB_SLUG}/api/v2"

# Логін
print("📌 Логін...")
r = requests.post(f"{base}/auth/token/",
    headers={'X-API-Key': API_KEY},
    json={'username': EMAIL, 'password': PASSWORD}, timeout=15)
if r.status_code != 200:
    print(f"❌ Логін не вдався: {r.status_code} {r.text[:300]}")
    raise SystemExit
token = r.json().get('token')
print("✅ Логін OK\n")

H = {'Authorization': f'Bearer {token}', 'X-API-Key': API_KEY}
today = datetime.now().strftime("%Y-%m-%d")
tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

# Кандидати endpoint'ів для "Рух коштів"
candidates = [
    f"{base}/manager/cashflow/?hall={HALL_ID}&date_after={today}&date_before={tomorrow}",
    f"{base}/manager/cashflow/?hall={HALL_ID}&date_effective_after={today}&date_effective_before={tomorrow}",
    f"{base}/manager/cash-flow/?hall={HALL_ID}&date_after={today}&date_before={tomorrow}",
    f"{base}/manager/finance/?hall={HALL_ID}&date_after={today}&date_before={tomorrow}",
    f"{base}/manager/money-movement/?hall={HALL_ID}&date_after={today}",
    f"{base}/manager/transaction/?hall={HALL_ID}&date_effective_after={today}&date_effective_before={tomorrow}",
    f"{base}/manager/payment/?hall={HALL_ID}&date_after={today}&date_before={tomorrow}",
    f"{base}/manager/balance/?hall={HALL_ID}&date={today}",
    f"{base}/manager/report/cashflow/?hall={HALL_ID}&date={today}",
    f"{base}/manager/report/?hall={HALL_ID}&date={today}",
]

print(f"🔎 Перевіряю endpoint'и за {today}...\n")
for url in candidates:
    short = url.replace(base, "")
    try:
        rr = requests.get(url, headers=H, timeout=15)
        code = rr.status_code
        if code == 200:
            txt = rr.text
            # шукаємо ознаки наших сум
            hit = "27325" in txt or "13095" in txt or "14230" in txt
            preview = txt[:400].replace("\n", " ")
            print(f"✅ [{code}] {short}")
            print(f"    {'🎯 МІСТИТЬ НАШІ СУМИ!' if hit else 'дані є, але без наших сум'}")
            print(f"    {preview}\n")
        else:
            print(f"❌ [{code}] {short}")
    except Exception as e:
        print(f"⚠️  [ERR] {short}  {e}")

print("\nГотово. Шукай рядок з 🎯 — це правильний endpoint.")
