from datetime import datetime, timedelta
from market import app
from market import db
from flask import render_template, redirect, url_for, flash, request
from sqlalchemy import func
from market.models import User, Products, Inventory, Products_detailed_description, Shopping_cart, Orders, OrderProduct, User_details
from market.forms import RegisterForm, LoginForm, NewProductForm, InventoryForm, DetailedDescriptionForm, BuyForm, SCForm, SubmitOrderForm, UserDetailsForm, OrderStatusChange
from flask_uploads import configure_uploads, IMAGES, UploadSet
from wtforms.validators import ValidationError
import plotly.graph_objs as go
import random


from flask_login import login_user, logout_user, login_required, current_user

import logging



with app.app_context():
    db.create_all()

#Page that display home page view
@app.route('/')
@app.route('/home', methods=['GET'])
def home_page():
    #query that retrieves 2 random products to display in home page
    products = Products.query.all()
    random_products = random.sample(products, 2)


    return render_template('home.html', random_products=random_products)

#Page that display view register a user
@app.route('/register', methods=['GET', 'POST'])
def register_page():
    form = RegisterForm()
    if form.validate_on_submit(): # In background checks if all data required is input and if submit is pressed, True
        user_to_create = User(username=form.username.data,
                                email_address=form.email_address.data,
                                password=form.password1.data)
        db.session.add(user_to_create)
        db.session.commit()
        login_user(user_to_create)
        flash(f'Account successfully created, you are now logged in as: {user_to_create.username}', category='success')

        return redirect(url_for('register_additional_page'))
    if form.errors != {}: #if no errors from validations
        for err_msg in form.errors.values():
            flash(f'There was an error while creating a user: {err_msg}', category='danger')
    return render_template('register.html', form=form)

#Page that display view to add aditional data for registration process
@app.route('/register/additional_data', methods=['GET', 'POST'])
@login_required
def register_additional_page():
    form = UserDetailsForm()
    if form.validate_on_submit(): # In background checks if all data required is input and if submit is pressed, True
        additional_data_to_create = User_details(user_id=current_user.id,
                                         phone_number=form.phone_number.data,
                                         address_city=form.address_city.data,
                                         address_street=form.address_street.data,
                                         address_street_optional=form.address_street_optional.data,
                                         address_postal_code=form.address_postal_code.data,
                                         address_country=form.address_country.data)

        db.session.add(additional_data_to_create)
        db.session.commit()
        flash(f'Data Succesfully added, you can now enjoy the shopping !', category='success')

        return redirect(url_for('home_page'))
    if form.errors != {}: #if no errors from validations
        for err_msg in form.errors.values():
            flash(f'There was an error whit the info you are trying to add: {err_msg}', category='danger')
    return render_template('register_user_details.html', form=form)

#Page that display login view
@app.route('/login', methods=['GET', 'POST'])
def login_page():
    form = LoginForm()
    if form.validate_on_submit():
        attempted_user = User.query.filter_by(username=form.username.data).first()
        if attempted_user and attempted_user.check_password_correction(
            attempted_password=form.password.data
        ):
            login_user(attempted_user)
            flash(f'Success! You are logged in as: {attempted_user.username}', category='success')
            return redirect(url_for('home_page'))
        else:
            flash('Username and Passowrd not matching, please try again !', category='danger')

    return render_template('login.html', form=form)

@app.route('/logout')
def logout_page():
    logout_user()
    flash("You have been logged out!", category='info')
    return redirect(url_for("home_page"))

