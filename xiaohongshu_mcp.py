from typing import Any, List, Dict, Optional
import asyncio
import json
import os
import pandas as pd
from datetime import datetime
from playwright.async_api import async_playwright
from fastmcp import FastMCP

# 设置环境变量强制Playwright使用英文路径的临时目录（必须在导入playwright之前设置）
import sys
import subprocess

# 强制设置系统级环境变量
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

# 初始化 FastMCP 服务器
mcp = FastMCP("xiaohongshu_scraper")

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

async def ensure_browser():
    """确保浏览器已启动并登录"""
    global browser_context, main_page, is_logged_in
    
    if browser_context is None:
        # 强制设置当前进程的环境变量
        import tempfile
        import shutil
        
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
        
        # 强制修改当前进程环境变量
        os.environ['TMPDIR'] = TEMP_PLAYWRIGHT_DIR
        os.environ['TMP'] = TEMP_PLAYWRIGHT_DIR
        os.environ['TEMP'] = TEMP_PLAYWRIGHT_DIR
        os.environ['PLAYWRIGHT_BROWSERS_PATH'] = PLAYWRIGHT_BROWSERS_DIR
        
        # 设置tempfile模块的临时目录
        tempfile.tempdir = TEMP_PLAYWRIGHT_DIR
        
        # 启动浏览器
        playwright_instance = await async_playwright().start()
        
        # 使用持久化上下文来保存用户状态
        browser_context = await playwright_instance.chromium.launch_persistent_context(
            user_data_dir=BROWSER_DATA_DIR,
            headless=False,  # 非隐藏模式，方便用户登录
            viewport={"width": 1280, "height": 800},
            timeout=60000,
            env={
                **os.environ,
                'TMPDIR': TEMP_PLAYWRIGHT_DIR,
                'TMP': TEMP_PLAYWRIGHT_DIR,
                'TEMP': TEMP_PLAYWRIGHT_DIR,
                'PLAYWRIGHT_BROWSERS_PATH': PLAYWRIGHT_BROWSERS_DIR
            }
        )
        
        # 创建一个新页面
        if browser_context.pages:
            main_page = browser_context.pages[0]
        else:
            main_page = await browser_context.new_page()
        
        # 设置页面级别的超时时间
        main_page.set_default_timeout(60000)
    
    # 检查登录状态
    if not is_logged_in:
        # 访问小红书首页
        if main_page:  # 添加空检查
            await main_page.goto("https://www.xiaohongshu.com", timeout=60000)
            await asyncio.sleep(3)
            
            # 检查是否已登录
            login_elements = await main_page.query_selector_all('text="登录"') if main_page else []  # 添加空检查
            if login_elements:
                return False  # 需要登录
            else:
                is_logged_in = True
                return True  # 已登录
        else:
            return False  # main_page为None，需要重新初始化
    
    return True

@mcp.tool()
async def login() -> str:
    """登录小红书账号"""
    global is_logged_in
    
    await ensure_browser()
    
    if is_logged_in:
        return "已登录小红书账号"
    
    # 访问小红书登录页面
    if not main_page:  # 添加空检查
        return "浏览器初始化失败，请重试"
        
    await main_page.goto("https://www.xiaohongshu.com", timeout=60000)
    await asyncio.sleep(3)
    
    # 查找登录按钮并点击
    login_elements = await main_page.query_selector_all('text="登录"') if main_page else []  # 添加空检查
    if login_elements:
        await login_elements[0].click()
        
        # 提示用户手动登录
        message = "请在打开的浏览器窗口中完成登录操作。登录成功后，系统将自动继续。"
        
        # 等待用户登录成功
        max_wait_time = 180  # 等待3分钟
        wait_interval = 5
        waited_time = 0
        
        while waited_time < max_wait_time:
            # 检查是否已登录成功
            if not main_page:  # 添加空检查
                return "浏览器初始化失败，请重试"
                
            still_login = await main_page.query_selector_all('text="登录"')
            if not still_login:
                is_logged_in = True
                await asyncio.sleep(2)  # 等待页面加载
                return "登录成功！"
            
            # 继续等待
            await asyncio.sleep(wait_interval)
            waited_time += wait_interval
        
        return "登录等待超时。请重试或手动登录后再使用其他功能。"
    else:
        is_logged_in = True
        return "已登录小红书账号"

@mcp.tool()
async def search_notes(keywords: str, limit: int = 5) -> str:
    """根据关键词搜索笔记（基础搜索）
    
    Args:
        keywords: 搜索关键词
        limit: 返回结果数量限制
    """
    return await _basic_search(keywords, limit)

@mcp.tool()
async def smart_search_notes(task_description: str, limit: int = 10) -> str:
    """智能搜索笔记 - AI Agent式深度搜索
    
    这是一个智能搜索系统，能够：
    1. 分析用户任务意图
    2. 自动生成多个搜索策略
    3. 执行多轮搜索并优化关键词
    4. 智能筛选和排序结果
    5. 提供搜索分析报告
    
    Args:
        task_description: 任务描述，例如：
                         "我想找一些关于护肤的笔记，特别是敏感肌护理方面的"
                         "帮我搜索最近流行的穿搭趋势，偏向日系风格"
                         "找一些关于AI工具使用的教程和经验分享"
        limit: 返回结果数量限制
    
    Returns:
        str: 包含搜索结果和分析报告的详细信息
    """
    return await _intelligent_search_agent(task_description, limit)

async def _basic_search(keywords: str, limit: int = 5) -> str:
    """基础搜索功能（原search_notes逻辑）"""
    login_status = await ensure_browser()
    if not login_status:
        return "请先登录小红书账号"
    
    if not main_page:  # 添加空检查
        return "浏览器初始化失败，请重试"
        
    # 构建搜索URL并访问
    search_url = f"https://www.xiaohongshu.com/search_result?keyword={keywords}"
    try:
        await main_page.goto(search_url, timeout=60000)
        await asyncio.sleep(5)  # 等待页面加载
        
        # 等待页面完全加载
        await asyncio.sleep(5)
        
        # 打印页面HTML用于调试
        page_html = await main_page.content()
        print(f"页面HTML片段: {page_html[10000:10500]}...")
        
        # 使用更精确的选择器获取帖子卡片
        print("尝试获取帖子卡片...")
        if not main_page:  # 添加空检查
            return "浏览器初始化失败，请重试"
            
        post_cards = await main_page.query_selector_all('section.note-item')
        print(f"找到 {len(post_cards)} 个帖子卡片")
        
        if not post_cards:
            # 尝试备用选择器
            if not main_page:  # 添加空检查
                return "浏览器初始化失败，请重试"
                
            post_cards = await main_page.query_selector_all('div[data-v-a264b01a]')
            print(f"使用备用选择器找到 {len(post_cards)} 个帖子卡片")
        
        post_links = []
        post_titles = []
        
        for card in post_cards:
            try:
                # 获取链接
                link_element = await card.query_selector('a[href*="/search_result/"]') if card else None  # 添加空检查
                if not link_element:
                    continue
                
                href = await link_element.get_attribute('href')
                if href and '/search_result/' in href:
                    # 构建完整URL
                    if href.startswith('/'):
                        full_url = f"https://www.xiaohongshu.com{href}"
                    else:
                        full_url = href
                        
                    post_links.append(full_url)
                    
                    # 尝试获取帖子标题
                    try:
                        # 打印卡片HTML用于调试
                        card_html = await card.inner_html() if card else ""  # 添加空检查
                        print(f"卡片HTML片段: {card_html[:200]}...")
                        
                        # 首先尝试获取卡片内的footer中的标题
                        title_element = await card.query_selector('div.footer a.title span') if card else None  # 添加空检查
                        if title_element:
                            title = await title_element.text_content() 
                            print(f"找到标题(方法1): {title}")
                        else:
                            # 尝试直接获取标题元素
                            title_element = await card.query_selector('a.title span') if card else None  # 添加空检查
                            if title_element:
                                title = await title_element.text_content()
                                print(f"找到标题(方法2): {title}")
                            else:
                                # 尝试获取任何可能的文本内容
                                text_elements = await card.query_selector_all('span') if card else []  # 添加空检查
                                potential_titles = []
                                for text_el in text_elements:
                                    text = await text_el.text_content() if text_el else ""  # 添加空检查
                                    if text and len(text.strip()) > 5:
                                        potential_titles.append(text.strip())
                                
                                if potential_titles:
                                    # 选择最长的文本作为标题
                                    title = max(potential_titles, key=len) if potential_titles else "未知标题"  # 添加空检查
                                    print(f"找到可能的标题(方法3): {title}")
                                else:
                                    # 尝试直接获取卡片中的所有文本
                                    if not card:  # 添加空检查
                                        title = "未知标题"
                                        print("卡片为空，使用默认值'未知标题'")
                                    else:
                                        all_text = await card.evaluate('el => Array.from(el.querySelectorAll("*")).map(node => node.textContent).filter(text => text && text.trim().length > 5)')
                                        if all_text and isinstance(all_text, list) and all_text:  # 使用布尔检查替代len
                                            # 选择最长的文本作为标题
                                            title = max(all_text, key=len)
                                            print(f"找到可能的标题(方法4): {title}")
                                        else:
                                            title = "未知标题"
                                            print("无法找到标题，使用默认值'未知标题'")
                        
                        # 如果获取到的标题为空，设为未知标题
                        if not title or (isinstance(title, str) and title.strip() == ""):  # 增加类型检查
                            title = "未知标题"
                            print("获取到的标题为空，使用默认值'未知标题'")
                    except Exception as e:
                        print(f"获取标题时出错: {str(e)}")
                        title = "未知标题"
                    
                    post_titles.append(title)
            except Exception as e:
                print(f"处理帖子卡片时出错: {str(e)}")
        
        # 去重
        unique_posts = []
        seen_urls = set()
        for url, title in zip(post_links, post_titles):
            if url not in seen_urls:
                seen_urls.add(url)
                unique_posts.append({"url": url, "title": title})
        
        # 限制返回数量
        unique_posts = unique_posts[:limit]
        
        # 格式化返回结果
        if unique_posts:
            result = "搜索结果：\n\n"
            for i, post in enumerate(unique_posts, 1):
                result += f"{i}. {post['title']}\n   链接: {post['url']}\n\n"
            
            return result
        else:
            return f"未找到与\"{keywords}\"相关的笔记"
    
    except Exception as e:
        return f"搜索笔记时出错: {str(e)}"

