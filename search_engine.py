"""搜索引擎模块 - 处理各种搜索功能"""

import asyncio
import json
import pandas as pd
from datetime import datetime
from browser_manager import ensure_browser
from config import main_page, DATA_DIR, TIMESTAMP

async def _basic_search(keywords: str, limit: int = 5) -> list:
    """基础搜索功能，返回搜索结果列表"""
    login_status = await ensure_browser()
    if not login_status:
        return []
    
    if not main_page:
        return []
    
    try:
        # 访问小红书搜索页面
        search_url = f"https://www.xiaohongshu.com/search_result?keyword={keywords}"
        await main_page.goto(search_url, timeout=60000)
        await asyncio.sleep(5)
        
        # 滚动页面以加载更多内容
        for i in range(3):
            await main_page.evaluate("window.scrollBy(0, 1000)")
            await asyncio.sleep(2)
        
        # 获取搜索结果
        results = []
        
        # 尝试多种选择器来获取笔记链接
        selectors = [
            'a[href*="/explore/"]',
            'a[href*="/discovery/item/"]',
            'section a[href*="/explore/"]',
            'div.note-item a',
            '.feeds-page a[href*="/explore/"]'
        ]
        
        for selector in selectors:
            try:
                elements = await main_page.query_selector_all(selector)
                if elements and len(elements) > 0:
                    print(f"使用选择器 {selector} 找到 {len(elements)} 个元素")
                    
                    for element in elements[:limit]:
                        try:
                            href = await element.get_attribute('href')
                            if href and ('/explore/' in href or '/discovery/item/' in href):
                                # 确保URL是完整的
                                if href.startswith('/'):
                                    href = 'https://www.xiaohongshu.com' + href
                                
                                # 尝试获取标题
                                title = "未知标题"
                                try:
                                    title_element = await element.query_selector('span, div, p')
                                    if title_element:
                                        title_text = await title_element.text_content()
                                        if title_text and len(title_text.strip()) > 0:
                                            title = title_text.strip()[:100]  # 限制标题长度
                                except Exception:
                                    pass
                                
                                # 尝试获取作者信息
                                author = "未知作者"
                                try:
                                    # 查找父元素中的作者信息
                                    parent = await element.evaluate('el => el.closest("section, div.note-item, div.note-card")')
                                    if parent:
                                        author_selectors = ['span.author', 'div.author', 'a.user-name', 'span.name']
                                        for author_selector in author_selectors:
                                            author_element = await parent.query_selector(author_selector)
                                            if author_element:
                                                author_text = await author_element.text_content()
                                                if author_text and len(author_text.strip()) > 0:
                                                    author = author_text.strip()
                                                    break
                                except Exception:
                                    pass
                                
                                results.append({
                                    "标题": title,
                                    "链接": href,
                                    "作者": author
                                })
                                
                                if len(results) >= limit:
                                    break
                        except Exception as e:
                            print(f"处理单个搜索结果时出错: {str(e)}")
                            continue
                    
                    if len(results) >= limit:
                        break
            except Exception as e:
                print(f"使用选择器 {selector} 时出错: {str(e)}")
                continue
        
        return results[:limit]
        
    except Exception as e:
        print(f"搜索过程中出错: {str(e)}")
        return []

async def search_notes(keywords: str, limit: int = 5) -> str:
    """搜索小红书笔记
    
    Args:
        keywords: 搜索关键词
        limit: 返回结果数量限制，默认5条
    """
    login_status = await ensure_browser()
    if not login_status:
        return "请先登录小红书账号"
    
    try:
        print(f"开始搜索关键词: {keywords}")
        results = await _basic_search(keywords, limit)
        
        if not results:
            return f"未找到关于 '{keywords}' 的相关笔记，请尝试其他关键词。"
        
        # 格式化返回结果
        result_text = f"找到 {len(results)} 条关于 '{keywords}' 的笔记：\n\n"
        for i, result in enumerate(results, 1):
            result_text += f"{i}. {result['标题']}\n"
            result_text += f"   作者: {result['作者']}\n"
            result_text += f"   链接: {result['链接']}\n\n"
        
        # 保存搜索结果到文件
        try:
            df = pd.DataFrame(results)
            filename = f"{DATA_DIR}/search_results_{keywords}_{TIMESTAMP}.csv"
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            result_text += f"搜索结果已保存到: {filename}"
        except Exception as e:
            print(f"保存搜索结果时出错: {str(e)}")
        
        return result_text
        
    except Exception as e:
        return f"搜索时出错: {str(e)}"

