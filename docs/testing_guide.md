# Testing Guide

This guide explains how to test the Xbox LEGO RC Controller components on your ESP32-S3.

## Prerequisites

### Hardware Required
- XIAO ESP32-S3 development board
- USB-C cable
- Xbox One/Series Wireless Controller (Bluetooth enabled)
- LEGO Technic Move Hub (from set 42176)

### Software Required
- Python 3.x installed on your computer
- One of the following tools:
  - **mpremote** (recommended): `pip install mpremote`
  - **Thonny IDE** (easiest for beginners)
  - **ampy**: `pip install adafruit-ampy`

### MicroPython Firmware
1. Download the latest MicroPython firmware for ESP32-S3 from: https://micropython.org/download/ESP32_GENERIC_S3/
2. Flash it using esptool:
   ```bash
   pip install esptool
   esptool.py --chip esp32s3 --port COM_PORT erase_flash
   esptool.py --chip esp32s3 --port COM_PORT write_flash -z 0 firmware.bin
   ```
   Replace `COM_PORT` with your actual port (e.g., COM3 on Windows)

## Installing Required Libraries

The code uses `aioble` which needs to be installed on the ESP32:

### Method 1: Using mpremote
```bash
mpremote mip install aioble
```

### Method 2: Using Thonny
1. Tools → Manage packages
2. Search for "aioble"
3. Click Install

## Deploying Code to ESP32

### Method 1: Using mpremote (Recommended)
```bash
# Navigate to project directory
cd esp32-xbox-lego-rc-upython

# Create src directory on device
mpremote mkdir :src
mpremote mkdir :src/utils

# Upload utility modules
mpremote cp src/utils/constants.py :src/utils/constants.py
mpremote cp src/utils/ble_utils.py :src/utils/ble_utils.py
mpremote cp src/utils/math_utils.py :src/utils/math_utils.py
mpremote cp src/utils/__init__.py :src/utils/__init__.py

# Upload client modules
mpremote cp src/lego_client.py :src/lego_client.py
mpremote cp src/xbox_client.py :src/xbox_client.py

# Upload test scripts
mpremote cp testing/test_lego_hub.py :test_lego_hub.py
mpremote cp testing/test_xbox_controller.py :test_xbox_controller.py
```

### Method 2: Using Thonny
1. Open Thonny IDE
2. Select MicroPython (ESP32) interpreter in bottom-right
3. In the file browser, create the directory structure on the device
4. Right-click each file and "Upload to /"

## Running Tests

### Test 1: LEGO Hub Connection

**Preparation:**
1. Turn on your LEGO Technic Move Hub (it should start blinking)
2. Make sure it's not connected to anything else

**Run the test:**
```python
# Connect to ESP32 via mpremote or Thonny REPL
import test_lego_hub
test_lego_hub.run()
```

**Expected Output:**
```
=== Test 1: Scanning for LEGO hub ===
Found device: Technic Move Hub (XX:XX:XX:XX:XX:XX)
✓ Found LEGO hub!

=== Test 2: Connecting to LEGO hub ===
Connecting to LEGO hub...
Connected! Discovering services...
✓ Connected successfully!

=== Test 3: Steering calibration ===
Calibrating steering...
✓ Calibration successful!

... (more tests)
```

**Troubleshooting:**
- If hub not found: Make sure it's powered on and blinking (pairing mode)
- If connection fails: Try power cycling the hub
- If commands don't work: Check that calibration completed successfully

### Test 2: Xbox Controller Connection

**Preparation:**
1. Turn on your Xbox controller
2. Put it in pairing mode: Hold the Xbox button + the pairing button (small button on top) until it starts flashing rapidly
3. Make sure it's not connected to any other device

**Run the test:**
```python
# Connect to ESP32 via mpremote or Thonny REPL
import test_xbox_controller
test_xbox_controller.run()
```

**Expected Output:**
```
=== Test 1: Scanning for Xbox controller ===
Looking for device: 'Xbox Wireless Controller'
Found device: Xbox Wireless Controller (XX:XX:XX:XX:XX:XX)
✓ Found Xbox controller!

=== Test 2: Connecting to Xbox controller ===
Connecting to Xbox controller...
Connected! Discovering services...
✓ Connected successfully!

=== Test 3: Single input report read ===
Press any button on the controller...
✓ Received report: 15 bytes
...
```

**Troubleshooting:**
- Controller not found: Make sure it's in pairing mode (rapidly flashing)
- Connection timeout: Controller may have paired with another device - unpair it first
- No input data: Try pressing buttons and moving sticks

### Quick Tests

For faster iteration, use the quick test functions:

```python
# Quick LEGO test - just scan, connect, calibrate
import test_lego_hub
client = test_lego_hub.quick_test()

# Quick Xbox test - scan, connect, show inputs for 10s
import test_xbox_controller
client = test_xbox_controller.quick_test()
```

## Testing Individual Functions

Once connected, you can test individual functions:

### LEGO Hub Functions
```python
import test_lego_hub
import asyncio

# Run quick test to get connected client
client = test_lego_hub.quick_test()

# Test drive command
await client.drive(speed=50, angle=0, lights=client.LIGHTS_ON_ON)
await asyncio.sleep(2)
await client.drive(speed=0, angle=0, lights=client.LIGHTS_OFF_OFF)

# Test LED colors
await client.change_led_color(9)  # Red
await asyncio.sleep(1)
await client.change_led_color(6)  # Green

# Disconnect when done
await client.disconnect()
```

### Xbox Controller Functions
```python
import test_xbox_controller
import asyncio

# Run quick test
client = test_xbox_controller.quick_test()

# The quick test shows inputs for 10 seconds
# To access state manually:
print(client.state.left_stick_x)
print(client.state.button_a)

# Disconnect when done
await client.disconnect()
```

## Common Issues

### Import Errors
```
ImportError: no module named 'utils'
```
**Solution:** Make sure the src/utils directory is uploaded to the device

### Connection Timeout
```
Connection timeout after 10000ms
```
**Solution:**
- Device may be too far away - bring it closer
- Device may be connected elsewhere - disconnect/power cycle it
- Try increasing timeout in code

### Memory Errors
```
MemoryError: memory allocation failed
```
**Solution:**
- ESP32 has limited RAM
- Try running one test at a time
- Use `import gc; gc.collect()` to free memory between tests

## Next Steps

After verifying both clients work individually:
1. Test dual simultaneous connections with `test_dual_connection.py`
2. Proceed to full application integration
3. Add display and UI components

## Debugging Tips

### Enable Verbose Output
Uncomment debug print statements in the client files to see detailed BLE communication

### Monitor BLE Activity
```python
# In REPL
import bluetooth
bluetooth.active(True)
# Check active connections
```

### Memory Monitoring
```python
import gc
print(f"Free memory: {gc.mem_free()} bytes")
gc.collect()
print(f"After collection: {gc.mem_free()} bytes")
```

### Check Versions
```python
import sys
print(sys.implementation)  # Should show MicroPython version
```