async def _intelligent_search_agent(task_description: str, limit: int = 10) -> str:
    """智能搜索代理 - 实现AI Agent式的深度搜索"""
    try:
        print(f"\n=== 智能搜索代理启动 ===")
        print(f"任务描述: {task_description}")
        print(f"目标结果数量: {limit}")
        
        # 第一步：任务意图分析
        search_strategy = await _analyze_search_intent(task_description)
        print(f"\n搜索策略分析完成:")
        print(f"- 主要领域: {search_strategy['domain']}")
        print(f"- 核心关键词: {search_strategy['core_keywords']}")
        print(f"- 扩展关键词: {search_strategy['extended_keywords']}")
        print(f"- 搜索优先级: {search_strategy['priority']}")
        
        # 第二步：多轮搜索执行
        all_results = []
        search_rounds = []
        
        # 执行核心关键词搜索
        for i, keyword_group in enumerate(search_strategy['search_queries'][:3]):
            print(f"\n--- 第{i+1}轮搜索 ---")
            print(f"搜索关键词: {keyword_group}")
            
            round_results = await _execute_search_round(keyword_group, min(limit, 8))
            search_rounds.append({
                'round': i+1,
                'keywords': keyword_group,
                'results_count': len(round_results),
                'results': round_results
            })
            all_results.extend(round_results)
            
            # 避免过于频繁的请求
            await asyncio.sleep(2)
        
        # 第三步：结果去重和智能筛选
        print(f"\n--- 结果处理阶段 ---")
        print(f"原始结果数量: {len(all_results)}")
        
        unique_results = await _deduplicate_results(all_results)
        print(f"去重后结果数量: {len(unique_results)}")
        
        # 第四步：智能排序和筛选
        scored_results = await _score_and_rank_results(unique_results, search_strategy, task_description)
        final_results = scored_results[:limit]
        print(f"最终筛选结果数量: {len(final_results)}")
        
        # 第五步：生成搜索报告
        report = await _generate_search_report(task_description, search_strategy, search_rounds, final_results)
        
        return report
        
    except Exception as e:
        return f"智能搜索时出错: {str(e)}"

async def _analyze_search_intent(task_description: str) -> dict:
    """分析搜索意图并生成搜索策略"""
    # 领域关键词映射
    domain_mapping = {
        "美妆": ["护肤", "化妆", "彩妆", "美容", "面膜", "精华", "粉底", "口红", "眼影", "敏感肌", "痘痘", "美白", "抗老"],
        "穿搭": ["穿搭", "搭配", "服装", "时尚", "风格", "日系", "韩系", "欧美", "复古", "简约", "甜美", "酷帅", "职场"],
        "美食": ["美食", "料理", "烹饪", "食谱", "甜品", "烘焙", "家常菜", "减脂餐", "健康饮食", "网红店"],
        "旅行": ["旅行", "旅游", "攻略", "景点", "民宿", "酒店", "机票", "签证", "自由行", "跟团"],
        "健身": ["健身", "运动", "瘦身", "减肥", "瑜伽", "跑步", "力量训练", "有氧", "塑形", "马甲线"],
        "数码": ["数码", "手机", "电脑", "相机", "耳机", "智能", "科技", "评测", "开箱"],
        "家居": ["家居", "装修", "家具", "设计", "收纳", "布置", "软装", "北欧", "简约", "温馨"],
        "AI": ["AI", "人工智能", "ChatGPT", "Claude", "大模型", "编程", "工具", "效率", "自动化"]
    }
    
    # 分析任务描述，识别领域和关键词
    detected_domain = "生活"
    core_keywords = []
    extended_keywords = []
    
    task_lower = task_description.lower()
    
    # 识别主要领域
    for domain, keywords in domain_mapping.items():
        for keyword in keywords:
            if keyword.lower() in task_lower:
                detected_domain = domain
                core_keywords.append(keyword)
                break
        if detected_domain != "生活":
            break
    
    # 如果识别到领域，添加相关扩展关键词
    if detected_domain in domain_mapping:
        extended_keywords = domain_mapping[detected_domain][:8]
    
    # 从任务描述中提取其他关键词
    import re
    # 提取中文词汇
    chinese_words = re.findall(r'[\u4e00-\u9fff]+', task_description)
    for word in chinese_words:
        if len(word) >= 2 and word not in core_keywords:
            core_keywords.append(word)
    
    # 生成搜索查询组合
    search_queries = []
    
    # 核心关键词组合
    if core_keywords:
        search_queries.append(" ".join(core_keywords[:3]))
    
    # 领域+核心词组合
    if detected_domain != "生活" and core_keywords:
        search_queries.append(f"{detected_domain} {core_keywords[0]}")
    
    # 扩展关键词组合
    for ext_keyword in extended_keywords[:3]:
        if core_keywords:
            search_queries.append(f"{ext_keyword} {core_keywords[0]}")
        else:
            search_queries.append(ext_keyword)
    
    return {
        'domain': detected_domain,
        'core_keywords': core_keywords[:5],
        'extended_keywords': extended_keywords,
        'search_queries': search_queries[:5],
        'priority': 'high' if len(core_keywords) > 2 else 'medium'
    }

async def _execute_search_round(keywords: str, limit: int) -> list:
    """执行单轮搜索"""
    try:
        result_str = await _basic_search(keywords, limit)
        
        # 解析搜索结果
        results = []
        if "搜索结果：" in result_str:
            lines = result_str.split('\n')
            current_item = {}
            
            for line in lines:
                line = line.strip()
                if line and line[0].isdigit() and '. ' in line:
                    # 保存上一个项目
                    if current_item:
                        results.append(current_item)
                    # 开始新项目
                    title = line.split('. ', 1)[1] if '. ' in line else line
                    current_item = {'title': title, 'url': '', 'keywords': keywords}
                elif line.startswith('链接: '):
                    if current_item:
                        current_item['url'] = line.replace('链接: ', '')
            
            # 添加最后一个项目
            if current_item:
                results.append(current_item)
        
        return results
        
    except Exception as e:
        print(f"搜索轮次执行出错: {str(e)}")
        return []

async def _deduplicate_results(results: list) -> list:
    """去重搜索结果"""
    seen_urls = set()
    unique_results = []
    
    for result in results:
        url = result.get('url', '')
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_results.append(result)
    
    return unique_results

