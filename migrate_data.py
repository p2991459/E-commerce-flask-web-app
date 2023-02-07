#! /usr/bin/python3.10
"""
    This Python Script Takes data from Thirdparty API 
    And send to the Another API

    This file migrates Products and Orders
    use: python data-migration.py products|orders
"""

import requests
import json
import sys
import click
import os
import re
from dotenv import load_dotenv
from datetime import datetime
import stripe  # to get info of order payment

load_dotenv()

WP_BASE_URL = os.getenv('BASE_URL', default='')
WP_AUTH_KEY = os.getenv('SECRET_KEY', default='')
SS_AUTH_KEY = ''
STRIPE_API_KEY = ''
OUT_FOLDER = '%s/%s' % ('out', datetime.now().strftime('%Y%m%d%H%M%S'))
if not os.path.exists(OUT_FOLDER):
    # Create a new directory because it does not exist
    os.makedirs(OUT_FOLDER)
    print("The new directory %s is created!" % OUT_FOLDER)


@click.command()
@click.option('-t', '--type', 'migration_type',
              required=True,
              type=click.Choice(['orders', 'products'], case_sensitive=False),
              help='Choose what to migrate.'
              )
@click.option("--non-existing", 'only_non_existing',
              is_flag=True,
              default=False,
              show_default=True,
              help="Migrate data which does not exist in WooCommerce Database",
              )
@click.option("-l", "--limit",
              type=int,
              help="Migrate limited data (for testing).",
              )
@click.option("-id", "specific_ids",
              multiple=True,
              help="Migrate only specific given SquareSpace ID. Allows multiple.",
              )
@click.option("--squarespace-key", "ss_key",
              required=True,
              help="Squarespace API key to fetch orders and products",
              )
@click.option("--stripe-key", "stripe_key",
              help="Live Stripe API key to fetch order payment info",
              )
