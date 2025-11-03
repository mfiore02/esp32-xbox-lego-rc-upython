# ESP32 Xbox LEGO RC Controller - Design Specification

**Project Name:** ESP32 Xbox LEGO RC Controller
**Target Platform:** XIAO ESP32-S3 with MicroPython
**Version:** 1.1
**Last Updated:** 2025-11-03

---

## 1. Executive Summary

This project implements a wireless controller bridge that connects an Xbox One controller to a LEGO Technic Move Hub (set 42176) via Bluetooth Low Energy (BLE). The ESP32-S3 microcontroller acts as the intermediary, receiving inputs from the Xbox controller and translating them into motor control commands for the LEGO vehicle.

### Key Features
- Dual simultaneous BLE connections (Xbox controller + LEGO hub)
- Real-time input translation with low latency
- OLED display for status monitoring and configuration
- Physical UI controls for settings and mode selection
- Battery-powered portable operation
- Persistent configuration storage

---

## 2. System Architecture

### 2.1 Hardware Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ESP32-S3 Main Unit                       │
│  ┌────────────────────────────────────────────────────┐    │
│  │              XIAO ESP32-S3                          │    │
│  │  ┌──────────────────────────────────────────┐      │    │
│  │  │  • Dual-core Xtensa LX7 @ 240MHz        │      │    │
│  │  │  • 512KB SRAM, 8MB Flash                │      │    │
│  │  │  • BLE 5.0 Radio                         │      │    │
│  │  │  • MicroPython Runtime                   │      │    │
│  │  └──────────────────────────────────────────┘      │    │
│  └────────────────────────────────────────────────────┘    │
│                                                             │
│  Power:          Display:           UI Input:              │
│  • 1000mAh LiPo  • SSD1306 OLED    • Buttons/Joystick     │
│  • Charge IC     • 128x64 I2C      • Analog/Digital I/O    │
│  • Power Switch  • Status Display   • Menu Navigation      │
└─────────────────────────────────────────────────────────────┘
              │                            │
              │ BLE                        │ BLE
              ▼                            ▼
    ┌──────────────────┐        ┌──────────────────┐
    │  Xbox One        │        │  LEGO Technic    │
    │  Controller      │        │  Move Hub        │
    │                  │        │  (Set 42176)     │
    └──────────────────┘        └──────────────────┘
```

### 2.2 Software Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Application Layer                       │
├─────────────────────────────────────────────────────────────┤
│  Main Controller Loop                                       │
│  • Connection State Machine                                 │
│  • Input Processing Pipeline                                │
│  • Command Translation & Dispatch                           │
└─────────────────────────────────────────────────────────────┘
                          │
    ┌─────────────────────┼─────────────────────┐
    ▼                     ▼                     ▼
┌─────────┐        ┌─────────┐         ┌─────────────┐
│ BLE     │        │ Input   │         │ Display     │
│ Manager │        │ Handler │         │ Manager     │
└─────────┘        └─────────┘         └─────────────┘
    │                  │                     │
    ▼                  ▼                     ▼
┌─────────┐        ┌─────────┐         ┌─────────────┐
│ Xbox    │        │ Config  │         │ UI          │
│ Client  │        │ Manager │         │ Framework   │
└─────────┘        └─────────┘         └─────────────┘
    │
    ▼
┌─────────┐
│ LEGO    │
│ Client  │
└─────────┘
```

---

## 3. Hardware Specifications

### 3.1 XIAO ESP32-S3
- **MCU:** Espressif ESP32-S3 (dual-core Xtensa LX7 @ 240MHz)
- **Memory:** 512KB SRAM, 8MB Flash
- **Wireless:** WiFi 802.11 b/g/n, BLE 5.0
- **GPIO:** 21 GPIO pins (digital/analog/PWM/I2C/SPI/UART)
- **Power:** 3.3V operating voltage, USB-C charging

### 3.2 Display Module
- **Model:** SSD1306 OLED
- **Resolution:** 128x64 pixels
- **Interface:** I2C
- **Color:** Monochrome (white/blue)

### 3.3 UI Input
- **Option A:** Mechanical buttons (4-5 buttons)
  - Navigation: Up, Down, Left, Right
  - Action: Select/Enter
- **Option B:** Clickable joystick module
  - Analog X/Y axes + push button
  - Single component for all navigation

