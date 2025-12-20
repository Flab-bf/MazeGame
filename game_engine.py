import random, time
from collections import deque
from threading import Lock
import db as mds
import copy

#register/login 注册/登录
class LoginAndRegister:
    def __init__(self):
        self.user={}
    def register(self, user_massage):
         if  mds.user_exist(user_massage["account"]):
             return False
         else:
             mds.add_user(user_massage)
             return True
    def login(self, user_massage):
        if mds.user_exist(user_massage["account"]):
            if mds.password_correct(user_massage):
                return True
            else:
                return False
        else:
            return False

# GameEngine 支持以 socketio 对象为参数启动定时任务
class GameEngine:
    def __init__(self, socketio, w=21, h=21):
        self.sock = socketio
        self.lock = Lock()  # 保护共享状态
        # 世界状态
        self.width = w
        self.height = h
        self.grid = []        # 二维列表，0=墙，1=路
        self.start = (1,1)
        self.exit = (1,1)
        self.traps = []       # 列表：{"pos":[x,y],"type":"teleport"/"damage"/"slow"}
        self.boxes = []       # 列表：{"pos":[x,y],"type":"random","coins":n}
        self.shop = []        # 商品列表
        # 玩家状态： sid -> player dict
        self.players = {}     # player: {"sid":..., "name":..., "x":..,"y":..,"coins":..,"hp":..,"shield":..,"start_time":..,"finished":False,"finish_time":None}
        # 初始化世界
        self.generate_new_maze(self.width, self.height)
        # 启动背景任务：盲盒定时刷新
        self.sock.start_background_task(self._box_refresher)

    # 在game_engine.py的GameEngine类中添加以下方法
    def _serialize_player(self, player):
        """将玩家对象转换为前端需要的字典格式"""
        return {
            "sid": player["sid"],  # 玩家唯一标识
            "name": player["name"],  # 玩家名称
            "x": player["x"],  # x坐标
            "y": player["y"],  # y坐标
            "hp": player["hp"],  # 生命值
            "coins": player["coins"],  # 金币数量
            "shield": player.get("shield", False)  # 护盾状态（默认无）
        }

    # ---------------- Maze 生成与世界初始化 ----------------
    def generate_new_maze(self, width=21, height=21, seed=None):
        """生成新的迷宫并初始化陷阱/盲盒/商店配置"""
        with self.lock:
            if seed is None:
                seed = int(time.time() * 1000) & 0xffffffff
            random.seed(seed)
            # 强制奇数
            if width % 2 == 0: width += 1
            if height % 2 == 0: height += 1
            self.width = width
            self.height = height
            # 初始化网格（全墙）
            grid = [[0 for _ in range(width)] for __ in range(height)]
            # DFS 回溯器
            stack = [(1,1)]
            grid[1][1] = 1
            dirs = [(0,2),(0,-2),(2,0),(-2,0)]
            while stack:
                x,y = stack[-1]
                random.shuffle(dirs)
                carved = False
                for dx,dy in dirs:
                    nx,ny = x+dx, y+dy
                    if 1 <= nx < width-1 and 1 <= ny < height-1 and grid[ny][nx] == 0:
                        grid[ny][nx] = 1
                        grid[y + dy//2][x + dx//2] = 1
                        stack.append((nx,ny))
                        carved = True
                        break
                if not carved:
                    stack.pop()
            self.grid = grid
            self.start = (1,1)

            # BFS 求最远单元作为出口
            q = deque([self.start])
            dist = {self.start:0}
            while q:
                cx,cy = q.popleft()
                for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]:
                    nx,ny = cx+dx, cy+dy
                    if 0<=nx<width and 0<=ny<height and grid[ny][nx]==1 and (nx,ny) not in dist:
                        dist[(nx,ny)] = dist[(cx,cy)] + 1
                        q.append((nx,ny))
            # 出口选择最远点
            self.exit = max(dist.keys(), key=lambda k: dist[k])

            # 放置陷阱与盲盒（基于通路单元）
            path_cells = list(dist.keys())
            self.traps = []
            self.boxes = []

            # 确保在解路径上放一个盲盒
            prev = {self.start:None}
            q = deque([self.start])
            while q:
                cx,cy = q.popleft()
                for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]:
                    nx,ny = cx+dx, cy+dy
                    if 0<=nx<width and 0<=ny<height and grid[ny][nx]==1 and (nx,ny) not in prev:
                        prev[(nx,ny)] = (cx,cy)
                        q.append((nx,ny))
            path = []
            cur = self.exit
            while cur:
                path.append(cur)
                cur = prev.get(cur)
            possible_box_positions = [p for p in path[1:-1]]
            if possible_box_positions:
                bx = random.choice(possible_box_positions)
                self.boxes.append({"pos":[bx[0],bx[1]], "type":"guaranteed", "coins": random.randint(30,80)})

            # 随机其他陷阱
            sample_k = min(max(3, len(path_cells)//15), len(path_cells))
            for p in random.sample(path_cells, k=sample_k):
                if p == self.start or p == self.exit:
                    continue
                t = random.choice(["teleport","damage","slow"])
                self.traps.append({"pos":[p[0],p[1]], "type":t})

            # 更多盲盒
            sample_k2 = min(max(5, len(path_cells)//10), len(path_cells))
            for p in random.sample(path_cells, k=sample_k2):
                if p == self.start or p == self.exit: continue
                if any(p[0]==b['pos'][0] and p[1]==b['pos'][1] for b in self.boxes): continue
                self.boxes.append({"pos":[p[0],p[1]], "type":"random", "coins": random.randint(10,60)})

            # 商店基础物品
            self.shop = [
                {"id":"bomb","price":50,"desc":"炸开一堵墙（死胡同）"},
                {"id":"shield","price":70,"desc":"抵挡一次致命伤害"},
                {"id":"heal","price":40,"desc":"恢复生命值"},
            ]

            # 重置玩家位置（所有在线玩家回起点并清状态）
            for p in self.players.values():
                p['x'], p['y'] = self.start
                p['coins'] = 0
                p['hp'] = 100
                p['shield'] = False
                p['finished'] = False
                p['finish_time'] = None
                p['start_time'] = time.time()


    # ---------------- Player 管理 ----------------
    def add_player(self, sid, name):
        """添加新玩家，返回玩家对象引用（服务器内部使用）"""
        with self.lock:
            if sid in self.players:
                return self.players[sid]
            # 新玩家在起点出现
            p = {
                "sid": sid,
                "name": name,
                "x": self.start[0],
                "y": self.start[1],
                "coins": 0,
                "hp": 100,
                "shield": False,
                "start_time": time.time(),
                "finished": False,
                "finish_time": None
            }
            self.players[sid] = p
            return p

    def remove_player(self, sid):
        """移除玩家（断开连接时调用）"""
        with self.lock:
            if sid in self.players:
                del self.players[sid]

    # ---------------- 行为处理：移动、购买、开箱等 ----------------
    def process_move(self, sid, dx, dy):
        """
        权威处理移动指令：
          - 输入 dx,dy
          - 检查合法性（边界/墙）
          - 应用陷阱/盲盒效果
          - 返回 (changed_info_dict, action_info_for_client)
        changed_info_dict 包含可能被外部使用的重要事件（比如 finished）
        action_info_for_client 用于给发起者的反馈消息
        """
        with self.lock:
            if sid not in self.players:
                return {}, {"ok": False, "msg": "玩家不存在或未加入游戏。"}
            player = self.players[sid]
            if player['finished']:
                return {}, {"ok": False, "msg": "你已完成本局。"}

            nx = player['x'] + dx
            ny = player['y'] + dy
            # 边界检查
            if not (0 <= nx < self.width and 0 <= ny < self.height):
                return {}, {"ok": False, "msg": "不能移出地图边界。"}
            # 遇墙
            if self.grid[ny][nx] == 0:
                # 撞墙惩罚
                player['hp'] = max(0, player['hp'] - 5)
                return {}, {"ok": True, "msg": "撞墙！生命 -5"}
            # 合法移动：更新位置
            player['x'] = nx
            player['y'] = ny

            # 检查是否到达出口
            changed = {}
            if (nx,ny) == tuple(self.exit):
                player['finished'] = True
                player['finish_time'] = int(time.time() - player['start_time'])
                changed['finished'] = True
                changed['player_snapshot'] = self._snapshot_player(player)
                return changed, {"ok": True, "msg": f"到达出口！用时 {player['finish_time']} 秒，金币 {player['coins']}"}

            # 检查陷阱（若在陷阱坐标上）
            for t in self.traps:
                if t['pos'][0] == nx and t['pos'][1] == ny:
                    # 触发陷阱
                    if player['shield']:
                        player['shield'] = False
                        return {}, {"ok": True, "msg": "触发陷阱，但防护盾抵挡了一次伤害。"}
                    if t['type'] == 'damage':
                        player['hp'] = max(0, player['hp'] - 30)
                        return {}, {"ok": True, "msg": "遭遇伤害陷阱，生命 -30"}
                    elif t['type'] == 'teleport':
                        # 随机传送到任意通路单元
                        pass_cells = []
                        for yy in range(self.height):
                            for xx in range(self.width):
                                if self.grid[yy][xx] == 1:
                                    pass_cells.append((xx,yy))
                        dest = random.choice(pass_cells)
                        player['x'], player['y'] = dest
                        return {}, {"ok": True, "msg": f"触发传送陷阱，传送到 {dest}"}
                    elif t['type'] == 'slow':
                        # 示例：减速转换为扣血
                        player['hp'] = max(0, player['hp'] - 10)
                        return {}, {"ok": True, "msg": "触发减速陷阱（示意），生命 -10"}

            # 检查盲盒（若当前位置有盲盒）
            for i, b in enumerate(self.boxes):
                if b['pos'][0] == nx and b['pos'][1] == ny:
                    # 开箱：根据类型给奖励或惩罚（服务器决定内容）
                    content = self._resolve_box_content(b)
                    # 从世界中移除该盲盒（多人版需原子）
                    self.boxes.pop(i)
                    # 应用内容结果
                    if content['type'] == 'coins':
                        player['coins'] += content['amount']
                        return {}, {"ok": True, "msg": f"开箱获得金币 {content['amount']}"}
                    elif content['type'] == 'monster':
                        player['hp'] = max(0, player['hp'] - 20)
                        return {}, {"ok": True, "msg": "开箱出现怪物，被追击受伤 -20（示意）"}
                    elif content['type'] == 'item':
                        if content['id'] == 'shield':
                            player['shield'] = True
                            return {}, {"ok": True, "msg": "获得防护盾"}
                        # 其它物品可在此扩展
                    elif content['type'] == 'trap':
                        player['hp'] = max(0, player['hp'] - 15)
                        return {}, {"ok": True, "msg": "开箱触发陷阱，生命 -15"}

            # 常规移动没有特殊事件
            return {}, {"ok": True, "msg": "移动成功。"}

    def buy_item(self, sid, item_id):
        """服务器端购买验证与处理"""
        with self.lock:
            if sid not in self.players:
                return False, "玩家不存在"
            player = self.players[sid]
            # 查找商品
            item = next((it for it in self.shop if it['id']==item_id), None)
            if not item:
                return False, "商品不存在"
            if player['coins'] < item['price']:
                return False, "金币不足"
            # 扣钱并发放效果（示例：shield / heal / bomb）
            player['coins'] -= item['price']
            if item_id == 'shield':
                player['shield'] = True
            elif item_id == 'heal':
                player['hp'] = min(100, player['hp'] + 50)
            elif item_id == 'bomb':
                # 简单实现：如果玩家在死胡同则炸开一堵墙（尝试邻近不可通行点）
                self._use_bomb_at(player['x'], player['y'])
            return True, f"购买成功：{item['desc']}"

    # ---------------- 内部工具方法 ----------------
    def _use_bomb_at(self, x, y):
        """示例性炸墙：尝试在玩家周围炸开一个邻接的墙体（如果存在）"""
        for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]:
            nx,ny = x+dx, y+dy
            if 0<=nx<self.width and 0<=ny<self.height and self.grid[ny][nx]==0:
                # 使该墙变为通路
                self.grid[ny][nx] = 1
                return True
        return False

    def _resolve_box_content(self, box):
        """基于 box['type'] 决定服务器端盲盒产出（随机逻辑）"""
        r = random.random()
        if r < 0.4:
            return {"type":"coins", "amount": random.randint(30,80)}
        if r < 0.65:
            return {"type":"monster"}
        if r < 0.85:
            return {"type":"item", "id":"shield"}
        return {"type":"trap"}

    def _snapshot_player(self, p):
        """生成可序列化玩家快照（用于保存成绩等）"""
        return {
            "sid": p['sid'],
            "name": p['name'],
            "x": p['x'],
            "y": p['y'],
            "coins": p['coins'],
            "hp": p['hp'],
            "shield": p['shield'],
            "finished": p['finished'],
            "finish_time": p['finish_time']
        }

    # ---------------- 状态序列化（发送给客户端） ----------------
    def get_init_payload_for(self, sid):
        """返回连接某位玩家时需要的初始化数据（包含完整网格和世界元信息）"""
        with self.lock:
            payload = {
                "grid": self.grid,
                "width": self.width,
                "height": self.height,
                "start": list(self.start),
                "exit": list(self.exit),
                "shop": self.shop,
                "your_sid": sid,
                "players": [self._serialize_player(p) for p in self.players.values()],
                "traps_hint": [t for t in self.traps],  # 警示：陷阱一般不完全暴露，前端可选择低透明度显示
                "boxes": [b for b in self.boxes]
            }
            return payload

    def get_global_init_payload(self):
        """对所有玩家发送的完整初始化数据（例如生成新迷宫时）"""
        with self.lock:
            # 这里用一个通用版本，不带 your_sid（因为是广播）
            return {
                "grid": self.grid,
                "width": self.width,
                "height": self.height,
                "start": list(self.start),
                "exit": list(self.exit),
                "shop": self.shop,
                "players": [self._serialize_player(p) for p in self.players.values()],
                "traps_hint": [t for t in self.traps],
                "boxes": [b for b in self.boxes]
            }

    def get_state_payload(self):
        """返回当前世界快照（轻量级），用于频繁广播"""
        with self.lock:
            return {
                "players": [self._serialize_player(p) for p in self.players.values()],
                "boxes": [b for b in self.boxes],
                "traps_hint": [t for t in self.traps],  # 可选择性显示
                "exit": list(self.exit)
            }

    def get_leaderboard_snapshot(self):
        """
        为内存内排行榜提供基础（这里用数据库为准，发动时可从 DB 获取）
        但 engine 也可返回一个临时内存榜单（示例）
        """
        # 以玩家 finish_time 排序（仅本次在线玩家）
        with self.lock:
            finished = [p for p in self.players.values() if p['finished']]
            finished_sorted = sorted(finished, key=lambda x: x['finish_time'])
            # 返回若干字段，供前端显示
            return [{"name": p['name'], "time": p['finish_time'], "coins": p['coins']} for p in finished_sorted[:10]]

    # ---------------- 盲盒后台刷新任务 ----------------
    def _box_refresher(self):
        """周期性刷新盲盒或触发世界事件（每 20 秒刷新盲盒内容提示）"""
        while True:
            # 每 20 秒刷新一次（可长期运行）
            self.sock.sleep(20)
            with self.lock:
                # 简单示意：随机把一部分盒子位置替换为新的盒子（模拟“刷新内容”）
                if len(self.boxes) == 0: continue
                # 小概率改变某些盒子（示意性）
                for i in range(len(self.boxes)):
                    if random.random() < 0.3:
                        self.boxes[i]['coins'] = random.randint(10,80)
            # 广播盒子更新，让前端重新展示信息
            try:
                self.sock.emit('boxes_refreshed', {"boxes": [b for b in self.boxes]}, room='main')
            except Exception:
                pass
