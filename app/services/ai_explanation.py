import os
import requests
from app.utils.logger import get_logger

logger = get_logger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"


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
        "temperature": 0.3,
        "max_tokens": 512,
    }

    response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)

    if response.status_code != 200:
        raise Exception(f"Groq API returned {response.status_code}: {response.text[:300]}")

    return response.json()["choices"][0]["message"]["content"]


def generate_order_explanation(order) -> dict:
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        return _fallback_explanation(order)

    prompt = f"""You are an operations analyst for an eyewear company. Analyze this order and explain the risk.

Order ID: {order.order_id}
Customer: {order.customer_name}
Store: {order.store_location}
Lens Type: {order.lens_type}
Prescription: {order.prescription_power}
Coating: {order.coating}
Status: {order.current_status}
QC Failures: {order.qc_failure_count}
Inventory Available: {order.inventory_available}
Risk Score: {order.risk_score}%
Delay Reason: {order.delay_reason or 'None'}

Respond in exactly this format (plain text only, no markdown):
REASON: [one sentence why the order is at risk]
ACTION: [one specific recommended action]
IMPACT: [expected impact if action taken]"""

    try:
        text = _call_groq(prompt)
        return _parse_explanation(text)
    except Exception as e:
        logger.error("Explanation failed for %s: %s", order.order_id, e)
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
        reasons.append(f"{order.qc_failure_count} QC failure(s) extended processing time")
    if order.current_status in ("QC Failed", "Reorder Generated"):
        reasons.append("order is in rework cycle")

    reason = "Order {} is at risk because {}.".format(
        order.order_id,
        " and ".join(reasons) if reasons else "multiple operational factors are contributing to delay"
    )
    return {
        "reason": reason,
        "recommended_action": "Expedite lens procurement and prioritize QC re-inspection.",
        "expected_impact": "Timely action could reduce delay by 1-2 days and prevent SLA breach.",
    }
