# Testing Quick Start Guide

This guide will get you testing the LEGO hub and Xbox controller clients quickly.

## Step 1: Install Required Software

```bash
# Install mpremote (recommended tool)
pip install mpremote

# Alternative: Install Thonny IDE
# Download from https://thonny.org/
```

## Step 2: Flash MicroPython Firmware

1. Download ESP32-S3 firmware: https://micropython.org/download/ESP32_GENERIC_S3/
2. Install esptool: `pip install esptool`
3. Find your COM port (Device Manager on Windows, or `ls /dev/tty*` on Linux/Mac)
4. Flash firmware:

```bash
# Erase flash
esptool.py --chip esp32s3 --port COM3 erase_flash

# Write firmware (replace firmware.bin with your downloaded file)
esptool.py --chip esp32s3 --port COM3 write_flash -z 0 firmware.bin
```

Replace `COM3` with your actual port.

## Step 3: Deploy Code to ESP32

```bash
# Navigate to project directory
cd esp32-xbox-lego-rc-upython

# Install required libraries
python tools/deploy.py --libs --port COM3

# Deploy all code including tests
python tools/deploy.py --test --port COM3
```

Replace `COM3` with your port. Omit `--port COM3` to auto-detect.

## Step 4: Test LEGO Hub

**Hardware Prep:**
- Turn on LEGO Technic Move Hub (should blink)
- Keep it nearby (within 10 meters)

**Run Test:**
```bash
# Connect to REPL
mpremote

# In MicroPython REPL:
>>> import test_lego_hub
>>> test_lego_hub.run()
```

**Expected:** You should see the hub connect, calibrate steering, test motors, and control LEDs.

## Step 5: Test Xbox Controller

**Hardware Prep:**
- Turn on Xbox controller
- Put in pairing mode: Hold Xbox button + pairing button until rapidly flashing
- Make sure not connected to any other device

**Run Test:**
```bash
# Connect to REPL (if not already)
mpremote

# In MicroPython REPL:
>>> import test_xbox_controller
>>> test_xbox_controller.run()
```

**Expected:** Controller connects and you see real-time input from buttons/sticks/triggers.

## Quick Commands Reference

### Deploy Commands
```bash
# Deploy everything with tests
python tools/deploy.py --test

# Deploy with library installation
python tools/deploy.py --libs --test

# Clean device first, then deploy
python tools/deploy.py --clean --test

# List files on device
python tools/deploy.py --list
```

### REPL Commands
```bash
# Connect to device
mpremote

# In REPL - LEGO quick test
>>> import test_lego_hub
>>> test_lego_hub.quick_test()

# In REPL - Xbox quick test
>>> import test_xbox_controller
>>> test_xbox_controller.quick_test()

# Exit REPL
>>> Ctrl+D or Ctrl+X
```

### Manual Control (After Quick Test)

**LEGO Hub:**
```python
>>> import test_lego_hub
>>> import asyncio
>>> client = test_lego_hub.quick_test()

# Drive forward
>>> await client.drive(speed=50, angle=0)
>>> await asyncio.sleep(2)
>>> await client.drive(speed=0, angle=0)

# Turn LED red
>>> await client.change_led_color(9)

# Disconnect
>>> await client.disconnect()
```

**Xbox Controller:**
```python
>>> import test_xbox_controller
>>> client = test_xbox_controller.quick_test()
# Shows inputs for 10 seconds, then disconnects automatically
```

## Troubleshooting

### "Module not found" Error
**Problem:** `ImportError: no module named 'utils'`

**Solution:** Code not deployed properly
```bash
python tools/deploy.py --test
```

### Device Not Found During Scan
**Problem:** `No device matching 'xbox' found`

**Solutions:**
- **LEGO:** Make sure hub is powered on and blinking
- **Xbox:** Make sure controller is in pairing mode (rapidly flashing)
- Move devices closer to ESP32
- Try power cycling the device

### Connection Timeout
**Problem:** `Connection timeout after 10000ms`

**Solutions:**
- Device may already be connected elsewhere - disconnect it
- Power cycle the device
- Check if device is within range

### Memory Errors
**Problem:** `MemoryError: memory allocation failed`

**Solutions:**
```python
>>> import gc
>>> gc.collect()  # Free memory
```
- Restart the ESP32: Press reset button or power cycle
- Run one test at a time instead of both

### aioble Not Found
**Problem:** `ImportError: no module named 'aioble'`

**Solution:**
```bash
python tools/deploy.py --libs
```

## What to Look For

### Successful LEGO Test
```
✓ Found LEGO hub!
✓ Connected successfully!
✓ Calibration successful!
✓ LED test complete
✓ Motor control test complete
✓ Drive command test complete
```

### Successful Xbox Test
```
✓ Found Xbox controller!
✓ Connected successfully!
✓ Received report: 15 bytes
```

Followed by real-time input display showing stick movements, button presses, etc.

## Next Steps

Once both tests pass:
1. Review the test output to ensure all features work
2. Proceed to implement the BLE manager for dual connections
3. Create the main application loop
4. Add display and UI functionality

## Need Help?

- Check [docs/testing_guide.md](docs/testing_guide.md) for detailed troubleshooting
- Review the code in `testing/` directory to understand what each test does
- Check MicroPython logs for detailed error messages
