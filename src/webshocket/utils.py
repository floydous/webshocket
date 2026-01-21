import os
import time

from itertools import count

_ID_Counter = count(1)
_ID_Prefix = f"{os.getpid():x}{int(time.time()) & 0xFFFF:x}"


def generate_uuid() -> str:
    # Fastest method to generate a unique ID
    # itertools.count + hex() -> 6,553,260 IDs/sec
    # original uuid.uuid4() -> 561,011 IDs/sec

    return _ID_Prefix + hex(next(_ID_Counter))[2:]


def parse_duration(duration: str) -> float:
    if not duration:
        raise ValueError("Duration cannot be empty.")

    multipliers = {
        "s": 1,
        "h": 3600,
        "m": 60,
        "d": 86400,
    }

    if duration[-1] not in multipliers:
        validKeys = ", ".join(multipliers.keys())
        raise ValueError(f"Invalid duration unit. Expected one of {validKeys} (e.g '10s', '5m', '1h', '2d')")

    return float(duration[:-1]) * multipliers[duration[-1]]