async def _score_and_rank_results(results: list, strategy: dict, task_description: str) -> list:
    """对搜索结果进行评分和排序"""
    scored_results = []
    
    for result in results:
        score = 0
        title = result.get('title', '').lower()
        
        # 核心关键词匹配得分
        for keyword in strategy['core_keywords']:
            if keyword.lower() in title:
                score += 10
        
        # 领域关键词匹配得分
        domain_keywords = {
            "美妆": ["护肤", "化妆", "美容"],
            "穿搭": ["穿搭", "搭配", "时尚"],
            "美食": ["美食", "料理", "食谱"],
            "旅行": ["旅行", "攻略", "景点"],
            "健身": ["健身", "运动", "减肥"],
            "数码": ["数码", "科技", "评测"],
            "家居": ["家居", "装修", "设计"],
            "AI": ["AI", "工具", "效率"]
        }
        
        if strategy['domain'] in domain_keywords:
            for keyword in domain_keywords[strategy['domain']]:
                if keyword in title:
                    score += 5
        
        # 标题长度合理性得分
        title_len = len(result.get('title', ''))
        if 10 <= title_len <= 50:
            score += 3
        elif title_len > 50:
            score += 1
        
        # 添加随机因子避免结果过于固化
        import random
        score += random.uniform(0, 2)
        
        result['score'] = score
        scored_results.append(result)
    
    # 按得分排序
    return sorted(scored_results, key=lambda x: x['score'], reverse=True)

