from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import logging

app = Flask(__name__)

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

        # Log the incoming payload for debugging
        logging.info(f"Received Payload: {order_data}")
        
        # Chip In API URL
        chip_in_url = "https://gate.chip-in.asia/api/v1/purchases/"
        
        # Your Chip In API key
        api_key = "GL0wFCcFob5IgIIY2qsWfUtx1W27Wfm5Q2uoITFxo5QkLtjSxEHEh0ekux3VXIf8quVQo7IaoPdiuztmTDzmpw=="  # Replace with your actual API key
        
        # Prepare the headers and data to send to Chip In
        headers = {
            "Authorization": f"Bearer {api_key}",
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
            "brand_id": "4e89ff13-b543-4c3d-9763-caa6026acab3"  # Replace with your Chip In brand ID
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
    print("Received Chip In webhook event:", data)

    # Check if the event type is 'purchase.paid' (which means payment was successful)
    if data.get('event_type') == 'purchase.paid':
        purchase_info = data.get('purchase', {})
        payment_info = data.get('payment', {})
        client_info = data.get('client', {})

        # Extract necessary details
        purchase_id = data.get('id')
        customer_name = client_info.get('full_name')
        total_amount = purchase_info.get('total', 0)
        payment_status = data.get('status')
        payment_method = data.get('transaction_data', {}).get('payment_method')
        email = client_info.get('email')
        phone = client_info.get('phone')
        shipping_address = client_info.get('shipping_street_address')
        products = purchase_info.get('products', [])

        # Log for debugging
        print(f"Purchase ID: {purchase_id}")
        print(f"Customer: {customer_name}")
        print(f"Total Amount: {total_amount}")
        print(f"Payment Status: {payment_status}")
        print(f"Payment Method: {payment_method}")
        print(f"Customer Email: {email}")
        print(f"Customer Phone: {phone}")
        print(f"Shipping Address: {shipping_address}")
        print(f"Products: {products}")

        # TODO: Add code here to update your order management system, save data to database, send an email, etc.

    # Return a success response to Chip In
    return jsonify({'status': 'success'}), 200

# Start the Flask server
if __name__ == '__main__':
    app.run(debug=True)