from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import sqlite3
import asyncio
from typing import Optional

from parsers import parse_upi_sms
from config import REQUIRE_AUTH, API_KEY, STRIP_PII, USE_QUEUE, DB_PATH

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory queue (activated via USE_QUEUE=true in .env) ───────────────────
_queue: asyncio.Queue = asyncio.Queue()

@app.on_event("startup")
async def start_queue_worker():
    if USE_QUEUE:
        asyncio.create_task(queue_worker())

async def queue_worker():
    while True:
        payload = await _queue.get()
        _save_transaction(payload)
        _queue.task_done()

# ── Auth (activated via API_KEY=xxx in .env) ─────────────────────────────────
async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    if REQUIRE_AUTH and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

# ── DB ────────────────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                amount      REAL    NOT NULL,
                type        TEXT    NOT NULL,
                merchant    TEXT,
                upi_ref     TEXT,
                account     TEXT,
                balance     REAL,
                raw_sms     TEXT,
                timestamp   TEXT    NOT NULL,
                created_at  TEXT    DEFAULT (datetime('now'))
            )
        """)

init_db()

# ── Helpers ───────────────────────────────────────────────────────────────────
def _save_transaction(data: dict):
    with get_db() as conn:
        if data.get("upi_ref"):
            existing = conn.execute(
                "SELECT id FROM transactions WHERE upi_ref = ?", (data["upi_ref"],)
            ).fetchone()
            if existing:
                return "duplicate"

        merchant = None if STRIP_PII else data.get("merchant")

        conn.execute(
            """INSERT INTO transactions
               (amount, type, merchant, upi_ref, account, balance, raw_sms, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (data["amount"], data["type"], merchant,
             data.get("upi_ref"), data.get("account"), data.get("balance"),
             data.get("raw_sms"), data.get("timestamp"))
        )
    return "ok"

# ── Models ────────────────────────────────────────────────────────────────────
class SMSPayload(BaseModel):
    sms: str
    timestamp: str | None = None

class TransactionIn(BaseModel):
    amount: float
    type: str
    merchant: str | None = None
    upi_ref: str | None = None
    account: str | None = None
    balance: float | None = None
    timestamp: str | None = None

# ── Routes ────────────────────────────────────────────────────────────────────
@app.post("/sms", dependencies=[Depends(verify_api_key)])
async def receive_sms(payload: SMSPayload):
    parsed = parse_upi_sms(payload.sms)
    if not parsed:
        return {"status": "ignored", "reason": "Not a UPI transaction SMS"}

    ts = payload.timestamp or datetime.utcnow().isoformat()
    data = {**parsed, "raw_sms": payload.sms, "timestamp": ts}

    if USE_QUEUE:
        await _queue.put(data)
        return {"status": "queued", "parsed": parsed}

    status = _save_transaction(data)
    return {"status": status, "parsed": parsed}


@app.get("/transactions", dependencies=[Depends(verify_api_key)])
def get_transactions(limit: int = 100, offset: int = 0, type: str | None = None):
    with get_db() as conn:
        if type:
            rows = conn.execute(
                "SELECT * FROM transactions WHERE type=? ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                (type, limit, offset)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM transactions ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                (limit, offset)
            ).fetchall()
    return [dict(r) for r in rows]


@app.get("/summary", dependencies=[Depends(verify_api_key)])
def get_summary():
    with get_db() as conn:
        totals = conn.execute("""
            SELECT
                SUM(CASE WHEN type='debit'  THEN amount ELSE 0 END) AS total_spent,
                SUM(CASE WHEN type='credit' THEN amount ELSE 0 END) AS total_received,
                COUNT(*) AS total_transactions
            FROM transactions
        """).fetchone()

        monthly = conn.execute("""
            SELECT
                strftime('%Y-%m', timestamp) AS month,
                SUM(CASE WHEN type='debit'  THEN amount ELSE 0 END) AS spent,
                SUM(CASE WHEN type='credit' THEN amount ELSE 0 END) AS received
            FROM transactions
            GROUP BY month
            ORDER BY month DESC
            LIMIT 12
        """).fetchall()

        top_merchants = conn.execute("""
            SELECT merchant, SUM(amount) AS total, COUNT(*) AS count
            FROM transactions
            WHERE type='debit' AND merchant IS NOT NULL
            GROUP BY merchant
            ORDER BY total DESC
            LIMIT 10
        """).fetchall()

    return {
        "totals": dict(totals),
        "monthly": [dict(r) for r in monthly],
        "top_merchants": [dict(r) for r in top_merchants],
    }


@app.post("/transactions", dependencies=[Depends(verify_api_key)])
def add_transaction(txn: TransactionIn):
    ts = txn.timestamp or datetime.utcnow().isoformat()
    data = {
        "amount": txn.amount, "type": txn.type, "merchant": txn.merchant,
        "upi_ref": txn.upi_ref, "account": txn.account, "balance": txn.balance,
        "raw_sms": None, "timestamp": ts
    }
    _save_transaction(data)
    return {"status": "ok"}


@app.delete("/transactions/{txn_id}", dependencies=[Depends(verify_api_key)])
def delete_transaction(txn_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM transactions WHERE id=?", (txn_id,))
    return {"status": "ok"}
