# 食谱推荐 App

贾维斯智能食谱推荐系统 — 基于 AI 的菜谱搜索与推荐。

## 功能

- **菜谱搜索**：按菜名、食材、口味搜索
- **智能推荐**：根据偏好和场景推荐菜品
- **批量生成**：AI 自动生成菜谱数据库

## 快速启动

```bash
pip install flask flask-cors
python app.py
```

API 运行在 `http://localhost:8090`

## API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/health` | GET | 健康检查 |
| `/api/recipe/search?keyword=红烧肉` | GET | 搜索菜谱 |
| `/api/recipe/recommend` | POST | 智能推荐 |

## 数据结构

`data/recipes.json` — 菜谱数据库（95KB），含菜名、食材、做法、口味等字段。

## 生成菜谱

```bash
python generate_recipes.py
```

使用 FinnA AI 模型批量生成菜谱数据。
