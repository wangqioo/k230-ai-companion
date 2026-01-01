# 桌面宠物项目 - 配置文件

# ============ 显示配置 ============
DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 480

# ============ 唤醒配置 ============
WAKE_ANGLE_THRESHOLD = 20      # 唤醒角度阈值(度)，yaw角小于此值时唤醒
EXIT_ANGLE_THRESHOLD = 45      # 退出角度阈值(度)
EXIT_TIMEOUT_SEC = 3           # 转头多久后退出(秒)

# ============ 表情配置 ============
# 桌宠脸部位置（相对于屏幕中心）
FACE_CENTER_X = DISPLAY_WIDTH // 2
FACE_CENTER_Y = DISPLAY_HEIGHT // 2

# 眼睛配置
EYE_RADIUS = 40                # 眼睛半径
EYE_PUPIL_RADIUS = 15          # 瞳孔半径
EYE_SPACING = 120              # 两眼间距
EYE_Y_OFFSET = -30             # 眼睛垂直偏移（负数=靠上）
EYE_MOVE_RANGE_X = 20          # 眼睛水平移动范围
EYE_MOVE_RANGE_Y = 15          # 眼睛垂直移动范围

# 嘴巴配置
MOUTH_Y_OFFSET = 60            # 嘴巴垂直偏移（正数=靠下）
MOUTH_WIDTH = 80               # 嘴巴宽度
MOUTH_HEIGHT = 20              # 嘴巴高度

# 颜色配置 (R, G, B, A)
COLOR_BACKGROUND = (30, 30, 40, 255)       # 深色背景
COLOR_FACE = (255, 220, 180, 255)          # 肤色
COLOR_EYE_WHITE = (255, 255, 255, 255)     # 眼白
COLOR_EYE_PUPIL = (40, 40, 40, 255)        # 瞳孔
COLOR_MOUTH = (200, 100, 100, 255)         # 嘴巴

# ============ 云端配置 ============
CLOUD_WS_URL = "wss://your-server.com/ws"  # WebSocket地址
CLOUD_TIMEOUT_SEC = 10                      # 云端超时时间

# ============ 音频配置 ============
AUDIO_SAMPLE_RATE = 16000      # 采样率
AUDIO_CHANNELS = 1             # 单声道
AUDIO_BIT_DEPTH = 16           # 位深度