#Page that display all products for sale (if admin additional views)
@app.route('/products', methods=['GET', 'POST'])
@login_required
def products_page():
    products_for_sale = db.session.query(Products, Products_detailed_description,
                                      func.sum(Inventory.quantity_units).label('sum'))\
                                      .outerjoin(Products_detailed_description)\
                                      .outerjoin(Inventory, Inventory.product_id == Products.id)\
                                      .group_by(Products.id, Products_detailed_description.id)\
                                      .all()

    is_admin = current_user.admin_role
    form_description = DetailedDescriptionForm()
    form_purchase = BuyForm()

    if form_purchase.validate_on_submit():
        product_in_inventory = Inventory.query.filter_by(product_id=form_purchase.product_id.data).order_by(Inventory.batch).all()
        #in addition to check if product is already there search also by batch
        if form_purchase.product_units_to_buy.data <= form_purchase.product_units_available.data:
            # check if item already in sc, if yes add units.
            product_in_sc = Shopping_cart.query.filter_by(product_id=form_purchase.product_id.data).filter_by(user_id=current_user.id).first()
            if product_in_sc:
                # check if specific batch is in inventory
                open_quantity = form_purchase.product_units_to_buy.data
                product_in_sc.inventory_to_shopping_cart(open_quantity, form_purchase.product_id.data, current_user)

                flash(f'You added {form_purchase.product_units_to_buy.data} units of the product to the basket !', category='success')
            else:
                open_quantity = form_purchase.product_units_to_buy.data
                while open_quantity > 0:
                    # check first in batch in inventory for selcted product
                    last_batch = Inventory.query.filter_by(product_id=form_purchase.product_id.data).order_by(Inventory.batch).first()
                    if last_batch.quantity_units <= open_quantity:
                        # check last batch in inventory, if q < q user is tryin to buy, reduce, if same remove form inv, if more remove and search next batch
                        # creat items in sc according to n of batches impacted
                        # after creating items in sc, remove from inventory
                        current_order_sc = Shopping_cart(user_id = current_user.id,
                                                         product_id = form_purchase.product_id.data,
                                                         quantity = last_batch.quantity_units,
                                                         batch = last_batch.batch)
                        db.session.add(current_order_sc)
                        db.session.delete(last_batch)
                        db.session.commit()
                        open_quantity -= last_batch.quantity_units
                    else:
                        current_order_sc = Shopping_cart(user_id = current_user.id,
                                                         product_id = form_purchase.product_id.data,
                                                         quantity = open_quantity,
                                                         batch = last_batch.batch)
                        last_batch.quantity_units -= open_quantity
                        db.session.add(current_order_sc)
                        db.session.commit()
                        open_quantity = 0

                    flash(f'You added {form_purchase.product_units_to_buy.data} units of the product to the basket !', category='success')


            return redirect(url_for('products_page'))
        else:
            form_purchase.product_units_to_buy.errors.append("Error: Amount of units selected is not available, please reduce.")

        if form_purchase.errors != {}: #if no errors from validations
            for err_msg in form_purchase.errors.values():
                flash(f'There was an error while buying the product: {err_msg}', category='danger')

    if is_admin:

        if form_description.validate_on_submit():
            detailed_description_to_checked = Products_detailed_description.query.filter_by(product_id=form_description.product_id.data).first()
            if detailed_description_to_checked: #checks if detailed desc. already exist for selected product
                detailed_description_to_checked.detailed_description = form_description.detailed_description.data
                db.session.commit()
                flash('Product detailed description succesfully updated', category='success')
            else:
                detailed_description_to_be_added = Products_detailed_description(product_id=int(form_description.product_id.data),
                                                                  detailed_description=form_description.detailed_description.data)
                db.session.add(detailed_description_to_be_added)
                db.session.commit()
                flash('Product detailed description succesfully added', category='success')

            basic_description_to_checked = Products.query.filter_by(id=form_description.product_id.data).first()
            if basic_description_to_checked != form_description.basic_description.data:
                basic_description_to_checked.product_description = form_description.basic_description.data
                db.session.commit()
                flash('Product basic description succesfully updated', category='success')

            return redirect(url_for('products_page'))

        if form_description.errors != {}: #if no errors from validations
            for err_msg in form_description.errors.values():
                flash(f'There was an error while adding the product: {err_msg}', category='danger')

    return render_template('products.html', products_for_sale=products_for_sale, form_description=form_description, form_purchase=form_purchase)

images = UploadSet('images', IMAGES)
configure_uploads(app, images)

