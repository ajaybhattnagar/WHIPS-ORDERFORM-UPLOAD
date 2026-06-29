from flask import Flask, request, jsonify, json
from flask_cors import CORS
from functools import wraps



from routes.Details import details_blueprint

app = Flask(__name__)
app.register_blueprint(details_blueprint)

CORS(app)
CORS(app, expose_headers='Content-Disposition')



@app.route("/")
def welcome():
    return ("Welcome to API - CAN")




if __name__ == '__main__':
    # app.run(host="0.0.0.0", port=5000)
    app.run(debug=True)
    app.run(host='localhost', port=2277)
