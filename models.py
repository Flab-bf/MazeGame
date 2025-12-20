import random
import tkinter as tk
from tkinter import Canvas, simpledialog, messagebox, ttk
from PIL import Image, ImageTk
import time
import math
from game_3 import will_collide

#怪物及其逻辑
class Monster:
    MONSTER_TYPES = {
        "知识怪": {"speed": 3.0, "size_ratio": 0.6, "color": "purple", "img_path": r"D:\PythonProject\j\知识怪.png",
                   "prob": 10, "explode_radius": 0},
        "暴力怪": {"speed": 3.2, "size_ratio": 0.6, "color": "red", "img_path": r"D:\PythonProject\j\暴力怪.png",
                   "prob": 20, "explode_radius": 0},
        "爱财怪": {"speed": 3.7, "size_ratio": 0.6, "color": "yellow", "img_path": r"D:\PythonProject\j\爱财怪.png",
                   "prob": 15, "explode_radius": 0},
        "暴虐怪": {"speed": 3.8, "size_ratio": 0.6, "color": "black", "img_path": r"D:\PythonProject\j\暴虐怪.png",
                   "prob": 10, "explode_radius": 0},
        "弱智怪": {"speed": 3.5, "size_ratio": 0.7, "color": "green", "img_path": r"D:\PythonProject\j\弱智怪.png",
                   "prob": 15, "explode_radius": 0},
        "爆炸怪": {"speed": 3.8, "size_ratio": 0.8, "color": "orange", "img_path": r"D:\PythonProject\j\爆炸怪.png",
                   "prob": 20, "explode_radius": 100}
    }

    def __init__(self, x, y, cell_size, maze, frames_cache, monster_type=None):
        self.type = monster_type if monster_type else self.select_type_by_luck(50)
        self.config = self.MONSTER_TYPES[self.type]

        self.x = x
        self.y = y
        self.speed = self.config["speed"]
        self.size = int(cell_size * self.config["size_ratio"] - 30)
        self.color = self.config["color"]
        self.maze = maze
        self.cell_size = cell_size
        self.state = "active"
        self.explode_time = 0
        self.explode_radius = self.config["explode_radius"]
        self.explode_animation_progress = 0

        self.spawn_time = time.time()
        self.lifespan = 10.0 if self.type != "爆炸怪" else 30.0
        self.is_alive = True

        self.frames = frames_cache.get(self.type, None)
        self.current_frame = 0
        self.frame_timer = 0

    @classmethod
    def select_type_by_luck(cls, luck):
        total_prob = sum(data["prob"] for data in cls.MONSTER_TYPES.values())
        adjusted_probs = []
        for name, data in cls.MONSTER_TYPES.items():
            if name in ["知识怪", "暴虐怪"]:
                prob = data["prob"] * (1 + (luck - 50) / 100)
            else:
                prob = data["prob"] * (1 - (luck - 50) / 200)
            adjusted_probs.append((name, max(5, prob)))

        rand_val = random.uniform(0, sum(p for _, p in adjusted_probs))
        cumulative = 0
        for name, prob in adjusted_probs:
            cumulative += prob
            if rand_val <= cumulative:
                return name
        return random.choice(list(cls.MONSTER_TYPES.keys()))

    def update(self, player_x, player_y):
        # 1. 修正缩进错误（核心！原代码缩进错误导致逻辑失效）
        # 新增：检测是否中毒（无法移动）
        if id(self) in self.poisoned_monsters and time.time() < self.poisoned_monsters[id(self)]:
            return

        # 新增：检测玩家隐身（不索敌）【修正缩进】
        if hasattr(self, 'player_invisible') and self.player_invisible:
            return

        if time.time() - self.spawn_time > self.lifespan:
            self.is_alive = False
            return

        if self.type == "爆炸怪":
            if self.state == "exploding":
                if time.time() > self.explode_time:
                    self.state = "exploded"
                    self.is_alive = False
                remaining = self.explode_time - time.time()
                self.explode_animation_progress = 100 - int(remaining / 2 * 100)
            elif self.state == "exploded":
                if self.explode_animation_progress < 100:
                    self.explode_animation_progress += 2
                return  # 【修正缩进】爆炸完成后直接返回，不执行移动

        if self.frames:
            self.frame_timer += 1
            frame_interval = 40
            if self.type in ["弱智怪", "爱财怪"]:
                frame_interval = 40
            if self.frame_timer >= frame_interval:
                self.current_frame = (self.current_frame + 1) % len(self.frames)
                self.frame_timer = 0

        # 2. 替换移动逻辑为【自适应变向绕墙】（解决卡墙核心）
        dx = player_x - self.x
        dy = player_y - self.y
        distance = math.hypot(dx, dy)

        if distance > 0:
            # 基础移动向量（朝向玩家）
            base_move_x = (dx / distance) * self.speed
            base_move_y = (dy / distance) * self.speed

            # 优先直线移动
            if not will_collide(self.x, self.y, base_move_x, base_move_y, self.maze, self.cell_size, self.size):
                self.x += base_move_x
                self.y += base_move_y
            else:
                # 直线撞墙：生成候选方向（按相似度排序，避免乱走）
                candidate_dirs = [
                    (base_move_x, 0),  # 仅X方向（原朝向）
                    (0, base_move_y),  # 仅Y方向（原朝向）
                    (abs(base_move_x), 0),  # X正方向
                    (-abs(base_move_x), 0),  # X负方向
                    (0, abs(base_move_y)),  # Y正方向
                    (0, -abs(base_move_y))  # Y负方向
                ]

                # 遍历候选方向，找到第一个可行的
                moved = False
                for move_x, move_y in candidate_dirs:
                    if not will_collide(self.x, self.y, move_x, move_y, self.maze, self.cell_size, self.size):
                        self.x += move_x
                        self.y += move_y
                        moved = True
                        break

                # 兜底：微小偏移解决像素级贴墙
                if not moved:
                    tweak = 1  # 可根据cell_size调整（如cell_size=50则设为1）
                    tweak_dirs = [(tweak, 0), (-tweak, 0), (0, tweak), (0, -tweak)]
                    for tx, ty in tweak_dirs:
                        if not will_collide(self.x + tx, self.y + ty, 0, 0, self.maze, self.cell_size, self.size):
                            self.x += tx
                            self.y += ty
                            break

    #核心优化点（解决卡顿 + 卡墙）
    def get_current_frame(self):
        if self.frames:
            return self.frames[self.current_frame]
        return None

    def check_explode_collision(self, player_x, player_y, player_size):
        if self.state != "exploded":
            return False

        player_center_x = player_x + player_size / 2
        player_center_y = player_y + player_size / 2
        monster_center_x = self.x + self.size / 2
        monster_center_y = self.y + self.size / 2

        distance = math.hypot(player_center_x - monster_center_x, player_center_y - monster_center_y)
        return distance <= self.explode_radius

