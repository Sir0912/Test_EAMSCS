import serial
import requests

# Adjust COM port and baud rate to match your Arduino
ser = serial.Serial('COM3', 9600)

print('hello!') 

while True:
    line = ser.readline().decode().strip()
    if line.startswith("RFID Tag UID:"):
        uid = line.replace("RFID Tag UID:", "").strip()
        print("hello:", uid)

        # Send UID to Flask server
        response = requests.post("http://127.0.0.1:5000/scan", json={"uid": uid})
# import serial
# import requests
#
# # Change COM if needed (check in Device Manager)
# ser = serial.Serial('COM3', 9600)
#
# print("Scanner running...")
#
# while True:
#     line = ser.readline().decode().strip()
#
#     if line.startswith("RFID Tag UID:"):
#         uid = line.replace("RFID Tag UID:", "").strip()
#
#         print("Scanned UID:", uid)
#
#         requests.post(
#             "http://127.0.0.1:5000/scan",
#             json={"uid": uid}
#         )
