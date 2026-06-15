# 桌面宠物项目 - 开发计划

## 当前架构

项目已从“K230 一体化边缘设备”调整为双芯片分工：

```text
GC2093 camera
      |
      v
K230 CanMV
  camera capture
  face detection
  head pose
  primary-face selection
  normalized visual observation
      |
      | UART2 binary frames
      v
ESP32
  Xiaozhi firmware runtime
  K230 binary vision input adapter
  product interaction controller
  display / audio / buttons / motors
  WiFi / gateway / cloud
  watchdog and safe recovery
```

### 责任分配

| 关注点 | 负责人 | 备注 |
|---|---|---|
| 摄像头采集 | K230 | 使用 CanMV camera pipeline |
| 人脸检测和头部姿态 | K230 | 使用 KPU / Ai2d / face pose model |
| 视觉观测归一化 | K230 | 输出结构化事件，不输出原始图像 |
| UART 发布 | K230 | UART2, 921600 baud, CRC16 |
| 产品状态机 | ESP32 / Xiaozhi firmware | 复用小智 Application/音频/显示生命周期，视觉只作为输入门控 |
| 表情/屏幕/音频/按钮/电机 | ESP32 | K230 不再承担实时产品行为 |
| WiFi/网关/云端通信 | ESP32 或后端网关 | 旧 PC server 可作为后端 adapter |
| 看门狗/安全恢复 | ESP32 | K230 重启不能阻塞产品 |

## 旧计划处理

旧计划中的成果仍有参考价值，但运行时归属发生变化：

| 旧阶段 | 新状态 | 处理方式 |
|---|---|---|
| Step 1 显示系统 | 参考完成 | 表情概念迁移到 ESP32 output layer |
| Step 2 头部检测 | 保留在 K230 | 作为视觉协处理主能力 |
| Step 3 视觉联动 | 迁移到 ESP32 | 由 ESP32 根据视觉事件做状态机和眼睛跟随 |
| Step 4 K230 网络通信 | legacy/probe | 不再作为目标 runtime；ESP32 负责网络 |
| Step 5 PC 服务器端 | 可复用 | 作为 ASR/LLM/TTS 网关 adapter |
| Step 6 整合到 K230 main.py | 替换 | 改为 ESP32 end-to-end integration |

## 当前主线

### Phase 1: K230 视觉协处理链路 ✅ 基础完成，继续加深

**目标:** K230 只发布规范化视觉观测，不承担产品行为。

**已完成:**
- [x] K230 UART2 初始化和发布入口 `src/main_vision_uart.py`
- [x] face detection + head pose 封装 `src/vision/head_pose.py`
- [x] 二进制 UART 协议 `src/transport/vision_protocol.py`
- [x] UART publisher `src/transport/uart_publisher.py`
- [x] Python host tests 覆盖 CRC、frame、stream decoder、publisher

**下一步优化:**
- [x] `src/vision/visual_observation.py` 输出 canonical observation
- [x] `VisionPublisher` 接收 canonical observation，不接收 detector box/euler/frame size
- [x] K230 主循环只负责取帧、推理、调度发布

**验收标准:**
- host Python tests 全部通过
- `main_vision_uart.py` 中不再直接操作 detector dict 字段来构造协议 payload
- K230 runtime 不包含唤醒、表情、语音、网络、云端行为

### Phase 2: ESP32 / Xiaozhi VisionInput ✅ 原型完成，当前转入小智固件

**目标:** 在现有小智 ESP32 固件中接入 K230 二进制视觉协议，不从零做 Arduino 产品固件。

**已完成:**
- [x] C++ 增量 parser
- [x] CRC/version/length 校验
- [x] face payload 解码
- [x] 500ms freshness 示例
- [x] `esp32/vision_receiver` 原型验证 VisionInput 语义

