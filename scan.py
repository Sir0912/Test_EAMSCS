import serial
import requests
import time

# Change COM if needed (check in Device Manager)
# Common ports: COM3, COM4, COM5, /dev/ttyUSB0 on Linux
ser = serial.Serial('COM3', 9600, timeout=1)

print("=" * 50)
print("RFID Scanner Started")
print("Waiting for scans...")
print("=" * 50)

while True:
    try:
        line = ser.readline().decode().strip()

        if line.startswith("RFID Tag UID:"):
            uid = line.replace("RFID Tag UID:", "").strip()
            
            print(f"\n{'='*50}")
            print(f"SCAN DETECTED!")
            print(f"UID: {uid}")
            print(f"Time: {time.strftime('%Y-%m-%d %I:%M:%S %p')}")
            print(f"{'='*50}")
            
            # Send to Flask server
            response = requests.post(
                "http://127.0.0.1:5000/scan", 
                json={"uid": uid}
            )
            
            print(f"Server Response: {response.json()}")
            print("-" * 50)
            
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(1)