### 3.4 Power System
- **Battery:** 1000mAh LiPo (3.7V nominal)
- **Charging:** USB-C via onboard charge controller
- **Power Switch:** SPST toggle/slide switch
- **Expected Runtime:** 4-6 hours continuous operation

### 3.5 Peripheral Devices
- **Xbox One Controller:** BLE-enabled wireless controller
- **LEGO Technic Move Hub:** From set 42176, BLE-enabled hub with motors/servos

---

## 4. Software Components

### 4.1 Core Modules

#### 4.1.1 BLE Connection Manager (`ble_manager.py`)
**Responsibilities:**
- Initialize and manage BLE radio
- Handle dual simultaneous connections
- Monitor connection health
- Implement reconnection logic
- Manage pairing state

**Key APIs:**
```python
async def initialize()
async def scan_devices(timeout: int) -> List[BLEDevice]
async def connect_xbox(address: str) -> bool
async def connect_lego(address: str) -> bool
async def disconnect_all()
async def get_connection_status() -> dict
```

#### 4.1.2 Xbox Controller Client (`xbox_client.py`)
**Responsibilities:**
- Connect to Xbox controller via BLE
- Subscribe to input notifications
- Parse HID report data
- Normalize input values
- Apply dead zones

**Key APIs:**
```python
async def connect(address: str) -> bool
async def start_input_loop(callback=None)
def parse_hid_report(report: bytes)
def get_state() -> ControllerState
def set_dead_zone(dead_zone: float)
async def wait_for_button(button_name: str, timeout_ms: int) -> bool
```

**CRITICAL Initialization Sequence:**
```python
# Step 1: Connect to device
connection = await device.connect(timeout_ms=10000)

# Step 2: Discover HID service and characteristics
hid_service = await connection.service(bluetooth.UUID(0x1812))
report_characteristic = await hid_service.characteristic(bluetooth.UUID(0x2A4D))

# Step 3: REQUIRED - Pair with controller
await connection.pair(bond=True)

# Step 4: REQUIRED - Read Report Map to initialize controller
report_map_char = await hid_service.characteristic(bluetooth.UUID(0x2A4B))
report_map = await report_map_char.read()

# Step 5: Subscribe to notifications
await report_characteristic.subscribe(notify=True)

# Step 6: Read input reports as they arrive (event-driven)
report = await report_characteristic.notified()
```

**HID Report Format (15 bytes minimum):**
- Bytes 0-1: Left stick X (uint16 LE, 0-65535 → -1.0 to 1.0)
- Bytes 2-3: Left stick Y (uint16 LE, 0-65535 → -1.0 to 1.0, inverted: low=up, mapped to +1.0)
- Bytes 4-5: Right stick X (uint16 LE, 0-65535 → -1.0 to 1.0)
- Bytes 6-7: Right stick Y (uint16 LE, 0-65535 → -1.0 to 1.0, inverted: low=up, mapped to +1.0)
- Bytes 8-9: Left trigger (uint16 LE, 0-1023 → 0.0 to 1.0)
- Bytes 10-11: Right trigger (uint16 LE, 0-1023 → 0.0 to 1.0)
- Byte 12: D-pad (8-direction: 0/15=center, 1=up, 2=up-right, 3=right, 4=down-right, 5=down, 6=down-left, 7=left, 8=up-left)
- Byte 13: Buttons (A=0x01, B=0x02, X=0x08, Y=0x10, LB=0x40, RB=0x80)
- Byte 14: More buttons (View=0x04, Menu=0x08, LS=0x20, RS=0x40, Share=0x01*)
  - *Note: Share button may not be available on all controller revisions

**Data Structure:**
```python
class ControllerState:
    left_stick_x: float      # -1.0 (left) to +1.0 (right)
    left_stick_y: float      # -1.0 (down) to +1.0 (up)
    right_stick_x: float     # -1.0 (left) to +1.0 (right)
    right_stick_y: float     # -1.0 (down) to +1.0 (up)
    left_trigger: float      # 0.0 (not pressed) to 1.0 (fully pressed)
    right_trigger: float     # 0.0 (not pressed) to 1.0 (fully pressed)
    buttons: dict            # Button name -> bool
    dpad: dict               # Direction -> bool
```

#### 4.1.3 LEGO Hub Client (`lego_client.py`)
**Responsibilities:**
- Connect to LEGO Technic Move Hub
- Send motor control commands
- Send LED color commands
- Handle calibration sequences
- Manage motor state

