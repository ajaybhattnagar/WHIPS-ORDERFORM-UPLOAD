from flask import Flask, request, jsonify, json, Blueprint, Response, send_file
from flask_cors import CORS
from functools import wraps
import simplejson
import os
from utils import send_email_with_html
import pandas as pd
import random
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import psycopg2
from pathlib import Path
from werkzeug.utils import secure_filename

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart, MIMEBase
from email import encoders

with open ('config.json') as f:
    configData = json.load(f)

conn = psycopg2.connect(
    host=configData['postgress_host'],
    port=configData['postgress_port'],
    database=configData['postgress_database'],
    user=configData['postgress_user'],
    password=configData['postgress_password']
)
 
# ORDER_FORM_PATH = "C:\\test"

details_blueprint = Blueprint('details_blueprint', __name__)

app = Flask(__name__)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

def send_email_order_form(email, customer_id, ship_to_name, attachments=[]):
    try:
        html_subject = "Order Form Submission Confirmation"
        body = """
        <html>
            <head>
            </head>
            <body>

                <p>Your order has been received and is being processed. Please wait for an order acknowledgment email.</p>
                <p><span class="label">Customer ID:</span> {customer_id}</p>
                <p><span class="label">Ship To Name:</span> {ship_to_name}</p>

                <br>

                <p>Thank you for your business!</p>

                <p>Best regards,<br></p>

            </body>
            </html>
        """.format(customer_id=customer_id, ship_to_name=ship_to_name)

        print(f"Sending email to {email} with attachments: {attachments}")

        msg = MIMEMultipart()
        msg['From'] = configData['smtp_user']
        msg['To'] = email
        msg['Cc'] = ''
        msg['Subject'] = html_subject
        msg.attach(MIMEText(body, 'html'))

        # Attach all the files from attachments list
        for file_path in attachments:
            if os.path.isfile(file_path):
                with open(file_path, 'rb') as attachment:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment.read())
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', f'attachment; filename={os.path.basename(file_path)}')
                    msg.attach(part)

        server = smtplib.SMTP(configData['smtp_host'], configData['smtp_port'])
        server.starttls()
        server.login(configData['smtp_user'], configData['smtp_password'])
        recipients = email
        server.sendmail(configData['smtp_user'], recipients , msg.as_string())
        server.quit()

        return True

    except Exception as e:
        print(str(e))
        return False


@details_blueprint.route("/api/v1/price_list", methods=['GET'])
# @limiter.limit("1000000 per minute")
def get_price_list():
    # Check if the connection to the database is established
    if conn is None:
        return { "message": "Database connection is not established" }, 500

    try:
        query_params = request.args.get('or')
        limit = int(request.args.get('limit', 20))

        sql_query = f"""SELECT * 
                        FROM price_list 
                        WHERE ("PART_ID" ILIKE '%{query_params}%' OR "DESC" ILIKE '%{query_params}%') 
                        LIMIT {limit} """
        cursor = conn.cursor()
        cursor.execute(sql_query)

        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]

        cursor.close()

        return jsonify(results), 200

    
    except Exception as e:
        conn.rollback()   # 🔥 THIS FIXES YOUR ERROR

        return {
            "message": "An error occurred",
            "error": str(e),
            "sql": sql_query
        }, 500

    finally:
        if cursor:
            cursor.close()

@details_blueprint.route("/api/v1/price_list/part_id", methods=['GET'])
# @limiter.limit("10 per minute")
def get_part_details():
    # Check if the connection to the database is established
    if conn is None:
        return { "message": "Database connection is not established" }, 500

    try:
        query_params = request.args.get('or')
        limit = int(request.args.get('limit', 20))

        sql_query = f"""SELECT * 
                        FROM price_list 
                        WHERE "PART_ID" = '{query_params}' 
                        LIMIT 1 """
        cursor = conn.cursor()
        cursor.execute(sql_query)

        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]

        cursor.close()

        return jsonify(results), 200

    
    except Exception as e:
        conn.rollback()   # 🔥 THIS FIXES YOUR ERROR

        return {
            "message": "An error occurred",
            "error": str(e),
            "sql": sql_query
        }, 500

    finally:
        if cursor:
            cursor.close()



@details_blueprint.route("/api/v1/price_list/upload_excel", methods=['POST'])
# @limiter.limit("10 per minute")
def upload_excel():
    try:
        file = request.files.get('file')

        if not file:
            return {"message": "No file uploaded"}, 400

        BASE_DIR = Path(__file__).resolve().parent
        folder_path = BASE_DIR / "ORDER_FORMS"
        folder_path.mkdir(parents=True, exist_ok=True)

        filename = secure_filename(file.filename)
        file_path = folder_path / filename

        file.save(str(file_path))

        # optional fields safely
        notes = request.form.get("notes")
        email = request.form.get("email")
        customer_id = request.form.get("customer")
        ship_to_name = request.form.get("name")

        if not notes:
            notes = "No notes provided"

        # Send email with the file attached
        send_email_order_form(email=email, customer_id=customer_id, ship_to_name=ship_to_name, attachments=[file_path])

        # try:
        #     notes_json = simplejson.loads(notes)
        #     notes_df = pd.DataFrame.from_dict(notes_json, orient='index')
        #     notes_df.to_csv(os.path.join(folder_path, "NOTES.csv"))
        # except Exception:
        #     pass  # keep raw notes if not JSON

        order_number = ''.join(random.choices('0123456789', k=6))

        return {
            "message": "Form submitted successfully!",
            "order_number": order_number
        }, 200

    except Exception as e:
        return {"message": "An error occurred", "error": str(e)}, 500
