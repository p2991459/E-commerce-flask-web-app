# models.py
import datetime
import json
import time
import uuid
import jwt
from functools import wraps
from flask import request, jsonify, make_response
from decouple import config, Csv
from flask_login import UserMixin
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey

from . import db

from .utils import (
    str_list_to_int_list, clean_phone_number, validate_phone_number, get_productid_qty
)

BACKEND_API_SECRET_KEY = config('BACKEND_API_SECRET_KEY', default='')
TEST_ORDER_IDS = config('TEST_ORDER_IDS', cast=Csv(int), default=[])
ADMIN = config('ADMIN')
DELIVERY_LOG_STR = 'delivery_log'


def get_all_zones_with_postal_code(postal_code, order_id=None):
    all_zones = []
    if type(postal_code) == str and postal_code.strip() == '':
        return all_zones
    if order_id and 'C-' in order_id:
        print("Getting zone for %s" % order_id)
    elif order_id and int(order_id) in TEST_ORDER_IDS:
        return ["TEST"]
    postal_code = str(postal_code)
    if len(postal_code) > 5:
        postal_code = postal_code[0:5]
    zone_zips = ZoneZips.query.all()
    zone_zips_dict = {zz.zone: zz.zips for zz in zone_zips}
    for k, v in zone_zips_dict.items():
        list_v = str_list_to_int_list(v)
        try:
            if int(postal_code) in list_v:
                if k not in all_zones:
                    all_zones.append(k)
        except ValueError as ve:
            print("%s does not seem a valid postal code, not processing it." % postal_code)
            print(str(ve))
    return all_zones


class PermissionTable(db.Model):

    """Store permission related information"""
    
    __table_args__ = {'extend_existing': True}
    __tablename__ = 'permission'

    id = db.Column(db.Integer,
                   primary_key=True)  # primary keys are required by SQLAlchemy

    permission_text = db.Column(db.String(1000))
    permission_unique_text = db.Column(db.String(200))
    module_name = db.Column(db.String(100))
    updated_at = db.Column(db.Text, default=datetime.datetime.now().isoformat())


class MasterRole(db.Model):

    """Store data related to roles added by admin
    """
    
    __table_args__ = {'extend_existing': True}
    __tablename__ = 'master_role'

    id = db.Column(db.Integer,
                   primary_key=True)  # primary keys are required by SQLAlchemy

    role_name = db.Column(db.String(100), unique=True)
    updated_at = db.Column(db.Text, default=datetime.datetime.now().isoformat())


class PermissionRole(db.Model):

    """Store permission related to roles added by admin
    """
    
    __table_args__ = {'extend_existing': True}
    __tablename__ = 'permission_role'

    id = db.Column(db.Integer,
                   primary_key=True)  # primary keys are required by SQLAlchemy

    role_id = db.Column(
        db.Text, db.ForeignKey('master_role.id'),
        nullable=False
    )
    permission_id = db.Column(
        db.Text, db.ForeignKey('permission.id'),
        nullable=False
    )
    updated_at = db.Column(db.Text, default=datetime.datetime.now().isoformat())


class User(UserMixin, db.Model):
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer,
                   primary_key=True)  # primary keys are required by SQLAlchemy
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(1000))
    name = db.Column(db.String(1000))
    is_admin = db.Column(db.Integer)
    role_id = db.Column(
        db.Text, db.ForeignKey('master_role.id'),
        nullable=True
    )

    @property
    def role_name(self):
        master_role = MasterRole.query.filter_by(id=self.role_id).first()
        return master_role.role_name if master_role else ''

    @property
    def is_admin(self):
        return self.email in ADMIN


class RoutificProjects(db.Model):
    __table_args__ = {'extend_existing': True}
    fetched_datetime = db.Column(db.Text,
                                 default=datetime.datetime.now().isoformat())
    project_id = db.Column(db.Text,
                           primary_key=True)
    project_details = db.Column(db.Text)
    squarespace_product_id = db.Column(db.Text, default="")
    july_delivery = db.Column(db.Text)
    aug_delivery = db.Column(db.Text)
    sep_delivery = db.Column(db.Text)
    oct_delivery = db.Column(db.Text)
    web_form_group = db.Column(db.Text, default=datetime.datetime.now().isoformat())

    def __init__(self, project_id, project_details, squarespace_product_id,
                 web_form_group):
        self.project_id = project_id
        self.project_details = project_details
        self.squarespace_product_id = squarespace_product_id
        self.web_form_group = web_form_group


class RoutificSolutions(db.Model):
    __table_args__ = {'extend_existing': True}
    project_id = db.Column(db.Text,
                           primary_key=True)
    solution = db.Column(db.Text)