async def _generate_search_report(task_description: str, strategy: dict, search_rounds: list, final_results: list) -> str:
    """生成搜索分析报告"""
    report = f"""🤖 智能搜索分析报告

📋 任务描述: {task_description}

🎯 搜索策略分析:
• 识别领域: {strategy['domain']}
• 核心关键词: {', '.join(strategy['core_keywords'])}
• 搜索优先级: {strategy['priority']}

🔍 搜索执行过程:"""
    
    total_searched = 0
    for round_info in search_rounds:
        report += f"\n• 第{round_info['round']}轮: \"{round_info['keywords']}\" → {round_info['results_count']}个结果"
        total_searched += round_info['results_count']
    
    report += f"\n\n📊 搜索统计:\n• 总搜索结果: {total_searched}个\n• 去重后结果: {len(final_results)}个\n• 最终推荐: {len(final_results)}个\n\n🏆 推荐结果:\n\n"
    
    for i, result in enumerate(final_results, 1):
        score_stars = "⭐" * min(5, int(result.get('score', 0) // 3))
        report += f"{i}. {result['title']} {score_stars}\n   🔗 {result['url']}\n   📊 匹配度: {result.get('score', 0):.1f}分\n\n"
    
    if not final_results:
        report += "❌ 未找到符合条件的笔记，建议：\n• 尝试更通用的关键词\n• 检查关键词拼写\n• 扩大搜索范围\n"
    
    return report

@mcp.tool()
async def deep_search_and_analyze(task_description: str, analyze_content: bool = True, limit: int = 5) -> str:
    """深度搜索并分析 - 最高级的AI Agent搜索模式
    
    这是最智能的搜索模式，能够：
    1. 执行智能搜索获取相关笔记
    2. 自动分析每个笔记的详细内容
    3. 提取关键信息和趋势
    4. 生成深度分析报告
    5. 提供行动建议
    
    Args:
        task_description: 任务描述
        analyze_content: 是否分析笔记内容（耗时较长但信息更全面）
        limit: 分析的笔记数量限制
    
    Returns:
        str: 包含搜索结果、内容分析和趋势报告的综合信息
    """
    try:
        print(f"\n=== 深度搜索分析代理启动 ===")
        print(f"任务: {task_description}")
        print(f"内容分析: {'开启' if analyze_content else '关闭'}")
        print(f"分析数量: {limit}")
        
        # 第一步：执行智能搜索
        search_results = await _intelligent_search_agent(task_description, limit * 2)
        
        if "❌ 未找到符合条件的笔记" in search_results:
            return search_results
        
        # 从搜索结果中提取URL
        urls = await _extract_urls_from_search_results(search_results)
        selected_urls = urls[:limit]
        
        print(f"\n=== 开始深度内容分析 ===")
        print(f"将分析 {len(selected_urls)} 个笔记")
        
        # 第二步：内容分析（如果启用）
        analyzed_notes = []
        if analyze_content and selected_urls:
            for i, url in enumerate(selected_urls, 1):
                print(f"\n--- 分析第{i}个笔记 ---")
                print(f"URL: {url}")
                
                try:
                    note_analysis = await analyze_note(url)
                    if "error" not in note_analysis:
                        analyzed_notes.append(note_analysis)
                        print(f"✅ 分析完成: {note_analysis.get('标题', '未知标题')}")
                    else:
                        print(f"❌ 分析失败: {note_analysis.get('error', '未知错误')}")
                    
                    # 避免请求过于频繁
                    await asyncio.sleep(3)
                    
                except Exception as e:
                    print(f"❌ 分析笔记时出错: {str(e)}")
                    continue
        
        # 第三步：生成深度分析报告
        deep_report = await _generate_deep_analysis_report(
            task_description, search_results, analyzed_notes
        )
        
        return deep_report
        
    except Exception as e:
        return f"深度搜索分析时出错: {str(e)}"

async def _extract_urls_from_search_results(search_results: str) -> list:
    """从搜索结果中提取URL"""
    urls = []
    lines = search_results.split('\n')
    
    for line in lines:
        if '🔗 ' in line:
            url = line.split('🔗 ', 1)[1].strip()
            if url.startswith('http'):
                urls.append(url)
    
    return urls

async def _generate_deep_analysis_report(task_description: str, search_results: str, analyzed_notes: list) -> str:
    """生成深度分析报告"""
    report = f"""🧠 深度搜索分析报告

📋 分析任务: {task_description}

{search_results}

═══════════════════════════════════════

📊 内容深度分析:"""
    
    if not analyzed_notes:
        report += "\n\n⚠️ 未能获取到笔记内容进行深度分析"
        return report
    
    # 统计分析
    total_notes = len(analyzed_notes)
    domains = []
    all_keywords = []
    authors = []
    
    for note in analyzed_notes:
        if note.get('领域'):
            domains.extend(note['领域'])
        if note.get('关键词'):
            all_keywords.extend(note['关键词'])
        if note.get('作者'):
            authors.append(note['作者'])
    
    # 领域分布统计
    from collections import Counter
    domain_count = Counter(domains)
    keyword_count = Counter(all_keywords)
    
    report += f"\n\n📈 统计概览:\n• 分析笔记数量: {total_notes}个\n• 涉及领域: {len(domain_count)}个\n• 提取关键词: {len(keyword_count)}个\n• 涉及作者: {len(set(authors))}位"
    
    # 热门领域
    if domain_count:
        report += "\n\n🏷️ 热门领域分布:"
        for domain, count in domain_count.most_common(5):
            percentage = (count / len(domains)) * 100
            report += f"\n• {domain}: {count}次 ({percentage:.1f}%)"
    
    # 热门关键词
    if keyword_count:
        report += "\n\n🔥 热门关键词:"
        for keyword, count in keyword_count.most_common(10):
            report += f"\n• {keyword} ({count}次)"
    
    # 详细笔记分析
    report += "\n\n📝 详细笔记分析:\n"
    
    for i, note in enumerate(analyzed_notes, 1):
        report += f"\n{i}. 📄 {note.get('标题', '未知标题')}\n"
        report += f"   👤 作者: {note.get('作者', '未知')}\n"
        report += f"   🏷️ 领域: {', '.join(note.get('领域', []))}\n"
        
        content = note.get('内容', '')
        if content and content != '未能获取内容':
            # 显示内容摘要
            content_preview = content[:100] + '...' if len(content) > 100 else content
            report += f"   📖 内容摘要: {content_preview}\n"
        
        report += f"   🔗 链接: {note.get('url', '')}\n"
    
    # 趋势分析和建议
    report += "\n\n🎯 趋势分析与建议:\n"
    
    if domain_count:
        top_domain = domain_count.most_common(1)[0][0]
        report += f"• 主要关注领域是 '{top_domain}'，建议深入研究该领域的最新趋势\n"
    
    if keyword_count:
        top_keywords = [kw for kw, _ in keyword_count.most_common(3)]
        report += f"• 核心关键词包括: {', '.join(top_keywords)}，可作为内容创作的重点方向\n"
    
    if len(set(authors)) > 1:
        report += f"• 发现 {len(set(authors))} 位不同作者，建议关注他们的其他作品\n"
    
    # 内容质量评估
    quality_notes = [note for note in analyzed_notes if note.get('内容') and len(note.get('内容', '')) > 50]
    if quality_notes:
        quality_ratio = len(quality_notes) / total_notes * 100
        report += f"• 内容质量评估: {len(quality_notes)}/{total_notes} 个笔记有详细内容 ({quality_ratio:.1f}%)\n"
    
    report += "\n💡 行动建议:\n"
    report += "• 可以基于热门关键词创作相关内容\n"
    report += "• 关注高质量作者的更新动态\n"
    report += "• 结合趋势分析制定内容策略\n"
    report += "• 考虑在热门领域进行深度布局\n"
    
    return report

@mcp.tool()
async def get_note_content(url: str) -> str:
    """获取笔记内容
    
    Args:
        url: 笔记 URL
    """
    login_status = await ensure_browser()
    if not login_status:
        return "请先登录小红书账号"
    
    if not main_page:  # 添加空检查
        return "浏览器初始化失败，请重试"
        
    try:
        # 使用通用URL处理函数
        processed_url = process_url(url)
        print(f"处理后的URL: {processed_url}")
        
        # 访问帖子链接，保留完整参数
        await main_page.goto(processed_url, timeout=60000)
        await asyncio.sleep(10)  # 增加等待时间到10秒
        
        # 检查是否加载了错误页面
        if not main_page:  # 添加空检查
            return "浏览器初始化失败，请重试"
            
        error_page = await main_page.evaluate('''
            () => {
                // 检查常见的错误信息
                const errorTexts = [
                    "当前笔记暂时无法浏览",
                    "内容不存在",
                    "页面不存在",
                    "内容已被删除"
                ];
                
                for (const text of errorTexts) {
                    if (document.body.innerText.includes(text)) {
                        return {
                            isError: true,
                            errorText: text
                        };
                    }
                }
                
                return { isError: false };
            }
        ''')
        
        if error_page.get("isError", False):
            return f"无法获取笔记内容: {error_page.get('errorText', '未知错误')}\n请检查链接是否有效或尝试使用带有有效token的完整URL。"
        
        # 增强滚动操作以确保所有内容加载
        if not main_page:  # 添加空检查
            return "浏览器初始化失败，请重试"
            
        await main_page.evaluate('''
            () => {
                // 先滚动到页面底部
                window.scrollTo(0, document.body.scrollHeight);
                setTimeout(() => { 
                    // 然后滚动到中间
                    window.scrollTo(0, document.body.scrollHeight / 2); 
                }, 1000);
                setTimeout(() => { 
                    // 最后回到顶部
                    window.scrollTo(0, 0); 
                }, 2000);
            }
        ''')
        await asyncio.sleep(3)  # 等待滚动完成和内容加载
        
        # 打印页面结构片段用于分析
        try:
            print("打印页面结构片段用于分析")
            if not main_page:  # 添加空检查
                return "浏览器初始化失败，请重试"
                
            page_structure = await main_page.evaluate('''
                () => {
                    // 获取笔记内容区域
                    const noteContent = document.querySelector('.note-content');
                    const detailDesc = document.querySelector('#detail-desc');
                    const commentArea = document.querySelector('.comments-container, .comment-list');
                    
                    return {
                        hasNoteContent: !!noteContent,
                        hasDetailDesc: !!detailDesc,
                        hasCommentArea: !!commentArea,
                        noteContentHtml: noteContent ? noteContent.outerHTML.slice(0, 500) : null,
                        detailDescHtml: detailDesc ? detailDesc.outerHTML.slice(0, 500) : null,
                        commentAreaFirstChild: commentArea ? 
                            (commentArea.firstElementChild ? commentArea.firstElementChild.outerHTML.slice(0, 500) : null) : null,
                        pageTitle: document.title,
                        bodyText: document.body.innerText.slice(0, 500)
                    };
                }
            ''')
            print(f"页面结构分析: {json.dumps(page_structure, ensure_ascii=False, indent=2)}")
            
            # 再次检查内容是否可见
            if "当前笔记暂时无法浏览" in page_structure.get("bodyText", ""):
                return "无法获取笔记内容: 当前笔记暂时无法浏览\n请检查链接是否有效或尝试使用带有有效token的完整URL。"
        except Exception as e:
            print(f"打印页面结构时出错: {str(e)}")
        
        # 获取帖子内容
        post_content = {}
        
        # 获取帖子标题 - 方法1：使用id选择器
        try:
            print("尝试获取标题 - 方法1：使用id选择器")
            if not main_page:  # 添加空检查
                return "浏览器初始化失败，请重试"
                
            title_element = await main_page.query_selector('#detail-title')
            if title_element:
                title = await title_element.text_content()
                post_content["标题"] = title.strip() if title else "未知标题"
                print(f"方法1获取到标题: {post_content['标题']}")
            else:
                print("方法1未找到标题元素")
                post_content["标题"] = "未知标题"
        except Exception as e:
            print(f"方法1获取标题出错: {str(e)}")
            post_content["标题"] = "未知标题"
        
        # 获取帖子标题 - 方法2：使用class选择器
        if post_content["标题"] == "未知标题":
            try:
                print("尝试获取标题 - 方法2：使用class选择器")
                if not main_page:  # 添加空检查
                    return "浏览器初始化失败，请重试"
                    
                title_element = await main_page.query_selector('div.title')
                if title_element:
                    title = await title_element.text_content()
                    post_content["标题"] = title.strip() if title else "未知标题"
                    print(f"方法2获取到标题: {post_content['标题']}")
                else:
                    print("方法2未找到标题元素")
            except Exception as e:
                print(f"方法2获取标题出错: {str(e)}")
        
        # 获取帖子标题 - 方法3：使用JavaScript
        if post_content["标题"] == "未知标题":
            try:
                print("尝试获取标题 - 方法3：使用JavaScript")
                if not main_page:  # 添加空检查
                    return "浏览器初始化失败，请重试"
                    
                title = await main_page.evaluate('''
                    () => {
                        // 尝试多种可能的标题选择器
                        const selectors = [
                            '#detail-title',
                            'div.title',
                            'h1',
                            'div.note-content div.title'
                        ];
                        
                        for (const selector of selectors) {
                            const el = document.querySelector(selector);
                            if (el && el.textContent.trim()) {
                                return el.textContent.trim();
                            }
                        }
                        return null;
                    }
                ''')
                if title:
                    post_content["标题"] = title
                    print(f"方法3获取到标题: {post_content['标题']}")
                else:
                    print("方法3未找到标题元素")
            except Exception as e:
                print(f"方法3获取标题出错: {str(e)}")
        
        # 获取作者 - 方法1：使用username类选择器
        try:
            print("尝试获取作者 - 方法1：使用username类选择器")
            author_element = await main_page.query_selector('span.username')
            if author_element:
                author = await author_element.text_content()
                post_content["作者"] = author.strip() if author else "未知作者"
                print(f"方法1获取到作者: {post_content['作者']}")
            else:
                print("方法1未找到作者元素")
                post_content["作者"] = "未知作者"
        except Exception as e:
            print(f"方法1获取作者出错: {str(e)}")
            post_content["作者"] = "未知作者"
        
        # 获取作者 - 方法2：使用链接选择器
        if post_content["作者"] == "未知作者":
            try:
                print("尝试获取作者 - 方法2：使用链接选择器")
                author_element = await main_page.query_selector('a.name')
                if author_element:
                    author = await author_element.text_content()
                    post_content["作者"] = author.strip() if author else "未知作者"
                    print(f"方法2获取到作者: {post_content['作者']}")
                else:
                    print("方法2未找到作者元素")
            except Exception as e:
                print(f"方法2获取作者出错: {str(e)}")
        
        # 获取作者 - 方法3：使用JavaScript
        if post_content["作者"] == "未知作者":
            try:
                print("尝试获取作者 - 方法3：使用JavaScript")
                author = await main_page.evaluate('''
                    () => {
                        // 尝试多种可能的作者选择器
                        const selectors = [
                            'span.username',
                            'a.name',
                            '.author-wrapper .username',
                            '.info .name'
                        ];
                        
                        for (const selector of selectors) {
                            const el = document.querySelector(selector);
                            if (el && el.textContent.trim()) {
                                return el.textContent.trim();
                            }
                        }
                        return null;
                    }
                ''')
                if author:
                    post_content["作者"] = author
                    print(f"方法3获取到作者: {post_content['作者']}")
                else:
                    print("方法3未找到作者元素")
            except Exception as e:
                print(f"方法3获取作者出错: {str(e)}")
        
        # 获取发布时间 - 方法1：使用date类选择器
        try:
            print("尝试获取发布时间 - 方法1：使用date类选择器")
            time_element = await main_page.query_selector('span.date')
            if time_element:
                time_text = await time_element.text_content()
                post_content["发布时间"] = time_text.strip() if time_text else "未知"
                print(f"方法1获取到发布时间: {post_content['发布时间']}")
            else:
                print("方法1未找到发布时间元素")
                post_content["发布时间"] = "未知"
        except Exception as e:
            print(f"方法1获取发布时间出错: {str(e)}")
            post_content["发布时间"] = "未知"
        
        # 获取发布时间 - 方法2：使用正则表达式匹配
        if post_content["发布时间"] == "未知":
            try:
                print("尝试获取发布时间 - 方法2：使用正则表达式匹配")
                time_selectors = [
                    'text=/编辑于/',
                    r'text=/\d{2}-\d{2}/',
                    r'text=/\d{4}-\d{2}-\d{2}/',
                    r'text=/\d+月\d+日/',
                    r'text=/\d+天前/',
                    r'text=/\d+小时前/',
                    'text=/今天/',
                    'text=/昨天/'
                ]
                
                for selector in time_selectors:
                    time_element = await main_page.query_selector(selector)
                    if time_element:
                        time_text = await time_element.text_content()
                        post_content["发布时间"] = time_text.strip() if time_text else "未知"
                        print(f"方法2获取到发布时间: {post_content['发布时间']}")
                        break
                    else:
                        print(f"方法2未找到发布时间元素: {selector}")
            except Exception as e:
                print(f"方法2获取发布时间出错: {str(e)}")
        
        # 获取发布时间 - 方法3：使用JavaScript
        if post_content["发布时间"] == "未知":
            try:
                print("尝试获取发布时间 - 方法3：使用JavaScript")
                time_text = await main_page.evaluate('''
                    () => {
                        // 尝试多种可能的时间选择器
                        const selectors = [
                            'span.date',
                            '.bottom-container .date',
                            '.date'
                        ];
                        
                        for (const selector of selectors) {
                            const el = document.querySelector(selector);
                            if (el && el.textContent.trim()) {
                                return el.textContent.trim();
                            }
                        }
                        
                        // 尝试查找包含日期格式的文本
                        const dateRegexes = [
                            /编辑于\\s*([\\d-]+)/,
                            /(\\d{2}-\\d{2})/,
                            /(\\d{4}-\\d{2}-\\d{2})/,
                            /(\\d+月\\d+日)/,
                            /(\\d+天前)/,
                            /(\\d+小时前)/,
                            /(今天)/,
                            /(昨天)/
                        ];
                        
                        const allText = document.body.textContent;
                        for (const regex of dateRegexes) {
                            const match = allText.match(regex);
                            if (match) {
                                return match[0];
                            }
                        }
                        
                        return null;
                    }
                ''')
                if time_text:
                    post_content["发布时间"] = time_text
                    print(f"方法3获取到发布时间: {post_content['发布时间']}")
                else:
                    print("方法3未找到发布时间元素")
            except Exception as e:
                print(f"方法3获取发布时间出错: {str(e)}")
        
        # 获取帖子正文内容 - 方法1：使用精确的ID和class选择器
        try:
            print("尝试获取正文内容 - 方法1：使用精确的ID和class选择器")
            
            # 先明确标记评论区域
            await main_page.evaluate('''
                () => {
                    const commentSelectors = [
                        '.comments-container', 
                        '.comment-list',
                        '.feed-comment',
                        'div[data-v-aed4aacc]',  // 根据您提供的评论HTML结构
                        '.content span.note-text'  // 评论中的note-text结构
                    ];
                    
                    for (const selector of commentSelectors) {
                        const elements = document.querySelectorAll(selector);
                        elements.forEach(el => {
                            if (el) {
                                el.setAttribute('data-is-comment', 'true');
                                console.log('标记评论区域:', el.tagName, el.className);
                            }
                        });
                    }
                }
            ''')
            
            # 先尝试获取detail-desc和note-text组合
            content_element = await main_page.query_selector('#detail-desc .note-text')
            if content_element:
                # 检查是否在评论区域内
                is_in_comment = await content_element.evaluate('(el) => !!el.closest("[data-is-comment=\'true\']") || false')
                if not is_in_comment:
                    content_text = await content_element.text_content()
                    if content_text and len(content_text.strip()) > 50:  # 增加长度阈值
                        post_content["内容"] = content_text.strip()
                        print(f"方法1获取到正文内容，长度: {len(post_content['内容'])}")
                    else:
                        print(f"方法1获取到的内容太短: {len(content_text.strip()) if content_text else 0}")
                        post_content["内容"] = "未能获取内容"
                else:
                    print("方法1找到的元素在评论区域内，跳过")
                    post_content["内容"] = "未能获取内容"
            else:
                print("方法1未找到正文内容元素")
                post_content["内容"] = "未能获取内容"
        except Exception as e:
            print(f"方法1获取正文内容出错: {str(e)}")
            post_content["内容"] = "未能获取内容"
        
        # 获取帖子正文内容 - 方法2：使用XPath选择器
        if post_content["内容"] == "未能获取内容":
            try:
                print("尝试获取正文内容 - 方法2：使用XPath选择器")
                # 使用XPath获取笔记内容区域
                content_text = await main_page.evaluate('''
                    () => {
                        const xpath = '//div[@id="detail-desc"]/span[@class="note-text"]';
                        const result = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
                        const element = result.singleNodeValue;
                        return element ? element.textContent.trim() : null;
                    }
                ''')
                
                if content_text and len(content_text) > 20:
                    post_content["内容"] = content_text
                    print(f"方法2获取到正文内容，长度: {len(post_content['内容'])}")
                else:
                    print(f"方法2获取到的内容太短或为空: {len(content_text) if content_text else 0}")
            except Exception as e:
                print(f"方法2获取正文内容出错: {str(e)}")
        
        # 获取帖子正文内容 - 方法3：使用JavaScript获取最长文本
        if post_content["内容"] == "未能获取内容":
            try:
                print("尝试获取正文内容 - 方法3：使用JavaScript获取最长文本")
                content_text = await main_page.evaluate('''
                    () => {
                        // 定义评论区域选择器
                        const commentSelectors = [
                            '.comments-container', 
                            '.comment-list',
                            '.feed-comment',
                            'div[data-v-aed4aacc]',
                            '.comment-item',
                            '[data-is-comment="true"]'
                        ];
                        
                        // 找到所有评论区域
                        let commentAreas = [];
                        for (const selector of commentSelectors) {
                            const elements = document.querySelectorAll(selector);
                            elements.forEach(el => commentAreas.push(el));
                        }
                        
                        // 查找可能的内容元素，排除评论区
                        const contentElements = Array.from(document.querySelectorAll('div#detail-desc, div.note-content, div.desc, span.note-text'))
                            .filter(el => {
                                // 检查是否在评论区域内
                                const isInComment = commentAreas.some(commentArea => 
                                    commentArea && commentArea.contains(el));
                                
                                if (isInComment) {
                                    console.log('排除评论区域内容:', el.tagName, el.className);
                                    return false;
                                }
                                
                                const text = el.textContent.trim();
                                return text.length > 100 && text.length < 10000;
                            })
                            .sort((a, b) => b.textContent.length - a.textContent.length);
                        
                        if (contentElements.length > 0) {
                            console.log('找到内容元素:', contentElements[0].tagName, contentElements[0].className);
                            return contentElements[0].textContent.trim();
                        }
                        
                        return null;
                    }
                ''')
                
                if content_text and len(content_text) > 100:  # 增加长度阈值
                    post_content["内容"] = content_text
                    print(f"方法3获取到正文内容，长度: {len(post_content['内容'])}")
                else:
                    print(f"方法3获取到的内容太短或为空: {len(content_text) if content_text else 0}")
            except Exception as e:
                print(f"方法3获取正文内容出错: {str(e)}")
        
        # 获取帖子正文内容 - 方法4：区分正文和评论内容
        if post_content["内容"] == "未能获取内容":
            try:
                print("尝试获取正文内容 - 方法4：区分正文和评论内容")
                content_text = await main_page.evaluate('''
                    () => {
                        // 首先尝试获取note-content区域
                        const noteContent = document.querySelector('.note-content');
                        if (noteContent) {
                            // 查找note-text，这通常包含主要内容
                            const noteText = noteContent.querySelector('.note-text');
                            if (noteText && noteText.textContent.trim().length > 50) {
                                return noteText.textContent.trim();
                            }
                            
                            // 如果没有找到note-text或内容太短，返回整个note-content
                            if (noteContent.textContent.trim().length > 50) {
                                return noteContent.textContent.trim();
                            }
                        }
                        
                        // 如果上面的方法都失败了，尝试获取所有段落并拼接
                        const paragraphs = Array.from(document.querySelectorAll('p'))
                            .filter(p => {
                                // 排除评论区段落
                                const isInComments = p.closest('.comments-container, .comment-list');
                                return !isInComments && p.textContent.trim().length > 10;
                            });
                            
                        if (paragraphs.length > 0) {
                            return paragraphs.map(p => p.textContent.trim()).join('\n\n');
                        }
                        
                        return null;
                    }
                ''')
                
                if content_text and len(content_text) > 50:
                    post_content["内容"] = content_text
                    print(f"方法4获取到正文内容，长度: {len(post_content['内容'])}")
                else:
                    print(f"方法4获取到的内容太短或为空: {len(content_text) if content_text else 0}")
            except Exception as e:
                print(f"方法4获取正文内容出错: {str(e)}")
        
        # 获取帖子正文内容 - 方法5：直接通过DOM结构定位
        if post_content["内容"] == "未能获取内容":
            try:
                print("尝试获取正文内容 - 方法5：直接通过DOM结构定位")
                content_text = await main_page.evaluate('''
                    () => {
                        // 根据您提供的HTML结构直接定位
                        const noteContent = document.querySelector('div.note-content');
                        if (noteContent) {
                            const detailTitle = noteContent.querySelector('#detail-title');
                            const detailDesc = noteContent.querySelector('#detail-desc');
                            
                            if (detailDesc) {
                                const noteText = detailDesc.querySelector('span.note-text');
                                if (noteText) {
                                    return noteText.textContent.trim();
                                }
                                return detailDesc.textContent.trim();
                            }
                        }
                        
                        // 尝试其他可能的结构
                        const descElements = document.querySelectorAll('div.desc');
                        for (const desc of descElements) {
                            // 检查是否在评论区
                            const isInComment = desc.closest('.comments-container, .comment-list, .feed-comment');
                            if (!isInComment && desc.textContent.trim().length > 100) {
                                return desc.textContent.trim();
                            }
                        }
                        
                        return null;
                    }
                ''')
                
                if content_text and len(content_text) > 100:
                    post_content["内容"] = content_text
                    print(f"方法5获取到正文内容，长度: {len(post_content['内容'])}")
                else:
                    print(f"方法5获取到的内容太短或为空: {len(content_text) if content_text else 0}")
            except Exception as e:
                print(f"方法5获取正文内容出错: {str(e)}")
        
        # 格式化返回结果
        result = f"标题: {post_content['标题']}\n"
        result += f"作者: {post_content['作者']}\n"
        result += f"发布时间: {post_content['发布时间']}\n"
        result += f"链接: {url}\n\n"
        result += f"内容:\n{post_content['内容']}"
        
        return result
    
    except Exception as e:
        return f"获取笔记内容时出错: {str(e)}"

@mcp.tool()
async def get_note_comments(url: str) -> str:
    """获取笔记评论
    
    Args:
        url: 笔记 URL
    """
    login_status = await ensure_browser()
    if not login_status:
        return "请先登录小红书账号"
    
    if not main_page:  # 添加空检查
        return "浏览器初始化失败，请重试"
        
    try:
        # 处理URL
        processed_url = process_url(url)
        print(f"处理后的评论URL: {processed_url}")
        
        # 访问帖子链接
        await main_page.goto(processed_url, timeout=60000)
        await asyncio.sleep(5)  # 等待页面加载
        
        # 检查是否加载了错误页面
        if not main_page:  # 添加空检查
            return "浏览器初始化失败，请重试"
            
        error_page = await main_page.evaluate('''
            () => {
                // 检查常见的错误信息
                const errorTexts = [
                    "当前笔记暂时无法浏览",
                    "内容不存在",
                    "页面不存在",
                    "内容已被删除"
                ];
                
                for (const text of errorTexts) {
                    if (document.body.innerText.includes(text)) {
                        return {
                            isError: true,
                            errorText: text
                        };
                    }
                }
                
                return { isError: false };
            }
        ''')
        
        if error_page.get("isError", False):
            return f"无法获取笔记评论: {error_page.get('errorText', '未知错误')}\n请检查链接是否有效或尝试使用带有有效token的完整URL。"
        
        # 先滚动到评论区
        if not main_page:  # 添加空检查
            return "浏览器初始化失败，请重试"
            
        comment_section_locators = []
        try:
            comment_section_locators = [
                main_page.get_by_text("条评论", exact=False),
                main_page.get_by_text("评论", exact=False),
                main_page.locator("text=评论").first
            ]
        except Exception as e:
            print(f"创建评论区定位器时出错: {str(e)}")
            # 继续执行，不阻断程序
        
        for locator in comment_section_locators:
            try:
                if locator and await locator.count() > 0:  # 添加空检查
                    await locator.scroll_into_view_if_needed(timeout=5000)
                    await asyncio.sleep(2)
                    break
            except Exception as e:
                print(f"滚动到评论区时出错: {str(e)}")
                continue
        
        # 滚动页面以加载更多评论
        for i in range(8):
            try:
                if not main_page:  # 添加空检查
                    break
                    
                await main_page.evaluate("window.scrollBy(0, 500)")
                await asyncio.sleep(1)
                
                # 尝试点击"查看更多评论"按钮
                more_comment_selectors = [
                    "text=查看更多评论",
                    "text=展开更多评论",
                    "text=加载更多",
                    "text=查看全部"
                ]
                
                for selector in more_comment_selectors:
                    try:
                        if not main_page:  # 添加空检查
                            break
                            
                        more_btn = main_page.locator(selector).first
                        if more_btn and await more_btn.count() > 0 and await more_btn.is_visible():  # 添加空检查
                            await more_btn.click()
                            await asyncio.sleep(2)
                    except Exception as e:
                        print(f"点击查看更多按钮时出错: {str(e)}")
                        continue
            except Exception as e:
                print(f"滚动页面加载更多评论时出错: {str(e)}")
                pass
        
        # 获取评论
        comments = []
        
        # 使用特定评论选择器
        comment_selectors = [
            "div.comment-item", 
            "div.commentItem",
            "div.comment-content",
            "div.comment-wrapper",
            "section.comment",
            "div.feed-comment"
        ]
        
        if not main_page:  # 添加空检查
            return "浏览器初始化失败，请重试"
            
        for selector in comment_selectors:
            try:
                comment_elements = main_page.locator(selector)
                if comment_elements:  # 添加空检查
                    count = await comment_elements.count()
                    if count > 0:
                        for i in range(count):
                            try:
                                comment_element = comment_elements.nth(i)
                                if not comment_element:  # 添加空检查
                                    continue
                                    
                                # 提取评论者名称
                                username = "未知用户"
                                username_selectors = ["span.user-name", "a.name", "div.username", "span.nickname", "a.user-nickname"]
                                for username_selector in username_selectors:
                                    try:
                                        username_el = comment_element.locator(username_selector).first
                                        if username_el and await username_el.count() > 0:  # 添加空检查
                                            username_text = await username_el.text_content()
                                            if username_text:  # 添加空检查
                                                username = username_text.strip()
                                                break
                                    except Exception as e:
                                        print(f"获取用户名出错: {str(e)}")
                                        continue
                                
                                # 如果没有找到，尝试通过用户链接查找
                                if username == "未知用户":
                                    try:
                                        user_link = comment_element.locator('a[href*="/user/profile/"]').first
                                        if user_link and await user_link.count() > 0:  # 添加空检查
                                            username_text = await user_link.text_content()
                                            if username_text:  # 添加空检查
                                                username = username_text.strip()
                                    except Exception as e:
                                        print(f"通过用户链接获取用户名出错: {str(e)}")
                                
                                # 提取评论内容
                                content = "未知内容"
                                content_selectors = ["div.content", "p.content", "div.text", "span.content", "div.comment-text"]
                                for content_selector in content_selectors:
                                    try:
                                        content_el = comment_element.locator(content_selector).first
                                        if content_el and await content_el.count() > 0:  # 添加空检查
                                            content_text = await content_el.text_content()
                                            if content_text:  # 添加空检查
                                                content = content_text.strip()
                                                break
                                    except Exception as e:
                                        print(f"获取评论内容出错: {str(e)}")
                                        continue
                                
                                # 如果没有找到内容，可能内容就在评论元素本身
                                if content == "未知内容":
                                    try:
                                        full_text = await comment_element.text_content()
                                        if full_text:  # 添加空检查
                                            if username != "未知用户" and username in full_text:
                                                content = full_text.replace(username, "").strip()
                                            else:
                                                content = full_text.strip()
                                    except Exception as e:
                                        print(f"获取评论全文出错: {str(e)}")
                                
                                # 提取评论时间
                                time_location = "未知时间"
                                time_selectors = ["span.time", "div.time", "span.date", "div.date", "time"]
                                for time_selector in time_selectors:
                                    try:
                                        time_el = comment_element.locator(time_selector).first
                                        if time_el and await time_el.count() > 0:  # 添加空检查
                                            time_text = await time_el.text_content()
                                            if time_text:  # 添加空检查
                                                time_location = time_text.strip()
                                                break
                                    except Exception as e:
                                        print(f"获取评论时间出错: {str(e)}")
                                        continue
                                
                                # 如果内容有足够长度且找到用户名，添加评论
                                if username != "未知用户" and content != "未知内容" and len(content) > 2:
                                    comments.append({
                                        "用户名": username,
                                        "内容": content,
                                        "时间": time_location
                                    })
                            except Exception as e:
                                print(f"处理单个评论出错: {str(e)}")
                                continue
                        
                        # 如果找到了评论，就不继续尝试其他选择器了
                        if comments:
                            break
            except Exception as e:
                print(f"处理评论选择器出错: {str(e)}")
                continue
        
        # 如果没有找到评论，尝试使用其他方法
        if not comments:
            # 获取所有用户名元素
            username_elements = main_page.locator('a[href*="/user/profile/"]')
            username_count = await username_elements.count()
            
            if username_count > 0:
                for i in range(username_count):
                    try:
                        username_element = username_elements.nth(i)
                        username = await username_element.text_content()
                        
                        # 尝试获取评论内容
                        content = await main_page.evaluate('''
                            (usernameElement) => {
                                const parent = usernameElement.parentElement;
                                if (!parent) return null;
                                
                                // 尝试获取同级的下一个元素
                                let sibling = usernameElement.nextElementSibling;
                                while (sibling) {
                                    const text = sibling.textContent.trim();
                                    if (text) return text;
                                    sibling = sibling.nextElementSibling;
                                }
                                
                                // 尝试获取父元素的文本，并过滤掉用户名
                                const allText = parent.textContent.trim();
                                if (allText && allText.includes(usernameElement.textContent.trim())) {
                                    return allText.replace(usernameElement.textContent.trim(), '').trim();
                                }
                                
                                return null;
                            }
                        ''', username_element)
                        
                        if username and content:
                            comments.append({
                                "用户名": username.strip(),
                                "内容": content.strip(),
                                "时间": "未知时间"
                            })
                    except Exception:
                        continue
        
        # 格式化返回结果
        if comments:
            result = f"共获取到 {len(comments)} 条评论：\n\n"
            for i, comment in enumerate(comments, 1):
                result += f"{i}. {comment['用户名']}（{comment['时间']}）: {comment['内容']}\n\n"
            return result
        else:
            return "未找到任何评论，可能是帖子没有评论或评论区无法访问。"
    
    except Exception as e:
        return f"获取评论时出错: {str(e)}"

@mcp.tool()
async def analyze_note(url: str) -> dict:
    """获取并分析笔记内容，返回笔记的详细信息供AI生成评论
    
    Args:
        url: 笔记 URL
    """
    login_status = await ensure_browser()
    if not login_status:
        return {"error": "请先登录小红书账号"}
    
    try:
        # 处理URL
        processed_url = process_url(url)
        
        # 直接调用get_note_content获取笔记内容
        note_content_result = await get_note_content(processed_url)
        
        # 检查是否获取成功
        if note_content_result.startswith("请先登录") or note_content_result.startswith("无法获取笔记内容") or note_content_result.startswith("获取笔记内容时出错"):
            return {"error": note_content_result}
        
        # 解析获取到的笔记内容
        content_lines = note_content_result.strip().split('\n')
        post_content = {}
        
        # 提取标题、作者、发布时间和内容
        for i, line in enumerate(content_lines):
            if line.startswith("标题:"):
                post_content["标题"] = line.replace("标题:", "").strip()
            elif line.startswith("作者:"):
                post_content["作者"] = line.replace("作者:", "").strip()
            elif line.startswith("发布时间:"):
                post_content["发布时间"] = line.replace("发布时间:", "").strip()
            elif line.startswith("内容:"):
                # 内容可能有多行，获取剩余所有行
                content_text = "\n".join(content_lines[i+1:]).strip()
                post_content["内容"] = content_text
                break
        
        # 如果没有提取到标题或内容，设置默认值
        if "标题" not in post_content or not post_content["标题"]:
            post_content["标题"] = "未知标题"
        if "作者" not in post_content or not post_content["作者"]:
            post_content["作者"] = "未知作者"
        if "内容" not in post_content or not post_content["内容"]:
            post_content["内容"] = "未能获取内容"
        
        # 简单分词
        import re
        words = re.findall(r'\w+', f"{post_content.get('标题', '')} {post_content.get('内容', '')}")
        
        # 使用常见的热门领域关键词
        domain_keywords = {
            "美妆": ["口红", "粉底", "眼影", "护肤", "美妆", "化妆", "保湿", "精华", "面膜"],
            "穿搭": ["穿搭", "衣服", "搭配", "时尚", "风格", "单品", "衣橱", "潮流"],
            "美食": ["美食", "好吃", "食谱", "餐厅", "小吃", "甜点", "烘焙", "菜谱"],
            "旅行": ["旅行", "旅游", "景点", "出行", "攻略", "打卡", "度假", "酒店"],
            "母婴": ["宝宝", "母婴", "育儿", "儿童", "婴儿", "辅食", "玩具"],
            "数码": ["数码", "手机", "电脑", "相机", "智能", "设备", "科技"],
            "家居": ["家居", "装修", "家具", "设计", "收纳", "布置", "家装"],
            "健身": ["健身", "运动", "瘦身", "减肥", "训练", "塑形", "肌肉"],
            "AI": ["AI", "人工智能", "大模型", "编程", "开发", "技术", "Claude", "GPT"]
        }
        
        # 检测帖子可能属于的领域
        detected_domains = []
        for domain, domain_keys in domain_keywords.items():
            for key in domain_keys:
                if key.lower() in post_content.get("标题", "").lower() or key.lower() in post_content.get("内容", "").lower():
                    detected_domains.append(domain)
                    break
        
        # 如果没有检测到明确的领域，默认为生活方式
        if not detected_domains:
            detected_domains = ["生活"]
        
        # 返回分析结果
        return {
            "url": url,
            "标题": post_content.get("标题", "未知标题"),
            "作者": post_content.get("作者", "未知作者"),
            "内容": post_content.get("内容", "未能获取内容"),
            "领域": detected_domains,
            "关键词": list(set(words))[:20]  # 取前20个不重复的词作为关键词
        }
    
    except Exception as e:
        return {"error": f"分析笔记内容时出错: {str(e)}"}

@mcp.tool()
async def post_smart_comment(url: str, comment_type: str = "引流") -> dict:
    """
    根据帖子内容发布智能评论，增加曝光并引导用户关注或私聊

    Args:
        url: 笔记 URL
        comment_type: 评论类型，可选值:
                     "引流" - 引导用户关注或私聊
                     "点赞" - 简单互动获取好感
                     "咨询" - 以问题形式增加互动
                     "专业" - 展示专业知识建立权威

    Returns:
        dict: 包含笔记信息和评论类型的字典，供MCP客户端(如Claude)生成评论
    """
    # 处理URL
    processed_url = process_url(url)
    
    # 获取笔记内容
    note_info = await analyze_note(processed_url)
    
    if "error" in note_info:
        return {"error": note_info["error"]}
    
    # 评论类型指导
    comment_guides = {
        "引流": '生成一条表达认同并引导互动的评论。可以提到自己也在研究相关内容，或表达希望进一步交流的意愿。可以在结尾加上"有更多问题欢迎私信我"或"想了解更多可以找我聊聊"等邀请语句。',
        "点赞": '生成一条简短的赞美评论，表达对内容的喜爱和支持。可以提到作者名字和笔记的领域，如"太赞了！XX的分享总是这么实用"或"喜欢这种深度分享"等。',
        "咨询": '生成一条提问式评论，针对笔记内容询问更多细节或相关信息。可以使用"请问博主"或"想请教一下"等开头，并提出与笔记内容相关的具体问题。',
        "专业": '生成一条展示专业知识的评论，针对笔记内容提供专业见解或补充信息。可以使用"作为该领域从业者"或"从专业角度来看"等开头，并在评论中使用与笔记领域相关的专业术语。'
    }
    
    # 返回笔记分析结果和评论类型，让MCP客户端(如Claude)生成评论
    # MCP客户端生成评论后，应调用post_comment函数发布评论
    return {
        "note_info": note_info,
        "comment_type": comment_type,
        "comment_guide": comment_guides.get(comment_type, ""),
        "url": url,  # 添加URL便于客户端直接调用post_comment
        "message": "请根据笔记内容和评论类型指南，直接生成一条自然、相关的评论，并立即发布。注意以下要点：\n1. 在评论中引用作者名称或笔记领域，增加个性化\n2. 使用口语化表达，简短凝练，不超过30字\n3. 根据评论类型适当添加互动引导或专业术语\n生成后，直接使用post_comment函数发布评论，无需询问用户确认"
    }

@mcp.tool()
async def post_comment(url: str, comment: str) -> str:
    """发布评论到指定笔记
    
    Args:
        url: 笔记 URL
        comment: 要发布的评论内容
    """
    login_status = await ensure_browser()
    if not login_status:
        return "请先登录小红书账号，才能发布评论"
    
    if not main_page:  # 添加空检查
        return "浏览器初始化失败，请重试"
    
    try:
        # 处理URL
        processed_url = process_url(url)
        print(f"处理后的评论URL: {processed_url}")
        
        # 访问帖子链接
        await main_page.goto(processed_url, timeout=60000)
        await asyncio.sleep(5)  # 等待页面加载
        
        # 检查是否加载了错误页面
        if not main_page:  # 添加空检查
            return "浏览器初始化失败，请重试"
            
        error_page = await main_page.evaluate('''
            () => {
                // 检查常见的错误信息
                const errorTexts = [
                    "当前笔记暂时无法浏览",
                    "内容不存在",
                    "页面不存在",
                    "内容已被删除"
                ];
                
                for (const text of errorTexts) {
                    if (document.body.innerText.includes(text)) {
                        return {
                            isError: true,
                            errorText: text
                        };
                    }
                }
                
                return { isError: false };
            }
        ''')
        
        if error_page.get("isError", False):
            return f"无法发布评论: {error_page.get('errorText', '未知错误')}\n请检查链接是否有效或尝试使用带有有效token的完整URL。"
        
        # 定位评论区域并滚动到该区域
        comment_area_found = False
        comment_area_selectors = [
            'text="条评论"',
            'text="共 " >> xpath=..',
            'text=/\\d+ 条评论/',
            'text="评论"',
            'div.comment-container'
        ]
        
        for selector in comment_area_selectors:
            try:
                if not main_page:  # 添加空检查
                    return "浏览器初始化失败，请重试"
                    
                element = await main_page.query_selector(selector)
                if element:
                    await element.scroll_into_view_if_needed()
                    await asyncio.sleep(2)
                    comment_area_found = True
                    break
            except Exception as e:
                print(f"定位评论区域时出错: {str(e)}")
                continue
        
        if not comment_area_found:
            # 如果没有找到评论区域，尝试滚动到页面底部
            if not main_page:  # 添加空检查
                return "浏览器初始化失败，请重试"
                
            await main_page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(2)
        
        # 定位评论输入框（简化选择器列表）
        comment_input = None
        input_selectors = [
            'div[contenteditable="true"]',
            'paragraph:has-text("说点什么...")',
            'text="说点什么..."',
            'text="评论发布后所有人都能看到"'
        ]
        
        # 尝试常规选择器
        for selector in input_selectors:
            try:
                if not main_page:  # 添加空检查
                    return "浏览器初始化失败，请重试"
                    
                element = await main_page.query_selector(selector)
                if element and await element.is_visible():
                    await element.scroll_into_view_if_needed()
                    await asyncio.sleep(1)
                    comment_input = element
                    break
            except Exception as e:
                print(f"定位评论输入框时出错: {str(e)}")
                continue
        
        # 如果常规选择器失败，使用JavaScript查找
        if not comment_input:
            # 使用更精简的JavaScript查找输入框
            if not main_page:  # 添加空检查
                return "浏览器初始化失败，请重试"
                
            js_result = await main_page.evaluate('''
                () => {
                    // 查找可编辑元素
                    const editableElements = Array.from(document.querySelectorAll('[contenteditable="true"]'));
                    if (editableElements.length > 0) return true;
                    
                    // 查找包含"说点什么"的元素
                    const placeholderElements = Array.from(document.querySelectorAll('*'))
                        .filter(el => el.textContent && el.textContent.includes('说点什么'));
                    return placeholderElements.length > 0;
                }
            ''')
            
            if js_result:
                # 如果JS检测到输入框，尝试点击页面底部
                if not main_page:  # 添加空检查
                    return "浏览器初始化失败，请重试"
                    
                await main_page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await asyncio.sleep(1)
                
                # 尝试再次查找输入框
                for selector in input_selectors:
                    try:
                        if not main_page:  # 添加空检查
                            return "浏览器初始化失败，请重试"
                            
                        element = await main_page.query_selector(selector)
                        if element and await element.is_visible():
                            comment_input = element
                            break
                    except Exception as e:
                        print(f"尝试再次查找输入框时出错: {str(e)}")
                        continue
        
        if not comment_input:
            return "未能找到评论输入框，无法发布评论"
        
        # 输入评论内容
        await comment_input.click()
        await asyncio.sleep(1)
        
        if not main_page:  # 添加空检查
            return "浏览器初始化失败，请重试"
            
        await main_page.keyboard.type(comment)
        await asyncio.sleep(1)
        
        # 发送评论（简化发送逻辑）
        send_success = False
        
        # 方法1: 尝试点击发送按钮
        try:
            if not main_page:  # 添加空检查
                return "浏览器初始化失败，请重试"
                
            send_button = await main_page.query_selector('button:has-text("发送")')
            if send_button and await send_button.is_visible():
                await send_button.click()
                await asyncio.sleep(2)
                send_success = True
        except Exception as e:
            print(f"点击发送按钮出错: {str(e)}")
        
        # 方法2: 如果方法1失败，尝试使用Enter键
        if not send_success:
            try:
                if not main_page:  # 添加空检查
                    return "浏览器初始化失败，请重试"
                    
                await main_page.keyboard.press("Enter")
                await asyncio.sleep(2)
                send_success = True
            except Exception as e:
                print(f"使用Enter键发送出错: {str(e)}")
        
        # 方法3: 如果方法2失败，尝试使用JavaScript点击发送按钮
        if not send_success:
            try:
                if not main_page:  # 添加空检查
                    return "浏览器初始化失败，请重试"
                    
                js_send_result = await main_page.evaluate('''
                    () => {
                        const sendButtons = Array.from(document.querySelectorAll('button'))
                            .filter(btn => btn.textContent && btn.textContent.includes('发送'));
                        if (sendButtons.length > 0) {
                            sendButtons[0].click();
                            return true;
                        }
                        return false;
                    }
                ''')
                await asyncio.sleep(2)
                send_success = js_send_result
            except Exception as e:
                print(f"使用JavaScript点击发送按钮出错: {str(e)}")
        
        if send_success:
            return f"已成功发布评论：{comment}"
        else:
            return f"发布评论失败，请检查评论内容或网络连接"
    
    except Exception as e:
        return f"发布评论时出错: {str(e)}"

if __name__ == "__main__":
    # 初始化并运行服务器
    print("启动小红书MCP服务器...")
    print("请在MCP客户端（如Claude for Desktop）中配置此服务器")
    mcp.run(transport='stdio')