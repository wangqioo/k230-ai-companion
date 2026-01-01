# K230 CanMV 图形绘制性能优化经验

## 背景

在 K230 庐山派开发板上实现桌宠动画时，遇到了严重的帧率问题。本文档记录了优化过程和最终解决方案。

## 问题描述

需要在 800x480 LCD 上实时绘制动画：
- 眼睛（椭圆形，带眨眼动画）
- 瞳孔（圆形，跟随移动）
- 嘴巴（多种形状）
- 腮红（椭圆形）

初始实现使用 Python 循环逐像素填充，帧率极低（约 2-3 FPS），动画非常卡顿。

---

## 失败的尝试

### 尝试1：numpy 向量化（mgrid + mask索引）

```python
# 标准numpy写法
import numpy as np
y_grid, x_grid = np.mgrid[0:height, 0:width]

def fill_circle(cx, cy, r, color):
    dist_sq = (x_grid - cx) ** 2 + (y_grid - cy) ** 2
    mask = dist_sq <= r * r
    img_np[mask] = color  # 向量化赋值
```

**失败原因**：`ulab.numpy` 是精简版，不支持 `mgrid`

```
AttributeError: 'module' object has no attribute 'mgrid'
```

### 尝试2：手动创建坐标网格 + mask索引

```python
# 手动创建网格
x_grid = np.zeros((height, width), dtype=np.int16)
y_grid = np.zeros((height, width), dtype=np.int16)
for y in range(height):
    y_grid[y, :] = y
for x in range(width):
    x_grid[:, x] = x

# 使用mask
mask = dist_sq <= r * r
img_np[mask] = color
```

**失败原因**：`ulab` 不支持 2D 布尔数组作为索引

```
NotImplementedError: operation is implemented for 1D Boolean arrays only
```

### 尝试3：边界框内 Python 循环

```python
def fill_circle(cx, cy, r, color):
    for y in range(cy - r, cy + r + 1):
        for x in range(cx - r, cx + r + 1):
            if (x - cx)**2 + (y - cy)**2 <= r*r:
                img_np[y, x] = color
```

**问题**：虽然只遍历边界框（约 110x110 = 12100 像素），但 MicroPython 解释器执行 Python 循环本身就很慢，帧率仍然不理想。

---

## 成功方案：使用 image 库内置绘图函数

### 核心原理

`image` 库的绘图函数（`draw_circle`、`draw_ellipse`、`draw_rectangle`）是 **C 语言实现**的，执行速度比 Python 循环快几个数量级。

### 关键技巧：用同心圆/椭圆模拟填充

由于 `thickness=-1` 填充参数可能不被支持，使用**同心圆/椭圆从外到内绘制**来实现填充效果：

```python
def _draw_filled_circle(self, cx, cy, r, color):
    """用同心圆模拟填充"""
    if r <= 0:
        return
    cx, cy, r = int(cx), int(cy), int(r)
    # 从外到内画同心圆，thickness=2确保无缝隙
    for radius in range(r, 0, -1):
        self.img.draw_circle(cx, cy, radius, color=color, thickness=2)
    # 中心点
    self.img.draw_circle(cx, cy, 1, color=color, thickness=1)

def _draw_filled_ellipse(self, cx, cy, rx, ry, color):
    """用同心椭圆模拟填充"""
    if rx <= 0 or ry <= 0:
        return
    cx, cy = int(cx), int(cy)
    rx, ry = int(rx), int(ry)
    # 从外到内画同心椭圆
    steps = max(rx, ry)
    for i in range(steps, 0, -1):
        scale = i / steps
        self.img.draw_ellipse(cx, cy, int(rx * scale), int(ry * scale),
                              0, 0, 360, color=color, thickness=2)
```

### 矩形填充

矩形可以直接使用 `fill=True` 参数：

```python
def _draw_filled_rect(self, x, y, w, h, color):
    self.img.draw_rectangle(int(x), int(y), int(w), int(h),
                            color=color, thickness=-1, fill=True)
```

---

## 性能对比

| 方案 | 帧率 (FPS) | 备注 |
|------|-----------|------|
| Python 循环逐像素 | 2-3 | 极慢，不可用 |
| numpy mask 索引 | - | ulab 不支持 |
| 边界框 Python 循环 | 5-8 | 仍然较慢 |
| **image 库 C 函数** | **25-30+** | 流畅动画 |

---

## 完整示例代码结构

