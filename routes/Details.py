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

with open ('config.json') as f:
    configData = json.load(f)

conn = psycopg2.connect(
    host=configData['postgress_host'],
    port=configData['postgress_port'],
    database=configData['postgress_database'],
    user=configData['postgress_user'],
    password=configData['postgress_password']
)
 
ORDER_FORM_PATH = configData['ORDER_FORM_PATH']
# ORDER_FORM_PATH = "C:\\test"

details_blueprint = Blueprint('details_blueprint', __name__)

app = Flask(__name__)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)


@details_blueprint.route("/api/v1/upload", methods=['POST'])
@limiter.limit("10 per minute")
def upload_order_form():
    try:
        # code to accept form data and save to file
        customer_id = request.form.get('customerid')
        name = request.form.get('name')
        lastname = request.form.get('lastName')
        email = request.form.get('email')
        notes = request.form.get('notes')
        files = request.files.getlist('files')   

        fileNameList = []           

        # code to save files to disk
        # Create a folder in the name of first name and last name and email under the uploads folder
        folder_name = f"{customer_id}_{name}_{email}"
        folder_path = f"{ORDER_FORM_PATH}/{folder_name}"
        os.makedirs(folder_path, exist_ok=True)
        for file in files:
            file.save(os.path.join(folder_path, file.filename))
            fileNameList.append(file.filename)

        # Save notes as text file
        # Chek if notes is empty
        if notes is None:
            notes = "No notes provided"

        try:
            # convert notes to dictionary
            notes = simplejson.loads(notes)
            notes_df = pd.DataFrame.from_dict(notes, orient='index')
            notes_df.to_csv(f"{folder_path}/NOTES.csv", index=True)
        except simplejson.errors.JSONDecodeError:
            notes = {"notes": notes}

        # Generate a random order number
        order_number = ''.join(random.choices('0123456789', k=6))

        # Send an email to the customer
        send_email_with_html(customerid = customer_id, 
                            name = name, 
                            order_confirmation = order_number, 
                            email = email,
                            attachedFilesList = fileNameList
                            )
        return {"message": "Form submitted successfully!", "name": name}, 200
    except Exception as e:
        return {"message": "An error occurred", "error": str(e)}, 500


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

        folder_path = os.path.join(ORDER_FORM_PATH)
        os.makedirs(folder_path, exist_ok=True)

        file_path = os.path.join(folder_path, file.filename)
        file.save(file_path)

        # optional fields safely
        notes = request.form.get("notes")
        name = request.form.get("name")

        if not notes:
            notes = "No notes provided"

        try:
            notes_json = simplejson.loads(notes)
            notes_df = pd.DataFrame.from_dict(notes_json, orient='index')
            notes_df.to_csv(os.path.join(folder_path, "NOTES.csv"))
        except Exception:
            pass  # keep raw notes if not JSON

        order_number = ''.join(random.choices('0123456789', k=6))

        return {
            "message": "Form submitted successfully!",
            "order_number": order_number
        }, 200

    except Exception as e:
        return {"message": "An error occurred", "error": str(e)}, 500