**Key APIs:**
```python
async def connect(device) -> bool
async def disconnect()
async def drive(speed: int, angle: int, lights: int)
async def calibrate_steering()
def is_connected() -> bool
```

**CRITICAL Initialization Sequence:**
```python
# Step 1: Connect to device
connection = await device.connect(timeout_ms=10000)

# Step 2: Discover LEGO service and characteristic
service = await connection.service(LEGO_SERVICE_UUID)
characteristic = await service.characteristic(LEGO_CHARACTERISTIC_UUID)

# Step 3: REQUIRED - Pair with hub
await connection.pair(bond=True)  # CRITICAL - hub ignores commands without this

# Step 4: Send commands
await characteristic.write(command_bytes, response=True)
```

**BLE Protocol Details:**
- Service UUID: `00001623-1212-EFDE-1623-785FEABCD123`
- Characteristic UUID: `00001624-1212-EFDE-1623-785FEABCD123`
- **Pairing:** REQUIRED with `bond=True` - hub will connect but ignore all commands without pairing
- **Command Format (Drive):**
  ```
  [0x0d, 0x00, 0x81, 0x36, 0x11, 0x51, 0x00, 0x03, 0x00, speed, angle, lights, 0x00]
  ```
  - speed: -100 to 100 (signed byte, forward/reverse)
  - angle: -100 to 100 (signed byte, left/right steering)
  - lights: 0x00=off, 0x64=on, or RGB pattern

#### 4.1.4 Input Translator (`input_translator.py`)
**Responsibilities:**
- Map controller inputs to vehicle commands
- Apply control curves and scaling
- Implement control modes (normal, turbo, slow)
- Handle button-triggered actions
- Manage lights and special functions

**Key APIs:**
```python
def translate(controller_state: ControllerState) -> VehicleCommand
def set_control_mode(mode: str)
def apply_calibration(calibration: dict)
```

**Control Mapping (Default):**
- Left Stick Y → Throttle (forward/reverse)
- Right Stick X → Steering angle
- Left Trigger → Brake (reduces speed)
- Right Trigger → Boost (increases speed)
- A Button → Toggle lights
- X Button → Emergency stop
- LB Button → Cycle control mode
- D-pad Up/Down → Adjust speed limit

#### 4.1.5 Display Manager (`display_manager.py`)
**Responsibilities:**
- Initialize SSD1306 display
- Render UI screens
- Update status information
- Display connection state
- Show battery level
- Render menus

**Key APIs:**
```python
async def initialize()
def clear()
def show_status_screen(data: dict)
def show_menu_screen(items: list, selected: int)
def show_connection_screen(xbox_status: str, lego_status: str)
def update()
```

#### 4.1.6 UI Framework (`ui_framework.py`)
**Responsibilities:**
- Handle screen navigation
- Process button/joystick inputs
- Manage menu state
- Implement settings screens
- Coordinate with display manager

**Key APIs:**
```python
async def initialize()
async def process_input(button: str)
def navigate_to(screen: str)
def get_current_screen() -> str
```

**Screen Types:**
- Status Screen (default)
- Connection Screen
- Settings Menu
- Calibration Screen
- About/Info Screen

#### 4.1.7 Configuration Manager (`config_manager.py`)
**Responsibilities:**
- Load/save configuration from flash
- Manage user preferences
- Store device addresses
- Save calibration data
- Provide defaults

**Key APIs:**
```python
def load_config() -> dict
def save_config(config: dict) -> bool
def get(key: str, default=None)
def set(key: str, value)
def reset_to_defaults()
```

**Configuration Schema:**
```python
{
    "devices": {
        "xbox_address": "XX:XX:XX:XX:XX:XX",
        "lego_address": "XX:XX:XX:XX:XX:XX"
    },
    "controls": {
        "dead_zone": 0.03,
        "steering_curve": 1.0,
        "throttle_curve": 1.0,
        "reverse_steering": false
    },
    "calibration": {
        "steering_center": 0,
        "steering_max_left": -100,
        "steering_max_right": 100
    },
    "display": {
        "brightness": 255,
        "auto_off": 300
    }
}
```

#### 4.1.8 Power Manager (`power_manager.py`)
**Responsibilities:**
- Monitor battery voltage
- Calculate battery percentage
- Implement low-power modes
- Handle auto-shutdown
- Wake-on-button support

**Key APIs:**
```python
async def initialize()
def get_battery_voltage() -> float
def get_battery_percentage() -> int
async def enter_sleep_mode()
def is_low_battery() -> bool
```

