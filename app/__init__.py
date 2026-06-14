from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()


def create_app(config=None):
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # Load configuration
    if config is None:
        from app.config import get_config
        config = get_config()
    app.config.from_object(config)

    # Initialise extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Register blueprints
    from app.routes.dashboard import bp as dashboard_bp
    from app.routes.orders import bp as orders_bp
    from app.routes.inventory import bp as inventory_bp
    from app.routes.analytics import bp as analytics_bp
    from app.routes.ai import bp as ai_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(ai_bp)

    # Import models so Flask-Migrate can detect them
    from app.models import Order, Inventory, OrderHistory  # noqa: F401

    # Jinja2 globals
    from datetime import datetime
    app.jinja_env.globals["now"] = datetime.utcnow

    return app
