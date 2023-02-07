# main.py

from calendar import monthrange
from collections import OrderedDict, defaultdict
from datetime import date, timedelta
from operator import or_
from dateutil import parser, tz
from decimal import Decimal
from enum import IntEnum
from flask import (
    Blueprint, render_template, request, send_from_directory, current_app, Response
)
from numpy import math
import jwt
from werkzeug.security import generate_password_hash, check_password_hash
from flask import make_response, jsonify, flash, redirect
from flask_login import login_required, current_user
from googleapiclient.discovery import build
from decouple import config, Csv
from docxtpl import DocxTemplate, RichText
from pathlib import Path
import re
from re import sub
from sqlalchemy import func, and_
from time import sleep
from urllib.parse import urlencode, unquote, urlparse
import xlwt
import io
from .auth import is_admin
from . import db, celery, create_app
import ast
import base64
import hashlib
import hmac
import sys
import click
import csv
import datetime
import json
import logging
import requests
import uuid
from .models import (
    ArrangementProductionHistory, ArrangementTypesRecipe, EmailTrace, FlowerProperties, OperationSettings, OutreachCanvassRoutes, OutreachContacts, ProductKey, ProductsMapping, RoutificProjects, SquarespaceCSAOrders, PlanningStatus,
    SquareSpaceOneTimeOrders, RoutificSolutions, Driver, DeliveryEmail,
    DeliveryEmailSent, DeliveryEmailSentActivity, DeliveryDatesForZones,
    CSAShippingDetailUpdates, Storage, VolunteerDaySubscriber, VolunteerDays, ZoneZips, get_all_zones_with_postal_code,
    ManualPlans, CustomOrder, CustomOrderShippingDetailUpdates,
    get_stop_from_order, get_shipping_address, Event, Webhook, count_deliveries,
    WebhookNotification, Product, ProductGoogleForms, CustomerSatisfactionEmail,
    Settings, MasterRole, PermissionRole, PermissionTable, User, EventNotificationEmailTrace, RoutificRouteStatus,
    Grant, CalculatorKeyValue, FloralArrangments, EmploymentDocuments, EmployeeData, EmployeeAdditionalDocs,
    TrainingVideos, EmpIdeas, EmpComplaints, AutomatedPlan, AutomatedPlanSetting, OutreachEmail, CrawlerInput,
    Presentation, ZipDetail , VolunteerWeatherAlert, PredictedWeather, PresentationEventSubscriber,
    SubscriptionManagement, token_required, WcIdOrderNumberMapping
)
from .model import Vehicle
from sqlalchemy.orm import make_transient
from .utils import (
    ZONE_ZIP_DICT, clean_phone_number, validate_phone_number,
    format_date_for_routific, get_productid_qty, celcius_to_farenheit
)


from json import JSONDecodeError
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import mailchimp_transactional as MailchimpTransactional
import mailchimp_marketing as MailchimpMarketing
from mailchimp_transactional.api_client import ApiClientError
from mailchimp_marketing.api_client import ApiClientError
import pandas as pd
from airtable import AirtableError, airtable
from string import Template
from .airtable_syncing import sync_airtable_data
from dateutil.rrule import rrule, DAILY, WEEKLY, MONTHLY, YEARLY, weekday
from dateutil.relativedelta import relativedelta
import httplib2
from .elfinder import elFinder
from .elfinder.api_const import API_NAME, API_TARGETS, API_DIRS, API_UPLOAD, API_UPLOAD_PATH, API_INTERSECT
from .elfinder.util import get_all, get_one
from .ml_module.weather.predict_weather import fetch_dataset, predict_one_year_weather
from .wc_sqrspc_data_reformat import (wc_orders_to_sqrspc_form,
 get_order_sqrspc_form, wc_prod_to_sqrspc_form, get_prod_sqrspc_form, wc_to_ss_id)
from werkzeug.utils import secure_filename

main = Blueprint('main', __name__)
log = logging.getLogger(__name__)
logging.getLogger("urllib3").setLevel(logging.WARNING)

# setup custom logger
CUSTOM_LOG_PATH = './custom-logs'
if not os.path.exists(CUSTOM_LOG_PATH):
    os.makedirs(CUSTOM_LOG_PATH)
custom_logger = logging.getLogger('custom-logger')
fileHandler = logging.handlers.TimedRotatingFileHandler(
                os.path.join(CUSTOM_LOG_PATH, "logs.txt"), 'D')
custom_logger.addHandler(fileHandler)
custom_logger.propagate = False  # disable from console

logging.basicConfig(level=logging.DEBUG)
USER_AGENT = 'pc-app/0.0.1'
# Get environment variables
'''copy and past all required variable from env file
Please note that this file uses all variables as mentioned in readme.md'''


@main.before_request
def log_request_info():
    time = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    logtxt = '\n############# Request @ %s-#############' % time
    logtxt += '\nip: ' + request.remote_addr
    logtxt += '\nhostname: ' + request.host
    logtxt += '\nurl: ' + request.url
    logtxt += '\nmethod: ' + request.method
    # logtxt += '\nUser-Agent: ' + request.user_agent.string
    # logtxt += '\nReferer: ' + str(request.referrer)
    # logtxt += '\nDomain: ' + request.host_url
    logtxt += '\nQuery: ' + str(request.query_string)
    logtxt += '\nInput: ' + str(request.get_data())
    for k, v in request.headers:
        logtxt += '\n%s: %s' % (k, v)

    custom_logger.info(logtxt)


@main.after_request
def log_post_request_info(req):
    logtxt = '\nResponse: ' + str(req.response)
    custom_logger.info(logtxt)
    return req


@main.app_template_filter()
def date_to_int(dt):
    try:
        dttm = datetime.datetime.strptime(dt, "%m/%d/%Y")
    except ValueError as ve:
        print("Could not parse %s" % dt)
        return 0
    return int(dttm.timestamp())


def load_routific_airtable_product_mapping():
    products_mappings = ProductsMapping.query.all()
    products_dict = {mapping.routific_id: mapping.airtable_id for mapping in products_mappings}
    log.debug("Products mapping loaded successfully.")
    return products_dict


def actual_reload_settings():
    global rapp_settings
    settings_list = Settings.query.all()
    rapp_settings = {s.name: s.value for s in settings_list}
    print("%s" % rapp_settings)


def get_user_permission(role_type):
    list_permission = []
    get_permission = PermissionRole.query.filter_by(role_id=role_type).all()
    for permission in get_permission:
        try:
            permission_id = int(permission.permission_id)
            get_user_role = PermissionTable.query.filter_by(id=permission_id).first()
            list_permission.append(get_user_role.module_name)
        except:
            pass
    return list_permission


def check_user_permission(menu_item):
    """
    Check if the current user has access to the given menu_item

    :param menu_item: The unique name string that represents menuItem in the backend e.g. 'squarespace' for SquareSpace
    :return: True if the user has permission to the menu_item and False otherwise
    """
    get_user_id = User.query.get(current_user.id)
    role_of_user = get_user_id.role_id
    all_permissions = get_user_permission(role_of_user)
    if not is_admin():
        if menu_item not in all_permissions:
            return False
    return all_permissions


@main.record
def reload_settings(setup_state):
    app = setup_state.app
    with app.app_context():
        actual_reload_settings()


def sorting_permission(role):
    try:
        list_permission = []
        get_user_role = MasterRole.query.get(role)
        get_permission = PermissionRole.query.filter_by(role_id=get_user_role.id)

        for permission in get_permission:
            try:
                permission_id = int(permission.permission_id)
                get_user_role = PermissionTable.query.filter_by(id=permission_id).first()
                permission_dict = {}
                permission_dict['content_type_id'] = get_user_role.module_name
                permission_dict['name'] = get_user_role.permission_text
                list_permission.append(permission_dict)
            except:
                pass
        return list_permission
    except Exception as e:
        print(str(e))


def save_setting(name_value_dict):
    msg = []
    for n, v in name_value_dict.items():
        s = Settings.query.filter(Settings.name == n).first()
        if s:
            if s.value != v:
                msg.append("Setting %s exists. Changing it from %s to %s" % (n, s.value, v))
                s.value = v
        else:
            msg.append("Setting %s DOES NOT exist. Created a new one." % n)
            s = Settings(name=n, value=v)
            db.session.add(s)
    db.session.commit()
    actual_reload_settings()
    return ' & '.join(msg) if msg else 'No change found.'


# This function has been replaced with set_wc_order_fullfilled
def set_order_fullfilled(order_id, shipment_dict=None, projects_project_data_dict=None, project_order_ids_dict=None,
                         projectorder_delivery_dict=None):
    """
    Sets the given order as fulfilled

    :param order_id: The SquareSpace order id and NOT the integer order id
    :param shipment_dict:
    :param projects_project_data_dict:
    :param project_order_ids_dict:
    :param projectorder_delivery_dict:
    :return:
    """

    shipment_dict = shipment_dict or {}
    order_delivery_date = ''
    if 'C-' in order_id:
        message = "CustomOrder %s; we don't need to mark as fulfilled" % order_id
        print(message)
        return message
    order = get_squarespace_order_from_squarespace_order_id(order_id)
    url = SQUARESPACE_SET_ORDER_FULFILLED_URL % order_id
    if 'carrierName' in shipment_dict:
        carrier_name = shipment_dict['carrierName']
    else:
        project_id = ""
        order_delivery_date = ""
        for k,v in project_order_ids_dict.items():
            if order.order_id in v:
                project_id = k
                break
        if project_id:
            order_delivery_date = projects_project_data_dict[project_id].get('date')
            if order_delivery_date:
                order_delivery_date = format_str_to_date(order_delivery_date)

        if order.is_multi_product_order or type(order) == SquarespaceCSAOrders:
            carrier_date = ""
            print("Multi product or CSA order. Set schedule delivery date empty")
        else:
            carrier_date = ' (Scheduled Delivery Date: %s)' % order_delivery_date
        carrier_name = 'Southside Blooms Delivery%s' % carrier_date
    print("SEND SQUARESPACE NOTIFICATION: %s - %s" % (order.order_id, carrier_name))
    json_data = {
        "shouldSendNotification": True,
        "shipments": [{
            "shipDate": shipment_dict['shipDate'] if 'shipDate' in shipment_dict else get_utc_time_now_isoformat(),
            "carrierName": carrier_name,
            "service": shipment_dict['service'] if 'service' in shipment_dict else 'Booms',
            "trackingNumber": shipment_dict['trackingNumber'] if 'trackingNumber' in shipment_dict else 'N/A',
            "trackingUrl": shipment_dict['trackingUrl'] if 'trackingUrl' in shipment_dict else 'endpoint',
        }]
    }
    headers = {
        'User-Agent': USER_AGENT,
        'Authorization': 'Bearer %s' % SECRET_KEY
    }
    print(json.dumps(json_data))
    r = requests.post(url, headers=headers, json=json_data)
    if 200 <= r.status_code < 300:
        return_string = "Successfully fulfilled: %s" % order_id
        log.debug(return_string)
    else:
        return_string = "Error, Status code: %s" % r.status_code
        log.error(return_string)
    print(return_string)
    return return_string


# This function is replacement of set_order_fullfilled and used for WOOCOMMERCE.
def set_order_fullfilled(order_id, shipment_dict=None, projects_project_data_dict=None, project_order_ids_dict=None,
                         projectorder_delivery_dict=None):
    """
    Sets the given order as fulfilled

    :param order_id: The SquareSpace order id and NOT the integer order id
    :param shipment_dict:
    :param projects_project_data_dict:
    :param project_order_ids_dict:
    :param projectorder_delivery_dict:
    :return:
    """

    #shipment and carrier data need to be fix as issue#300

    url = '%s%s' % (WC_SSB_ORDERS_URL, order_id)
    headers = {
        'User-Agent': USER_AGENT,
        'Authorization': 'Basic %s' % WC_SECRET_KEY
    }
    data = {
        "status": "completed",
    }
    r = requests.post(url,headers=headers, data=data)
    if 200 <= r.status_code < 300:
        return_string = "Successfully fulfilled: %s" % order_id
        log.debug(return_string)
    else:
        return_string = "Error, Status code: %s" % r.status_code
        log.error(return_string)
    print(return_string)
    return return_string


def get_utc_time_now_isoformat():
    now = datetime.datetime.utcnow()
    return now.strftime('%Y-%m-%dT%H:%M:%S') + now.strftime('.%f')[:4] + 'Z'


@main.app_template_filter('formatdatetime')
def format_datetime(value, format="%d %b %Y %I:%M %p"):
    """Format a date time to (Default): d Mon YYYY HH:MM P"""
    if value is None:
        return ""
    elif type(value) == str:
        fmt_str = r"%Y-%m-%dT%H:%M:%S.%f"  # replaces the fromisoformatm, not available in python 3.6
        value = datetime.datetime.strptime(value, fmt_str)
        #value = datetime.datetime.fromisoformat(value)
    return value.strftime(format)




@main.route('/create-subscription-webhook')
@login_required
def create_subscription_webhook():
    url = 'URL'
    params = {
        'client_id': SS_OAUTH_CLIENT_ID,
        'redirect_uri': '%s/oauth/connect' % SITE_URL,
        'scope': 'website.orders,website.orders.read,website.products,website.products.read',
        'state': OAUTH_STATE
    }
    link = '%s?%s' % (url, urlencode(params))
    print('LINK = %s' % link)
    print("Received the following:")
    resp = make_response("<a href='%s'>Create subscription</a>" % link)
    return resp