class SquarespaceCSAOrders(db.Model):
    squarespace_order_id = db.Column(db.Text,
                                     primary_key=True)
    order_id = db.Column(db.Text)
    product_id = db.Column(db.Text)
    billing_email = db.Column(db.Text)
    billing_name = db.Column(db.Text)
    item_qty = db.Column(db.Text)
    shipping_name = db.Column(db.Text)
    shipping_address1 = db.Column(db.Text)
    shipping_address2 = db.Column(db.Text)
    shipping_city = db.Column(db.Text)
    shipping_zip = db.Column(db.Text)
    shipping_state = db.Column(db.Text)
    shipping_country = db.Column(db.Text)
    shipping_phone = db.Column(db.Text)
    checkout_shipping_email = db.Column(db.Text)
    delivery_zone = db.Column(db.Text)
    apr_delivery = db.Column(db.Text)
    may_delivery = db.Column(db.Text)
    jun_delivery = db.Column(db.Text)
    jul_delivery = db.Column(db.Text)
    aug_delivery = db.Column(db.Text)
    sep_delivery = db.Column(db.Text)
    oct_delivery = db.Column(db.Text)
    personal_note = db.Column(db.Text)
    notes = db.Column(db.Text)
    order_year = db.Column(db.Text)
    squarespace_fulfillment_status = db.Column(db.Text)
    squarespace_fulfillment_date = db.Column(db.DateTime)
    created_date = db.Column(db.Text)
    multi_line_items = db.Column(db.Text)
    sales_price = db.Column(db.Text)
    order_source = db.Column(db.Text)
    delivery_details = db.Column(db.Text, default='')

    def __init__(self, squarespace_order_id, order_id, billing_email, item_qty,
                 shipping_name, shipping_address1, shipping_address2,
                 shipping_city, shipping_zip, shipping_state, shipping_country,
                 shipping_phone, checkout_shipping_email, delivery_zone,
                 apr_delivery, may_delivery, jun_delivery,
                 jul_delivery, aug_delivery, sep_delivery, oct_delivery,
                 personal_note, notes, product_id="", order_year="2020", squarespace_fulfillment_status="Unknown",
                 squarespace_fulfillment_date="", created_date="", multi_line_items="",
                 sales_price="", order_source="", billing_name=""):
        self.squarespace_order_id = squarespace_order_id
        self.order_id = order_id
        self.product_id = product_id
        self.billing_email = billing_email
        self.billing_name = billing_name
        self.item_qty = item_qty
        self.shipping_name = shipping_name
        self.shipping_address1 = shipping_address1
        self.shipping_address2 = shipping_address2
        self.shipping_city = shipping_city
        self.shipping_zip = shipping_zip
        self.shipping_state = shipping_state
        self.shipping_country = shipping_country
        self.shipping_phone = shipping_phone
        self.checkout_shipping_email = checkout_shipping_email
        self.delivery_zone = delivery_zone
        self.apr_delivery = apr_delivery
        self.may_delivery = may_delivery
        self.jun_delivery = jun_delivery
        self.jul_delivery = jul_delivery
        self.aug_delivery = aug_delivery
        self.sep_delivery = sep_delivery
        self.oct_delivery = oct_delivery
        self.personal_note = personal_note
        self.notes = notes
        self.order_year = order_year
        self.squarespace_fulfillment_status = squarespace_fulfillment_status
        self.squarespace_fulfillment_date = squarespace_fulfillment_date
        self.created_date = created_date
        self.multi_line_items = multi_line_items
        self.sales_price = sales_price
        self.order_source = order_source
        self.set_shipping()
        self.set_delivery_details()

    @property
    def product_details(self):
        product_details_list = []
        if self.multi_line_items:
            items = self.multi_line_items.split("+++")
            for item in items:
                product_id, qty = get_productid_qty(item)
                p = Product.query.filter(Product.product_id==product_id).first()
                if p:
                    product_details_list.append({'product_name': p.product_name, 'quantity': qty, 'product_id': product_id})
                else:
                    print("Product with id %s NOT FOUND" % product_id)
        return product_details_list

    @property
    def is_multi_product_order(self):
        if "+++" in self.multi_line_items:
            return True
        return False

    def set_shipping(self):
        updated_shipping = CSAShippingDetailUpdates.query.filter_by(order_id=self.order_id).order_by(CSAShippingDetailUpdates.id.desc()).first()
        if updated_shipping:
            self.shipping_name = updated_shipping.shipping_name
            self.shipping_address1 = updated_shipping.shipping_address_1
            self.shipping_address2 = updated_shipping.shipping_address_2
            self.shipping_city = updated_shipping.shipping_city
            self.shipping_zip = updated_shipping.shipping_zip
            self.shipping_state = updated_shipping.shipping_state
            self.shipping_phone = updated_shipping.shipping_phone
            self.checkout_shipping_email = updated_shipping.shipping_email
            zones = get_all_zones_with_postal_code(self.shipping_zip)
            self.delivery_zone = zones[0] if len(zones) > 0 else ''
            self.notes = updated_shipping.notes

    def set_delivery_details(self, product_details=None):
        if product_details:
            self.delivery_details = json.dumps(product_details)
        else:
            self.delivery_details = json.dumps(self.product_details)
        db.session.commit()

    def to_html_row(self):
        self.set_shipping()
        table_row = ("#############".join([
            self.order_id,
            self.delivery_zone,  # delivery_zone
            self.billing_email,
            '<br/>'.join(self.multi_line_items.split('+++') if self.multi_line_items else ''),
            self.shipping_name if self.shipping_name else "",
            self.shipping_address1 if self.shipping_address1 else "",
            self.shipping_address2 if self.shipping_address2 else "",
            self.shipping_city if self.shipping_city else "",
            self.shipping_zip,
            self.shipping_state,
            self.shipping_country,
            self.shipping_phone,
            self.checkout_shipping_email,
            str(get_delivery_dates_html(self.apr_delivery, self.order_id)),
            str(count_deliveries(self.apr_delivery)),
            self.personal_note if self.personal_note else "",
            self.notes if self.notes else "",
            self.squarespace_order_id,
            self.squarespace_fulfillment_status if self and self.squarespace_fulfillment_status else ""
        ]))
        final_table_row = "<tr><td>%s</td></tr>" % table_row.replace(
            "#############", "</td><td>")
        return final_table_row


def epoch_to_datetime(epoch, in_ms=True):
    default_ret_value = '--'
    if epoch == '':
        return default_ret_value
    try:
        if in_ms:
            epoch = epoch / 1000
        return time.strftime('%m/%d/%Y %H:%M:%S', time.localtime(epoch))
    except Exception as ex:
        print(str(ex))
        return default_ret_value


def get_stop_from_order(order, product_details=None):
    order.set_shipping()
    stop = {'name': '%s' % order.shipping_name}
    if order.shipping_address2:
        address = '%s %s, %s, %s %s, %s' % (
            order.shipping_address1,
            order.shipping_address2,
            order.shipping_city,
            order.shipping_state,
            order.shipping_zip,
            order.shipping_country
        )
    else:
        address = '%s, %s, %s %s, %s' % (
            order.shipping_address1,
            order.shipping_city,
            order.shipping_state,
            order.shipping_zip,
            order.shipping_country
        )
    stop['location'] = {'address': address}
    phone_number = clean_phone_number(order.shipping_phone)
    if phone_number:
        if validate_phone_number(phone_number):
            stop['phone_number'] = phone_number
        else:
            print("%s is not a valid phone number." % phone_number)
    if 'C-' in order.order_id:
        stop['email'] = order.shipping_email
    elif order.checkout_shipping_email is None or order.checkout_shipping_email.strip() == '':
        stop['email'] = order.billing_email
    else:
        stop['email'] = order.checkout_shipping_email
    stop['notes'] = order.personal_note
    stop['custom_notes'] = {
        'order_id': order.order_id,
        'SSOID': order.squarespace_order_id if hasattr(order, 'squarespace_order_id') else '',
        'custom_notes': '' if order.notes is None or order is None else order.notes,
        'quantity': order.item_qty,
        'product_details': json.dumps(order.product_details) if product_details is None else json.dumps(product_details)
    }
    return stop


def get_delivery_dates_html(apr_delivery, order_id):
    if apr_delivery is None or apr_delivery.strip() == "":
        return ""
    deliveries_list = json.loads(apr_delivery)
    dd_html = []
    updates_html = []
    for delivery in deliveries_list:
        if 'delivery_status' in delivery and delivery['delivery_status'] and 'status' in delivery[
            'delivery_status'] and delivery['delivery_status'][
                'status'] == 'undelivered':
            dd_html.append(
                "<span class='undelivered' title='Marked as undelivered'></span>%s" % (
                delivery['delivery_date']))
        elif 'delivery_status' in delivery and delivery['delivery_status'] and 'status' in delivery[
            'delivery_status'] and delivery['delivery_status'][
                'status'] == 'rescheduled':
            message = 'Marked as rescheduled'
            if 'delivery_status' in delivery and delivery['delivery_status'] and 'delivery_remarks' in delivery[
            'delivery_status'] and delivery['delivery_status']['delivery_remarks']:
                message = delivery['delivery_status']['delivery_remarks']
            dd_html.append(
                "<span class='rescheduled' title='%s'></span>%s" % (
                    message,
                    delivery['delivery_date'])
            )
        elif 'delivery_date' in delivery:
            delivery_date = datetime.datetime.strptime(delivery['delivery_date'], '%Y-%m-%d')
            if delivery_date >= datetime.datetime.today():
                dd_html.append(
                    "<span class='future-delivery' title='Scheduled'></span>%s&nbsp;&nbsp;<a href='#' data-value='%s-%s' class='undelivered'>x</a>" % (
                    delivery['delivery_date'], order_id,
                    delivery['routific_project_id'])
                )
            else:
                dd_html.append("<span class='delivered' title='Delivered'></span>%s&nbsp;&nbsp;<a href='#' data-value='%s-%s' class='undelivered'>x</a>" % (delivery['delivery_date'], order_id, delivery['routific_project_id']))
        elif 'shipping_location_change' in delivery:
            print("shipping_location_change")
            updates_html.append("<span title='%s -- On %s -- By %s'><i class=\"fas fa-truck-moving\"></i></span>" % (
                                delivery["shipping_location_change"]["remarks"],
                                delivery["shipping_location_change"]["at"],
                                delivery["shipping_location_change"]["by"],
                                ))
        elif 'shipping_info_change' in delivery:
            print("shipping_info_change")
            updates_html.append("<span title='%s -- On %s -- By %s'><i class=\"fas fa-address-card\"></i></span>" % (
                                delivery["shipping_info_change"]["remarks"],
                                delivery["shipping_info_change"]["at"],
                                delivery["shipping_info_change"]["by"],
                                ))
    final_html = "<ul class='ul_delivery_dates'>%s</ul>" % ("<li><div class='inner_div'>%s</div></li>" % "</div></li><li><div>".join(dd_html))

    if updates_html:
        return final_html + "<div>%s</div>" % '&nbsp;&nbsp;'.join(updates_html)
    else:
        return final_html


