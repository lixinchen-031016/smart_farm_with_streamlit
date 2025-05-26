import logging

# 配置日志记录器
logging.basicConfig(
    filename='operation_log.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'  # 统一时间格式便于解析
)

def log_operation(user, action, details):
    """记录操作日志"""
    logging.info(f"User: {user}, Action: {action}, Details: {details}")
