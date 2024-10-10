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
    "all_events": True,
    "public_key": "-----BEGIN PUBLIC KEY-----\nMIIBojANBgkqhkiG9w0BAQEFAAOCAY8AMIIBigKCAYEAxndobfnBwKtqUUgGhcsP\n3Ehj9b9I6Hx8aMJbYGzCfwo7T9U9ua4lF3efLqnhX82V1/JHP1h7GjL9dnrDTE/W\nobZ7mzr+gVq511M55NqK/fGwJ7JJGtJDIvcoyrvhDDuI20zxYb7WMUq4q8/hk/2n\nrOD7P+yQnxpz/pTPMSKWcihax5d5mf5LzyccZtXtyZPBTNRByNrPFd6+0Z+uJKO7\nC5TTkmr9IK8+ZjByD2H5y/GjCisJCkW0QkFhYQMKAuwiSKoVcWI6j7uFSf3vfida\nuASBZ6dXfdgweRQkhqd4qJvoxZSIhlLwR2PTr18ZWm7Pz/YnezS2XVDy0Snbea24\nPzg/kEeD8SGK8Tk6pQxXKuQ+5FLmIoqP6aF5BlMnc0XT2ArYrI+ptC3jMxdnI0xS\n4LXMJqwCCURs/kbljgXKS+wyfVOIKQpZo7ErDZjaXO8d0rpwcpbXaNjGCKdgTsV0\nHRvUnhl8cieiaD/VjD/LiHYmLQTmn/Aprma4lFQxNmzxAgMBAAE=\n-----END PUBLIC KEY-----\n",
    "events": ["purchase.created"],
    "callback": "https://chip-in-backend-4531.onrender.com/chipin-webhook",  # Replace with your actual backend URL
}

# Sending POST request to Chip In API
response = requests.post(url, json=payload, headers=headers)

# Print the response for debugging
print(response.json())