def count_deliveries(apr_delivery):
    if apr_delivery is None or apr_delivery.strip() == "":
        return 0
    deliveries_list = json.loads(apr_delivery)
    cnt = 0
    for delivery in deliveries_list:
        if 'delivery_date' in delivery:
            delivery_date = datetime.datetime.strptime(delivery['delivery_date'], '%Y-%m-%d')
            if 'delivery_status' in delivery and delivery['delivery_status'] and 'status' in delivery['delivery_status'] and delivery['delivery_status']['status'] == 'undelivered':
                print("Delivery status is undelivered, hence not counting")
            elif 'delivery_status' in delivery and delivery['delivery_status'] and 'status' in delivery['delivery_status'] and delivery['delivery_status']['status'] == 'rescheduled':
                print("Delivery status is/was rescheduled, not counting")
            elif delivery_date >= datetime.datetime.today():
                print("Future delivery, not counting")
            else:
                cnt += 1
    return str(cnt)


class CSAShippingDetailUpdates(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    updated_at = db.Column(db.Text, default=datetime.datetime.now().isoformat())
    order_id = db.Column(
        db.Text, db.ForeignKey('squarespace_csa_orders.order_id'),
        nullable=False
    )
    shipping_name = db.Column(db.Text)
    shipping_address_1 = db.Column(db.Text)
    shipping_address_2 = db.Column(db.Text)
    shipping_city = db.Column(db.Text)
    shipping_zip = db.Column(db.Text)
    shipping_state = db.Column(db.Text)
    shipping_phone = db.Column(db.Text)
    shipping_email = db.Column(db.Text)
    notes = db.Column(db.Text)

    def get_shipping_address(self):
        address = None
        if self.shipping_address_2 and self.shipping_address_2.strip():
            address = '%s %s, %s, %s %s, %s' % (
                self.shipping_address_1,
                self.shipping_address_2,
                self.shipping_city,
                self.shipping_state,
                self.shipping_zip,
                'US'
            )
        else:
            address = '%s, %s, %s %s, %s' % (
                self.shipping_address_1,
                self.shipping_city,
                self.shipping_state,
                self.shipping_zip,
                'US'
            )
        return address

    def to_string(self):
        return "%s, %s, %s, %s, %s; %s %s" %(
            self.shipping_name, self.shipping_address_1 + ' ' +  self.shipping_address_2,
            self.shipping_zip, self.shipping_city, self.shipping_state,
            self.shipping_phone, self.shipping_email
        )


class CustomOrderShippingDetailUpdates(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    updated_at = db.Column(db.Text, default=datetime.datetime.now().isoformat())
    order_id = db.Column(
        db.Text, db.ForeignKey('custom_order.order_id'),
        nullable=False
    )
    shipping_name = db.Column(db.Text)
    shipping_address_1 = db.Column(db.Text)
    shipping_address_2 = db.Column(db.Text)
    shipping_city = db.Column(db.Text)
    shipping_zip = db.Column(db.Text)
    shipping_state = db.Column(db.Text)
    shipping_phone = db.Column(db.Text)
    shipping_email = db.Column(db.Text)
    notes = db.Column(db.Text)

    def get_shipping_address(self):
        address = None
        if self.shipping_address_2 and self.shipping_address_2.strip():
            address = '%s %s, %s, %s %s, %s' % (
                self.shipping_address_1,
                self.shipping_address_2,
                self.shipping_city,
                self.shipping_state,
                self.shipping_zip,
                'US'
            )
        else:
            address = '%s, %s, %s %s, %s' % (
                self.shipping_address_1,
                self.shipping_city,
                self.shipping_state,
                self.shipping_zip,
                'US'
            )
        return address

    def to_string(self):
        return "%s, %s, %s, %s, %s; %s %s" %(
            self.shipping_name, self.shipping_address_1 + ' ' +  self.shipping_address_2,
            self.shipping_zip, self.shipping_city, self.shipping_state,
            self.shipping_phone, self.shipping_email
        )


class SquareSpaceOneTimeOrders(db.Model):
    fetched_datetime = db.Column(db.Text, default=datetime.datetime.now().isoformat())
    squarespace_order_id = db.Column(db.Text, primary_key=True)
    order_id = db.Column(db.Text)
    product_id = db.Column(db.Text)
    billing_email = db.Column(db.Text)
    billing_name = db.Column(db.Text)
    item_qty = db.Column(db.Text)
    shipping_name = db.Column(db.Text)
    shipping_address1 = db.Column(db.Text)
    shipping_address2 = db.Column(db.Text)
    shipping_city = db.Column(db.Text)
    shipping_zip = db.Column(db.Text)
    shipping_state = db.Column(db.Text)
    shipping_country = db.Column(db.Text)
    shipping_phone = db.Column(db.Text)
    checkout_shipping_email = db.Column(db.Text)
    delivery_zone = db.Column(db.Text)
    planned_delivery_date = db.Column(db.Text)
    personal_note = db.Column(db.Text)
    notes = db.Column(db.Text)
    order_year = db.Column(db.Text)
    delivered_by_driver = db.Column(db.Text, default="")
    apr_delivery = db.Column(db.Text)
    squarespace_fulfillment_status = db.Column(db.Text)
    squarespace_fulfillment_date = db.Column(db.DateTime)
    created_date = db.Column(db.Text)
    multi_line_items = db.Column(db.Text)
    sales_price = db.Column(db.Text)
    order_source = db.Column(db.Text)
    delivery_details = db.Column(db.Text, default='')

    def __init__(self, squarespace_order_id, order_id, billing_email, item_qty,
                 shipping_name, shipping_address1, shipping_address2,
                 shipping_city, shipping_zip, shipping_state, shipping_country,
                 shipping_phone, checkout_shipping_email, delivery_zone,
                 planned_delivery_date, personal_note, notes, product_id="",
                 order_year="2020", apr_delivery="", squarespace_fulfillment_status="", 
                 squarespace_fulfillment_date="", created_date="",
                 multi_line_items="", sales_price="", order_source="", billing_name=""):
        self.squarespace_order_id = squarespace_order_id
        self.order_id = order_id
        self.product_id = product_id
        self.billing_email = billing_email
        self.billing_name = billing_name
        self.item_qty = item_qty
        self.shipping_name = shipping_name
        self.shipping_address1 = shipping_address1
        self.shipping_address2 = shipping_address2
        self.shipping_city = shipping_city
        self.shipping_zip = shipping_zip
        self.shipping_state = shipping_state
        self.shipping_country = shipping_country
        self.shipping_phone = shipping_phone
        self.checkout_shipping_email = checkout_shipping_email
        self.delivery_zone = delivery_zone
        self.planned_delivery_date = planned_delivery_date
        self.personal_note = personal_note
        self.notes = notes
        self.order_year = order_year
        self.apr_delivery = apr_delivery
        self.squarespace_fulfillment_status = squarespace_fulfillment_status
        self.squarespace_fulfillment_date = squarespace_fulfillment_date
        self.created_date = created_date
        self.multi_line_items = multi_line_items
        self.sales_price = sales_price
        self.order_source = order_source
        self.set_shipping()
        self.set_delivery_details()

    def set_delivery_details(self, product_details=None):
        if product_details:
            self.delivery_details = json.dumps(product_details)
        else:
            self.delivery_details = json.dumps(self.product_details)
        db.session.commit()

    def set_shipping(self):
        updated_shipping = CSAShippingDetailUpdates.query.filter_by(
            order_id=self.order_id).order_by(CSAShippingDetailUpdates.id.desc()).first()
        if updated_shipping:
            self.shipping_name = updated_shipping.shipping_name
            self.shipping_address1 = updated_shipping.shipping_address_1
            self.shipping_address2 = updated_shipping.shipping_address_2
            self.shipping_city = updated_shipping.shipping_city
            self.shipping_zip = updated_shipping.shipping_zip
            self.shipping_state = updated_shipping.shipping_state
            self.shipping_phone = updated_shipping.shipping_phone
            self.checkout_shipping_email = updated_shipping.shipping_email
            zones = get_all_zones_with_postal_code(self.shipping_zip)
            self.delivery_zone = zones[0] if len(zones) > 0 else ''
            self.notes = updated_shipping.notes

    def to_html_row(self):
        self.set_shipping()
        table_row = ("#############".join([
            self.order_id,
            self.delivery_zone,  # delivery_zone
            self.billing_email,
            '<br/>'.join(self.multi_line_items.split('+++') if self.multi_line_items else ''),
            self.shipping_name,
            '' if self.shipping_address1 is None else self.shipping_address1,
            '' if self.shipping_address2 is None else self.shipping_address2,
            '' if self.shipping_city is None else self.shipping_city,
            '' if self.shipping_zip is None else self.shipping_zip,
            '' if self.shipping_state is None else self.shipping_state,
            '' if self.shipping_country is None else self.shipping_country,
            '' if self.shipping_phone is None else self.shipping_phone,
            '' if self.checkout_shipping_email is None else self.checkout_shipping_email,
            self.get_delivery_dates_html(),
            str(count_deliveries(self.apr_delivery)),
            '' if self.personal_note is None else self.personal_note,
            '' if self.notes is None else self.notes,
            '' if self.squarespace_order_id is None else self.squarespace_order_id,
            '' if self.squarespace_fulfillment_status is None else self.squarespace_fulfillment_status
        ]))
        final_table_row = "<tr><td>%s</td></tr>" % table_row.replace(
            "#############", "</td><td>")
        return final_table_row

    @property
    def product_details(self):
        product_details_list = []
        if self.multi_line_items:
            items = self.multi_line_items.split("+++")
            for item in items:
                product_id, qty = get_productid_qty(item)
                p = Product.query.filter(Product.product_id == product_id).first()
                product_details_list.append({'product_name': p.product_name if p else '--',
                                             'quantity': qty, 'product_id': product_id})
        return product_details_list

    @property
    def is_multi_product_order(self):
        if "+++" in self.multi_line_items:
            return True
        return False

    def get_delivery_dates_html(self):
        dd_html_final = '<div><ul>%s</ul></div>'
        dd_html = []
        dd_html_delivered = "<span class='delivered' title='Delivered'></span>"
        dd_html_undelivered = "<span class='undelivered' title='Marked as undelivered'></span>"
        if self.delivery_details and DELIVERY_LOG_STR in self.delivery_details:
            dds = json.loads(self.delivery_details)
            for dd in dds:
                dd_logs = dd.get(DELIVERY_LOG_STR, [])
                dd_done_dict = {}
                for dd_log in dd_logs:
                    dd_log_status = dd_log.get('status', '')
                    if dd_log_status == 'done':
                        dd_done_dict = dd_log
                if dd_done_dict:
                    dd_html.append("<li>%s %s QTY: %s DELIVERED ON: %s</li>" % (
                        dd_html_delivered, dd.get('product_name', '--'), dd.get('quantity', '--'),
                        epoch_to_datetime(dd_done_dict.get('date', ''))
                    ))
                else:
                    print("Did not find done dict")
                    dd_html.append("<li>%s %s QTY: %s UNDELIVERED REASON: %s</li>" % (
                        dd_html_undelivered, dd.get('product_name', '--'), dd.get('quantity', '--'), str(dd_logs)
                    ))
        return dd_html_final % ''.join(dd_html) if dd_html else str(get_delivery_dates_html(self.apr_delivery,
                                                                                            self.order_id))


class PlanningStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    celery_job_id = db.Column(db.Text)
    date_time = db.Column(db.Text)
    status = db.Column(db.Text)
    one_time_delivered=db.Column(db.Boolean)

    def __init__(self, celery_job_id, date_time, status, one_time_delivered):
        self.celery_job_id=celery_job_id
        self.date_time=date_time
        self.status=status
        self.one_time_delivered=one_time_delivered


automated_plan_driver_assoc = db.Table(
    'automated_plan_driver_assoc',
    db.Model.metadata,
    db.Column('automated_plan_id', ForeignKey('automated_plan.id'), primary_key=True),
    db.Column('driver_id', ForeignKey('driver.id'), primary_key=True)
)


class Driver(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    driver_name = db.Column(db.Text)
    phone_number = db.Column(db.Text)
    working_hours = db.Column(db.Text)
    automated_plan_id = db.Column(db.Integer, ForeignKey('automated_plan.id'), nullable=True)
    automated_plans = db.relationship(
        "AutomatedPlan",
        secondary=automated_plan_driver_assoc,
        back_populates="drivers"
    )


class DeliveryEmail(db.Model):
    __tablename__ = 'delivery_email'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_email = db.Column(db.Text, nullable=False)
    order_id = db.Column(db.Text, nullable=False)
    squarespace_order_id = db.Column(db.Text)
    change_hash = db.Column(db.Text, nullable=False)
    change_location_hash = db.Column(db.Text, nullable=True)
    delivery_date = db.Column(db.Text)
    routific_project_id = db.Column(db.Text)


class DeliveryEmailSent(db.Model):
    __tablename__ = 'delivery_email_sent'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    delivery_email_id = db.Column(
        db.Integer, db.ForeignKey('delivery_email.id'), nullable=False
    )
    email_type = db.Column(db.Text)
    sent_on = db.Column(db.Text, default=datetime.datetime.now().isoformat())


class DeliveryEmailSentActivity(db.Model):
    """
    Stores all interactions that the user does with the delivery email sent to
    the user
    """
    __tablename__ = 'delivery_email_sent_activity'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    delivery_email_id = db.Column(
        db.Integer, db.ForeignKey('delivery_email.id'), nullable=False
    )
    activity_on = db.Column(db.Text,
                            default=datetime.datetime.now().isoformat())
    action = db.Column(db.Text)


class DeliveryDatesForZones(db.Model):
    """
    Stores when a delivery is scheduled for a particular zone
    Needed in rescheduling a delivery.
    """
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    zone = db.Column(db.Text)
    delivery_date = db.Column(db.Text)


automated_plan_zonezips_assoc = db.Table(
    'automated_plan_zonezips_assoc',
    db.Model.metadata,
    db.Column('automated_plan_id', ForeignKey('automated_plan.id'), primary_key=True),
    db.Column('zone_zips_id', ForeignKey('zone_zips.id'), primary_key=True)
)


class ZoneZips(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    zone = db.Column(db.Text)
    zips = db.Column(db.Text)
    automated_plans = db.relationship(
        "AutomatedPlan",
        secondary=automated_plan_zonezips_assoc,
        back_populates="delivery_zones"
    )


class ManualPlans(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_at = db.Column(db.Text,
                           default=datetime.datetime.now().isoformat())
    schedule_date = db.Column(db.Text)
    zones = db.Column(db.Text)
    reschedule_zones = db.Column(db.Text)
    user_deleted = db.Column(db.Boolean, default=False, server_default='0', nullable=False)


class Event(db.Model):
    event_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_at = db.Column(db.Text,
                           default=datetime.datetime.now().isoformat())
    name = db.Column(db.Text)
    email = db.Column(db.Text)
    phone_number = db.Column(db.Text)
    event_date = db.Column(db.Text)
    event_type = db.Column(db.Text)
    floral_product = db.Column(db.Text)
    flowers_ordered = db.Column(db.Text, default=None)
    colors = db.Column(db.Text)
    event_location = db.Column(db.Text)
    delivery_time = db.Column(db.Text)
    delivery_contact_info = db.Column(db.Text, default='', server_default='')
    invoice_or_contract = db.Column(db.Integer, default=1)
    contract_first = db.Column(db.Text)
    second = db.Column(db.Text)
    total_price = db.Column(db.Text)
    completed = db.Column(db.Text)
    archived = db.Column(db.Integer, default=0)
    notes = db.Column(db.Text)

    def __str__(self):
        s = {"Name": self.name, "Location": self.event_location, "Delivery Time": self.delivery_time,
             "Event Date": self.event_date, "Event Type": self.event_type, "Phone": self.phone_number,
             "Floral products": self.floral_product, "Colors": self.colors, "Notes": self.notes}
        return '<br>'.join(["%s: %s" % (k, v) for k, v in s.items()])


class CustomOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(db.Text)
    order_date = db.Column(db.Text)
    order_source = db.Column(db.Text)
    created_date = db.Column(db.Text)
    product_id = db.Column(db.Text)
    item_qty = db.Column(db.Text)

    shipping_name = db.Column(db.Text)
    shipping_address1 = db.Column(db.Text)
    shipping_address2 = db.Column(db.Text)
    shipping_city = db.Column(db.Text)
    shipping_zip = db.Column(db.Text)
    shipping_state = db.Column(db.Text)
    shipping_country = db.Column(db.Text)
    shipping_phone = db.Column(db.Text)
    shipping_email = db.Column(db.Text)

    billing_name = db.Column(db.Text)
    billing_address1 = db.Column(db.Text)
    billing_address2 = db.Column(db.Text)
    billing_city = db.Column(db.Text)
    billing_zip = db.Column(db.Text)
    billing_state = db.Column(db.Text)
    billing_country = db.Column(db.Text)
    billing_phone = db.Column(db.Text)
    billing_email = db.Column(db.Text)

    delivery_zone = db.Column(db.Text)
    delivery_dates = db.Column(db.Text)
    apr_delivery = db.Column(db.Text)
    personal_note = db.Column(db.Text)
    notes = db.Column(db.Text)
    order_year = db.Column(db.Text)

    paid_on = db.Column(db.Text)
    paid_via = db.Column(db.Text)
    payment_reference_number = db.Column(db.Text)
    amount_paid = db.Column(db.Text)
    discount = db.Column(db.Text)
    vat = db.Column(db.Text)

    def __init__(self, order_id="", order_date="", order_source="",
                 created_date="", product_id="", item_qty="", shipping_name="",
                 shipping_address1="", shipping_address2="", shipping_city="",
                 shipping_zip="", shipping_state="", shipping_country="",
                 shipping_phone="", shipping_email="", billing_name="",
                 billing_address1="", billing_address2="", billing_city="",
                 billing_zip="", billing_state="", billing_country="",
                 billing_phone="", billing_email="", delivery_zone="",
                 delivery_dates="", personal_note="", notes="", order_year="",
                 paid_on="", paid_via="", payment_reference_number="",
                 amount_paid="", discount="", vat="", fulfillment_status = ""):
        self.order_id = order_id
        self.order_date = order_date
        self.order_source = order_source
        self.created_date = created_date
        self.product_id = product_id
        self.item_qty = item_qty
        self.shipping_name = shipping_name
        self.shipping_address1 = shipping_address1
        self.shipping_address2 = shipping_address2
        self.shipping_city = shipping_city
        self.shipping_zip = shipping_zip
        self.shipping_state = shipping_state
        self.shipping_country = shipping_country
        self.shipping_phone = shipping_phone
        self.shipping_email = shipping_email
        self.billing_name = billing_name
        self.billing_address1 = billing_address1
        self.billing_address2 = billing_address2
        self.billing_city = billing_city
        self.billing_zip = billing_zip
        self.billing_state = billing_state
        self.billing_country = billing_country
        self.billing_phone = billing_phone
        self.billing_email = billing_email
        self.delivery_zone = delivery_zone
        self.delivery_dates = delivery_dates
        self.personal_note = personal_note
        self.notes = notes
        self.order_year = order_year
        self.paid_on = paid_on
        self.paid_via = paid_via
        self.payment_reference_number = payment_reference_number
        self.amount_paid = amount_paid
        self.discount = discount
        self.vat = vat

    def set_order_id(self):
        self.created_date = datetime.datetime.now().strftime(
            "%Y %m %d %H:%M:%S")
        self.order_id = "C-%s" % self.id

    @property
    def product_details(self):
        product_details_list = []
        p = Product.query.filter(Product.product_id==self.product_id).first()
        product_details_list.append({'product_name': p.product_name, 'quantity': self.item_qty, 'product_id': self.product_id})
        return product_details_list

    def set_shipping(self):
        updated_shipping = CustomOrderShippingDetailUpdates.query.filter_by(order_id=self.order_id).order_by(CustomOrderShippingDetailUpdates.id.desc()).first()
        if updated_shipping:
            self.shipping_name = updated_shipping.shipping_name
            self.shipping_address1 = updated_shipping.shipping_address_1
            self.shipping_address2 = updated_shipping.shipping_address_2
            self.shipping_city = updated_shipping.shipping_city
            self.shipping_zip = updated_shipping.shipping_zip
            self.shipping_state = updated_shipping.shipping_state
            self.shipping_phone = updated_shipping.shipping_phone
            self.shipping_email = updated_shipping.shipping_email
            zones = get_all_zones_with_postal_code(self.shipping_zip)
            self.delivery_zone = zones[0] if len(zones) > 0 else ''
            self.notes = updated_shipping.notes

    def to_html_row(self):
        self.set_shipping()
        table_row = ("#############".join([
            self.order_id,
            self.delivery_zone,  # delivery_zone
            self.billing_email,
            self.item_qty,
            self.shipping_name,
            self.shipping_address1,
            self.shipping_address2,
            self.shipping_city,
            self.shipping_zip,
            self.shipping_state,
            self.shipping_country,
            self.shipping_phone,
            self.shipping_email,
            str(get_delivery_dates_html(self.apr_delivery, self.order_id)),
            str(count_deliveries(self.apr_delivery)),
            self.personal_note,
            self.notes,
            "",  # No squarespace order_id for CustomOrder,
            ""   # No fulfillmentstatus  for CustomOrder
        ]))
        final_table_row = "<tr><td>%s</td></tr>" % table_row.replace(
            "#############", "</td><td>")
        return final_table_row


class Webhook(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    webhook_id = db.Column(db.Text)
    secret = db.Column(db.Text)
    created_on = db.Column(db.DateTime, default=datetime.datetime.now())
    is_active = db.Column(db.Boolean, default=True)


class WebhookNotification(db.Model):
    notification_id = db.Column(db.Text, primary_key=True)
    received_on = db.Column(db.DateTime, default=datetime.datetime.now())
    handled_on = db.Column(db.DateTime, default=datetime.datetime.fromtimestamp(0))
    notification_body = db.Column(db.Text, default='')


automated_plan_product_assoc = db.Table(
    'automated_plan_product_assoc',
    db.Model.metadata,
    db.Column('automated_plan_id', ForeignKey('automated_plan.id'), primary_key=True),
    db.Column('product_id', ForeignKey('product.id'), primary_key=True)
)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id = db.Column(db.Text)
    product_name = db.Column(db.Text)
    product_short_name = db.Column(db.Text)
    is_visible = db.Column(db.Boolean, default=0)
    product_url = db.Column(db.Text, default=None)
    has_subscription = db.Column(db.Boolean(name='has_subscription'), default=False)
    subs_period = db.Column(db.Text)
    subs_period_interval = db.Column(db.Integer)
    created_on = db.Column(db.DateTime, default=datetime.datetime.now())
    updated_on = db.Column(db.DateTime, default=datetime.datetime.now())
    automated_plans = db.relationship(
        "AutomatedPlan",
        secondary=automated_plan_product_assoc,
        back_populates="products"
    )
    automated_plan_setting = db.relationship('AutomatedPlanSetting', backref='product', lazy=True)


class ProductGoogleForms(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    url = db.Column(db.Text)
    google_spreadsheet_id = db.Column(db.Text)
    title = db.Column(db.Text)
    fetched_on = db.Column(db.DateTime, default=datetime.datetime.now())


class CustomerSatisfactionEmail(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(db.Integer)
    sent_on = db.Column(db.DateTime, default=datetime.datetime.now())
    opened_on = db.Column(db.DateTime)
    skip_survey_send = db.Column(db.Boolean, default=0)


class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.Text)
    value = db.Column(db.Text)


class EventNotificationEmailTrace(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    event_id = db.Column(db.Integer)
    event_type = db.Column(db.Integer)
    sent_on = db.Column(db.DateTime, default=datetime.datetime.now())


def get_shipping_address(order):
    address = None
    if order.shipping_address2 and order.shipping_address2.strip():
        address = '%s %s, %s, %s %s, %s' % (
            order.shipping_address1,
            order.shipping_address2,
            order.shipping_city,
            order.shipping_state,
            order.shipping_zip,
            'US'
        )
    else:
        address = '%s, %s, %s %s, %s' % (
            order.shipping_address1,
            order.shipping_city,
            order.shipping_state,
            order.shipping_zip,
            'US'
        )
    return address


class RoutificRouteStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Text)
    routes = db.Column(db.Text)


class ArrangementProductionHistory(db.Model):
    __table_args__ = {'extend_existing': True}
    __tablename__ = 'arr_prod_history'
    project_id = db.Column(db.Text, primary_key=True)
    product_id = db.Column(db.Text, primary_key=True)
    airtable_record_id = db.Column(db.Text)
    harvest_goal_record_id = db.Column(db.Text)
    status = db.Column(db.Text)
    
    def __init__(self, project_id, product_id, airtable_record_id, harvest_goal_record_id, status):
        self.project_id = project_id
        self.product_id = product_id
        self.airtable_record_id = airtable_record_id
        self.harvest_goal_record_id = harvest_goal_record_id
        self.status = status


class VolunteerDays(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_at = db.Column(db.Text,
                           default=datetime.datetime.now().isoformat())
    vday_date = db.Column(db.Text)
    site_location = db.Column(db.Text)
    group_name = db.Column(db.Text)
    group_email = db.Column(db.Text)
    group_phone_number = db.Column(db.Text)
    no_of_volunteer = db.Column(db.Text)
    tasks = db.Column(db.Text)
    sm_name = db.Column(db.Text)
    sm_phone_number = db.Column(db.Text)
    sm_email = db.Column(db.Text)
    org_name = db.Column(db.Text)
    org_contact = db.Column(db.Text)
    org_email = db.Column(db.Text)
    org_phone_number = db.Column(db.Text)
    org_website = db.Column(db.Text)
    notes = db.Column(db.Text)
    event_type = db.Column(db.Text)
    youth_email = db.Column(db.Text)
    parent_event_id = db.Column(db.Integer)
    recurring_type = db.Column(db.Text)
    recurring_rule = db.Column(db.Text)
    uuid = db.Column(db.Text, default=str(uuid.uuid4()))
    
    def clone(self):
        d = dict(self.__dict__)
        d.pop("id")
        d.pop("uuid")
        d.pop("vday_date")
        d.pop("created_at")
        d.pop("_sa_instance_state")
        return self.__class__(**d)        


class Grant(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_on = db.Column(db.DateTime, default=datetime.datetime.now())
    name = db.Column(db.Text)
    contact_person = db.Column(db.Text)
    email = db.Column(db.Text)
    phone = db.Column(db.Text)
    website = db.Column(db.Text)
    amount = db.Column(db.Text)
    application_due_date = db.Column(db.Text)
    report_due_date = db.Column(db.Text)
    completed = db.Column(db.Text)
    completed_date = db.Column(db.DateTime)
    report_completed = db.Column(db.Text)
    approved_rejected_date = db.Column(db.Text)
    pending = db.Column(db.Integer, default=0)  # active = 0, pending = 1 , rejected = 2
    handled_by = db.Column(db.Integer, nullable=True)
    archived = db.Column(db.Integer, default=0)

    
class EmailTrace(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    event_category = db.Column(db.Text)
    event_id = db.Column(db.Text)
    event_type = db.Column(db.Text)
    sent_on = db.Column(db.DateTime, default=datetime.datetime.now())


class VolunteerDaySubscriber(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    vol_day_id = db.Column(db.Integer, db.ForeignKey('volunteer_days.id'), nullable=False)
    name = db.Column(db.Text)
    email = db.Column(db.Text)
    contact = db.Column(db.Text)


class CalculatorKeyValue(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    key_name = db.Column(db.Text)
    abrv = db.Column(db.Text)  # Abbreviation
    amount = db.Column(db.Text)
    notes = db.Column(db.Text)
    equation = db.Column(db.Text)


class FloralArrangments(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.Text)
    abrv = db.Column(db.Text)  # Abbreviation
    stem_use = db.Column(
        db.Integer, 
        db.ForeignKey('calculator_key_value.id', ondelete='SET NULL'),
        nullable=True)  # id from key_value table to get floral avg. stem use


class ProductKey(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_name = db.Column(db.Text)
    product_id = db.Column(db.Text)
    platform = db.Column(db.Text)
    created_on = db.Column(db.DateTime, default=datetime.datetime.now())


class ProductsMapping(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    routific_id = db.Column(db.Text)
    airtable_id = db.Column(db.Text)
    created_on = db.Column(db.DateTime, default=datetime.datetime.now())
    updated_on = db.Column(db.DateTime, default=datetime.datetime.now())


class EmploymentDocuments(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    doc_name = db.Column(db.Text)
    file_name = db.Column(db.Text)
    submitted_on = db.Column(db.DateTime, default=datetime.datetime.now())
    updated_on = db.Column(db.DateTime, default=datetime.datetime.now())


class EmployeeData(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
                        db.Integer, 
                        db.ForeignKey('user.id', ondelete='Cascade'),
                        nullable=False,
                        unique=True
                        )
    doc_submitted = db.Column(db.String(500))  # list of doc ids
    signed_docs = db.Column(db.String(500))  # list of doc ids
    t_videos_watched = db.Column(db.String(500))  # list of training Video ids


class EmployeeAdditionalDocs(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
                        db.Integer, 
                        db.ForeignKey('user.id', ondelete='Cascade'),
                        nullable=False,
                        )
    doc_name = db.Column(db.Text)
    doc_file = db.Column(db.String)
    submitted_on = db.Column(db.DateTime, default=datetime.datetime.now())


class TrainingVideos(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    video_name = db.Column(db.Text)
    video_file = db.Column(db.Text)
    video_url = db.Column(db.Text)
    video_type = db.Column(db.Text)
    video_id = db.Column(db.Text)
    uploaded_on = db.Column(db.DateTime, default=datetime.datetime.now())


class EmpIdeas(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    submitted_by = db.Column(
                        db.Integer, 
                        db.ForeignKey('user.id', ondelete='Cascade'),
                        nullable=False,
                        )
    title = db.Column(db.Text)
    description = db.Column(db.String)
    submitted_on = db.Column(db.DateTime, default=datetime.datetime.now())


class EmpComplaints(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    submitted_by = db.Column(
                        db.Integer, 
                        db.ForeignKey('user.id', ondelete='Cascade'),
                        nullable=True,
                        )
    title = db.Column(db.Text)
    description = db.Column(db.String)
    is_reviewed = db.Column(db.Boolean(name='is_reviewed'), default=False)
    submitted_on = db.Column(db.DateTime, default=datetime.datetime.now())


class AutomatedPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    delivery_date = db.Column(db.Date, default=datetime.date.today())
    max_stops = db.Column(db.Integer, default=40)
    drivers = db.relationship(
        "Driver",
        secondary=automated_plan_driver_assoc,
        back_populates="automated_plans")
    products = db.relationship(
        "Product",
        secondary=automated_plan_product_assoc,
        back_populates="automated_plans")
    delivery_zones = db.relationship(
        "ZoneZips",
        secondary=automated_plan_zonezips_assoc,
        back_populates="automated_plans")
    routific_project_id = db.Column(db.Text)

    def __str__(self):
        return "Plan %s: %s" % (self.id, self.delivery_date)


class AutomatedPlanSetting(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # the cut off time in seconds before the delivery date
    cut_off_time = db.Column(db.Integer, default=24*60*60)
    automated_scheduling = db.Column(db.Boolean(name='automated_scheduling'), default=False)
    product_id = db.Column(db.Text, db.ForeignKey('product.product_id'), nullable=False)


class YouthPartner(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.Text)
    billing_rate = db.Column(db.Float)
    is_billed_by_partner = db.Column(db.Boolean(name='is_billed_by_partner'), default=True)
    youth_employees = relationship("YouthEmployee", back_populates="youth_partner")
    youth_managers = relationship("YouthManager", back_populates="youth_partner")
    time_tracking = relationship("TimeTracking", back_populates="youth_partner")
    

class YouthEmployee(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    youth_partner_id = db.Column(db.Integer, db.ForeignKey('youth_partner.id'), nullable=False)
    youth_partner = relationship("YouthPartner", back_populates="youth_employees")
    time_tracking = relationship("TimeTracking", back_populates="youth_employee")
    first_name = db.Column(db.Text)
    last_name = db.Column(db.Text)
    phone = db.Column(db.Text)
    email = db.Column(db.Text)
    position = db.Column(db.Text)
    notes = db.Column(db.Text)
    created_on = db.Column(db.DateTime, default=datetime.datetime.now())
    updated_on = db.Column(db.DateTime, default=datetime.datetime.now())
    
    def serialize(self):
        return {
            'id': self.id,
            'youth_partner_id': self.youth_partner_id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'phone': self.phone,
            'email': self.email,
            'position': self.position,
            'notes': self.notes
        }


class YouthManager(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    youth_partner_id = db.Column(db.Integer, db.ForeignKey('youth_partner.id'), nullable=False)
    youth_partner = relationship("YouthPartner", back_populates="youth_managers")
    first_name = db.Column(db.Text)
    last_name = db.Column(db.Text)
    phone = db.Column(db.Text)
    email = db.Column(db.Text)
    position = db.Column(db.Text)
    notes = db.Column(db.Text)
    created_on = db.Column(db.DateTime, default=datetime.datetime.now())
    updated_on = db.Column(db.DateTime, default=datetime.datetime.now())


class TimeTracking(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    day = db.Column(db.Text)
    youth_partner_id = db.Column(db.Integer, db.ForeignKey('youth_partner.id'), nullable=False)
    youth_partner = relationship("YouthPartner", back_populates="time_tracking")
    youth_employee_id = db.Column(db.Integer, db.ForeignKey('youth_employee.id'), nullable=False)
    youth_employee = relationship("YouthEmployee", back_populates="time_tracking")
    hours_worked = db.Column(db.Float)
    attendance = db.Column(db.Text)
    created_on = db.Column(db.DateTime, default=datetime.datetime.now())
    updated_on = db.Column(db.DateTime, default=datetime.datetime.now())


class CrawlerInput(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.Text)
    source = db.Column(db.Text)  # tripadv_ex, google_ex, etc.
    website = db.Column(db.Text) 
    keyword = db.Column(db.Text) 
    created_on = db.Column(db.DateTime, default=datetime.datetime.now())
    updated_on = db.Column(db.DateTime, default=None)


class CrawlerOutput(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    output_file = db.Column(db.Text)
    crawled_datetime = db.Column(db.DateTime, default=None)
    crawler_input_id = db.Column(db.Integer, db.ForeignKey('crawler_input.id'), nullable=False)
    total_emails_found = db.Column(db.Integer)


class OutreachEmail(db.Model):
    email = db.Column(db.Text, primary_key=True)
    created_on = db.Column(db.DateTime, default=datetime.datetime.now())
    input_source = db.Column(db.Integer, db.ForeignKey('crawler_input.id'), nullable=False)
    moderated_on = db.Column(db.DateTime, default=None)


class FlowerProperties(db.Model):
    id = db.Column(db.Text, primary_key=True)
    name = db.Column(db.Text)
    source = db.Column(db.Text)
    storage_type = db.Column(db.Text)
    flower_type = db.Column(db.Text)
    time_to_expire = db.Column(db.Text)
    in_storage = db.Column(db.Text, default='')
    arr_type_recipe1 = db.Column(db.Text, default='')
    arr_type_recipe2 = db.Column(db.Text, default='')
    arr_type_recipe3 = db.Column(db.Text, default='')
    arr_type_recipe4 = db.Column(db.Text, default='')
    arr_type_recipe5 = db.Column(db.Text, default='')
    arr_type_recipe6 = db.Column(db.Text, default='')
    arr_type_recipe7 = db.Column(db.Text, default='')
    arr_type_recipe8 = db.Column(db.Text, default='')
    arr_type_recipe9 = db.Column(db.Text, default='')


class ArrangementTypesRecipe(db.Model):
    id = db.Column(db.Text, primary_key=True)
    name = db.Column(db.Text)
    flower1 = db.Column(db.Text)
    qty_flower1 = db.Column(db.Integer)
    flower2 = db.Column(db.Text)
    qty_flower2 = db.Column(db.Integer)
    flower3 = db.Column(db.Text)
    qty_flower3 = db.Column(db.Integer)
    flower4 = db.Column(db.Text)
    qty_flower4 = db.Column(db.Integer)
    flower5 = db.Column(db.Text)
    qty_flower5 = db.Column(db.Integer)
    flower6 = db.Column(db.Text)
    qty_flower6 = db.Column(db.Integer)
    flower7 = db.Column(db.Text)
    qty_flower7 = db.Column(db.Integer)
    flower8 = db.Column(db.Text)
    qty_flower8 = db.Column(db.Integer)
    flower9 = db.Column(db.Text)
    qty_flower9 = db.Column(db.Integer)
    arr_production = db.Column(db.Text, default='')
    harvest_goal = db.Column(db.Text, default='')
    

class Storage(db.Model):
    id = db.Column(db.Text, primary_key=True)
    name = db.Column(db.Text)
    flower_name = db.Column(db.Text)
    amt_in_storage = db.Column(db.Text)
    amt_harvested = db.Column(db.Text)
    exp_tag = db.Column(db.Text)
    exp_date = db.Column(db.Text)
    harvest_date = db.Column(db.Text)
    flower_type = db.Column(db.Text)
    time_to_expire = db.Column(db.Text)
    amt_in_storage1 = db.Column(db.Text)
    amt_in_storage2 = db.Column(db.Text)
    amt_in_storage3 = db.Column(db.Text)
    amt_in_storage4 = db.Column(db.Text)
    amt_in_storage5 = db.Column(db.Text)
    amt_in_storage6 = db.Column(db.Text)
    decrease1 = db.Column(db.Text)
    decrease2 = db.Column(db.Text)
    decrease3 = db.Column(db.Text)
    decrease4 = db.Column(db.Text)
    decrease5 = db.Column(db.Text)
    decrease6 = db.Column(db.Text)
    harvest_goal = db.Column(db.Text)
    harvest_goal2 = db.Column(db.Text)


class OperationSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.Text)
    value = db.Column(db.Text)


class Presentation(db.Model):
    presentation_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.Text)
    email = db.Column(db.Text)
    phone_number = db.Column(db.Text)
    presentation_date = db.Column(db.Text)
    presentation_type = db.Column(db.Text)
    presentation_location = db.Column(db.Text)
    notes = db.Column(db.Text)
    followup = db.Column(db.Text)
    uuid = db.Column(db.Text, default=str(uuid.uuid4()))
    archived = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now())
    modified_at = db.Column(db.DateTime, default=None)


class PresentationEventSubscriber(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    presentation_event_id = db.Column(db.Integer, db.ForeignKey('presentation.presentation_id'), nullable=False)
    name = db.Column(db.Text)
    email = db.Column(db.Text)
    contact = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now())


class ZipDetail(db.Model):
    zipcode = db.Column(db.Text, primary_key=True)
    lat = db.Column(db.Text)
    lon = db.Column(db.Text)
    name = db.Column(db.Text)


class VolunteerWeatherAlert(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    volunteer_day_id = db.Column(db.Integer, db.ForeignKey('volunteer_days.id'), nullable=False)
    sent_alert = db.Column(db.Boolean(name='sent_alert'), default=0)
    sent_on = db.Column(db.DateTime, default=datetime.datetime.now())


class PredictedWeather(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    date = db.Column(db.Date, default=None)
    zipcode = db.Column(db.Text)
    max_temp = db.Column(db.Text)  # in °C
    min_temp = db.Column(db.Text)  # in °C
    prec = db.Column(db.Text)  # in MM
    generated_at = db.Column(db.DateTime, default=datetime.datetime.now())


class OutreachCanvassRoutes(db.Model):
    canvass_route_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    contact_date = db.Column(db.Text)
    neighborhood = db.Column(db.Text)
    area_street = db.Column(db.Text)
    bnumbers = db.Column(db.Text)
    summary = db.Column(db.Text)
    for_next_time = db.Column(db.Text)
    uuid = db.Column(db.Text, default=str(uuid.uuid4()))
    archived = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now())


class OutreachContacts(db.Model):
    outreach_contact_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    outreach_type = db.Column(db.Text)
    org = db.Column(db.Text)
    desc = db.Column(db.Text)
    contact = db.Column(db.Text)
    email = db.Column(db.Text)
    phone = db.Column(db.Text)
    outreach_date = db.Column(db.Text)
    notes = db.Column(db.Text)
    follow_up = db.Column(db.Text)
    collab_idea = db.Column(db.Text)
    event = db.Column(db.Text)
    summary = db.Column(db.Text)
    school_uni_name = db.Column(db.Text)
    archived = db.Column(db.Integer, default=0)
    created_at = db.Column(db.Text, default=datetime.datetime.now().isoformat())

    modified_at = db.Column(db.DateTime, default=None)


class SubscriptionManagement(db.Model):
    subscription_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, nullable=False)
    customer_name = db.Column(db.Text)
    product = relationship("Product", backref=db.backref("product", uselist=False))
    product_id = db.Column(db.Text, db.ForeignKey('product.product_id'), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)  # parent order date
    parent_order_id = db.Column(db.Integer, nullable=False)
    related_orders = db.Column(db.Text)
    last_order_id = db.Column(db.Integer, nullable=False)
    last_order_date = db.Column(db.DateTime, nullable=False)
    next_order_date = db.Column(db.DateTime, nullable=False)
    subs_period = db.Column(db.Text, nullable=False)
    subs_period_interval = db.Column(db.Integer, nullable=False)
    stripe_customer = db.Column(db.Text)
    stripe_source = db.Column(db.Text)
    is_active = db.Column(db.Boolean(name='is_active'), default=True)
    cancelled_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now())
    modified_at = db.Column(db.DateTime, default=None)


class WcIdOrderNumberMapping(db.Model):
    wc_id = db.Column(db.Integer, primary_key=True)
    ss_id = db.Column(db.Text, unique=True, nullable=False)
    order_number = db.Column(db.Text, unique=True, nullable=False)
    
    @staticmethod
    def get_order_number_by_wc_id(wc_id, is_multiple=False):
        if not wc_id: return
        qry = WcIdOrderNumberMapping.query
        if is_multiple:
            result  = dict()
            res = qry.filter(WcIdOrderNumberMapping.wc_id.in_(wc_id))
            for mp in res:
                result[str(mp.wc_id)] = mp.order_number
            return result

        else:
            res = qry.get(wc_id)
            return res.order_number if res else None


# token decorator 
def token_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        token = None
        # pass jwt-token in headers
        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']
        if not token:  # throw error if no token provided
            return make_response(jsonify({"message": "A valid token is missing!"}), 401)
        try:
            data = jwt.decode(token, BACKEND_API_SECRET_KEY, algorithms=['HS256'])
            current_user = User.query.filter_by(email=data['email']).first()
        except:
            return make_response(jsonify({"message": "Invalid token!"}), 401)

        if current_user:
            return f(*args, **kwargs)
        else:
            return make_response(jsonify({"message": "Couldn't found user!"}), 401)
    return decorator
