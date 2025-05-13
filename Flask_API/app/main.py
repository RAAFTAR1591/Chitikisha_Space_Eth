from flask import Flask, request, jsonify
from web3 import Web3
import requests
import time
import json
from solcx import install_solc, set_solc_version, compile_standard
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
# Web3 setup
ganache_url = "http://localhost:8545"
web3 = Web3(Web3.HTTPProvider(ganache_url))

# Install and set Solidity compiler version
install_solc("0.8.0")
set_solc_version("0.8.0")

# Load contract source
with open("MedicalRecord.sol", "r") as file:
    contract_source_code = file.read()

# Compile contract
compiled_sol = compile_standard({
    "language": "Solidity",
    "sources": {
        "MedicalRecord.sol": {
            "content": contract_source_code
        }
    },
    "settings": {
        "outputSelection": {
            "*": {
                "*": ["abi", "evm.bytecode"]
            }
        }
    }
})

abi = compiled_sol["contracts"]["MedicalRecord.sol"]["MedicalRecord"]["abi"]
bytecode = compiled_sol["contracts"]["MedicalRecord.sol"]["MedicalRecord"]["evm"]["bytecode"]["object"]

# Deploy contract
doctor = web3.eth.accounts[0]
patients = web3.eth.accounts[1:4]

MedicalRecord = web3.eth.contract(abi=abi, bytecode=bytecode)
tx_hash = MedicalRecord.constructor().transact({'from': doctor})
tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)

contract = web3.eth.contract(
    address=tx_receipt.contractAddress,
    abi=abi
)

from PIL import Image
import numpy as np
import json

# Helper function to convert image to list
def image_to_list(image_path):
    image = Image.open(image_path)
    image = image.resize((120, 120))  # Resize to 120p
    image_array = np.array(image) / 255.0  # Normalize
    image_list = image_array.tolist()  # Convert to list
    return image_list

# Function to process the image and upload the symptom
def process_image_and_upload_symptom(patient_id, image_path):
    image_list = image_to_list(image_path)
    # Convert list to string for storing in the blockchain
    symptom = json.dumps(image_list)
    
    # Update the symptom in the blockchain using the contract
    tx = contract.functions.uploadSymptom(symptom).transact({'from': patients[patient_id]})
    web3.eth.wait_for_transaction_receipt(tx)


# Routes

@app.route("/upload/symptom", methods=["POST"])
def upload_symptom():
    data = request.json
    patient_id = data.get("patient_id")
    symptom = data.get("symptom")
    tx = contract.functions.uploadSymptom(symptom).transact({'from': patients[patient_id]})
    web3.eth.wait_for_transaction_receipt(tx)
    return jsonify({"status": "symptom uploaded"})


@app.route("/upload/file", methods=["POST"])
def upload_file():
    try:
        patient_id = int(request.form['patient_id'])
        file = request.files['file']
        res = requests.post('http://localhost:5001/api/v0/add', files={'file': file})
        cid = res.json()['Hash']
        tx = contract.functions.uploadRecord(cid).transact({'from': patients[patient_id]})
        web3.eth.wait_for_transaction_receipt(tx)
        return jsonify({"cid": cid, "status": "file uploaded"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/doctor/view/<int:patient_id>")
def view_records(patient_id):
    symptoms = contract.functions.getSymptoms(patients[patient_id]).call({'from': doctor})
    cids = contract.functions.getRecords(patients[patient_id]).call({'from': doctor})
    return jsonify({"symptoms": symptoms, "cids": cids})

import threading

@app.route("/upload/image", methods=["POST"])
def upload_image():
    try:
        # Expecting plain text with `patient_id` and `image_url`
        patient_id = request.form.get("patient_id")
        image_url = request.form.get("image_url")  # Assuming the image path
        
        # Start a new thread to process the image and update the symptom
        thread = threading.Thread(target=process_image_and_upload_symptom, args=(int(patient_id), image_url))
        thread.start()
        
        return jsonify({"status": "image upload started"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/doctor/fetch_image/<int:patient_id>", methods=["GET"])
def fetch_image(patient_id):
    # Retrieve the symptom (image list) from the blockchain
    symptom = contract.functions.getSymptoms(patients[patient_id]).call({'from': doctor})
    
    # Convert the symptom back from JSON string to a Python list
    image_list = json.loads(symptom[0])  # Assuming the symptom is stored as a list of one string
    
    # Convert the image list back to a numpy array
    image_array = np.array(image_list, dtype=np.float32) * 255.0
    image_array = image_array.astype(np.uint8)
    
    # Recreate the image from the numpy array
    image = Image.fromarray(image_array)
    
    # Optionally save it to a file
    image.save("restored_image.jpg")
    
    return jsonify({"status": "Image restored", "message": "Image successfully reconstructed from the blockchain"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