#Page that allows to create a new product
@app.route('/products/new_product', methods=['GET', 'POST'])
@login_required
def new_product_page():
    is_admin = current_user.admin_role
    if is_admin:
        form = NewProductForm()
        if form.validate_on_submit(): #in background checks if all data required is input and if submit is pressed, True
            filename = images.save(form.new_product_image.data)
            filename_for_db = str(filename)
            product_to_create = Products(product_name=form.new_product_name.data,
                                    product_description=form.new_product_description.data,
                                    product_price=form.new_product_price.data,
                                    product_image=filename_for_db)
            db.session.add(product_to_create)
            db.session.commit()
            flash(f'{product_to_create.product_name} succesfully created', category='success')

        if form.errors != {}: #if no errors from validations
            for err_msg in form.errors.values():
                flash(f'There was an error while adding the product: {err_msg}', category='danger')

        return render_template('new_product.html', form=form)

    else:
        flash('You must be an admin to access this page!', category='danger')
        return redirect(url_for('home_page'))

# Page that shows current_order
@app.route('/shopping_cart', methods=['GET', 'POST'])
@login_required
def shopping_cart_page():
    products_in_cart = db.session.query(Shopping_cart, Products).\
        join(Products, Shopping_cart.product_id == Products.id).\
        filter(Shopping_cart.user_id == current_user.id).\
        group_by(Shopping_cart.product_id).\
        with_entities(Shopping_cart, Products, func.sum(Shopping_cart.quantity).label('total_quantity')).\
        all()
    total_price = db.session.query(func.sum(Shopping_cart.quantity * Products.product_price)).\
        join(Products).\
        filter(Shopping_cart.user_id == current_user.id).\
        scalar()
    form = SCForm()
    submit_order_form = SubmitOrderForm()
    if form.validate_on_submit():
        # Remove the item from the basket
        if form.submit_remove.data:
            products_to_remove = Shopping_cart.query.filter_by(product_id=form.product_id.data).filter_by(user_id=current_user.id).all()
            for product in products_to_remove:
                if product.batch_is_in_inventory():
                    product.move_batch_back_to_inventory(product.quantity)
                else:
                    batch_to_move_to_inventory = Inventory(product_id=form.product_id.data,
                                                           quantity_units=product.quantity,
                                                           batch=product.batch)
                    db.session.add(batch_to_move_to_inventory)
                    db.session.delete(product)
            db.session.commit()
            flash('Product removed from basket !', category='success')
            return redirect(url_for('shopping_cart_page'))
        elif form.submit_change.data:
            # Update the quantity of the selceted item currently in the basket
            product_units_available = db.session.query(func.sum(Inventory.quantity_units)).filter_by(product_id=form.product_id.data).scalar()
            current_product_units = db.session.query(func.sum(Shopping_cart.quantity)).filter_by(product_id=form.product_id.data).scalar()
            product_to_be_updated = Shopping_cart.query.filter_by(product_id=form.product_id.data).first()
            new_desired_quantity = form.product_units_in_sc.data
            quantity_difference = new_desired_quantity - current_product_units
            if quantity_difference <= (product_units_available or 0):
                print(new_desired_quantity, current_product_units, quantity_difference)
                if quantity_difference > 0: # product_to_be_updated.quantity gives a wrong result as if we have multiple bathces the total quanityt is no taken in consideration, rewrite query
                # this should also fix visualization, so that we have 1 product for id with quantity sum of all bathes
                    product_to_be_updated.inventory_to_shopping_cart(quantity_difference, form.product_id.data, current_user)
                else:
                    open_quantity = abs(quantity_difference)
                    product_to_be_updated.reduce_quantity_in_sc(open_quantity, form.product_id.data, current_user)

                flash('Quantity updated !', category='success')
                return redirect(url_for('shopping_cart_page'))
            else:
                flash(f'Amounts of units selected is higher than units available. Currently we have {product_units_available} units.', category='danger')
                return redirect(url_for('shopping_cart_page'))

    if submit_order_form.validate_on_submit():
        new_order = Orders(user_id=current_user.id, total_cost=total_price)
        db.session.add(new_order)
        db.session.commit()
        print("ok unltil 1")

        bought_items = Shopping_cart.query.filter_by(user_id=current_user.id).all()

        for item in bought_items:
            print(f"check 1.5 {item.product_id}")
            new_order_product = OrderProduct(order_id=new_order.id,
                                             product_id=item.product.id,
                                             quantity=item.quantity)
            print("ok unltil 2")
            db.session.add(new_order_product)
            db.session.delete(item)
            print("ok unltil 3")

        db.session.commit()
        flash('Your order has been submitted!', 'success')
        return redirect(url_for('home_page'))



    return render_template('shopping_cart.html', products_in_cart=products_in_cart, form=form, total_price=total_price, submit_order_form=submit_order_form)

