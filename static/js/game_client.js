/*
重构后的前端客户端：
- 保留核心通信逻辑，优化UI交互和视觉反馈
- 增加移动端适配（虚拟方向键）
- 使用requestAnimationFrame优化渲染性能
- 增强状态变化的动画效果
*/

// 连接Socket.IO服务器
const socket = io('http://127.0.0.1:5000', {
  transports: ['websocket', 'polling'],
  reconnection: true,
  reconnectionAttempts: 5
});

// 全局状态管理
const gameState = {
  grid: [],
  width: 21,
  height: 21,
  playerSid: null,
  players: {},
  boxes: [],
  exit: [0, 0],
  shop: [],
  isJoined: false,
  lastRenderTime: 0,
  animationFrameId: null
};

// DOM元素缓存
const elements = {
  canvas: document.getElementById('game'),
  ctx: document.getElementById('game').getContext('2d'),
  status: document.getElementById('status'),
  timer: document.getElementById('timer'),
  coins: document.getElementById('coins'),
  hp: document.getElementById('hp'),
  log: document.getElementById('log'),
  leaderboard: document.getElementById('leaderboard'),
  shopList: document.getElementById('shopList'),
  joinBtn: document.getElementById('joinBtn'),
  playerName: document.getElementById('playerName'),
  newMazeBtn: document.getElementById('newMazeBtn'),
  moveButtons: document.querySelectorAll('.move-btn')
};

// 初始化画布
let cellSize = 30;

// 工具函数：格式化日志
function logMessage(msg, type = 'info') {
  const logDiv = elements.log;
  const timestamp = new Date().toLocaleTimeString();
  const logEntry = document.createElement('div');
  logEntry.className = `mb-1 ${
    type === 'success' ? 'text-success' : 
    type === 'error' ? 'text-danger' : 
    type === 'warn' ? 'text-accent' : ''
  }`;
  logEntry.innerHTML = `<span class="text-gray-500">[${timestamp}]</span> ${msg}`;
  logDiv.prepend(logEntry);

  // 限制日志数量
  if (logDiv.children.length > 5) {
    logDiv.removeChild(logDiv.lastChild);
  }
}

// 初始化事件监听
function initEventListeners() {
  // 加入游戏
  elements.joinBtn.addEventListener('click', () => {
    const name = elements.playerName.value.trim() || `玩家${Math.floor(Math.random() * 1000)}`;
    socket.emit('join', { name });
    elements.status.textContent = `正在加入: ${name}`;
    elements.playerName.disabled = true;
    elements.joinBtn.disabled = true;
    elements.joinBtn.classList.add('opacity-50', 'cursor-not-allowed');
  });

  // 生成新迷宫
  elements.newMazeBtn.addEventListener('click', () => {
    const size = parseInt(prompt("输入迷宫尺寸（奇数，建议15-31）", "21")) || 21;
    const validSize = size % 2 === 1 ? Math.min(Math.max(15, size), 31) : 21;
    socket.emit('request_new_maze', { w: validSize, h: validSize });
    logMessage(`请求生成 ${validSize}x${validSize} 的新迷宫`);
  });

  // 键盘控制
  window.addEventListener('keydown', (e) => {
    if (!gameState.isJoined) return;

    let dx = 0, dy = 0;
    switch(e.key) {
      case 'ArrowUp': dy = -1; break;
      case 'ArrowDown': dy = 1; break;
      case 'ArrowLeft': dx = -1; break;
      case 'ArrowRight': dx = 1; break;
      default: return; // 忽略其他按键
    }
    socket.emit('move', { dx, dy });
    e.preventDefault(); // 防止页面滚动
  });

  // 移动端虚拟按键
  elements.moveButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      if (!gameState.isJoined) return;
      const dx = parseInt(btn.dataset.dx);
      const dy = parseInt(btn.dataset.dy);
      socket.emit('move', { dx, dy });
    });
  });
}

// 渲染商店
function renderShop() {
  elements.shopList.innerHTML = '';
  if (gameState.shop.length === 0) {
    elements.shopList.innerHTML = '<div class="text-gray-400 italic text-sm">暂无商品</div>';
    return;
  }

  gameState.shop.forEach(item => {
    const btn = document.createElement('button');
    btn.className = 'w-full flex justify-between items-center bg-gray-800 hover:bg-gray-700 p-3 rounded-lg transition-all btn-hover';
    btn.innerHTML = `
      <div>
        <div class="font-medium">${item.desc}</div>
        <div class="text-xs text-gray-400">ID: ${item.id}</div>
      </div>
      <span class="bg-yellow-500/20 text-yellow-400 px-2 py-1 rounded-full text-sm">
        <i class="fa fa-coins mr-1"></i>${item.price}
      </span>
    `;
    btn.addEventListener('click', () => {
      socket.emit('buy', { item_id: item.id });
    });
    elements.shopList.appendChild(btn);
  });
}

