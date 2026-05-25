#!/usr/bin/env python3
"""
贾维斯菜谱批量生成脚本
方案A: 用 FinnA 模型列菜名 + 分批生成做法
"""

import os
import sys
import json
import time
import re
import requests

# ====== 配置 ======
FINNA_API_KEY = "app-6OzRGg93TfuDOny9NUnKMvQU"
FINNA_API_BASE = "https://www.finna.com.cn/v1"
FINNA_MODEL = "qwen3-32b"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RECIPES_FILE = os.path.join(BASE_DIR, "data", "recipes.json")
BATCH_SIZE = 5
MAX_RETRIES = 3


def call_model(prompt, temperature=0.7, max_tokens=4096):
    """调用 FinnA API"""
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.post(
                f"{FINNA_API_BASE}/chat/completions",
                headers={
                    "Authorization": f"Bearer {FINNA_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": FINNA_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": False,
                    "extra_body": {"enable_thinking": False},
                },
                timeout=60,
            )
            data = resp.json()
            if "choices" in data and data["choices"]:
                return data["choices"][0]["message"]["content"].strip()
            else:
                error_msg = data.get("error", str(data))
                print(f"  [尝试 {attempt+1}/{MAX_RETRIES}] API返回异常: {error_msg[:200]}")
        except Exception as e:
            print(f"  [尝试 {attempt+1}/{MAX_RETRIES}] API调用失败: {e}")
        if attempt < MAX_RETRIES - 1:
            time.sleep(3)
    return None


def generate_dish_list():
    """第一步：生成300+道家常素菜名清单"""
    print("=" * 60)
    print("第一步：生成300+道家常素菜名清单...")
    print("=" * 60)

    prompt = """你是一位中国烹饪专家。请列出300道以上最经典的中国家常素菜菜名。

要求：
1. 必须是素菜（无肉、无海鲜），鸡蛋和奶制品可以包含
2. 涵盖以下类别：凉菜、热菜、汤羹、主食、小吃
3. 包含各种常见食材：豆腐、豆制品、菌菇、叶菜、根茎类、瓜果类、蛋类、豆类等
4. 菜名要具体、经典、家常
5. 必须输出纯JSON数组格式，不要任何markdown标记、不要```json

输出格式示例：
["菜名1", "菜名2", "菜名3", ...]

请直接输出JSON数组，开始。"""

    result = call_model(prompt, temperature=0.3, max_tokens=8192)
    if not result:
        print("无法生成菜名列表")
        return []

    # 清理输出
    result = re.sub(r'```(?:json)?\s*', '', result).strip()
    start = result.find('[')
    end = result.rfind(']')
    if start >= 0 and end > start:
        result = result[start:end+1]

    try:
        dishes = json.loads(result)
        if not isinstance(dishes, list):
            raise ValueError("不是数组")
        print(f"成功生成 {len(dishes)} 道菜名")
        return dishes
    except json.JSONDecodeError as e:
        print(f"JSON解析失败: {e}")
        print(f"原始输出前500字:\n{result[:500]}")
        return []


