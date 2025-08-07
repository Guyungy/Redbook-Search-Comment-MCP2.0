"""评论管理模块 - 处理评论获取、生成和发布"""

import asyncio
from browser_manager import ensure_browser
from config import main_page, process_url
from content_analyzer import analyze_note

async def get_note_comments(url: str) -> str:
    """获取笔记的评论内容
    
    Args:
        url: 笔记 URL
    """
    login_status = await ensure_browser()
    if not login_status:
        return "请先登录小红书账号"
    
    if not main_page:
        return "浏览器初始化失败，请重试"
    
    try:
        # 处理URL
        processed_url = process_url(url)
        print(f"处理后的URL: {processed_url}")
        
        # 访问帖子链接
        await main_page.goto(processed_url, timeout=60000)
        await asyncio.sleep(5)  # 等待页面加载
        
        # 检查是否加载了错误页面
        error_page = await main_page.evaluate('''
            () => {
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
        
        # 滚动页面以加载更多评论
        print("滚动页面以加载更多评论...")
        for i in range(3):  # 滚动3次
            await main_page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(2)
        
        # 获取评论内容
        comments = await main_page.evaluate('''
            () => {
                const comments = [];
                
                // 多种评论选择器
                const commentSelectors = [
                    '.comment-item',
                    '.feed-comment',
                    '.comment-list .comment',
                    'div[data-v-aed4aacc]',
                    '.comments-container .comment'
                ];
                
                let commentElements = [];
                
                // 尝试不同的选择器
                for (const selector of commentSelectors) {
                    const elements = document.querySelectorAll(selector);
                    if (elements.length > 0) {
                        commentElements = Array.from(elements);
                        console.log(`使用选择器 ${selector} 找到 ${elements.length} 个评论`);
                        break;
                    }
                }
                
                // 如果没有找到评论元素，尝试更通用的方法
                if (commentElements.length === 0) {
                    // 查找包含用户名和评论内容的元素
                    const allDivs = document.querySelectorAll('div');
                    for (const div of allDivs) {
                        const text = div.textContent.trim();
                        // 如果包含典型的评论特征（用户名 + 内容），且不是太长
                        if (text.length > 10 && text.length < 500 && 
                            (text.includes('：') || text.includes(': ') || text.includes('回复'))) {
                            commentElements.push(div);
                        }
                    }
                }
                
                console.log(`总共找到 ${commentElements.length} 个潜在评论元素`);
                
                for (let i = 0; i < Math.min(commentElements.length, 20); i++) {
                    const element = commentElements[i];
                    
                    try {
                        // 尝试获取用户名
                        let username = '';
                        const usernameSelectors = [
                            '.username',
                            '.user-name',
                            '.name',
                            '.author',
                            'a[href*="user"]',
                            'span.user'
                        ];
                        
                        for (const selector of usernameSelectors) {
                            const usernameEl = element.querySelector(selector);
                            if (usernameEl && usernameEl.textContent.trim()) {
                                username = usernameEl.textContent.trim();
                                break;
                            }
                        }
                        
                        // 尝试获取评论内容
                        let content = '';
                        const contentSelectors = [
                            '.content',
                            '.comment-content',
                            '.text',
                            '.comment-text',
                            'span:not(.username):not(.user-name):not(.name):not(.time)'
                        ];
                        
                        for (const selector of contentSelectors) {
                            const contentEl = element.querySelector(selector);
                            if (contentEl && contentEl.textContent.trim() && 
                                contentEl.textContent.trim() !== username) {
                                content = contentEl.textContent.trim();
                                break;
                            }
                        }
                        
                        // 如果没有找到内容，尝试直接从元素获取文本
                        if (!content) {
                            const fullText = element.textContent.trim();
                            // 移除用户名部分
                            if (username && fullText.includes(username)) {
                                content = fullText.replace(username, '').replace(/^[：:：\s]+/, '').trim();
                            } else {
                                content = fullText;
                            }
                        }
                        
                        // 尝试获取时间
                        let time = '';
                        const timeSelectors = [
                            '.time',
                            '.date',
                            '.publish-time',
                            'time',
                            'span[title*="20"]'
                        ];
                        
                        for (const selector of timeSelectors) {
                            const timeEl = element.querySelector(selector);
                            if (timeEl && timeEl.textContent.trim()) {
                                time = timeEl.textContent.trim();
                                break;
                            }
                        }
                        
                        // 只有当有实际内容时才添加评论
                        if (content && content.length > 2 && content !== username) {
                            comments.push({
                                username: username || '匿名用户',
                                content: content,
                                time: time || '未知时间'
                            });
                        }
                        
                    } catch (e) {
                        console.log('处理评论元素时出错:', e);
                        continue;
                    }
                }
                
                return comments;
            }
        ''')
        
        if not comments or len(comments) == 0:
            return "未找到评论内容，可能该笔记没有评论或评论加载失败"
        
        # 格式化评论内容
        result = f"找到 {len(comments)} 条评论:\n\n"
        for i, comment in enumerate(comments, 1):
            result += f"{i}. {comment['username']}\n"
            result += f"   内容: {comment['content']}\n"
            if comment['time'] != '未知时间':
                result += f"   时间: {comment['time']}\n"
            result += "\n"
        
        return result
    
    except Exception as e:
        return f"获取评论时出错: {str(e)}"

async def post_smart_comment(url: str, comment_type: str = "点赞") -> str:
    """根据笔记内容智能生成并准备评论
    
    Args:
        url: 笔记 URL
        comment_type: 评论类型，可选：点赞、引流、提问、分享经验
    """
    try:
        # 分析笔记内容
        note_analysis = await analyze_note(url)
        
        if "error" in note_analysis:
            return f"无法分析笔记内容: {note_analysis['error']}"
        
        # 根据笔记内容和评论类型生成评论建议
        title = note_analysis.get("标题", "")
        content = note_analysis.get("内容", "")
        domains = note_analysis.get("领域", [])
        keywords = note_analysis.get("关键词", [])
        
        # 生成评论建议
        comment_suggestions = {
            "点赞": [
                f"太棒了！{title}真的很有用",
                "学到了，感谢分享！",
                "这个内容质量很高，收藏了",
                "楼主分享的很详细，点赞支持"
            ],
            "引流": [
                f"关于{domains[0] if domains else '这个话题'}，我也有一些心得，欢迎交流",
                "同样关注这个领域，可以互相学习",
                "有相同兴趣的朋友可以关注我，一起讨论"
            ],
            "提问": [
                f"请问{keywords[0] if keywords else '这个'}具体怎么操作呢？",
                "能详细说说具体的步骤吗？",
                "这个方法适合新手吗？"
            ],
            "分享经验": [
                f"我也试过类似的方法，{domains[0] if domains else '这个领域'}确实需要多实践",
                "补充一点经验：...",
                "我的做法是..."
            ]
        }
        
        suggestions = comment_suggestions.get(comment_type, comment_suggestions["点赞"])
        
        result = f"笔记分析结果:\n"
        result += f"标题: {title}\n"
        result += f"领域: {', '.join(domains)}\n"
        result += f"关键词: {', '.join(keywords[:5])}\n\n"
        result += f"评论类型: {comment_type}\n"
        result += f"建议评论:\n"
        
        for i, suggestion in enumerate(suggestions, 1):
            result += f"{i}. {suggestion}\n"
        
        result += f"\n使用 post_comment(url, comment_text) 来发布评论"
        
        return result
    
    except Exception as e:
        return f"生成智能评论时出错: {str(e)}"

async def post_comment(url: str, comment_text: str) -> str:
    """在指定笔记下发布评论
    
    Args:
        url: 笔记 URL
        comment_text: 要发布的评论内容
    """
    login_status = await ensure_browser()
    if not login_status:
        return "请先登录小红书账号"
    
    if not main_page:
        return "浏览器初始化失败，请重试"
    
    try:
        # 处理URL
        processed_url = process_url(url)
        print(f"处理后的URL: {processed_url}")
        
        # 访问帖子链接
        await main_page.goto(processed_url, timeout=60000)
        await asyncio.sleep(5)  # 等待页面加载
        
        # 检查是否加载了错误页面
        error_page = await main_page.evaluate('''
            () => {
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
            return f"无法访问笔记: {error_page.get('errorText', '未知错误')}\n请检查链接是否有效。"
        
        # 滚动到评论区域
        await main_page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        await asyncio.sleep(2)
        
        # 查找评论输入框
        comment_input = None
        input_selectors = [
            'textarea[placeholder*="评论"]',
            'textarea[placeholder*="说点什么"]',
            'input[placeholder*="评论"]',
            'input[placeholder*="说点什么"]',
            '.comment-input textarea',
            '.comment-input input',
            'textarea.comment',
            'input.comment'
        ]
        
        for selector in input_selectors:
            try:
                comment_input = await main_page.query_selector(selector)
                if comment_input:
                    print(f"找到评论输入框: {selector}")
                    break
            except Exception as e:
                print(f"尝试选择器 {selector} 时出错: {str(e)}")
                continue
        
        # 如果没有找到输入框，尝试使用JavaScript查找
        if not comment_input:
            print("尝试使用JavaScript查找评论输入框")
            comment_input_found = await main_page.evaluate('''
                () => {
                    const inputs = document.querySelectorAll('input, textarea');
                    for (const input of inputs) {
                        const placeholder = input.placeholder || '';
                        if (placeholder.includes('评论') || placeholder.includes('说点什么') || 
                            input.className.includes('comment') || input.id.includes('comment')) {
                            input.focus();
                            return true;
                        }
                    }
                    return false;
                }
            ''')
            
            if comment_input_found:
                # 重新查找已聚焦的输入框
                comment_input = await main_page.query_selector(':focus')
        
        if not comment_input:
            return "未找到评论输入框，可能该笔记不支持评论或页面结构已变化"
        
        # 点击输入框并输入评论
        await comment_input.click()
        await asyncio.sleep(1)
        await comment_input.fill(comment_text)
        await asyncio.sleep(2)
        
        print(f"已输入评论内容: {comment_text}")
        
        # 查找并点击发送按钮
        send_success = False
        
        # 方法1: 查找发送按钮
        send_selectors = [
            'button:has-text("发送")',
            'button:has-text("发布")',
            'button:has-text("提交")',
            '.send-btn',
            '.submit-btn',
            '.comment-send',
            'button[type="submit"]'
        ]
        
        for selector in send_selectors:
            try:
                send_button = await main_page.query_selector(selector)
                if send_button:
                    await send_button.click()
                    print(f"点击发送按钮: {selector}")
                    send_success = True
                    break
            except Exception as e:
                print(f"尝试点击发送按钮 {selector} 时出错: {str(e)}")
                continue
        
        # 方法2: 尝试按Enter键
        if not send_success:
            try:
                await comment_input.press('Enter')
                print("尝试按Enter键发送评论")
                send_success = True
            except Exception as e:
                print(f"按Enter键时出错: {str(e)}")
        
        # 方法3: 使用JavaScript查找并点击发送按钮
        if not send_success:
            try:
                js_send_success = await main_page.evaluate('''
                    () => {
                        const buttons = document.querySelectorAll('button');
                        for (const button of buttons) {
                            const text = button.textContent.trim();
                            if (text.includes('发送') || text.includes('发布') || text.includes('提交')) {
                                button.click();
                                return true;
                            }
                        }
                        return false;
                    }
                ''')
                
                if js_send_success:
                    print("使用JavaScript成功点击发送按钮")
                    send_success = True
            except Exception as e:
                print(f"使用JavaScript点击发送按钮时出错: {str(e)}")
        
        if send_success:
            await asyncio.sleep(3)  # 等待评论发送
            return f"评论发送成功: {comment_text}"
        else:
            return f"评论内容已输入但可能需要手动点击发送按钮: {comment_text}"
    
    except Exception as e:
        return f"发布评论时出错: {str(e)}"