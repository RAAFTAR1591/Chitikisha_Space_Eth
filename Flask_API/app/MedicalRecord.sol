// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract MedicalRecord {
    struct Patient {
        string[] symptoms;
        string[] recordHashes;
    }

    mapping(address => Patient) private patients;

    address public doctor;

    constructor() {
        doctor = msg.sender;
    }

    function uploadSymptom(string memory _symptom) public {
        patients[msg.sender].symptoms.push(_symptom);
    }

    function uploadRecord(string memory _hash) public {
        patients[msg.sender].recordHashes.push(_hash);
    }

    function getSymptoms(address patient) public view returns (string[] memory) {
        require(msg.sender == doctor, "Only doctor can view symptoms");
        return patients[patient].symptoms;
    }

    function getRecords(address patient) public view returns (string[] memory) {
        require(msg.sender == doctor, "Only doctor can view records");
        return patients[patient].recordHashes;
    }
}