# 玩家角色类
class Player:
    PLAYER_TYPES = {
        "战士": {"speed": 5.0, "size_ratio": 0.9, "luck": 50, "hp": 100},
        "刺客": {"speed": 5.8, "size_ratio": 0.9, "luck": 70, "hp": 80},
        "盗贼": {"speed": 5.2, "size_ratio": 0.9, "luck": 90, "hp": 70}
    }

    def __init__(self, player_type, cell_size):
        self.type = player_type
        self.config = self.PLAYER_TYPES[player_type]
        self.speed = self.config["speed"]
        self.size = int(cell_size * self.config["size_ratio"] - 20)
        self.luck = self.config["luck"]
        self.hp = self.config["hp"]
        self.max_hp = self.config["hp"]  # 新增：最大生命值（用于回复药水上限）
        self.x = cell_size * 1
        self.y = cell_size * 1
        self.gold = 50
        self.control_reversed = False
        self.reverse_end_time = 0
        # 新增：装备相关属性
        self.equipment = []  # 持有装备列表
        self.shield_active = False  # 防护盾激活状态
        self.invisible = False  # 隐身状态
        self.invisible_end = 0  # 隐身结束时间
        self.poisoned_monsters = {}  # 中毒怪物字典 {monster_id: 结束时间}
        self.negative_effects = []  # 负面效果列表 ["reverse", ...]
        # 新增：透视药水相关属性
        self.clairvoyance = False  # 透视状态
        self.clairvoyance_end = 0  # 透视结束时间
        # 存储盲盒内容（透视用）
        self.box_contents = {}  # {(x,y): "金币/装备/怪物类型"}