#Page that allows to see inventory overview and navigate inventory possibilities
@app.route('/inventory', methods=['GET', 'POST'])
@login_required
def inventory_page():
    is_admin = current_user.admin_role
    if is_admin:
        #products_for_sale = Products.query.all()
        inventory = Inventory.query.all()
        form = InventoryForm()
        if form.validate_on_submit():
            product_id_for_batch = print((form.product.data.id))
            batch_to_create = Inventory(product_id=form.product.data.id,
                                    quantity_units=form.quantity.data)
            db.session.add(batch_to_create)
            db.session.commit()

        products_ids = [id for id, in Products.query.with_entities(Products.id)]
        quantity = Inventory.query.with_entities(func.sum(Inventory.quantity_units).filter(Inventory.product_id == 2)).scalar()

        products_produced = Products.query.all()
        info_availability = [(product.product_name,
                              product.id,
                              Inventory.query.with_entities(func.sum(Inventory.quantity_units).filter(Inventory.product_id == product.id)).scalar())
                              for product in products_produced ]
        print(info_availability)

        return render_template('inventory.html', form=form, inventory=inventory, info_availability=info_availability)

    else:
        flash('You must be an admin to access this page!', category='danger')
        return redirect(url_for('home_page'))

#Page that allows to add new batches of products
@app.route('/inventory/new_batch', methods=['GET', 'POST'])
@login_required
def new_batch_page():
    is_admin = current_user.admin_role
    if is_admin:
        inventory = Inventory.query.all()
        form = InventoryForm()
        if form.validate_on_submit():
            product_id_for_batch = print((form.product.data.id))
            batch_to_create = Inventory(product_id=form.product.data.id,
                                    quantity_units=form.quantity.data)
            db.session.add(batch_to_create)
            db.session.commit()
            return redirect(url_for('inventory_page'))

        return render_template('new_batch.html', form=form, inventory=inventory)

    else:
        flash('You must be an admin to access this page!', category='danger')
        return redirect(url_for('home_page'))

#Page that shows a detailed inventory
@app.route('/inventory/detailed_inventory', methods=['GET'])
@login_required
def detailed_inventory_page():
    is_admin = current_user.admin_role
    if is_admin:
        inventory = Inventory.query.all()

        return render_template('detailed_inventory.html', inventory=inventory)

    else:
        flash('You must be an admin to access this page!', category='danger')
        return redirect(url_for('home_page'))

#Page that shows an admin view
@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin_page():
    is_admin = current_user.admin_role
    if is_admin:
        return render_template('admin.html')

    else:
        flash('You must be an admin to access this page!', category='danger')
        return redirect(url_for('home_page'))

#Page that shows an Users admin view
@app.route('/admin/users_list', methods=['GET', 'POST'])
@login_required
def admin_users_page():
    is_admin = current_user.admin_role
    if is_admin:
        registered_users = User.query.all()
        return render_template('admin_users_list.html', registered_users=registered_users)

    else:
        flash('You must be an admin to access this page!', category='danger')
        return redirect(url_for('home_page'))

#Page that shows an all orders (admin view)
@app.route('/admin/open_orders_list', methods=['GET', 'POST'])
@login_required
def admin_open_orders_page():
    is_admin = current_user.admin_role
    if is_admin:
        open_orders = Orders.query.filter(Orders.order_status.in_(["Open", "In progress"])).all()
        return render_template('admin_open_orders_list.html', open_orders=open_orders)

    else:
        flash('You must be an admin to access this page!', category='danger')
        return redirect(url_for('home_page'))

