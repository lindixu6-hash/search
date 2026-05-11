# ============================================
# 导入必要的库
# ============================================

# flask - Web 框架，用来创建网页和处理请求
from flask import Flask, render_template, request, jsonify

# dotenv - 用来读取 .env 文件中的环境变量
from dotenv import load_dotenv

# os - 用来读取环境变量
import os

# requests - 用来发送 HTTP 请求（调用 Tavily API）
import requests

# openai - 用来调用大模型（DeepSeek 兼容 OpenAI 格式）
from openai import OpenAI


# ============================================
# 初始化
# ============================================

# 创建 Flask 应用实例
app = Flask(__name__)

# 加载 .env 文件中的环境变量到系统环境中
# override=True 确保覆盖系统环境变量中的旧值
load_dotenv(override=True)


# ============================================
# 初始化大模型客户端
# ============================================

# 创建 OpenAI 客户端，配置为使用 Kimi
# [注意] 这里使用 Kimi 的 API Key 和地址
client = OpenAI(
    api_key=os.getenv("KIMI_API_KEY"),         # 从环境变量读取 API Key
    base_url=os.getenv("KIMI_BASE_URL")        # Kimi 的 API 地址
)

# 打印启动信息，方便调试
print("=" * 50)
print("AI 搜索助手启动中...")
print(f"使用模型: {os.getenv('KIMI_MODEL')}")
print("=" * 50)


# ============================================
# 辅助函数 - 实现核心搜索逻辑
# ============================================