// 渲染排行榜
function renderLeaderboard(data) {
  elements.leaderboard.innerHTML = '';
  if (!data || data.length === 0) {
    elements.leaderboard.innerHTML = '<li class="text-gray-400 italic text-sm">暂无记录</li>';
    return;
  }

  data.forEach((entry, index) => {
    const li = document.createElement('li');
    li.className = `p-2 rounded-lg ${index < 3 ? 'bg-gradient-to-r from-yellow-900/30 to-transparent' : 'bg-gray-800/50'}`;
    li.innerHTML = `
      <div class="flex justify-between items-center">
        <span class="${index < 3 ? 'font-bold' : ''}">${entry.name}</span>
        <div class="text-right">
          <div>用时: ${entry.time}s</div>
          <div class="text-xs text-gray-400">金币: ${entry.coins}</div>
        </div>
      </div>
    `;
    elements.leaderboard.appendChild(li);
  });
}

// 调整画布大小
function resizeCanvas() {
  const containerWidth = elements.canvas.parentElement.clientWidth;
  cellSize = Math.min(
    Math.floor(containerWidth / gameState.width),
    30 // 最大单元格大小
  );
  elements.canvas.width = gameState.width * cellSize;
  elements.canvas.height = gameState.height * cellSize;
}

// 绘制游戏世界
function draw(currentTime) {
  // 计算时间差，控制渲染帧率
  const deltaTime = (currentTime - gameState.lastRenderTime) / 16.67; // 基于60fps的时间因子
  gameState.lastRenderTime = currentTime;

  const ctx = elements.ctx;
  const { width, height, grid, players, boxes, exit, playerSid } = gameState;

  // 清空画布
  ctx.clearRect(0, 0, elements.canvas.width, elements.canvas.height);

  // 绘制迷宫网格
  if (grid.length > 0) {
    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        // 墙和路的样式（带轻微渐变）
        if (grid[y][x] === 0) {
          ctx.fillStyle = '#111827';
          ctx.fillRect(x * cellSize, y * cellSize, cellSize, cellSize);
          // 墙的边框效果
          ctx.strokeStyle = '#1F2937';
          ctx.strokeRect(x * cellSize, y * cellSize, cellSize, cellSize);
        } else {
          ctx.fillStyle = '#1F2937';
          ctx.fillRect(x * cellSize, y * cellSize, cellSize, cellSize);
        }
      }
    }
  }

  // 绘制出口（带脉动动画）
  const exitPulse = 0.7 + Math.sin(currentTime / 500) * 0.3;
  ctx.fillStyle = `rgba(16, 185, 129, ${exitPulse})`; // success颜色带透明度动画
  ctx.fillRect(
    exit[0] * cellSize,
    exit[1] * cellSize,
    cellSize,
    cellSize
  );
  // 出口标记
  ctx.fillStyle = '#fff';
  ctx.font = `${cellSize / 2}px sans-serif`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText('EXIT', (exit[0] + 0.5) * cellSize, (exit[1] + 0.5) * cellSize);

  // 绘制盲盒（带旋转动画）
  boxes.forEach(box => {
    ctx.save();
    ctx.translate(
      (box.pos[0] + 0.5) * cellSize,
      (box.pos[1] + 0.5) * cellSize
    );
    // 旋转动画
    ctx.rotate(currentTime / 1000);

    // 盲盒主体
    ctx.fillStyle = box.type === 'guaranteed' ? '#D97706' : '#F59E0B';
    ctx.fillRect(
      -cellSize * 0.35,
      -cellSize * 0.35,
      cellSize * 0.7,
      cellSize * 0.7
    );
    // 盲盒标记
    ctx.fillStyle = '#fff';
    ctx.font = `${cellSize / 4}px sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('?', 0, 0);
    ctx.restore();
  });

  // 绘制玩家
  Object.values(players).forEach(player => {
    const isLocalPlayer = player.sid === playerSid;
    const x = player.x * cellSize + cellSize / 2;
    const y = player.y * cellSize + cellSize / 2;

    // 玩家光环（本地玩家有蓝色光环）
    if (isLocalPlayer) {
      ctx.beginPath();
      ctx.arc(x, y, cellSize * 0.45, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(59, 130, 246, 0.2)';
      ctx.fill();
    }

    // 玩家主体（圆形）
    ctx.beginPath();
    ctx.arc(x, y, cellSize * 0.35, 0, Math.PI * 2);
    ctx.fillStyle = isLocalPlayer ? '#3B82F6' : '#8B5CF6';
    ctx.fill();
    // 玩家边框
    ctx.strokeStyle = '#fff';
    ctx.lineWidth = 2;
    ctx.stroke();

    // 护盾效果
    if (player.shield) {
      ctx.beginPath();
      ctx.arc(x, y, cellSize * 0.4, 0, Math.PI * 2);
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.7)';
      ctx.lineWidth = 2;
      ctx.setLineDash([3, 3]);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // 玩家名称
    ctx.fillStyle = '#fff';
    ctx.font = `${Math.max(8, cellSize / 5)}px sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    ctx.fillText(
      player.name,
      x,
      y + cellSize * 0.35
    );
  });

  // 持续渲染
  gameState.animationFrameId = requestAnimationFrame(draw);
}

