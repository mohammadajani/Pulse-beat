import asyncio
import json
import websockets
from bleak import BleakClient

# Replace with your watch's MAC address
ADDRESS = "E4:61:9F:DB:72:56"
HR_UUID = "00002a37-0000-1000-8000-00805f9b34fb"

# Global variable to store the latest BPM
current_bpm = "AFK"

def hr_handler(sender, data):
    global current_bpm
    is_16_bit = data[0] & 0x01
    current_bpm = int.from_bytes(data[1:3], byteorder='little') if is_16_bit else data[1]
    print(f"Heart Rate: {current_bpm} BPM")

async def ws_handler(websocket):
    global current_bpm
    last_sent_bpm = None
    
    try:
        while True:
            # Only send an update if the BPM has changed
            if current_bpm != last_sent_bpm:
                if current_bpm == "AFK":
                    image = "afk.png"
                elif current_bpm < 80:
                    image = "1.png"
                elif 80 <= current_bpm <= 89:
                    image = "2.png"
                elif 90 <= current_bpm <= 99:
                    image = "3.png"
                elif 100 <= current_bpm <= 109:
                    image = "4.png"
                else:
                    image = "5.png"
                    
                # Package the data as JSON and send it to the HTML file
                message = json.dumps({"bpm": current_bpm, "image": image})
                await websocket.send(message)
                last_sent_bpm = current_bpm
                
            await asyncio.sleep(0.2) # Check for updates 5 times a second
    except websockets.exceptions.ConnectionClosed:
        pass

async def main():
    print("Starting local WebSocket server on port 8765...")
    async with websockets.serve(ws_handler, "localhost", 8765):
        print(f"Connecting to watch at {ADDRESS}...")
        try:
            async with BleakClient(ADDRESS) as client:
                print("Connected! Broadcasting to OBS...")
                await client.start_notify(HR_UUID, hr_handler)
                await asyncio.Future() # Keep running forever
        except Exception as e:
            print(f"Connection failed: {e}")
            global current_bpm
            current_bpm = "AFK"

if __name__ == "__main__":
    asyncio.run(main())