```python
import image
from media.display import *
from media.media import *

class PetFace:
    def __init__(self, width=800, height=480):
        # 直接创建 image 对象，不需要 numpy
        self.img = image.Image(width, height, image.ARGB8888)

    def _draw_filled_circle(self, cx, cy, r, color):
        # 同心圆填充
        for radius in range(int(r), 0, -1):
            self.img.draw_circle(int(cx), int(cy), radius,
                                 color=color, thickness=2)

    def _draw_filled_ellipse(self, cx, cy, rx, ry, color):
        # 同心椭圆填充
        steps = max(int(rx), int(ry))
        for i in range(steps, 0, -1):
            scale = i / steps
            self.img.draw_ellipse(int(cx), int(cy),
                                  int(rx * scale), int(ry * scale),
                                  0, 0, 360, color=color, thickness=2)

    def render(self):
        self.img.clear()
        # 背景
        self.img.draw_rectangle(0, 0, 800, 480,
                                color=(40, 44, 52, 255), fill=True)
        # 绘制眼睛、嘴巴等...
        self._draw_filled_ellipse(320, 210, 55, 55, (255, 255, 255, 255))
        self._draw_filled_ellipse(480, 210, 55, 55, (255, 255, 255, 255))
        return self.img

# 主循环
Display.init(Display.ST7701, width=800, height=480, to_ide=True)
MediaManager.init()
pet = PetFace()

while True:
    img = pet.render()
    Display.show_image(img)
```

---

## ulab.numpy 功能限制总结

在 K230 CanMV 的 `ulab.numpy` 中，以下功能**不可用**：

| 功能 | 标准 numpy | ulab.numpy |
|------|-----------|------------|
| `np.mgrid` | ✅ | ❌ |
| `np.meshgrid` | ✅ | ❌ |
| 2D 布尔数组索引 | ✅ | ❌ |
| 高级花式索引 | ✅ | ❌ |

**可用的 ulab 功能**：
- 基础数组创建：`np.zeros()`, `np.ones()`, `np.array()`
- 切片赋值：`arr[y1:y2, x1:x2] = value`
- 基础数学运算：`+`, `-`, `*`, `/`, `**`
- 基础函数：`np.sin()`, `np.cos()`, `np.sqrt()` 等

---

## 关键经验总结

1. **优先使用 C 实现的库函数**
   - `image.draw_xxx()` 比 Python 循环快 10 倍以上
   - 即使需要多次调用（如同心圆），仍然比 Python 循环快

2. **避免在热路径使用 Python 循环**
   - MicroPython 解释器执行循环非常慢
   - 每帧需要执行的代码尽量用 C 函数

3. **ulab 不是完整的 numpy**
   - 很多高级功能不支持
   - 在使用前先测试功能是否可用

4. **同心圆/椭圆是填充的好方法**
   - 当 `fill=True` 或 `thickness=-1` 不工作时
   - 从外到内绘制同心图形可以实现填充效果

5. **备选方案：预渲染精灵图**
   - 如果图形复杂，可以预先制作 PNG 图片
   - 运行时用 `img.draw_image()` 拼接
   - 这是游戏开发中常用的方式

---

---

## 为什么 Python 可以调用 C 函数？

### 原理解释

```
┌─────────────────────────────────────────────────┐
│  你写的 Python 代码                              │
│  for radius in range(r, 0, -1):                 │
│      img.draw_circle(...)  ←── 调用 C 函数       │
└─────────────────────────────────────────────────┘
                    ↓ 调用
┌─────────────────────────────────────────────────┐
│  image 库（C 语言编写，预编译好的）               │
│  void draw_circle(...) {                        │
│      // C 代码直接操作像素内存，极快              │
│  }                                              │
└─────────────────────────────────────────────────┘
```

### 速度对比

| 方式 | 实际执行 | 速度 |
|------|---------|------|
| Python 循环写像素 | 每个像素都经过 Python 解释器 | 极慢 |
| 调用 `draw_circle()` | Python 只调用一次，C 完成所有工作 | 极快 |

### 类比理解

```
慢的方式（纯 Python）：
  你亲自一块一块搬砖，搬 10000 块

快的方式（调用 C 函数）：
  你打一个电话叫卡车，卡车一次运走 10000 块
```

### 代码对比

```python
# 慢：Python 循环 38 万次（800x480 像素）
for y in range(480):
    for x in range(800):
        if 在圆内:
            img_np[y, x] = color  # Python 解释器执行

# 快：调用 C 函数
img.draw_circle(cx, cy, r, color)  # C 代码直接操作内存
```

### 为什么可以这样？

`image` 库是 CanMV 固件的一部分，用 C 语言写好并编译进固件里。你的 Python 代码只是**调用**这些预编译的 C 函数，不需要自己写 C。

这就是为什么：
- `draw_circle()` 快 → C 实现
- `draw_ellipse()` 快 → C 实现
- `draw_rectangle()` 快 → C 实现
- 自己写的 Python 循环慢 → 解释执行

MicroPython 的很多库都是这样设计的：
- **底层性能敏感的操作** → C 语言实现
- **上层逻辑和胶水代码** → Python 实现

这样既保证了性能，又保留了 Python 的易用性。

---

## 参考资料

- CanMV K230 官方文档：https://developer.canaan-creative.com/k230_canmv
- image 模块 API 参考（OpenMV 兼容）
- ulab 文档：https://micropython-ulab.readthedocs.io/
