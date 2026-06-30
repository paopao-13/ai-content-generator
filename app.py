# -*- coding: utf-8 -*-
"""
AI辅助内容生成与批量处理工具
技术栈：Flask + SQLite + OpenAI API
"""

import sqlite3
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect
import openai

# 导入配置（API密钥等）
from config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL

app = Flask(__name__)

# 初始化OpenAI客户端
client = openai.OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL
)

# ========== 数据库初始化 ==========

def init_db():
    conn = sqlite3.connect('content_generator.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS generated_contents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_name TEXT NOT NULL,
            prompt TEXT NOT NULL,
            generated_text TEXT NOT NULL,
            status TEXT DEFAULT 'generated',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# 预设Prompt模板
TEMPLATES = {
    "product_title": {
        "name": "电商标题生成",
        "system_prompt": "你是一个电商文案专家。根据产品描述，生成3个吸引人的标题，每个不超过20字。"
    },
    "social_post": {
        "name": "社媒文案生成",
        "system_prompt": "你是一个社交媒体运营专家。根据主题，生成一段适合发布在小红书/抖音的文案，带话题标签。"
    },
    "tag_generator": {
        "name": "话题标签生成",
        "system_prompt": "你是一个SEO专家。根据内容主题，生成10个相关的话题标签，用#开头。"
    },
    "email_reply": {
        "name": "邮件回复生成",
        "system_prompt": "你是一个商务沟通专家。根据邮件内容，生成一段礼貌、专业的回复。"
    }
}

# ========== 核心功能：调用LLM生成内容 ==========

def generate_content(template_key, user_input):
    template = TEMPLATES.get(template_key, TEMPLATES["product_title"])
    
    messages = [
        {"role": "system", "content": template["system_prompt"]},
        {"role": "user", "content": user_input}
    ]
    
    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"生成失败：{str(e)}"

# ========== 路由 ==========

@app.route('/')
def index():
    return render_template('index.html', templates=TEMPLATES)

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    template_key = data.get('template', 'product_title')
    user_input = data.get('input', '')
    
    if not user_input:
        return jsonify({"error": "请输入内容描述"}), 400
    
    # 调用AI生成
    result = generate_content(template_key, user_input)
    
    # 保存到数据库
    conn = sqlite3.connect('content_generator.db')
    c = conn.cursor()
    c.execute(
        "INSERT INTO generated_contents (template_name, prompt, generated_text) VALUES (?, ?, ?)",
        (TEMPLATES[template_key]["name"], user_input, result)
    )
    conn.commit()
    content_id = c.lastrowid
    conn.close()
    
    return jsonify({
        "id": content_id,
        "result": result,
        "template": TEMPLATES[template_key]["name"]
    })

@app.route('/history')
def history():
    conn = sqlite3.connect('content_generator.db')
    c = conn.cursor()
    c.execute("SELECT * FROM generated_contents ORDER BY created_at DESC LIMIT 50")
    rows = c.fetchall()
    conn.close()
    
    contents = []
    for row in rows:
        contents.append({
            "id": row[0],
            "template_name": row[1],
            "prompt": row[2],
            "generated_text": row[3],
            "status": row[4],
            "created_at": row[5]
        })
    
    return render_template('history.html', contents=contents)

@app.route('/update_status/<int:content_id>', methods=['POST'])
def update_status(content_id):
    data = request.json
    new_status = data.get('status', 'approved')
    
    conn = sqlite3.connect('content_generator.db')
    c = conn.cursor()
    c.execute("UPDATE generated_contents SET status = ? WHERE id = ?", (new_status, content_id))
    conn.commit()
    conn.close()
    
    return jsonify({"success": True})

@app.route('/batch_generate', methods=['POST'])
def batch_generate():
    """批量生成：一次处理多个输入"""
    data = request.json
    template_key = data.get('template', 'product_title')
    inputs = data.get('inputs', [])
    
    results = []
    for user_input in inputs:
        if user_input.strip():
            result = generate_content(template_key, user_input)
            results.append({
                "input": user_input,
                "output": result
            })
    
    return jsonify({"results": results, "count": len(results)})

# ========== 启动 ==========

if __name__ == '__main__':
    init_db()
    print("=" * 50)
    print("AI内容生成工具已启动")
    print("访问 http://127.0.0.1:5000")
    print("=" * 50)
    app.run(debug=True, port=5000)
