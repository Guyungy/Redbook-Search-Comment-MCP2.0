"""配置文件 - 全局变量和环境设置"""

import os
import subprocess
from datetime import datetime

# 设置环境变量强制Playwright使用英文路径的临时目录（必须在导入playwright之前设置）
os.environ['TMPDIR'] = 'C:\\temp_playwright'
os.environ['TMP'] = 'C:\\temp_playwright'
os.environ['TEMP'] = 'C:\\temp_playwright'
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = 'C:\\playwright_browsers'

# 设置Windows系统环境变量（用户级别）
try:
    subprocess.run(['setx', 'TEMP', 'C:\\temp_playwright'], check=False, capture_output=True)
    subprocess.run(['setx', 'TMP', 'C:\\temp_playwright'], check=False, capture_output=True)
except Exception:
    pass  # 忽略设置失败

# 全局变量 - 使用英文绝对路径避免中文路径权限问题
BROWSER_DATA_DIR = "C:\\browser_data"
DATA_DIR = "C:\\redbook_data"
TEMP_PLAYWRIGHT_DIR = "C:\\temp_playwright"
PLAYWRIGHT_BROWSERS_DIR = "C:\\playwright_browsers"
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

# 确保目录存在
os.makedirs(BROWSER_DATA_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(TEMP_PLAYWRIGHT_DIR, exist_ok=True)
os.makedirs(PLAYWRIGHT_BROWSERS_DIR, exist_ok=True)

# 用于存储浏览器上下文，以便在不同方法之间共享
browser_context = None
main_page = None
is_logged_in = False

def process_url(url: str) -> str:
    """处理URL，确保格式正确并保留所有参数
    
    Args:
        url: 原始URL
    
    Returns:
        str: 处理后的URL
    """
    processed_url = url.strip()
    
    # 移除可能的@符号前缀
    if processed_url.startswith('@'):
        processed_url = processed_url[1:]
    
    # 确保URL使用https协议
    if processed_url.startswith('http://'):
        processed_url = 'https://' + processed_url[7:]
    elif not processed_url.startswith('https://'):
        processed_url = 'https://' + processed_url
        
    # 如果URL不包含www.xiaohongshu.com，则添加它
    if 'xiaohongshu.com' in processed_url and 'www.xiaohongshu.com' not in processed_url:
        processed_url = processed_url.replace('xiaohongshu.com', 'www.xiaohongshu.com')
    
    return processed_url