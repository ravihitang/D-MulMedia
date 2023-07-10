import json
import os
import requests
import zipfile
import shutil
from flask import render_template, redirect, request, send_file
from werkzeug.utils import secure_filename
from app import app
from timeit import default_timer as timer

# Stores all the post transaction in the node
request_tx = []
# Store filename
files = {}
# Destination for uploaded files
UPLOAD_FOLDER = "app/static/Uploads"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Store address
ADDR = "http://127.0.0.1:8800"


# Create a list of requests that peers have sent to upload files
def get_tx_req():
    global request_tx
    chain_addr = "{0}/chain".format(ADDR)
    resp = requests.get(chain_addr)
    if resp.status_code == 200:
        content = []
        chain = json.loads(resp.content.decode())
        for block in chain["chain"]:
            for trans in block["transactions"]:
                trans["index"] = block["index"]
                trans["hash"] = block["prev_hash"]
                content.append(trans)
        request_tx = sorted(content, key=lambda k: k["hash"], reverse=True)


# Loads and runs the home page
@app.route("/")
def index():
    get_tx_req()
    return render_template("index.html", title="FileStorage",
                           subtitle="A Decentralized Network for File Storage/Sharing",
                           node_address=ADDR, request_tx=request_tx)


@app.route("/uploaded")
def uploaded():
    return render_template("uploaded.html", title="FileStorage",
                           subtitle="A Decentralized Network for File Storage/Sharing",
                           node_address=ADDR, request_tx=request_tx)


@app.route("/submit", methods=["POST"])
# When a new transaction is created, it is processed and added to the transaction
def submit():
    start = timer()
    user = request.form["user"]
    uni_Key = request.form["file_key"]
    up_file = request.files["v_file"]

    # Save the uploaded file in the destination folder
    filename = secure_filename(up_file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    up_file.save(file_path)

    # Create a unique filename for the encrypted zip file
    zip_filename = f"{filename}.zip"
    zip_path = os.path.join(app.config['UPLOAD_FOLDER'], zip_filename)

    # Create a zip file and add the uploaded file with encryption
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.setpassword(uni_Key.encode())  # Set password for encryption
        zip_file.write(file_path, filename)  # Add the uploaded file to the zip

    # Remove the original uploaded file
    os.remove(file_path)

    # Add the encrypted zip file to the list to create a download link
    files[zip_filename] = zip_path

    # Create a transaction object
    post_object = {
        "user": user,
        "v_file": zip_filename,
        "file_key": uni_Key,
        "file_data": str(up_file.stream.read()),
        "file_size": os.stat(zip_path).st_size
    }

    # Submit a new transaction
    address = "{0}/new_transaction".format(ADDR)
    requests.post(address, json=post_object)

    end = timer()
    print(end - start)
    return redirect("/")


# Creates a download link for the file
@app.route("/submit/<string:variable>", methods=["GET"])
def download_file(variable):
    p = files[variable]
    return send_file(p, as_attachment=True)