@main.route('/list-subscription-webhooks')
@login_required
def list_subscription_webhooks():
    log.debug("Diff between now and SS_ACCESS_TOKEN_CREATED_AT is %s" % (datetime.datetime.now() - SS_ACCESS_TOKEN_CREATED_AT).seconds)
    if SS_ACCESS_TOKEN_DICT and (datetime.datetime.now() - SS_ACCESS_TOKEN_CREATED_AT).seconds < 1800:
        log.debug("access token %s is fresh. Reuse it" % SS_ACCESS_TOKEN_DICT)
        url = '%s' % (SS_WEBHOOK_URL)
        headers = {'Authorization': 'Bearer %s' % SS_ACCESS_TOKEN_DICT.get('token'), 'User-Agent': USER_AGENT}
        r = requests.get(url, headers=headers)
        projects_response = r.json()
        output = list()
        output.append('<table style="width: 100%; border: 1px solid black; border-collapse: collapse;"><th>id</th><th>websiteId</th><th>clientID</th><th>endpointUrl</th><th>topics</th>'
                      '<th>createdOn</th><th>updatedOn</th><th>Action</th>')
        for sub in projects_response.get('webhookSubscriptions', []):
            row = [sub.get('id'), sub.get('websiteId'), sub.get('clientId'), sub.get('endpointUrl'),
                   str(sub.get('topics')), sub.get('createdOn'), sub.get('updatedOn'),
                   '%s<br/>%s</br>%s' % ('<a href="%s">Delete</a>' % ('/webhook-delete?%s' % urlencode(
                       { 'id': sub.get('id'), 'ot': SS_ACCESS_TOKEN_DICT.get('token')})),
                                          '<a href="/webhook-test?%s">Test order create</a>' % (
                                              urlencode({'oc': 'order.create',
                                                         'ot': SS_ACCESS_TOKEN_DICT.get(
                                                             'token'),
                                                         'id': sub.get('id')})),
                                          '<a href="/webhook-test?%s">Test order update</a>' % (
                                              urlencode({'oc': 'order.update',
                                                         'ot': SS_ACCESS_TOKEN_DICT.get(
                                                             'token'),
                                                         'id': sub.get('id')})),
                                                                      )


                   ]
            st = '</td><td>'.join(row)
            output.append('<tr><td>%s</td></tr>' % st)
        output.append('</table>')
        resp = make_response("List subscriptions<br/><br/>%s" % ''.join(output))
        return resp
    else:
        log.debug("Create a new access token")
        url = 'URL'
        params = {
            'client_id': SS_OAUTH_CLIENT_ID,
            'redirect_uri': '%s/oauth/connect' % SITE_URL,
            'scope': 'website.orders,website.orders.read,website.products,website.products.read',
            'state': '%s+list-subscription-webhooks' % OAUTH_STATE
        }
        link = '%s?%s' % (url, urlencode(params))
        print('LINK = %s' % link)
        print("Received the following:")
        resp = make_response("<a href='%s'>List subscriptions</a>" % link)
        return resp


def verify_payload(payload, secret, squarespace_signature):
    command = 'echo -n \'%s\' | openssl sha256 -mac hmac -macopt hexkey:%s' % (payload, secret)
    print(command)
    stream = os.popen(command)
    output = stream.read()
    print("output = %s, squarespace_signature = %s" % (output, squarespace_signature))
    return squarespace_signature.lower() in output.lower()


def verify_wc_payload(payload, webhook_secret, request_signature):
    signature = hmac.new(
            webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).digest()
    if hmac.compare_digest(
            request_signature.encode(), base64.b64encode(signature)
        ):
        return True
    return False


def get_parsed_fulfilled_on_date(fulfilled_on_str):
    try:
        if "." in fulfilled_on_str:
            parsed_date = datetime.datetime.strptime(fulfilled_on_str, "%Y-%m-%dT%H:%M:%S.%fZ")
        else:
            parsed_date = datetime.datetime.strptime(fulfilled_on_str, "%Y-%m-%dT%H:%M:%SZ")
        return parsed_date
    except Exception as e:
        try:
            return datetime.datetime.strptime(fulfilled_on_str, "%Y-%m-%dT%H:%M:%S")
        except:
            print('Exception:', e)
            return None


@main.route('/webhook-test')
def webhook_test_order_create():
    webhook_id = request.values.get('id', None)
    ot = unquote(request.values.get('ot', None))
    oc = unquote(request.values.get('oc', None))

    if webhook_id is None or ot is None or oc is None:
        resp = make_response("Either id or ot is incorrect; id=%s & ot=%s & oc=%s" % (webhook_id, ot, oc))
    else:
        print('id=%s & ot=%s & oc=%s' % (webhook_id, ot, oc))
        url = 'endpoint' % webhook_id
        headers = {'Authorization': 'Bearer %s' % ot, 'User-Agent': USER_AGENT, 'Content-Type': 'application/json'}
        if oc == 'order.create':
            test_order_data = {
                'topic': 'order.create'
            }
            print("Sending request for testing order.create")
        else:
            test_order_data = {
                'topic': 'order.update'
            }
            print("Sending request for testing order.update")
        r = requests.post(url, headers=headers, json=test_order_data)
        projects_response = r.json()
        resp = make_response('Done sending test notification %s.' % projects_response)
    return resp


@main.route('/webhook-delete')
def webhook_delete():
    webhook_id = request.values.get('id', None)
    ot = unquote(request.values.get('ot', None))

    if webhook_id is None or ot is None:
        resp = make_response("Either id or ot is incorrect; id=%s & ot=%s" % (webhook_id, ot))
    else:
        print('id=%s & ot=%s' % (webhook_id, ot))
        url = 'url%s' % webhook_id
        headers = {'Authorization': 'Bearer %s' % ot, 'User-Agent': USER_AGENT}
        r = requests.delete(url, headers=headers)
        projects_response = r.status_code
        resp = make_response('Done deleting %s. <a href="%s">Go back to list webhooks</a>' % (projects_response, '/list-subscription-webhooks'))
    return resp


def remove_visits_from_project(from_project_id, items_to_move_list):
    if len(items_to_move_list) == 0 or from_project_id is None:
        return
    # get details of the from project
    from_project_details = get_project(from_project_id)
    dict_to_put = {'fleet': from_project_details['fleet'] if 'fleet' in from_project_details else None,
                   'visits': from_project_details['visits'],
                   'settings': from_project_details['settings'],
                   'name': from_project_details['name'],
                   'date': from_project_details['date'],
                   'status': from_project_details['status'],
                   'version': from_project_details['version']}
    if 'isSolutionDirty' in from_project_details:
        dict_to_put['isSolutionDirty'] = from_project_details[
            'isSolutionDirty']
    # check if the from project contains the visit
    all_items_exist = all(
        i in dict_to_put['visits'].keys() for i in items_to_move_list)
    if all_items_exist:
        popped_items = []
        print("all items exist")
        print("Before popping %s" % dict_to_put['visits'])
        for item in items_to_move_list:
            # attempt deleting the visit
            print("Popping %s" % item)
            popped_items.append(
                convert_to_stop(dict_to_put['visits'].pop(item)))
        print("After popping %s" % dict_to_put['visits'])
        url = '%s/%s' % (ROUTIFIC_RETRIEVE_PROJECT_DATA_URL, from_project_id)
        headers = {'Content-Type': 'application/json;charset=utf-8',
                   'Authorization': 'Bearer %s' % (ROUTIFIC_API_KEY),
                   'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:80.0) Gecko/20100101 Firefox/80.0',
                   'Accept': 'application/json, text/plain, */*',
                   'Accept-Language': 'en-US,en;q=0.5'
                   }
        r = requests.Request('PUT', url, headers=headers, json=dict_to_put)
        prepared = r.prepare()
        pretty_print_POST(prepared)
        s = requests.Session()
        response_put = s.send(prepared).json()
        if 'error' in response_put:
            return make_response(jsonify(
                {'error': True, 'message': 'Missing parameters',
                 'details': response_put}), 400)


def auto_schedule_order(order_id):
    if ENABLE_AUTO_SCHEDULING_ORDERS:
        log.debug("auto_schedule_order: START. given order_id=%s" % order_id)
        mark_this_order_fulfilled = False
        # We may need to call below function to fetch order based on squarespace_order_id
        new_order = get_order_local(order_id)

        # Check if the setting for the product is set to auto and apply auto schedule cut off
        product_details = new_order.product_details
        for p in product_details:
            ap_settings = AutomatedPlanSetting.query.filter(AutomatedPlanSetting.product_id==p['product_id']).all()
            if len(ap_settings) > 1:
                log.debug("NOTE: There are more than 1 ap settings for product id %s. Use the first." % p['product_id'])
                ap_setting = ap_settings[0]
            elif len(ap_settings) == 0:
                log.debug("NOTE: There is no ap setting for product id %s. Create one." % p['product_id'])
                ap_setting = AutomatedPlanSetting(product_id=p['product_id'])
                db.session.add(ap_setting)
                db.session.commit()
                log.debug("Created")
            else:
                log.debug("NOTE: Only one ap setting for product id %s. Use it." % p['product_id'])
                ap_setting = ap_settings[0]
            if ap_setting.automated_scheduling:
                num_days_before_auto_scheduling_off = ap_setting.cut_off_time
                today_datetime = datetime.datetime.combine(datetime.date.today(), datetime.datetime.min.time())
                plans_after_datetime = today_datetime + timedelta(seconds=num_days_before_auto_scheduling_off)
                log.debug("num_days_before_auto_scheduling_off: %s seconds" % num_days_before_auto_scheduling_off)
                log.debug("plans_after_datetime: %s" % plans_after_datetime)

                # Schedule the order to the next available automated plan
                automated_plans = AutomatedPlan.query.filter(
                    func.DATETIME(AutomatedPlan.delivery_date) > plans_after_datetime).order_by(
                    AutomatedPlan.delivery_date.asc()).all()
                goto_new_plan = True
                for plan in automated_plans:
                    if goto_new_plan:
                        log.debug("Checking if we can schedule in plan %s" % plan)
                        plan_product_ids = [pr.product_id for pr in plan.products]
                        if p['product_id'] in plan_product_ids:
                            # check if we have already used the available number of stops for the project
                            if plan.routific_project_id:
                                routific_project = get_project(plan.routific_project_id)
                                all_visits = routific_project.get('visits', [])
                                if len(all_visits) < plan.max_stops:
                                    log.debug("There are %s visits in the plan %s. We can schedule." % (
                                            len(all_visits), plan.delivery_date
                                        )
                                    )
                                    # We can schedule the order in this automated plan's routific project
                                    response = add_stop_to_routific_project(
                                        plan.routific_project_id, [get_stop_from_order(new_order)]
                                    )
                                    if type(response) == list and len(response) == 1:
                                        # a way to check that we added 1 stop that of the new order
                                        log.debug("We scheduled stop %s" % json.dumps(response))
                                        delivery_details = ast.literal_eval(new_order.delivery_details)
                                        for item in delivery_details:
                                            if item.get('product_id') == p.get('product_id'):
                                                item['schedule'] = {
                                                    'routific_project_id': plan.routific_project_id,
                                                    'date': str(plan.delivery_date)
                                                }
                                                mark_this_order_fulfilled = True
                                        new_order.set_delivery_details(delivery_details)
                                    goto_new_plan = False
                                else:
                                    log.debug("More stops (%s) than allowed max_stops in the "
                                              "project %s" % (len(all_visits), plan.delivery_date))
                                    # We need to look for another automated plan
                                    goto_new_plan = True
                            else:
                                log.debug("Routific project id does not exist for plan %s" % plan.delivery_date)
                        else:
                            log.debug("Product %s - %s is not included in the plan %s" % (
                                p['product_id'], p['product_name'], plan.delivery_date)
                            )
            else:
                log.debug("Product %s is set to manual planning" % str(p))
        # TODO check if every item of the order has been scheduled
        if mark_this_order_fulfilled:
            log.debug("Marking order %s as fulfilled")
            (projects_project_data_dict, project_order_ids_dict,
             projectorder_delivery_dict) = get_routific_project_order_ids(
                force_reload=True
            )
            if USE_WOOCOMMERCE_API:
                set_wc_order_fullfilled(
                    new_order.squarespace_order_id,
                    project_order_ids_dict=project_order_ids_dict,
                    projects_project_data_dict=projects_project_data_dict,
                    projectorder_delivery_dict=projectorder_delivery_dict
                )
            else:
                set_order_fullfilled(
                    new_order.squarespace_order_id,
                    project_order_ids_dict=project_order_ids_dict,
                    projects_project_data_dict=projects_project_data_dict,
                    projectorder_delivery_dict=projectorder_delivery_dict
                )
        log.debug("Done automatic scheduling Order ID = %s" % new_order.squarespace_order_id)
    else:
        log.debug("Automatic Scheduling DISABLED. Please set ENABLE_AUTO_SCHEDULING_ORDERS")

@main.route('/wc/get-delivery-details/<order_id>')
@token_required
def get_delivery_details(order_id):
    order = get_order_local_by_order_id(order_id)
    if order:
        return order.delivery_details
    else:
        return json.dumps([])


@main.route('/wc/auto-schedule-api/<order_id>')
@token_required
def auto_schedule_api(order_id):
    print('Auto Scheduling order %s from WC' % order_id)
    auto_schedule_order(order_id)
    return 'Success'


def get_all_future_routific_projects():
    all_routific_projects = list_all_routific_projects()
    future_routific_projects = []
    for project in all_routific_projects:
        project_date = project.get('date')
        project_name = project.get('name', '--')
        if datetime.datetime.strptime(project_date, '%Y-%m-%d').date() > datetime.date.today():
            log.debug("The project %s on %s is a future project" % (project_name, project_date))
            future_routific_projects.append(project)
    return future_routific_projects


