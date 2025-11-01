"""
Constants and enumerations for ESP32 Xbox LEGO RC Controller
"""

# LEGO Technic Move Hub BLE Protocol
LEGO_SERVICE_UUID = "00001623-1212-EFDE-1623-785FEABCD123"
LEGO_CHARACTERISTIC_UUID = "00001624-1212-EFDE-1623-785FEABCD123"

# LEGO Motor Port IDs
MOTOR_PORT_A = 0x00
MOTOR_PORT_B = 0x01
MOTOR_PORT_C = 0x02
MOTOR_PORT_D = 0x03
MOTOR_PORT_AB = 0x32  # Combined ports A+B
MOTOR_PORT_CD = 0x33  # Combined ports C+D
MOTOR_PORT_ALL = 0x36  # All motors (drive system)

# LEGO Command Types
CMD_MOTOR_START_POWER = 0x81
CMD_MOTOR_GOTO_ABS_POS = 0x0d
CMD_MOTOR_START_SPEED = 0x07

# Light States
LIGHTS_OFF = 0x00
LIGHTS_ON = 0x01
LIGHTS_BOTH_ON = 0x02

# Xbox Controller BLE UUIDs (to be determined during implementation)
# These will need to be discovered by analyzing the controller
XBOX_SERVICE_UUID = None  # TBD
XBOX_CHARACTERISTIC_UUID = None  # TBD

# Control Constants
DEFAULT_DEAD_ZONE = 0.03  # 3% dead zone
MAX_SPEED = 100
MAX_STEERING_ANGLE = 100

# Display Constants
DISPLAY_WIDTH = 128
DISPLAY_HEIGHT = 64
DISPLAY_I2C_ADDR = 0x3C

# Connection Constants
BLE_SCAN_DURATION_MS = 5000
BLE_CONNECT_TIMEOUT_MS = 10000
BLE_RECONNECT_DELAY_MS = 5000
MAX_RECONNECT_ATTEMPTS = 3

# Battery Thresholds (for 3.7V LiPo)
BATTERY_MIN_VOLTAGE = 3.3  # Cutoff voltage
BATTERY_MAX_VOLTAGE = 4.2  # Fully charged
BATTERY_LOW_THRESHOLD = 3.5  # Low battery warning

# Device Name Patterns (for scanning)
XBOX_NAME_PATTERN = "xbox"
LEGO_NAME_PATTERN = "technic move"

# Control Modes
class ControlMode:
    NORMAL = "normal"
    TURBO = "turbo"
    SLOW = "slow"

# UI Screens
class Screen:
    STATUS = "status"
    CONNECTION = "connection"
    SETTINGS = "settings"
    CALIBRATION = "calibration"
    ABOUT = "about"

# Button Mappings (logical buttons, not physical pins)
class Button:
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    SELECT = "select"
    BACK = "back"

# System States
class SystemState:
    STARTUP = "startup"
    SCANNING = "scanning"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RUNNING = "running"
    ERROR = "error"
    SHUTDOWN = "shutdown"
