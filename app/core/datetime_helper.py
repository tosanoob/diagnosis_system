"""
Helper module để xử lý vấn đề datetime và timezone trong ứng dụng
"""
from datetime import datetime, timezone

def now_utc():
    """
    Trả về thời gian hiện tại ở timezone UTC
    """
    return datetime.now(timezone.utc)

def get_timezone_utc():
    """
    Trả về timezone UTC (tương thích với mọi phiên bản Python)
    """
    return timezone.utc