def get_signature(dashboard_secret, payload):
        key = bytes(dashboard_secret, 'utf-8')
        digester = hmac.new(key=key, msg=payload, digestmod=hashlib.sha1)
        signature = digester.hexdigest()
        return signature


# This function needs to be remove before final PR
@main.route('/test')
def test():
    # renewal_order = prepare_renewal_order(1)
    # # return renewal_order
    # return insert_renewal_order(renewal_order)
    notif = WebhookNotification.query.filter_by(notification_id='721c625f1b8925907b41585b6604c102').first()
    headers = {
        'X-WC-Webhook-Topic': 'order.updated',
        # 'X-WC-Webhook-Topic': 'order.created'
    }
    return wc_webhooks_order(json.loads(notif.notification_body), headers)


@main.route('/webhook_recall/<notif_id>')
def webhook_recall(notif_id:WebhookNotification):
    """
        - This function is for testing purpose only, if the /wc/webhooks/order give error.
        - This function is used to hit the same notification data stored in
        notification_body(webhook_notification table) from Webhook call of front-end.
        - If data couldn't insert to backend DB, we cannot call the notif id based on WC log.
        - This function bypass the webhook payload-verification, duplicacy-check and data-validation

        :param: notif_id: Notification id from the WebhookNotification table
    """
    notif = WebhookNotification.query.filter_by(notification_id=notif_id).first()
    headers = {
        'X-WC-Webhook-Topic': 'order.updated',
        # 'X-WC-Webhook-Topic': 'order.created'
    }
    if notif:
        return wc_webhooks_order(json.loads(notif.notification_body), headers)
    else:
        return {'Error': 'Invalid Notification ID.'}


def map_order_ids(order):
    ss_id = order.get('id')
    order_number = order.get('orderNumber')
    wc_id = order.get('order_prop', {}).get('id')
    wc_ord_num = order.get('order_prop', {}).get('_order_number')

    if str(order_number) != str(wc_ord_num):
        print('!!!ALERT!!!\nsquarespace orderNumber %s does not matching with '
         'WooCommerce order_number %s' %(order_number, wc_ord_num))

    mp = WcIdOrderNumberMapping.query.filter(
            (WcIdOrderNumberMapping.wc_id == wc_id) |
            (WcIdOrderNumberMapping.ss_id == ss_id) |
            (WcIdOrderNumberMapping.order_number == order_number)
        )
    if mp: mp.delete()

    mp_obj = WcIdOrderNumberMapping(
            wc_id=wc_id,
            ss_id=ss_id,
            order_number=order_number
            )
    db.session.add(mp_obj)
    db.session.commit()


def create_or_update_subscription_if_eligibal(order):
    print('***********create_or_update_subscription_if_eligibal*************')
    for li in order.get('lineItems', []):
        ordered_product = Product.query.filter_by(product_id=li['productId']).first()
        if ordered_product and ordered_product.has_subscription:
            print('ordered product %s is subsciption type' % li['productId'])

            o_prop = order.get('order_prop', {})
            print('is_migrated_order:', o_prop.get('is_migrated_order'))
            print('is_renewal:', o_prop.get('is_renewal'))
            print('subs_id:', o_prop.get('subs_id'))
            print('parent_id:', o_prop.get('parent_id'))
            print('customer_id:', o_prop.get('customer_id'))

            if o_prop.get('is_renewal') and o_prop.get('subs_id') and o_prop.get('parent_id'):
                print('Updating Subscription')
                ord_data = {
                    'id': o_prop.get('id'),
                    'customer_id': o_prop.get('customer_id'),
                    'stripe_customer': o_prop.get('_stripe_customer_id'),
                    'stripe_source': o_prop.get('_stripe_source_id'),
                    'date_created': order.get('createdOn'),
                }
                update_subscription_on_renewal(o_prop.get('subs_id'), ordered_product, ord_data)
            elif bool(o_prop.get('parent_id')) == False and bool(o_prop.get('is_renewal')) == False and not o_prop.get('subs_id'):
                subs = None
                if o_prop.get('is_migrated_order'):
                    print('Order ID %s found migrated order' % o_prop.get('id'))
                    subs = SubscriptionManagement.query.filter_by(
                        user_id=o_prop.get('customer_id'),
                        product_id= ordered_product.product_id
                        ).first()
                else:
                    # check if subscription exist for same order
                    subs = SubscriptionManagement.query.filter_by(
                        user_id=o_prop.get('customer_id'),
                        product_id= ordered_product.product_id,
                        parent_order_id= o_prop.get('id')
                        ).first()
                if not subs:
                    print('creating new subscription')
                    subs_data = prepare_new_subscription(ordered_product, order)
                    subs = create_wp_subscription(subs_data)
                    print('Subscription id %s created for '
                            'user %s' % (subs.subscription_id, subs.user_id)
                        )
                    if subs:
                        print('updating WC order %s with subscription id %s' %
                            (o_prop.get('id'), subs.subscription_id))
                        order_payload = {
                            'meta_data' : [
                                {'key':'subs_id', 'value':subs.subscription_id}
                            ]
                        }
                        update_wc_order(o_prop.get('id'), order_payload)
                else:
                    print('User have already subscription with this product.')
                    print('user_id:', subs.user_id)
                    print('product_id:', subs.product_id)
                    print('subs_id:', subs.subscription_id)
                    print('parent_id:', subs.parent_order_id)
                    ord_data = {
                        'id': o_prop.get('id'),
                        'customer_id': o_prop.get('customer_id'),
                        'stripe_customer': o_prop.get('_stripe_customer_id'),
                        'stripe_source': o_prop.get('_stripe_source_id'),
                        'date_created': order.get('createdOn'),
                    }
                    updated = update_subscription_on_renewal(subs.subscription_id, ordered_product, ord_data)
                    if updated:
                        print('updating WC order %s with parent_id %s and is_renewal:1' %
                            (o_prop.get('id'), subs.parent_order_id))
                        order_payload = {
                            'parent_id': subs.parent_order_id,
                            'meta_data' : [
                                {'key':'is_renewal', 'value':'1'},
                                {'key':'subs_id', 'value':subs.subscription_id}
                            ]
                        }
                        update_wc_order(o_prop.get('id'), order_payload)
            else:
                print('Above details are not valid to create/update a subscription.')
        else:
            print('Product id %s is not subscription type.' % li.get('productId', ''))


# The original SquareSpace endpoint was '/webhooks/order'
# and the corresponding method was webhooks_order
@main.route('/wc/webhooks/order', methods=["POST", "GET"])  # WooCommerce Order Webhook
def wc_webhooks_order(data=None, headers={}):
    """
        This Webhook calls for
            1. Order Created
            2. Order Updated (Mean status update: pending, processing, cancelld, fulfilled)

        Note:
            1. Get data in WC format but later change it to SS format to keep exising code same
                (We may change it to work with WC format everywhere in future.)
            2. Not yet implemented for deleted and restored order

        WEBHOOK-SECRET yet to be implemented.

        WooCommerce different order status being treated as Pending, fulfilled & cancelled
        PENDING: pending, processing, on-hold
        FULFILLED: completed
        CANCELLED: cancelled, refunded, failed, trash

    """

    try:
        if not data:
            data = request.json
            n_data = json.dumps(data)
            headers = request.headers
            webhook_signature = headers.get("x-wc-webhook-signature", '')
            webhook_delivery_id = headers.get('X-WC-Webhook-Delivery-ID', '')
            webhook_resource = headers.get('X-WC-Webhook-Resource', '')
            notif_id = webhook_delivery_id + '-' + webhook_signature

            # Check if duplicate webhook notification
            wn = WebhookNotification.query.get(notif_id)
            if wn:
                print("WebhookNotication DUPLICATE request")
                print("previous notif value = %s" % str(wn.__dict__))
                return make_response('DUPLICATE REQUEST!!')
            else:
                print("FRESH WebhookNotification. Save.")

                # save notification
                wn = WebhookNotification(
                    notification_id=notif_id,
                    notification_body=n_data
                )
                db.session.add(wn)
                db.session.commit()
                print(wn.notification_id)

            # Verification of webhook
            verified_payload = verify_wc_payload(  # boolean
                    request.get_data(),     # payload
                    WC_WEBHOOK_SECRET,      # secret from wc webhook
                    webhook_signature       # signature from response header
                )
            if not verified_payload:
                msg = 'Payload Verification failed'
                print(msg)
                return make_response(msg)

            validator_keys = ['id', 'order_key', 'number', 'created_via', 'status']
            valid_order_data = all(i in data for i in validator_keys)  # boolean

            if webhook_resource != 'order' or not valid_order_data:
                return_msg = 'request.json = %s -- No valid data hence quitting' % n_data
                return make_response(return_msg)

        # print("SquareSpace order received")
        # converting WC order into SquareSpace form
        ss_order = get_order_sqrspc_form(data)
        wc_order = data.copy()  # (orignal) wc format, helps to work with subscripiton related things
        orderId = ss_order['id']
        # print(ss_order)

        order_number = ss_order.get('orderNumber')
        print('order_id:', orderId)
        print('order_number:', order_number)
        # local_order = get_order_local(order_number)
        local_order = get_order_local_by_order_id(orderId)

        topic = headers.get('X-WC-Webhook-Topic', None)
        print('CASE %s' % topic)
        map_order_ids(ss_order)

        # No subscription related change for these status(cancelled, refunded, failed, trash)
        # All above status comed under CANCELLED SquareSpace status
        is_migrtd = ss_order.get('order_prop', {}).get('is_migrated_order')
        if is_migrtd or ss_order.get('fulfillmentStatus') != 'CANCELED':
            create_or_update_subscription_if_eligibal(ss_order)
        if topic in ['order.created', 'order.updated']:
            print('Check if the order exists')
            if local_order and (topic == 'order.updated' or topic == 'order.created'):
                print("Order %s %s already exists. Do not insert." % (order_number, orderId))
                # print("********LOCAL***********")
                # print(local_order.__dict__)
                # print("********REMOTE**********")
                # print(ss_order)
                # print("************************")

                local_status = local_order.squarespace_fulfillment_status
                remote_status = ss_order.get('fulfillmentStatus')
                # print('Local order: ', local_status)
                # print('Remote order: ', remote_status)
                if local_status == remote_status:
                    msg = 'No status changed!, local:%s, remote:%s' % (local_status, remote_status)
                    print(msg)
                    return make_response(msg)

                wc_update_type = ss_order.get('woocommerceStatus')
                print("WooCommerce wc_update_type = %s" % wc_update_type)

                # if ss_order.get('fulfillmentStatus') is 'FULFILLED':
                if wc_update_type == 'completed':
                    log.debug("In fulfilled ")
                    local_order.squarespace_fulfillment_status = ss_order.get("fulfillmentStatus", "")
                    # convert fulfilledOn value to datetime before saving
                    fulfilled_on_str = ss_order.get("fulfilledOn")
                    local_order.squarespace_fulfillment_date = get_parsed_fulfilled_on_date(fulfilled_on_str)
                    db.session.commit()
                    print("Saved fulfillmentStatus %s" % local_order.squarespace_fulfillment_status)
                elif local_status == 'CANCELED' and remote_status == 'PENDING': # updated status in WC
                    local_order.squarespace_fulfillment_status = remote_status
                    db.session.commit()
                # elif ss_order.get('fulfillmentStatus') == 'CANCELED':
                elif wc_update_type in ('cancelled', 'refunded'):
                    log.debug("In canceled")
                    log.debug("Order %s has been canceled" % orderId)
                    # remove the order from future routific projects if scheduled already

                    future_routific_projects = get_all_future_routific_projects()
                    log.debug("We found %s future routific projects" % len(future_routific_projects))
                    log.debug("Checking if we find order_id %s in them" % orderId)
                    for fp in future_routific_projects:
                        rp = get_project(fp['_id'])
                        visits = rp.get('visits', [])
                        visits_to_remove = []
                        for visit in visits:
                            notes_order_id = get_order_id_from_custom_notes(visits.get(visit))
                            # if notes_order_id and int(notes_order_id) == int(orderId):
                            if notes_order_id and str(notes_order_id) == str(orderId):
                                log.debug("Order ID %s found in %s" % (orderId, rp['name']))
                                visits_to_remove.append(visit)
                        if visits_to_remove:
                            pass
                            # temproralily commented
                            # remove_visits_from_project(fp['_id'], visits_to_remove)
                        else:
                            print("Order ID %s not found in %s" % (orderId, rp['name']))
                    # mark order as canceled
                    order_canceled_distinguish = 'CANCELED'
                    """  
                        orderId: large string (in case of ss), order_number: small number
                        Instead of squareSpace_id(orderId),
                        it was fetching from order_id(order_number).
                    """
                    # soc = get_squarespace_order_from_order_id(orderId)
                    soc = get_squarespace_order_from_squarespace_order_id(orderId)
                    print('soc:', soc, 'orderId', orderId)
                    if soc:
                        log.debug("Renaming %s to %s-%s" % (soc.squarespace_order_id, soc.squarespace_order_id,
                                                            order_canceled_distinguish))
                        soc.squarespace_order_id = '%s-%s' % (
                            soc.squarespace_order_id, order_canceled_distinguish)
                    db.session.commit()
                else:
                    msg = "NOT implemented yet wc_update_type: %s[%s]. " % (wc_update_type, remote_status)
                    msg += ('We only support for order.fulfilled(completed) and order.cancelled'
                     'to update and esisting order')
                    print(msg)
                    return make_response(msg)
            else:
                print("Local order for %s %s does not exist. So, insert." % (order_number, orderId))
                # Store details
                li = ss_order.get('lineItems', [])[0] if len(ss_order.get('lineItems', [])) > 0 else None
                if li:
                    shipping_address = ss_order.get('shippingAddress', {})
                    zones = get_all_zones_with_postal_code(
                        shipping_address.get('postalCode', '') if shipping_address else '',
                        ss_order.get('orderNumber', '')
                    )
                    created_on = str(ss_order.get('createdOn', ''))
                    billing_name = '%s %s' % (ss_order.get('billingAddress', {}).get('firstName', ''),
                                              ss_order.get('billingAddress', {}).get('lastName', ''))
                    if 'csa' in li.get('productName', '').lower():
                        new_order = SquarespaceCSAOrders(
                            squarespace_order_id=ss_order.get('id'),
                            order_id=ss_order.get('orderNumber'),
                            billing_email=ss_order.get('customerEmail'),
                            item_qty=li.get('quantity', ''),
                            shipping_name='%s %s' % (ss_order.get('shippingAddress', {}).get('firstName', ''), ss_order.get('shippingAddress', {}).get('lastName', '')),
                            shipping_address1=ss_order.get('shippingAddress', {}).get('address1', ''),
                            shipping_address2=ss_order.get('shippingAddress', {}).get('address2', ''),
                            shipping_city=ss_order.get('shippingAddress', {}).get('city', ''),
                            shipping_zip=ss_order.get('shippingAddress', {}).get('postalCode', ''),
                            shipping_state=ss_order.get('shippingAddress', {}).get('state', ''),
                            shipping_country=ss_order.get('shippingAddress', {}).get('countryCode', ''),
                            shipping_phone=ss_order.get('shippingAddress', {}).get('phone', ''),
                            checkout_shipping_email=get_shipping_email(ss_order.get('formSubmission', [])),
                            delivery_zone=zones[0] if len(zones) > 0 else '',  # Delivery zone
                            apr_delivery="",
                            may_delivery="",
                            jun_delivery="",
                            jul_delivery="",  # July delivery
                            aug_delivery="",  # Aug delivery
                            sep_delivery="",  # Sep delivery
                            oct_delivery="",  # Oct delivery
                            personal_note="",
                            notes=get_note(ss_order.get("formSubmission", "")),
                            product_id=li.get('productId', ''),
                            order_year=created_on[0:4] if created_on else '',
                            squarespace_fulfillment_status=ss_order.get("fulfillmentStatus", ""),
                            squarespace_fulfillment_date=get_parsed_fulfilled_on_date(ss_order.get("fulfilledOn")),
                            created_date=created_on,
                            multi_line_items=get_multi_line_item_str(ss_order.get('lineItems', [])),
                            sales_price=str(ss_order.get('grandTotal', {'value': 0}).get('value', 0)),
                            order_source=get_order_source(ss_order.get('formSubmission', [])),
                            billing_name=billing_name
                        )
                    else:
                        print("OneTimeOrder")
                        new_order = SquareSpaceOneTimeOrders(
                            squarespace_order_id=ss_order.get('id'),
                            order_id=ss_order.get('orderNumber'),
                            billing_email=ss_order.get('customerEmail'),
                            item_qty=li.get('quantity', ''),
                            shipping_name='%s %s' % (ss_order.get('shippingAddress', {}).get('firstName', ''), ss_order.get('shippingAddress', {}).get('lastName', '')),
                            shipping_address1=ss_order.get('shippingAddress', {}).get('address1', ''),
                            shipping_address2=ss_order.get('shippingAddress', {}).get('address2', ''),
                            shipping_city=ss_order.get('shippingAddress', {}).get('city', ''),
                            shipping_zip=ss_order.get('shippingAddress', {}).get('postalCode', ''),
                            shipping_state=ss_order.get('shippingAddress', {}).get('state', ''),
                            shipping_country=ss_order.get('shippingAddress', {}).get('countryCode', ''),
                            shipping_phone=ss_order.get('shippingAddress', {}).get('phone', ''),
                            checkout_shipping_email=get_shipping_email(ss_order.get('formSubmission', [])),
                            delivery_zone=zones[0] if len(zones) > 0 else '',  # Delivery zone
                            personal_note="",
                            notes=get_note(ss_order.get("formSubmission", "")),  # extra notes)
                            product_id=li.get('productId', ''),
                            apr_delivery="",
                            planned_delivery_date="",
                            order_year=created_on[0:4] if created_on else '',
                            squarespace_fulfillment_status=ss_order.get("fulfillmentStatus", ""),
                            squarespace_fulfillment_date=get_parsed_fulfilled_on_date(ss_order.get("fulfilledOn")),
                            created_date=created_on,
                            multi_line_items=get_multi_line_item_str(ss_order.get('lineItems', [])),
                            sales_price=str(ss_order.get('grandTotal', {'value': 0}).get('value', 0)),
                            order_source=get_order_source(ss_order.get('formSubmission', [])),
                            billing_name=billing_name
                        )
                    db.session.add(new_order)
                    db.session.commit()
                else:
                    print("li is None")

            if ss_order.get('woocommerceStatus') == 'processing':
                auto_schedule_order(ss_order.get('orderNumber'))
        else:
            print('CASE in not covered.')
    except Exception as e:
        msg = 'Exception found in order_webhook: '+ str(e)

        exc_type, exc_obj, tb = sys.exc_info()
        print('Webhook Traceback:', exc_obj)

        local_vars = {}
        while tb:
            filename = tb.tb_frame.f_code.co_filename
            name = tb.tb_frame.f_code.co_name
            line_no = tb.tb_lineno
            print(f"File {filename} line {line_no}, in {name}")

            local_vars = tb.tb_frame.f_locals
            tb = tb.tb_next
        # print("Local variables in top frame:", local_vars)
        return make_response(msg)
    else:
        # Below code moved on top
        # wn = WebhookNotification(
        #     notification_id=webhook_delivery_id,
        #     notification_body=n_data
        # )
        # db.session.add(wn)
        # db.session.commit()
        return_msg = "Successfully handled"
        return make_response(return_msg)


