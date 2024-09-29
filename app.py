from flask import Flask, request, jsonify
from sqlalchemy.orm import sessionmaker
from models import Order, engine, Session
from dotenv import load_dotenv
import os
from flask_cors import CORS
import requests
import logging

app = Flask(__name__)

# Load the .env file
load_dotenv()

# Load Shopify and Chip In credentials from environment variables
SHOPIFY_API_KEY = os.getenv('SHOPIFY_API_KEY')
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


# Helper functions for reusability

def split_full_name(full_name):
    """Split full name into first_name and last_name."""
    name_parts = full_name.split(" ", 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ""
    return first_name, last_name


def format_line_items(items):
    """Format line items to match Shopify's required structure."""
    return [
        {
            "title": item["name"],
            "quantity": int(float(item["quantity"])),
            "price": item["price"]
        } for item in items
    ]


def format_shipping_address(shipping_address, first_name, last_name):
    """Format the shipping address as per Shopify's requirements."""
    return {
        "first_name": first_name,
        "last_name": last_name,
        "address1": shipping_address.get('address1', ''),
        "city": shipping_address.get('city', ''),
        "province": shipping_address.get('province', ''),
        "zip": shipping_address.get('zip', ''),
        "country": shipping_address.get('country', '')
    }


# Customer lookup or creation

def find_or_create_customer(first_name, last_name, email, phone):
    """Find a customer by phone or email, or create a new customer if not found."""
    shopify_search_customer_by_phone_url = f"{SHOPIFY_STORE_URL}/admin/api/2023-04/customers/search.json?query=phone:{phone}"
    shopify_search_customer_by_email_url = f"{SHOPIFY_STORE_URL}/admin/api/2023-04/customers/search.json?query=email:{email}"
    shopify_customer_url = f"{SHOPIFY_STORE_URL}/admin/api/2023-04/customers.json"
    
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_API_KEY,
        "Content-Type": "application/json"
    }
    
    # Step 1: Search for customer by phone
    response_by_phone = requests.get(shopify_search_customer_by_phone_url, headers=headers)
    if response_by_phone.status_code == 200 and response_by_phone.json().get('customers'):
        return response_by_phone.json()['customers'][0]['id']

    # Step 2: Search for customer by email
    response_by_email = requests.get(shopify_search_customer_by_email_url, headers=headers)
    if response_by_email.status_code == 200 and response_by_email.json().get('customers'):
        return response_by_email.json()['customers'][0]['id']

    # Step 3: Create a new customer if none found
    customer_data = {
        "customer": {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": phone
        }
    }
    customer_response = requests.post(shopify_customer_url, json=customer_data, headers=headers)
    if customer_response.status_code == 201:
        return customer_response.json()['customer']['id']
    else:
        logging.error(f"Failed to create customer: {customer_response.text}")
        return None


# Order creation or updating

def create_shopify_order(full_name, email, phone, shipping_address, items, financial_status="paid"):
    """Create or update a Shopify order."""
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_API_KEY,
        "Content-Type": "application/json"
    }
    
    # Split full name into first_name and last_name
    first_name, last_name = split_full_name(full_name)
    
    # Find or create customer
    customer_id = find_or_create_customer(first_name, last_name, email, phone)
    if not customer_id:
        return None

    # Format the order data
    order_data = {
        "order": {
            "customer_id": customer_id,
            "financial_status": financial_status,
            "line_items": format_line_items(items),
            "shipping_address": format_shipping_address(shipping_address, first_name, last_name),
            "note": "Order created via custom payment integration"
        }
    }

    # Send the order creation request
    shopify_order_url = f"{SHOPIFY_STORE_URL}/admin/api/2023-04/orders.json"
    order_response = requests.post(shopify_order_url, json=order_data, headers=headers)

    if order_response.status_code == 201:
        logging.info(f"Shopify order created successfully: {order_response.json()}")
        return order_response.json()
    else:
        logging.error(f"Failed to create order: {order_response.text}")
        return None


# Webhook handlers

@app.route('/chipin-webhook', methods=['POST'])
def chipin_webhook():
    try:
        data = request.get_json()
        logging.info(f"Received Chip In webhook event: {data}")

        # Extract relevant fields
        payment_status = data.get('status')
        chip_in_order_id = data.get('id')
        client = data.get('client', {})
        purchase = data.get('purchase', {})
        
        # Only proceed if payment is 'paid'
        if payment_status == 'paid':
            logging.info(f"Chip In order {chip_in_order_id} has been paid. Updating Shopify order.")
            
            # Extract details
            full_name = client.get('full_name')
            email = client.get('email')
            phone = client.get('phone')
            shipping_address = {
                'address1': client.get('shipping_street_address', ''),
                'city': client.get('shipping_city', ''),
                'province': client.get('shipping_state', ''),
                'zip': client.get('shipping_zip_code', ''),
                'country': client.get('shipping_country', '')
            }
            items = purchase.get('products', [])
            
            # Create or update Shopify order
            shopify_order_response = create_shopify_order(full_name, email, phone, shipping_address, items, financial_status='paid')

            if shopify_order_response:
                return jsonify({'status': 'success', 'shopify_order_id': shopify_order_response.get('order', {}).get('id')}), 200
            else:
                return jsonify({'error': 'Failed to create/update Shopify order'}), 400
        else:
            return jsonify({'status': 'ignored'}), 200

    except Exception as e:
        logging.error(f"Error processing Chip In webhook: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/', methods=['GET'])
def index():
    return "Server is working!"


def register_shopify_webhook():
    """Register a webhook with Shopify for order paid events."""
    shopify_webhook_url = f"{SHOPIFY_STORE_URL}/admin/api/2023-04/webhooks.json"
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_API_KEY,
        "Content-Type": "application/json"
    }

    webhook_data = {
        "webhook": {
            "topic": "orders/paid",
            "address": "https://your-server-url/shopify-webhook",  # Update with your actual server URL
            "format": "json"
        }
    }

    response = requests.post(shopify_webhook_url, json=webhook_data, headers=headers)

    if response.status_code == 201:
        logging.info("Webhook registered successfully")
    else:
        logging.error(f"Failed to register webhook: {response.status_code}, {response.text}")


@app.route('/shopify-webhook', methods=['POST'])
def shopify_webhook():
    try:
        data = request.get_json()
        logging.info(f"Received Shopify webhook event: {data}")

        # First try to get the ID at the root level
        shopify_order_id = data.get('id')

        # Get the financial status from the payload
        financial_status = data.get('financial_status')

        # Check if the financial status is 'paid'
        if financial_status == 'paid':
            logging.info(f"Shopify order {shopify_order_id} has been paid.")
            return jsonify({'status': 'success', 'order_id': shopify_order_id}), 200
        else:
            logging.warning(f"Shopify order {shopify_order_id} financial status: {financial_status}")
            return jsonify({'status': 'ignored'}), 200

    except Exception as e:
        logging.error(f"Error processing Shopify webhook: {e}")
        return jsonify({'error': str(e)}), 500


# Start the Flask server
if __name__ == '__main__':
    register_shopify_webhook