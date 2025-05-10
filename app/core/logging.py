import logging
import os
from pathlib import Path

# Định nghĩa custom logging level APP_INFO
APP_INFO = 25  # Giữa INFO (20) và WARNING (30)
logging.addLevelName(APP_INFO, 'APP_INFO')

# Thêm method app_info cho logger
def app_info(self, message, *args, **kwargs):
    if self.isEnabledFor(APP_INFO):
        self._log(APP_INFO, message, args, **kwargs)

# Thêm method app_info vào Logger class
logging.Logger.app_info = app_info

def setup_logging(log_file: str = "logs/app.log", level=APP_INFO):
    """
    Cấu hình logging cho ứng dụng
    
    Args:
        log_file: Đường dẫn file log
        level: Level logging mặc định
    """
    # Đảm bảo thư mục logs tồn tại
    log_dir = os.path.dirname(log_file)
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

def get_logger(name: str):
    """
    Lấy logger với tên xác định
    
    Args:
        name: Tên của logger
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)

# Khởi tạo logger mặc định
setup_logging()
logger = get_logger("app") 