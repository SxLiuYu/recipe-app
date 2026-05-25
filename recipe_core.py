"""
Recipe Recommendation — 根据现有食材推荐菜谱
存储常用菜谱 + LLM 动态生成
"""

import json
import os
import random
import re
import requests
from typing import Dict, List, Optional

# ── Data ────────────────────────────────────────
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
RECIPE_FILE = os.path.join(DATA_DIR, "recipes.json")

# ── LLM Config ──────────────────────────────────
FINNA_API_BASE = os.getenv("FINNA_API_BASE", "https://www.finna.com.cn/v1").rstrip("/")
FINNA_KEY_DEEPSEEK = os.getenv("FINNA_KEY_DEEPSEEK", "")
LLM_MODEL = "Pro/deepseek-ai/DeepSeek-V3.1-Terminus"

# ── 内置菜谱库（30个家常菜）─────────────────────
DEFAULT_RECIPES = [
    # ── 素菜 ──
    {"name": "番茄炒蛋", "ingredients": ["番茄", "鸡蛋", "盐", "糖", "油"], "steps": ["番茄切块，鸡蛋打散加少许盐", "热油煎炒鸡蛋，盛出备用", "热油炒番茄出汁，加糖盐调味", "倒入鸡蛋一起翻炒均匀出锅"], "difficulty": "简单", "time": "10分钟"},
    {"name": "鸡蛋炒饭", "ingredients": ["米饭", "鸡蛋", "葱花", "盐", "油"], "steps": ["米饭最好隔夜，打散", "鸡蛋打散煎熟盛出", "热油炒米饭，压散", "加入鸡蛋翻炒，加盐调味，撒葱花出锅"], "difficulty": "简单", "time": "10分钟"},
    {"name": "酸辣土豆丝", "ingredients": ["土豆", "醋", "辣椒", "盐", "蒜", "油"], "steps": ["土豆切丝泡水去淀粉", "热油爆香蒜和辣椒", "大火翻炒土豆丝，加醋加盐", "翻炒几分钟出锅，保持脆感"], "difficulty": "简单", "time": "15分钟"},
    {"name": "拍黄瓜", "ingredients": ["黄瓜", "蒜", "醋", "生抽", "香油", "盐"], "steps": ["黄瓜洗净拍碎切段", "蒜切末", "加所有调料拌匀，放十分钟入味即可"], "difficulty": "简单", "time": "5分钟"},
    {"name": "蒜蓉青菜", "ingredients": ["青菜", "蒜", "盐", "油"], "steps": ["蒜剁成蒜蓉", "热油爆香蒜蓉", "放入青菜快速翻炒，加盐调味", "青菜变软即可出锅"], "difficulty": "简单", "time": "5分钟"},
    {"name": "醋溜白菜", "ingredients": ["白菜", "醋", "干辣椒", "蒜", "盐", "油"], "steps": ["白菜帮切片，叶子撕小块", "热油爆香干辣椒和蒜片", "先炒白菜帮，再放叶子", "加醋、盐大火快炒出锅"], "difficulty": "简单", "time": "10分钟"},
    {"name": "干煸四季豆", "ingredients": ["四季豆", "干辣椒", "花椒", "蒜", "盐", "油"], "steps": ["四季豆去筋掰段", "热油中小火煸至表皮起皱", "爆香干辣椒花椒蒜片", "倒入四季豆加盐翻炒均匀"], "difficulty": "中等", "time": "20分钟"},
    {"name": "地三鲜", "ingredients": ["土豆", "茄子", "青椒", "蒜", "生抽", "盐", "油"], "steps": ["土豆切片，茄子切块，青椒切块", "分别炸/煎土豆和茄子至金黄", "热油爆香蒜", "放入所有食材，加生抽盐大火翻炒出锅"], "difficulty": "中等", "time": "25分钟"},
    {"name": "麻婆豆腐", "ingredients": ["豆腐", "肉末", "豆瓣酱", "花椒粉", "葱花", "生抽"], "steps": ["豆腐切块焯水", "热油炒肉末至变色", "加豆瓣酱炒出红油", "加水烧开放豆腐，煮5分钟", "勾芡出锅，撒花椒粉和葱花"], "difficulty": "中等", "time": "20分钟"},
    {"name": "红烧茄子", "ingredients": ["茄子", "蒜", "生抽", "老抽", "糖", "葱花"], "steps": ["茄子切条，撒盐腌制10分钟挤水", "热油煎茄子至软", "加蒜末炒香", "加生抽老抽糖和少许水，焖2分钟", "收汁撒葱花出锅"], "difficulty": "简单", "time": "20分钟"},
    {"name": "手撕包菜", "ingredients": ["包菜", "干辣椒", "蒜", "醋", "生抽", "盐", "油"], "steps": ["包菜手撕成块洗净沥干", "热油爆香干辣椒蒜片", "大火翻炒包菜至断生", "加醋、生抽、盐调味出锅"], "difficulty": "简单", "time": "10分钟"},
    {"name": "蚝油生菜", "ingredients": ["生菜", "蚝油", "蒜", "生抽", "油"], "steps": ["生菜洗净", "水开下生菜烫30秒捞出", "热油爆香蒜末", "加蚝油生抽炒匀淋在生菜上"], "difficulty": "简单", "time": "5分钟"},
    # ── 荤菜 ──
    {"name": "红烧排骨", "ingredients": ["排骨", "葱姜", "生抽", "老抽", "糖", "料酒"], "steps": ["排骨冷水下锅焯水捞出", "热油炒糖色，倒入排骨上色", "加葱姜料酒生抽老抽，加水没过", "大火烧开转小火炖40分钟，大火收汁"], "difficulty": "中等", "time": "60分钟"},
    {"name": "可乐鸡翅", "ingredients": ["鸡翅", "可乐", "姜", "生抽", "老抽", "料酒"], "steps": ["鸡翅两面划刀，加料酒生抽腌制15分钟", "热油煎鸡翅至两面金黄", "倒入可乐没过鸡翅", "加姜片、少许老抽，中小火炖15分钟", "大火收汁即可"], "difficulty": "简单", "time": "30分钟"},
    {"name": "回锅肉", "ingredients": ["五花肉", "青蒜", "豆瓣酱", "姜", "料酒", "糖"], "steps": ["五花肉冷水下锅加姜料酒煮20分钟", "捞出切薄片", "热油煸炒肉片至卷曲出油", "加豆瓣酱炒出红油", "加青蒜段翻炒，加少许糖调味出锅"], "difficulty": "中等", "time": "35分钟"},
    {"name": "宫保鸡丁", "ingredients": ["鸡胸肉", "花生米", "干辣椒", "花椒", "葱", "醋", "糖", "生抽", "淀粉"], "steps": ["鸡胸肉切丁，加料酒生抽淀粉腌制", "调碗汁：醋糖生抽淀粉水拌匀", "炸花生米备用", "热油滑炒鸡丁至变白盛出", "爆香干辣椒花椒葱段，倒入鸡丁", "加碗汁翻炒，最后加花生米出锅"], "difficulty": "中等", "time": "25分钟"},
    {"name": "青椒肉丝", "ingredients": ["青椒", "猪肉", "姜", "生抽", "料酒", "淀粉", "盐", "油"], "steps": ["猪肉切丝，加料酒生抽淀粉腌制", "青椒切丝", "热油滑炒肉丝至变色盛出", "爆香姜丝，炒青椒至断生", "倒入肉丝，加盐生抽翻炒均匀"], "difficulty": "简单", "time": "15分钟"},
    {"name": "鱼香肉丝", "ingredients": ["猪肉", "木耳", "胡萝卜", "青椒", "豆瓣酱", "醋", "糖", "生抽", "淀粉"], "steps": ["猪肉切丝腌制，木耳胡萝卜青椒切丝", "调鱼香汁：醋2糖1生抽1淀粉水拌匀", "热油滑炒肉丝盛出", "爆香豆瓣酱，炒胡萝卜木耳青椒", "倒入肉丝和鱼香汁，大火翻炒收汁"], "difficulty": "中等", "time": "25分钟"},
    {"name": "红烧肉", "ingredients": ["五花肉", "葱姜", "八角", "桂皮", "生抽", "老抽", "冰糖", "料酒"], "steps": ["五花肉切块焯水", "热油炒冰糖至焦糖色", "下五花肉上色", "加葱姜八角桂皮料酒生抽老抽", "加热水没过，大火烧开转小火炖1小时", "大火收汁即可"], "difficulty": "中等", "time": "90分钟"},
    {"name": "糖醋里脊", "ingredients": ["猪里脊", "醋", "糖", "番茄酱", "面粉", "鸡蛋", "淀粉", "盐"], "steps": ["里脊切条，加盐料酒腌制", "调面糊：面粉鸡蛋淀粉水搅匀", "里脊裹面糊，六成热油炸至金黄", "调汁：番茄酱糖醋水淀粉拌匀", "热锅炒汁至浓稠，倒入炸好的里脊裹匀"], "difficulty": "中等", "time": "30分钟"},
    {"name": "蒜苔炒肉", "ingredients": ["蒜苔", "猪肉", "生抽", "料酒", "淀粉", "盐", "油"], "steps": ["猪肉切丝腌制", "蒜苔切段", "热油滑炒肉丝盛出", "炒蒜苔至变软", "倒入肉丝，加盐生抽翻炒均匀"], "difficulty": "简单", "time": "15分钟"},
    {"name": "西红柿牛腩", "ingredients": ["牛腩", "番茄", "葱姜", "番茄酱", "生抽", "盐"], "steps": ["牛腩切块焯水", "番茄切块", "热油炒番茄出汁，加番茄酱", "放入牛腩，加热水没过", "加葱姜生抽，小火炖1.5小时", "加盐调味出锅"], "difficulty": "中等", "time": "120分钟"},
    {"name": "土豆炖牛肉", "ingredients": ["牛腩", "土豆", "胡萝卜", "葱姜", "生抽", "老抽", "八角", "盐"], "steps": ["牛腩切块焯水", "热油炒葱姜八角出香", "下牛腩翻炒，加生抽老抽", "加水没过，大火烧开转小火炖1小时", "加土豆胡萝卜块，继续炖20分钟", "加盐调味收汁"], "difficulty": "中等", "time": "90分钟"},
    {"name": "葱爆羊肉", "ingredients": ["羊肉", "大葱", "生抽", "料酒", "孜然", "盐", "油"], "steps": ["羊肉切薄片，加料酒生抽腌制", "大葱切斜段", "热油大火爆炒羊肉至变色", "加葱段翻炒", "加孜然盐调味，迅速出锅"], "difficulty": "简单", "time": "10分钟"},
    # ── 汤 ──
    {"name": "紫菜蛋花汤", "ingredients": ["紫菜", "鸡蛋", "葱花", "盐", "香油"], "steps": ["水烧开", "鸡蛋打散", "水开后淋入蛋液搅成蛋花", "关火，放入紫菜，加盐和香油", "撒葱花出锅"], "difficulty": "简单", "time": "5分钟"},
    {"name": "番茄蛋花汤", "ingredients": ["番茄", "鸡蛋", "葱花", "盐", "油"], "steps": ["番茄切块", "热油炒番茄至出汁", "加水烧开", "淋入蛋液搅成蛋花", "加盐调味，撒葱花出锅"], "difficulty": "简单", "time": "10分钟"},
    {"name": "玉米排骨汤", "ingredients": ["排骨", "玉米", "胡萝卜", "姜", "盐"], "steps": ["排骨焯水", "玉米切段，胡萝卜切块", "排骨玉米姜片放入锅中，加足量水", "大火烧开转小火炖1小时", "加胡萝卜再炖20分钟", "加盐调味即可"], "difficulty": "简单", "time": "90分钟"},
    # ── 凉菜 ──
    {"name": "凉拌三丝", "ingredients": ["粉丝", "黄瓜", "胡萝卜", "蒜", "醋", "生抽", "香油", "辣椒油"], "steps": ["粉丝泡软焯水过凉", "黄瓜胡萝卜切丝", "蒜切末", "所有食材放大碗，加调料拌匀即可"], "difficulty": "简单", "time": "10分钟"},
    {"name": "皮蛋豆腐", "ingredients": ["皮蛋", "内酯豆腐", "葱花", "生抽", "香油", "醋"], "steps": ["豆腐切块摆盘", "皮蛋切碎放在豆腐上", "撒葱花", "淋生抽醋香油调成的汁即可"], "difficulty": "简单", "time": "5分钟"},
    {"name": "口水鸡", "ingredients": ["鸡腿", "葱花", "蒜", "辣椒油", "花椒油", "生抽", "醋", "糖", "花生碎"], "steps": ["鸡腿冷水下锅煮熟捞出过凉", "去骨切块摆盘", "调汁：辣椒油花椒油生抽醋糖蒜末拌匀", "浇在鸡肉上，撒葱花花生碎"], "difficulty": "中等", "time": "30分钟"},
]

