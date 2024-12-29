from flask import Flask, jsonify, request
import requests
import re
import logging

app = Flask(__name__)

MAIL_URL = "https://www.1secmail.com/api/v1/"
DOMAINS = ["dpptd.com", "rteet.com"]  # List of domains to use

logging.basicConfig(level=logging.DEBUG)

@app.route('/getMailAddress', methods=['GET'])
def get_email():
    """Generate a temporary email with a dynamic domain and return it."""
    email_found = False
    retries = 5
    response_text = {}

    while retries > 0 and not email_found:
        for domain in DOMAINS:  # Iterate through the list of domains
            response = requests.get(f"{MAIL_URL}?action=genRandomMailbox&domain={domain}")
            if response.status_code == 200:
                email_data = response.json()
                email = email_data[0]  # Example: "dryyfhj5@rteet.com"
                mail_id = email.split('@')[0]  # Example: "dryyfhj5"
                email_found = True
                response_text = {
                    "TEMP_MAIL": f"{mail_id}:{email}"  # Mail ID and Full email address
                }
                break
        if not email_found:
            retries -= 1
            if retries == 0:
                response_text = {"error": "Failed to generate email after retries"}
                break
    logging.debug(response_text)
    return jsonify(response_text), 200

@app.route('/get_otp', methods=['GET'])
def get_otp():
    """Fetch OTP from the temporary email using mail_id and dynamically handled domain."""
    mail_id = request.args.get('mail_id')
    if not mail_id:
        return jsonify({'error': 'mail_id parameter is missing'}), 400

    domain = None
    for d in DOMAINS:  # Check domain dynamically
        response = requests.get(f"{MAIL_URL}?action=getMessages&login={mail_id}&domain={d}")
        if response.status_code == 200 and response.json():
            domain = d
            break

    if not domain:
        return jsonify({'error': 'Domain not found for the provided mail_id'}), 404

    response = requests.get(f"{MAIL_URL}?action=getMessages&login={mail_id}&domain={domain}")
    if response.status_code == 200:
        messages = response.json()
        if messages:
            latest_message = messages[0]
            message_id = latest_message['id']
            message_response = requests.get(f"{MAIL_URL}?action=readMessage&login={mail_id}&domain={domain}&id={message_id}")
            message_data = message_response.json()
            if message_data:
                message_body = message_data['body']
                otp = extract_otp_from_message(message_body)
                if otp != 'OTP not found':
                    return jsonify({'OTP': otp}), 200
                else:
                    return jsonify({'error': otp}), 404
            return jsonify({'error': 'No message found in email'}), 404
        return jsonify({'error': 'No emails found for the provided mail_id'}), 404
    return jsonify({'error': f'Failed to fetch messages. HTTP status code: {response.status_code}'}), 500

def extract_otp_from_message(message_body):
    """Extract OTP from the email content."""
    otp = re.findall(r'\b\d{6}\b', message_body)
    if otp:
        return otp[0]
    return 'OTP not found'

if __name__ == '__main__':
    app.run(debug=True)