# This function has been replaced with wc_webhooks_order(wc/webhooks/order)
# In order to use WooCommerce API
@main.route('/webhooks/order', methods=["POST", "GET"])
def webhooks_order():
    return_msg = ''
    n_data = json.dumps(request.json)
    pdict = get_products_dict()
    pdict_short = get_products_short_dict()
    print("Received webhooks order %s" % n_data)
    we = Webhook.query.filter_by(webhook_id=request.json.get('subscriptionId')).first()
    if verify_payload(request.get_data().decode('utf-8'), we.secret, request.headers.get('Squarespace-Signature', '')):
        print("Payload is verified, yay")
    else:
        print("Payload is not verified, quit now")
        return

    wn = WebhookNotification.query.get(request.json.get('id', ''))
    if wn:
        print("WebhookNotication DUPLICATE request")
        print("previous notif value = %s" % str(wn.__dict__))
    else:
        print("FRESH WebhookNotification. Save.")
        data = request.json.get('data', None)
        if data:
            orderId = data.get('orderId')
            print("orderId = %s" % orderId)
            # Fetch order details
            """ This function is being used by SquareSpace webhook, no need to
             add/replace woocommerce order fetching here. """
            ss_order = fetch_squarespace_order(order_id=orderId)
            print("SquareSpace order received")
            print(ss_order)
        else:
            return_msg = 'request.json.get("data") = %s -- No data hence quitting' % data
            return make_response(return_msg)

        order_number = ss_order.get('orderNumber')  # the integer order_id
        local_order = get_order_local(order_number)

        topic = request.json.get('topic', None)
        if topic in ['order.create', 'order.update']:
            #  "data": {
            #    // String; unique order id.
            #    "orderId": "5f3c39ce69e11e796f19990e",
            #    // String; describes the update to the order.
            #    // Values can include: `FULFILLED`, `REFUNDED`, `CANCELED`, `MARKED_PENDING`, or `EMAIL_UPDATED`
            #    "update": "FULFILLED"
            #  }
            # See https://developers.squarespace.com/webhooks/events/order-update
            order_data = request.json.get('data', None)
            print("Data = %s" % json.dumps(order_data))
            print('CASE %s' % topic)
            print('Check if the order exists')
            if local_order:
                print("Order %s %s already exists. Do not insert." % (order_number, orderId))
                print("********LOCAL***********")
                print(local_order.__dict__)
                print("********REMOTE**********")
                print(ss_order)
                print("************************")
                if topic == 'order.update':
                    update_type = data.get('update')
                    print("update_type = %s" % update_type)
                    if update_type in ['FULFILLED', 'MARKED_PENDING']:
                        log.debug("In fulfilled / marked_pending")
                        local_order.squarespace_fulfillment_status = ss_order.get("fulfillmentStatus", "")
                        # convert fulfilledOn value to datetime before saving
                        fulfilled_on_str = ss_order.get("fulfilledOn")
                        local_order.squarespace_fulfillment_date = get_parsed_fulfilled_on_date(fulfilled_on_str)
                        db.session.commit()
                        print("Saved fulfillmentStatus %s" % local_order.squarespace_fulfillment_status)
                    elif update_type == 'CANCELED':
                        log.debug("In canceled")
                        log.debug("Order %s has been canceled" % orderId)
                        # remove the order from future routific projects if scheduled already

                        future_routific_projects = get_all_future_routific_projects()
                        log.debug("We found %s future routific projects" % len(future_routific_projects))
                        log.debug("Checking if we find order_id %s in them" % orderId)
                        for fp in future_routific_projects:
                            rp = get_project(fp['_id'])
                            visits = rp.get('visits', [])
                            visits_to_remove = []
                            for visit in visits:
                                notes_order_id = get_order_id_from_custom_notes(visits.get(visit))
                                if notes_order_id and int(notes_order_id) == int(orderId):
                                    log.debug("Order ID %s found in %s" % (orderId, rp['name']))
                                    visits_to_remove.append(visit)
                            if visits_to_remove:
                                remove_visits_from_project(fp['_id'], visits_to_remove)
                            else:
                                print("Order ID %s not found in %s" % (orderId, rp['name']))
                        # mark order as canceled
                        order_canceled_distinguish = 'CANCELED'
                        soc = get_squarespace_order_from_order_id(orderId)
                        if soc:
                            log.debug("Renaming %s to %s-%s" % (soc.squarespace_order_id, soc.squarespace_order_id,
                                                                order_canceled_distinguish))
                            soc.squarespace_order_id = '%s-%s' % (
                                soc.squarespace_order_id, order_canceled_distinguish)
                        db.session.commit()
                    else:
                        print("update_type = %s" % update_type)
                        print("NOT implemented yet")
                        print("*******************")
            else:
                print("Local order for %s %s does not exist. So, insert." % (order_number, orderId))
                # Store details
                li = ss_order.get('lineItems', [])[0] if len(ss_order.get('lineItems', [])) > 0 else None
                if li:
                    shipping_address = ss_order.get('shippingAddress', {})
                    zones = get_all_zones_with_postal_code(
                        shipping_address.get('postalCode', '') if shipping_address else '',
                        ss_order.get('orderNumber', '')
                    )
                    print("type createdOn = %s and value = %s" % (type(ss_order.get('createdOn', '')),
                                                                  ss_order.get('createdOn', '')))
                    created_on = str(ss_order.get('createdOn', ''))
                    billing_name = '%s %s' % (ss_order.get('billingAddress', {}).get('firstName', ''),
                                              ss_order.get('billingAddress', {}).get('lastName', ''))
                    if 'csa' in li.get('productName', '').lower():
                        new_order = SquarespaceCSAOrders(
                            squarespace_order_id=ss_order.get('id'),
                            order_id=ss_order.get('orderNumber'),
                            billing_email=ss_order.get('customerEmail'),
                            item_qty=li.get('quantity', ''),
                            shipping_name='%s %s' % (ss_order.get('shippingAddress', {}).get('firstName', ''), ss_order.get('shippingAddress', {}).get('lastName', '')),
                            shipping_address1=ss_order.get('shippingAddress', {}).get('address1', ''),
                            shipping_address2=ss_order.get('shippingAddress', {}).get('address2', ''),
                            shipping_city=ss_order.get('shippingAddress', {}).get('city', ''),
                            shipping_zip=ss_order.get('shippingAddress', {}).get('postalCode', ''),
                            shipping_state=ss_order.get('shippingAddress', {}).get('state', ''),
                            shipping_country=ss_order.get('shippingAddress', {}).get('countryCode', ''),
                            shipping_phone=ss_order.get('shippingAddress', {}).get('phone', ''),
                            checkout_shipping_email=get_shipping_email(ss_order.get('formSubmission', [])),
                            delivery_zone=zones[0] if len(zones) > 0 else '',  # Delivery zone
                            apr_delivery="",
                            may_delivery="",
                            jun_delivery="",
                            jul_delivery="",  # July delivery
                            aug_delivery="",  # Aug delivery
                            sep_delivery="",  # Sep delivery
                            oct_delivery="",  # Oct delivery
                            personal_note="",
                            notes=get_note(ss_order.get("formSubmission", "")),
                            product_id=li.get('productId', ''),
                            order_year=created_on[0:4] if created_on else '',
                            squarespace_fulfillment_status=ss_order.get("fulfillmentStatus", ""),
                            squarespace_fulfillment_date=ss_order.get("fulfilledOn"),
                            created_date=created_on,
                            multi_line_items=get_multi_line_item_str(ss_order.get('lineItems', [])),
                            sales_price=str(ss_order.get('grandTotal', {'value': 0}).get('value', 0)),
                            order_source=get_order_source(ss_order.get('formSubmission', []),
                            billing_name=billing_name)
                        )
                    else:
                        print("OneTimeOrder")
                        new_order = SquareSpaceOneTimeOrders(
                            squarespace_order_id=ss_order.get('id'),
                            order_id=ss_order.get('orderNumber'),
                            billing_email=ss_order.get('customerEmail'),
                            item_qty=li.get('quantity', ''),
                            shipping_name='%s %s' % (ss_order.get('shippingAddress', {}).get('firstName', ''), ss_order.get('shippingAddress', {}).get('lastName', '')),
                            shipping_address1=ss_order.get('shippingAddress', {}).get('address1', ''),
                            shipping_address2=ss_order.get('shippingAddress', {}).get('address2', ''),
                            shipping_city=ss_order.get('shippingAddress', {}).get('city', ''),
                            shipping_zip=ss_order.get('shippingAddress', {}).get('postalCode', ''),
                            shipping_state=ss_order.get('shippingAddress', {}).get('state', ''),
                            shipping_country=ss_order.get('shippingAddress', {}).get('countryCode', ''),
                            shipping_phone=ss_order.get('shippingAddress', {}).get('phone', ''),
                            checkout_shipping_email=get_shipping_email(ss_order.get('formSubmission', [])),
                            delivery_zone=zones[0] if len(zones) > 0 else '',  # Delivery zone
                            personal_note="",
                            notes=get_note(ss_order.get("formSubmission", "")),  # extra notes)
                            product_id=li.get('productId', ''),
                            order_year=created_on[0:4] if created_on else '',
                            apr_delivery="",
                            planned_delivery_date="",
                            squarespace_fulfillment_status=ss_order.get("fulfillmentStatus", ""),
                            squarespace_fulfillment_date=ss_order.get("fulfilledOn"),
                            created_date=created_on,
                            multi_line_items=get_multi_line_item_str(ss_order.get('lineItems', [])),
                            sales_price=str(ss_order.get('grandTotal', {'value': 0}).get('value', 0)),
                            order_source=get_order_source(ss_order.get('formSubmission', [])),
                            billing_name=billing_name
                        )
                    db.session.add(new_order)
                    db.session.commit()
                    auto_schedule_order(new_order.order_id)
                else:
                    print("li is None")
 

