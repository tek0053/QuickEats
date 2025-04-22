from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def init_app(app):
    # Configure the DB here or in app.py
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_BINDS'] = {
        'db': "sqlite:///clothing_store.sqlite"
    }
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///clothing_store.sqlite'

    db.init_app(app)
    app.logger.info('Initialized models')

    with app.app_context():
        from .user import User
        from .food_category import FoodCategory
        from .menu_item import MenuItem
        from .order import Order
        from .order_item import OrderItem
        from .review import Review

        db.create_all()
        db.session.commit()
        app.logger.debug('All tables are created')
