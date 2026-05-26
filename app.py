#!/usr/bin/env python3
"""
老婆点菜 — Flask API + 前端
"""
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from recipe_core import search_recipe as do_search
from smart_recommend import recommend_smart, recommend_daily, recommend_by_context
from wife_profile import (
    get_profile, update_profile, get_profile_summary,
    favorite_dish, unfavorite_dish, dislike_dish, remove_dislike,
    record_order, get_history, get_frequently_ordered, get_recent_orders,
)

app = Flask(__name__)
CORS(app)


# ── 前端 ──
@app.route("/")
def index():
    return render_template("index.html")


# ── 菜谱 API ──
@app.route("/api/recipes/all", methods=["GET"])
def all_recipes():
    """获取全部菜谱"""
    import json, os
    recipe_file = os.path.join(os.path.dirname(__file__), "data", "recipes.json")
    with open(recipe_file, "r", encoding="utf-8") as f:
        recipes = json.load(f)
    return jsonify({"recipes": recipes, "total": len(recipes)})


@app.route("/api/recipe/search", methods=["GET"])
def search():
    keyword = request.args.get("keyword", "")
    if not keyword:
        return jsonify({"status": "error", "message": "keyword is required"}), 400
    try:
        result = do_search(keyword)
        return jsonify({"status": "success", "data": result})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ── 用户画像 API ──
@app.route("/api/user/profile", methods=["GET"])
def user_profile():
    """获取老婆口味画像"""
    profile = get_profile()
    history = get_history()
    top = get_frequently_ordered(10)
    
    return jsonify({
        **profile,
        "top_dishes": top,
        "recent_orders": get_recent_orders(7),
    })


@app.route("/api/user/profile", methods=["POST"])
def update_user_profile():
    """更新口味偏好"""
    data = request.get_json() or {}
    profile = update_profile(data)
    return jsonify(profile)


@app.route("/api/user/favorite", methods=["POST"])
def add_favorite():
    """收藏一道菜"""
    data = request.get_json() or {}
    dish = data.get("dish", "")
    if not dish:
        return jsonify({"status": "error", "message": "dish is required"}), 400
    profile = favorite_dish(dish)
    return jsonify(profile)


@app.route("/api/user/unfavorite", methods=["POST"])
def remove_favorite():
    """取消收藏"""
    data = request.get_json() or {}
    dish = data.get("dish", "")
    if not dish:
        return jsonify({"status": "error", "message": "dish is required"}), 400
    profile = unfavorite_dish(dish)
    return jsonify(profile)


@app.route("/api/user/dislike", methods=["POST"])
def add_dislike():
    """标记不喜欢"""
    data = request.get_json() or {}
    dish = data.get("dish", "")
    if not dish:
        return jsonify({"status": "error", "message": "dish is required"}), 400
    profile = dislike_dish(dish)
    return jsonify(profile)


@app.route("/api/user/undislike", methods=["POST"])
def remove_user_dislike():
    """取消不喜欢"""
    data = request.get_json() or {}
    dish = data.get("dish", "")
    if not dish:
        return jsonify({"status": "error", "message": "dish is required"}), 400
    profile = remove_dislike(dish)
    return jsonify(profile)


# ── 推荐 API ──
@app.route("/api/recommend/daily", methods=["GET"])
def daily_recommend():
    """今日推荐"""
    results = recommend_daily()
    return jsonify({"recommendations": results, "total": len(results)})


@app.route("/api/recommend/smart", methods=["POST"])
def smart_recommend():
    """智能推荐（可指定食材）"""
    data = request.get_json() or {}
    ingredients = data.get("ingredients", [])
    results = recommend_smart(limit=10, ingredients=ingredients if ingredients else None)
    return jsonify({"recommendations": results, "total": len(results)})


@app.route("/api/recommend/context", methods=["POST"])
def context_recommend():
    """场景推荐：'想吃辣的'、'想吃肉'等"""
    data = request.get_json() or {}
    context = data.get("context", "")
    if not context:
        return jsonify({"status": "error", "message": "context is required"}), 400
    results = recommend_by_context(context)
    return jsonify({"recommendations": results, "total": len(results)})


# ── 点菜 API ──
@app.route("/api/order", methods=["POST"])
def place_order():
    """点菜！"""
    data = request.get_json() or {}
    dish = data.get("dish", "")
    if not dish:
        return jsonify({"status": "error", "message": "dish is required"}), 400
    order = record_order(dish)
    return jsonify({"status": "success", "order": order})


@app.route("/api/order/history", methods=["GET"])
def order_history():
    """点菜历史"""
    days = request.args.get("days", 30, type=int)
    recent = get_recent_orders(days)
    top = get_frequently_ordered(20)
    return jsonify({
        "recent": recent,
        "top_dishes": top,
    })


# ── 健康检查 ──
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "wife-menu"})


if __name__ == "__main__":
    print("🍳 老婆点菜系统启动...")
    print("   前端: http://localhost:8091")
    print("   API:  http://localhost:8091/api/health")
    app.run(host="0.0.0.0", port=8091, debug=False)