### 4.2 Main Application (`main.py`)

**Responsibilities:**
- Initialize all subsystems
- Implement main control loop
- Coordinate state machine
- Handle errors and recovery
- Manage graceful shutdown

**State Machine:**
```
┌─────────────┐
│   STARTUP   │
└──────┬──────┘
       │
       ▼
┌─────────────┐     ┌──────────────┐
│  SCANNING   │────▶│  CONNECTING  │
└─────────────┘     └──────┬───────┘
       ▲                   │
       │                   ▼
       │            ┌──────────────┐
       │            │  CONNECTED   │
       │            └──────┬───────┘
       │                   │
       │                   ▼
       │            ┌──────────────┐
       └────────────│   RUNNING    │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │   SHUTDOWN   │
                    └──────────────┘
```

---

## 5. Development Phases

### Phase 1: Core BLE Connectivity (Week 1-2) ✓ COMPLETE
**Objectives:**
- Port LEGO hub connection to MicroPython/aioble ✓
- Implement Xbox controller BLE connection ✓
- Test individual device connections ✓
- Verify command transmission to LEGO hub ✓
- Document BLE requirements and critical initialization steps ✓

**Deliverables:**
- `lego_client.py` - Working LEGO hub connection and motor control ✓
- `xbox_client.py` - Working Xbox controller connection and input reading ✓
- `utils/ble_utils.py` - BLE scanning utilities with active scanning ✓
- `utils/math_utils.py` - Input processing utilities ✓
- `testing/test_lego_hub.py` - Comprehensive LEGO hub test suite (5 tests) ✓
- `testing/test_xbox_controller.py` - Comprehensive Xbox controller test suite (8 tests) ✓
- `testing/discover_xbox_characteristics.py` - BLE service discovery tool ✓
- `testing/discover_xbox_setup.py` - Systematic initialization testing tool ✓
- `tools/deploy.py` - Automated deployment script ✓
- `docs/testing_guide.md` - Comprehensive testing documentation ✓
- `TESTING_QUICKSTART.md` - Quick start testing guide ✓

**Success Criteria:**
- Successfully connect to LEGO hub ✓
- Send motor commands to LEGO hub and control RC car ✓
- Successfully connect to Xbox controller ✓
- Receive real-time input data from Xbox controller ✓
- Validated all critical BLE requirements through hardware testing ✓

**Critical Discoveries:**
1. Active scanning (`active=True`) required for device name discovery
2. Both devices require pairing with `bond=True`
3. Xbox controller requires reading Report Map (0x2A4B) before sending input
4. Xbox controller uses event-driven notifications (only sends on state change)
5. Systematic testing revealed undocumented initialization requirements

**Next Steps:**
- Implement BLE manager for dual simultaneous connections (Phase 2)
- Create input translator to map Xbox inputs to LEGO commands (Phase 2)

### ✓ Phase 2: Control Loop Implementation (COMPLETE)
**Objectives:**
- Implement input translation logic ✓
- Create main control loop ✓
- Test basic drive/steer/lights functionality ✓
- Optimize latency and responsiveness ✓

**Deliverables:**
- `input_translator.py` - Controller to vehicle command mapping with control modes ✓
- `main.py` - Main application loop ✓
- `ble_manager.py` - Dual BLE connection manager ✓
- `utils/bonding_utils.py` - Bonding data management ✓
- `testing/test_ble_manager.py` - BLE manager test suite (7 tests) ✓
- `testing/test_input_translator.py` - Input translator test suite (11 tests) ✓

**Success Criteria:**
- Control latency < 50ms ✓
- Smooth steering and throttle response ✓
- All basic controls working (forward, reverse, steer, lights) ✓
- No connection drops during operation ✓
- Control modes implemented (normal, turbo, slow) ✓

### Phase 3: UI and Display (Week 4)
**Objectives:**
- Implement OLED display driver
- Create status display screens
- Add settings/configuration screens
- Implement button navigation

**Deliverables:**
- `display_manager.py` - Display driver and rendering
- `ui_framework.py` - Screen navigation and menus
- `config_manager.py` - Configuration persistence

**Success Criteria:**
- Clear, readable status display
- Working menu navigation
- Settings can be changed and saved
- Connection status visible at all times

### Phase 4: Polish and Advanced Features (Week 5-6)
**Objectives:**
- Implement power management
- Enhance reconnection logic
- Add advanced calibration routines
- Comprehensive testing
- Performance optimization

