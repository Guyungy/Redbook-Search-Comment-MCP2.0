# 小红书自动搜索评论工具（MCP Server 2.0）

一款基于 Playwright 开发的小红书自动化工具，作为 MCP Server 可接入 Claude for Desktop 等 MCP 客户端，实现智能搜索、内容获取和评论发布功能。

## 主要功能

### 1. 用户登录
- 持久化登录，扫码登录后保存登录状态
- 自动检测登录状态，无需重复登录

### 2. 内容搜索与获取
- **搜索笔记**：根据关键词搜索小红书笔记，可指定返回数量
- **获取笔记内容**：提取笔记标题、作者、发布时间和正文内容
- **获取评论**：获取笔记的评论信息，包括评论者、内容和时间

### 3. 智能评论
- **内容分析**：自动分析笔记领域（美妆、穿搭、美食、旅行等8个领域）
- **AI评论生成**：结合 MCP 客户端的 AI 能力生成自然评论
- **多种评论类型**：
  - 引流型：引导用户关注或私聊
  - 点赞型：简单互动获取好感
  - 咨询型：以问题形式增加互动
  - 专业型：展示专业知识建立权威

## 安装方法

### 1. 环境准备
确保系统已安装 Python 3.8 或更高版本。

### 2. 克隆项目
```bash
git clone <项目地址>
cd Redbook-Search-Comment-MCP2.0
```

### 3. 创建虚拟环境
```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
.\venv\Scripts\activate
# Mac/Linux
source venv/bin/activate
```

### 4. 安装依赖
```bash
pip install -r requirements.txt
playwright install
```

### 5. MCP 配置
在 Claude for Desktop 的配置文件中添加：

```json
{
    "mcpServers": {
        "xiaohongshu MCP": {
            "command": "C:\\Users\\4AM\\Documents\\GitHub\\Redbook-Search-Comment-MCP2.0\\venv\\Scripts\\python.exe",
            "args": [
                "C:\\Users\\4AM\\Documents\\GitHub\\Redbook-Search-Comment-MCP2.0\\xiaohongshu_mcp.py",
                "--stdio"
            ]
        }
    }
}
```

**注意**：请将路径替换为你的实际项目路径。

## 使用方法

### 1. 启动服务
配置好 MCP 后，在 Claude for Desktop 中连接服务器。

### 2. 基本操作

#### 登录小红书
```
帮我登录小红书账号
```

#### 搜索笔记
```
帮我搜索小红书笔记，关键词为：美食
帮我搜索小红书笔记，关键词为旅游，返回10条结果
```

#### 获取笔记内容
```
帮我获取这个笔记的内容：https://www.xiaohongshu.com/explore/xxxx
```

#### 获取笔记评论
```
帮我获取这个笔记的评论：https://www.xiaohongshu.com/explore/xxxx
```

#### 发布智能评论
```
帮我为这个笔记写一条引流评论：https://www.xiaohongshu.com/explore/xxxx
帮我为这个笔记写一条专业评论：https://www.xiaohongshu.com/explore/xxxx
```

### 3. 评论类型说明
- **引流**：引导用户关注或私聊，增加粉丝互动
- **点赞**：简单互动获取好感，提升曝光率
- **咨询**：以问题形式增加互动，引发博主回复
- **专业**：展示专业知识建立权威，建立专业形象

## 项目结构

```
Redbook-Search-Comment-MCP2.0/
├── xiaohongshu_mcp.py      # 主程序文件
├── requirements.txt        # 依赖包列表
├── test_mcp.py            # 测试脚本
└── README.md              # 说明文档
```

## 注意事项

1. 首次使用需要手动扫码登录小红书
2. 请遵守小红书的使用条款和社区规范
3. 建议合理控制评论频率，避免被平台限制
4. 确保网络连接稳定，避免操作中断

## 常见问题

**Q: 提示 Playwright 浏览器不存在？**
A: 运行 `playwright install` 安装浏览器。

**Q: 登录后仍提示未登录？**
A: 检查网络连接，重新运行登录命令。

**Q: 无法获取笔记内容？**
A: 确认笔记链接有效，部分私密笔记可能无法访问。

---

> 本项目基于 [JonaFly/RednoteMCP](https://github.com/JonaFly/RednoteMCP.git) 优化开发，感谢原作者的贡献！