**下一步优化:**
- [x] 新增 `esp32/vision_receiver/vision_input.h/.cpp` 作为 host/protocol 原型
- [x] 将 face visible、face lost、heartbeat、error、timeout 转成 `VisionEvent`
- [x] 明确 `VisionAvailable` 和 `VisionTimeout` 是 ESP32 本地事件，不是 K230 payload
- [x] sketch 只负责读 UART、喂 parser、分发事件
- [ ] 停止把 `esp32/vision_receiver` 作为产品固件主线，只保留为协议/host 测试参考
- [x] 将二进制 parser/adapter 接入 `/Users/wq/Workshop/MCU/xiaozhi-project/xiaozhi-esp32/main/grind_buddy/`
- [x] 小智侧 UART integration 使用 K230 binary frames，而不是 JSON Lines

**验收标准:**
- host C++ tests 覆盖 first valid frame、face visible、face lost、timeout once、resume after timeout、K230 error
- 小智固件 host tests 覆盖 binary frame parser 和 `Face/FaceLost` 到 `presence/gaze/face.pose` 的语义映射
- 产品交互控制器后续只依赖视觉语义事件，不直接依赖 K230 原始 payload
- corrupted frame 不刷新 vision availability

### Phase 3: Xiaozhi 视觉门控交互控制器

**目标:** 把旧 Step 3 的视觉联动迁移到现有小智固件，复用 `Application`、音频、显示和 `grind_buddy` 控制器。

**任务清单:**
- [x] 定义 `InteractionState` / `GrindBuddyController` 作为小智侧视觉门控状态层
- [x] 根据 gaze/presence 触发 `WakeWordInvoke` / `SilenceListening`
- [x] 用 K230 binary `Face` 派生 `presence.enter` / `gaze.enter` / `face.pose`
- [x] 用 `FaceLost` / `VisionTimeout` 派生 `presence.leave`
- [ ] 将 K230 sequence reset / restart 视为可恢复事件
- [ ] 接入小智 TTS/listening 回调后驱动 listening / thinking / talking 状态

**验收标准:**
- 不依赖 K230 原始图像
- 不依赖 K230 产品状态判断
- 视觉事件能驱动小智现有语音交互进入/退出
- 不修改小智全局 `DeviceStateMachine` 来表达视觉状态

### Phase 4: ESP32 Output Layer

**目标:** 在小智 ESP32 固件上重建用户可见行为。

**任务清单:**
- [ ] 表情状态：neutral / happy / sleepy / listening / thinking / talking
- [ ] 眼睛跟随：由 normalized face center 映射
- [ ] 说话/倾听/思考动画 hook
- [ ] 如有电机，加入动作安全限制
- [ ] 如有屏幕，接入 ESP32 显示驱动

**验收标准:**
- K230 只提供视觉事件
- ESP32 独立控制表情和动作
- no-vision 时进入安全输出状态

### Phase 5: ESP32 Audio + Interaction Loop

**目标:** 把旧语音对话能力迁移到 ESP32 侧。

**任务清单:**
- [ ] 按钮触发固定时长录音
- [ ] 音频播放
- [ ] listening / thinking / talking 状态联动
- [ ] 失败时回到安全状态
- [ ] 后续再考虑 VAD、唤醒词、流式 TTS

**验收标准:**
- K230 视觉运行不受 ESP32 语音流程阻塞
- 音频状态由 ESP32 状态机管理

### Phase 6: ESP32 Network Client + Gateway

**目标:** ESP32 作为客户端接入后端或 PC 网关。

**任务清单:**
- [ ] ESP32 WiFi 连接
- [ ] ESP32 上传音频或会话请求
- [ ] 请求携带结构化视觉上下文，不上传 K230 原始图像
- [ ] 复用或替换旧 `server/` 作为 ASR/LLM/TTS adapter
- [ ] 网络失败不阻塞安全状态

**验收标准:**
- 语音请求能返回文本/音频回复
- ESP32 在网络失败时仍能保持本地状态机和安全输出

### Phase 7: End-to-End Recovery and Tuning

**目标:** 完整闭环跑通并做硬件级容错。

**任务清单:**
- [ ] standby → face attention → wake/listen → conversation → face-away/timeout → idle
- [ ] K230 重启容忍
- [ ] UART fault 注入测试
- [ ] ESP32 watchdog 和 safe-state 行为
- [ ] 延迟、帧率、timeout、heartbeat 参数调优