**Deliverables:**
- `power_manager.py` - Battery monitoring and power saving
- Enhanced error handling throughout
- User documentation
- Testing suite

**Success Criteria:**
- Battery monitoring working
- Enhanced auto-reconnect on disconnect
- All features stable and tested
- Documentation complete

---

## 6. Technical Requirements and Constraints

### 6.1 Performance Requirements
- **Control Latency:** < 50ms from controller input to motor command
- **Connection Stability:** 99.9% uptime during normal operation
- **Battery Life:** Minimum 4 hours continuous operation
- **Display Update Rate:** 10+ fps for smooth UI
- **Memory Usage:** < 400KB RAM (leave headroom for BLE stack)

### 6.2 BLE Requirements
- **Simultaneous Connections:** 2 active connections (Xbox + LEGO)
- **Connection Range:** 10+ meters line-of-sight
- **Auto-reconnect:** Attempt reconnection within 5 seconds of disconnect
- **Pairing:** Support BLE pairing with both devices

### 6.2.1 CRITICAL BLE Implementation Requirements (Validated in Phase 1)

The following requirements were discovered during Phase 1 hardware testing and are ESSENTIAL for successful BLE operation:

1. **Active Scanning Required**
   - BLE scanning MUST use `active=True` parameter in aioble.scan()
   - Without active scanning, scan response packets are not received
   - Device names are contained in scan response packets, not advertising packets
   - Passive scanning will cause all device discovery to fail
   ```python
   # REQUIRED:
   async with aioble.scan(duration_ms=timeout_ms, active=True) as scanner:
   ```

2. **LEGO Hub Pairing Requirement**
   - The LEGO Technic Move Hub REQUIRES pairing with `bond=True`
   - Without pairing, the hub will connect but ignore ALL commands
   - This creates an authenticated encrypted link required by the hub
   - Must be done after connection but before sending commands
   ```python
   await connection.pair(bond=True)  # CRITICAL for LEGO hub
   ```

3. **Xbox Controller Pairing Requirement**
   - The Xbox controller REQUIRES pairing to exit pairing mode
   - Without pairing, controller stays in pairing mode (rapid blinking)
   - PC will detect controller as available for pairing after ESP32 disconnect
   - Must be done after connection but before reading Report Map
   ```python
   await connection.pair(bond=True)  # CRITICAL for Xbox controller
   ```

4. **Xbox Controller Report Map Initialization**
   - The Xbox controller REQUIRES reading the HID Report Map (0x2A4B) before it will send input data
   - This is an undocumented requirement discovered through systematic testing
   - Without this step, the controller will NOT send any HID notifications
   - Must be done AFTER pairing but BEFORE subscribing to notifications
   ```python
   # CRITICAL: Read Report Map to initialize controller
   report_map_char = await hid_service.characteristic(bluetooth.UUID(0x2A4B))
   report_map = await report_map_char.read()
   ```

5. **Event-Driven Xbox Controller Input**
   - The Xbox controller uses event-driven notifications
   - Input reports are ONLY sent when controller state changes
   - No periodic "heartbeat" or constant stream of data
   - Applications must use `characteristic.notified()` to wait for events
   - This is normal HID behavior and reduces BLE traffic

### 6.3 MicroPython Constraints
- **Library Availability:** Limited to MicroPython-compatible libraries
- **Memory Management:** Manual garbage collection may be required
- **BLE Stack:** aioble library limitations vs. desktop Bleak
- **Float Performance:** Limited FPU support on ESP32-S3
- **File System:** Limited flash storage for config/logs

### 6.4 Safety Requirements
- **Battery Protection:** Monitor voltage, prevent over-discharge
- **Thermal Management:** Monitor MCU temperature
- **Failsafe Mode:** Stop motors if connection lost
- **Emergency Stop:** Physical button to immediately halt operation

---

## 7. Testing Strategy

### 7.1 Unit Testing
- Individual module testing (each .py file)
- Mock BLE devices for isolated testing
- Configuration manager persistence tests
- Input translation validation

### 7.2 Integration Testing
- Dual BLE connection stability
- End-to-end input to motor command flow
- Display and UI interaction
- Configuration save/load cycles

### 7.3 Performance Testing
- Latency measurements (input to command)
- Memory usage profiling
- Battery life testing
- Connection range testing
- Stress testing (extended operation)

### 7.4 User Acceptance Testing
- Real-world driving scenarios
- UI usability testing
- Battery life validation
- Edge case handling (out of range, low battery, etc.)

