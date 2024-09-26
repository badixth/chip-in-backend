from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import logging

# Initialize logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# Enable CORS for your Shopify domain
CORS(app, resources={r"/*": {"origins": "https://www.vamos.com.my"}},
     supports_credentials=True, 
     methods=["GET", "POST", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization"])

# Route to create a Chip In purchase session
@app.route('/create-chip-in-session', methods=['POST'])
def create_chip_in_session():
    try:
        # Get the cart data from the POST request
        order_data = request.json

        # Chip In API URL
        chip_in_url = "https://gate.chip-in.asia/api/v1/purchases/"
        
        # Your Chip In API key
        api_key = "GL0wFCcFob5IgIIY2qsWfUtx1W27Wfm5Q2uoITFxo5QkLtjSxEHEh0ekux3VXIf8quVQo7IaoPdiuztmTDzmpw=="  # Replace with your actual API key
        
        # Prepare the headers and data to send to Chip In
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        # Prepare the payload based on the cart data
        payload = {
            "client": {
                "email": "guest@gmail.com",  # Placeholder or email for guest users
                "phone": "",  # Optional field
                "full_name": "Guest"  # Placeholder name
            },
            "purchase": {
                "products": [
                    {"name": item['name'], "price": item['price']} for item in order_data['items']
                ],
                "currency": "MYR"  # Add currency if needed
            },
            "brand_id": "4e89ff13-b543-4c3d-9763-caa6026acab3"  # Replace with your Chip In brand ID
        }

        # Send the request to Chip In API to create the payment session
        response = requests.post(chip_in_url, json=payload, headers=headers)

        # Log the full response for debugging purposes
        logging.info(f"Chip In API Response: {response.text}")

        # Parse the response JSON
        response_data = response.json()

        # Check if a checkout URL is present, regardless of any error messages
        checkout_url = response_data.get('checkout_url')
        if checkout_url:
            # Return the checkout URL to the frontend
            return jsonify({'checkout_url': checkout_url}), 200
        else:
            # If no checkout URL is found, return the error message
            return jsonify({'error': 'Failed to create Chip In session', 'details': response.text}), 400

    except Exception as e:
        # Return error in case of any exception
        return jsonify({'error': str(e)}), 500


# Start the Flask server
if __name__ == '__main__':
    app.run(debug=True)