def main(migration_type, only_non_existing, limit, specific_ids, ss_key, stripe_key):
    global SS_AUTH_KEY, STRIPE_API_KEY, OUT_FOLDER
    SS_AUTH_KEY = ss_key
    STRIPE_API_KEY = stripe_key


    if (migration_type == 'orders') and (STRIPE_API_KEY == None or STRIPE_API_KEY == ''):
        print('Order migration required valid --stripe-key arg.')
        return
    ss_data = list()
    if specific_ids:
        for ss_id in specific_ids:
            ss_data.append(fetch_data(migration_type, ss_id=ss_id))
        else:
            print('Data Fetching complete. Total: %s' % len(ss_data))
    else:
        ss_data = fetch_data(migration_type, limit)

    # todo: check if this order with same user id and same product have any subscription .
    send_data = send_order if migration_type == 'orders' else send_product

    existing_ss_ids = []
    if only_non_existing:
        url = "%swp-json/ssb-backend/v1/get_ss_existing_post_id" % WP_BASE_URL
        headers = {
            'authorization': "Basic %s" % WP_AUTH_KEY,
            'content-type': "application/json",
        }
        try:
            existing_ss_ids = requests.request("GET", url, headers=headers).json()
        except:
            print('Couldn\'t get exisitng IDs from Wocommerce')

    for data in ss_data:
        filename = ''
        if data['id'] not in existing_ss_ids:
            resp = send_data(data)
            print('Data Inserted Successfully.')
        else:
            filename = '-existing'
            # todo: improve: add wc id also in message to easy to know
            print('%s already exist in WooCommerce, Can\'t insert.' % data['id'])
            if migration_type == 'orders':
                # update the status of wooCommerce (existing)order as per SquareSpace order Status.
                print('updating...')
                status_dict = {
                    'PENDING': 'processing',
                    'FULFILLED': 'completed',
                    'CANCELED': 'cancelled'
                }
                update_payload = {
                    'status': status_dict[data['fulfillmentStatus']],
                    'date_completed': data['fulfilledOn']
                }
                print(update_wc_order(data['id'], update_payload))
        # dump a copy of the json to file for reference
        with open('%s/%s%s.json' % (OUT_FOLDER,
                                    data.get('orderNumber', 'unknown-%s' % datetime.now().strftime('%Y%m%d%H%M%S')),
                                    filename),
                  'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    print('EXECUTION DONE!!')


def fetch_data(data_type=None, limit=None, ss_id=None):  # type: orders, products
    print('Fetching squarespace data...')
    data_list = []
    stops = []
    label_texts = []
    data_holder_key = 'result' if data_type == 'orders' else 'products'
    url = 'third_party_api/%s/' % data_type
    if ss_id:
        url += ss_id
    headers = {
        'User-Agent': 'USER',
        'Authorization': 'Bearer %s' % SS_AUTH_KEY
    }
    r = requests.get(url, headers=headers)
    data_chunk = r.json()
    if ss_id and data_type == 'orders':
        return data_chunk
    if ss_id and data_type == 'products':
        return data_chunk['products'][0]
    else:
        data_list.extend(data_chunk[data_holder_key])
    if limit and len(data_list) >= limit:
        data_list = data_list[:limit]
    cnt = 0
    while 'pagination' in data_chunk and data_chunk["pagination"]["hasNextPage"]:
        if limit and len(data_list) >= limit:
            data_list = data_list[:limit]
            break
        url = "%s" % data_chunk["pagination"]["nextPageUrl"]
        cnt += 1
        print("%s Requesting %s" % (cnt, url))
        r = requests.get(url, headers=headers)
        data_chunk = r.json()
        data_list.extend(data_chunk[data_holder_key])

    if data_type == 'products':
        print('Fetching data completed. Total %s %s fetched.' % (len(data_list), data_type))
        return data_list
    else:
        # order the data_list based on orderNumber so that we have an ascending order of the list
        # This is important in subscription order migration from SquareSpace to WooCommerce where we want to have the
        # first order of the subscription insert first and then only the others
        ordered_data_list = sorted(data_list, key=lambda d: int(d['orderNumber']))
        print('Fetching data completed. Total %s %s fetched.' % (len(ordered_data_list), data_type))
        return ordered_data_list


def prepare_product_data(ss_data):
    wc_format = {}
    wc_format['id'] = ss_data['id']
    wc_format['name'] = ss_data['name']
    wc_format['description'] = ss_data['description']
    wc_format['type'] = ss_data['type']
    wc_format['date_created'] = ss_data['createdOn']
    wc_format['date_modified'] = ss_data['modifiedOn']
    wc_format['status'] = 'publish' if ss_data['isVisible'] else 'draft'
    wc_format['slug'] = re.sub('^p/', '', ss_data['urlSlug'])
    wc_format['meta_data'] = [{
        "key": "_ss_id",
        "value": ss_data['id']
    }]
    wc_format['images'] = []
    for img in ss_data['images']:
        wc_format['images'].append(img['url'])

    if len(ss_data['variantAttributes']):
        wc_format['var_attr'] = ss_data['variantAttributes']
        wc_format['is_variable'] = True
        variants = []
        attributes = {}
        for var in ss_data['variants']:
            tmp_var = {}
            tmp_var['sku'] = var['sku']
            tmp_var['image'] = var['image']['url']
            tmp_var['price'] = var['pricing']['basePrice']['value']
            tmp_var['stock_quantity'] = var['stock']['quantity']
            tmp_var['stock_unlimited'] = str(var['stock']['unlimited'])
            tmp_var['attr'] = {k.lower(): v.lower() for k, v in var['attributes'].items()}

            for nm, val in var['attributes'].items():
                nm, val = nm.lower(), val.lower()
                if nm in attributes:
                    if val not in attributes[nm]:
                        attributes[nm].append(val)
                else:
                    attributes[nm] = [val]
            variants.append(tmp_var)
        wc_format['variants'] = variants
        wc_format['attributes'] = attributes
    else:
        wc_format['is_variable'] = False
        main_variant = ss_data['variants'][0]
        wc_format['price'] = main_variant['pricing']['basePrice']['value']
        wc_format['sku'] = main_variant['sku']
        wc_format['stock_quantity'] = main_variant['stock']['quantity']
        wc_format['stock_unlimited'] = str(main_variant['stock']['unlimited'])
    return wc_format


def get_payment_info(order_id):
    payment_info = {}
    stripe.api_key = STRIPE_API_KEY
    stripe.api_version = "2022-08-01"
    payment_detail = stripe.Charge.search(query="metadata['id']:'%s'" % order_id)
    try:
        payment_detail = payment_detail.get('data', {})[0]
    except:
        pass
    payment_info['id'] = payment_detail.get('id')
    payment_info['captured'] = payment_detail.get('captured')
    payment_info['customer'] = payment_detail.get('customer')
    payment_info['currency'] = payment_detail.get('currency')
    payment_info['payment_method'] = payment_detail.get('payment_method')
    payment_info['payment_intent'] = payment_detail.get('payment_intent')
    created_on = payment_detail.get('created')
    try:
        fmt_str = r"%Y-%m-%dT%H:%M:%S.%f"  
        created_on = datetime.fromtimestamp(created_on)
        payment_info['created'] = created_on.strftime(fmt_str)
    except Exception as e:
        print(e)
        payment_info['created'] = ''
    return payment_info


def prepare_order_data(ss_data, payment_data):
    wc_format = {}
    status_dict = {
        'PENDING': 'processing',
        'FULFILLED': 'completed',
        'CANCELED': 'cancelled'
    }
    wc_format['id'] = ss_data['id']
    wc_format['parent_id'] = 0
    wc_format['user_email'] = ss_data.get('customerEmail')
    wc_format['status'] = status_dict[ss_data['fulfillmentStatus']]
    wc_format['currency'] = ss_data.get('subtotal', {}).get('currency')
    wc_format['date_created'] = ss_data['createdOn']
    wc_format['date_modified'] = ss_data['modifiedOn']
    wc_format['discount_total'] = ss_data.get('discountTotal', {}).get('value')
    wc_format['shipping_total'] = ss_data.get('shippingTotal', {}).get('value')
    wc_format['total'] = ss_data.get('grandTotal', {}).get('value')
    wc_format['total_tax'] = ss_data.get('taxTotal', {}).get('value')
    wc_format['order_key'] = ss_data['id']
    billing = ss_data.get('billingAddress') or {}

    wc_format['billing'] = {
        "first_name": billing.get('firstName') or '',
        "last_name": billing.get('lastName') or '',
        # "company": billing.get('') or '',
        "address_1": billing.get('address1') or '',
        "address_2": billing.get('address2') or '',
        "city": billing.get('city') or '',
        "state": billing.get('state') or '',
        "postcode": billing.get('postalCode') or '',
        "country": billing.get('countryCode') or '',
        "email": ss_data.get('customerEmail') or '',
        "phone": billing.get('phone') or ''
    }
    shipping = ss_data.get('shippingAddress') or {}
    wc_format['shipping'] = {
        "first_name": shipping.get('firstName') or '',
        "last_name": shipping.get('lastName') or '',
        "address_1": shipping.get('address1') or '',
        # "address_2": shipping.get('address2') or '',
        "city": shipping.get('city') or '',
        "state": shipping.get('state') or '',
        "postcode": shipping.get('postalCode') or '',
        "country": shipping.get('countryCode') or '',
        "phone": shipping.get('phone') or ''
    }
    wc_format['payment_method'] = 'stripe'
    wc_format['payment_method_title'] = 'Card (Stripe)'
    wc_format['transaction_id'] = payment_data.get('transaction_id')
    # wc_format['customer_ip_address'] = ''
    # wc_format['customer_user_agent'] = ''
    wc_format['created_via'] = ss_data['channelName']
    # wc_format['customer_note'] = ss_data['internalNotes']
    wc_format['date_completed'] = ss_data['fulfilledOn']
    wc_format['date_paid'] = payment_data.get('created', '')
    # wc_format['cart_hash'] = None
    wc_format['number'] = ss_data['orderNumber']
    wc_format['line_items'] = []
    for item in ss_data['lineItems']:
        temp_dict = {
            # "id": item['_________'],
            "name": item['productName'],
            "product_id": item['productId'],
            # "variation_id": item['variantId'],
            "qty": item['quantity'],
            # "tax_class": "",
            "subtotal": float(item['unitPricePaid']['value']),
            # "subtotal_tax": item['________'],
            "total": float(item['unitPricePaid']['value']) * item['quantity'],
            # "total_tax": item['________'],
            # "taxes": [
            #     {
            #         "id": item['________'],
            #         "total": item['________'],
            #         "subtotal": item['________'],
            #     }
            # ],
            # "meta_data": [],
            "sku": item['sku'],
            "price": float(item['unitPricePaid']['value']),
            "image": {
                # "id": item['________'],
                "src": item['imageUrl'],
            },
            # "parent_name": item['________'],
        }
        wc_format['line_items'].append(temp_dict)
    wc_format['tax_lines'] = [{
        "tax_total": ss_data['taxTotal']['value'],
    }]
    wc_format['shipping_lines'] = []
    for item in ss_data['shippingLines']:
        temp_dict = {
            "method_title": item['method'],
            "method_id": item['method'].replace(' ', '_'),
            "total": item['amount']['value']
        }

        wc_format['shipping_lines'].append(temp_dict)

    for dl in ss_data['discountLines']:
        if dl['promoCode'] == None and dl['name'] == '2022 Spring Flash Sale':
            dl['promoCode'] = '2022SpringFlashSale'
        wc_format['promoCode'] = dl['promoCode']
        break  # assuming one promo-code per order
    wc_format['meta_data'] = [
        {"key": "_ss_id", "value": ss_data['id']},
        {"key": "ss_orderNumber", "value": ss_data['orderNumber']},
        {"key": "_order_number", "value": ss_data['orderNumber']},  # for sequence plugin
        {"key": "is_migrated_order", "value": 1},
        {"key": "squarespace_id", "value": ss_data['id']},  # visible in order detail WC page
    ]
    if ss_data['formSubmission']:
        for form in ss_data['formSubmission']:
            if form['label'] == 'From':
                wc_format['meta_data'].append({
                    "key": 'order_from',
                    "value": form['value']
                })
            if form['label'] == 'To':
                wc_format['meta_data'].append({
                    "key": 'order_to',
                    "value": form['value']
                })
            if form['label'] == 'Where did you hear about us?':
                wc_format['meta_data'].append({
                    "key": 'order_source',
                    "value": form['value']
                })
            if form['label'] == 'Shipping Email':
                wc_format['meta_data'].append({
                    "key": 'shipping_email',
                    "value": form['value']
                })
            if form['label'] == 'Optional: Donation Code':
                wc_format['meta_data'].append({
                    "key": 'donation_code',
                    "value": form['value']
                })
            if form['label'] == 'ShoCo Member Username':
                wc_format['meta_data'].append({
                    "key": 'shoco_member_username',
                    "value": form['value']
                })
            if form['label'] in (
                    'Optional: Include a message for the recipient.',
                    'Optional: Add a Personal Note'):
                wc_format['meta_data'].append({
                    "key": form['label'],
                    "value": form['value']
                })

    wc_format['meta_data'].extend([
        {"key": "_stripe_customer_id", "value": payment_data.get('customer', '')},
        {"key": "_stripe_source_id", "value": payment_data.get('payment_method', '')},
        {"key": "_stripe_intent_id", "value": payment_data.get('payment_intent', '')},
        {"key": "_stripe_charge_captured", "value": payment_data.get('captured', '')},
        # {"key": "_stripe_fee", "value": payment_data.get('fee', '')},
        # {"key": "_stripe_net", "value": payment_data.get('net', '')},
        {"key": "_stripe_currency", "value": payment_data.get('currency', '')},
    ])

    try:
        ref_amount = float(ss_data.get('refundedTotal', {}).get('value'))
        if ref_amount > 0: wc_format['refund_amount'] = ref_amount
    except:
        pass

    return wc_format


def send_order(order_data):
    global OUT_FOLDER
    # prepare order data
    payment_info = get_payment_info(order_data.get('id'))
    order_data = prepare_order_data(order_data, payment_info)
    url = "%swp-json/ssb-backend/v1/ss_orders" % WP_BASE_URL

    headers = {
        'authorization': "Basic %s" % WP_AUTH_KEY,
        'content-type': "application/json",
    }

    with open('%s/%s-wc.json' % (OUT_FOLDER,
                                 order_data.get('number', 'unknown-%s' % datetime.now().strftime('%Y%m%d%H%M%S'))),
              'w', encoding='utf-8') as f:
        json.dump(order_data, f, ensure_ascii=False, indent=4)

    order_data = json.dumps(order_data)
    response = requests.request("POST", url, data=order_data, headers=headers)
    print(response.text)
    return response.text


def send_product(product_data):
    global OUT_FOLDER
    # prepare product data
    product_data = prepare_product_data(product_data)
    url = "%sURL" % WP_BASE_URL

    headers = {
        'authorization': "Basic %s" % WP_AUTH_KEY,
        'content-type': "application/json",
    }

    with open('%s/%s-wc.json' % (OUT_FOLDER,
                                 product_data.get('number', 'unknown-%s' % datetime.now().strftime('%Y%m%d%H%M%S'))),
              'w', encoding='utf-8') as f:
        json.dump(product_data, f, ensure_ascii=False, indent=4)

    product_data = json.dumps(product_data)
    print('Sending request to ThirdParty...')
    response = requests.request("POST", url, data=product_data, headers=headers)

    print(response.text)
    return response.text


def update_wc_order(order_id, payload):
    if not order_id or not payload:
        print('Invalid order ID or payload.')
        return
    url = "%sOrder_endpoint%s" % (WP_BASE_URL, order_id)
    headers = {
        'Authorization': 'Basic %s' % AUTH_KEY,
        'Content-Type': 'application/json'
    }
    r = requests.post(url,headers=headers, data=json.dumps(payload))
    if 200 <= r.status_code < 300:
        return_string = "Successfully Updated: %s" % order_id
    else:
        return_string = "Error, Status code: %s" % r.status_code
        print('WC error:', r.text)
    return return_string


if __name__ == '__main__':
    main()