#Page that shows all orders for a user
@app.route('/admin/all_orders_history', methods=['GET'])
@login_required
def admin_all_orders_page():
    is_admin = current_user.admin_role
    if is_admin:
        orders = Orders.query.group_by(Orders.id).all()
        return render_template('admin_order_history.html', orders=orders)
    else:
        flash('You must be an admin to access this page!', category='danger')
        return redirect(url_for('home_page'))



#Page that shows a sales dashboard
@app.route('/admin/sales_dashboard', methods=['GET'])
@login_required
def sales_dashboard_page():
    is_admin = current_user.admin_role
    if is_admin:
        # Calculate the date range for the sales data
        today = datetime.today().date()
        start_date = today - timedelta(days=120)

        # Query the database for the sales data
        orders = Orders.query.filter(Orders.order_date >= start_date).all()
        sales_data = {}
        order_data = {}
        avg_order_data = {}
        
        for order in orders:
            date_str = order.order_date.strftime('%Y-%m-%d')

            if date_str in sales_data:
                sales_data[date_str] += order.total_cost
                order_data[date_str] += 1
            else:
                sales_data[date_str] = order.total_cost
                order_data[date_str] = 1

            # Calculate average order cost
            for date_str in sales_data:
                avg_order_data[date_str] = sales_data[date_str] / order_data[date_str]

        # Create a bar chart of the sales data
        data_sales = go.Bar(x=list(sales_data.keys()), y=list(sales_data.values()))
        layout_sales = go.Layout(title='Sales Dashboard', xaxis_title='Date', yaxis_title='Sales (in $)')
        fig_sales = go.Figure(data=[data_sales], layout=layout_sales)
        # Create a bar chart of the orders data
        data_orders = go.Bar(x=list(order_data.keys()), y=list(order_data.values()))
        layout_orders = go.Layout(title='Orders Dashboard', xaxis_title='Date', yaxis_title='Number of orders')
        fig_orders = go.Figure(data=[data_orders], layout=layout_orders)
        # Create a bar chart of the avg order value data
        data_avg_orders = go.Bar(x=list(avg_order_data.keys()), y=list(avg_order_data.values()))
        layout_avg_orders = go.Layout(title='Avg Dashboard', xaxis_title='Date', yaxis_title='Number of orders')
        fig_avg_orders = go.Figure(data=[data_avg_orders], layout=layout_avg_orders)

        return render_template('admin_sales_dashboard.html', plot_sales=fig_sales.to_html(), plot_orders=fig_orders.to_html(), plot_avg_orders=fig_avg_orders.to_html())
    else:
        flash('You must be an admin to access this page!', category='danger')
        return redirect(url_for('home_page'))

#Page that shows a products dashboard
@app.route('/admin/products_dashboard', methods=['GET'])
@login_required
def products_dashboard_page():
    is_admin = current_user.admin_role
    if is_admin:
        # Query the database for the sales data
        orders = db.session.query(OrderProduct, Products).join(Products, OrderProduct.product_id==Products.id).all()
        products_data = {}
        for order, product in orders:
            if product.product_name in products_data:
                products_data[product.product_name] += order.quantity
            else:
                products_data[product.product_name] = order.quantity

        # Create a bar chart of the product data
        data_product_sales = go.Bar(x=list(products_data.keys()), y=list(products_data.values()))
        layout_product_sales = go.Layout(title='Product Sales Dashboard', xaxis_title='Product', yaxis_title='Units Sold')
        fig_product_sales = go.Figure(data=[data_product_sales], layout=layout_product_sales)

        #Query the DB for inventory data
        inventory = db.session.query(func.sum(Inventory.quantity_units), Products).join(Products, Inventory.product_id==Products.id).group_by(Products.id).all()
        inv_data = {}
        for quantity_units, product in inventory:
            inv_data[product.product_name] = quantity_units

        # Create a bar chart of the inventory data
        data_inventory_availability = go.Bar(x=list(inv_data.keys()), y=list(inv_data.values()))
        layout_inventory_availability = go.Layout(title='Products in Inventory', xaxis_title='Product', yaxis_title='Units Available')
        fig_inventory_availability = go.Figure(data=[data_inventory_availability], layout=layout_inventory_availability)


        return render_template('admin_products_dashboard.html', plot_products_sales=fig_product_sales.to_html(), plot_inventory=fig_inventory_availability.to_html())
    else:
        flash('You must be an admin to access this page!', category='danger')
        return redirect(url_for('home_page'))

