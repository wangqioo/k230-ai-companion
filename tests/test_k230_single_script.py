import importlib.util
import json
import subprocess
import sys
import types
import unittest
from pathlib import Path

from src.transport import vision_protocol


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dist" / "main_vision_uart_single.py"


class MemoryUART:
    def __init__(self):
        self.writes = []

    def write(self, data):
        self.writes.append(data)
        return len(data)


class K230SingleScriptTest(unittest.TestCase):
    def setUp(self):
        self._sentinel = object()
        self._modules = {}

    def tearDown(self):
        for name, previous in self._modules.items():
            if previous is self._sentinel:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous

    def _install_module(self, name, module):
        if name not in self._modules:
            self._modules[name] = sys.modules.get(name, self._sentinel)
        sys.modules[name] = module

    def _install_canmv_fakes(self):
        libs = types.ModuleType("libs")
        pipeline = types.ModuleType("libs.PipeLine")
        ai_base = types.ModuleType("libs.AIBase")
        ai2d = types.ModuleType("libs.AI2D")
        media_pkg = types.ModuleType("media")
        media_mod = types.ModuleType("media.media")
        machine = types.ModuleType("machine")
        nncase = types.ModuleType("nncase_runtime")
        ulab = types.ModuleType("ulab")
        ulab_numpy = types.ModuleType("ulab.numpy")

        class ScopedTiming:
            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        class PipeLine:
            pass

        class AIBase:
            pass

        class Ai2d:
            pass

        class FPIOA:
            UART2_TXD = object()
            UART2_RXD = object()

        class UART:
            UART2 = object()

        pipeline.PipeLine = PipeLine
        pipeline.ScopedTiming = ScopedTiming
        ai_base.AIBase = AIBase
        ai2d.Ai2d = Ai2d
        media_mod.ALIGN_UP = lambda value, align: (value + align - 1) & ~(align - 1)
        machine.FPIOA = FPIOA
        machine.UART = UART

        self._install_module("libs", libs)
        self._install_module("libs.PipeLine", pipeline)
        self._install_module("libs.AIBase", ai_base)
        self._install_module("libs.AI2D", ai2d)
        self._install_module("media", media_pkg)
        self._install_module("media.media", media_mod)
        self._install_module("machine", machine)
        self._install_module("nncase_runtime", nncase)
        self._install_module("ulab", ulab)
        self._install_module("ulab.numpy", ulab_numpy)
        self._install_module("ujson", json)
        self._install_module("image", types.ModuleType("image"))
        self._install_module("aidemo", types.ModuleType("aidemo"))

    def _load_single_script(self):
        self._install_canmv_fakes()
        spec = importlib.util.spec_from_file_location("k230_single_under_test", OUT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_builder_generates_import_free_single_script(self):
        subprocess.run(
            [sys.executable, str(ROOT / "tools" / "build_k230_single.py")],
            check=True,
            capture_output=True,
            text=True,
        )

        script = OUT.read_text(encoding="utf-8")

        self.assertIn("class VisionPublisher", script)
        self.assertIn("class HeadPoseDetector", script)
        self.assertNotIn("from transport.", script)
        self.assertNotIn("from vision.", script)

    def test_single_script_protocol_matches_module_version(self):
        subprocess.run(
            [sys.executable, str(ROOT / "tools" / "build_k230_single.py")],
            check=True,
            capture_output=True,
            text=True,
        )
        single = self._load_single_script()

        observation = {
            "center_x": -100,
            "center_y": 200,
            "width": 300,
            "height": 400,
            "pitch_cd": 123,
            "yaw_cd": -456,
            "roll_cd": 789,
            "confidence": 88,
        }

        self.assertEqual(
            single.pack_face_observation(observation),
            vision_protocol.pack_face_observation(observation),
        )
        self.assertEqual(
            single.encode_frame(
                vision_protocol.MSG_FACE,
                vision_protocol.pack_face_observation(observation),
                sequence=7,
                timestamp_ms=12345,
            ),
            vision_protocol.encode_frame(
                vision_protocol.MSG_FACE,
                vision_protocol.pack_face_observation(observation),
                sequence=7,
                timestamp_ms=12345,
            ),
        )

    def test_single_script_publisher_writes_esp32_frames(self):
        subprocess.run(
            [sys.executable, str(ROOT / "tools" / "build_k230_single.py")],
            check=True,
            capture_output=True,
            text=True,
        )
        single = self._load_single_script()
        uart = MemoryUART()
        publisher = single.VisionPublisher(uart, initial_sequence=0xFFFF)

        publisher.publish_heartbeat(timestamp_ms=10)
        publisher.publish_face_lost(timestamp_ms=20)

        first = vision_protocol.decode_frame(uart.writes[0])
        second = vision_protocol.decode_frame(uart.writes[1])
        self.assertEqual(first["type"], vision_protocol.MSG_HEARTBEAT)
        self.assertEqual(first["sequence"], 0xFFFF)
        self.assertEqual(second["type"], vision_protocol.MSG_FACE_LOST)
        self.assertEqual(second["sequence"], 0)


if __name__ == "__main__":
    unittest.main()
