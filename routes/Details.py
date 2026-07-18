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
from pathlib import Path
from werkzeug.utils import secure_filename
import mysql.connector

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart, MIMEBase
from email import encoders

with open ('config.json') as f:
    configData = json.load(f)

def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=configData['mysql_host'],
            port=configData['mysql_port'],
            database=configData['mysql_database'],
            user=configData['mysql_user'],
            password=configData['mysql_password']
        )
        return conn
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return None
    
conn = get_db_connection()
 
# ORDER_FORM_PATH = "C:\\test"

details_blueprint = Blueprint('details_blueprint', __name__)

app = Flask(__name__)

def send_email_order_form(email, customer_id, ship_to_name, attachments=[]):
    try:
        html_subject = "Order Form Submission Confirmation"
        body = """
        <html>
            <head>
            </head>

            <body>
                <div class="container">

                    <p>Hello,</p>

                    <p>
                        Your order has been received and is currently being processed.
                        You will receive an order acknowledgment email once it has been reviewed.
                    </p>

                    <div class="details">
                        <p><span class="label">Customer ID:</span> {customer_id}</p>
                        <p><span class="label">Ship To Name:</span> {ship_to_name}</p>
                    </div>

                    <p>
                        Thank you for your business!
                    </p>

                    <div class="footer">
                        <p>
                            Best regards,<br>
                            Customer Service
                        </p>
                    </div>

                </div>
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
        # close the server connection if it was opened
        try:
            server.quit()
        except:
            pass
        return False

def send_email_link_for_order_form(email, link, po_number=None):
    try:
        html_subject = "Order Form Link"
        body = f"""
        <html>
            <head>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        color: #333333;
                        line-height: 1.5;
                    }}

                    .container {{
                        padding: 20px;
                    }}

                    .label {{
                        font-weight: bold;
                        color: #555555;
                    }}

                    .details {{
                        margin-top: 15px;
                        padding: 10px 0;
                    }}

                    .footer {{
                        margin-top: 25px;
                    }}
                </style>
            </head>

            <body>
                <div class="container">

                    <p>Hello,</p>

                    <p>
                        Please find the order form link for PO Number: {po_number}
                    </p>

                    <div class="details">
                        <p><span class="label">Order Form Link:</span> <a href="{link}">LINK</a></p>
                    </div>

                    <p>
                        Thank you for your business!
                    </p>

                    <div class="footer">
                        <p>
                            Best regards,<br>
                            Customer Service
                        </p>
                    </div>

                </div>
            </body>
            </html>
        """

        print(f"Sending email to {email} with order form link: {link}")

        msg = MIMEMultipart()
        msg['From'] = configData['smtp_user']
        msg['To'] = email
        msg['Cc'] = ''
        msg['Subject'] = html_subject
        msg.attach(MIMEText(body, 'html'))

        server = smtplib.SMTP(configData['smtp_host'], configData['smtp_port'])
        server.starttls()
        server.login(configData['smtp_user'], configData['smtp_password'])
        recipients = email
        server.sendmail(configData['smtp_user'], recipients , msg.as_string())
        server.quit()

        return True

    except Exception as e:
        print(str(e))
         # close the server connection if it was opened
        try:
            server.quit()
        except:
            pass
        return False

@details_blueprint.route("/api/v1/price_list", methods=['GET'])
def get_price_list():
    # Check if the connection to the database is established
    conn = get_db_connection()

    if conn is None:
        return { "message": "Database connection is not established" }, 500

    try:
        query_params = request.args.get('or')
        limit = int(request.args.get('limit', 30))

        sql_query = f"""SELECT PART_ID, `DESC`, COLOR, CASE_QTY, UNIT_PRICE, LLM, PRODUCT_CODE 
                        FROM PRICE_LIST 
                        WHERE STRING_SEARCH LIKE '%{query_params}%' 
                        LIMIT {limit} """
        mycursor = conn.cursor()
        mycursor.execute(sql_query)

        columns = [desc[0] for desc in mycursor.description]
        results = [dict(zip(columns, row)) for row in mycursor.fetchall()]

        mycursor.close()

        return jsonify(results), 200

    
    except Exception as e:
        conn.rollback()   # 🔥 THIS FIXES YOUR ERROR

        return {
            "message": "An error occurred",
            "error": str(e),
            "sql": sql_query
        }, 500

    finally:
        if mycursor:
            mycursor.close()

@details_blueprint.route("/api/v1/price_list/part_id", methods=['GET'])
def get_part_details():
    # Check if the connection to the database is established
    conn = get_db_connection()
    if conn is None:
        return { "message": "Database connection is not established" }, 500

    try:
        query_params = request.args.get('or')
        limit = int(request.args.get('limit', 20))

        sql_query = f"""SELECT PART_ID, `DESC`, COLOR, CASE_QTY, UNIT_PRICE, LLM, PRODUCT_CODE 
                        FROM PRICE_LIST 
                        WHERE PART_ID = '{query_params}' 
                        LIMIT 1 """
        mycursor = conn.cursor()
        mycursor.execute(sql_query)

        columns = [desc[0] for desc in mycursor.description]
        results = [dict(zip(columns, row)) for row in mycursor.fetchall()]

        mycursor.close()

        return jsonify(results), 200

    
    except Exception as e:
        conn.rollback()   # 🔥 THIS FIXES YOUR ERROR

        return {
            "message": "An error occurred",
            "error": str(e),
            "sql": sql_query
        }, 500

    finally:
        if mycursor:
            mycursor.close()
        if conn:
            conn.close()

@details_blueprint.route("/api/v1/price_list/upload_excel", methods=['POST'])
def upload_excel():
    try:
        file = request.files.get('file')

        if not file:
            return {"message": "No file uploaded"}, 400

        BASE_DIR = Path(__file__).resolve().parent
        folder_path = BASE_DIR / "ORDER_FORMS"
        folder_path.mkdir(parents=True, exist_ok=True)

        # Remove xlsx extension and append a random number to avoid overwriting
        filename_without_ext = secure_filename(file.filename.rsplit('.', 1)[0])
        filename = f"{filename_without_ext}_{random.randint(1000, 9999)}.xlsx"
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

@details_blueprint.route("/api/v1/price_list/send_order_form_link", methods=['POST'])
def send_order_form_link():
    try:
        link = request.form.get("link")
        email = request.form.get("email")
        po_number = request.form.get("po_number")

        if not link or not email:
            return {"message": "Missing required parameters"}, 400
        
        # Send email with the link
        send_email_link_for_order_form(email=email, link=link, po_number=po_number)

        return {
            "message": "Order form link sent successfully!"
        }, 200

        
    except Exception as e:
        return {"message": "An error occurred", "error": str(e)}, 500