def generate_recipes_batch(dishes_batch):
    """生成一批菜谱（5道）"""
    dishes_json = json.dumps(dishes_batch, ensure_ascii=False)
    brace_open = "{"
    brace_close = "}"

    prompt = f"""你是一位中国烹饪大厨。请为以下素菜生成详细的菜谱。

菜名列表: {dishes_json}

请为每一道菜生成JSON格式的菜谱，输出为JSON数组。

每道菜的格式:
{brace_open}
  "name": "菜名",
  "category": "分类（凉菜/热菜/汤羹/主食/小吃）",
  "difficulty": "难度（简单/中等/困难）",
  "time": "烹饪时间（如：15分钟）",
  "ingredients": ["食材1", "食材2", ...],
  "steps": ["步骤1", "步骤2", ...],
  "tips": "小贴士（可选）",
  "tags": ["标签1", "标签2", ...]
{brace_close}

要求：
1. 食材合理，步骤清晰可操作
2. 每个步骤用一句话说明，一般3-6步
3. 只输出纯JSON数组，不要markdown标记
4. 不要省略任何菜，list中每道菜都要有对应条目

输出:"""

    result = call_model(prompt, temperature=0.7, max_tokens=4096)
    if not result:
        return []

    # 清理输出
    result = re.sub(r'```(?:json)?\s*', '', result).strip()
    start = result.find('[')
    end = result.rfind(']')
    if start >= 0 and end > start:
        result = result[start:end+1]

    try:
        recipes = json.loads(result)
        if not isinstance(recipes, list):
            raise ValueError("不是数组")
        valid = [r for r in recipes if r.get("name")]
        if len(valid) < len(recipes):
            print(f"  {len(recipes)-len(valid)} 道菜缺少name字段，已过滤")
        print(f"  生成了 {len(valid)} 道菜谱")
        return valid
    except json.JSONDecodeError as e:
        print(f"  JSON解析失败: {e}")
        print(f"  原始输出前300字: {result[:300]}")
        return []


def load_existing():
    """加载已有的菜谱"""
    if os.path.exists(RECIPES_FILE):
        try:
            with open(RECIPES_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    existing_names = {r.get("name") for r in data if r.get("name")}
                    print(f"已有 {len(data)} 道菜谱")
                    return data, existing_names
        except Exception as e:
            print(f"读取已有菜谱失败: {e}")
    return [], set()


def save_recipes(recipes):
    """保存菜谱"""
    os.makedirs(os.path.dirname(RECIPES_FILE), exist_ok=True)
    with open(RECIPES_FILE, 'w', encoding='utf-8') as f:
        json.dump(recipes, f, ensure_ascii=False, indent=2)
    print(f"已保存 {len(recipes)} 道菜谱")


def main():
    print("贾维斯家常素菜谱批量生成工具")
    print()

    # 第一步：生成菜名列表
    all_dishes = generate_dish_list()
    if not all_dishes:
        print("无法生成菜名列表，退出")
        return

    # 保存菜名列表
    dishes_file = os.path.join(BASE_DIR, "data", "dish_names.json")
    os.makedirs(os.path.dirname(dishes_file), exist_ok=True)
    with open(dishes_file, 'w', encoding='utf-8') as f:
        json.dump(all_dishes, f, ensure_ascii=False, indent=2)
    print(f"菜名列表已保存到 {dishes_file}")

    # 第二步：加载已有菜谱，去重
    existing_recipes, existing_names = load_existing()
    new_dishes = [d for d in all_dishes if d not in existing_names]
    print(f"\n需要生成 {len(new_dishes)} 道新菜谱（已去重）")

    if not new_dishes:
        print("所有菜谱已存在！")
        save_recipes(existing_recipes)
        return

    # 第三步：分批生成
    all_recipes = existing_recipes.copy()
    total_batches = (len(new_dishes) + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"开始分批生成（每批{BATCH_SIZE}道，共{total_batches}批）...\n")

    for i in range(0, len(new_dishes), BATCH_SIZE):
        batch = new_dishes[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1

        print(f"--- 第 {batch_num}/{total_batches} 批 ---")
        print(f"  菜名: {', '.join(batch[:3])}{'...' if len(batch) > 3 else ''}")

        recipes = generate_recipes_batch(batch)
        if recipes:
            all_recipes.extend(recipes)
            save_recipes(all_recipes)
        else:
            print(f"  第{batch_num}批生成失败，跳过")

        if batch_num < total_batches:
            wait = 3
            print(f"  等待{wait}秒...")
            time.sleep(wait)

    # 最终保存
    save_recipes(all_recipes)
    print(f"\n完成！共生成 {len(all_recipes)} 道菜谱")


if __name__ == "__main__":
    main()