#Page that shows an Users details view
@app.route('/user/details', methods=['GET', 'POST'])
@login_required
def user_details_page():
    is_admin = current_user.admin_role
    if is_admin:
        registered_users = User.query.all()
        return render_template('admin_users_list.html', registered_users=registered_users)

    else:
        flash('You must be an admin to access this page!', category='danger')
        return redirect(url_for('home_page'))

#Page that shows an Users personal view
@app.route('/user', methods=['GET', 'POST'])
@login_required
def user_page():

    orders = Orders.query.filter_by(user_id=current_user.id).group_by(Orders.id).all()
    last_five_orders = list(reversed(orders[-5:]))
    personal_details = User_details.query.filter_by(user_id=current_user.id).first()

    return render_template('user.html', orders=orders, last_five_orders=last_five_orders, personal_details=personal_details)

#Page that shows all orders for a user
@app.route('/user/orders_history', methods=['GET', 'POST'])
@login_required
def user_all_orders_page():

    orders = Orders.query.filter_by(user_id=current_user.id).group_by(Orders.id).all()

    return render_template('user_order_history.html', orders=orders)

#Page that shows personal details for a user/if admin, allows to see details of a selected user
@app.route('/user/personal_details', methods=['GET', 'POST'])
@login_required
def personal_details_page():

    is_admin = current_user.admin_role
    if is_admin:
        user_id = request.args.get('user_id')
        username = request.args.get('username')
        personal_details = User_details.query.filter_by(user_id=user_id).first()

        return render_template('user_personal_details.html', personal_details=personal_details, username=username)

    else:
        personal_details = User_details.query.filter_by(user_id=current_user.id).first()

    return render_template('user_personal_details.html', personal_details=personal_details)

#Page that allow to update personal details for a user
@app.route('/user/modify_personal_details', methods=['GET', 'POST'])
@login_required
def modify_personal_details_page():

    personal_details = User_details.query.filter_by(user_id=current_user.id).first()

    form = UserDetailsForm()

    if form.validate_on_submit():
        personal_details.phone_number = form.phone_number.data
        personal_details.address_city = form.address_city.data
        personal_details.address_street = form.address_street.data
        personal_details.address_street_optional = form.address_street_optional.data
        personal_details.address_postal_code = form.address_postal_code.data
        personal_details.address_country = form.address_country.data

        db.session.commit()

        flash('Data successfully updated !', category='success')

        return redirect(url_for('personal_details_page'))

    if form.errors != {}: #if errors from validations
        for err_msg in form.errors.values():
            flash(f'There was an error while updating the data: {err_msg}', category='danger')

    return render_template('user_modify_personal_details.html', personal_details=personal_details, form=form)

#Page that shows the details of an existing order
@app.route('/order_details', methods=['GET', 'POST'])
@login_required
def order_details_page():
    order_id = request.args.get('order_id')

    order_details = OrderProduct.query.filter_by(order_id=order_id).all()

    products_ordered = [Products.query.get(order.product_id) for order in order_details]

    is_admin = current_user.admin_role
    if is_admin:
        user_id = request.args.get('user_id')
        user_info = User.query.filter_by(id=user_id).first()
        user_details = User_details.query.filter_by(user_id=user_id).first()

        form = OrderStatusChange()

        if form.validate_on_submit():
            order_to_be_updated = Orders.query.filter_by(id=order_id).first()
            print(order_to_be_updated)
            if form.submit_in_progress.data:
                order_to_be_updated.order_status = "In progress"
            if form.submit_shipped.data:
                order_to_be_updated.order_status = "Shipped"

            db.session.commit()
            return redirect(url_for('admin_open_orders_page'))

    return render_template('order_details.html', order_details=order_details, products_ordered=products_ordered, order_id=order_id, user_info=user_info, user_details=user_details, form=form)

#Page that shows an admin view
@app.route('/about', methods=['GET'])
def about_page():
    return render_template('about.html')
