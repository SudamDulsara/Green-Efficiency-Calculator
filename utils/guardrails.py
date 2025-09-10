def clamp(v, lo, hi):
    try:
        v = float(v)
    except Exception:
        return lo
    return max(lo, min(hi, v))

def clamp_hours(x): return clamp(x, 0, 24)
def clamp_watts(x): return clamp(x, 0, 10000)
def clamp_count(x): return int(clamp(x, 0, 1000))
def clamp_kwh(x): return clamp(x, 0, 1e7)
