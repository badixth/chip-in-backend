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
load_dotenv()  # This loads the .env file

# Load Shopify and Chip In credentials from environment variables
SHOPIFY_API_KEY = os.getenv('SHOPIFY_API_KEY') # This is now the access token
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
        # Step 1: Get the JSON data sent from the frontend
        try:
            data = request.get_json()
        except Exception as e:
            return jsonify({'error': 'Invalid JSON data', 'details': str(e)}), 400

        # Step 2: Extract the required fields from the incoming data
        full_name = data.get('name')
        email = data.get('email')
        phone = data.get('phone')
        shipping_address = data.get('shipping_address')
        notes = data.get('notes', '')  # Optional field with default value of empty string
        items = data.get('items')
        shopify_order_id = data.get("order_id")  # Capture the Shopify Order ID

        # Step 3: Split full_name into first_name and last_name
        name_parts = full_name.split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""  # Handle cases where no last name is provided


        # Step 3.1: Check if all required fields are present
        if not all([first_name, email, phone, shipping_address, items]):
            return jsonify({'error': 'Missing required fields'}), 400

        # Step 4: Prepare the payload for Chip In API
        chip_in_url = "https://gate.chip-in.asia/api/v1/purchases/"
        
        headers = {
            "Authorization": f"Bearer {CHIP_IN_API_KEY}",
            "Content-Type": "application/json"
        }

        # Extract the shipping address parts properly
        address1 = shipping_address.get('address1')
        city = shipping_address.get('city')
        province = shipping_address.get('province')
        zip_code = shipping_address.get('zip')
        country = shipping_address.get('country')

        payload = {
            "client": {
                "email": email,
                "phone": phone,
                "full_name": full_name,  # Send full name to Chip In if required
                "first_name": first_name,  # Optionally send first and last names separately if needed
                "last_name": last_name,
                "street_address": address1,
                "country": province,
                "city": city,
                "zip_code": zip_code,
                "state": province,
                "shipping_street_address": address1,
                "shipping_country": country,
                "shipping_city": city,
                "shipping_zip_code": zip_code,
                "shipping_state": province,
                "personal_code": notes
            },
            "purchase": {
                "products": [
                    {"name": item['name'], "price": int(item['price']), "quantity": item['quantity']} for item in items
                ],
                "currency": "MYR"
            },
            "notes": notes,
            "brand_id": CHIP_IN_BRAND_ID,
            #"shipping_address": {
            #    "address1": address1,
            #    "city": city,
            #    "province": province,
            #    "zip": zip_code,
            #    "country": country
            
        }

        # Log the outgoing payload for debugging
        logging.info(f"Payload sent to Chip In API: {payload}")

        # Step 5: Send the request to Chip In API
        response = requests.post(chip_in_url, json=payload, headers=headers)
        response_data = response.json()

        # Log the response from Chip In API for debugging
        logging.info(f"Chip In API Response: {response_data}")

        # Check if the response status is successful
        if response.status_code == 201 and response_data.get('checkout_url'):
            return jsonify({'checkout_url': response_data['checkout_url']}), 201
        else:
            return jsonify({
                'error': 'Failed to create Chip In session',
                'details': response_data
            }), 400


    except Exception as e:
        # Log the error for debugging
        logging.error(f"Error processing payment: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/chipin-webhook', methods=['POST'])
def chipin_webhook():
    try:
        # Get the JSON data from the POST request sent by Chip In
        data = request.get_json()
        logging.info(f"Received Chip In webhook event: {data}")

        # Extract relevant fields from the webhook data
        payment_status = data.get('status')
        chip_in_order_id = data.get('id')  # Chip In order ID
        client = data.get('client', {})
        purchase = data.get('purchase', {})

        # Extract customer details
        full_name = client.get('full_name')
        email = client.get('email')
        phone = client.get('phone')

        # Extract shipping address from Chip In (you might need to adjust this based on Chip In's actual response)
        address1 = client.get('shipping_street_address', '')
        city = client.get('shipping_city', '')
        province = client.get('shipping_state', '')
        zip_code = client.get('shipping_zip_code', '')
        country = client.get('shipping_country', '')

        # Extract order items from Chip In
        items = purchase.get('products', [])
        
        # Only proceed if the payment status is 'paid'
        if payment_status == 'paid':
            logging.info(f"Chip In order {chip_in_order_id} has been paid. Updating Shopify order.")

            # Here you will create or update the order in Shopify using the previously captured order ID or details.
            # Assuming `shopify_order_id` is captured earlier, you can call your `update_shopify_order_status` or create a new order.

            # Create or update the Shopify order
            shopify_order_response = create_shopify_order(
                name=full_name,
                email=email,
                phone=phone,
                shipping_address={
                    'address1': address1,
                    'city': city,
                    'province': province,
                    'zip': zip_code,
                    'country': country
                },
                items=items,
                financial_status='paid'  # Mark the order as paid
            )

            if shopify_order_response:
                logging.info(f"Shopify order created or updated successfully: {shopify_order_response}")
                return jsonify({'status': 'success', 'shopify_order_id': shopify_order_response.get('order', {}).get('id')}), 200
            else:
                return jsonify({'error': 'Failed to create/update Shopify order'}), 400
        else:
            logging.warning(f"Chip In order {chip_in_order_id} is not marked as paid. Status: {payment_status}")
            return jsonify({'status': 'ignored'}), 200

    except Exception as e:
        logging.error(f"Error processing Chip In webhook: {e}")
        return jsonify({'error': str(e)}), 500



@app.route('/', methods=['GET'])
def register_shopify_webhook():
    shopify_webhook_url = f"{SHOPIFY_STORE_URL}/admin/api/2023-04/webhooks.json"
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_API_KEY,
        "Content-Type": "application/json"
    }

    webhook_data = {
        "webhook": {
            "topic": "orders/paid",
            "address": "https://chip-in-backend-4531.onrender.com/shopify-webhook",  # Update with your actual server URL
            "format": "json"
        }
    }

    response = requests.post(shopify_webhook_url, json=webhook_data, headers=headers)

