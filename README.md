# ESP32 Xbox LEGO RC Controller

Control your LEGO Technic Move Hub (set 42176) wirelessly with an Xbox One controller via an ESP32-S3 BLE bridge.

![Project Status](https://img.shields.io/badge/Phase%201-Complete-brightgreen)
![MicroPython](https://img.shields.io/badge/MicroPython-v1.20+-blue)
![ESP32-S3](https://img.shields.io/badge/ESP32--S3-Supported-orange)

## Overview

This project creates a wireless bridge between an Xbox Wireless Controller and a LEGO Technic Move Hub using a XIAO ESP32-S3 microcontroller running MicroPython. The ESP32 maintains dual simultaneous BLE connections, translating Xbox controller inputs into real-time motor control commands for the LEGO RC car.

### Key Features

- **Dual BLE Connections:** Simultaneous connections to Xbox controller and LEGO hub
- **Real-Time Control:** Low-latency input translation (<50ms target)
- **Full Input Support:** All buttons, analog sticks, triggers, and D-pad
- **Motor Control:** Drive, steering, and LED control for LEGO Technic vehicles
- **Event-Driven:** Efficient BLE communication using notifications
- **Comprehensive Testing:** 15+ test scripts validating all functionality
- **Well Documented:** Complete design spec, testing guides, and API documentation

## Hardware Requirements

- **XIAO ESP32-S3** - Main microcontroller with BLE 5.0
- **Xbox One/Series Wireless Controller** - BLE-enabled version
- **LEGO Technic Move Hub** - From set 42176 (Porsche GT4 e-Performance)
- **USB-C Cable** - For programming the ESP32
- *(Optional)* 1000mAh LiPo battery for portable operation
- *(Future)* SSD1306 OLED display (128x64) for status/UI

## Quick Start

### 1. Install MicroPython

```bash
# Install esptool
pip install esptool

# Download firmware from https://micropython.org/download/ESP32_GENERIC_S3/

# Flash to ESP32-S3
esptool.py --chip esp32s3 --port COM3 erase_flash
esptool.py --chip esp32s3 --port COM3 write_flash -z 0 firmware.bin
```

### 2. Deploy Code

```bash
# Install mpremote
pip install mpremote

# Deploy everything (includes library installation)
python tools/deploy.py --libs --test --port COM3
```

### 3. Test LEGO Hub

```bash
# Connect to REPL
mpremote

# Run LEGO hub test
>>> import test_lego_hub
>>> test_lego_hub.run()
```

### 4. Test Xbox Controller

```bash
# In REPL
>>> import test_xbox_controller
>>> test_xbox_controller.run()
```

See [TESTING_QUICKSTART.md](TESTING_QUICKSTART.md) for detailed instructions.

## Project Status

### ✓ Phase 1: Core BLE Connectivity (COMPLETE)

**Achievements:**
- ✓ LEGO hub BLE client with motor control
- ✓ Xbox controller BLE client with full input reading
- ✓ Comprehensive test suites (15 tests total)
- ✓ Automated deployment tools
- ✓ Complete documentation

**Critical Discoveries:**
1. **Active Scanning Required:** BLE scans must use `active=True` to receive device names
2. **LEGO Hub Pairing:** Hub requires `pair(bond=True)` or it ignores all commands
3. **Xbox Controller Pairing:** Controller requires `pair(bond=True)` to exit pairing mode
4. **Xbox Report Map:** Controller requires reading HID Report Map (0x2A4B) before sending input
5. **Event-Driven Input:** Xbox controller only sends data when inputs change

All requirements are implemented and validated on hardware.

### 🔄 Phase 2: Control Loop (IN PROGRESS)

**Next Steps:**
- Implement BLE manager for dual simultaneous connections
- Create input translator (Xbox inputs → LEGO commands)
- Develop main control loop
- Test integrated system

### 📋 Phase 3: Display & UI (PLANNED)

- SSD1306 OLED display integration
- Menu system for settings
- Battery monitoring
- Configuration management

### 🎯 Phase 4: Polish & Features (PLANNED)

- Power management
- Auto-reconnection
- Control modes (normal, turbo, slow)
- Calibration routines

## Documentation

- **[DESIGN_SPEC.md](DESIGN_SPEC.md)** - Complete design specification with architecture, components, and phases
- **[docs/testing_guide.md](docs/testing_guide.md)** - Comprehensive testing documentation and troubleshooting
- **[TESTING_QUICKSTART.md](TESTING_QUICKSTART.md)** - 5-step quick start guide
- **API Reference:** See docstrings in source files

## Project Structure

```
esp32-xbox-lego-rc-upython/
├── README.md                           # This file
├── DESIGN_SPEC.md                      # Complete design specification
├── TESTING_QUICKSTART.md               # Quick start testing guide
├── src/
│   ├── lego_client.py                  # LEGO hub BLE client
│   ├── xbox_client.py                  # Xbox controller BLE client
│   └── utils/
│       ├── constants.py                # BLE UUIDs, motor IDs, constants
│       ├── ble_utils.py                # BLE scanning utilities
│       └── math_utils.py               # Input processing utilities
├── testing/
│   ├── test_lego_hub.py                # LEGO hub test suite (8 tests)
│   ├── test_xbox_controller.py         # Xbox controller test suite (7 tests)
│   ├── discover_xbox_characteristics.py # BLE service discovery
│   ├── discover_xbox_setup.py          # Initialization testing
│   └── ble_scan.py                     # Simple BLE scanner
├── tools/
│   └── deploy.py                       # Automated deployment script
├── docs/
│   └── testing_guide.md                # Detailed testing documentation
└── reference/
    └── LEGO Technic 42176 XBOX RC.py   # Desktop reference implementation
```

## Control Mapping (Planned)

| Xbox Input | LEGO Function |
|------------|---------------|
| Left Stick X | Steering |
| Right Stick Y | Throttle (Forward/Reverse) |
| Triggers | Brake |
| Y Button | Toggle Lights |
| A Button | Confirm/Select |
| B Button | Cancel/Back |

## Technical Highlights

### BLE Protocol Details

**LEGO Technic Move Hub:**
- Service UUID: `00001623-1212-EFDE-1623-785FEABCD123`
- Characteristic UUID: `00001624-1212-EFDE-1623-785FEABCD123`
- Requires authenticated pairing before accepting commands

**Xbox Wireless Controller:**
- HID Service UUID: `0x1812`
- HID Report UUID: `0x2A4D`
- Report Map UUID: `0x2A4B` (must be read to initialize)
- 15-byte HID reports with sticks, triggers, buttons, D-pad

### Critical Implementation Notes

All BLE operations require specific initialization sequences discovered through systematic hardware testing:

```python
# LEGO Hub - MUST pair before sending commands
await connection.pair(bond=True)

# Xbox Controller - MUST read Report Map before subscribing
report_map = await report_map_char.read()
await report_char.subscribe(notify=True)
```

See [DESIGN_SPEC.md](DESIGN_SPEC.md) section 6.2.1 for complete details.

## Requirements

### Software
- **MicroPython:** v1.20 or later
- **Python:** 3.8+ (for deployment tools)
- **Libraries:**
  - `aioble` (installed via mpremote)
  - `asyncio` (built-in)
  - `bluetooth` (built-in)

### Development Tools
- `mpremote` - Recommended for deployment
- `esptool.py` - For flashing firmware
- *(Optional)* Thonny IDE - Alternative to mpremote

## Testing

The project includes comprehensive test suites:

**LEGO Hub Tests (8 tests):**
- Scanning and connection
- Steering calibration
- LED color control
- Motor control
- Drive commands
- Interactive demo

**Xbox Controller Tests (7 tests):**
- Scanning and connection
- Single report reading
- Button mapping verification
- Analog input testing
- D-pad testing
- Continuous input display

**Discovery Tools:**
- BLE service/characteristic discovery
- Systematic initialization testing

Run all tests: `test_lego_hub.run()` and `test_xbox_controller.run()`

## Troubleshooting

### Device Not Found
- **LEGO:** Ensure hub is powered on and blinking (pairing mode)
- **Xbox:** Hold Xbox + pairing button until rapid flashing
- Active scanning (`active=True`) is required - already implemented

### Hub Connects But Doesn't Move
- CRITICAL: Hub requires pairing - check for "Paired successfully!" message
- Power cycle hub and retry
- See [docs/testing_guide.md](docs/testing_guide.md)

### Controller No Input Data
- CRITICAL: Controller requires Report Map read - check for "Report Map read: X bytes"
- Input is event-driven - you must press buttons/move sticks to see data
- See [docs/testing_guide.md](docs/testing_guide.md)

## Contributing

This is a personal project, but suggestions and improvements are welcome! Key areas for contribution:
- Phase 2 implementation (BLE manager, input translator)
- Display/UI development (Phase 3)
- Control mode implementations
- Testing and validation

## References

- **ESP32-S3:** [Datasheet](https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf)
- **MicroPython:** [Documentation](https://docs.micropython.org/)
- **aioble:** [GitHub](https://github.com/micropython/micropython-lib/tree/master/micropython/bluetooth/aioble)
- **LEGO Hub Protocol:** Based on set 42176 reference implementation

## License

MIT License - See source files for details.

## Acknowledgments

- Based on working reference implementations:
  - AndyHegemann/Micropython-ESP32-BLE-Xbox-Controller
  - alejandro7896/ESP32_Xbox_Wireless_Controller
- LEGO Technic set 42176 provided the reference Python implementation

---

**Project Version:** 1.1
**Last Updated:** 2025-10-31
**Status:** Phase 1 Complete ✓