---

## 8. Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Xbox BLE protocol incompatibility | High | Medium | Research protocol, use USB sniffer if needed |
| Dual BLE connection instability | High | Medium | Implement robust reconnection, test extensively |
| Memory limitations | Medium | Low | Profile memory usage, optimize early |
| Battery life insufficient | Medium | Low | Implement aggressive power saving |
| Control latency too high | High | Low | Optimize async loops, minimize processing |

---

## 9. Future Enhancements (Post-V1)

- **WiFi Telemetry:** Stream telemetry data to mobile app
- **Multiple Profiles:** Save different control configurations
- **Button Remapping:** User-customizable button assignments
- **Vibration Feedback:** Send haptic feedback to controller
- **OTA Updates:** Over-the-air firmware updates via WiFi
- **Multi-Vehicle Support:** Connect to different LEGO models
- **Data Logging:** Log sessions for analysis

---

## 10. Development Tools and Environment

### 10.1 Development Environment
- **IDE:** VSCode with Pymakr or MPRemote extension
- **Python Version:** MicroPython v1.20+
- **Flash Tool:** esptool.py
- **Serial Monitor:** mpremote, screen, or PuTTY

### 10.2 Required Libraries (MicroPython)
- `aioble` - Async BLE library
- `asyncio` - Async/await support
- `ssd1306` - OLED display driver
- `machine` - Hardware interfaces
- `json` - Configuration serialization

### 10.3 Development Hardware
- XIAO ESP32-S3 development board
- USB-C cable for programming
- Xbox One controller (BLE version)
- LEGO Technic Move Hub (set 42176)
- SSD1306 OLED display module
- Breadboard and jumper wires for prototyping
- LiPo battery (1000mAh)

---

## 11. File Structure

```
esp32-xbox-lego-rc-upython/
├── README.md                    # Project overview and setup
├── DESIGN_SPEC.md              # This document
├── requirements.txt            # MicroPython library dependencies
├── docs/
│   ├── hardware_setup.md       # Wiring diagrams and assembly
│   ├── api_reference.md        # API documentation
│   ├── ble_protocol.md         # BLE protocol details
│   └── troubleshooting.md      # Common issues and solutions
├── src/
│   ├── main.py                 # Main application entry point
│   ├── ble_manager.py          # BLE connection management
│   ├── xbox_client.py          # Xbox controller BLE client
│   ├── lego_client.py          # LEGO hub BLE client
│   ├── input_translator.py     # Input to command translation
│   ├── display_manager.py      # Display driver and rendering
│   ├── ui_framework.py         # UI screens and navigation
│   ├── config_manager.py       # Configuration management
│   ├── power_manager.py        # Power and battery management
│   └── utils/
│       ├── ble_utils.py        # BLE helper functions
│       ├── math_utils.py       # Math/curve functions
│       └── constants.py        # Constants and enums
├── testing/
│   ├── ble_scan.py             # BLE scanning utility
│   ├── test_xbox_client.py     # Xbox client tests
│   ├── test_lego_client.py     # LEGO client tests
│   ├── test_input_translator.py # Input translation tests
│   └── test_dual_connection.py # Dual connection tests
├── reference/
│   └── LEGO Technic 42176 XBOX RC.py  # Desktop reference implementation
└── tools/
    ├── deploy.py               # Deploy code to ESP32
    ├── flash_firmware.sh       # Flash MicroPython firmware
    └── config_generator.py     # Generate default config
```

---

## 12. References

- **ESP32-S3 Datasheet:** https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf
- **MicroPython Documentation:** https://docs.micropython.org/
- **aioble Documentation:** https://github.com/micropython/micropython-lib/tree/master/micropython/bluetooth/aioble
- **Xbox Controller BLE Protocol:** TBD (requires reverse engineering)
- **LEGO Technic Hub Protocol:** Reference implementation included

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-10-31 | Claude | Initial design specification |
| 1.1 | 2025-10-31 | Claude | Added Phase 1 critical discoveries, updated BLE requirements with validated findings, documented Xbox Report Map requirement, documented pairing requirements for both devices, updated Phase 1 status to complete |
| 1.2 | 2025-11-03 | Claude | Updated Phase 2 status to complete, corrected test counts (5 LEGO, 8 Xbox, 7 BLE manager, 11 input translator), updated control mappings to match implementation, removed incomplete features from documentation |
