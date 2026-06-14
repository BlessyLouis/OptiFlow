import os
import json
from datetime import datetime, timedelta
import google.generativeai as genai
from app.models.order import Order
from app.models.inventory import Inventory
from app.utils.logger import get_logger
from app.utils.constants import ACTIVE_STATUSES

logger = get_logger(__name__)

_client_configured = False


def _ensure_configured():
    global _client_configured
    if not _client_configured:
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if api_key:
            genai.configure(api_key=api_key)
            _client_configured = True


def _build_context_snapshot() -> str:
    """Gather live data from the DB to inject into the copilot prompt."""
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

    # Summarise high-risk orders for the context
    risk_summaries = []
    for o in high_risk[:20]:  # Cap at 20 to keep context reasonable
        risk_summaries.append(
            f"  - {o.order_id}: {o.lens_type}, {o.store_location}, "
            f"Status={o.current_status}, Risk={o.risk_score}%, "
            f"Reason={o.delay_reason or 'N/A'}"
        )

    # Store-wise delay count
    from app import db
    from sqlalchemy import func
    store_delays = (
        db.session.query(Order.store_location, func.count(Order.id))
        .filter(Order.risk_score >= 71)
        .group_by(Order.store_location)
        .order_by(func.count(Order.id).desc())
        .limit(5)
        .all()
    )
    store_summary = "\n".join(f"  - {s}: {c} high-risk orders" for s, c in store_delays)

    context = f"""
=== OPTIFLOW OPERATIONS SNAPSHOT (as of {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}) ===

ACTIVE ORDERS: {total_active}
SLA BREACHES (overdue): {sla_breaches}
HIGH RISK ORDERS (risk ≥71%): {len(high_risk)}
LOW STOCK SKUs: {low_stock}
OUT OF STOCK SKUs: {out_of_stock}

HIGH RISK ORDER DETAILS:
{chr(10).join(risk_summaries) or '  None currently'}

TOP STORES BY DELAY COUNT:
{store_summary or '  No data'}
"""
    return context


def answer_copilot_query(user_question: str) -> str:
    """
    Take a free-form operations question, inject live DB context,
    and return a Gemini-generated answer.
    """
    _ensure_configured()

    context = _build_context_snapshot()

    system_prompt = f"""You are OptiFlow Copilot, an intelligent operations assistant for an eyewear company's order management system. You have access to live operational data.

{context}

Answer the user's question based strictly on the data above. Be concise, actionable, and specific. If a question cannot be answered from the available data, say so clearly. Do not hallucinate order details not present in the data."""

    if not _client_configured:
        return (
            "AI Copilot is not configured. Please set the GEMINI_API_KEY environment variable to enable this feature."
        )

    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(f"{system_prompt}\n\nUser question: {user_question}")
        return response.text.strip()
    except Exception as e:
        logger.error("Copilot query failed: %s", e)
        return f"The AI copilot encountered an error: {str(e)}. Please try again."
