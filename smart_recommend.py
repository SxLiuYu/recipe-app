"""
智能推荐引擎 — 基于老婆画像的个性化推荐
"""

import json
import os
import random
from typing import List, Dict, Optional
from wife_profile import get_profile, get_history, get_frequently_ordered


DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
RECIPE_FILE = os.path.join(DATA_DIR, "recipes.json")


def _load_recipes() -> list:
    if os.path.exists(RECIPE_FILE):
        with open(RECIPE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _score_recipe(recipe: dict, profile: dict) -> int:
    """打分 — 基于老婆画像给菜谱打分"""
    score = 50  # 基础分
    
    name = recipe.get("name", "")
    ingredients = recipe.get("ingredients", [])
    pref = profile.get("preferences", {})
    favorites = profile.get("favorites", [])
    dislikes = profile.get("dislikes", [])
    
    # 明确不喜欢 → 直接负分
    if name in dislikes:
        return -100
    
    # 收藏过的 → 加分
    if name in favorites:
        score += 30
    
    # 喜欢的食材匹配 → 加分
    fav_ingredients = pref.get("favorite_ingredients", [])
    for ing in ingredients:
        for fi in fav_ingredients:
            if fi in ing or ing in fi:
                score += 15
                break
    
    # 不吃的食材 → 大幅扣分
    disliked_ingredients = pref.get("disliked_ingredients", [])
    for ing in ingredients:
        for di in disliked_ingredients:
            if di in ing or ing in di:
                score -= 40
                break
    
    # 过敏 → 直接负分
    allergies = pref.get("allergies", [])
    for ing in ingredients:
        for allergy in allergies:
            if allergy in ing or ing in allergy:
                return -100
    
    # 菜系偏好
    fav_cuisines = pref.get("favorite_cuisines", [])
    all_ingredients_text = " ".join(ingredients) + name
    cuisine_keywords = {
        "川菜": ["麻辣", "豆瓣酱", "花椒", "干辣椒", "红油", "水煮", "鱼香", "宫保", "回锅"],
        "粤菜": ["蚝油", "清蒸", "白切", "煲", "虾饺", "叉烧"],
        "湘菜": ["剁椒", "腊肉", "酸豆角"],
        "东北菜": ["酸菜", "炖", "锅包肉", "地三鲜"],
        "江浙菜": ["糖醋", "红烧", "东坡"],
        "西北菜": ["孜然", "羊肉", "拉面"],
    }
    for cuisine in fav_cuisines:
        if cuisine in cuisine_keywords:
            for kw in cuisine_keywords[cuisine]:
                if kw in all_ingredients_text:
                    score += 10
                    break
    
    # 口味偏好微调
    taste = profile.get("taste", {})
    spiciness = taste.get("spiciness", 3)
    spicy_keywords = ["辣", "辣椒", "花椒", "麻辣", "红油"]
    is_spicy = any(kw in all_ingredients_text for kw in spicy_keywords)
    if is_spicy:
        if spiciness >= 4:  # 很能吃辣
            score += 10
        elif spiciness <= 1:  # 不太吃辣
            score -= 20
    
    sweet_keywords = ["糖", "甜", "蜜", "拔丝"]
    is_sweet = any(kw in all_ingredients_text for kw in sweet_keywords)
    sweetness = taste.get("sweetness", 2)
    if is_sweet:
        if sweetness >= 4:
            score += 8
        elif sweetness <= 0:
            score -= 15
    
    sour_keywords = ["醋", "酸", "柠檬"]
    is_sour = any(kw in all_ingredients_text for kw in sour_keywords)
    sourness = taste.get("sourness", 2)
    if is_sour:
        if sourness >= 4:
            score += 8
        elif sourness <= 0:
            score -= 10
    
    return score


def recommend_smart(limit: int = 10, ingredients: List[str] = None, exclude_seen: bool = True) -> List[dict]:
    """
    智能推荐
    - 基于老婆画像打分
    - 可指定现有食材过滤
    - 排除最近点过的菜（避免重复）
    """
    recipes = _load_recipes()
    profile = get_profile()
    history = get_history()
    
    recently_ordered = set()
    if exclude_seen:
        recent_cutoff = 7  # 7天内不重复推荐
        from datetime import datetime, timedelta
        cutoff = datetime.now() - timedelta(days=recent_cutoff)
        for order in history["orders"]:
            try:
                order_time = datetime.fromisoformat(order["ordered_at"])
                if order_time > cutoff:
                    recently_ordered.add(order["dish"])
            except:
                pass
    
    # 过滤 + 打分
    candidates = []
    for recipe in recipes:
        name = recipe.get("name", "")
        
        # 跳过最近点过的
        if name in recently_ordered:
            continue
        
        # 食材过滤
        if ingredients:
            recipe_ingredients = [ing.lower() for ing in recipe.get("ingredients", [])]
            has_match = any(
                any(ui.lower() in ri for ri in recipe_ingredients)
                for ui in ingredients
            )
            if not has_match:
                continue
        
        score = _score_recipe(recipe, profile)
        if score > -50:  # 过滤掉强烈不喜欢的
            candidates.append((score, recipe))
    
    # 排序
    candidates.sort(key=lambda x: x[0], reverse=True)
    
    results = []
    for score, recipe in candidates[:limit]:
        recipe["_score"] = score
        results.append(recipe)
    
    # 如果结果不够，用随机补充
    if len(results) < limit:
        remaining = [r for r in recipes if r["name"] not in {x["name"] for x in results}]
        random.shuffle(remaining)
        for r in remaining[:limit - len(results)]:
            r["_score"] = -999
            results.append(r)
    
    return results


def recommend_daily() -> List[dict]:
    """今日推荐：带理由的个性化推荐"""
    top = recommend_smart(limit=6)
    
    profile = get_profile()
    fav_ingredients = profile.get("preferences", {}).get("favorite_ingredients", [])
    
    # 给推荐加理由
    for r in top:
        score = r.get("_score", 0)
        reasons = []
        name = r["name"]
        
        if name in profile.get("favorites", []):
            reasons.append("💝 你收藏过的")
        if score == 0:
            reasons.append("🆕 还没试过")
        
        # 口味匹配
        ingredients_text = " ".join(r.get("ingredients", []))
        if fav_ingredients:
            for fi in fav_ingredients:
                if fi in ingredients_text:
                    reasons.append(f"有爱吃的{fi}")
                    break
        
        if score > 80:
            reasons.append("⭐ 强烈推荐")
        elif score > 60:
            reasons.append("👍 应该会喜欢")
        
        r["_reasons"] = reasons if reasons else ["📋 常规推荐"]
    
    return top


def recommend_by_context(context: str) -> List[dict]:
    """
    场景推荐：根据场景智能推荐
    比如："今天想吃清爽的"、"想吃肉"、"来点辣的"
    """
    from wife_profile import get_profile
    
    recipes = _load_recipes()
    profile = get_profile()
    
    context_lower = context.lower()
    
    # 关键词映射
    keyword_map = {
        "清爽": ["凉拌", "清炒", "白灼", "蒸", "凉"],
        "清淡": ["清炒", "白灼", "蒸", "煮", "素"],
        "肉": ["肉", "鸡", "鱼", "虾", "牛", "羊", "排骨", "翅"],
        "辣的": ["辣", "麻辣", "红油", "干辣椒", "豆瓣", "剁椒"],
        "酸的": ["醋", "酸", "柠檬", "番茄"],
        "甜的": ["糖", "甜", "蜜", "拔丝", "可乐"],
        "汤": ["汤", "羹"],
        "快手": ["炒", "煎"],
        "下饭": ["麻婆", "红烧", "鱼香", "宫保", "回锅", "干煸"],
        "素菜": [],  # 食材中无荤关键词
    }
    
    # 确定匹配策略
    positive_kw = []
    negative_kw = []
    
    for intent, keywords in keyword_map.items():
        if intent in context_lower:
            positive_kw.extend(keywords)
    
    # 如果说了"不想要XX"
    for no_prefix in ["不要", "不吃", "不想", "别"]:
        idx = context_lower.find(no_prefix)
        if idx >= 0:
            after = context_lower[idx + len(no_prefix):].strip()[:10]
            negative_kw.append(after)
    
    # "素菜"特殊处理
    if "素菜" in context_lower or "素食" in context_lower:
        meat_keywords = ["肉", "鸡", "鱼", "虾", "牛", "羊", "排骨", "翅", "腿"]
        negative_kw.extend(meat_keywords)
    
    # 嗜辣
    if "无辣不欢" in context_lower or "越辣越好" in context_lower:
        positive_kw.extend(["麻辣", "红油", "干辣椒", "剁椒", "泡椒"])
    
    # 打分
    candidates = []
    for recipe in recipes:
        name = recipe["name"]
        ingredients_text = " ".join(recipe.get("ingredients", []))
        full_text = name + ingredients_text
        
        score = 50
        
        # 正向匹配
        if positive_kw:
            matched = sum(1 for kw in positive_kw if kw in full_text)
            score += matched * 15
        
        # 负向匹配
        if negative_kw:
            has_negative = any(kw in full_text for kw in negative_kw)
            if has_negative:
                score -= 60
        
        # 叠加画像评分
        profile_score = _score_recipe(recipe, profile)
        score = score + profile_score - 50  # 合并
        
        if score > -50:
            score = min(score, 120)  # 上限
            candidates.append((score, recipe))
    
    candidates.sort(key=lambda x: x[0], reverse=True)
    
    results = []
    for score, recipe in candidates[:10]:
        recipe["_score"] = score
        results.append(recipe)
    
    return results


if __name__ == "__main__":
    # 测试
    results = recommend_smart(limit=5)
    for r in results:
        print(f"{r['_score']:>4} | {r['name']} | {r.get('difficulty', '?')}")
