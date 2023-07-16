import json
import os
import requests
import shutil
import pyminizip
from flask import render_template, redirect, request, send_file
from werkzeug.utils import secure_filename
from app import app
from timeit import default_timer as timer

# Stores all the post transactions in the node
request_tx = []
# Store filename
files = {}
# Destination for uploaded files
UPLOAD_FOLDER = "app/Uploads/"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Store address
ADDR = "http://127.0.0.1:8800"


# Create a list of requests that peers have sent to upload files
def get_tx_req():
    global request_tx
    chain_addr = f"{ADDR}/chain"
    resp = requests.get(chain_addr)
    if resp.status_code == 200:
        content = []
        chain = json.loads(resp.content.decode())
        for block in chain["chain"]:
            for trans in block["transactions"]:
                trans["index"] = block["index"]
                trans["hash"] = block["prev_hash"]

                # Retrieve the uploaded file information if available
                if "v_file" in trans:
                    filename = trans["v_file"]
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    if os.path.exists(file_path):
                        trans["file_size"] = os.stat(file_path).st_size
                        trans["file_path"] = file_path

                content.append(trans)

        # Sort transactions based on their hashes
        request_tx = sorted(content, key=lambda k: k["hash"], reverse=True)

# Loads and runs the home page
@app.route("/")
def index():
    get_tx_req()
    return render_template("index.html", title="FileStorage",subtitle="A Decentralized Network for File Storage/Sharing",node_address=ADDR, request_tx=request_tx)


@app.route("/uploaded")
def uploaded():
    get_tx_req()
    return render_template("uploaded.html", title="FileStorage",subtitle="A Decentralized Network for File Storage/Sharing",node_address=ADDR, request_tx=request_tx)


@app.route("/submit", methods=["POST"])
# When new transaction is created it is processed and added to transaction
def submit():
    start = timer()
    user = request.form["user"]
    uni_Key = request.form["file_key"]
    up_file = request.files["v_file"]
    
    #save the uploaded file in destination
    file_name=up_file.filename;
    file_path = os.path.join(app.config['UPLOAD_FOLDER'],file_name)
    up_file.save(os.path.join("app/Uploads/",secure_filename(file_name)))

    # Create a unique filename for the encrypted zip file
    zip_filename = f"{up_file.filename}.zip"
    zip_path = os.path.join('app/Uploads',zip_filename)

    # Create an encrypted zip file using pyminizip
    pyminizip.compress(file_path, None, zip_path, uni_Key, 1)

    # Remove the original uploaded file
    os.remove(file_path)

    # Add the encrypted zip file to the list to create a download link
    files[zip_filename] = f"Uploads/{zip_filename}"


    #create a transaction object
    post_object = {
        "user": user, #user name
        "v_file" : zip_filename, #filename
        "file_key": uni_Key,
        "file_data" : str(up_file.stream.read()), #file data
        "file_size" : os.stat(zip_path).st_size  #file size
    }
   
    # Submit a new transaction
    address = "{0}/new_transaction".format(ADDR)
    requests.post(address, json=post_object)
    end = timer()
    print(end - start)
    return redirect("/")


@app.route("/debug/files")
def debug_files():
    return str(files)


@app.route("/submit/<string:variable>",methods = ["GET"])
def download_file(variable):
    p = files[variable]
    return send_file(p,as_attachment=True)
