import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
import json


with open ('config.json') as f:
    configData = json.load(f)

# Import the HTML template
template = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Order Confirmation</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f4f4f4;
        }}
        .container {{
            max-width: 600px;
            margin: 20px auto;
            background: #ffffff;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0px 0px 10px rgba(0, 0, 0, 0.1);
        }}
        .header {{
            text-align: center;
            padding-bottom: 20px;
            border-bottom: 2px solid #ddd;
        }}
        .header h1 {{
            color: #333;
        }}
        .order-details {{
            padding: 20px 0;
        }}
        .order-details p {{
            margin: 5px 0;
            color: #555;
        }}
        .footer {{
            text-align: center;
            padding-top: 20px;
            border-top: 2px solid #ddd;
            font-size: 12px;
            color: #888;
        }}
        .button {{
            display: inline-block;
            background: #28a745;
            color: #ffffff;
            padding: 10px 20px;
            text-decoration: none;
            border-radius: 5px;
            margin-top: 15px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Order Confirmation</h1>
        </div>
        <div class="order-details">
            <p>Thank you for your order, <strong>{CustomerName}</strong>!</p>
            <p>Your order confirmation number is: <strong>#{OrderID}</strong>.</p>
            <p>Attached files: <strong>{AttachedFiles}</strong>.</p>
 
        </div>
        <div class="footer">
            <p>If you have any questions, contact our support team.</p>
            <p>Whips Carpentry. All rights reserved.</p>
        </div>
    </div>
</body>
</html>"""

 
def send_email_with_html(customerid, name, order_confirmation, email, attachedFilesList):
    msg = MIMEMultipart()
    msg['From'] = configData['smtp_user']
    msg['To'] = email
    msg['Subject'] = "Order Confirmation - Order Number: " + order_confirmation

    # Convert attachedFilesList to a string
    attachedFilesList = ', '.join(attachedFilesList)

    _template = template.format(CustomerName=name, OrderID=order_confirmation, AttachedFiles=attachedFilesList)
    msg.attach(MIMEText(_template, 'html'))

    

    server = smtplib.SMTP(configData['smtp_host'], configData['smtp_port'])
    server.starttls()
    server.login(configData['smtp_user'], configData['smtp_password'])
    server.sendmail(configData['smtp_user'], email, msg.as_string())
    server.quit()