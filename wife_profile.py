"""
老婆口味画像系统 — 记住她的偏好，越用越懂她
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Optional

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
PROFILE_FILE = os.path.join(DATA_DIR, "wife_profile.json")
HISTORY_FILE = os.path.join(DATA_DIR, "order_history.json")


def _load(filepath: str, default: dict) -> dict:
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def _save(filepath: str, data: dict):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── 初始化画像 ──
DEFAULT_PROFILE = {
    "name": "老婆",
    "created_at": datetime.now().isoformat(),
    "taste": {
        "spiciness": 0,       # 0-5，0=不吃辣，5=无辣不欢
        "saltiness": 3,       # 咸度偏好
        "sweetness": 2,       # 甜度偏好
        "sourness": 2,        # 酸度偏好
    },
    "preferences": {
        "favorite_cuisines": [],     # 喜欢的菜系：川菜、粤菜、东北菜...
        "favorite_ingredients": [],   # 喜欢的食材
        "disliked_ingredients": [],   # 不吃的食材
        "allergies": [],              # 过敏
        "dietary": [],                # 饮食限制：素食、低脂、低碳...
    },
    "favorites": [],           # 收藏的菜名
    "dislikes": [],            # 明确不喜欢的菜名
    "stats": {
        "total_orders": 0,
        "last_order_at": None,
    }
}


def get_profile() -> dict:
    """获取老婆画像"""
    return _load(PROFILE_FILE, DEFAULT_PROFILE.copy())


def update_profile(updates: dict) -> dict:
    """更新画像"""
    profile = get_profile()
    
    if "taste" in updates:
        profile["taste"].update(updates["taste"])
    if "preferences" in updates:
        for key in ["favorite_cuisines", "favorite_ingredients", "disliked_ingredients", "allergies", "dietary"]:
            if key in updates["preferences"]:
                existing = profile["preferences"].get(key, [])
                new_items = updates["preferences"][key]
                if isinstance(new_items, list):
                    profile["preferences"][key] = list(set(existing + new_items))
                else:
                    profile["preferences"][key] = new_items
    
    _save(PROFILE_FILE, profile)
    return profile


def favorite_dish(dish_name: str) -> dict:
    """收藏一道菜"""
    profile = get_profile()
    if dish_name not in profile["favorites"]:
        profile["favorites"].append(dish_name)
    _save(PROFILE_FILE, profile)
    return profile


def unfavorite_dish(dish_name: str) -> dict:
    """取消收藏"""
    profile = get_profile()
    if dish_name in profile["favorites"]:
        profile["favorites"].remove(dish_name)
    _save(PROFILE_FILE, profile)
    return profile


def dislike_dish(dish_name: str) -> dict:
    """标记不喜欢"""
    profile = get_profile()
    if dish_name not in profile["dislikes"]:
        profile["dislikes"].append(dish_name)
    # 如果之前收藏过，移除
    if dish_name in profile["favorites"]:
        profile["favorites"].remove(dish_name)
    _save(PROFILE_FILE, profile)
    return profile


def remove_dislike(dish_name: str) -> dict:
    """取消不喜欢"""
    profile = get_profile()
    if dish_name in profile["dislikes"]:
        profile["dislikes"].remove(dish_name)
    _save(PROFILE_FILE, profile)
    return profile


# ── 点菜历史 ──
DEFAULT_HISTORY = {"orders": []}


def get_history() -> dict:
    return _load(HISTORY_FILE, DEFAULT_HISTORY.copy())


def record_order(dish_name: str, rating: Optional[int] = None, note: str = "") -> dict:
    """记录一次点菜"""
    history = get_history()
    order = {
        "dish": dish_name,
        "ordered_at": datetime.now().isoformat(),
        "rating": rating,      # 1-5，吃完后的评价
        "note": note,
    }
    history["orders"].append(order)
    _save(HISTORY_FILE, history)
    
    # 更新统计
    profile = get_profile()
    profile["stats"]["total_orders"] += 1
    profile["stats"]["last_order_at"] = order["ordered_at"]
    _save(PROFILE_FILE, profile)
    
    return order


def get_frequently_ordered(limit: int = 10) -> List[dict]:
    """最常点的菜"""
    history = get_history()
    counts = {}
    last_order = {}
    for order in history["orders"]:
        dish = order["dish"]
        counts[dish] = counts.get(dish, 0) + 1
        last_order[dish] = order["ordered_at"]
    
    sorted_dishes = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    return [
        {"name": dish, "count": cnt, "last_ordered": last_order[dish]}
        for dish, cnt in sorted_dishes[:limit]
    ]


def get_recent_orders(days: int = 7) -> List[dict]:
    """最近 N 天的点菜记录"""
    from datetime import timedelta
    cutoff = datetime.now() - timedelta(days=days)
    history = get_history()
    return [
        o for o in history["orders"]
        if datetime.fromisoformat(o["ordered_at"]) > cutoff
    ]


def get_profile_summary() -> str:
    """画像摘要（给人看的）"""
    profile = get_profile()
    taste = profile["taste"]
    pref = profile["preferences"]
    stats = profile["stats"]
    
    lines = [f"👩 {profile['name']} 的口味画像"]
    
    taste_desc = {
        "spiciness": ["不吃辣", "微微辣", "微辣", "中辣", "很辣", "无辣不欢"][taste["spiciness"]],
        "saltiness": ["极淡", "偏淡", "正常", "偏咸", "很咸", "重咸"][taste["saltiness"]],
        "sweetness": ["不甜", "微甜", "正常", "偏甜", "很甜", "嗜甜"][taste["sweetness"]],
        "sourness": ["不酸", "微酸", "正常", "偏酸", "很酸", "嗜酸"][taste["sourness"]],
    }
    lines.append(f"  口味: 辣度{taste_desc['spiciness']} | 咸度{taste_desc['saltiness']} | 甜度{taste_desc['sweetness']} | 酸度{taste_desc['sourness']}")
    
    if pref["favorite_cuisines"]:
        lines.append(f"  爱吃的菜系: {', '.join(pref['favorite_cuisines'])}")
    if pref["favorite_ingredients"]:
        lines.append(f"  爱吃的食材: {', '.join(pref['favorite_ingredients'])}")
    if pref["disliked_ingredients"]:
        lines.append(f"  不吃的食材: {', '.join(pref['disliked_ingredients'])}")
    if pref["allergies"]:
        lines.append(f"  过敏: {', '.join(pref['allergies'])}")
    if pref["dietary"]:
        lines.append(f"  饮食限制: {', '.join(pref['dietary'])}")
    
    lines.append(f"  收藏: {len(profile['favorites'])} 道 | 不喜欢的: {len(profile['dislikes'])} 道")
    lines.append(f"  历史点菜: {stats['total_orders']} 次")
    
    return "\n".join(lines)


if __name__ == "__main__":
    # 初始化画像
    profile = get_profile()
    print(json.dumps(profile, ensure_ascii=False, indent=2))
