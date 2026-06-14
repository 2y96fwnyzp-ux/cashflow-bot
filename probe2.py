#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Розвідник 2: дивимось повну структуру транзакцій з manager/transaction/
і пробуємо порахувати касу по способах оплати.
"""
import os, json, requests
from datetime import datetime, timedelta
from collections import defaultdict

INSTASPORT_URL = "https://instasport.ua"
CLUB_SLUG = "planetfitness"
HALL_ID   = "1376"
EMAIL     = os.getenv("INSTASPORT_EMAIL", "m-g-r@gmx.de")
PASSWORD  = os.getenv("INSTASPORT_PASSWORD", "Prepremium1990--")
API_KEY   = os.getenv("INSTASPORT_API_KEY", "3q8hnVD33+HCZdDenynXq85oD0m8rhqHE/hSQbi2JxY=")

base = f"{INSTASPORT_URL}/admin/club/{CLUB_SLUG}/api/v2"

print("📌 Логін...")
r = requests.post(f"{base}/auth/token/",
    headers={'X-API-Key': API_KEY},
    json={'username': EMAIL, 'password': PASSWORD}, timeout=15)
token = r.json().get('token')
print("✅ Логін OK\n")

H = {'Authorization': f'Bearer {token}', 'X-API-Key': API_KEY}
today = datetime.now().strftime("%Y-%m-%d")
tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

# Тягнемо ВСІ сторінки транзакцій за сьогодні
all_results = []
url = f"{base}/manager/transaction/?hall={HALL_ID}&date_effective_after={today}&date_effective_before={tomorrow}&page_size=200"
while url:
    rr = requests.get(url, headers=H, timeout=20)
    if rr.status_code != 200:
        print(f"❌ {rr.status_code}")
        break
    d = rr.json()
    all_results.extend(d.get("results", []))
    url = d.get("next")
print(f"Усього транзакцій за {today}: {len(all_results)}\n")

if not all_results:
    print("Порожньо.")
    raise SystemExit

# 1) Показуємо ВСІ поля першої транзакції
print("="*60)
print("ПОВНА СТРУКТУРА ПЕРШОЇ ТРАНЗАКЦІЇ (всі поля):")
print("="*60)
print(json.dumps(all_results[0], ensure_ascii=False, indent=2))
print()

# 2) Які взагалі є ключі
print("="*60)
print("УСІ КЛЮЧІ (поля) в транзакції:")
print("="*60)
print(list(all_results[0].keys()))
print()

# 3) Шукаємо грошові поля і поля способу оплати
print("="*60)
print("АНАЛІЗ ГРОШОВИХ ПОЛІВ:")
print("="*60)
money_fields = ["value", "amount", "price", "sum", "total", "cash", "paid"]
pay_fields   = ["deal", "payment", "pay_type", "type", "method", "paid_detail", "kind"]

first = all_results[0]
for f in money_fields:
    if f in first:
        print(f"  💰 грошове поле '{f}' = {first[f]}")
for f in pay_fields:
    if f in first:
        print(f"  🏷  поле способу оплати '{f}' = {first[f]}")
print()

# 4) Групуємо суми по всіх можливих "способах оплати"
print("="*60)
print("СУМИ ПО ГРУПАХ (пробуємо різні поля групування):")
print("="*60)
# знайдемо перше реально присутнє грошове поле
mf = next((f for f in money_fields if f in first), None)
print(f"Використовую грошове поле: '{mf}'\n")

for gf in pay_fields:
    if gf in first:
        groups = defaultdict(float)
        for t in all_results:
            try:
                groups[str(t.get(gf))] += float(t.get(mf, 0) or 0)
            except: pass
        print(f"  Групування по '{gf}':")
        for k, v in sorted(groups.items(), key=lambda x: -x[1]):
            print(f"      {gf}={k}: {v:,.2f}")
        print()

total = sum(float(t.get(mf, 0) or 0) for t in all_results)
print(f"ЗАГАЛЬНА СУМА всіх '{mf}': {total:,.2f}")
print("\n(Очікуємо побачити десь 13095 готівка, 14230 термінал, разом 27325)")
