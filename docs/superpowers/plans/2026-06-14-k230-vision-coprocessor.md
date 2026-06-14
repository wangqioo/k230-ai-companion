# K230 Vision Coprocessor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a tested UART link where K230 publishes visual observations and ESP32 safely consumes them.

**Architecture:** A hardware-neutral binary protocol is shared by a Python encoder and a C++ incremental parser. K230 owns inference and publication only; ESP32 owns timeout policy and product behavior.

**Tech Stack:** CanMV MicroPython, Python `unittest`, ESP32 C++, host `g++`, UART2.

---

### Task 1: Protocol encoder and Python parser

**Files:**
- Create: `src/transport/__init__.py`
- Create: `src/transport/vision_protocol.py`
- Create: `tests/test_vision_protocol.py`

- [ ] Write tests for CRC, frame round-trip, normalization, corrupt-frame recovery, and sequence wraparound.
- [ ] Run `python3 -m unittest tests.test_vision_protocol -v` and confirm missing-module failure.
- [ ] Implement the minimal protocol encoder and incremental parser.
- [ ] Run the protocol tests and confirm they pass.

### Task 2: K230 UART publisher

**Files:**
- Create: `src/transport/uart_publisher.py`
- Create: `tests/test_uart_publisher.py`

- [ ] Write tests using an in-memory UART Adapter.
- [ ] Run the tests and confirm missing publisher failure.
- [ ] Implement sequence ownership and message publication.
- [ ] Run both Python test modules.

### Task 3: K230 visual entry

**Files:**
- Create: `src/main_vision_uart.py`
- Modify: `src/vision/head_pose.py`

- [ ] Add a hardware-neutral test for observation conversion.
- [ ] Run it and confirm the conversion Module is missing.
- [ ] Implement normalized observation conversion and the K230 inference loop.
- [ ] Run all Python tests and compile all Python files.

### Task 4: ESP32 receiver

**Files:**
- Create: `esp32/vision_receiver/vision_protocol.h`
- Create: `esp32/vision_receiver/vision_protocol.cpp`
- Create: `esp32/vision_receiver/vision_receiver.ino`
- Create: `tests/cpp/test_vision_protocol.cpp`

- [ ] Write a host C++ test using golden heartbeat, face, CRC-failure, and timeout cases.
- [ ] Run `g++` and confirm missing parser failure.
- [ ] Implement the incremental parser and timeout state.
- [ ] Compile and run the host C++ test.

### Task 5: Documentation and verification

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture.md`

- [ ] Document wiring, baud rate, message meanings, deployment, and legacy status.
- [ ] Run Python tests, C++ tests, `compileall`, and `git diff --check`.
- [ ] Record hardware-only verification that remains.