**验收标准:**
- K230 卡顿或重启不会卡死 ESP32
- ESP32 网络/音频失败不会影响 no-vision 安全行为
- 产品交互可重复、可恢复

## 暂缓项

以下事项有价值，但不是当前推进架构的 blocker：

- protocol contract generator：等协议出现 ESP32→K230 command 或更多 message type 后再做
- runtime profile system：等出现多套硬件/模型/显示配置后再做
- legacy 目录搬迁：先在文档中明确 legacy 状态，避免当前改动扩大
- K230 HTTP/Base64/image upload 优化：目标 runtime 不再需要
- streaming TTS / VAD / wake word：等基础 ESP32 interaction loop 稳定后再做

## 当前优化任务

### Task A: K230 canonical visual observation

**文件:**
- `src/vision/visual_observation.py`
- `src/transport/vision_protocol.py`
- `src/transport/uart_publisher.py`
- `src/main_vision_uart.py`
- `tests/test_visual_observation.py`
- `tests/test_vision_protocol.py`
- `tests/test_uart_publisher.py`

**步骤:**
- [x] 先写 host Python failing tests
- [x] 实现 canonical observation
- [x] 收窄 publisher interface
- [x] 更新 K230 main loop
- [x] 运行 Python tests 和 compileall

### Task B: ESP32 VisionInput semantic event module

**文件:**
- `esp32/vision_receiver/vision_input.h`
- `esp32/vision_receiver/vision_input.cpp`
- `esp32/vision_receiver/vision_protocol.h`
- `esp32/vision_receiver/vision_protocol.cpp`
- `esp32/vision_receiver/vision_receiver.ino`
- `tests/cpp/test_vision_input.cpp`
- `tests/cpp/test_vision_protocol.cpp`

**步骤:**
- [x] 先写 host C++ failing tests
- [x] 添加 `decodeError`
- [x] 实现 `VisionInput` / `VisionEvent` / `VisionSnapshot`
- [x] 精简 Arduino sketch
- [x] 编译并运行 C++ tests

### Task C: Xiaozhi K230 binary vision integration

**文件:**
- `/Users/wq/Workshop/MCU/xiaozhi-project/xiaozhi-esp32/main/grind_buddy/k230_binary_protocol.h`
- `/Users/wq/Workshop/MCU/xiaozhi-project/xiaozhi-esp32/main/grind_buddy/k230_binary_protocol.cc`
- `/Users/wq/Workshop/MCU/xiaozhi-project/xiaozhi-esp32/main/grind_buddy/k230_vision_adapter.h`
- `/Users/wq/Workshop/MCU/xiaozhi-project/xiaozhi-esp32/main/grind_buddy/k230_vision_adapter.cc`
- `/Users/wq/Workshop/MCU/xiaozhi-project/xiaozhi-esp32/main/grind_buddy/grind_buddy_uart_integration.cc`
- `/Users/wq/Workshop/MCU/xiaozhi-project/xiaozhi-esp32/main/boards/szpi-s3/config.h`
- `/Users/wq/Workshop/MCU/xiaozhi-project/xiaozhi-esp32/tests/cpp/test_k230_binary_protocol.cpp`
- `/Users/wq/Workshop/MCU/xiaozhi-project/xiaozhi-esp32/tests/cpp/test_k230_vision_adapter.cpp`

**步骤:**
- [x] 先写 host C++ failing tests
- [x] 在小智 `grind_buddy` 中实现 K230 binary frame parser
- [x] 实现 Face/FaceLost/Heartbeat/Error 到视觉语义事件的 adapter
- [x] 将 UART integration 从 `K230JsonLineParser` 切到 binary parser + adapter
- [x] 串口参数收敛到 SZPI-S3 board config，默认对齐 K230 `921600` baud
- [x] 运行 host C++ tests 和 SZPI-S3 IDF build

## 参考文档

- `README.md`
- `docs/architecture.md`
- `docs/development_notes.md`
- `docs/superpowers/specs/2026-06-14-k230-vision-coprocessor-design.md`
- `K230_GRAPHICS_OPTIMIZATION.md`