def generate_keywords(query, previous_results, round_num):
    """
    让大模型根据用户问题和之前的搜索结果，生成新的搜索关键词

    参数:
        query: 用户的问题
        previous_results: 之前搜索到的结果
        round_num: 当前是第几轮

    返回:
        生成的关键词字符串
    """

    # 构建提示词
    # 根据是第几轮，提示词会有所不同
    if round_num == 0:
        # 第一轮：根据用户问题生成关键词
        prompt = f"""请将以下用户问题转换为搜索引擎能理解的关键词。

用户问题: {query}

要求:
1. 提取 3-5 个核心关键词
2. 关键词之间用空格分隔
3. 只返回关键词，不要解释

关键词:"""
    else:
        # 后续轮：根据已有结果，生成新的搜索方向
        previous_summary = f"已搜索 {len(previous_results)} 条结果" if previous_results else "无结果"
        prompt = f"""用户问题: {query}

{previous_summary}

上一轮搜索结果不够充分，请生成新的搜索关键词，换个角度搜索。

要求:
1. 生成 3-5 个新的关键词
2. 从不同角度扩展搜索范围
3. 只返回关键词，不要解释

新关键词:"""

    try:
        # 调用 DeepSeek API
        response = client.chat.completions.create(
            model=os.getenv("KIMI_MODEL"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7  # 稍微有点创造性，生成不同角度的关键词
        )

        # 提取返回的关键词
        keywords = response.choices[0].message.content.strip()
        return keywords

    except Exception as e:
        print(f"生成关键词失败: {e}")
        # 如果失败，返回原始问题作为关键词
        return query


def call_search_api(keywords):
    """
    调用 Tavily 搜索引擎 API
    """

    try:
        # 构建 API 请求
        headers = {
            "Authorization": f"Bearer {os.getenv('TAVILY_API_KEY')}",
            "Content-Type": "application/json"
        }

        # Tavily API 的请求格式
        data = {
            "query": keywords,
            "max_results": 10,
            "search_depth": "basic"
        }

        print(f"  → 调用 Tavily API，关键词: {keywords}")

        # 发送 POST 请求
        response = requests.post(
            os.getenv("TAVILY_URL"),
            headers=headers,
            json=data,
            timeout=30
        )

        # 打印状态码和响应内容（调试用）
        print(f"  → API 状态码: {response.status_code}")

        # 解析返回的 JSON
        result = response.json()

        # 🔍 调试：打印 API 返回的数据结构
        print(f"  → API 返回的键: {result.keys()}")
        print(f"  → results 内容长度: {len(result.get('results', []))}")

        # 提取搜索结果
        search_results = result.get('results', [])
        print(f"  → 实际返回 {len(search_results)} 条结果")

        return search_results

    except Exception as e:
        print(f"  ❌ 搜索 API 调用失败: {e}")
        return []


def check_results_quality(results, previous_count):
    """
    检查搜索结果是否足够好，是否需要继续搜索

    参数:
        results: 本轮搜索到的结果
        previous_count: 之前已有的结果数量

    返回:
        True - 结果足够，可以停止
        False - 结果不足，需要继续搜索
    """

    # 检查1: 结果数量太少（少于3条），继续搜索
    if len(results) < 3:
        return False

    # 检查2: 总结果数量已经很多了（超过15条），可以停止
    # 避免搜索太多结果导致处理时间过长
    if previous_count + len(results) > 15:
        return True

    # 检查3: 用 AI 判断结果质量
    # 只取前3条结果，节省 token
    sample_results = results[:3]
    sample_text = "\n".join([
        f"标题: {r.get('title', '')}\n内容: {r.get('content', '')[:100]}"
        for r in sample_results
    ])

    prompt = f"""判断以下搜索结果是否能够回答用户的问题。

搜索结果:
{sample_text}

问题：这些结果是否相关、是否有实质内容？

回答规则:
- 如果结果相关且有实质内容，返回 "yes"
- 如果结果不相关或内容空洞，返回 "no"
- 只返回 yes 或 no，不要解释

判断:"""

    try:
        response = client.chat.completions.create(
            model=os.getenv("KIMI_MODEL"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )

        judgment = response.choices[0].message.content.strip().lower()

        # 如果 AI 判断结果足够，返回 True
        return "yes" in judgment

    except Exception as e:
        print(f"结果质量检查失败: {e}")
        # 如果检查失败，默认返回 True，避免无限循环
        return True


def generate_report(query, all_results):
    """
    基于所有搜索结果，生成最终的研究报告

    参数:
        query: 用户的问题
        all_results: 所有搜索结果的列表

    返回:
        生成的报告（Markdown 格式）
    """

    # 构建上下文：把所有搜索结果拼接起来
    # 为了节省 token，每个结果只取标题和内容摘要
    context_parts = []
    for i, result in enumerate(all_results, 1):
        title = result.get('title', '无标题')
        content = result.get('content', '')[:200]  # 只取前200字
        url = result.get('url', '')

        context_parts.append(f"""
### 结果 {i}
**标题**: {title}
**链接**: {url}
**摘要**: {content}...
""")

    # 拼接所有结果
    results_context = "\n".join(context_parts)

    # 构建生成报告的提示词
    prompt = f"""你是一个专业的研究助手。请根据以下搜索结果，为用户生成一份详细的研究报告。

用户问题: {query}

搜索结果:
{results_context}

要求:
1. 用 Markdown 格式输出
2. 报告结构：概述、核心要点、详细分析、结论
3. 引用搜索结果时，标注来源编号 [结果1]、[结果2] 等
4. 保持客观，不要编造信息
5. 如果搜索结果不足以回答问题，如实说明

请开始生成报告:
"""

    try:
        response = client.chat.completions.create(
            model=os.getenv("KIMI_MODEL"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5  # 介于创造性和准确性之间
        )

        report = response.choices[0].message.content.strip()
        return report

    except Exception as e:
        print(f"生成报告失败: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return f"抱歉，生成报告时出现错误：{type(e).__name__}: {e}"


# ============================================
# 路由函数 - 处理网页请求
# ============================================

# 首页路由 - 用户访问 http://localhost:3000 时触发
@app.route('/')
def index():
    """
    渲染并返回首页 HTML
    templates/index.html 文件会在下一步创建
    """
    return render_template('index.html')


# 搜索路由 - 用户点击"搜索"按钮时触发
@app.route('/search', methods=['POST'])
def search():
    """
    处理搜索请求的核心函数

    流程：
    1. 获取用户输入的问题
    2. 多轮搜索直到结果足够
    3. 生成最终报告
    4. 返回结果给前端
    """

    # 获取前端发送的 JSON 数据
    data = request.json

    # 提取用户输入的搜索问题
    user_query = data.get('query', '')

    # 如果用户没输入问题，返回错误
    if not user_query:
        return jsonify({'error': '请输入搜索问题'}), 400

    print(f"\n收到搜索请求: {user_query}")

    # ============================================
    # 多轮搜索：循环直到结果足够或达到上限
    # ============================================

    # 存储所有搜索结果
    all_results = []

    # 当前是第几轮搜索
    search_round = 0

    # 最多搜索 3 轮（避免无限循环）
    max_rounds = 3

    # 循环搜索
    while search_round < max_rounds:
        print(f"\n--- 第 {search_round + 1} 轮搜索 ---")

        # [步骤A] 让 AI 拆解/生成关键词
        keywords = generate_keywords(user_query, all_results, search_round)
        print(f"生成的关键词: {keywords}")

        # [步骤B] 调用 Tavily 搜索 API
        search_results = call_search_api(keywords)
        print(f"搜索到 {len(search_results)} 条结果")

        # [步骤C] 检查结果是否足够
        if check_results_quality(search_results, len(all_results)):
            # 结果足够，把结果加入总集，结束循环
            all_results.extend(search_results)
            print("结果质量满足要求，停止搜索")
            break
        else:
            # 结果不够，加入总集，继续下一轮
            all_results.extend(search_results)
            search_round += 1
            print(f"结果不足，继续第 {search_round + 1} 轮...")

    # ============================================
    # 生成最终报告
    # ============================================

    print(f"\n搜索完成！共 {search_round + 1} 轮，找到 {len(all_results)} 条结果")
    print("正在生成报告...")

    # 调用大模型生成研究报告
    report = generate_report(user_query, all_results)

    # 返回结果给前端
    return jsonify({
        'report': report,                    # 生成的报告
        'search_rounds': search_round + 1,   # 搜索轮数
        'total_results': len(all_results)    # 结果总数
    })


# ============================================
# 启动程序
# ============================================

if __name__ == '__main__':
    # 从环境变量读取端口号，默认 3000
    port = int(os.getenv('PORT', 3000))

    print(f"\n{'='*50}")
    print(f"🚀 服务已启动！")
    print(f"📍 请在浏览器访问: http://localhost:{port}")
    print(f"{'='*50}\n")

    # 启动 Flask 应用
    # debug=True 表示修改代码会自动重载
    app.run(host='0.0.0.0', port=port, debug=True)
