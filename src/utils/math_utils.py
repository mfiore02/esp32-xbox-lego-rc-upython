"""
Math utilities for input processing and control curves
"""


def apply_dead_zone(value: float, dead_zone: float = 0.03) -> float:
    """
    Apply dead zone to an input value.

    Args:
        value: Input value (typically -1.0 to 1.0)
        dead_zone: Dead zone threshold (0.0 to 1.0)

    Returns:
        Value with dead zone applied, scaled appropriately
    """
    if abs(value) < dead_zone:
        return 0.0

    # Scale the value to remove the dead zone gap
    if value > 0:
        return (value - dead_zone) / (1.0 - dead_zone)
    else:
        return (value + dead_zone) / (1.0 - dead_zone)


def apply_curve(value: float, curve_factor: float = 1.0) -> float:
    """
    Apply a power curve to an input value for finer control.

    Args:
        value: Input value (-1.0 to 1.0)
        curve_factor: Curve exponent (1.0 = linear, >1.0 = exponential, <1.0 = logarithmic)

    Returns:
        Value with curve applied
    """
    if curve_factor == 1.0:
        return value

    sign = 1 if value >= 0 else -1
    return sign * (abs(value) ** curve_factor)


def clamp(value: float, min_val: float, max_val: float) -> float:
    """
    Clamp a value between min and max.

    Args:
        value: Value to clamp
        min_val: Minimum value
        max_val: Maximum value

    Returns:
        Clamped value
    """
    return max(min_val, min(max_val, value))


def map_range(value: float, in_min: float, in_max: float, out_min: float, out_max: float) -> float:
    """
    Map a value from one range to another.

    Args:
        value: Input value
        in_min: Input range minimum
        in_max: Input range maximum
        out_min: Output range minimum
        out_max: Output range maximum

    Returns:
        Mapped value
    """
    return (value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


def float_to_int8(value: float, scale: int = 100) -> int:
    """
    Convert a float (-1.0 to 1.0) to signed int8 (-scale to scale).

    Args:
        value: Float value (-1.0 to 1.0)
        scale: Maximum output value (default 100)

    Returns:
        Integer in range -scale to scale
    """
    value = clamp(value, -1.0, 1.0)
    return int(value * scale)


def normalize_stick_input(raw_value: int, center: int = 128, max_val: int = 255) -> float:
    """
    Normalize a joystick raw value (0-255) to -1.0 to 1.0.

    Args:
        raw_value: Raw joystick value
        center: Center/neutral value
        max_val: Maximum value

    Returns:
        Normalized value (-1.0 to 1.0)
    """
    if raw_value >= center:
        # Positive range
        return (raw_value - center) / (max_val - center)
    else:
        # Negative range
        return (raw_value - center) / center
