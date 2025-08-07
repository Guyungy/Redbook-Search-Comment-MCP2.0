"""小红书搜索和评论 MCP 服务器 - 重构版本"""

from fastmcp import FastMCP

# 导入模块
from config import DATA_DIR, TIMESTAMP
from browser_manager import ensure_browser, login, reset_login
from search_engine import search_notes, smart_search_notes, deep_search_and_analyze
from content_analyzer import get_note_content, analyze_note
from comment_manager import get_note_comments, post_smart_comment, post_comment

# 初始化 FastMCP 服务器
mcp = FastMCP("xiaohongshu_scraper")

@mcp.tool()
async def login_xiaohongshu() -> str:
    """登录小红书账号
    
    Returns:
        str: 登录状态信息
    """
    return await login()

@mcp.tool()
async def reset_login_status() -> str:
    """重置登录状态，清除当前登录信息
    
    Returns:
        str: 重置状态信息
    """
    return await reset_login()

@mcp.tool()
async def search_xiaohongshu_notes(keyword: str, limit: int = 10) -> str:
    """搜索小红书笔记
    
    Args:
        keyword: 搜索关键词
        limit: 搜索结果数量限制，默认10条
    
    Returns:
        str: 搜索结果
    """
    return await search_notes(keyword, limit)

@mcp.tool()
async def smart_search_xiaohongshu_notes(keyword: str, limit: int = 10) -> str:
    """智能搜索小红书笔记（AI增强版）
    
    Args:
        keyword: 搜索关键词
        limit: 搜索结果数量限制，默认10条
    
    Returns:
        str: 智能搜索结果
    """
    return await smart_search_notes(keyword, limit)

@mcp.tool()
async def deep_search_and_analyze_notes(task_description: str, analyze_content: bool = True, limit: int = 5) -> str:
    """深度搜索和分析小红书笔记
    
    Args:
        task_description: 任务描述
        analyze_content: 是否分析内容，默认True
        limit: 搜索结果数量限制，默认5条
    
    Returns:
        str: 深度分析结果
    """
    return await deep_search_and_analyze(task_description, analyze_content, limit)

@mcp.tool()
async def get_xiaohongshu_note_content(url: str) -> str:
    """获取小红书笔记详细内容
    
    Args:
        url: 笔记URL
    
    Returns:
        str: 笔记内容
    """
    return await get_note_content(url)

@mcp.tool()
async def analyze_xiaohongshu_note(url: str) -> str:
    """分析小红书笔记内容
    
    Args:
        url: 笔记URL
    
    Returns:
        str: 分析结果
    """
    result = await analyze_note(url)
    if "error" in result:
        return result["error"]
    
    # 格式化返回结果
    formatted_result = f"笔记分析结果:\n"
    formatted_result += f"标题: {result.get('标题', '未知')}\n"
    formatted_result += f"作者: {result.get('作者', '未知')}\n"
    formatted_result += f"领域: {', '.join(result.get('领域', []))}\n"
    formatted_result += f"关键词: {', '.join(result.get('关键词', [])[:10])}\n"
    formatted_result += f"内容预览: {result.get('内容', '')[:200]}..."
    
    return formatted_result

@mcp.tool()
async def get_xiaohongshu_note_comments(url: str) -> str:
    """获取小红书笔记的评论
    
    Args:
        url: 笔记URL
    
    Returns:
        str: 评论内容
    """
    return await get_note_comments(url)

@mcp.tool()
async def generate_smart_comment(url: str, comment_type: str = "点赞") -> str:
    """根据笔记内容智能生成评论建议
    
    Args:
        url: 笔记URL
        comment_type: 评论类型，可选：点赞、引流、提问、分享经验
    
    Returns:
        str: 智能评论建议
    """
    return await post_smart_comment(url, comment_type)

@mcp.tool()
async def post_xiaohongshu_comment(url: str, comment_text: str) -> str:
    """在小红书笔记下发布评论
    
    Args:
        url: 笔记URL
        comment_text: 评论内容
    
    Returns:
        str: 发布结果
    """
    return await post_comment(url, comment_text)

if __name__ == "__main__":
    # 初始化并运行服务器
    print("启动小红书MCP服务器（重构版本）...")
    print("请在MCP客户端（如Claude for Desktop）中配置此服务器")
    mcp.run(transport='stdio')