#!/usr/bin/env python3
"""批量扩展菜谱库 — 多品类生成"""
import json, time, re, requests, sys

API_KEY = "app-ULzJbc3OaIN50mZVSU7sAa97"
API_BASE = "https://www.finna.com.cn/v1"
MODEL = "deepseek-v4-flash"

DATA_DIR = "/opt/recipe-app/data" if "linux" in sys.platform else "data"
RECIPES_FILE = f"{DATA_DIR}/recipes.json"

def call_llm(prompt, max_tokens=4096):
    for attempt in range(3):
        try:
            resp = requests.post(
                f"{API_BASE}/chat/completions",
                headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7, "max_tokens": max_tokens,
                    "stream": False, "extra_body": {"enable_thinking": False}
                },
                timeout=90
            )
            data = resp.json()
            if "choices" in data and data["choices"]:
                return data["choices"][0]["message"]["content"].strip()
            print(f"  API error: {data.get('error', str(data))[:200]}")
        except Exception as e:
            print(f"  Attempt {attempt+1} failed: {e}")
        time.sleep(3)
    return None

def generate_category(category_name, count=30):
    """为一个品类生成菜谱"""
    print(f"\n{'='*50}")
    print(f"生成 {category_name} ({count} 道)...")
    
    prompt = f"""你是中国烹饪专家。请生成{count}道经典{category_name}菜谱。

返回纯 JSON 数组，每道菜包含:
- name: 菜名
- ingredients: 食材列表(含用量)
- steps: 步骤列表(每步一句话)
- difficulty: 简单/中等/困难
- time: 预计时间
- category: "{category_name}"

要求:
1. 菜名经典家常，中国人熟知的
2. 食材用量要具体(如"排骨500g"、"生抽2勺")
3. 步骤清晰可操作
4. 难度和时间的分布合理(60%简单,30%中等,10%困难)

只返回 JSON 数组，不要 markdown 标记，不要```json。

输出示例:
[
  {{"name": "红烧排骨", "ingredients": ["排骨500g", "葱2根", "姜3片", "生抽2勺", "老抽1勺", "冰糖20g", "料酒2勺"], "steps": ["排骨冷水焯水捞出", "热油炒糖色至棕红", "倒入排骨翻炒上色", "加葱姜料酒生抽老抽", "加水没过排骨，大火烧开转小火炖40分钟", "大火收汁出锅"], "difficulty": "中等", "time": "60分钟", "category": "{category_name}"}},
  ...
]

直接输出数组，开始。"""

    result = call_llm(prompt, max_tokens=8192)
    if not result:
        print(f"  ❌ 生成失败")
        return []
    
    # Clean + parse
    result = re.sub(r'```(?:json)?\s*', '', result).strip()
    start = result.find('[')
    end = result.rfind(']')
    if start >= 0 and end > start:
        result = result[start:end+1]
    
    try:
        recipes = json.loads(result)
        print(f"  ✅ 生成 {len(recipes)} 道")
        return recipes
    except json.JSONDecodeError as e:
        print(f"  ❌ JSON 解析失败: {e}")
        print(f"  Output preview: {result[:300]}")
        return []

def merge_recipes(existing, new_recipes):
    """合并去重"""
    existing_names = {r["name"] for r in existing}
    added = 0
    for r in new_recipes:
        if r["name"] not in existing_names:
            existing_names.add(r["name"])
            existing.append(r)
            added += 1
    return added

def main():
    # Load existing
    with open(RECIPES_FILE, "r", encoding="utf-8") as f:
        recipes = json.load(f)
    original_count = len(recipes)
    print(f"当前菜谱: {original_count} 道")
    
    # Categories to expand
    categories = [
        ("肉类硬菜", 30),
        ("水产海鲜", 30),
        ("汤羹煲类", 25),
        ("面食主食", 25),
        ("烘焙甜点", 20),
        ("西式料理", 20),
        ("日韩料理", 20),
        ("烧烤小吃", 20),
        ("早餐早点", 20),
        ("饮品类", 15),
    ]
    
    total_added = 0
    for cat_name, count in categories:
        new_recipes = generate_category(cat_name, count)
        if new_recipes:
            added = merge_recipes(recipes, new_recipes)
            total_added += added
            print(f"  → 新增 {added} 道，累计 {len(recipes)} 道")
        
        if len(recipes) >= 500:
            print("\n已达 500 道上限，停止生成")
            break
        
        time.sleep(2)  # Rate limit
    
    # Save
    with open(RECIPES_FILE, "w", encoding="utf-8") as f:
        json.dump(recipes, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*50}")
    print(f"完成! {original_count} → {len(recipes)} 道 (+{total_added})")

if __name__ == "__main__":
    main()
