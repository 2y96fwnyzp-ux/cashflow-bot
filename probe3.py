#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Розвідник 3: групуємо суми по debit_account, credit_account
щоб знайти що = готівка (13095), що = термінал (14230).
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
r = requests.post(f"{base}/auth/token/", headers={'X-API-Key': API_KEY},
    json={'username': EMAIL, 'password': PASSWORD}, timeout=15)
token = r.json().get('token')
H = {'Authorization': f'Bearer {token}', 'X-API-Key': API_KEY}
print("✅ Логін OK\n")

today = datetime.now().strftime("%Y-%m-%d")
tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

all_results = []
url = f"{base}/manager/transaction/?hall={HALL_ID}&date_effective_after={today}&date_effective_before={tomorrow}&page_size=200"
while url:
    rr = requests.get(url, headers=H, timeout=20)
    d = rr.json()
    all_results.extend(d.get("results", []))
    url = d.get("next")
print(f"Транзакцій: {len(all_results)}  (ціль: готівка 13095, термінал 14230)\n")

def grp(field):
    g = defaultdict(float)
    for t in all_results:
        try: g[str(t.get(field))] += float(t.get("value", 0) or 0)
        except: pass
    return g

for field in ["debit_account", "credit_account"]:
    print("="*55)
    print(f"СУМИ ПО '{field}':")
    print("="*55)
    for k, v in sorted(grp(field).items(), key=lambda x: -x[1]):
        mark = ""
        if 13000 <= v <= 13200: mark = "  ⬅️ схоже на ГОТІВКУ (13095)"
        if 14100 <= v <= 14350: mark = "  ⬅️ схоже на ТЕРМІНАЛ (14230)"
        print(f"   {field}={k}: {v:,.2f}{mark}")
    print()

# Пари debit+credit
print("="*55)
print("СУМИ ПО ПАРАХ debit→credit:")
print("="*55)
pairs = defaultdict(float)
for t in all_results:
    key = f"{t.get('debit_account')}→{t.get('credit_account')}"
    try: pairs[key] += float(t.get("value", 0) or 0)
    except: pass
for k, v in sorted(pairs.items(), key=lambda x: -x[1]):
    print(f"   {k}: {v:,.2f}")

# Тільки реальні надходження (supplementary=false)
print("\n" + "="*55)
print("ТІЛЬКИ supplementary=false, по debit_account:")
print("="*55)
g2 = defaultdict(float)
for t in all_results:
    if not t.get("supplementary"):
        try: g2[str(t.get("debit_account"))] += float(t.get("value",0) or 0)
        except: pass
for k, v in sorted(g2.items(), key=lambda x: -x[1]):
    print(f"   debit={k}: {v:,.2f}")
