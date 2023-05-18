from market import db, app, login_manager
from market import bcrypt
from flask_login import UserMixin
import datetime

with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer(), primary_key=True)
    username = db.Column(db.String(length=30), nullable=False, unique=True)
    email_address = db.Column(db.String(length=40), nullable=False, unique=True)
    password_hash = db.Column(db.String(length=60), nullable=False)
    admin_role = db.Column(db.Boolean, default=False, nullable=False)
    #link to user details

    @property
    def password(self):
        return self.password

    @password.setter
    def password(self, plain_text_password):
        self.password_hash = bcrypt.generate_password_hash(plain_text_password).decode('utf-8')

    def check_password_correction(self, attempted_password):
        return bcrypt.check_password_hash(self.password_hash, attempted_password)

class User_details(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    phone_number = db.Column(db.String(length=15), nullable=False, unique=False)
    address_city = db.Column(db.String(length=25), nullable=False, unique=False)
    address_street = db.Column(db.String(length=30), nullable=False, unique=False)
    address_street_optional = db.Column(db.String(length=30), nullable=True, unique=False)
    address_postal_code = db.Column(db.String(length=7), nullable=False, unique=False)
    address_country = db.Column(db.String(length=15), nullable=False, unique=False)
    #link to user

class Products(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    product_name = db.Column(db.String(length=25), nullable=False, unique=True)
    product_description = db.Column(db.String(length=25), nullable=False, unique=False) #evaluate charachters limit
    product_price = db.Column(db.Integer, nullable=False, unique=False)
    product_image = db.Column(db.String(length=20), nullable=True, unique=False)
    orders = db.relationship('OrderProduct', backref=db.backref('products', lazy=True))
    #link to inventory

class Inventory(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    quantity_units = db.Column(db.Integer(), nullable=False, unique=False)
    batch = db.Column(db.DateTime, default=datetime.datetime.now)

class Products_detailed_description(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    detailed_description = db.Column(db.String(length=300), nullable=False, unique=False)

class Shopping_cart(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer(), db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer(), nullable=False)
    batch = db.Column(db.DateTime)

    user = db.relationship('User', backref=db.backref('shopping_cart', uselist=False))
    product = db.relationship('Products', backref=db.backref('shopping_cart_items', lazy=True))

    def batch_is_in_inventory(self):
        inventory_item = Inventory.query.filter_by(product_id=self.product_id, batch=self.batch).first()
        if inventory_item:
            return True
        else:
            return False

    def move_batch_back_to_inventory(self, units_to_increase):
        inventory_item = Inventory.query.filter_by(product_id=self.product_id, batch=self.batch).first()
        inventory_item.quantity_units += units_to_increase
        if self.quantity == units_to_increase:
            db.session.delete(self)
        else:
            self.quantity -= units_to_increase
            db.session.commit()

    def inventory_to_shopping_cart(self, open_quantity, selected_product_id, current_user):
        while open_quantity > 0:
            product_in_sc = Shopping_cart.query.filter_by(product_id=selected_product_id).filter_by(user_id=current_user.id).all()
            last_batch = Inventory.query.filter_by(product_id=selected_product_id).order_by(Inventory.batch).first()
            batches_in_sc = [item.batch for item in product_in_sc]
            if last_batch.batch not in batches_in_sc:
                if last_batch.quantity_units <= open_quantity:
                    current_order_sc = Shopping_cart(user_id = current_user.id,
                                                     product_id = selected_product_id,
                                                     quantity = last_batch.quantity_units,
                                                     batch = last_batch.batch)
                    db.session.add(current_order_sc)
                    db.session.delete(last_batch)
                    db.session.commit()
                    open_quantity -= last_batch.quantity_units
                else:
                    current_order_sc = Shopping_cart(user_id = current_user.id,
                                                     product_id = selected_product_id,
                                                     quantity = open_quantity,
                                                     batch = last_batch.batch)
                    last_batch.quantity_units -= open_quantity
                    db.session.add(current_order_sc)
                    db.session.commit()
                    open_quantity = 0
            else:
                if last_batch.quantity_units <= open_quantity:
                    batch_already_in_sc = Shopping_cart.query.filter_by(batch=last_batch.batch).first()
                    batch_already_in_sc.quantity += last_batch.quantity_units
                    db.session.delete(last_batch)
                    db.session.commit()
                    open_quantity -= last_batch.quantity_units
                else:
                    batch_already_in_sc = Shopping_cart.query.filter_by(batch=last_batch.batch).first()
                    batch_already_in_sc.quantity += open_quantity
                    last_batch.quantity_units -= open_quantity
                    db.session.commit()
                    open_quantity = 0

    def reduce_quantity_in_sc(self, open_quantity, selected_product_id, current_user):
        while open_quantity > 0:
            product_in_sc = Shopping_cart.query.filter_by(product_id=selected_product_id).filter_by(user_id=current_user.id).first()
            if open_quantity >= product_in_sc.quantity:
                if self.batch_is_in_inventory():
                    self.move_batch_back_to_inventory(product_in_sc.quantity)
                    open_quantity -= product_in_sc.quantity
                    db.session.commit()
                else:
                    batch_to_move_to_inventory = Inventory(product_id=product_in_sc.product_id,
                                                           quantity_units=product_in_sc.quantity,
                                                           batch=product_in_sc.batch)
                    db.session.add(batch_to_move_to_inventory)
                    db.session.delete(product_in_sc)
                    db.session.commit()
            else:
                if self.batch_is_in_inventory():
                    self.move_batch_back_to_inventory(open_quantity)
                    open_quantity = 0
                    db.session.commit()
                else:
                    batch_to_move_to_inventory = Inventory(product_id=product_in_sc.product_id,
                                                           quantity_units=open_quantity,
                                                           batch=product_in_sc.batch)
                    db.session.add(batch_to_move_to_inventory)
                    product_in_sc.quantity -= open_quantity
                    open_quantity = 0
                    db.session.commit()




class Orders(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('user.id'), nullable=False)
    order_date = db.Column(db.DateTime, default=datetime.datetime.now())
    order_status = db.Column(db.String(length=15), nullable=False, unique=False, default="Open")
    total_cost = db.Column(db.Integer(), nullable=False, unique=False)
    products = db.relationship('OrderProduct', backref=db.backref('orders', lazy=True))

class OrderProduct(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    order_id = db.Column(db.Integer(), db.ForeignKey('orders.id'), nullable=True)
    product_id = db.Column(db.Integer(), db.ForeignKey('products.id'), nullable=True)
    quantity = db.Column(db.Integer(), nullable=False)
