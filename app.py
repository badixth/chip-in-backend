from flask import Flask, request, jsonify
from sqlalchemy.orm import sessionmaker
from models import Order, engine, Session
from dotenv import load_dotenv
import os
from flask_cors import CORS
import requests
import logging
import traceback  # For stack trace

app = Flask(__name__)

# Load the .env file
load_dotenv()

# Load Shopify and Chip In credentials from environment variables
SHOPIFY_API_KEY = os.getenv('SHOPIFY_API_KEY')  # This is now the access token
SHOPIFY_STORE_URL = os.getenv('SHOPIFY_STORE_URL')
CHIP_IN_API_KEY = os.getenv('CHIP_IN_API_KEY')
CHIP_IN_BRAND_ID = os.getenv('CHIP_IN_BRAND_ID')

# Use the session from models.py
session = Session()

# Enable CORS for the Shopify domain
CORS(app, resources={r"/*": {"origins": "*"}},
     supports_credentials=True,
     methods=["GET", "POST", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization"])

# Setup logging to display incoming payloads
logging.basicConfig(level=logging.INFO)
logging.info(f"CHIP_IN_BRAND_ID: {CHIP_IN_BRAND_ID}")

@app.route('/create-chip-in-session', methods=['POST'])
def create_chip_in_session():
    try:
        data = request.get_json()
        
        # Extract required fields
        full_name = data.get('name')
        email = data.get('email')
        phone = data.get('phone')
        shipping_address = data.get('shipping_address')
        notes = data.get('notes', '')
        items = data.get('items')
        logging.info(f"order items: {items}")
        shopify_order_id = data.get("order_id")
        
        # Split full_name into first_name and last_name
        name_parts = full_name.split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""
        
        if not all([first_name, email, phone, shipping_address, items]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        headers = {
            "X-Shopify-Access-Token": SHOPIFY_API_KEY,
            "Content-Type": "application/json"
        }
        
        customer = find_shopify_customer_by_phone(phone)
        
        if customer:
            response = requests.get(f"{SHOPIFY_STORE_URL}/admin/api/2024-10/customers/{customer['id']}.json", headers=headers)
            logging.info(f"Before update customer: {response.json()}")
            
            data = {
                "customer": {
                    "id": customer["id"],
                    "email": email,
                    "first_name": first_name,
                    "last_name": last_name,
                },
            }
            response = requests.put(f"{SHOPIFY_STORE_URL}/admin/api/2024-10/customers/{customer['id']}.json", json=data, headers=headers)
            logging.info(f"POST customer information update: {response.content}")
        
        chip_in_url = "https://gate.chip-in.asia/api/v1/purchases/"
        headers = {
            "Authorization": f"Bearer {CHIP_IN_API_KEY}",
            "Content-Type": "application/json"
        }
        
        address1 = shipping_address.get('address1')
        city = shipping_address.get('city')
        province = shipping_address.get('province')
        zip_code = shipping_address.get('zip')
        country = shipping_address.get('country')

        payload = {
            "client": {
                "email": email,
                "phone": phone,
                "full_name": full_name,
                "first_name": first_name,
                "last_name": last_name,
                "shipping_street_address": address1,
                "shipping_country": country,
                "shipping_city": city,
                "shipping_zip_code": zip_code,
                "shipping_state": province,
            },
            "purchase": {
                "products": [
                    {"name": item['name'], "price": int(item['price']*100), "quantity": item['quantity'], "category": item["variant_id"]} for item in items
                ],
                "currency": "MYR"
            },
            "notes": notes,
            "brand_id": CHIP_IN_BRAND_ID
        }

        logging.info(f"Payload sent to Chip In API: {payload}")
        response = requests.post(chip_in_url, json=payload, headers=headers)
        response_data = response.json()
        
        if response.status_code == 201 and response_data.get('checkout_url'):
            return jsonify({'checkout_url': response_data['checkout_url']}), 201
        else:
            return jsonify({'error': 'Failed to create Chip In session', 'details': response_data}), 400
    except Exception as e:
        logging.error(f"Error in create_chip_in_session: {e}")
        logging.error(traceback.format_exc())  # Log the full stack trace
        return jsonify({'error': str(e)}), 500


@app.route('/chipin-webhook', methods=['POST'])
def chipin_webhook():
    try:
        data = request.get_json()
        logging.info(f"Received Chip In webhook event: {data}")
        
        if data.get('status') == 'paid':
            shopify_order_response = create_shopify_order(
                name=data['client']['full_name'],
                email=data['client']['email'],
                phone=data['client']['phone'],
                shipping_address={
                    "address1": data['client']['shipping_street_address'],
                    "city": data['client']['shipping_city'],
                    "province": data['client']['shipping_state'],
                    "zip": data['client']['shipping_zip_code'],
                    "country": "MY",
                    "phone": data['client']['phone'],
                },
                items=data['purchase']['products']
            )

            if shopify_order_response:
                return jsonify({'status': 'success'}), 200
            else:
                return jsonify({'error': 'Failed to create Shopify order'}), 400
        else:
            return jsonify({'status': 'ignored'}), 200
    except Exception as e:
        logging.error(f"Error in chipin_webhook: {e}")
        logging.error(traceback.format_exc())  # Log the full stack trace
        return jsonify({'error': str(e)}), 500


def find_shopify_customer_by_phone(phone):
    try:
        shopify_customer_search_url = f"{SHOPIFY_STORE_URL}/admin/api/2024-10/customers/search.json?query=phone:{phone}"
        headers = {
            "X-Shopify-Access-Token": SHOPIFY_API_KEY,
            "Content-Type": "application/json"
        }
        response = requests.get(shopify_customer_search_url, headers=headers)
        
        if response.status_code == 200:
            customers = response.json().get("customers", [])
            if customers:
                return customers[0]
        
        if phone.startswith("+60"):
            phone_without_country_code = phone[3:]
            shopify_customer_search_url = f"{SHOPIFY_STORE_URL}/admin/api/2024-10/customers/search.json?query=phone:{phone_without_country_code}"
            response = requests.get(shopify_customer_search_url, headers=headers)
            
            if response.status_code == 200:
                customers = response.json().get("customers", [])
                if customers:
                    return customers[0]

        return None
    except Exception as e:
        logging.error(f"Error in find_shopify_customer_by_phone: {e}")
        logging.error(traceback.format_exc())  # Log the full stack trace
        return None


def create_shopify_order(name, email, phone, shipping_address, items, financial_status="paid"):
    try:
        customer = find_shopify_customer_by_phone(phone)
        shopify_order_url = f"{SHOPIFY_STORE_URL}/admin/api/2024-10/orders.json"
        headers = {
            "X-Shopify-Access-Token": SHOPIFY_API_KEY,
            "Content-Type": "application/json"
        }

        name_parts = name.split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        if customer:
            order_data = {
                "order": {
                    "financial_status": financial_status,
                    "customer": {
                        "id": customer["id"],
                        "first_name": first_name,
                        "last_name": last_name,
                    },
                    "line_items": [
                        {"title": item["name"], "quantity": int(float(item["quantity"])), "price": item["price"]/100, "variant_id": item["category"]} for item in items
                    ],
                    "shipping_address": {
                        "first_name": first_name,
                        "last_name": last_name,
                        "address1": shipping_address['address1'],
                        "city": shipping_address['city'],
                        "province": shipping_address['province'],
                        "zip": shipping_address['zip'],
                        "country": "MY",
                        "phone": phone
                    },
                    "note": "Order created via custom payment integration",
                    "send_receipt": True
                }
            }
        else:
            order_data = {
                "order": {
                    "email": email,
                    "phone": phone,
                    "financial_status": financial_status,
                    "customer": {
                        "first_name": first_name,
                        "last_name": last_name,
                        "email": email,
                        "phone": phone
                    },
                    "line_items": [
                        {"title": item["name"], "quantity": int(float(item["quantity"])), "price": item["price"]/100, "variant_id": item["category"]} for item in items
                    ],
                    "shipping_address": {
                        "first_name": first_name,
                        "last_name": last_name,
                        "address1": shipping_address['address1'],
                        "city": shipping_address['city'],
                        "province": shipping_address['province'],
                        "zip": shipping_address['zip'],
                        "country": "MY",
                        "phone": phone
                    },
                    "note": "Order created via custom payment integration",
                    "send_receipt": True
                }
            }

        response = requests.post(shopify_order_url, json=order_data, headers=headers)
        if response.status_code == 201:
            return response.json()
        else:
            return None
    except Exception as e:
        logging.error(f"Error in create_shopify_order: {e}")
        logging.error(traceback.format_exc())  # Log the full stack trace
        return None


# Start the Flask server
if __name__ == '__main__':
    try:
        register_shopify_webhook()  # Register webhook at server start if needed
        app.run(debug=True)
    except Exception as e:
        logging.error(f"Error starting the Flask app: {e}")
        logging.error(traceback.format_exc())  # Log the full stack trace