def get_project(project_id):
    """Fetches the project with the given id from routific and returns the json
    response
    :param project_id:
    :return:
    """
    url = '%s/%s' % (ROUTIFIC_RETRIEVE_PROJECT_DATA_URL, project_id)
    headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer %s' % ROUTIFIC_API_KEY}
    r = requests.get(url, headers=headers)
    projects_response = r.json()
    if 'error_code' in projects_response:
        print("ERROR retrieving all projects")
        log.error(json.dumps(projects_response))
    else:
        pass
        # print(json.dumps(projects_response))
        log.debug("Got project response")
    return projects_response


def get_project_routes(project_id):
    """Fetches the project routes for the project with the given id from routific and returns the json
    response
    :param project_id:
    :return:
    """
    url = ROUTIFIC_RETRIEVE_PROJECT_ROUTES_URL % project_id
    headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer %s' % ROUTIFIC_API_KEY}
    r = requests.get(url, headers=headers)
    projects_response = {}
    try:
        projects_response = r.json()
    except JSONDecodeError as jsde:
        log.error(str(jsde))
        projects_response['error_code'] = str(jsde)

    if 'error_code' in projects_response:
        print("ERROR retrieving all projects")
        print(json.dumps(projects_response))
    else:
        print(json.dumps(projects_response))
    return projects_response


def get_project_and_show_multiple_orders_only(project_id):
    url = '%s/%s' % (ROUTIFIC_RETRIEVE_PROJECT_DATA_URL, project_id)
    headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer %s' % ROUTIFIC_API_KEY}
    r = requests.get(url, headers=headers)
    CHECK_EMAIL = False
    CHECK_PHONE = True
    projects_response = r.json()
    if 'error_code' in projects_response:
        print("ERROR retrieving all projects")
        print(json.dumps(projects_response))
    else:
        print(json.dumps(projects_response))
    results = []
    if 'visits' in projects_response and len(projects_response['visits']) > 0:
        for visit in projects_response['visits']:
            result_dict = dict()
            order_id = ""
            order_email = projects_response['visits'][visit]['email']
            order_phone = projects_response['visits'][visit]['phone'] if 'phone' in projects_response['visits'][visit] else ''
            if 'customNotes' in projects_response['visits'][visit]:
                order_id = projects_response['visits'][visit]['customNotes']['order_id'] if 'order_id' in projects_response['visits'][visit]['customNotes'] else ''
            if CHECK_EMAIL:
                # check if other orders exist for order_id and email
                squarespace_csa_orders = SquarespaceCSAOrders.query.filter_by(billing_email=order_email).filter(
                    ~SquarespaceCSAOrders.squarespace_order_id.contains('-')).filter_by(order_year=datetime.date.today().year).all()
                squarespace_onetime_orders = SquareSpaceOneTimeOrders.query.filter_by(order_year=datetime.date.today().year).filter_by(billing_email=order_email).filter(
                    ~SquareSpaceOneTimeOrders.squarespace_order_id.contains('-')).all()
                custom_order = CustomOrder.query.filter_by(billing_email=order_email).all()
            elif CHECK_PHONE:
                query = "with cte as ( select *, replace(replace(replace(replace(replace(replace(shipping_phone, ' ', ''), '-', ''), '(', ''), ')', ''), '+1', ''), '.', '') s_phone from squarespace_csa_orders) select '+1' || case when s_phone like ('1%%') THEN substr(s_phone, 2, length(s_phone) - 1) else s_phone END ss_phone, * from cte where (ss_phone like '{ss_phone}' and cte.squarespace_order_id not like '%%-%%' and cte.order_year='{order_year}') OR (billing_email = '{order_email}' and cte.squarespace_order_id not like '%%-%%' and cte.order_year='{order_year}') OR (checkout_shipping_email = '{order_email}' and cte.squarespace_order_id not like '%%-%%' and cte.order_year='{order_year}')"
                squarespace_csa_orders = db.session.execute(query.format(ss_phone=order_phone, order_year=datetime.date.today().year, order_email=order_email)).fetchall()
                squarespace_onetime_orders = db.session.execute('''with cte as                  (    select *,           replace(replace(replace(replace(replace(replace(shipping_phone, ' ', ''), '-', ''), '(', ''), ')', ''), '+1',                           ''), '.', '') s_phone    from square_space_one_time_orders) select '+1' || case when s_phone like ('1%%') THEN substr(s_phone, 2, length(s_phone) - 1)                 else s_phone END ss_phone, * from cte where (ss_phone like '{ss_phone}' and cte.squarespace_order_id not like '%%-%%' and cte.order_year='{order_year}') OR (billing_email = '{order_email}' and cte.squarespace_order_id not like '%%-%%' and cte.order_year='{order_year}') OR (checkout_shipping_email = '{order_email}' and cte.squarespace_order_id not like '%%-%%' and cte.order_year='{order_year}') '''.format(
                    ss_phone=order_phone, order_year=datetime.date.today().year, order_email=order_email
                )).fetchall()
                custom_order = db.session.execute('''with cte as (    select *,           replace(replace(replace(replace(replace(replace(billing_phone, ' ', ''), '-', ''), '(', ''), ')', ''), '+1',                           ''), '.', '') s_phone    from custom_order) select '+1' || case when s_phone like ('1%%') THEN substr(s_phone, 2, length(s_phone) - 1)                 else s_phone END ss_phone, * from cte where ss_phone like ('1%%') ''').fetchall()

            if ((len(squarespace_onetime_orders) > 0 and len(squarespace_csa_orders) > 0) or
                (len(squarespace_onetime_orders) > 0 and len(custom_order) > 0) or
                (len(squarespace_csa_orders) > 0 and len(custom_order) > 0)):
                # refresh the squarespace fulfillment status, so that we don't include the fulfilled orders
                ch_squarespace_csa_orders = []
                ch_squarespace_onetime_orders = []
                for x in squarespace_csa_orders:
                    dictx = dict(x)
                    log.debug("OrderId = %s" % dictx.get('order_id', '-'))
                    if dictx.get('squarespace_fulfillment_status', '') == 'FULFILLED':
                        log.debug("OrderId = %s is Fulfilled" % dictx.get('order_id', '-'))
                        continue
                    else:
                        if USE_WOOCOMMERCE_API:
                            order = fetch_wc_order(dictx.get('squarespace_order_id', ''))
                        else:
                            order = fetch_squarespace_order(dictx.get('squarespace_order_id', ''))
                        sp_fulfillment_status = order.get('fulfillmentStatus', '')
                        if sp_fulfillment_status == dictx.get('squarespace_fulfillment_status', ''):
                            log.debug("Fulfillment status not changed and is not fulfilled; order Id = %s" % dictx.get('order_id', '-'))
                        else:
                            sp_order_obj = SquarespaceCSAOrders.query.filter_by(
                                squarespace_order_id=dictx.get('squarespace_order_id', '')).first()
                            sp_order_obj.squarespace_fulfillment_status = sp_fulfillment_status
                            fulfilled_on_str = order.get('fulfilledOn')
                            sp_order_obj.squarespace_fulfillment_date = get_parsed_fulfilled_on_date(fulfilled_on_str)
                            db.session.commit()
                            if sp_order_obj.squarespace_fulfillment_status == 'FULFILLED':
                                log.debug("OrderId = %s is Fulfilled" % dictx.get('order_id', '-'))
                                continue
                            log.debug("OrderId = %s is not fulfilled; appending" % dictx.get('order_id', '-'))
                        ch_squarespace_csa_orders.append(dictx)
                for x in squarespace_onetime_orders:
                    dictx = dict(x)
                    if dictx.get('squarespace_fulfillment_status', '') == 'FULFILLED':
                        continue
                    else:
                        if USE_WOOCOMMERCE_API:
                            order = fetch_wc_order(dictx.get('squarespace_order_id', ''))
                        else:
                            order = fetch_squarespace_order(dictx.get('squarespace_order_id', ''))
                        sp_fulfillment_status = order.get('fulfillmentStatus', '')
                        if sp_fulfillment_status == dictx.get('squarespace_fulfillment_status', ''):
                            log.debug("Onetime Fulfillment status not changed and is not fulfilled")
                        else:
                            sp_order_obj = SquareSpaceOneTimeOrders.query.filter_by(
                                squarespace_order_id=dictx.get('squarespace_order_id', '')).first()
                            sp_order_obj.squarespace_fulfillment_status = sp_fulfillment_status
                            fulfilled_on_str = order.get('fulfilledOn')
                            sp_order_obj.squarespace_fulfillment_date = get_parsed_fulfilled_on_date(fulfilled_on_str)
                            db.session.commit()
                            if sp_order_obj.squarespace_fulfillment_status == 'FULFILLED':
                                continue
                        ch_squarespace_onetime_orders.append(dictx)
                if len(ch_squarespace_onetime_orders) > 0 and len(ch_squarespace_csa_orders) > 0:
                    result_dict['email'] = order_email
                    result_dict['order_id'] = order_id
                    result_dict['squarespace_csa_orders'] = ch_squarespace_csa_orders
                    result_dict['squarespace_onetime_orders'] = ch_squarespace_onetime_orders
                    result_dict['custom_order'] = [dict(x) for x in custom_order]
                    results.append(result_dict)
    return json.dumps(results)


def move_items_logic(from_project_id, to_project_id, items_to_move,
                     deliver_later):
    items_to_move_list = items_to_move.split(',')
    new_items_to_move_list = []
    for item_to_move in items_to_move_list:
        if item_to_move.startswith("driver"):
            print(
                "Skipping stop %s because it is either driver's initial or end" % item_to_move)
        else:
            new_items_to_move_list.append(item_to_move)
    items_to_move_list = new_items_to_move_list
    if from_project_id == '' or to_project_id == '' or items_to_move == '':
        return make_response(
            jsonify({'error': True, 'message': 'Parameter empty'}), 400)
    if from_project_id == to_project_id:
        return make_response(jsonify({'error': True,
                                      'message': 'From and to projects can\'t be the same'}),
                             400)
    # get details of the from project
    # TODO refactor and use remove_visits_from_project
    from_project_details = get_project(from_project_id)
    dict_to_put = {'fleet': from_project_details['fleet'] if 'fleet' in from_project_details else None,
                   'visits': from_project_details['visits'],
                   'settings': from_project_details['settings'],
                   'name': from_project_details['name'],
                   'date': from_project_details['date'],
                   'status': from_project_details['status'],
                   'version': from_project_details['version']}
    if 'isSolutionDirty' in from_project_details:
        dict_to_put['isSolutionDirty'] = from_project_details[
            'isSolutionDirty']
    # check if the from project contains the visit
    all_items_exist = all(
        i in dict_to_put['visits'].keys() for i in items_to_move_list)
    if all_items_exist:
        popped_items = []
        print("all items exist")
        print("Before popping %s" % dict_to_put['visits'])
        for item in items_to_move_list:
            # attempt deleting the visit
            print("Popping %s" % item)
            popped_items.append(
                convert_to_stop(dict_to_put['visits'].pop(item)))
        print("After popping %s" % dict_to_put['visits'])
        url = '%s/%s' % (ROUTIFIC_RETRIEVE_PROJECT_DATA_URL, from_project_id)
        headers = {'Content-Type': 'application/json;charset=utf-8',
                   'Authorization': 'Bearer %s' % (ROUTIFIC_API_KEY),
                   'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:80.0) Gecko/20100101 Firefox/80.0',
                   'Accept': 'application/json, text/plain, */*',
                   'Accept-Language': 'en-US,en;q=0.5'
                   }
        r = requests.Request('PUT', url, headers=headers, json=dict_to_put)
        prepared = r.prepare()
        pretty_print_POST(prepared)
        s = requests.Session()
        response_put = s.send(prepared).json()
        if 'error' in response_put:
            return make_response(jsonify(
                {'error': True, 'message': 'Missing parameters',
                 'details': response_put}), 400)

        # add the popped item to the TO Project
        to_project_details = get_project(to_project_id)
        response_post = add_stop_to_routific_project(to_project_id, popped_items)
        set_delivery_details(popped_items, to_project_id, to_project_details['date'])
        if deliver_later or from_project_id == '5f5eeefcac034800172121f8':
            # write to file as a precautionary measure
            # define empty list
            from_project_details = get_project(from_project_id)
            # write items to file
            deliver_later_file = "deliver_later.txt"
            with open(deliver_later_file, 'r+') as read_file:
                read_file.truncate(0)
            with open(deliver_later_file, 'w') as filehandle:
                print("%s" % from_project_details['visits'])
                filehandle.writelines("{%s\n" % json.dumps({
                                                               datetime.datetime.now().isoformat():
                                                                   from_project_details[
                                                                       'visits'][
                                                                       item]})
                                      for item in
                                      from_project_details['visits'])
        # 1. Update the routific project_details
        # 2. Reflect the same web-form-group
        update_project_details(from_project_id)
        update_project_details(to_project_id)
        return response_put


