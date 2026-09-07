import asyncio
import json
import os
import websockets
from bleak import BleakClient, BleakScanner

HR_UUID = "00002a37-0000-1000-8000-00805f9b34fb"
CONFIG_FILE = "config_pro.json"
CLIENTS = set()
current_bpm = "AFK"
ble_client = None
ble_connecting = False

config = {
    "macAddress": "", "size": 150, "fontSize": 45, "showText": True, "showImage": True,
    "overlayLayout": "row", "elementSpacing": 20, "animationType": "heartbeat", "animScaleIntensity": 1.15,
    "imgAfk": "afk.png", "img1": "1.png", "img2": "2.png", "img3": "3.png", "img4": "4.png", "img5": "5.png"
}

if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "r") as f:
        config.update(json.load(f))

def save_config():
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)

async def broadcast(message_dict):
    if CLIENTS:
        websockets.broadcast(CLIENTS, json.dumps(message_dict))

async def log_to_dash(msg):
    print(msg) 
    await broadcast({"type": "console_log", "message": msg})

def hr_handler(sender, data):
    global current_bpm
    is_16_bit = data[0] & 0x01
    current_bpm = int.from_bytes(data[1:3], byteorder='little') if is_16_bit else data[1]

async def manage_bluetooth(action):
    global ble_client, current_bpm, ble_connecting
    
    if action == "connect":
        if ble_client and ble_client.is_connected: return
        if ble_connecting: return
            
        mac = config.get("macAddress", "").strip()
        if not mac:
            await log_to_dash("ERROR: Missing MAC Address.")
            return
        
        ble_connecting = True
        await broadcast({"type": "status_update", "status": "Connecting...", "color": "#f9e2af"})
        
        try:
            await log_to_dash(f"Scanning for {mac}...")
            device = await BleakScanner.find_device_by_address(mac, timeout=5.0)
            
            if not device:
                await log_to_dash("ERROR: Watch not found. Is screen on?")
                ble_connecting = False
                await broadcast({"type": "status_update", "status": "Failed", "color": "#f38ba8"})
                return
                
            await log_to_dash(f"Found {device.name}. Connecting...")
            
            # FIX: Passing the MAC string directly works around the Windows Catastrophic Failure bug
            ble_client = BleakClient(mac) 
            await ble_client.connect()
            await ble_client.start_notify(HR_UUID, hr_handler)
            
            ble_connecting = False
            await log_to_dash("Connected and receiving BPM!")
            await broadcast({"type": "status_update", "status": "Connected", "color": "#a6e3a1"})
            
        except Exception as e:
            ble_connecting = False
            current_bpm = "AFK"
            await log_to_dash(f"CONNECTION FAILED: {str(e)}") 
            await broadcast({"type": "status_update", "status": "Failed", "color": "#f38ba8"})
            if ble_client:
                try: await ble_client.disconnect()
                except: pass
            ble_client = None
                
    elif action == "disconnect":
        if ble_client and ble_client.is_connected:
            try: await ble_client.disconnect()
            except: pass
        ble_client = None
        current_bpm = "AFK"
        ble_connecting = False
        await log_to_dash("Disconnected.")
        await broadcast({"type": "status_update", "status": "Disconnected", "color": "#f38ba8"})

async def broadcast_loop():
    global current_bpm
    last_sent_bpm = None
    while True:
        if current_bpm != last_sent_bpm and CLIENTS:
            state = "afk" if current_bpm == "AFK" else ("1" if current_bpm < 80 else "2" if current_bpm <= 89 else "3" if current_bpm <= 99 else "4" if current_bpm <= 109 else "5")
            await broadcast({"type": "bpm_update", "bpm": current_bpm, "state": state})
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
    except Exception:
        pass
    finally:
        CLIENTS.remove(websocket)

async def main():
    print("ItsMhaa Server Running.")
    print("CRITICAL: DO NOT type localhost:8765 into your web browser. Just double-click dashboard.html.")
    
    # FIX: This wrapper prevents the script from crashing if an invalid connection hits it
    try:
        async with websockets.serve(ws_handler, "localhost", 8765):
            await broadcast_loop()
    except Exception as e:
        print(f"Server error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server stopped.")