import random
import tkinter as tk
from tkinter import Canvas, simpledialog, messagebox, ttk
from PIL import Image, ImageTk
import time
import math
from models import *

import numpy as np
# 优化迷宫生成逻辑（带环、多分支、增加可玩性）
def generate_maze(size):
    """
    生成带多路径（起点→终点）、起点死胡同、环路、盲盒的迷宫
    :param size: 迷宫尺寸（最终会转为奇数）
    :return: 迷宫二维数组（0=墙,1=路径,2=终点,3=盲盒）、盲盒位置列表
    """
    # 确保尺寸为奇数，保证墙壁/路径布局合理
    size = size if size % 2 == 1 else size + 1
    if size < 9:  # 最小尺寸提升到9，确保起点有足够空间做多路径
        size = 9

    # 初始化迷宫：0=墙，1=路径，2=终点，3=盲盒
    maze = np.zeros((size, size))
    start_x, start_y = 1, 1  # 起点固定在左上角
    end_x, end_y = size - 2, size - 2  # 终点固定在右下角
    maze[start_y][start_x] = 1  # 标记起点为路径
    maze[end_y][end_x] = 2  # 标记终点

    # 方向定义（上下左右）：分两步 - 第一步：紧邻墙（步长1），第二步：路径延伸（步长2）
    dirs_step1 = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # 紧邻墙壁（步长1）
    dirs_step2 = [(-2, 0), (2, 0), (0, -2), (0, 2)]  # 路径延伸（步长2）
    visited = set()  # 记录已访问的路径节点
    visited.add((start_x, start_y))

    # -------------------------- 核心优化：起点开局就有多条可见路径 --------------------------
    # 1. 强制为起点选择2-3个方向，直接打通紧邻的墙（开局就能看到岔路）
    start_exit_count = random.randint(2, 3)  # 起点出口数量（2-3个）
    random.shuffle(dirs_step1)
    start_exits = []  # 存储起点的直接出口（紧邻的路径节点）

    for i in range(start_exit_count):
        dx1, dy1 = dirs_step1[i]  # 紧邻墙的方向（步长1）
        wall_x, wall_y = start_x + dx1, start_y + dy1  # 起点和分支之间的墙
        dx2, dy2 = dx1 * 2, dy1 * 2  # 分支延伸的方向（步长2）
        branch_x, branch_y = start_x + dx2, start_y + dy2  # 分支的第一个路径节点

        # 确保分支在迷宫范围内
        if 1 <= branch_x < size - 1 and 1 <= branch_y < size - 1:
            # 第一步：打通起点紧邻的墙（开局可见的岔路）
            maze[wall_y][wall_x] = 1
            # 第二步：标记分支节点为路径（起点出口延伸）
            maze[branch_y][branch_x] = 1
            visited.add((branch_x, branch_y))
            start_exits.append((branch_x, branch_y))

    # 兜底：如果随机选的方向无效，强制补全出口
    if len(start_exits) < 2:
        for dx1, dy1 in dirs_step1:
            wall_x, wall_y = start_x + dx1, start_y + dy1
            dx2, dy2 = dx1 * 2, dy1 * 2
            branch_x, branch_y = start_x + dx2, start_y + dy2
            if 1 <= branch_x < size - 1 and 1 <= branch_y < size - 1 and (branch_x, branch_y) not in visited:
                maze[wall_y][wall_x] = 1
                maze[branch_y][branch_x] = 1
                visited.add((branch_x, branch_y))
                start_exits.append((branch_x, branch_y))
                if len(start_exits) >= 2:
                    break

    # -------------------------- 核心优化：每条起点分支独立扩展（保证多路径） --------------------------
    # 初始化栈：每条起点分支单独入栈，确保每条路径都能独立延伸到终点
    stack = start_exits.copy()
    # 基础DFS扩展：优先扩展起点分支，保证多条路径的独立性
    while stack:
        curr_x, curr_y = stack[-1]
        random.shuffle(dirs_step2)
        neighbors = []
        # 为当前分支寻找未访问的延伸节点
        for dx, dy in dirs_step2:
            nx, ny = curr_x + dx, curr_y + dy
            if 1 <= nx < size - 1 and 1 <= ny < size - 1 and (nx, ny) not in visited:
                neighbors.append((nx, ny, dx, dy))

        if neighbors:
            # 选择一个邻居扩展当前分支
            nx, ny, dx, dy = random.choice(neighbors)
            visited.add((nx, ny))
            maze[ny][nx] = 1  # 标记分支路径
            # 打通当前节点和邻居之间的墙
            maze[curr_y + dy // 2][curr_x + dx // 2] = 1
            stack.append((nx, ny))
        else:
            stack.pop()

    # -------------------------- 核心保留：起点周边专属死胡同（增加迷惑性） --------------------------
    # 在起点未用作出口的方向生成死胡同（开局就有假路）
    unused_dirs = [d for d in dirs_step1 if d not in dirs_step1[:start_exit_count]]
    dead_end_from_start = random.randint(1, min(2, len(unused_dirs)))  # 1-2条死胡同

    for i in range(dead_end_from_start):
        dx1, dy1 = unused_dirs[i]
        # 死胡同第一步：打通起点紧邻的墙（看起来像真路径）
        wall_x, wall_y = start_x + dx1, start_y + dy1
        # 死胡同第二步：延伸1-2步后终止（形成死路）
        dx2, dy2 = dx1 * 2, dy1 * 2
        dead_x1, dead_y1 = start_x + dx2, start_y + dy2
        dx3, dy3 = dx1 * 3, dy1 * 3
        dead_x2, dead_y2 = start_x + dx3, start_y + dy3

        if 1 <= dead_x2 < size - 1 and 1 <= dead_y2 < size - 1:
            # 打通墙，制造死胡同的视觉效果
            maze[wall_y][wall_x] = 1
            maze[dead_y1][dead_x1] = 1  # 死胡同第一段
            maze[start_y + dy1 * 2][start_x + dx1 * 2] = 1  # 中间墙
            maze[dead_y2][dead_x2] = 1  # 死胡同末端（无后续）

    # -------------------------- 优化：强化多路径环路（让分支互通） --------------------------
    loop_probability = 0.5  # 提升到50%概率生成环路，让多条路径互相连通
    for y in range(1, size - 1, 2):
        for x in range(1, size - 1, 2):
            if maze[y][x] == 1 and random.random() < loop_probability:
                random.shuffle(dirs_step2)
                # 随机选1-2个方向打通额外的墙，形成环路
                for dx, dy in dirs_step2[:random.randint(1, 2)]:
                    nx, ny = x + dx, y + dy
                    mx, my = x + dx // 2, y + dy // 2
                    if 1 <= nx < size - 1 and 1 <= ny < size - 1 and maze[ny][nx] == 0:
                        maze[ny][nx] = 1
                        maze[my][mx] = 1

    # -------------------------- 保留：全局死胡同（增加整体可玩性） --------------------------
    dead_end_prob = 0.2  # 降低全局死胡同概率，避免干扰主路径
    for y in range(1, size - 1, 2):
        for x in range(1, size - 1, 2):
            if maze[y][x] == 1 and (x, y) != (start_x, start_y) and random.random() < dead_end_prob:
                random.shuffle(dirs_step2)
                for dx, dy in dirs_step2[:1]:
                    nx, ny = x + dx, y + dy
                    mx, my = x + dx // 2, y + dy // 2
                    if 1 <= nx < size - 1 and 1 <= ny < size - 1 and maze[ny][nx] == 0:
                        maze[my][mx] = 1
                        maze[ny][nx] = 1  # 死胡同末端
                        break

    # -------------------------- 兜底：确保所有起点分支连通到终点 --------------------------
    # 检查每条起点分支是否连通终点，不连通则强制打通
    from collections import deque
    def is_connected(start, end, maze):
        """检查两点是否连通"""
        q = deque([start])
        visited_check = set([start])
        while q:
            x, y = q.popleft()
            if (x, y) == end:
                return True
            for dx, dy in dirs_step1:
                nx, ny = x + dx, y + dy
                if 0 <= nx < size and 0 <= ny < size and maze[ny][nx] in (1, 2) and (nx, ny) not in visited_check:
                    visited_check.add((nx, ny))
                    q.append((nx, ny))
        return False

    # 强制打通未连通的分支到主路径
    for branch in start_exits:
        if not is_connected(branch, (end_x, end_y), maze):
            # 从分支向终点方向打通
            curr_x, curr_y = branch
            for _ in range(3):  # 最多延伸3步
                # 向终点方向移动
                dx = 1 if end_x > curr_x else -1 if end_x < curr_x else 0
                dy = 1 if end_y > curr_y else -1 if end_y < curr_y else 0
                nx, ny = curr_x + dx, curr_y + dy
                if 1 <= nx < size - 1 and 1 <= ny < size - 1:
                    maze[ny][nx] = 1
                    curr_x, curr_y = nx, ny
                    maze[end_x][end_y] = 2
                else:
                    break

    # -------------------------- 放置盲盒（路径上随机位置） --------------------------
    box_count = min(10, size // 2)  # 盲盒数量随尺寸调整
    valid_box_pos = []
    for y in range(size):
        for x in range(size):
            # 盲盒避开起点/终点，只放在路径上
            if maze[y][x] == 1 and (x, y) != (start_x, start_y) and (x, y) != (end_x, end_y):
                valid_box_pos.append((x, y))

    box_pos_list = []
    if valid_box_pos:
        box_pos_list = random.sample(valid_box_pos, min(box_count, len(valid_box_pos)))
        for (x, y) in box_pos_list:
            maze[y][x] = 3  # 3标记盲盒

    return maze, box_pos_list

# 优化碰撞检测（减少向上移动时的冗余计算）
def will_collide(x, y, dx, dy, maze, cell_size, entity_size):
    new_x = x + dx
    new_y = y + dy
    # 只检测关键点位（减少8个点→4个点，提升效率）
    check_points = [
        (new_x, new_y),
        (new_x + entity_size, new_y),
        (new_x, new_y + entity_size),
        (new_x + entity_size, new_y + entity_size)
    ]
    for cx, cy in check_points:
        c_grid_x = int(cx // cell_size)
        c_grid_y = int(cy // cell_size)
        if 0 <= c_grid_x < len(maze[0]) and 0 <= c_grid_y < len(maze):
            if maze[c_grid_y][c_grid_x] == 0:
                return True
    if new_x < 0 or new_x + entity_size > cell_size * len(maze[0]):
        return True
    if new_y < 0 or new_y + entity_size > cell_size * len(maze):
        return True
    return False


def split_spritesheet(image_path, rows, cols):
    try:
        img = Image.open(image_path)
        s_w, s_h = img.size
        width = s_w // cols
        height = s_h // rows
        frames = []
        for row in range(rows):
            for col in range(cols):
                box = (col * width, row * height, (col + 1) * width, (row + 1) * height)
                frame = img.crop(box)
                frames.append(frame)
        return frames
    except Exception as e:
        print(f"图片切割错误: {e}")
        return []


def resize_frames(frames, size):
    return [frame.resize((size, size), Image.LANCZOS) for frame in frames]

class MazeGame:
    def __init__(self, root):
        self.root = root
        self.root.title("迷宫盲盒怪物追击")
        self.root.geometry("800x800")
        self.root.resizable(True, True)

        self.size = 27
        self.cell_size = 50
        self.game_over = False
        self.game_win = False
        self.selected_player_type = None
        self.paused = False  # 新增：游戏暂停标志（解决对话框阻塞问题）
        self.end_screen_created = False  # 新增：标记结束界面是否已创建
        self.monsters_defeated = 0  # 新增：击败怪物计数器

        # ========== 修改：调整盲盒奖励概率 ==========
        # 提高怪物概率（70%），降低金币（15%）和装备（15%）概率
        self.box_gold_prob = 0.15  # 原0.3 → 改为0.15
        self.box_equip_prob = 0.15  # 原0.2 → 改为0.15
        # 剩余70%概率开出怪物（1 - 0.15 - 0.15 = 0.7）
        self.gold_min = 30  # 金币最小值
        self.gold_max = 80  # 金币最大值

        # 新增：盲盒奖励提示文本（用于非阻塞显示）
        self.box_reward_text = ""
        self.box_reward_show_time = 0

        # 新增：记录终点坐标（方便检测）
        self.end_grid_x = self.size - 2
        self.end_grid_y = self.size - 2

        self.box_color = "#FFD700"
        self.box_size = self.cell_size - 5
        self.last_box_refresh = time.time()
        self.box_refresh_interval = 20
        self.box_positions = []
        self.box_refresh_highlight = 0

        self.monsters = []
        self.monster_frames_cache = {}

        self.invincible = False
        self.invincible_end = 0
        self.invincible_duration = 2.0

        # 新增：动画帧率控制参数（避免硬编码）
        self.animation_frame_interval = 15
        self.animation_frame_count = 3  # 4行3列→每方向3帧
        self.last_animation_time = time.time()  # 基于时间戳控制动画

        self.init_character_select()
    def init_character_select(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        self.select_frame = tk.Frame(self.root, bg="#f0f8ff")
        self.select_frame.pack(fill=tk.BOTH, expand=True)

        title_label = tk.Label(
            self.select_frame,
            text="⚔️ 选择你的冒险角色 ⚔️",
            font=("微软雅黑", 28, "bold"),
            bg="#f0f8ff",
            fg="#2c3e50"
        )
        title_label.pack(pady=40)

        card_container = tk.Frame(self.select_frame, bg="#f0f8ff")
        card_container.pack(fill=tk.X, padx=80, pady=20)

        for char_name, attr in Player.PLAYER_TYPES.items():
            card = tk.Frame(
                card_container,
                bg="white",
                relief=tk.RAISED,
                bd=4,
                padx=20,
                pady=20
            )
            card.pack(side=tk.LEFT, expand=True, padx=15, pady=10)

            name_lbl = tk.Label(
                card,
                text=char_name,
                font=("微软雅黑", 20, "bold"),
                bg="white",
                fg="#e74c3c"
            )
            name_lbl.pack(pady=10)

            attr_text = f"""
速度：{attr['speed']}
体型：{attr['size_ratio']}
幸运值：{attr['luck']}
生命值：{attr['hp']}
            """
            attr_lbl = tk.Label(
                card,
                text=attr_text,
                font=("微软雅黑", 12),
                bg="white",
                fg="#34495e",
                justify=tk.LEFT
            )
            attr_lbl.pack(pady=5)

            select_btn = tk.Button(
                card,
                text="选择",
                font=("微软雅黑", 12, "bold"),
                bg="#3498db",
                fg="white",
                padx=20,
                pady=5,
                command=lambda c=char_name: self.start_game(c)
            )
            select_btn.pack(pady=10)

    def start_game(self, player_type):
        self.selected_player_type = player_type
        self.select_frame.destroy()

        self.player = Player(self.selected_player_type, self.cell_size)
        # 给玩家添加击败怪物计数属性
        self.player.monsters_defeated = 0
        self.preload_all_assets()
        self.maze, self.box_positions = generate_maze(self.size)

        self.directions = {"up": False, "down": False, "left": False, "right": False}

        self.canvas = Canvas(self.root, bg="#e3e3e3")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # 新增：装备使用按钮
        self.create_equipment_buttons()

        self.root.bind("<KeyPress>", self.on_key_press)
        self.root.bind("<KeyRelease>", self.on_key_release)
        self.root.bind("<Configure>", self.on_resize)

        self.game_loop()

    def create_equipment_buttons(self):
        """创建装备使用按钮面板"""
        self.equip_frame = tk.Frame(self.root, bg="#f0f8ff", relief=tk.RAISED, bd=2)
        self.equip_frame.place(x=10, y=150, width=180, height=200)

        # 装备面板标题
        tk.Label(
            self.equip_frame,
            text="📦 装备栏",
            font=("微软雅黑", 14, "bold"),
            bg="#f0f8ff",
            fg="#2c3e50"
        ).pack(pady=5)

        # 装备按钮容器（滚动条）
        self.equip_btn_frame = tk.Frame(self.equip_frame, bg="#f0f8ff")
        self.equip_btn_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def update_equipment_buttons(self):
        """更新装备栏按钮"""
        # 清空原有按钮
        for widget in self.equip_btn_frame.winfo_children():
            widget.destroy()

        # 为每个装备创建按钮
        for idx, equip in enumerate(self.player.equipment):
            btn = tk.Button(
                self.equip_btn_frame,
                text=equip["name"],
                font=("微软雅黑", 10),
                bg="#9b59b6",
                fg="white",
                width=15,
                command=lambda e=equip: self.use_equipment(e)
            )
            btn.pack(pady=2)

        # 如果没有装备，显示提示
        if len(self.player.equipment) == 0:
            tk.Label(
                self.equip_btn_frame,
                text="暂无装备",
                font=("微软雅黑", 10),
                bg="#f0f8ff",
                fg="#95a5a6"
            ).pack(pady=20)

    def use_equipment(self, equip):
        """使用装备的回调函数 - 传递更多参数给装备使用方法"""
        if self.game_over or self.paused:
            return

        # 使用装备并获取提示信息 - 新增传递box_positions和maze参数
        msg = EquipmentSystem.use_equipment(self.player, equip, self.monsters,
                                            self.box_positions, self.maze)

        # 从装备列表中移除已使用的装备
        self.player.equipment.remove(equip)

        # 更新装备栏按钮
        self.update_equipment_buttons()

        # 显示使用结果
        messagebox.showinfo("装备使用", msg)

    def preload_all_assets(self):
        self.load_player_assets()
        self.preload_monster_frames()  # 补充调用怪物资源预加载

    def preload_monster_frames(self):
        for monster_type, config in Monster.MONSTER_TYPES.items():
            try:
                if monster_type in ["弱智怪", "爱财怪"]:
                    sprite_frames = split_spritesheet(config["img_path"], 4, 3)
                else:
                    sprite_frames = split_spritesheet(config["img_path"], 4, 4)

                if sprite_frames:
                    size = int(self.cell_size * config["size_ratio"] - 2)
                    resized_frames = resize_frames(sprite_frames, size)
                    self.monster_frames_cache[monster_type] = [ImageTk.PhotoImage(f) for f in resized_frames]
                else:
                    self.monster_frames_cache[monster_type] = None
            except Exception as e:
                print(f"预加载{monster_type}怪物图片失败: {e}")
                self.monster_frames_cache[monster_type] = None

    # 修复核心：玩家动画帧索引（4行3列→总12帧，按方向分配）
    def load_player_assets(self):
        try:
            char_images = {
                "战士": r"D:\PythonProject\j\角色1.png",
                "刺客": r"D:\PythonProject\j\角色2.png",
                "盗贼": r"D:\PythonProject\j\角色3.png"
            }
            # 4行3列 → 总12帧
            frames = split_spritesheet(char_images[self.player.type], 4, 3)
            resized_frames = resize_frames(frames, self.player.size)

            # 正确分配方向帧（每方向3帧，避免索引越界）
            self.player_frames = {
                "down": [ImageTk.PhotoImage(f) for f in resized_frames[0:3]],  # 第1行：0-2
                "left": [ImageTk.PhotoImage(f) for f in resized_frames[3:6]],  # 第2行：3-5
                "right": [ImageTk.PhotoImage(f) for f in resized_frames[6:9]],  # 第3行：6-8
                "up": [ImageTk.PhotoImage(f) for f in resized_frames[9:12]]  # 第4行：9-11（修复上键帧！）
            }
            self.current_frame = self.player_frames["down"][0]
            self.frame_index = 0
            self.frame_timer = 0
        except Exception as e:
            print(f"加载玩家图片失败: {e}")
            self.player_frames = None
            self.current_frame = None

    def load_image(self, path, size):
        try:
            img = Image.open(path)
            img = img.resize(size, Image.LANCZOS)
            return ImageTk.PhotoImage(img)
        except Exception as e:
            print(f"加载图片{path}失败: {e}")
            return None

    # 优化按键处理（减少反向控制的映射开销）
    def on_key_press(self, event):
        if self.game_over or self.paused:  # 暂停时忽略按键
            return
        key = event.keysym.lower()
        if self.player.control_reversed:
            key_map = {"up": "down", "down": "up", "left": "right", "right": "left"}
            key = key_map.get(key, key)
        if key in ["up", "down", "left", "right"]:
            self.directions[key] = True

    def on_key_release(self, event):
        if self.game_over or self.paused:  # 暂停时忽略按键
            return
        key = event.keysym.lower()
        if self.player.control_reversed:
            key_map = {"up": "down", "down": "up", "left": "right", "right": "left"}
            key = key_map.get(key, key)
        if key in ["up", "down", "left", "right"]:
            self.directions[key] = False

    def on_resize(self, event):
        self.draw()

    def update_player(self):
        # 新增：检测透视状态过期
        if self.player.clairvoyance and time.time() > self.player.clairvoyance_end:
            self.player.clairvoyance = False
            self.player.box_contents = {}

        # 原有代码保持不变
        if self.player.invisible and time.time() > self.player.invisible_end:
            self.player.invisible = False

        if self.player.control_reversed and time.time() > self.player.reverse_end_time:
            self.player.control_reversed = False

        dx, dy = 0, 0
        if self.directions["up"]:
            dy -= self.player.speed
        if self.directions["down"]:
            dy += self.player.speed
        if self.directions["left"]:
            dx -= self.player.speed
        if self.directions["right"]:
            dx += self.player.speed

        if not will_collide(self.player.x, self.player.y, dx, dy, self.maze, self.cell_size, self.player.size):
            self.player.x += dx
            self.player.y += dy

        self.check_box_collision()

        # ========== 终极修复：终点检测逻辑 ==========
        # 1. 计算终点的像素范围
        end_pixel_x1 = self.end_grid_x * self.cell_size
        end_pixel_y1 = self.end_grid_y * self.cell_size
        end_pixel_x2 = end_pixel_x1 + self.cell_size
        end_pixel_y2 = end_pixel_y1 + self.cell_size

        # 2. 计算玩家的像素范围
        player_x1 = self.player.x
        player_y1 = self.player.y
        player_x2 = self.player.x + self.player.size
        player_y2 = self.player.y + self.player.size

        # 3. 矩形碰撞检测（玩家和终点格子有重叠就判定到达）
        if (player_x1 < end_pixel_x2 and
                player_x2 > end_pixel_x1 and
                player_y1 < end_pixel_y2 and
                player_y2 > end_pixel_y1):
            self.game_over = True
            self.game_win = True
            return

        self.update_player_animation()

    def check_box_collision(self):
        grid_x = int(self.player.x // self.cell_size)
        grid_y = int(self.player.y // self.cell_size)
        if 0 <= grid_x < len(self.maze[0]) and 0 <= grid_y < len(self.maze):
            if self.maze[grid_y][grid_x] == 3:
                # 移除盲盒标记
                self.maze[grid_y][grid_x] = 1
                if (grid_x, grid_y) in self.box_positions:
                    self.box_positions.remove((grid_x, grid_y))

                # 新增：盲盒随机奖励（金币/装备/怪物）
                rand_val = random.random()
                if rand_val < self.box_gold_prob:
                    # 开出金币
                    gold_amount = random.randint(self.gold_min, self.gold_max)
                    self.player.gold += gold_amount
                    # ========== 修改：替换阻塞式messagebox为非阻塞文本提示 ==========
                    self.box_reward_text = f"🎉 获得{gold_amount}枚金币！当前：{self.player.gold}"
                    self.box_reward_show_time = time.time() + 3  # 显示3秒

                elif rand_val < self.box_gold_prob + self.box_equip_prob:
                    # 开出装备
                    equip = EquipmentSystem.get_random_equip(1)[0]
                    self.player.equipment.append(equip)
                    self.update_equipment_buttons()
                    # ========== 修改：替换阻塞式messagebox为非阻塞文本提示 ==========
                    self.box_reward_text = f"🎉 获得【{equip['name']}】！{equip['desc']}"
                    self.box_reward_show_time = time.time() + 3  # 显示3秒

                else:
                    # 开出怪物（原有逻辑）
                    monster_x = grid_x * self.cell_size + 5
                    monster_y = grid_y * self.cell_size + 5
                    monster_type = Monster.select_type_by_luck(self.player.luck)
                    self.monsters.append(
                        Monster(monster_x, monster_y, self.cell_size, self.maze, self.monster_frames_cache,
                                monster_type))
                    self.handle_special_monster_effects(self.monsters[-1])
                    # ========== 修改：添加怪物提示 ==========
                    self.box_reward_text = f"⚠️ 开出{monster_type}！小心追击！"
                    self.box_reward_show_time = time.time() + 3  # 显示3秒

                # 无论开出什么都给予短暂无敌
                self.invincible = True
                self.invincible_end = time.time() + self.invincible_duration

    def handle_special_monster_effects(self, monster):
        if monster.type == "知识怪":
            self.handle_knowledge_monster(monster)
        elif monster.type == "爱财怪":
            self.handle_money_monster(monster)

    # 修复核心：知识怪处理函数（暂停游戏+重置方向键+恢复焦点+新增装备奖励）
    def handle_knowledge_monster(self, monster):
        # 1. 暂停游戏，重置所有方向键状态（关键！避免对话框阻塞导致按键残留）
        self.paused = True
        self.directions = {"up": False, "down": False, "left": False, "right": False}

        questions = [
            {"question": "1+1等于几?", "answer": "2"},
            {"question": "9*9=?", "answer": "81"},
            {"question": "地球是什么形状?", "answer": "圆形"},
            {"question": "3+2=?", "answer": "5"}
        ]
        q = random.choice(questions)
        answer = simpledialog.askstring("知识问答", q["question"], parent=self.root)

        # 处理用户关闭对话框的情况（answer为None）
        if answer is None:
            answer = ""

        if answer.lower() == q["answer"].lower():
            monster.is_alive = False
            self.monsters_defeated += 1  # 新增：击败怪物计数+1
            self.player.monsters_defeated += 1

            # 新增：回答正确掉落1-2件装备
            equip_count = random.randint(1, 2)
            equips = EquipmentSystem.get_random_equip(equip_count)
            equip_names = [eq["name"] for eq in equips]
            equip_descs = [f"【{eq['name']}】：{eq['desc']}" for eq in equips]

            # 添加装备到玩家背包
            self.player.equipment.extend(equips)
            self.update_equipment_buttons()

            # ========== 修改：保留messagebox（问答类必须阻塞），但优化提示 ==========
            messagebox.showinfo("正确",
                                f"回答正确！怪物消失了！\n"
                                f"获得{equip_count}件装备奖励：\n" + "\n".join(equip_descs))
        else:
            messagebox.showinfo("错误", "回答错误！怪物开始追击你！")

        # 2. 恢复游戏，强制聚焦主窗口（确保按键事件能被捕获）
        self.paused = False
        self.root.focus_set()  # 关键：让主窗口重新获得焦点

    # 修复核心：爱财怪处理函数（同知识怪，避免对话框导致的移动问题）
    def handle_money_monster(self, monster):
        # 1. 暂停游戏，重置方向键
        self.paused = True
        self.directions = {"up": False, "down": False, "left": False, "right": False}

        required_gold = random.randint(10, 30)
        if self.player.gold >= required_gold:
            response = messagebox.askyesno("爱财怪", f"爱财怪要求你支付{required_gold}金币，是否支付？")
            if response:
                self.player.gold -= required_gold
                monster.is_alive = False
                self.monsters_defeated += 1  # 新增：击败怪物计数+1
                self.player.monsters_defeated += 1
                messagebox.showinfo("成功", f"支付了{required_gold}金币，怪物消失了！")
            else:
                monster.type = "暴虐怪"
                monster.config = Monster.MONSTER_TYPES["暴虐怪"]
                monster.speed = monster.config["speed"]
                monster.color = monster.config["color"]
                messagebox.showinfo("警告", "你拒绝支付！爱财怪变成了暴虐怪！")
        else:
            monster.type = "暴虐怪"
            monster.config = Monster.MONSTER_TYPES["暴虐怪"]
            monster.speed = monster.config["speed"]
            monster.color = monster.config["color"]
            messagebox.showinfo("警告", f"你没有足够的金币（需要{required_gold}）！爱财怪变成了暴虐怪！")

        # 2. 恢复游戏，聚焦主窗口
        self.paused = False
        self.root.focus_set()

    # 优化动画更新（基于时间戳，避免卡顿）
    def update_player_animation(self):
        if not self.player_frames:
            return

        # 基于时间戳控制动画（避免游戏循环波动导致卡顿）
        current_time = time.time()
        if current_time - self.last_animation_time >= self.animation_frame_interval / 1000:
            self.frame_index = (self.frame_index + 1) % self.animation_frame_count
            self.last_animation_time = current_time

        # 优化方向判断顺序（减少冗余）
        if self.directions["down"]:
            self.current_frame = self.player_frames["down"][self.frame_index]
        elif self.directions["up"]:
            self.current_frame = self.player_frames["up"][self.frame_index]  # 修复后可正常显示
        elif self.directions["right"]:
            self.current_frame = self.player_frames["right"][self.frame_index]
        elif self.directions["left"]:
            self.current_frame = self.player_frames["left"][self.frame_index]
        else:
            self.current_frame = self.player_frames["down"][0]

    def update_monsters(self):
        self.monsters = [m for m in self.monsters if m.is_alive or m.state == "exploded"]

        # 新增：传递玩家隐身状态给怪物
        for monster in self.monsters:
            monster.player_invisible = self.player.invisible
            monster.poisoned_monsters = self.player.poisoned_monsters

        for monster in self.monsters:
            if monster.is_alive:
                # 新增：检测暴虐怪的5秒消失逻辑
                if hasattr(monster, 'disappear_time') and time.time() > monster.disappear_time:
                    monster.is_alive = False
                    continue
                monster.update(self.player.x, self.player.y)

                if not self.invincible and self.check_entity_collision(monster):
                    # 新增：检测防护盾
                    if self.player.shield_active:
                        # 防护盾抵挡伤害
                        self.player.shield_active = False
                        # ========== 修改：防护盾提示也改为非阻塞 ==========
                        self.box_reward_text = "🛡️ 防护盾抵挡了一次伤害！"
                        self.box_reward_show_time = time.time() + 2
                        continue

                    self.handle_monster_collision(monster)
                    if self.game_over:
                        break

            if monster.type == "爆炸怪" and monster.state == "exploded":
                if monster.check_explode_collision(self.player.x, self.player.y, self.player.size):
                    self.game_over = True
                    self.game_win = False
                    break

        # 清理过期的中毒状态
        expired_ids = []
        for monster_id, end_time in self.player.poisoned_monsters.items():
            if time.time() > end_time:
                expired_ids.append(monster_id)
        for monster_id in expired_ids:
            del self.player.poisoned_monsters[monster_id]

        if self.invincible and time.time() > self.invincible_end:
            self.invincible = False

        current_time = time.time()
        if current_time - self.last_box_refresh > self.box_refresh_interval:
            self.refresh_boxes()
            self.last_box_refresh = current_time

    def refresh_boxes(self):
        if not self.box_positions:
            return

        for (x, y) in self.box_positions:
            self.maze[y][x] = 1
        for (x, y) in self.box_positions:
            self.maze[y][x] = 3

        self.box_refresh_highlight = time.time() + 5

    # ========== 核心修改：怪物攻击伤害机制 ==========
    def handle_monster_collision(self, monster):
        tip = ""
        # 暴力怪：一击必杀，直接设置生命值为0
        if monster.type == "暴力怪":
            self.player.hp = 0
            tip = f"⚠️ 被{monster.type}攻击！一击必杀！"
            monster.is_alive = True  # 怪物继续存在
        # 暴虐怪：减50生命值，回到起点，5秒后消失
        elif monster.type == "暴虐怪":
            self.player.hp -= 50
            self.player.x = self.cell_size * 1
            self.player.y = self.cell_size * 1
            tip = f"⚠️ 被{monster.type}攻击！HP-50，回到起点！"
            # 设置暴虐怪5秒后消失
            monster.disappear_time = time.time() + 5
            monster.is_alive = True
        # 知识怪：减50生命值，保留原有属性惩罚
        elif monster.type == "知识怪":
            self.player.hp -= 50
            self.player.speed -= 0.1
            monster.is_alive = True
            tip = f"⚠️ 被{monster.type}攻击！HP-50"
        # 爱财怪：减50生命值，保留原有金币惩罚
        elif monster.type == "爱财怪":
            self.player.hp -= 50
            self.player.gold -= 10
            monster.is_alive = True
            tip = f"⚠️ 被{monster.type}攻击！HP-50"
        # 弱智怪：减50生命值，保留原有反向控制效果
        elif monster.type == "弱智怪":
            self.player.hp -= 50
            self.player.control_reversed = True
            self.player.reverse_end_time = time.time() + 5
            self.player.speed -= 0.3
            monster.is_alive = False
            tip = f"⚠️ 被{monster.type}攻击！HP-50，控制反向5秒！"
        # 爆炸怪：减50生命值，保留原有爆炸逻辑
        elif monster.type == "爆炸怪":
            self.player.hp -= 50
            monster.state = "exploding"
            monster.explode_time = time.time() + 2
            tip = f"⚠️ 被{monster.type}攻击！HP-50，即将爆炸！"

        # 设置碰撞提示文本
        self.box_reward_text = tip
        self.box_reward_show_time = time.time() + 2

        # 生命值≤0则游戏失败
        if self.player.hp <= 0:
            self.game_over = True
            self.game_win = False

    def check_entity_collision(self, monster):
        return (
                self.player.x < monster.x + monster.size and
                self.player.x + self.player.size > monster.x and
                self.player.y < monster.y + monster.size and
                self.player.y + self.player.size > monster.y
        )

    def draw_explode_effect(self, monster, scale, offset_x, offset_y):
        if monster.state != "exploded" and monster.state != "exploding":
            return

        monster_center_x = offset_x + (monster.x + monster.size / 2) * scale
        monster_center_y = offset_y + (monster.y + monster.size / 2) * scale
        explode_radius = monster.explode_radius * scale

        if monster.state == "exploding":
            progress = monster.explode_animation_progress / 100
            radius = explode_radius * progress
            self.canvas.create_oval(
                monster_center_x - radius, monster_center_y - radius,
                monster_center_x + radius, monster_center_y + radius,
                outline="#ff4444", width=3, dash=(5, 5)
            )
        else:
            progress = min(monster.explode_animation_progress / 100, 1)
            outer_radius = explode_radius * progress
            self.canvas.create_oval(
                monster_center_x - outer_radius, monster_center_y - outer_radius,
                monster_center_x + outer_radius, monster_center_y + outer_radius,
                outline="#ff0000", width=5
            )
            middle_radius = outer_radius * 0.7
            self.canvas.create_oval(
                monster_center_x - middle_radius, monster_center_y - middle_radius,
                monster_center_x + middle_radius, monster_center_y + middle_radius,
                fill="#ff8800", outline="#ff8800"
            )
            inner_radius = outer_radius * 0.4
            self.canvas.create_oval(
                monster_center_x - inner_radius, monster_center_y - inner_radius,
                monster_center_x + inner_radius, monster_center_y + inner_radius,
                fill="#ffff00", outline="#ffff00"
            )

    def draw(self):
        self.canvas.delete("all")
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()

        maze_width = self.cell_size * len(self.maze[0])
        maze_height = self.cell_size * len(self.maze)
        scale = min(width / maze_width, height / maze_height)
        scaled_cell = self.cell_size * scale
        offset_x = (width - int(maze_width * scale)) // 2
        offset_y = (height - int(maze_height * scale)) // 2

        for y, row in enumerate(self.maze):
            for x, cell in enumerate(row):
                x1 = offset_x + x * scaled_cell
                y1 = offset_y + y * scaled_cell
                x2 = x1 + scaled_cell
                y2 = y1 + scaled_cell

                if cell == 0:
                    self.canvas.create_rectangle(x1, y1, x2, y2, fill="#000000", outline="")
                elif cell == 1:
                    self.canvas.create_rectangle(x1, y1, x2, y2, fill="#cce5ff", outline="")
                elif cell == 2:
                    # 恢复需求：红色边框（宽度4）+ 蓝色背景 + 白色“终点”文字
                    self.canvas.create_rectangle(
                        x1, y1, x2, y2,
                        fill="#0066CC",  # 深蓝色背景（高对比度）
                        outline="red",  # 红色边框
                        width=4  # 加粗边框，确保醒目
                    )
                    # 绘制“终点”文字，居中显示
                    self.canvas.create_text(
                        x1 + scaled_cell // 2, y1 + scaled_cell // 2,
                        text="终点",
                        font=("微软雅黑", 16, "bold"),  # 加粗字体，提升辨识度
                        fill="white"  # 白色文字在蓝色背景上对比度拉满
                    )
                elif cell == 3:
                    box_fill = self.box_color
                    if time.time() < self.box_refresh_highlight:
                        box_fill = "#FFA500"

                    self.canvas.create_rectangle(x1 + 2, y1 + 2, x2 - 2, y2 - 2,
                                                 fill=box_fill, outline="orange", width=2)
                    self.canvas.create_text(x1 + scaled_cell // 2, y1 + scaled_cell // 2,
                                            text="🎁", font=("Arial", 12))

                    # 新增：透视状态下显示盲盒内容
                    if self.player.clairvoyance and (x, y) in self.player.box_contents:
                        # 绘制透视背景
                        self.canvas.create_rectangle(x1 + 5, y1 + scaled_cell + 5,
                                                     x2 - 5, y1 + scaled_cell + 30,
                                                     fill="white", outline="black", width=1)
                        # 显示盲盒内容
                        content = self.player.box_contents[(x, y)]
                        self.canvas.create_text(x1 + scaled_cell // 2, y1 + scaled_cell + 20,
                                                text=content, font=("微软雅黑", 8), fill="red")

        attr_texts = [
            f"角色: {self.player.type}",
            f"生命值: {max(0, self.player.hp)}/{self.player.max_hp}",  # 新增：显示最大生命值
            f"速度: {self.player.speed:.1f}",
            f"金币: {self.player.gold}",
            f"逃脱怪物: {self.player.monsters_defeated}",  # 新增：显示击败怪物数
            f"装备数量: {len(self.player.equipment)}"  # 新增：显示装备数量
        ]
        for idx, text in enumerate(attr_texts):
            self.canvas.create_text(50, 20 + idx * 20, text=text, font=("微软雅黑", 12), fill="#2c3e50")

        # 新增：显示特殊状态（添加透视状态）
        status_texts = []
        if self.player.shield_active:
            status_texts.append("🛡️ 防护盾激活")
        if self.player.invisible:
            invisible_remain = max(0, int(self.player.invisible_end - time.time()))
            status_texts.append(f"👻 隐身剩余: {invisible_remain}s")
        if self.player.control_reversed:
            reverse_remain = max(0, int(self.player.reverse_end_time - time.time()))
            status_texts.append(f"🔄 控制反向剩余: {reverse_remain}s")
        if self.player.clairvoyance:
            clairvoyance_remain = max(0, int(self.player.clairvoyance_end - time.time()))
            status_texts.append(f"🔍 透视剩余: {clairvoyance_remain}s")

        if status_texts:
            for idx, text in enumerate(status_texts):
                self.canvas.create_text(width // 2, 30 + idx * 25,
                                        text=text, fill="purple", font=("微软雅黑", 14, "bold"))

        # ========== 修复核心：盲盒奖励提示文本（移除不支持的bg参数，用矩形做背景） ==========
        if time.time() < self.box_reward_show_time:
            # 1. 先绘制白色背景矩形（模拟bg效果）
            text_width = len(self.box_reward_text) * 10  # 估算文本宽度
            text_x = width // 2
            text_y = height - 50
            # 绘制背景矩形（比文本大一点，居中）
            self.canvas.create_rectangle(
                text_x - text_width / 2 - 10, text_y - 15,
                text_x + text_width / 2 + 10, text_y + 15,
                fill="white", outline="gray", width=1
            )
            # 2. 绘制文本（移除bg参数，保留其他样式）
            self.canvas.create_text(
                text_x,
                text_y,
                text=self.box_reward_text,
                fill="#e74c3c" if "⚠️" in self.box_reward_text else "#27ae60",
                font=("微软雅黑", 16, "bold")
            )

        refresh_remain = max(0, int(self.box_refresh_interval - (time.time() - self.last_box_refresh)))
        self.canvas.create_text(width - 100, 20,
                                text=f"盲盒刷新: {refresh_remain}s",
                                font=("微软雅黑", 12), fill="#e74c3c")

        for monster in self.monsters:
            if monster.type == "爆炸怪":
                self.draw_explode_effect(monster, scale, offset_x, offset_y)

        if not self.game_over:
            player_x = offset_x + self.player.x * scale
            player_y = offset_y + self.player.y * scale
            scaled_player = int(self.player.size * scale)

            if self.invincible:
                alpha = int((time.time() * 10) % 2)
                if alpha:
                    if self.current_frame:
                        self.canvas.create_image(
                            player_x + scaled_player // 2,
                            player_y + scaled_player // 2,
                            image=self.current_frame
                        )
                    else:
                        self.canvas.create_rectangle(
                            player_x, player_y,
                            player_x + scaled_player,
                            player_y + scaled_player,
                            fill="#8B4513", outline=""
                        )
                invincible_remain = max(0, int(self.invincible_end - time.time()))
                self.canvas.create_text(width // 2, 30 - len(status_texts) * 25,
                                        text=f"无敌剩余: {invincible_remain}s",
                                        fill="red", font=("微软雅黑", 14, "bold"))
            else:
                if self.current_frame:
                    self.canvas.create_image(
                        player_x + scaled_player // 2,
                        player_y + scaled_player // 2,
                        image=self.current_frame
                    )
                else:
                    self.canvas.create_rectangle(
                        player_x, player_y,
                        player_x + scaled_player,
                        player_y + scaled_player,
                        fill="#8B4513", outline=""
                    )

        for monster in self.monsters:
            if monster.is_alive:
                monster_x = offset_x + monster.x * scale
                monster_y = offset_y + monster.y * scale
                scaled_monster = int(monster.size * scale)

                # 新增：中毒怪物显示
                if id(monster) in self.player.poisoned_monsters and time.time() < self.player.poisoned_monsters[
                    id(monster)]:
                    # 绘制中毒特效
                    self.canvas.create_oval(
                        monster_x - 5, monster_y - 5,
                        monster_x + scaled_monster + 5, monster_y + scaled_monster + 5,
                        outline="#2ecc71", width=3, dash=(2, 2)
                    )
                    self.canvas.create_text(
                        monster_x + scaled_monster // 2,
                        monster_y - 10,
                        text="🟢 中毒",
                        fill="green", font=("微软雅黑", 10, "bold")
                    )

                if monster.type == "爆炸怪" and monster.state == "exploding":
                    explode_remain = max(0, int(monster.explode_time - time.time()))
                    self.canvas.create_text(
                        monster_x + scaled_monster // 2,
                        monster_y - 10,
                        text=f"{explode_remain}s",
                        fill="red", font=("微软雅黑", 12, "bold")
                    )

                monster_frame = monster.get_current_frame()
                if monster_frame:
                    self.canvas.create_image(
                        monster_x + scaled_monster // 2,
                        monster_y + scaled_monster // 2,
                        image=monster_frame
                    )
                else:
                    self.canvas.create_oval(
                        monster_x, monster_y,
                        monster_x + scaled_monster,
                        monster_y + scaled_monster,
                        fill=monster.color, outline=""
                    )
                self.canvas.create_text(
                    monster_x + scaled_monster // 2,
                    monster_y + scaled_monster + 15,
                    text=monster.type,
                    fill="black", font=("微软雅黑", 10)
                )

        if self.game_over:
            result_text = "游戏胜利！" if self.game_win else "游戏结束！"
            color = "green" if self.game_win else "red"
            self.canvas.create_text(width // 2, height // 2, text=result_text,
                                    font=("微软雅黑", 30, "bold"),
                                    fill=color)

    # 新增：创建游戏结束界面
    def create_end_screen(self):
        # 销毁所有现有组件
        for widget in self.root.winfo_children():
            widget.destroy()

        # 创建结束界面的主框架
        end_frame = tk.Frame(self.root, bg="#f0f8ff")
        end_frame.pack(fill=tk.BOTH, expand=True)

        # 标题
        if self.game_win:
            title_text = "🎉 迷宫冒险胜利！🎉"
            title_color = "#2ecc71"
            subtitle_text = "你成功逃出了迷宫，击败了所有阻碍你的怪物！"
        else:
            title_text = "💀 迷宫冒险失败！💀"
            title_color = "#e74c3c"
            subtitle_text = "很遗憾，你没能逃出迷宫，再接再厉！"

        # 主标题
        title_label = tk.Label(
            end_frame,
            text=title_text,
            font=("微软雅黑", 36, "bold"),
            bg="#f0f8ff",
            fg=title_color
        )
        title_label.pack(pady=30)

        # 副标题
        subtitle_label = tk.Label(
            end_frame,
            text=subtitle_text,
            font=("微软雅黑", 16),
            bg="#f0f8ff",
            fg="#34495e"
        )
        subtitle_label.pack(pady=10)

        # 统计信息框架
        stats_frame = tk.Frame(end_frame, bg="white", relief=tk.RAISED, bd=4, padx=40, pady=30)
        stats_frame.pack(pady=20, ipadx=20, ipady=10)

        # 准备统计信息
        stats = [
            ("角色类型", self.player.type),
            ("最终生命值", max(0, self.player.hp)),
            ("剩余金币", self.player.gold),
            ("逃脱怪物数", self.player.monsters_defeated),
            ("最终速度", f"{self.player.speed:.1f}"),
            ("剩余装备数", len(self.player.equipment))  # 新增：统计剩余装备
        ]

        for idx, (label, value) in enumerate(stats):
            # 标签列
            tk.Label(
                stats_frame,
                text=f"{label}:",
                font=("微软雅黑", 14, "bold"),
                bg="white",
                fg="#2c3e50"
            ).grid(row=idx, column=0, padx=20, pady=8, sticky="w")

            # 值列
            val_color = "#e74c3c" if label == "最终生命值" and value <= 0 else "#3498db"
            tk.Label(
                stats_frame,
                text=str(value),
                font=("微软雅黑", 14),
                bg="white",
                fg=val_color
            ).grid(row=idx, column=1, padx=20, pady=8, sticky="e")

        # 按钮框架
        btn_frame = tk.Frame(end_frame, bg="#f0f8ff")
        btn_frame.pack(pady=40)

        # 重新开始按钮
        restart_btn = tk.Button(
            btn_frame,
            text="🔄 重新开始",
            font=("微软雅黑", 16, "bold"),
            bg="#3498db",
            fg="white",
            padx=40,
            pady=15,
            relief=tk.RAISED,
            bd=3,
            command=self.restart_game
        )
        restart_btn.pack(side=tk.LEFT, padx=30)

        # 退出按钮
        quit_btn = tk.Button(
            btn_frame,
            text="🚪 退出游戏",
            font=("微软雅黑", 16, "bold"),
            bg="#e74c3c",
            fg="white",
            padx=40,
            pady=15,
            relief=tk.RAISED,
            bd=3,
            command=self.root.quit
        )
        quit_btn.pack(side=tk.LEFT, padx=30)

    # 新增：重新开始游戏
    def restart_game(self):
        # 重置所有游戏状态
        self.game_over = False
        self.game_win = False
        self.paused = False
        self.end_screen_created = False
        self.monsters_defeated = 0
        self.monsters = []
        self.last_box_refresh = time.time()
        self.box_refresh_highlight = 0
        self.invincible = False
        self.invincible_end = 0
        self.selected_player_type = None
        # 重置奖励提示
        self.box_reward_text = ""
        self.box_reward_show_time = 0

        # 回到角色选择界面
        self.init_character_select()

    # 修复核心：游戏循环增加暂停判断和结束界面创建
    def game_loop(self):
        if not self.game_over and not self.paused:
            self.update_player()
            self.update_monsters()
        self.draw()

        # 检测游戏结束，创建结束界面（只创建一次）
        if self.game_over and not self.end_screen_created:
            self.end_screen_created = True
            self.root.after(500, self.create_end_screen)  # 延迟500ms显示，让玩家看到最终画面

        self.root.after(20, self.game_loop)


if __name__ == "__main__":
    root = tk.Tk()
    game = MazeGame(root)
    root.mainloop()