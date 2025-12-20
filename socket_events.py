# socket_events.py
from flask import request
from flask_socketio import emit, join_room, leave_room

from db import save_score

#其中socketio.emit为玩家主动通信，在game_engine中为服务器主动通信
def register_socket_events(socketio, engine):
    """注册所有SocketIO事件，依赖socketio和engine实例"""

    @socketio.on('connect')
    def on_connect():
        sid = request.sid
        print(f"[connect] sid={sid}")
        emit('message', {'msg': '连接已建立，请发送 join 事件并携带玩家名以进入游戏。'})

    @socketio.on('join')
    def on_join(data):
        sid = request.sid
        name = data.get('name', '匿名')
        print(f"[join] sid={sid} name={name}")
        player = engine.add_player(sid, name)
        join_room('main')
        emit('init', engine.get_init_payload_for(sid))
        socketio.emit('state', engine.get_state_payload(), room='main')

    @socketio.on('request_new_maze')
    def on_request_new_maze(data):
        sid = request.sid
        w = int(data.get('w', 21))
        h = int(data.get('h', 21))
        print(f"[request_new_maze] from {sid} size={w}x{h}")
        engine.generate_new_maze(w, h)
        socketio.emit('init', engine.get_global_init_payload(), room='main')
        socketio.emit('state', engine.get_state_payload(), room='main')
        socketio.emit('message', {'msg': f'新的迷宫已生成：{w}x{h}'}, room='main')

    @socketio.on('move')
    def on_move(data):
        sid = request.sid
        dx = int(data.get('dx', 0))
        dy = int(data.get('dy', 0))
        changed, info = engine.process_move(sid, dx, dy)
        emit('action_result', info)
        socketio.emit('state', engine.get_state_payload(), room='main')
        if changed.get('finished'):
            p = changed['player_snapshot']
            save_score(p['name'], p['finish_time'], p['coins'])
            socketio.emit('leaderboard_update', {'top': [dict(n) for n in engine.get_leaderboard_snapshot()]}, room='main')

    @socketio.on('buy')
    def on_buy(data):
        sid = request.sid
        item_id = data.get('item_id')
        success, msg = engine.buy_item(sid, item_id)
        emit('buy_result', {"success": success, "msg": msg})
        if success:
            socketio.emit('state', engine.get_state_payload(), room='main')

    @socketio.on('disconnect')
    def on_disconnect():
        sid = request.sid
        print(f"[disconnect] sid={sid}")
        engine.remove_player(sid)
        leave_room('main')
        socketio.emit('state', engine.get_state_payload(), room='main')