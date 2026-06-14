# OptiFlow — AI-Powered Order Management System

An internal operations platform for eyewear companies. Manages the full order lifecycle from prescription intake to delivery, with ML-based SLA breach prediction, AI-powered explanations via Gemini, inventory forecasting, and an operations copilot.

---

## Features

- **Order Pipeline** — Full lifecycle tracking with QC failure workflow and timeline
- **Inventory Management** — Stock allocation on order creation, low-stock alerts, restocking
- **SLA Breach Prediction** — Random Forest classifier scoring each order 0–100%
- **AI Explanation Engine** — Gemini-generated risk analysis for high-risk orders
- **AI Operations Copilot** — Natural language Q&A over live order and inventory data
- **Inventory Forecasting** — Predicted stockout dates and reorder suggestions
- **Action Center** — Consolidated view of high-risk orders with recommended actions
- **Analytics Dashboard** — Chart.js visualisations for status, SLA, QC trends, store performance

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Flask 3, SQLAlchemy, Flask-Migrate |
| Database | SQLite (dev), PostgreSQL (prod) |
| Frontend | Jinja2, Bootstrap 5, Chart.js |
| AI | Google Gemini 1.5 Flash |
| ML | Scikit-Learn Random Forest |
| Deployment | Render |

---

## Local Setup

### 1. Clone and create virtual environment

```bash
git clone <repo-url>
cd optiflow
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env`:

```
FLASK_ENV=development
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///optiflow.db
GEMINI_API_KEY=your-gemini-api-key-here
```

Get a Gemini API key at: https://aistudio.google.com/app/apikey

### 3. Train the ML model

```bash
python -m app.ml.train_model
```

This generates `app/ml/sla_model.pkl`. The app runs without it (falls back to a heuristic scorer), but training takes ~5 seconds and significantly improves risk score quality.

### 4. Initialise the database and seed data

```bash
flask db init
flask db migrate -m "initial schema"
flask db upgrade
python -c "from run import app; from seed.seed_data import seed; ctx = app.app_context(); ctx.push(); seed()"
```

### 5. Run the development server

```bash
python run.py
```

Visit http://localhost:5000

---

## Project Structure

```
optiflow/
├── app/
│   ├── __init__.py          # App factory, extension init, blueprint registration
│   ├── config.py            # DevelopmentConfig / ProductionConfig
│   ├── models/
│   │   ├── order.py         # Order model with SLA helpers
│   │   ├── inventory.py     # Inventory SKU model
│   │   └── order_history.py # Per-order audit trail
│   ├── routes/
│   │   ├── dashboard.py     # / — KPIs and overview
│   │   ├── orders.py        # /orders — CRUD and status advancement
│   │   ├── inventory.py     # /inventory — stock view and restocking
│   │   ├── analytics.py     # /analytics — chart data API
│   │   └── ai.py            # /ai — copilot and action center
│   ├── services/
│   │   ├── inventory_service.py   # Stock check, allocation, restock
│   │   ├── inventory_forecast.py  # Consumption rate + stockout prediction
│   │   ├── sla_prediction.py      # Load model, predict risk score
│   │   ├── ai_explanation.py      # Gemini per-order risk explanation
│   │   └── ai_copilot.py          # Gemini operations Q&A with DB context
│   ├── ml/
│   │   ├── train_model.py   # Synthetic data generation + RF training
│   │   └── sla_model.pkl    # Trained model (generated, not committed)
│   ├── utils/
│   │   ├── logger.py        # Structured stdout logger
│   │   └── constants.py     # Lens types, statuses, SLA hours, thresholds
│   ├── templates/           # Jinja2 HTML templates
│   └── static/              # CSS and JS assets
├── seed/
│   └── seed_data.py         # 500 orders + inventory + history
├── run.py                   # Entry point
├── requirements.txt
└── .env.example
```

---

## Deployment on Render

### 1. Push to GitHub

```bash
git init
git add .
git commit -m "initial commit"
git remote add origin <your-github-repo>
git push -u origin main
```

### 2. Create a Render Web Service

1. Go to https://render.com → New → Web Service
2. Connect your GitHub repo
3. Set the following:

| Setting | Value |
|---|---|
| Build Command | `pip install -r requirements.txt && python -m app.ml.train_model` |
| Start Command | `gunicorn run:app` |
| Instance Type | Free or Starter |

### 3. Add environment variables in Render dashboard

```
FLASK_ENV=production
SECRET_KEY=<generate a strong random key>
GEMINI_API_KEY=<your key>
DATABASE_URL=<your PostgreSQL URL from Render's DB service>
```

### 4. Create a PostgreSQL database on Render

1. New → PostgreSQL
2. Copy the **External Database URL** into `DATABASE_URL` above

### 5. Run migrations and seed (one-time via Render Shell)

In the Render dashboard → Shell tab:

```bash
flask db upgrade
python -c "from run import app; from seed.seed_data import seed; ctx = app.app_context(); ctx.push(); seed()"
```

---

## Adding a Gemini API Key

The system degrades gracefully without a Gemini key:
- Order risk explanations fall back to rule-based text
- Copilot returns a configuration error message
- All other features (ML scoring, inventory, analytics) work normally

---

## Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | Yes | Flask session secret |
| `DATABASE_URL` | Yes | SQLAlchemy DB URI |
| `GEMINI_API_KEY` | Recommended | Google Gemini API key |
| `FLASK_ENV` | No | `development` or `production` |
| `LOG_LEVEL` | No | `INFO`, `DEBUG`, `WARNING` |

---

## Development Notes

- The ML model trains on synthetic data that mirrors the heuristic scorer. In production, retrain monthly on real order outcomes for accurate SLA predictions.
- The copilot injects a live DB snapshot (up to 20 high-risk orders) into each Gemini prompt. For very large datasets, consider caching this snapshot.
- `flask db migrate` must be re-run whenever models change.