def add_stop_to_routific_project(routific_project_id, stop_json):
    url = ROUTIFIC_ADD_STOP_TO_PROJECT_DATA_URL % routific_project_id
    headers = {'Content-Type': 'application/json;charset=utf-8',
               'Authorization': 'Bearer %s' % (ROUTIFIC_API_KEY),
               'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:80.0) Gecko/20100101 Firefox/80.0',
               'Accept': 'application/json, text/plain, */*',
               'Accept-Language': 'en-US,en;q=0.5'
               }
    r = requests.Request('POST', url, headers=headers, json=stop_json)
    prepared = r.prepare()
    s = requests.Session()
    response_post = s.send(prepared).json()
    return response_post


@main.cli.command('add-stop-to-routific-project')
@click.option('--routific_project_id', help="The routific project to which we add a stop", required=True, default='tst')
@click.option('--order_id', help="The squarespace onetime order id", required=True, default=0)
def test_add_stop_to_routific_project(routific_project_id, order_id):
    new_order = SquareSpaceOneTimeOrders.query.filter_by(order_id=order_id).first()
    add_stop_to_routific_project(routific_project_id, [get_stop_from_order(new_order)])
    print("Done")


@main.route('/moveItemsFromRoutificProject', methods=['GET'])
@login_required
def move_items_from_routific_project():
    required_keys = ['itemsToMove', 'fromProject', 'toProject']
    result = all(elem in request.values for elem in required_keys)
    num_drivers = None
    product_id = None
    product_name = None
    if result:
        from_project_id = request.values.get('fromProject', '').strip()
        to_project_id = request.values.get('toProject', '').strip()
        items_to_move = request.values.get('itemsToMove', '').strip()
        deliver_later = request.values.get('deliverLater', '').strip()
        if 'numDrivers' in request.values:
            num_drivers = int(request.values.get('numDrivers', 1).strip())
        if 'productId' in request.values:
            product_id = request.values.get('productId', '').strip()
        if 'productName' in request.values:
            product_name = request.values.get('productName', '').strip()
        return move_items_logic(from_project_id, to_project_id, items_to_move, deliver_later)
    else:
        return make_response(jsonify({'error': True, 'message': 'Missing parameters'}), 400)


def update_project_details(project_id):
    project_details = get_project(project_id)
    rps = RoutificProjects.query.filter_by(project_id=project_id).all()
    if len(rps) > 0:
        project_in_db = rps[len(rps) - 1]
        create_or_update_routific_projects(
            project_id=project_id,
            project_details=json.dumps(project_details),
            product_id=project_in_db.squarespace_product_id,
            web_form_group=project_in_db.web_form_group
        )


def convert_to_stop(popped_item):
    for item in ['id', 'duration', 'load', 'status', 'isPriority', 'createdAt']:
        if item in popped_item:
            popped_item.pop(item)
    return popped_item


def pretty_print_POST(req):
    """
    At this point it is completely built and ready
    to be fired; it is "prepared".

    However pay attention at the formatting used in
    this function because it is programmed to be pretty
    printed and may differ from the actual request.
    """
    print('{}\n{}\r\n{}\r\n\r\n{}'.format(
        '-----------START-----------',
        req.method + ' ' + req.url,
        '\r\n'.join('{}: {}'.format(k, v) for k, v in req.headers.items()),
        req.body,
    ))


@main.route('/reloadRoutificProjects')
@login_required
def handle_send_delivery_schedule_email(routific_project_id, send_one_by_one=False):
    ALREADY_SENT_EMAILS_LIST = config('ALREADY_SENT_EMAILS_LIST', cast=lambda v: [s.strip() for s in v.split(',')],
                                      default=[])
    if routific_project_id:
        p_data = get_project(routific_project_id)
        log.debug("We need to send emails to the following addresses")
        all_visits = p_data.get('visits', None)
        total_emails_sent = 0
        if all_visits:
            for visit in all_visits:
                email = p_data['visits'][visit].get('email', None)
                billing_email = ''
                name = p_data['visits'][visit].get('name', None)
                custom_notes = p_data['visits'][visit].get('customNotes', None)
                order_id = custom_notes.get('order_id', None)
                if order_id is None:
                    order_id = custom_notes.get('Order ID', None)
                product_details = ast.literal_eval(custom_notes.get('product_details', '[]'))
                for p in product_details:
                    if 'csa' in p.get('product_name').lower() and email not in ALREADY_SENT_EMAILS_LIST:
                        log.debug("We have not sent CSA scheduled email to %s yet. Sending now." % email)
                        squarespace_order_id = None
                        if squarespace_order_id is None:
                            if 'C-' in order_id:
                                print("CustomOrder %s" % order_id)
                                squarespace_order_id = order_id
                            else:
                                squarespace_order_id_obj = SquarespaceCSAOrders.query.filter_by(
                                    order_id=order_id).order_by(SquarespaceCSAOrders.order_year.desc()).first()
                                if squarespace_order_id_obj:
                                    squarespace_order_id = squarespace_order_id_obj.squarespace_order_id
                                    if '-' in squarespace_order_id:
                                        squarespace_order_id = squarespace_order_id[0:squarespace_order_id.index('-')]
                                    log.debug("Squarespace order_id = %s" % squarespace_order_id)
                                    billing_email = squarespace_order_id_obj.billing_email
                                else:
                                    log.error("Squarespace order id was not found for %s" % order_id)
                        if order_id is None:
                            log.error('Order ID does not exist for %s - %s' % (email, name))
                            continue
                        if squarespace_order_id is None:
                            log.error('SquareSpace Order ID does not exist for %s - %s' % (email, name))
                            continue
                        if email:
                            print("Send email to %s" % email)
                            project_date = datetime.datetime.strptime(p_data['date'],
                                                                      '%Y-%m-%d')
                            project_date = project_date.strftime('%m-%d-%Y')
                            delivery_email = DeliveryEmail(
                                user_email=email,
                                order_id=order_id,
                                squarespace_order_id=squarespace_order_id,
                                change_hash=str(uuid.uuid1()),
                                change_location_hash=str(uuid.uuid1()),
                                delivery_date=project_date,
                                routific_project_id=routific_project_id
                            )
                            db.session.add(delivery_email)
                            db.session.commit()
                            if send_one_by_one:
                                if click.confirm(
                                    'Do you want to send email to %s <%s> for order %s?' % (name, email, order_id),
                                        default=False):
                                    log.debug("User chose to send email")
                                else:
                                    log.debug("User chose No, hence NOT sending email "
                                              "to %s <%s> for order %s" % (name, email, order_id))
                                    return
                            send_email(
                                email=email, delivery_date=project_date,
                                reschedule_link='%s/reschedule/%s' %
                                            (APP_SITE_URL, delivery_email.change_hash),
                                reschedule_location_link='%s/deliver-to-new-address/%s' %
                                            (APP_SITE_URL, delivery_email.change_location_hash),
                                customer_name=name,
                                message_template_id=RESCHEDULE_GENERAL_EMAIL,
                                order_id=order_id
                            )
                            if billing_email.strip() != email.strip() and billing_email:
                                log.debug("biliing and shipping emails are not same")
                                log.debug("shipping: %s, billing: %s" % (email, billing_email))
                                log.debug("sending email to billing address also")
                                # send email to billing_email also
                                send_email(
                                    email=billing_email, delivery_date=project_date,
                                    reschedule_link='%s/reschedule/%s' %
                                                    (APP_SITE_URL, delivery_email.change_hash),
                                    reschedule_location_link='%s/deliver-to-new-address/%s' %
                                                             (APP_SITE_URL, delivery_email.change_location_hash),
                                    customer_name=name,
                                    message_template_id=RESCHEDULE_GENERAL_EMAIL,
                                    order_id=order_id
                                )
                            delivery_email_sent = DeliveryEmailSent(
                                delivery_email_id=delivery_email.id,
                                email_type="Schedule Notif"
                            )
                            db.session.add(delivery_email_sent)
                            db.session.commit()
                            total_emails_sent += 1
                        else:
                            log.error("~~~~")
                            log.error("No email set in the "
                                      "order %s" % p_data['visits'][visit])
                            log.error("****")
                    else:
                        log.debug("Product %s is not CSA OR email already sent to %s" % (p.get('product_name'), email))
            return make_response(jsonify({'message': 'Total mails sent: %s' % total_emails_sent}), 200)
        else:
            return make_response(jsonify({'message': "Did not find any visits in the given project."}), 404)
    else:
        msg = "Routific project id not supplied"
        log.error(msg)
        return make_response(jsonify({'message': msg}), 404)


def handle_error(error):
    message = str(error)
    print(message)
    return message


def _get_validated_emails(emails_str):
    name_mail_list = []
    extract_emails_regex = re.compile(r'"([^"]+)"(?:\s+<([^<>]+)>)?')
    valid_mail_regex = re.compile(VALID_EMAIL_REGEX)

    emails = re.findall(extract_emails_regex, emails_str)

    for nm, mail in emails:
        if valid_mail_regex.match(mail):
            name_mail_list.append({
                'name': nm,
                'email': mail
                })
    return name_mail_list


@main.route('/sendEmailMC', methods=["POST"])
@login_required
def send_email_mc(emailSubject='', emailContent='', emailContentText='', emailTo='', template_name="ssb-generic"):
    # Changed template_name default to ssb-generic from ssb-delivery-scheduled
    emailSubject = unquote(request.values.get('emailSubject', emailSubject))
    emailContent = unquote(request.values.get('emailBody', emailContent))
    emailContentText = unquote(request.values.get('emailBodyText', emailContentText))
    emailTo = unquote(request.values.get('emailTo', emailTo))
    template_name = unquote(request.values.get('templateName', template_name))
    emailToDictList = _get_validated_emails(emailTo)
    error_occured = False
    return_msg = ''

    # update template
    import mailchimp_transactional as MailchimpTransactional
    from mailchimp_transactional.api_client import ApiClientError
    try:
        mailchimp = MailchimpTransactional.Client(MC_API_KEY)
        response = mailchimp.templates.update({
            "name": "ssb-generic",
            "key": MC_API_KEY,
            "from_email": 'info@southsideblooms.com',
            "from_name": 'Southside Blooms',
            "subject": emailSubject,
            "text": emailContentText,
            "code": emailContent,
            "publish": True,
            "labels": ['ssb-generic'],
        })
        print(response)
    except ApiClientError as error:
        error_occured = True
        return_msg = handle_error(error.text)

    try:
        if '{{user}}' in emailContent or '{{user}}' in emailContentText:
            print('Found {{user}} in content so looping')
            # loop over the list and send individual requests
            for toEmail in emailToDictList:
                name = ''
                email = ''
                for k,v in toEmail.items():
                    if k == 'name':
                        name = v
                    if k == 'email':
                        email = v
                if email == '':
                     print('Email is empty %s %s -- skipping' % (name, email))
                message = {
                    "from_email": "info@southsideblooms.com",
                    "subject": emailSubject,
                    "to": [{'name': name, 'email': email, 'type': 'to'}],
                    "merge_vars": [{
                        'rcpt': email,
                        'vars': [{
                            'name': 'user',
                            'content': name
                        }, {
                            'name': 'MC_PREVIEW_TEXT',
                            'content': ''
                        }]
                    }],
                    "global_merge_vars": [{
                        'name': 'MC_PREVIEW_TEXT',
                        'content': ''
                    }],
                    "merge_language": 'handlebars'
                }
                mailchimp = MailchimpTransactional.Client(MC_API_KEY)
                response = mailchimp.messages.send_template({
                    "template_name": template_name,
                    "template_content": [
                        {"name": "test", "content": ""}],
                    "message": message})
                print("Done for %s - %s" % (name, email))
        else:
            # can send all emails at once as bcc
            message = {
                "from_email": "info@southsideblooms.com",
                "subject": emailSubject,
                "to": emailToDictList,
                "merge_vars": [{
                    'vars': [{
                        'name': 'MC_PREVIEW_TEXT',
                        'content': ''
                    }]
                }],
                "global_merge_vars": [{
                    'name': 'MC_PREVIEW_TEXT',
                    'content': ''
                }],
                "merge_language": 'handlebars'
            }
            mailchimp = MailchimpTransactional.Client(MC_API_KEY)
            response = mailchimp.messages.send_template({
                "template_name": template_name,
                "template_content": [
                    {"name": "test", "content": ""}],
                "message": message})
        return_msg = 'Mail sent successfully'
    except ApiClientError as error:
        error_occured = True
        return_msg = handle_error(error.text)

    return make_response(jsonify({'error': error_occured,
                                  'message': return_msg}),
                         200 if not error_occured else 500)



