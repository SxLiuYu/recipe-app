#!/usr/bin/env python3
"""食谱推荐 API - 独立 Flask 应用"""

import sys
import os

# 添加 jarvis 路径
# 当前目录即项目根

from flask import Flask, request, jsonify
from flask_cors import CORS
from recipe_core import (
    search_recipe as do_search,
    recommend_recipe as do_recommend,
)

app = Flask(__name__)
CORS(app)


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "recipe-api"})


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


@app.route("/api/recipe/recommend", methods=["POST"])
def recommend():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "JSON body required"}), 400
        ingredients = data.get("ingredients", [])
        cuisine = data.get("cuisine", "")
        result = do_recommend(ingredients, cuisine)
        return jsonify({"status": "success", "data": result})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    
    app.run(host="0.0.0.0", port=8090, debug=False)