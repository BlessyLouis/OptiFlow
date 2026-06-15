import os
from google import genai
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _get_client():
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)


def generate_order_explanation(order) -> dict:
    client = _get_client()

    if not client:
        return _fallback_explanation(order)

    prompt = f"""You are an operations analyst for an eyewear company. Analyze this order and explain the risk.

Order ID: {order.order_id}
Customer: {order.customer_name}
Store: {order.store_location}
Lens Type: {order.lens_type}
Prescription Power: {order.prescription_power}
Coating: {order.coating}
Current Status: {order.current_status}
QC Failures: {order.qc_failure_count}
Inventory Available: {order.inventory_available}
Risk Score: {order.risk_score}%
Delay Reason: {order.delay_reason or 'None recorded'}

Respond in exactly this format (plain text, no markdown):
REASON: [one sentence explaining why the order is at risk]
ACTION: [one specific recommended action]
IMPACT: [expected business impact if action is taken]"""

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        return _parse_explanation(response.text)
    except Exception as e:
        logger.error("Gemini explanation failed for order %s: %s", order.order_id, e)
        return _fallback_explanation(order)


def _parse_explanation(text: str) -> dict:
    result = {"reason": "", "recommended_action": "", "expected_impact": ""}
    for line in text.strip().splitlines():
        if line.startswith("REASON:"):
            result["reason"] = line.replace("REASON:", "").strip()
        elif line.startswith("ACTION:"):
            result["recommended_action"] = line.replace("ACTION:", "").strip()
        elif line.startswith("IMPACT:"):
            result["expected_impact"] = line.replace("IMPACT:", "").strip()
    return result


def _fallback_explanation(order) -> dict:
    reasons = []
    if not order.inventory_available:
        reasons.append("required lens is unavailable in-house")
    if order.qc_failure_count > 0:
        reasons.append(f"{order.qc_failure_count} QC failure(s) have extended processing time")
    if order.current_status in ("QC Failed", "Reorder Generated"):
        reasons.append("order is currently in rework cycle")

    reason = "Order {} is at risk because {}".format(
        order.order_id,
        " and ".join(reasons) if reasons else "multiple operational factors are contributing to delay"
    )
    return {
        "reason": reason,
        "recommended_action": "Expedite lens procurement and prioritize QC re-inspection.",
        "expected_impact": "Timely action could reduce delay by 1-2 days and prevent SLA breach.",
    }