# 新增：装备配置类
class EquipmentSystem:
    # 装备类型配置 - 新增透视药水和爆破弹
    EQUIP_TYPES = {
        1: {"name": "回复药水", "effect": "hp", "value": 10, "desc": "立即恢复10点生命值"},
        2: {"name": "速度药水", "effect": "speed", "value": 1.0, "desc": "永久增加1点移动速度"},
        3: {"name": "防护盾", "effect": "shield", "value": 1, "desc": "抵挡一次怪物伤害"},
        4: {"name": "隐身药水", "effect": "invisible", "value": 5, "desc": "5秒内不被怪物索敌"},
        5: {"name": "毒药", "effect": "poison", "value": 3, "desc": "使怪物3秒内无法移动"},
        6: {"name": "净化药水", "effect": "purify", "value": 1, "desc": "清除所有负面效果"},
        7: {"name": "透视药水", "effect": "clairvoyance", "value": 3, "desc": "3秒内可以看见盲盒里的物品"},
        8: {"name": "爆破弹", "effect": "bomb", "value": 1, "desc": "使用时可以消灭最近的一个怪物"}
    }

    @classmethod
    def get_random_equip(cls, count=1):
        """随机获取指定数量的装备"""
        equip_ids = random.sample(list(cls.EQUIP_TYPES.keys()), count)
        return [cls.EQUIP_TYPES[eq_id] for eq_id in equip_ids]

    @classmethod
    def use_equipment(cls, player, equip, monsters=None, box_positions=None, maze=None):
        """使用装备并触发对应效果"""
        equip_name = equip["name"]
        effect = equip["effect"]
        value = equip["value"]

        if effect == "hp":
            # 回复药水：生命值不超过最大值
            player.hp = min(player.hp + value, player.max_hp)
            msg = f"使用{equip_name}，生命值恢复{value}点！当前生命值：{player.hp}"

        elif effect == "speed":
            # 速度药水：永久增加速度
            player.speed += value
            msg = f"使用{equip_name}，速度永久增加{value}点！当前速度：{player.speed:.1f}"

        elif effect == "shield":
            # 防护盾：激活护盾
            player.shield_active = True
            msg = f"使用{equip_name}，防护盾已激活！可抵挡一次怪物伤害"

        elif effect == "invisible":
            # 隐身药水：设置隐身状态
            player.invisible = True
            player.invisible_end = time.time() + value
            msg = f"使用{equip_name}，进入隐身状态{value}秒！怪物无法发现你"

        elif effect == "poison":
            # 毒药：让所有怪物中毒
            if monsters and len(monsters) > 0:
                for monster in monsters:
                    player.poisoned_monsters[id(monster)] = time.time() + value
                msg = f"使用{equip_name}，所有怪物中毒{value}秒！无法移动"
            else:
                msg = f"使用{equip_name}，但当前没有怪物可中毒！"

        elif effect == "purify":
            # 净化药水：清除所有负面效果
            player.control_reversed = False
            player.reverse_end_time = 0
            player.negative_effects = []
            msg = f"使用{equip_name}，所有负面效果已清除！"

        elif effect == "clairvoyance":
            # 新增：透视药水逻辑
            player.clairvoyance = True
            player.clairvoyance_end = time.time() + value
            # 预先生成所有盲盒的内容
            player.box_contents = {}
            if box_positions and maze:
                for (x, y) in box_positions:
                    rand_val = random.random()
                    box_gold_prob = 0.15
                    box_equip_prob = 0.15
                    if rand_val < box_gold_prob:
                        gold_amount = random.randint(30, 80)
                        player.box_contents[(x, y)] = f"金币{gold_amount}枚"
                    elif rand_val < box_gold_prob + box_equip_prob:
                        equip = cls.get_random_equip(1)[0]
                        player.box_contents[(x, y)] = f"装备【{equip['name']}】"
                    else:
                        monster_type = Monster.select_type_by_luck(player.luck)
                        player.box_contents[(x, y)] = f"怪物【{monster_type}】"
            msg = f"使用{equip_name}，进入透视状态{value}秒！可以看到盲盒里的内容"

        elif effect == "bomb":
            # 新增：爆破弹逻辑
            if monsters and len(monsters) > 0:
                # 找到最近的怪物
                closest_monster = None
                min_distance = float('inf')
                player_center_x = player.x + player.size / 2
                player_center_y = player.y + player.size / 2

                for monster in monsters:
                    if monster.is_alive:
                        monster_center_x = monster.x + monster.size / 2
                        monster_center_y = monster.y + monster.size / 2
                        distance = math.hypot(player_center_x - monster_center_x,
                                              player_center_y - monster_center_y)
                        if distance < min_distance:
                            min_distance = distance
                            closest_monster = monster

                if closest_monster:
                    closest_monster.is_alive = False
                    # 更新击败怪物计数
                    if hasattr(player, 'monsters_defeated'):
                        player.monsters_defeated += 1
                    msg = f"使用{equip_name}，消灭了最近的{closest_monster.type}！"
                else:
                    msg = f"使用{equip_name}，但当前没有存活的怪物！"
            else:
                msg = f"使用{equip_name}，但当前没有怪物可消灭！"

        else:
            msg = f"{equip_name}使用失败，未知效果！"

        return msg

