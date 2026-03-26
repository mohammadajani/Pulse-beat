import asyncio
import json
import os
import websockets
from bleak import BleakClient

# --- REPLACE WITH YOUR MAC ADDRESS ---
ADDRESS = "E4:61:9F:DB:72:56"
HR_UUID = "00002a37-0000-1000-8000-00805f9b34fb"

CONFIG_FILE = "config_pro.json"
CLIENTS = set()
current_bpm = "AFK"
ble_client = None
ble_connecting = False

# Pro Default Settings - Updated for Layout and Animations
config = {
    "size": 150,
    "fontSize": 45,
    "showText": True,
    "showImage": True,
    # Layout options: 'row' (Text Right), 'row-reverse' (Left), 'column' (Bottom), 'column-reverse' (Top), 'center' (Stacked)
    "overlayLayout": "row", 
    "elementSpacing": 20, # Spacing between text and image
    "animationType": "heartbeat", # none, pulse, heartbeat, bounce, jiggle
    "animScaleIntensity": 1.15 # Controls how much the heart expands on a beat (1.0 to 2.0)
}

if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "r") as f:
        config.update(json.load(f))

def save_config():
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)

def hr_handler(sender, data):
    global current_bpm
    is_16_bit = data[0] & 0x01
    current_bpm = int.from_bytes(data[1:3], byteorder='little') if is_16_bit else data[1]

async def broadcast(message_dict):
    if CLIENTS:
        websockets.broadcast(CLIENTS, json.dumps(message_dict))

async def manage_bluetooth(action):
    global ble_client, current_bpm, ble_connecting
    
    if action == "connect":
        if ble_client and ble_client.is_connected:
            return
        
        ble_connecting = True
        await broadcast({"type": "status_update", "status": "Connecting...", "color": "#f9e2af"})
        
        try:
            ble_client = BleakClient(ADDRESS)
            await ble_client.connect()
            await ble_client.start_notify(HR_UUID, hr_handler)
            ble_connecting = False
            await broadcast({"type": "status_update", "status": "Connected", "color": "#a6e3a1"})
        except Exception as e:
            ble_connecting = False
            current_bpm = "AFK"
            await broadcast({"type": "status_update", "status": f"Failed (Retry)", "color": "#f38ba8"})
            if ble_client:
                await ble_client.disconnect()
                
    elif action == "disconnect":
        if ble_client and ble_client.is_connected:
            await ble_client.disconnect()
        current_bpm = "AFK"
        await broadcast({"type": "status_update", "status": "Disconnected", "color": "#f38ba8"})

async def broadcast_loop():
    global current_bpm
    last_sent_bpm = None
    
    while True:
        if current_bpm != last_sent_bpm and CLIENTS:
            image = "afk.png" if current_bpm == "AFK" else (
                "1.png" if current_bpm < 80 else
                "2.png" if current_bpm <= 89 else
                "3.png" if current_bpm <= 99 else
                "4.png" if current_bpm <= 109 else "5.png"
            )
            await broadcast({"type": "bpm_update", "bpm": current_bpm, "image": image})
            last_sent_bpm = current_bpm
        await asyncio.sleep(0.2)

async def ws_handler(websocket):
    CLIENTS.add(websocket)
    
    await websocket.send(json.dumps({"type": "config_update", "config": config}))
    status_msg = "Connected" if (ble_client and ble_client.is_connected) else ("Connecting..." if ble_connecting else "Disconnected")
    color = "#a6e3a1" if status_msg == "Connected" else ("#f9e2af" if status_msg == "Connecting..." else "#f38ba8")
    await websocket.send(json.dumps({"type": "status_update", "status": status_msg, "color": color}))
    
    try:
        async for message in websocket:
            data = json.loads(message)
            if data.get("type") == "save_settings":
                config.update(data["config"])
                save_config()
                await broadcast({"type": "config_update", "config": config})
            elif data.get("type") == "ble_command":
                asyncio.create_task(manage_bluetooth(data["action"]))
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        CLIENTS.remove(websocket)

async def main():
    print(f"Server ProItsMhaa running. Fight well. Open dashboard.html.")
    server = await websockets.serve(ws_handler, "localhost", 8765)
    asyncio.create_task(broadcast_loop())
    await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())