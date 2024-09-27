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

@app.route('/', methods=['GET'])
def index():
    return "Server is working!"

# Route to create a Chip In purchase session
@app.route('/create-chip-in-session', methods=['POST'])
def create_chip_in_session():
    try:
        # Get the cart data and form data from the POST request
        order_data = request.json
        shopify_order_id = order_data.get("order_id")  # Capture the Shopify Order ID

        # Log the incoming payload for debugging
        logging.info(f"Received Payload: {order_data}")
        
        # Chip In API URL
        chip_in_url = "https://gate.chip-in.asia/api/v1/purchases/"
        
        # Prepare the headers and data to send to Chip In
        headers = {
            "Authorization": f"Bearer {CHIP_IN_API_KEY}",  # Use API key from environment
            "Content-Type": "application/json"
        }

        # Prepare the payload for the Chip In API
        payload = {
            "client": {
                "email": order_data["email"],
                "phone": order_data["phone"],
                "full_name": order_data["name"]
            },
            "purchase": {
                "products": [
                    {"name": item['name'], "price": item['price'], "quantity": item['quantity']} for item in order_data['items']
                ],
                "currency": "MYR"
            },
            "notes": order_data.get("notes", ""),
            "brand_id": CHIP_IN_BRAND_ID,  # Use Chip In brand ID
            "custom_fields": {
                "shopify_order_id": shopify_order_id  # Pass Shopify Order ID to Chip In
            }
        }

        logging.info(f"Payload sent to Chip In API: {payload}")

        # Send the request to Chip In API to create the payment session
        response = requests.post(chip_in_url, json=payload, headers=headers)
        response_data = response.json()

        logging.info(f"Chip In API Response: {response_data}")

        # Check if a checkout URL is present, return it to frontend
        checkout_url = response_data.get('checkout_url')
        if checkout_url:
            return jsonify({'checkout_url': checkout_url}), 200
        else:
            return jsonify({'error': 'Failed to create Chip In session', 'details': response.text}), 400

    except Exception as e:
        logging.error(f"Error processing payment: {e}")
        return jsonify({'error': str(e)}), 500


# Webhook endpoint to receive payment events
@app.route('/chipin-webhook', methods=['POST'])
def chipin_webhook():
    data = request.json  # Get the JSON payload sent by Chip In

    # Log the received data for debugging purposes
    logging.info(f"Received Chip In webhook event: {data}")

    # Check if the event type is 'purchase.paid'
    if data.get('event_type') == 'purchase.paid':
        shopify_order_id = data.get('custom_fields', {}).get('shopify_order_id')  # Retrieve Shopify order_id

        # Check if Shopify order_id exists, then update the Shopify order status
        if shopify_order_id:
            if update_shopify_order_status(shopify_order_id, 'paid'):  # Update the status to 'paid'
                logging.info(f"Shopify order {shopify_order_id} marked as paid.")
                return jsonify({'status': 'success'}), 200
            else:
                logging.warning(f"Failed to update Shopify order: {shopify_order_id}")
                return jsonify({'error': 'Failed to update Shopify order'}), 400
        else:
            logging.warning("No Shopify order_id found in the webhook event.")
            return jsonify({'error': 'Shopify order_id missing'}), 400
            
    
    # If the event is not a 'purchase.paid', ignore it
    return jsonify({'status': 'ignored'}), 200


# Function to update Shopify order status
def update_shopify_order_status(order_id, status):
    shopify_order_url = f"https://{SHOPIFY_STORE_URL}/admin/api/2023-01/orders/{order_id}.json"

    headers = {
        "X-Shopify-Access-Token": SHOPIFY_API_KEY,  # Use access token as API key in the header
        "Content-Type": "application/json"
    }
    
    payload = {
        "order": {
            "id": order_id,
            "financial_status": status  # Possible values: 'paid', 'pending', etc.
        }
    } 

    response = requests.put(shopify_order_url, json=payload, headers=headers)
    
    if response.status_code == 200:
        logging.info(f"Order {order_id} updated successfully in Shopify.")
        return True
    else:
        logging.error(f"Failed to update order in Shopify. Status Code: {response.status_code}")
        return False


# Start the Flask server
if __name__ == '__main__':
    app.run(debug=True)