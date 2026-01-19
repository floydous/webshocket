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