if response.status_code == 201:
        logging.info("Webhook registered successfully")
        return jsonify({"message": "Webhook registered successfully"}), 201
    elif response.status_code == 422:
        logging.error(f"Webhook already exists: {response.status_code}, {response.text}")
        return jsonify({"error": "Webhook already exists"}), 422
    else:
        logging.error(f"Failed to register webhook: {response.status_code}, {response.text}")
        return jsonify({"error": "Failed to register webhook"}), response.status_code       

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




def create_shopify_order(name, email, phone, shipping_address, items, financial_status="paid"):
    # Shopify API URL
    shopify_order_url = f"{SHOPIFY_STORE_URL}/admin/api/2023-04/orders.json"

    headers = {
        "X-Shopify-Access-Token": SHOPIFY_API_KEY,
        "Content-Type": "application/json"
    }

    # Split full name into first_name and last_name
    name_parts = name.split(" ", 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    # Prepare the order payload
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
                {"title": item["name"], "quantity": int(float(item["quantity"])), "price": item["price"]} for item in items
            ],
            "shipping_address": {
                "first_name": first_name,
                "last_name": last_name,
                "address1": shipping_address.get('address1', ''),
                "city": shipping_address.get('city', ''),
                "province": shipping_address.get('province', ''),
                "zip": shipping_address.get('zip', ''),
                "country": shipping_address.get('country', '')
            },
            "note": "Order created via custom payment integration"
        }
    }

    response = requests.post(shopify_order_url, json=order_data, headers=headers)
    
    # Log the response for debugging
    print(response.json())

    if response.status_code == 201:
        logging.info(f"Shopify order created successfully: {response.json()}")
        return response.json()  # Return the created order details
    else:
        logging.error(f"Failed to create order in Shopify. Status Code: {response.status_code}, Response: {response.text}")
        print(f"Failed to create order: {response.status_code}")
        return None


# Start the Flask server
if __name__ == '__main__':
    register_shopify_webhook()  # Register webhook at server start
    app.run(debug=True)