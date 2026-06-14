from flask import Blueprint, render_template, request, jsonify
from app.models.order import Order
from app.services.ai_copilot import answer_copilot_query
from app.services.ai_explanation import generate_order_explanation
from app.utils.logger import get_logger

bp = Blueprint("ai", __name__, url_prefix="/ai")
logger = get_logger(__name__)


@bp.route("/copilot")
def copilot():
    suggested_queries = [
        "Which orders are likely to breach SLA this week?",
        "Which store has the highest number of delays?",
        "What inventory should be reordered urgently?",
        "Show me all orders with QC failures.",
        "Summarise the current operational status.",
    ]
    return render_template("copilot.html", suggested_queries=suggested_queries)


@bp.route("/copilot/ask", methods=["POST"])
def copilot_ask():
    data = request.get_json()
    if not data or not data.get("question"):
        return jsonify({"error": "No question provided."}), 400

    question = data["question"].strip()
    if len(question) > 500:
        return jsonify({"error": "Question too long (max 500 chars)."}), 400

    logger.info("Copilot query: %s", question[:100])
    answer = answer_copilot_query(question)
    return jsonify({"answer": answer})


@bp.route("/action-center")
def action_center():
    """Display high-risk orders with AI-generated recommendations."""
    high_risk_orders = (
        Order.query.filter(Order.risk_score >= 71)
        .order_by(Order.risk_score.desc())
        .limit(30)
        .all()
    )

    # Pre-generate explanations for the top 10 to keep page load reasonable
    enriched = []
    for order in high_risk_orders[:3]:
        explanation = generate_order_explanation(order)
        enriched.append({"order": order, "explanation": explanation})

    # Rest shown without AI explanation (they can be loaded on demand)
    remaining = high_risk_orders[10:]

    return render_template(
        "action_center.html",
        enriched=enriched,
        remaining=remaining,
    )


@bp.route("/explain/<order_id>")
def explain_order(order_id):
    """JSON endpoint to fetch AI explanation for a single order."""
    order = Order.query.filter_by(order_id=order_id).first_or_404()
    explanation = generate_order_explanation(order)
    return jsonify(explanation)
