# app.py
import eventlet
eventlet.monkey_patch()
from flask import Flask
from flask_socketio import SocketIO
from models import init_db
from game_engine import GameEngine
from routes import main_routes  # 导入HTTP路由蓝图
from socket_events import register_socket_events  # 导入SocketIO事件注册函数

# Flask + SocketIO 初始化
app = Flask(__name__)
app.config['SECRET_KEY'] = 'escape_maze_secret'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')
#cors_allowed_origins="*"，允许所有域名的请求访问。async_mode=eventlet 是一个轻量级的异步网络库

# 初始化数据库
with app.app_context():
    init_db()



# 初始化游戏引擎
engine = GameEngine(socketio)

# 注册HTTP路由蓝图
app.register_blueprint(main_routes)

# 注册SocketIO事件（传入socketio和engine实例）
register_socket_events(socketio, engine)

if __name__ == '__main__':
    socketio.run(
        app,
        host='127.0.0.1',
        port=5000,
        debug=True,
        use_reloader=False,
        allow_unsafe_werkzeug=True
    )