// 处理Socket.IO事件
function initSocketEvents() {
  // 连接状态
  socket.on('connect', () => {
    elements.status.textContent = '已连接服务器';
    logMessage('成功连接到游戏服务器', 'success');
  });

  socket.on('disconnect', (reason) => {
    elements.status.textContent = `已断开连接: ${reason}`;
    logMessage(`与服务器断开连接: ${reason}`, 'error');
    gameState.isJoined = false;
    elements.playerName.disabled = false;
    elements.joinBtn.disabled = false;
    elements.joinBtn.classList.remove('opacity-50', 'cursor-not-allowed');
  });

  // 初始化游戏数据
  socket.on('init', (data) => {
    gameState.grid = data.grid;
    gameState.width = data.width;
    gameState.height = data.height;
    gameState.exit = data.exit;
    gameState.shop = data.shop || [];
    gameState.playerSid = data.your_sid;
    gameState.players = {};
    (data.players || []).forEach(p => { gameState.players[p.sid] = p; });
    gameState.boxes = data.boxes || [];
    gameState.isJoined = true;

    // 更新UI
    elements.status.textContent = `已加入 (ID: ${gameState.playerSid.substring(0, 6)})`;
    renderShop();
    resizeCanvas();
    logMessage('游戏初始化完成，开始探索吧！', 'success');
  });

  // 状态更新
  socket.on('state', (data) => {
    // 更新玩家列表
    gameState.players = {};
    (data.players || []).forEach(p => { gameState.players[p.sid] = p; });
    gameState.boxes = data.boxes || [];
    gameState.exit = data.exit || gameState.exit;

    // 更新本地玩家状态
    const localPlayer = gameState.players[gameState.playerSid];
    if (localPlayer) {
      elements.coins.textContent = `金币: ${localPlayer.coins}`;
      elements.hp.textContent = `生命: ${localPlayer.hp}`;

      // 生命低于30时显示警告
      elements.hp.className = localPlayer.hp < 30 ? 'text-danger font-bold' : '';
    }
  });

  // 盲盒刷新
  socket.on('boxes_refreshed', (data) => {
    gameState.boxes = data.boxes || gameState.boxes;
    logMessage('盲盒已刷新！快去寻找惊喜吧', 'warn');
  });

  // 操作结果反馈
  socket.on('buy_result', (data) => {
    logMessage(data.msg, data.success ? 'success' : 'error');
  });

  socket.on('action_result', (data) => {
    logMessage(data.msg, data.ok ? 'info' : 'error');
  });

  // 排行榜更新
  socket.on('leaderboard_update', (data) => {
    renderLeaderboard(data.top || []);
  });

  // 通用消息
  socket.on('message', (data) => {
    logMessage(data.msg);
  });
}

// 初始化排行榜数据
async function fetchLeaderboard() {
  try {
    const res = await fetch('/api/leaderboard');
    const data = await res.json();
    renderLeaderboard(data.map(item => ({
      name: item.name,
      time: item.time,
      coins: item.coins
    })));
  } catch (e) {
    console.warn('获取排行榜失败:', e);
    logMessage('获取排行榜数据失败', 'error');
  }
}

// 窗口大小变化时重新调整画布
window.addEventListener('resize', resizeCanvas);

// 初始化游戏
function initGame() {
  initEventListeners();
  initSocketEvents();
  fetchLeaderboard();
  // 启动渲染循环
  gameState.lastRenderTime = performance.now();
  gameState.animationFrameId = requestAnimationFrame(draw);
}

// 页面加载完成后初始化
window.addEventListener('load', initGame);

// 页面卸载时清理
window.addEventListener('beforeunload', () => {
  if (gameState.animationFrameId) {
    cancelAnimationFrame(gameState.animationFrameId);
  }
  socket.disconnect();
});