# routes.py
from flask import Blueprint, render_template, jsonify
from models import get_top_scores  # 导入数据库查询函数

# 创建蓝图（命名为`main`，模块为当前文件）
main_routes = Blueprint('main', __name__)

@main_routes.route('/')
def index():
    """渲染游戏首页"""
    return render_template('index.html')
'''
@main_routes.route('/user/login')

@main_routes.route('/user/register')
'''
@main_routes.route('/api/leaderboard')
def api_leaderboard():
    """返回排行榜JSON数据"""
    top_scores = get_top_scores(limit=10)
    return jsonify([
        {
            "name": r[0],
            "time": r[1],
            "coins": r[2],
            "date": r[3].isoformat()
        } for r in top_scores
    ])