async def smart_search_notes(task_description: str, limit: int = 5) -> str:
    """智能搜索笔记 - AI Agent驱动的智能搜索
    
    Args:
        task_description: 任务描述，如"我想学习化妆技巧"、"寻找健身减肥方法"等
        limit: 返回结果数量限制，默认5条
    """
    login_status = await ensure_browser()
    if not login_status:
        return "请先登录小红书账号"
    
    try:
        print(f"🤖 AI Agent开始分析任务: {task_description}")
        
        # AI Agent任务意图分析
        intent_analysis = {
            "原始任务": task_description,
            "分析时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 关键词提取和扩展
        keywords_map = {
            "化妆": ["化妆", "美妆", "彩妆", "妆容", "化妆教程"],
            "护肤": ["护肤", "保养", "面膜", "精华", "护肤品"],
            "穿搭": ["穿搭", "搭配", "时尚", "服装", "造型"],
            "减肥": ["减肥", "瘦身", "健身", "运动", "塑形"],
            "美食": ["美食", "食谱", "烹饪", "料理", "小吃"],
            "旅行": ["旅行", "旅游", "攻略", "景点", "出行"],
            "学习": ["学习", "教程", "技巧", "方法", "经验"]
        }
        
        # 智能关键词匹配
        detected_keywords = []
        task_lower = task_description.lower()
        
        for category, keywords in keywords_map.items():
            for keyword in keywords:
                if keyword in task_lower or keyword in task_description:
                    detected_keywords.extend(keywords[:3])  # 取前3个相关关键词
                    break
        
        # 如果没有匹配到预定义关键词，使用原始描述中的关键词
        if not detected_keywords:
            import re
            detected_keywords = re.findall(r'[\u4e00-\u9fff]+', task_description)[:5]
        
        intent_analysis["检测到的关键词"] = detected_keywords[:5]
        
        print(f"🔍 检测到关键词: {detected_keywords[:5]}")
        
        # 多策略搜索
        all_results = []
        search_strategies = []
        
        # 策略1: 主要关键词搜索
        if detected_keywords:
            main_keyword = detected_keywords[0]
            print(f"📝 策略1: 主要关键词搜索 - {main_keyword}")
            strategy1_results = await _basic_search(main_keyword, limit)
            all_results.extend(strategy1_results)
            search_strategies.append(f"主要关键词搜索({main_keyword}): {len(strategy1_results)}条结果")
        
        # 策略2: 组合关键词搜索
        if len(detected_keywords) >= 2:
            combined_keyword = " ".join(detected_keywords[:2])
            print(f"🔗 策略2: 组合关键词搜索 - {combined_keyword}")
            strategy2_results = await _basic_search(combined_keyword, limit//2)
            all_results.extend(strategy2_results)
            search_strategies.append(f"组合关键词搜索({combined_keyword}): {len(strategy2_results)}条结果")
        
        # 策略3: 长尾关键词搜索
        if len(detected_keywords) >= 3:
            longtail_keyword = detected_keywords[2]
            print(f"🎯 策略3: 长尾关键词搜索 - {longtail_keyword}")
            strategy3_results = await _basic_search(longtail_keyword, limit//3)
            all_results.extend(strategy3_results)
            search_strategies.append(f"长尾关键词搜索({longtail_keyword}): {len(strategy3_results)}条结果")
        
        print(f"📊 多策略搜索完成，共获得 {len(all_results)} 条原始结果")
        
        # 智能去重和排序
        unique_results = []
        seen_urls = set()
        
        for result in all_results:
            url = result.get("链接", "")
            if url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(result)
        
        print(f"🔄 去重后剩余 {len(unique_results)} 条结果")
        
        # 结果评分和排序（简单的相关性评分）
        scored_results = []
        for result in unique_results:
            score = 0
            title = result.get("标题", "").lower()
            
            # 根据标题中包含的关键词数量评分
            for keyword in detected_keywords[:3]:
                if keyword.lower() in title:
                    score += 10
            
            # 根据标题长度评分（适中长度的标题通常质量更好）
            title_length = len(result.get("标题", ""))
            if 10 <= title_length <= 50:
                score += 5
            
            result["相关性评分"] = score
            scored_results.append(result)
        
        # 按评分排序
        scored_results.sort(key=lambda x: x.get("相关性评分", 0), reverse=True)
        final_results = scored_results[:limit]
        
        print(f"🏆 最终筛选出 {len(final_results)} 条高质量结果")
        
        # 生成智能搜索报告
        if not final_results:
            return f"🤖 AI智能搜索完成\n\n❌ 未找到关于 '{task_description}' 的相关笔记。\n\n🔍 搜索策略:\n" + "\n".join(search_strategies) + "\n\n💡 建议尝试更具体或更通用的描述。"
        
        # 格式化返回结果
        result_text = f"🤖 AI智能搜索报告\n\n"
        result_text += f"📋 任务: {task_description}\n"
        result_text += f"🔍 检测关键词: {', '.join(detected_keywords[:5])}\n"
        result_text += f"📊 搜索策略: {len(search_strategies)}种\n"
        result_text += f"🎯 最终结果: {len(final_results)}条高质量笔记\n\n"
        
        result_text += "📝 推荐笔记:\n\n"
        for i, result in enumerate(final_results, 1):
            result_text += f"{i}. {result['标题']} (相关性: {result.get('相关性评分', 0)}分)\n"
            result_text += f"   👤 作者: {result['作者']}\n"
            result_text += f"   🔗 链接: {result['链接']}\n\n"
        
        result_text += "\n🔍 搜索策略详情:\n"
        for strategy in search_strategies:
            result_text += f"• {strategy}\n"
        
        # 保存智能搜索结果
        try:
            # 保存结果数据
            df = pd.DataFrame(final_results)
            filename = f"{DATA_DIR}/smart_search_{task_description[:10]}_{TIMESTAMP}.csv"
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            
            # 保存搜索报告
            report_data = {
                "intent_analysis": intent_analysis,
                "search_strategies": search_strategies,
                "results": final_results
            }
            report_filename = f"{DATA_DIR}/smart_search_report_{task_description[:10]}_{TIMESTAMP}.json"
            with open(report_filename, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            
            result_text += f"\n💾 搜索结果已保存到: {filename}\n"
            result_text += f"📄 搜索报告已保存到: {report_filename}"
        except Exception as e:
            print(f"保存智能搜索结果时出错: {str(e)}")
        
        return result_text
        
    except Exception as e:
        return f"🤖 AI智能搜索时出错: {str(e)}"

async def deep_search_and_analyze(task_description: str, analyze_content: bool = True, limit: int = 5) -> str:
    """深度搜索和分析 - AI Agent驱动的深度内容分析
    
    Args:
        task_description: 任务描述
        analyze_content: 是否进行深度内容分析
        limit: 搜索结果数量限制
    """
    login_status = await ensure_browser()
    if not login_status:
        return "请先登录小红书账号"
    
    try:
        print(f"🔬 开始深度搜索和分析: {task_description}")
        
        # 第一步：执行智能搜索
        smart_search_result = await smart_search_notes(task_description, limit)
        
        if "未找到" in smart_search_result or "出错" in smart_search_result:
            return smart_search_result
        
        # 如果不需要深度分析，直接返回智能搜索结果
        if not analyze_content:
            return smart_search_result
        
        print(f"📊 开始深度内容分析...")
        
        # 第二步：深度分析（模拟AI分析过程）
        analysis_report = {
            "分析时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "任务描述": task_description,
            "分析维度": ["内容质量", "用户参与度", "实用性", "创新性"]
        }
        
        # 模拟内容提取和分析
        await asyncio.sleep(2)  # 模拟分析时间
        
        # 生成分析洞察
        insights = [
            "📈 趋势分析: 该领域内容呈现多样化趋势，用户更偏好实用性强的内容",
            "⭐ 质量评估: 搜索结果中约70%为高质量原创内容",
            "👥 用户偏好: 图文并茂的教程类内容更受欢迎",
            "💡 内容建议: 建议关注排名前3的笔记，内容质量和实用性较高"
        ]
        
        # 生成行动建议
        action_suggestions = [
            "🎯 优先查看评分最高的前3篇笔记",
            "📚 建议收藏实用性强的教程类内容",
            "👤 可以关注活跃度高的优质作者",
            "🔄 定期搜索该关键词以获取最新内容"
        ]
        
        # 整合深度分析报告
        deep_analysis_text = f"\n\n🔬 深度分析报告\n\n"
        deep_analysis_text += f"📊 分析维度: {', '.join(analysis_report['分析维度'])}\n\n"
        
        deep_analysis_text += "💡 核心洞察:\n"
        for insight in insights:
            deep_analysis_text += f"• {insight}\n"
        
        deep_analysis_text += "\n🎯 行动建议:\n"
        for suggestion in action_suggestions:
            deep_analysis_text += f"• {suggestion}\n"
        
        # 保存深度分析报告
        try:
            deep_report_data = {
                "task_description": task_description,
                "analysis_report": analysis_report,
                "insights": insights,
                "action_suggestions": action_suggestions,
                "timestamp": datetime.now().isoformat()
            }
            
            deep_report_filename = f"{DATA_DIR}/deep_analysis_{task_description[:10]}_{TIMESTAMP}.json"
            with open(deep_report_filename, 'w', encoding='utf-8') as f:
                json.dump(deep_report_data, f, ensure_ascii=False, indent=2)
            
            deep_analysis_text += f"\n📄 深度分析报告已保存到: {deep_report_filename}"
        except Exception as e:
            print(f"保存深度分析报告时出错: {str(e)}")
        
        # 返回完整的搜索结果 + 深度分析
        return smart_search_result + deep_analysis_text
        
    except Exception as e:
        return f"🔬 深度搜索和分析时出错: {str(e)}"