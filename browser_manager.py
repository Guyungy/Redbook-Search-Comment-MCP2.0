"""浏览器管理模块 - 处理浏览器初始化、登录和状态管理"""

import asyncio
import os
import shutil
import tempfile
from playwright.async_api import async_playwright
from config import (
    BROWSER_DATA_DIR, TEMP_PLAYWRIGHT_DIR, PLAYWRIGHT_BROWSERS_DIR,
    browser_context, main_page, is_logged_in
)
import config

async def ensure_browser():
    """确保浏览器已启动并登录"""
    global browser_context, main_page, is_logged_in
    
    if browser_context is None:
        # 强制设置当前进程的环境变量
        # 清理可能存在的临时文件
        try:
            temp_dirs = [TEMP_PLAYWRIGHT_DIR, os.path.join(os.environ.get('TEMP', ''), 'playwright-artifacts*')]
            for temp_pattern in temp_dirs:
                if '*' in temp_pattern:
                    import glob
                    for path in glob.glob(temp_pattern):
                        if os.path.exists(path):
                            shutil.rmtree(path, ignore_errors=True)
                elif os.path.exists(temp_pattern):
                    shutil.rmtree(temp_pattern, ignore_errors=True)
        except Exception as e:
            print(f"清理临时文件时出错: {e}")
        
        # 重新创建临时目录
        os.makedirs(TEMP_PLAYWRIGHT_DIR, exist_ok=True)
        
        # 启动Playwright
        playwright = await async_playwright().start()
        
        # 启动浏览器，使用持久化上下文
        browser_context = await playwright.chromium.launch_persistent_context(
            user_data_dir=BROWSER_DATA_DIR,
            headless=False,
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                f'--user-data-dir={BROWSER_DATA_DIR}',
                f'--disk-cache-dir={TEMP_PLAYWRIGHT_DIR}'
            ],
            viewport={'width': 1280, 'height': 720}
        )
        
        # 创建主页面
        main_page = await browser_context.new_page()
        
        # 更新全局变量
        config.browser_context = browser_context
        config.main_page = main_page
    
    # 检查登录状态
    login_status = await _check_login_status()
    return login_status

async def _check_login_status():
    """检查当前登录状态"""
    global is_logged_in, main_page
    
    if not main_page:
        return False
    
    try:
        # 访问小红书首页检查登录状态
        await main_page.goto("https://www.xiaohongshu.com", timeout=30000)
        await asyncio.sleep(3)
        
        # 检查是否存在登录按钮
        login_elements = await main_page.query_selector_all('text="登录"')
        
        if login_elements:
            print("检测到需要登录")
            is_logged_in = False
            config.is_logged_in = False
            return False
        else:
            print("检测到已登录状态")
            is_logged_in = True
            config.is_logged_in = True
            return True
            
    except Exception as e:
        print(f"检查登录状态时出错: {str(e)}")
        is_logged_in = False
        config.is_logged_in = False
        return False

async def login() -> str:
    """登录小红书账号"""
    global is_logged_in, main_page, browser_context
    
    try:
        print("🔍 检查浏览器状态...")
        
        # 确保浏览器已启动
        browser_status = await ensure_browser()
        if not main_page:
            return "❌ 浏览器初始化失败，请重试"
        
        print("🌐 正在访问小红书登录页面...")
        
        # 访问小红书登录页面
        await main_page.goto("https://www.xiaohongshu.com", timeout=60000)
        await asyncio.sleep(3)
        
        # 检查是否已经登录
        login_elements = await main_page.query_selector_all('text="登录"')
        
        if not login_elements:
            print("✅ 检测到已登录状态")
            is_logged_in = True
            config.is_logged_in = True
            return "✅ 检测到已登录状态"
        
        print("🔑 需要登录，正在准备登录界面...")
        
        # 点击登录按钮
        try:
            login_button = await main_page.query_selector('text="登录"')
            if login_button:
                await login_button.click()
                await asyncio.sleep(2)
                print("✅ 已点击登录按钮")
        except Exception as e:
            print(f"点击登录按钮时出错: {str(e)}")
        
        print("📱 请在浏览器中完成登录操作（扫码或其他方式）")
        print("⏳ 等待登录完成，最多等待5分钟...")
        
        # 等待登录完成（最多5分钟）
        login_success = False
        for i in range(300):  # 5分钟 = 300秒
            try:
                # 检查是否还有登录按钮
                login_elements = await main_page.query_selector_all('text="登录"')
                if not login_elements:
                    login_success = True
                    break
                
                await asyncio.sleep(1)
                
                # 每30秒提示一次
                if i % 30 == 0 and i > 0:
                    remaining_time = (300 - i) // 60
                    print(f"⏳ 仍在等待登录，剩余时间约 {remaining_time} 分钟...")
                    
            except Exception as e:
                print(f"检查登录状态时出错: {str(e)}")
                await asyncio.sleep(1)
        
        if login_success:
            is_logged_in = True
            config.is_logged_in = True
            print("✅ 登录成功！")
            return "✅ 登录成功！登录状态已保存，下次使用时无需重新登录。"
        else:
            print("⏰ 登录超时")
            return "⏰ 登录超时，请重试。如果问题持续存在，请检查网络连接或尝试重启浏览器。"
            
    except Exception as e:
        print(f"❌ 登录过程中出错: {str(e)}")
        return f"❌ 登录失败: {str(e)}。请重试或检查网络连接。"

async def reset_login() -> str:
    """重置登录状态，强制重新登录
    
    当遇到登录相关问题时，可以使用此功能清除登录状态，
    然后重新调用login()函数进行登录。
    """
    global is_logged_in, browser_context, main_page
    
    try:
        print("🔄 正在重置登录状态...")
        
        # 重置登录标志
        is_logged_in = False
        config.is_logged_in = False
        
        # 如果浏览器上下文存在，关闭它
        if browser_context:
            try:
                await browser_context.close()
                print("🔒 已关闭浏览器上下文")
            except Exception as e:
                print(f"关闭浏览器上下文时出错: {str(e)}")
        
        # 重置全局变量
        browser_context = None
        main_page = None
        config.browser_context = None
        config.main_page = None
        
        print("✅ 登录状态已重置")
        return "✅ 登录状态已重置。请重新调用login()函数进行登录。"
        
    except Exception as e:
        print(f"❌ 重置登录状态时出错: {str(e)}")
        return f"❌ 重置失败: {str(e)}"