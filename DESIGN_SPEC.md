# ESP32 Xbox LEGO RC Controller - Design Specification

**Project Name:** ESP32 Xbox LEGO RC Controller
**Target Platform:** XIAO ESP32-S3 with MicroPython
**Version:** 1.0
**Last Updated:** 2025-10-31

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
async def read_inputs() -> ControllerState
def get_left_stick() -> (float, float)
def get_right_stick() -> (float, float)
def get_triggers() -> (float, float)
def get_buttons() -> dict
```

**Data Structure:**
```python
class ControllerState:
    left_stick_x: float      # -1.0 to 1.0
    left_stick_y: float      # -1.0 to 1.0
    right_stick_x: float     # -1.0 to 1.0
    right_stick_y: float     # -1.0 to 1.0
    left_trigger: float      # 0.0 to 1.0
    right_trigger: float     # 0.0 to 1.0
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
async def connect(address: str) -> bool
async def drive(speed: int, angle: int, lights: int)
async def motor_start_power(motor_id: int, power: int)
async def motor_stop(motor_id: int, brake: bool)
async def change_led_color(r: int, g: int, b: int)
async def calibrate_steering()
```

**BLE Protocol Details:**
- Service UUID: `00001623-1212-EFDE-1623-785FEABCD123`
- Characteristic UUID: `00001624-1212-EFDE-1623-785FEABCD123`
- Command Format (Drive):
  ```
  [0x0d, 0x00, 0x81, 0x36, 0x11, 0x51, 0x00, 0x03, 0x00, speed, angle, lights, 0x00]
  ```

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
- Left Stick X → Steering angle
- Right Stick Y → Throttle (forward/reverse)
- Left/Right Triggers → Brake
- Y Button → Toggle lights
- Right Bumper → Hard brake
- A Button → Confirm/Select
- B Button → Cancel/Back

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

### Phase 1: Core BLE Connectivity (Week 1-2)
**Objectives:**
- Port LEGO hub connection to MicroPython/aioble
- Implement Xbox controller BLE connection
- Test dual simultaneous connections
- Verify command transmission to LEGO hub

**Deliverables:**
- `lego_client.py` - Working LEGO hub connection and motor control
- `xbox_client.py` - Working Xbox controller connection and input reading
- `ble_manager.py` - Dual connection management
- Test scripts for individual components

**Success Criteria:**
- Successfully connect to both devices simultaneously
- Send motor commands to LEGO hub
- Receive input data from Xbox controller
- Maintain stable connections for 10+ minutes

### Phase 2: Control Loop Implementation (Week 3)
**Objectives:**
- Implement input translation logic
- Create main control loop
- Test basic drive/steer/lights functionality
- Optimize latency and responsiveness

**Deliverables:**
- `input_translator.py` - Controller to vehicle command mapping
- `main.py` - Main application loop
- Performance testing results

**Success Criteria:**
- Control latency < 50ms
- Smooth steering and throttle response
- All basic controls working (forward, reverse, steer, lights)
- No connection drops during operation

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
- Add reconnection logic
- Create calibration routines
- Add advanced control modes
- Comprehensive testing

**Deliverables:**
- `power_manager.py` - Battery monitoring and power saving
- Enhanced error handling throughout
- User documentation
- Testing suite

**Success Criteria:**
- Battery monitoring working
- Auto-reconnect on disconnect
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
