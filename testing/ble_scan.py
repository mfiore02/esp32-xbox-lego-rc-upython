import time
import asyncio
import aioble

async def scan_for_ble_devices():
    print("Scanning for Xbox controller and Lego hub devices...")
    async with aioble.scan(duration_ms=5000, interval_us=30000, window_us=30000, active=True) as scanner:
        async for result in scanner:
            #print(f"Device found: {result.name()} - RSSI: {result.rssi} dBm")
            if "xbox" in (result.name() or "").lower():
                print("=" * 50)
                print(f"Found Xbox controller: {result.name()} with address: {result.device.addr_hex()}")
                print(f"\tName: {result.name()}")
                print(f"\tAddress (hex): {result.device.addr_hex()}")
                print(f"\tAddress (raw): {result.device.addr}")
                print(f"\tAddress type: {result.device.addr_type}")  # Should show if RPA
                print(f"\tRSSI: {result.rssi}")
                print("=" * 50)
            if "technic move" in (result.name() or "").lower():
                print("=" * 50)
                print(f"Found Lego hub: {result.name()} with address: {result.device.addr_hex()}")
                print(f"\tName: {result.name()}")
                print(f"\tAddress (hex): {result.device.addr_hex()}")
                print(f"\tAddress (raw): {result.device.addr}")
                print(f"\tAddress type: {result.device.addr_type}")  # Should show if RPA
                print(f"\tRSSI: {result.rssi}")
                print("=" * 50)
            
def run():
    asyncio.run(scan_for_ble_devices())

if __name__ == "__main__":
    while True:
        run()
        print("Waiting 5 seconds before next scan...")
        time.sleep(5)  # Pause before the next scan cycle