# ── Helper: LLM ─────────────────────────────────
def _call_finna_llm(system_prompt: str, user_message: str, max_tokens: int = 1024) -> Optional[str]:
    """调用 FinnA DeepSeek API"""
    if not FINNA_KEY_DEEPSEEK:
        return None
    url = f"{FINNA_API_BASE}/chat/completions"
    headers = {
        "Authorization": f"Bearer {FINNA_KEY_DEEPSEEK}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.8,
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        if resp.status_code != 200:
            return None
        content = resp.json()["choices"][0]["message"]["content"].strip()
        return content
    except Exception:
        return None


def _parse_llm_recipe(text: str) -> Optional[dict]:
    """从 LLM 返回文本中提取 JSON 菜谱"""
    # 尝试找 JSON 块
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        text = m.group(1)
    # 直接尝试解析
    try:
        data = json.loads(text)
        if all(k in data for k in ["name", "steps", "ingredients"]):
            return data
    except json.JSONDecodeError:
        pass
    # 用大括号范围暴力解析
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            data = json.loads(text[start:end+1])
            if all(k in data for k in ("name", "steps", "ingredients")):
                return data
        except json.JSONDecodeError:
            pass
    return None


# ── Data CRUD ───────────────────────────────────
def _ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)


def _load_recipes() -> dict:
    if not os.path.exists(RECIPE_FILE):
        data = {"recipes": DEFAULT_RECIPES.copy()}
        _save_recipes(data)
        return data
    try:
        with open(RECIPE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"recipes": DEFAULT_RECIPES.copy()}


