import os
import requests
from datetime import datetime
from app.models.order import Order
from app.models.inventory import Inventory
from app.utils.logger import get_logger
from app.utils.constants import ACTIVE_STATUSES

logger = get_logger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama3-8b-8192"


def _call_groq(prompt: str) -> str:
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        return None

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.4,
        "max_tokens": 1024,
    }

    response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)

    if response.status_code != 200:
        raise Exception(f"Groq API returned {response.status_code}: {response.text[:300]}")

    return response.json()["choices"][0]["message"]["content"]


def _build_context_snapshot() -> str:
    from app import db
    from sqlalchemy import func

    total_active = Order.query.filter(Order.current_status.in_(ACTIVE_STATUSES)).count()
    high_risk = Order.query.filter(Order.risk_score >= 71).all()
    sla_breaches = Order.query.filter(
        Order.expected_delivery < datetime.utcnow(),
        Order.current_status.in_(ACTIVE_STATUSES),
    ).count()
    low_stock = Inventory.query.filter(
        Inventory.quantity_available <= Inventory.reorder_threshold,
        Inventory.quantity_available > 0,
    ).count()
    out_of_stock = Inventory.query.filter(Inventory.quantity_available == 0).count()

    risk_summaries = []
    for o in high_risk[:20]:
        risk_summaries.append(
            f"  - {o.order_id}: {o.lens_type}, {o.store_location}, "
            f"Status={o.current_status}, Risk={o.risk_score}%, "
            f"Reason={o.delay_reason or 'N/A'}"
        )

    store_delays = (
        db.session.query(Order.store_location, func.count(Order.id))
        .filter(Order.risk_score >= 71)
        .group_by(Order.store_location)
        .order_by(func.count(Order.id).desc())
        .limit(5)
        .all()
    )
    store_summary = "\n".join(f"  - {s}: {c} high-risk orders" for s, c in store_delays)

    return f"""
=== OPTIFLOW OPERATIONS SNAPSHOT ({datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}) ===
ACTIVE ORDERS: {total_active}
SLA BREACHES (overdue): {sla_breaches}
HIGH RISK ORDERS (risk >= 71%): {len(high_risk)}
LOW STOCK SKUs: {low_stock}
OUT OF STOCK SKUs: {out_of_stock}

HIGH RISK ORDER DETAILS:
{chr(10).join(risk_summaries) or '  None currently'}

TOP STORES BY DELAY COUNT:
{store_summary or '  No data'}
"""


def answer_copilot_query(user_question: str) -> str:
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        return "AI Copilot is not configured. Please set the GROQ_API_KEY environment variable."

    context = _build_context_snapshot()

    prompt = f"""You are OptiFlow Copilot, an intelligent operations assistant for an eyewear company.
You have access to live operational data shown below.

{context}

Answer the following question based on the data above.
Be concise, specific, and actionable.

User question: {user_question}"""

    try:
        return _call_groq(prompt).strip()
    except Exception as e:
        logger.error("Copilot query failed: %s", e)
        return f"Copilot error: {str(e)}"
