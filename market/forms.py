from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, FileField, IntegerField, SelectField
from wtforms_alchemy.fields import QuerySelectField
from wtforms.validators import Length, EqualTo, Email, DataRequired, ValidationError
from market.models import User, Products
from market import db, app

with app.app_context():
    db.create_all()

class RegisterForm(FlaskForm):
    def validate_username(self, username_to_check):
            user = User.query.filter_by(username=username_to_check.data).first()
            if user:
                raise ValidationError('Username already exists. Please try a different Username.')

    def validate_email_address(self, email_address_to_check):
            email_address = User.query.filter_by(email_address=email_address_to_check.data).first()
            if email_address:
                raise ValidationError('Email address already in use. Please use a different email address.')

    username = StringField(label='User Name', validators=[Length(min=2, max=30), DataRequired()])
    email_address = StringField(label='Email address', validators=[Email(), DataRequired()])
    password1 = PasswordField(label='Password:', validators=[Length(min=6), DataRequired()])
    password2 = PasswordField(label='Confirm Password:', validators=[EqualTo('password1'), DataRequired()])
    submit = SubmitField(label='Create Account')

class LoginForm(FlaskForm):
    username = StringField(label='User Name:', validators=[DataRequired()])
    password = StringField(label='Password:', validators=[DataRequired()])
    submit = SubmitField(label='Sign in')

class NewProductForm(FlaskForm):
    def validate_new_product_name(self, product_name_to_check): #functions thanks to validators, checks the form field name after validate_ in the following form
        product = Products.query.filter_by(product_name=product_name_to_check.data).first()
        print(product)
        if product:
            raise ValidationError('Product already in inventory. Please use a different name or add new batch to inventory.')

    new_product_name = StringField(label='New product name', validators=[DataRequired()])
    new_product_description = StringField(label='Description (max. 25 charachters)', validators=[Length(max=25), DataRequired()])
    new_product_price = StringField(label='New product price', validators=[DataRequired()])
    new_product_image = FileField(label='Upload image')
    submit = SubmitField(label='Add new product')

class InventoryForm(FlaskForm): #to be fixed, find way to remove app context

    def get_products():
        with app.app_context():
            return Products.query

    product = QuerySelectField('Products currently for sale', query_factory = get_products, get_label="product_name" )
    quantity = IntegerField(label='Amount of units of selected product', validators=[DataRequired()])
    submit = SubmitField(label='Add new product')

class DetailedDescriptionForm(FlaskForm):
    product_id = IntegerField(label='Product id', validators=[DataRequired()])
    basic_description = StringField(label='Description', validators=[Length(max=25), DataRequired()])
    detailed_description = StringField(label='Detailed description', validators=[Length(max=300), DataRequired()])
    submit = SubmitField(label='Save description')

class BuyForm(FlaskForm):
    product_id = IntegerField(label='Product id', validators=[DataRequired()], render_kw={'style': 'display:none;'})
    product_units_to_buy = IntegerField(label='How many units do you want to purchase ?', validators=[DataRequired()])
    product_units_available = IntegerField(label='Units available', validators=[DataRequired()], render_kw={'style': 'display:none;'})
    submit = SubmitField(label='Add to cart')

class SCForm(FlaskForm):
    product_id = IntegerField(label='Product id', validators=[DataRequired()], render_kw={'style': 'display:none;'})
    product_units_in_sc = IntegerField(label='Do you want to change the amount of units ?', validators=[DataRequired()])
    submit_remove = SubmitField(label='Remove')
    submit_change = SubmitField(label='Change quantity')

class SubmitOrderForm(FlaskForm):
    submit = SubmitField(label='Confirm Order')

class UserDetailsForm(FlaskForm):
    #user_id = IntegerField(label='User id', validators=[DataRequired()], render_kw={'style': 'display:none;'})
    phone_number = StringField(label='Phone Number', validators=[Length(max=15), DataRequired()])
    address_city = StringField(label='City', validators=[Length(max=25), DataRequired()])
    address_street = StringField(label='Street (Address)', validators=[Length(max=30), DataRequired()])
    address_street_optional = StringField(label='Additional info (Optional)', validators=[Length(max=30)])
    address_postal_code = StringField(label='Postal Code', validators=[Length(max=7), DataRequired()])
    address_country = StringField(label='Country', validators=[Length(max=15), DataRequired()])
    submit = SubmitField(label='Confirm Data')

class OrderStatusChange(FlaskForm):
    submit_in_progress = SubmitField(label='Set order status "In Progress"')
    submit_shipped = SubmitField(label='Set order status "Shipped"') 
