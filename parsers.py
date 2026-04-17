"""
parsers.py
All SMS parsing logic lives here. Add a new parser function for each bank format.
"""

import re


def parse_upi_sms(sms: str) -> dict | None:
    """
    Master parser — tries each bank parser in order.
    Returns a dict or None if not a UPI transaction.
    """
    sms_lower = sms.lower()
    if "upi" not in sms_lower:
        return None

    for parser in [parse_karnataka_bank, parse_generic]:
        result = parser(sms)
        if result:
            return result
    return None


def parse_karnataka_bank(sms: str) -> dict | None:
    """Karnataka Bank format: 'Your a/c XX0092 debited for Rs.X on DD-MM-YY trf to MERCHANT. UPI:XXXX'"""
    if "karnataka" not in sms.lower() and "kblbnk" not in sms.lower():
        return None

    result = {}

    amount_match = re.search(r"(?:rs\.?|inr|₹)\s*([\d,]+(?:\.\d{1,2})?)", sms, re.IGNORECASE)
    if not amount_match:
        return None
    result["amount"] = float(amount_match.group(1).replace(",", ""))

    sms_lower = sms.lower()
    if any(w in sms_lower for w in ["debited", "debit"]):
        result["type"] = "debit"
    elif any(w in sms_lower for w in ["credited", "credit", "received"]):
        result["type"] = "credit"
    else:
        result["type"] = "unknown"

    # Karnataka Bank uses "trf to MERCHANT" for debit, "from NAME" for credit
    merchant_match = (
        re.search(r"trf\s+to\s+([A-Za-z0-9@._\-\s]{3,40})(?:\.|,|UPI|$)", sms, re.IGNORECASE) or
        re.search(r"(?:credited|credit).*?from\s+([A-Za-z0-9@._\-\s]{3,40})(?:\s+on|\.|,|\(|$)", sms, re.IGNORECASE)
    )
    result["merchant"] = merchant_match.group(1).strip() if merchant_match else None

    ref_match = re.search(r"upi\s*:\s*(\d{6,})", sms, re.IGNORECASE)
    result["upi_ref"] = ref_match.group(1) if ref_match else None

    acc_match = re.search(r"(?:a/?c|acct|account)[^X\d]*[Xx]*(\d{4})", sms, re.IGNORECASE)
    result["account"] = acc_match.group(1) if acc_match else None

    bal_match = re.search(
        r"(?:avl\.?\s*bal\.?|available\s+balance|bal)\s*[:\-]?\s*(?:rs\.?|inr|₹)?\s*([\d,]+(?:\.\d{1,2})?)",
        sms, re.IGNORECASE
    )
    result["balance"] = float(bal_match.group(1).replace(",", "")) if bal_match else None

    return result


def parse_generic(sms: str) -> dict | None:
    """Generic Indian bank UPI SMS format."""
    result = {}

    amount_match = re.search(r"(?:rs\.?|inr|₹)\s*([\d,]+(?:\.\d{1,2})?)", sms, re.IGNORECASE)
    if not amount_match:
        return None
    result["amount"] = float(amount_match.group(1).replace(",", ""))

    sms_lower = sms.lower()
    if any(w in sms_lower for w in ["debited", "debit", "sent", "paid", "payment of"]):
        result["type"] = "debit"
    elif any(w in sms_lower for w in ["credited", "credit", "received"]):
        result["type"] = "credit"
    else:
        result["type"] = "unknown"

    merchant_match = re.search(
        r"(?:to|from)\s+([A-Za-z0-9@._\-\s]{3,40})(?:\s+on|\s+via|\s+ref|\.|,|$)",
        sms, re.IGNORECASE
    )
    result["merchant"] = merchant_match.group(1).strip() if merchant_match else None

    ref_match = re.search(r"(?:upi\s*ref\.?\s*(?:no\.?)?\s*:?\s*|upi\s*:\s*)(\d{10,})", sms, re.IGNORECASE)
    result["upi_ref"] = ref_match.group(1) if ref_match else None

    acc_match = re.search(r"(?:a/?c|acct|account)[^X\d]*[Xx]*(\d{4})", sms, re.IGNORECASE)
    result["account"] = acc_match.group(1) if acc_match else None

    bal_match = re.search(
        r"(?:avl\.?\s*bal\.?|available\s+balance|bal)\s*[:\-]?\s*(?:rs\.?|inr|₹)?\s*([\d,]+(?:\.\d{1,2})?)",
        sms, re.IGNORECASE
    )
    result["balance"] = float(bal_match.group(1).replace(",", "")) if bal_match else None

    return result
