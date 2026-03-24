import asyncio
from bleak import BleakClient

# Replace with your watch's MAC address
ADDRESS = "E4:61:9F:DB:72:56"

# The standard BLE UUID for Heart Rate Measurement
HR_UUID = "00002a37-0000-1000-8000-00805f9b34fb"

def hr_handler(sender, data):
    # The first byte (data[0]) contains flags.
    # The lowest bit (0x01) determines if the heart rate is 8-bit or 16-bit.
    flags = data[0]
    is_16_bit = flags & 0x01
    
    try:
        if is_16_bit:
            # 16-bit heart rate value (bytes 1 and 2)
            heart_rate = int.from_bytes(data[1:3], byteorder='little')
        else:
            # 8-bit heart rate value (byte 1)
            heart_rate = data[1]
            
        print(f"Heart Rate: {heart_rate} BPM")
        
        # Write to file for OBS to read
        with open("hr.txt", "w") as f:
            f.write(str(heart_rate))
            
    except Exception as e:
        print(f"Error parsing data or writing to file: {e}")

async def main():
    print(f"Connecting to {ADDRESS}...")
    try:
        async with BleakClient(ADDRESS) as client:
            print("Connected! Listening for heart rate data...")
            
            # Subscribe to the heart rate data stream
            await client.start_notify(HR_UUID, hr_handler)
            print("Press Ctrl+C to stop.")
            
            # Keep the script running continuously
            while True:
                await asyncio.sleep(1)
                
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())