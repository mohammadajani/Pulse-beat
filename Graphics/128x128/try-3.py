import asyncio
import shutil
import os
from bleak import BleakClient

# Replace with your watch's MAC address
ADDRESS = "E4:61:9F:DB:72:56"
HR_UUID = "00002a37-0000-1000-8000-00805f9b34fb"

# The file OBS will be looking at
IMAGE_CURRENT = "current_heart.png"

def set_afk_state():
    """Sets the stream image to AFK/Offline"""
    try:
        if os.path.exists("afk.png"):
            shutil.copyfile("afk.png", IMAGE_CURRENT)
        with open("hr.txt", "w") as f:
            f.write("AFK")
    except Exception as e:
        print(f"Error setting AFK state: {e}")

def update_visuals(bpm):
    """Updates the text file and the current image based on the 5 tiers"""
    # 1. Update the text file for your OBS text source
    with open("hr.txt", "w") as f:
        f.write(str(bpm))
        
    # 2. Determine which image to use based on the ranges
    if bpm < 80:
        source_image = "1.png"
    elif 80 <= bpm <= 89:
        source_image = "2.png"
    elif 90 <= bpm <= 99:
        source_image = "3.png"
    elif 100 <= bpm <= 109:
        source_image = "4.png"
    else: # 110 and above
        source_image = "5.png"
        
    # 3. Copy the correct tier image to 'current_heart.png'
    try:
        if os.path.exists(source_image):
            shutil.copyfile(source_image, IMAGE_CURRENT)
    except Exception as e:
        print(f"Error updating image: {e}")

def hr_handler(sender, data):
    flags = data[0]
    is_16_bit = flags & 0x01
    
    try:
        if is_16_bit:
            heart_rate = int.from_bytes(data[1:3], byteorder='little')
        else:
            heart_rate = data[1]
            
        print(f"Heart Rate: {heart_rate} BPM")
        update_visuals(heart_rate)
            
    except Exception as e:
        print(f"Error parsing data: {e}")

async def main():
    # Set to AFK before connecting
    set_afk_state()
    print(f"Connecting to {ADDRESS}...")
    
    try:
        async with BleakClient(ADDRESS) as client:
            print("Connected! Listening for heart rate data...")
            await client.start_notify(HR_UUID, hr_handler)
            
            while True:
                await asyncio.sleep(1)
                
    except Exception as e:
        print(f"Connection failed: {e}")
        set_afk_state()

if __name__ == "__main__":
    asyncio.run(main())