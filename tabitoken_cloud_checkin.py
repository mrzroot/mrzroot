#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
====================================================================
  ☁️ اسکریپت ابری ثبت Check-in روزانه TabiAI در GitHub Actions
====================================================================
"""

import os
import sys
import json
import urllib.request
import urllib.parse
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    'Content-Type': 'application/json',
    'Accept': 'application/json, text/plain, */*',
    'Origin': 'https://tabitoken.com',
    'Referer': 'https://tabitoken.com/profile',
}

CHECKIN_ENDPOINTS = [
    "https://tabitoken.com/api/user/checkin",
    "https://tabitoken.com/api/v1/user/checkin",
    "https://tabitoken.com/api/checkin",
    "https://api.tabitoken.com/v1/user/checkin",
    "https://tabitoken.com/api/task/daily_checkin"
]

PROFILE_ENDPOINT = "https://tabitoken.com/api/user/profile"

def main():
    print("=" * 65)
    print(f"🚀 شروع اجرای اسکریپت ابری TabiToken در {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 65)

    token = os.environ.get("TABITOKEN_AUTH_TOKEN", "").strip()
    cookie = os.environ.get("TABITOKEN_COOKIE", "").strip()

    if not token and not cookie:
        print("❌ خطا: متغیر TABITOKEN_AUTH_TOKEN یا TABITOKEN_COOKIE در تنظیمات Secret گیت‌هاب تعریف نشده است.")
        sys.exit(1)

    req_headers = HEADERS.copy()
    if token:
        if not token.lower().startswith("bearer "):
            token = f"Bearer {token}"
        req_headers['Authorization'] = token

    if cookie:
        req_headers['Cookie'] = cookie

    success = False
    for url in CHECKIN_ENDPOINTS:
        print(f"📡 ارسال درخواست Check-in به: {url} ...")
        try:
            req = urllib.request.Request(url, data=b"{}", headers=req_headers, method="POST")
            with urllib.request.urlopen(req, timeout=25) as resp:
                status = resp.status
                body = resp.read().decode('utf-8', errors='ignore')
                print(f"🎉 پاسخ موفقیت‌آمیز (کد {status}): {body}")
                success = True
                break
        except urllib.error.HTTPError as e:
            err_body = e.read().decode('utf-8', errors='ignore')
            if e.code == 400 and ("already" in err_body.lower() or "checked" in err_body.lower()):
                print(f"ℹ️ وضعیت: امروز قبلاً پاداش Check-in دریافت شده است ({err_body}).")
                success = True
                break
            print(f"⚠️ پاسخ سرور {url} (کد {e.code}): {err_body}")
        except Exception as e:
            print(f"⚠️ خطا در ارتباط با {url}: {e}")

    try:
        req_prof = urllib.request.Request(PROFILE_ENDPOINT, headers=req_headers, method="GET")
        with urllib.request.urlopen(req_prof, timeout=15) as resp:
            prof_data = json.loads(resp.read().decode('utf-8'))
            balance = prof_data.get("data", {}).get("balance", "نامشخص")
            print(f"💰 موجودی فعلی حساب شما: ${balance}")
    except Exception as e:
        print(f"⚠️ استعلام موجودی: {e}")

    print("=" * 65)
    if success:
        print("✅ عملیات دریافت پاداش ابری با موفقیت تکمیل شد!")
    else:
        print("⚠️ عملیات انجام شد؛ لطفاً اعتبار توکن را بررسی فرمایید.")
    print("=" * 65)

if __name__ == "__main__":
    main()
