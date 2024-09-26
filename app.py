from flask import Flask, request, jsonify
from flask_cors import CORS  # Import Flask-CORS
import requests

app = Flask(__name__)
CORS(app)

# Route to create a Chip In purchase session
@app.route('/create-chip-in-session', methods=['POST'])
def create_chip_in_session():
    # Get the cart data from the POST request
    order_data = request.json
    
    # Chip In API URL
    chip_in_url = "https://gate.chip-in.asia/api/v1/purchases/"
    
    # Your Chip In API key
    api_key = "GL0wFCcFob5IgIIY2qsWfUtx1W27Wfm5Q2uoITFxo5QkLtjSxEHEh0ekux3VXIf8quVQo7IaoPdiuztmTDzmpw=="# Replace with your actual API key
    
    # Prepare the headers and data to send to Chip In
    headers = {
        "Authorization": f"Bearer {api_key}",  # Use Bearer token for authorization
        "Content-Type": "application/json"
    }

    # Prepare the payload based on the cart data
    payload = {
        "client": {
            "email": "guest@gmail.com",  # Leave it blank or add placeholder
            "phone": "",  # Optional field, leave it blank
            "full_name": "Guest"  # Placeholder if no customer name is available
        },
        "purchase": {
            "products": [
                {"name": item['name'], "price": item['price']} for item in order_data['items']
            ]
        },
        "brand_id": "4e89ff13-b543-4c3d-9763-caa6026acab3"  # Replace with your Chip In brand ID
    }

    # Send the request to Chip In API to create the payment session
    response = requests.post(chip_in_url, json=payload, headers=headers)

    #Parse the response JSON
    response_data = response.json()
    
    # Check if a checkout URL is present, regardless of any error messages
    checkout_url = response_data.get('checkout_url')
    if checkout_url:
        # Return the checkout URL to the frontend
        return jsonify({'checkout_url': checkout_url}), 200
    else:
        # If no checkout URL is found, return the error message
        return jsonify({'error': 'Failed to get checkout URL', 'details': response.text}), 400


# Start the Flask server
if __name__ == '__main__':
    app.run(debug=True)


    <ul class=" trx_addons_list_dot" style="text-align: right;">
 	<li style="font-weight: 400; text-align: center;" aria-level="1">Automated cleaning for smaller areas.</li>
 	<li style="font-weight: 400; text-align: center;" aria-level="1">Precision Cleaning</li>
 	<li style="font-weight: 400; text-align: center;" aria-level="1">Minimal downtime for large areas</li>
    <li style="font-weight: 400; text-align: center;" aria-level="1">Post Performance report</li>
 	<li style="font-weight: 400; text-align: center;" aria-level="1">Report Panel Condition</li>
 	<li style="font-weight: 400; text-align: center;" aria-level="1">Priority Annual Scheduling</li>
    <li style="font-weight: 400; text-align: center;" aria-level="1">Full Operation Report</li>
</ul>