def _save_recipes(data: dict) -> bool:
    _ensure_data_dir()
    try:
        with open(RECIPE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        return False


def add_recipe(name: str, ingredients: List[str], steps: List[str],
               difficulty: str = "简单", time: str = None) -> str:
    """添加新菜谱"""
    data = _load_recipes()
    for r in data["recipes"]:
        if r["name"] == name:
            return f"{name} 菜谱已经存在"

    recipe = {
        "name": name,
        "ingredients": ingredients,
        "steps": steps,
        "difficulty": difficulty,
        "time": time or "未知"
    }
    data["recipes"].append(recipe)
    _save_recipes(data)
    return f"✅ 已添加菜谱：{name}"


def search_recipe_by_ingredient(ingredient: str) -> str:
    """根据食材搜索菜谱"""
    data = _load_recipes()
    matches = []
    for r in data["recipes"]:
        for ing in r["ingredients"]:
            if ingredient.lower() in ing.lower():
                matches.append(r)
                break
    if not matches:
        return f"找不到包含「{ingredient}」的菜谱"
    lines = [f"🔍 找到 {len(matches)} 个包含「{ingredient}」的菜谱："]
    for i, r in enumerate(matches, 1):
        lines.append(f"{i}. **{r['name']}** ({r['difficulty']}, {r['time']})")
        lines.append(f"   食材：{', '.join(r['ingredients'])}")
    return "\n".join(lines)


def get_recipe(name: str) -> Optional[str]:
    """获取完整菜谱做法（本地查找 + LLM 兜底）"""
    data = _load_recipes()
    for r in data["recipes"]:
        if r["name"] == name or name.lower() in r["name"].lower():
            return _format_recipe(r)
    # LLM 兜底生成
    llm_result = generate_recipe_llm(name, [])
    if llm_result:
        return llm_result
    return None


def _format_recipe(r: dict) -> str:
    lines = [f"🍳 {r['name']}"]
    lines.append(f"难度：{r['difficulty']}  预计时间：{r['time']}")
    lines.append(f"食材：{', '.join(r['ingredients'])}")
    lines.append("")
    lines.append("做法：")
    for j, step in enumerate(r["steps"], 1):
        lines.append(f"{j}. {step}")
    return "\n".join(lines)


def random_recipe() -> str:
    """随机推荐一个菜谱"""
    data = _load_recipes()
    if not data["recipes"]:
        return "还没有保存任何菜谱"
    recipe = random.choice(data["recipes"])
    return _format_recipe(recipe)


def list_all_recipes() -> str:
    """列出所有菜谱"""
    data = _load_recipes()
    recipes = data["recipes"]
    if not recipes:
        return "还没有保存任何菜谱"
    lines = [f"📖 已保存 {len(recipes)} 个菜谱："]
    for i, r in enumerate(recipes, 1):
        lines.append(f"{i}. {r['name']} ({r['difficulty']}, {r['time']})")
    return "\n".join(lines)


# ── LLM 生成 ────────────────────────────────────
def generate_recipe_llm(name: str, ingredients: List[str]) -> Optional[str]:
    """用 LLM 生成菜谱（本地没有时兜底）"""
    sys_prompt = """你是一个中餐菜谱专家。请根据用户提供的菜名和/或食材，生成一个家常菜谱。
请以 JSON 格式返回，包含以下字段：
- name（菜名）
- ingredients（食材列表，中文）
- steps（步骤列表，中文，每步一句话）
- difficulty（难度：简单/中等/困难）
- time（预计时间，如"20分钟"）

只返回 JSON，不要多余解释。

示例：
{"name": "醋溜白菜", "ingredients": ["白菜", "醋", "干辣椒", "蒜", "盐", "油"], "steps": ["白菜切片", "热油爆香干辣椒蒜片", "大火翻炒白菜", "加醋盐调味出锅"], "difficulty": "简单", "time": "10分钟"}"""

    if name and not ingredients:
        user_msg = f"菜名：{name}"
    else:
        ing_str = "、".join(ingredients)
        user_msg = f"菜名：{name or '家常菜'}，食材：{ing_str}"

    text = _call_finna_llm(sys_prompt, user_msg, max_tokens=1024)
    if not text:
        return None

    recipe = _parse_llm_recipe(text)
    if recipe:
        return f"🤖 AI 生成的「{recipe['name']}」做法：\n\n" + _format_recipe(recipe)
    return f"🤖 AI 生成的菜谱：\n\n{text}"


# ── Route Functions ─────────────────────────────

def recommend_recipe(ingredients: List[str], cuisine: str = "") -> dict:
    """
    推荐菜谱（路由入口函数）
    1. 本地搜索匹配食材的菜谱
    2. 没有匹配则 LLM 生成
    """
    data = _load_recipes()
    # 本地优先：查找包含至少一种食材的菜谱
    local_matches = []
    for r in data["recipes"]:
        if not ingredients:
            local_matches.append(r)
        else:
            for ing in ingredients:
                if any(ing.lower() in ri.lower() for ri in r["ingredients"]):
                    local_matches.append(r)
                    break
    if local_matches:
        # 按匹配食材数排序
        if ingredients:
            def score(r):
                return sum(1 for i in ingredients if any(i.lower() in ri.lower() for ri in r["ingredients"]))
            local_matches.sort(key=score, reverse=True)
        recipe = local_matches[0]
        return {
            "source": "local",
            "name": recipe["name"],
            "ingredients": recipe["ingredients"],
            "steps": recipe["steps"],
            "difficulty": recipe["difficulty"],
            "time": recipe["time"],
        }
    # LLM 兜底
    sys_prompt = """你是一个中餐菜谱专家。根据用户提供的食材，推荐一道合适的家常菜。
返回 JSON 格式：{"name": "...", "ingredients": [...], "steps": [...], "difficulty": "...", "time": "..."}
只返回 JSON。"""
    user_msg = f"食材：{'、'.join(ingredients)}"
    if cuisine:
        user_msg += f"\n偏好：{cuisine}菜系"
    text = _call_finna_llm(sys_prompt, user_msg)
    if text:
        recipe = _parse_llm_recipe(text)
        if recipe:
            return {"source": "llm", **recipe}
    # 最后兜底
    return {
        "source": "default",
        "name": "番茄炒蛋",
        "ingredients": ["番茄", "鸡蛋", "盐", "糖", "油"],
        "steps": ["番茄切块，鸡蛋打散", "热油炒鸡蛋盛出", "炒番茄出汁", "混合翻炒出锅"],
        "difficulty": "简单",
        "time": "10分钟",
    }


def search_recipe(keyword: str) -> dict:
    """
    搜索菜谱（路由入口函数）
    支持按菜名、按食材搜索，结果带 LLM 兜底
    """
    data = _load_recipes()
    results = []
    # 本地搜索
    for r in data["recipes"]:
        if keyword.lower() in r["name"].lower():
            results.append(r)
            continue
        for ing in r["ingredients"]:
            if keyword.lower() in ing.lower():
                results.append(r)
                break
    if results:
        return {
            "source": "local",
            "count": len(results),
            "recipes": results[:5],
        }
    # LLM 生成
    llm_result = generate_recipe_llm(keyword, [])
    return {
        "source": "llm" if llm_result else "none",
        "count": 1 if llm_result else 0,
        "recipes": [],
        "llm_hint": llm_result,
    }


# ── Voice Handler ───────────────────────────────

ADD_RECIPE_PATTERNS = [
    ("醋", "醋溜白菜"), ("可乐", "可乐鸡翅"), ("糖醋", "糖醋里脊"),
    ("红烧", "红烧排骨"), ("麻婆", "麻婆豆腐"), ("宫保", "宫保鸡丁"),
    ("回锅", "回锅肉"), ("鱼香", "鱼香肉丝"), ("地三鲜", "地三鲜"),
    ("干煸", "干煸四季豆"), ("蚝油", "蚝油生菜"), ("手撕", "手撕包菜"),
]

RECORD_PATTERNS = [
    "帮我记", "记录", "记一下", "帮我记住", "记下来",
]

VOICE_ADD_PATTERNS = [
    "帮我记录", "帮我加", "添加菜谱", "记一个菜",
]

def recipe_handler(text: str) -> Optional[str]:
    """菜谱意图处理（Jarvis 入口）"""
    text_lower = text.lower().strip()

    # ── 随机推荐 ──
    if ("随便" in text_lower or "推荐一个" in text_lower or "随机" in text_lower) and \
       ("菜" in text_lower or "菜谱" in text_lower):
        return random_recipe()

    # ── 列出所有 ──
    if ("列出" in text_lower or "看一下" in text_lower or "有什么菜" in text_lower) and \
       ("菜谱" in text_lower or "所有" in text_lower or "菜" in text_lower):
        return list_all_recipes()

    # ── 语音记录菜谱 ──
    if any(p in text for p in VOICE_ADD_PATTERNS):
        return _handle_voice_add(text)

    # ── 根据食材搜索 ──
    common_ingredients = [
        "土豆", "番茄", "鸡蛋", "排骨", "牛肉", "鸡肉", "鱼",
        "青菜", "黄瓜", "茄子", "豆腐", "米饭", "猪肉", "白菜",
        "青椒", "四季豆", "鸡翅", "牛腩", "羊肉", "蒜苔", "包菜",
        "生菜", "紫菜", "玉米", "豆腐", "粉丝", "木耳", "花生",
    ]
    for ing in common_ingredients:
        if ing in text and ("做什么" in text or "能做" in text or "菜谱" in text or "推荐" in text):
            return search_recipe_by_ingredient(ing)

    # ── 查询具体菜谱 ──
    data = _load_recipes()
    for r in data["recipes"]:
        if r["name"].lower() in text_lower or r["name"] in text:
            result = get_recipe(r["name"])
            if result:
                return result

    # ── "怎么做XX" ──
    if "怎么做" in text or "做法" in text or "怎么煮" in text or "怎么炒" in text:
        for prefix in ["怎么做", "做法", "怎么煮", "怎么炒", "给我"]:
            text = text.replace(prefix, "").strip()
        if text:
            # 先查本地
            result = get_recipe(text)
            if result:
                return result
            # LLM 兜底
            llm_result = generate_recipe_llm(text, [])
            if llm_result:
                return llm_result

    # ── LLM 兜底（如果是关于做菜的问题） ──
    if any(kw in text for kw in ["菜", "做", "煮", "炒", "煎", "炖", "蒸", "美食", "食谱"]):
        # 尝试提取菜名
        parts = text.split()
        for p in parts:
            if len(p) >= 2:
                # 尝试以关键词做模糊匹配
                for r in data["recipes"]:
                    if any(kw in p for kw in r["name"]):
                        return get_recipe(r["name"])
        return generate_recipe_llm(text, [])

    return None


def _handle_voice_add(text: str) -> Optional[str]:
    """处理语音添加菜谱"""
    data = _load_recipes()

    # 尝试匹配已知菜名
    for keyword, recipe_name in ADD_RECIPE_PATTERNS:
        if keyword in text:
            for r in data["recipes"]:
                if r["name"] == recipe_name:
                    return f"「{recipe_name}」已经在菜谱库中了，不用重复添加哦~\n\n已保存的菜谱用「列出菜谱」查看"

    # LLM 智能解析添加意图
    sys_prompt = """用户说了一段关于菜谱的话，请判断是否包含记录/添加菜谱的意图，如果包含，提取菜谱信息。
返回 JSON：
- has_recipe: true/false
- if true:
  - name: 菜名
  - ingredients: [食材列表]
  - steps: [步骤列表]
  - difficulty: 简单/中等/困难
  - time: 预计时间

只返回 JSON，不要多余文字。如果不包含菜谱信息，返回 {"has_recipe": false}"""
    llm_result = _call_finna_llm(sys_prompt, text, max_tokens=1024)
    if llm_result:
        try:
            result = json.loads(llm_result)
            if result.get("has_recipe") and result.get("name"):
                recipe_data = result
                add_result = add_recipe(
                    recipe_data["name"],
                    recipe_data["ingredients"],
                    recipe_data["steps"],
                    recipe_data.get("difficulty", "简单"),
                    recipe_data.get("time"),
                )
                lines = [f"✅ {add_result}"]
                lines.append(f"食材：{', '.join(recipe_data['ingredients'])}")
                return "\n".join(lines)
        except (json.JSONDecodeError, KeyError):
            pass

    return "我没听清楚菜谱内容，你可以直接说「帮我记一下醋溜白菜的做法：白菜切片，热油爆香...」"