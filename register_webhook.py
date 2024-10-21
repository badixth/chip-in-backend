import requests

# API URL for Chip In Webhooks
url = "https://gate.chip-in.asia/api/v1/webhooks/"

# Headers containing Authorization and Content-Type
headers = {
    "Authorization": "Bearer GL0wFCcFob5IgIIY2qsWfUtx1W27Wfm5Q2uoITFxo5QkLtjSxEHEh0ekux3VXIf8quVQo7IaoPdiuztmTDzmpw==",  # Replace with your actual API key
    "Content-Type": "application/json",
}

# Payload with the public key, event type, and callback URL
payload = {
    "title": "Chip In Webhook",
    "public_key": "-----BEGIN PUBLIC KEY-----\nMIIBojANBgkqhkiG9w0BAQEFAAOCAY8AMIIBigKCAYEAuyGnHmDXWx/tKuQjwNiE\nldsgwMA4yFUcy4W6LEUqvEFf+/CwvFhrheWi6yRECoVdwP6Jb2OBPEcMb05d1jsK\nhk/PHuwL4j4wWX2uqamok8ZypZyiJTtwN7VtfvXUYJQ5yitoUNS1rj2a6D15gClX\ngaNAqV4sPXwJSnZzFVWbawa23eze7dcoxyVPHmMlEcN3Gsfs7iCEYh2KW5u5Y3dz\n46+BJu4ciDBI21Lj0rR3E1PT/D6teOg8zyXbsupkLMjkNt1ngYpxD/+86lJ/OWuL\n8J8vmrIDFILv+xpyMg2YwMzGOALG2syy4L79mchS4RVWzZG/3sLn212Rs5bvWIGZ\nyG8uMB+Qk7ySfLGpa/6K5VS/J14gAqylA49bDBwvu6AuaR5YMhhsq4htZuN8kphf\nnLlECbAuUCGUh0Ngj8fs46dYIM1xD4rGQiVnSZKcriLDK5tOfux+NASS7/sKooIP\nRDcBw1bdVctacoQDE5ic1AlY8cIvsT0enUQt+k6ee2Y5AgMBAAE=\n-----END PUBLIC KEY-----\n",  # Replace with your actual public key
    "events": ["purchase.paid"],
    "callback": "https://chip-in-backend-4531.onrender.com/chipin-webhook",  # Replace with your actual backend URL
}

# Sending POST request to Chip In API
response = requests.post(url, json=payload, headers=headers)

# Print the response for debugging
print(response.json())