@main.cli.command('test_update_shipping')
def test_update_shipping():
    update_shipping_details_logic(
        order_id='1319',
        shipping_name='pcoder',
        shipping_address1='6340 S Peoria st',
        shipping_address2='',
        shipping_city='Chicago',
        shipping_zip='60621',
        shipping_state='IL',
        shipping_phone='+918019810768',
        shipping_email='coder.purple@gmail.com',
        notes='new notes'
    )

@main.cli.command('create_webhook')
def create_webhook():
    headers = {
        'User-Agent': USER_AGENT, 'Authorization': 'Bearer %s' % WEBHOOK_KEY
    }
    r = requests.post(SQUARESPACE_WEBHOOK_URL, json={
        'endpointUrl': 'Url',
        'topics': ["order.create", "order.update"],
    }, headers=headers)
    created_webhook = r.json()
    if 200 <= r.status_code < 300:
        return_string = "Succesfully created webhook"
        wh = Webhook(
            webhook_id=created_webhook.get('id'),
            secret=created_webhook.get('secret')
        )
        db.session.add(wh)
        db.session.commit()
        log.debug(return_string)

    else:
        return_string = "Error, Status code: %s" % r.status_code
        log.error(return_string)


@main.cli.command('import_delivery_zones_2020')
@click.argument('csv_file', required=False)
@click.option('--csv_file')
def create(csv_file):
    if csv_file is None or csv_file.strip() == "":
        # use default file
        csv_file = "CSA.csv"

    # open and read csv file
    with open(csv_file, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        print("Reading %s" % csvfile)
        for row in reader:
            order_id=row["Order ID"]
            billing_email=row["Billing Email"]
            print("Finding order #%s and email %s" % (order_id, billing_email))
            csas = SquarespaceCSAOrders.query.filter_by(
                order_id=order_id, billing_email=billing_email
            ).all()
            # Assume only one SquarespaceCSAOrder exist for a given order id
            # and email
            if len(csas) > 0:
                csas[0].delivery_zone = row["Delivery Zone"]
                print("Order ID=%s BillingEmail=%s DeliveryZone=%s" % (
                    order_id, billing_email, csas[0].delivery_zone
                ))
            else:
                print("No order")
            db.session.commit()
    print("Import delivery zones for 2020 from %s" % csv_file)
    pass


@main.cli.command('reload-products')
def reload_products():
    print("%s:  Reloading products BEGIN" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    if USE_WOOCOMMERCE_API:
        lp = list_wc_products(force_refresh=True)
    else:
        lp = list_products(force_refresh=True)
    print("Number of products = %s" % len(lp))
    print("%s:  Reloading products END" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))



@main.cli.command('volunteer-day-weather-check')
def volunteer_day_weather_check():
    zipcodes = list()
    all_zipcode_weather = dict()
    today = datetime.datetime.today()
    expected_ev_date = today + timedelta(days=5)
    vol_events = db.session.query(
                        VolunteerDays, VolunteerWeatherAlert
                        ).join(VolunteerWeatherAlert, isouter=True
                        ).filter(
                        func.Date(VolunteerDays.vday_date) >= today, 
                        func.Date(VolunteerDays.vday_date) <= expected_ev_date, 
                        ).all()

    # get list of all zip used in volunteer day
    for e, _ in vol_events:
        location = e.site_location
        try:
            zipcodes.append(re.findall(r'(\d{5})', location)[-1])
        except:
            continue
    volunteer_day_inuse_zip = set(zipcodes)

    _check_for_new_vol_day_address(volunteer_day_inuse_zip)

    for location in volunteer_day_inuse_zip:
        # sleep(1)  # Openweather allow 60 calls/minute only. uncomment if fetching large number of location
        all_zipcode_weather[location] = _get_openweather_forecast(location)
        
    for event, w_alert in vol_events:
        location = event.site_location
        event_date = event.vday_date
        try:
            zipcode = re.findall(r'(\d{5})', location)[-1]
            event_datetime = datetime.datetime.strptime(event_date, '%Y-%m-%d %H:%M')
            event_datetime = event_datetime.replace(tzinfo=tz.gettz('America/Chicago'))
        except Exception as e:
            print('Volunteer Day dated %s(ID:%s) have'
                  ' missing date or zipcode.' % (event.vday_date, event.id))
            continue

        local_weather = all_zipcode_weather[zipcode]

        # looking for weather at event date-time.
        try:
            weather_indexs = list(local_weather.keys())
            hour_diff = (event_datetime-weather_indexs[0]).total_seconds() / (60*60)
            event_time_index = int(hour_diff // 3)  # weather data have 3 hour interval

            event_hour_key = weather_indexs[event_time_index]
            event_weather = local_weather[event_hour_key]

            print('Event id %s weather: %s' % (event.id, event_weather))
            if event_weather['id'] in range(500, 600):
                if w_alert == None or w_alert.sent_alert == 0:
                    subject = "Volunteer Day - Bad Weather Alert!"
                    mail_body = '''
                        Hello {site_manager},
                        <br><br>
                        The forecast this week potentially has bad weather during a scheduled volunteer day. Please keep a close eye on the weather patterns to determine whether this volunteer event should be cancelled due to inclement weather. <br>
                        <b>Event Datetime:</b> {e_datetime}<br>
                        <b>Weather Detail:</b> {w_desc}<br>
                        <b>Precipitation Prob.:</b> {pop}%<br>
                        <b>Rainfall:</b> {rain_mm}mm<br>
                        <br>
                        Thank You,
                        <br>
                        The Southside Blooms Team
                    '''.format(
                        site_manager=event.sm_name,
                        e_datetime=event_date,
                        w_desc=event_weather['description'],
                        pop=event_weather['pop']*100,
                        rain_mm=event_weather['rain'] or 0
                        )
                    send_email(
                        email=event.sm_email,
                        use_mailchimp=True,
                        subject=subject,
                        feedback_urls=mail_body,
                        message_template_id='ssb-empty-content-no-footer',
                    )
                    VolunteerWeatherAlert.query.filter_by(volunteer_day_id=event.id).delete()
                    bad_notif = VolunteerWeatherAlert(
                            volunteer_day_id=event.id,
                            sent_alert=1,
                            sent_on=datetime.datetime.now()
                        )
                    db.session.add(bad_notif)
                    db.session.commit()
                    print('Volunteer Day dated %s(ID:%s) alerted'
                        ' for Bad Weather' % (event.vday_date, event.id))
                else:
                    print('Volunteer Day dated %s(ID:%s) already'
                        ' notified.' % (event.vday_date, event.id))
            elif w_alert != None and w_alert.sent_alert == 1:
                subject = "Volunteer Day - Good to go!"
                mail_body = '''
                    Hello {site_manager},
                    <br>
                    The forecast has changed this week and it is looking like the weather will be good during a scheduled volunteer event you have this week. Let's plan to stick with the planned volunteer day while keeping an eye on the weather for any last minute changes.<br>
                    <b>Event Datetime:</b> {e_datetime}<br>
                    <b>Weather Detail:</b> {w_desc}<br>
                    <b>Precipitation Prob.:</b> {pop}%<br>
                    <b>Rainfall:</b> {rain_mm}mm<br>
                    <br>
                    Thank You,
                    <br>
                    The Southside Blooms Team
                '''.format(
                    site_manager=event.sm_name,
                    e_datetime=event_date,
                    w_desc=event_weather['description'],
                    pop=event_weather['pop']*100,
                    rain_mm=event_weather['rain'] or 0
                    )
                send_email(
                    email=event.sm_email,
                    use_mailchimp=True,
                    subject=subject,
                    feedback_urls=mail_body,
                    message_template_id='ssb-empty-content-no-footer',
                )

                VolunteerWeatherAlert.query.filter_by(volunteer_day_id=event.id).delete()
                good_notif = VolunteerWeatherAlert(
                        volunteer_day_id=event.id,
                        sent_alert=0,
                        sent_on=datetime.datetime.now()
                    )
                db.session.add(good_notif)
                db.session.commit()

                print('Volunteer Day dated %s(ID:%s) alerted'
                    ' for Good Weather' % (event.vday_date, event.id))
            else:
                print('Weather is Good for volunteer day'
                    ' dated %s(ID:%s)' % (event.vday_date, event.id))
        except Exception as e:
            print('Something went wrong with volunteer day'
                    ' dated %s(ID:%s)' % (event.vday_date, event.id))



def _get_zip_geolocation(zipcode):
    url = "http://api.openweathermap.org/geo/1.0/zip?zip={zipcode},US&appid={api_key}"
    url = url.format(zipcode=zipcode, api_key=OPNW_KEY)
    r = requests.Request('GET', url)
    prepared = r.prepare()
    s = requests.Session()
    return s.send(prepared).json()


def _check_for_new_vol_day_address(zip_in_use):
    '''
        This function has been written to check if there new zip code exist
        which we don't have geo-location (latitude, longitude) in our Database.
        A geo-location is required to fetch weather data with Openweather API
        because Openweather will deprecate zipcode support directly very soon.
    '''

    # get zipcodes with geo-location
    db_zip = ZipDetail.query.with_entities(ZipDetail.zipcode).all()
    db_zip = set(map(lambda x: x[0], db_zip))

    # zipcode without geo-location
    new_volunteer_zips = zip_in_use - db_zip

    # fetch & insert zip detail in DB for new zipcodes
    for zp in new_volunteer_zips:
        geoloc = _get_zip_geolocation(zp)
        try:
            new_zip = ZipDetail(
                    zipcode=zp,
                    lat=geoloc['lat'],
                    lon=geoloc['lon'],
                    name=geoloc['name'],
                )
            db.session.add(new_zip)
            db.session.commit()
        except:
            print(geoloc)


def _get_openweather_forecast(zipcode):
    # get geolocation and hit api
    zip_detail = ZipDetail.query.get(zipcode)
    if not zip_detail:
        return 
    url = "http://api.openweathermap.org/data/2.5/forecast?unit=metric&lat={lat}&lon={lon}&appid={api_key}"
    url = url.format(lat=zip_detail.lat, lon=zip_detail.lon, api_key=OPNW_KEY)
    r = requests.Request('GET', url)
    prepared = r.prepare()
    s = requests.Session()
    response = s.send(prepared).json()

    weather_data = dict()
    try: response['list']
    except: 
        print(response)
        return 

    for ts_data in response['list']:
        from_zone = tz.tzutc()
        to_zone = tz.gettz('America/Chicago')

        utc = datetime.datetime.strptime(ts_data['dt_txt'], '%Y-%m-%d %H:%M:%S')
        utc = utc.replace(tzinfo=from_zone)

        local_datetime = utc.astimezone(to_zone)

        weather_data[local_datetime] = {
            **ts_data['weather'][0],
            'pop': ts_data['pop'],  # Probability of precipitation
            'rain': ts_data.get('rain', {}).get('3h'),
        }

    return weather_data


@main.cli.command('fetch-history-weather-data')
@click.option('--api_key',
    help="Use custom API KEY in case of 'unauthorised' or exceeded limit error",
    required=False)
def fetch_history_weather_data(api_key):
    data_dir = os.path.join(current_app.root_path, WEATHER_DATA_DIR)
    zip_codes = WEATHER_LOCATIONS.split(',')
    api_key = api_key or WEATHER_HISTORY_API_KEY

    for zipc in zip_codes:
        try:
            fetch_dataset(zipc, data_dir, api_key)
        except Exception as e:
            print('couldn\'t save data for %s' % zipc)
            print(e)


@main.cli.command('generate-weather-prediction')
def generate_weather_prediction():
    data_dir = os.path.join(current_app.root_path, WEATHER_DATA_DIR)
    zip_codes = WEATHER_LOCATIONS.split(',')

    for zipc in zip_codes:
        print('Starting prediction for %s' % zipc)

        try:
            csv_data = os.path.join(data_dir, zipc+'.csv')
            if os.path.exists(csv_data):
                pred_df = predict_one_year_weather(zipc, data_dir)
                print('Prediction Generated, processing Database insertion...')
            else:
                print('Data not found at location %s', csv_data)
                continue
        except Exception as e:
            print('Something went wrong with zipcode %s' % zipc)
            print(e)
            continue
        curr_time = pd.Timestamp.now() 

        # modifying dataframe as per our usage
        field_names = {
            'precipMM': 'prec',
            'maxtempC': 'max_temp',
            'mintempC': 'min_temp',
        }
        pred_df.rename(columns=field_names, inplace=True)

        pred_df['prec'] = pred_df['prec'].round(decimals=1)
        pred_df['max_temp'] = pred_df['max_temp'].round(0).apply(int)
        pred_df['min_temp'] = pred_df['min_temp'].round(0).apply(int)
        pred_df['date'] = pred_df.index.strftime('%Y-%m-%d')
        pred_df['zipcode'] = zipc
        pred_df['generated_at'] = curr_time

        res = pred_df.to_sql(
                name='predicted_weather',
                con=db.engine,
                index=False,
                if_exists='append',
                )

        if res:
            print('Successfully inserted prediction data(%s rows) for %s into Database' % (res, zipc))

            # Deleting previously generated records if exist
            PredictedWeather.query.filter(PredictedWeather.zipcode==zipc,
                                          PredictedWeather.generated_at<curr_time
                                         ).delete()
            db.session.commit()


@main.route('/get_weather')
def get_weather_from_db():
    date = request.values.get('date', None)
    location = request.values.get('location', None)

    try:
        zip_code = re.findall(r'(\d{5})', location)[-1]
    except Exception as e:
        return {'msg': 'Zipcode not found'}

    try:
        dt_obj = datetime.datetime.strptime(date, '%m-%d-%Y %H:%M')
        dt = dt_obj.strftime('%Y-%m-%d')
    except Exception as e:
        print(e)
        return {'msg': 'Invalid date format'}

    res = PredictedWeather.query.filter_by(date=dt, zipcode=zip_code).first()

    if res:
        result = {
            'min': celcius_to_farenheit(res.min_temp),
            'max': celcius_to_farenheit(res.max_temp),
            'prec': res.prec,
        }
        return {'result': result}
    else:
        return {'msg': 'Data not found.'}



def insert_renewal_order(order=None):
    """
        create order renewal in woocommerce
        :param: order-> prepared woocommerce order format data
    """
    url = "%swp-json/ssb-backend/v1/wc_orders" % WP_BASE_URL

    headers = {
        'authorization': "Basic %s" % WC_SECRET_KEY,
        'content-type': "application/json",
        }

    order_data = json.dumps(order)
    response = requests.request("POST", url, data=order_data, headers=headers)
    print(response.text)
    return response.text


def fetch_wc_user(user_id : str):
    url = '%s%s' % (WC_USER_URL, user_id)

    headers = {
        'User-Agent': USER_AGENT,'Authorization': 'Basic %s' % WC_SECRET_KEY
    }
    r = requests.get(url,headers=headers)
    if r.status_code == 200:
        try:
            return r.json()
        except Exception as e:
            print('Exepiton at fetch_wc_user: ', e)
    else:
        print('Something went wrong at fetch_wc_user')
        print(r.status_code, r.text)


def get_wc_user_saved_payment(user_id : str):
    # Not in use bcoz it is not retriving the complete payment information
    url = '%s%s' % (WC_USER_PAYMENT_INFO_URL, user_id)
    print(url)
    headers = {
        'User-Agent': USER_AGENT,'Authorization': 'Basic %s' % WC_SECRET_KEY
    }
    r = requests.get(url,headers=headers)
    if r.status_code == 200:
        try:
            print(r.text)
            return r.json()
        except Exception as e:
            print('Exepiton at get_wc_user_saved_payment: ', e)
    else:
        print('Something went wrong at get_wc_user_saved_payment')
        print(r.status_code, r.text)


def get_next_renewal_date(subs_type: str, subs_interval: int,
    last_order_date: datetime = None) -> datetime:
    """
        :param: subscription: subscription object from db
        :param: last_order_date: date object(order_created) of last order
    """
    if subs_type.lower() not in ('day', 'week', 'month'):
        print('Invalid Subscription Type:%s' % subs_type)
        return
    if subs_type.lower() == 'day':
        next_renewal_date = last_order_date + relativedelta(
            days=subs_interval)
    elif subs_type.lower() == 'week':
        next_renewal_date = last_order_date + relativedelta(
            weeks=subs_interval)
    elif subs_type.lower() == 'month':
        next_renewal_date = last_order_date + relativedelta(
            months=subs_interval)
    else:
        next_renewal_date = None
    return next_renewal_date


@main.cli.command('wc-subscription-renewal')
@click.option('--subscription_id',
              help="Input the subscription id in the ssb-backend that you want to renew",
              required=False)
def subscription_renewal(subscription_id):
    """
        This function needs to run daily with cron
        it checks for the subscription-next-renewal date from
        subscription-list and create a renewal order if found a renewal date is today.
    """
    if subscription_id:
        print("Subscription rewnewal only for subscription_id: %s" % subscription_id)
        subscriptions = SubscriptionManagement.query.filter(
            SubscriptionManagement.subscription_id == subscription_id
        ).all()
    else:
        subscriptions = SubscriptionManagement.query.filter(
            SubscriptionManagement.is_active == 1,
            func.date(SubscriptionManagement.next_order_date) == datetime.date.today()
        ).all()
    if not subscriptions:
        print('No Any Subscription Found!')
        return

    for subs in subscriptions:
        print(f'creating renewal order for subscription id: {subs.subscription_id}')
        renewal_order = prepare_renewal_order(subs.subscription_id)
        order = insert_renewal_order(renewal_order)
        print(order)  # todo: print only important info from order


def is_payment_done(order_id):
    """
        This function take order_id as argument and check for payment status
        By using stripe API search by meta-data. and return bool value.
        Purpose of this function is to check order payment before auto scheduling.
    """
    payment_info = {}
    stripe.api_key = STRIPE_API_KEY
    stripe.api_version = "2022-08-01"
    payment_detail = stripe.Charge.search(query="metadata['id']:'%s'" % order_id)
    if len(payment_detail['data']):
        return True
    else:
        return False


def update_wc_order(order_id, payload):
    if not order_id or not payload:
        print('Invalid order ID or payload.')
        return
    url = '%s%s' % (WC_SSB_ORDERS_URL, order_id)
    headers = {
        'User-Agent': USER_AGENT,
        'Authorization': 'Basic %s' % WC_SECRET_KEY,
        'Content-Type': 'application/json'
    }
    r = requests.post(url,headers=headers, data=json.dumps(payload))
    if 200 <= r.status_code < 300:
        return_string = "Successfully Updated: %s" % order_id
        log.debug(return_string)
    else:
        return_string = "Error, Status code: %s" % r.status_code
        print('WC error:', r.text)
        log.error(return_string)
    return return_string


# user login route
@main.route('/get-token', methods=['POST'])
def api_login():
    """
        This function takes email & password as input and return JWT authenticated token.
    """
    auth = request.values

    if not auth or not auth.get('email') or not auth.get('password'):
        return make_response('Could not verify!', 401, {'WWW-Authenticate': 'Basic-realm= "Login required!"'})

    user = User.query.filter_by(email=auth['email']).first()
    if not user:
        return make_response('Could not verify user!', 401, {'WWW-Authenticate': 'Basic-realm= "No user found!"'})

    if check_password_hash(user.password, auth.get('password')):
        if user.email not in ADMIN:
            return make_response('Can be Authenticated for Admin user only.', 403, {'WWW-Authenticate': 'Basic-realm= "Not an Admin."'})
        else:
            token = jwt.encode({'email': user.email}, BACKEND_API_SECRET_KEY, 'HS256')
            return make_response(jsonify({'token': token}), 201)

    return make_response('Could not verify password!', 403, {'WWW-Authenticate': 'Basic-realm= "Wrong Password!"'})

@main.route('/wc/sync-products')
@token_required
def sync_products():
    products = get_data(force_refresh=True)
    if products:
        return {'msg': 'Successfully synchronized products'}
    else:
        return {'msg': 'Something went wrong at sync-products'}


@main.route('/events/images', methods=['GET', 'POST'])
def events_notes_images():
    print("In the events image upload start")
    img = request.files['upload']
    filename = str(uuid.uuid1())
    img.save(os.path.join(EVENTS_NOTES_IMAGE_DIR, filename))
    print("In the events image upload end")
    return { "url":SITE_URL+"/img/events/"+filename }


@main.cli.command('reload-order-billing-name')
@click.option('--only_once', is_flag=True, help="Run this for the first data only", required=False)
@click.option('--sleep_interval', help="sleep interval in seconds between requests", required=False, default=0)
def reload_order_billing_name(only_once, sleep_interval):
    print("%s:  Reloading order billing name BEGIN" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    ss_csa_orders = SquarespaceCSAOrders.query.filter(
        ~SquarespaceCSAOrders.squarespace_order_id.contains('-')
    )
    total_csa_orders = len(ss_csa_orders.all())
    print("Total ss_csa_orders: %s" % total_csa_orders)
    cnt = 0
    for ss_csa_order in ss_csa_orders:
        cnt += 1
        if ss_csa_order.billing_name in (None, ''):
            o = fetch_squarespace_order(ss_csa_order.squarespace_order_id, False)
            ss_csa_order.billing_name = '%s %s' % (o.get('billingAddress', {}).get('firstName', ''),
                                                   o.get('billingAddress', {}).get('lastName', ''))
            print("(%s/%s) Update billing name of orderId %s to %s" % (
                cnt, total_csa_orders, ss_csa_order.order_id, ss_csa_order.billing_name))
        else:
            continue
        if only_once:
            break
        if sleep_interval > 0:
            sleep(sleep_interval)
    db.session.commit()
    cnt = 0
    ss_otos = SquareSpaceOneTimeOrders.query.filter(
        ~SquareSpaceOneTimeOrders.squarespace_order_id.contains('-')
    )
    total_ss_order = len(ss_otos.all())
    for ss_order in ss_otos:
        cnt += 1
        if ss_order.billing_name in (None, ''):
            o = fetch_squarespace_order(ss_order.squarespace_order_id, False)
            ss_order.billing_name = '%s %s' % (o.get('billingAddress', {}).get('firstName', ''),
                                               o.get('billingAddress', {}).get('lastName', ''))
            print("(%s/%s) Update billing name of orderId %s to %s" % (
                cnt, total_ss_order, ss_order.order_id, ss_order.billing_name))
        else:
            continue
        if only_once:
            break
        if sleep_interval > 0:
            sleep(sleep_interval)
    db.session.commit()
    print("%s:  Reloading order billing name END" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


@main.route('/subscription-management')
@login_required
def wp_subs_management():
    all_permissions = check_user_permission('admin')
    if all_permissions is False:
        return redirect("/", code=302)

    subs_list = SubscriptionManagement.query.order_by(
                    SubscriptionManagement.next_order_date.desc()).all()

    return render_template(
        'wp_subscriptions.html',
        all_permissions=all_permissions,
        site_url=SITE_URL,
        subs_list=subs_list,
        WP_BASE_URL=WP_BASE_URL,
        wc_to_order_number=wc_to_order_number,
    )


@main.app_template_filter()
def wc_to_order_number(wc_id, multiple=False):
    val = WcIdOrderNumberMapping.get_order_number_by_wc_id(
            wc_id, is_multiple=multiple)
    return val


@main.route('/wc/webhooks/product', methods=["POST", "GET"])  # WooCommerce Product Webhook
def wc_webhooks_product():
    try:
        msg = None
        data = request.json
        n_data = json.dumps(data)
        headers = request.headers
        webhook_signature = headers.get("x-wc-webhook-signature", '')
        webhook_delivery_id = headers.get('X-WC-Webhook-Delivery-ID', '')
        webhook_resource = headers.get('X-WC-Webhook-Resource', '')
        notif_id = webhook_delivery_id + '-' + webhook_signature

        # Check if duplicate webhook notification
        wn = WebhookNotification.query.get(notif_id)
        if wn:
            print("WebhookNotication DUPLICATE request")
            print("previous notif value = %s" % str(wn.__dict__))
            return make_response('DUPLICATE REQUEST!!')
        else:
            print("FRESH WebhookNotification. Save.")

            # save notification
            wn = WebhookNotification(
                notification_id=notif_id,
                notification_body=n_data
            )
            db.session.add(wn)
            db.session.commit()
            print(wn.notification_id)

        # Verification of webhook
        verified_payload = verify_wc_payload(  # boolean
                request.get_data(),     # payload
                WC_WEBHOOK_SECRET,      # secret from wc webhook
                webhook_signature       # signature from response header
            )
        if not verified_payload:
            msg = 'Payload Verification failed'
            print(msg)
            return make_response(msg)

        validator_keys = ['id', 'name', 'status', 'permalink']
        valid_product_data = all(i in data for i in validator_keys)  # boolean

        if webhook_resource != 'product' or not valid_product_data:
            return_msg = 'request.json = %s -- No valid data hence quitting' % n_data
            return make_response(return_msg)

        print("WooCommerce product received")
        # converting WC product into SquareSpace form
        product = get_prod_sqrspc_form(data)
        instance = Product.query.filter_by(product_id=product.get('id')).first()
        if instance:
            instance_is_visible = True if instance.is_visible == 1 else False
            if (instance.product_name != product.get('name') or
                    instance_is_visible != product.get('isVisible') or
                    instance.product_url != product.get('url') or
                    instance.has_subscription != product.get('has_subscription') or
                    instance.subs_period != product.get('subs_period') or
                    instance.subs_period_interval != product.get('subs_period_interval')
                   ):
                instance.product_name = product.get('name')
                instance.is_visible = product.get('isVisible')
                instance.product_url = product.get('url')
                instance.has_subscription = product.get('has_subscription')
                instance.subs_period = product.get('subs_period')
                instance.subs_period_interval = product.get('subs_period_interval')
                instance.updated_on = datetime.datetime.now()
                db.session.commit()
                msg = "Product %s updated" % product.get('name')
            else:
                msg = "Product %s NOT updated. All attributes same." % product.get('name')
        else:
            print("Insert new product")
            instance = Product(
                product_id=product.get('id'),
                product_name=product.get('name'),
                is_visible=product.get('isVisible'),
                product_url=product.get('url'),
                has_subscription=product.get('has_subscription'),
                subs_period=product.get('subs_period'),
                subs_period_interval=product.get('subs_period_interval'),
                created_on=datetime.datetime.now(),
                updated_on=datetime.datetime.now()
            )
            db.session.add(instance)
            db.session.commit()
            msg = "Product %s %s inserted" % (product.get('id'), product.get('name'))

        print(msg)
    except Exception as e:
        msg = 'Exception found in order_webhook: '+ str(e)

        exc_type, exc_obj, tb = sys.exc_info()
        print('Webhook Traceback:', exc_obj)

        local_vars = {}
        while tb:
            filename = tb.tb_frame.f_code.co_filename
            name = tb.tb_frame.f_code.co_name
            line_no = tb.tb_lineno
            print(f"File {filename} line {line_no}, in {name}")

            local_vars = tb.tb_frame.f_locals
            tb = tb.tb_next
        # print("Local variables in top frame:", local_vars)
        return make_response(msg)
    else:
        if not msg:
            msg = "Successfully handled"
        return make_response(msg)


