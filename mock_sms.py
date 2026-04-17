"""
mock_sms.py
Sends fake UPI SMS payloads to the backend for testing.
Simulates both Karnataka Bank and generic bank formats.

Usage:
  python3 mock_sms.py
  python3 mock_sms.py --platform android   # simulate Android format
"""

import requests
import argparse
from datetime import datetime, timedelta

BACKEND_URL = "http://localhost:8000/sms"

MOCK_SMS = [
    # Karnataka Bank debits
    "Your a/c XX0092 debited for Rs.125.00 on 10-04-26 trf to TOP IN TOWN RETAIL. UPI:159589621133.For dispute SMS BLOCK 0092 to 9152916275 -KarnatakaBank",
    "Your a/c XX0092 debited for Rs.60.00 on 11-04-26 trf to CARE CHEMIST. UPI:96669123456.For dispute SMS BLOCK 0092 to 9152916275 -KarnatakaBank",
    "Your a/c XX0092 debited for Rs.232.00 on 12-04-26 trf to KPN FARM FRESH. UPI:88153987654.For dispute SMS BLOCK 0092 to 9152916275 -KarnatakaBank",
    # Karnataka Bank credits
    "Your a/c XX0092 is credited by Rs.500.00 from RAHUL SHARMA on 10-04-26 (UPI Ref no 217558235501) -KarnatakaBank",
    "Your a/c XX0092 is credited by Rs.1000.00 from SOMASHEKAR on 11-04-26 (UPI Ref no 557328941147) -KarnatakaBank",
    # Generic bank format
    "INR 300.00 debited from A/c XX1234 on 12-Apr-26. UPI Ref: 123456789012. To: Swiggy. Avl Bal: INR 4500.00",
    "INR 1500.00 credited to A/c XX1234 on 12-Apr-26. UPI Ref: 987654321098. From: Salary. Avl Bal: INR 6000.00",
]

def send(sms: str, timestamp: str, api_key: str = ""):
    headers = {}
    if api_key:
        headers["x-api-key"] = api_key
    try:
        resp = requests.post(
            BACKEND_URL,
            json={"sms": sms, "timestamp": timestamp},
            headers=headers,
            timeout=5
        )
        result = resp.json()
        print(f"  [{result.get('status')}] {sms[:60]}...")
    except Exception as e:
        print(f"  [error] {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", default="macos", choices=["macos", "android"])
    parser.add_argument("--api-key", default="")
    args = parser.parse_args()

    print(f"Sending {len(MOCK_SMS)} mock SMS ({args.platform} format)...")
    base_time = datetime.utcnow() - timedelta(days=3)

    for i, sms in enumerate(MOCK_SMS):
        ts = (base_time + timedelta(hours=i*6)).isoformat()
        send(sms, ts, args.api_key)

    print("Done! Refresh your dashboard.")
