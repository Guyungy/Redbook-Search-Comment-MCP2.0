#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能搜索功能测试脚本

这个脚本演示了新的AI Agent式智能搜索功能：
1. 基础搜索 - search_notes()
2. 智能搜索 - smart_search_notes()
3. 深度搜索分析 - deep_search_and_analyze()
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from xiaohongshu_mcp import (
    search_notes,
    smart_search_notes, 
    deep_search_and_analyze,
    ensure_browser
)

async def test_basic_search():
    """测试基础搜索功能"""
    print("\n=== 测试基础搜索功能 ===")
    print("搜索关键词: 护肤")
    
    result = await search_notes("护肤", 5)
    print("\n基础搜索结果:")
    print(result)
    print("\n" + "="*50)

async def test_smart_search():
    """测试智能搜索功能"""
    print("\n=== 测试智能搜索功能 ===")
    
    # 测试案例1：护肤相关
    task1 = "我想找一些关于敏感肌护理的笔记，特别是针对换季时期的护肤建议"
    print(f"任务描述: {task1}")
    
    result1 = await smart_search_notes(task1, 8)
    print("\n智能搜索结果:")
    print(result1)
    print("\n" + "="*50)
    
    # 等待一段时间避免请求过于频繁
    await asyncio.sleep(3)
    
    # 测试案例2：穿搭相关
    task2 = "帮我搜索最近流行的日系穿搭趋势，偏向简约风格"
    print(f"\n任务描述: {task2}")
    
    result2 = await smart_search_notes(task2, 6)
    print("\n智能搜索结果:")
    print(result2)
    print("\n" + "="*50)

async def test_deep_search_analyze():
    """测试深度搜索分析功能"""
    print("\n=== 测试深度搜索分析功能 ===")
    
    # 深度分析案例
    task = "分析AI工具在内容创作中的应用趋势"
    print(f"分析任务: {task}")
    print("注意：深度分析会获取每个笔记的详细内容，耗时较长...")
    
    result = await deep_search_and_analyze(task, True, 3)
    print("\n深度分析结果:")
    print(result)
    print("\n" + "="*50)

async def main():
    """主测试函数"""
    print("🤖 小红书智能搜索功能测试")
    print("="*60)
    
    # 确保浏览器已启动
    print("正在初始化浏览器...")
    browser_status = await ensure_browser()
    if not browser_status:
        print("❌ 浏览器初始化失败，请先登录小红书账号")
        return
    
    print("✅ 浏览器初始化成功")
    
    try:
        # 测试基础搜索
        await test_basic_search()
        
        # 等待一段时间
        await asyncio.sleep(2)
        
        # 测试智能搜索
        await test_smart_search()
        
        # 等待一段时间
        await asyncio.sleep(3)
        
        # 测试深度搜索分析（可选，耗时较长）
        user_input = input("\n是否要测试深度搜索分析功能？(y/n): ")
        if user_input.lower() == 'y':
            await test_deep_search_analyze()
        
        print("\n🎉 所有测试完成！")
        
    except Exception as e:
        print(f"\n❌ 测试过程中出错: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("启动智能搜索测试...")
    print("请确保已经登录小红书账号")
    
    # 运行测试
    asyncio.run(main())