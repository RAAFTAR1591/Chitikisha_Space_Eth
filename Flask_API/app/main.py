from flask import Flask, request, jsonify
from web3 import Web3
import requests
import time
import json
from solcx import install_solc, set_solc_version, compile_standard

app = Flask(__name__)

# Web3 setup
ganache_url = "http://localhost:8545"
time.sleep(5)  # Wait for Ganache to initialize
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
