"""
最小HTTP测试服务器 - 用于K230通信测试
运行方式: python test_server.py
"""

from flask import Flask, request, jsonify, send_file
import base64
import os
from datetime import datetime

app = Flask(__name__)

# 存储目录
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.route('/ping', methods=['GET'])
def ping():
    """心跳测试 - K230用GET请求测试连通性"""
    return jsonify({
        "status": "ok",
        "message": "服务器正常运行",
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })


@app.route('/echo', methods=['POST'])
def echo():
    """回显测试 - K230用POST发JSON，服务器原样返回"""
    data = request.get_json()
    print(f"[收到POST] {data}")
    return jsonify({
        "status": "ok",
        "received": data,
        "message": "数据已收到"
    })


@app.route('/upload/image', methods=['POST'])
def upload_image():
    """图片上传测试 - 接收base64图片并保存"""
    data = request.get_json()

    if 'image' not in data:
        return jsonify({"status": "error", "message": "缺少image字段"}), 400

    try:
        # 解码base64
        img_data = base64.b64decode(data['image'])

        # 保存文件
        filename = f"img_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        filepath = os.path.join(UPLOAD_DIR, filename)
        with open(filepath, 'wb') as f:
            f.write(img_data)

        print(f"[图片保存] {filepath} ({len(img_data)} bytes)")

        return jsonify({
            "status": "ok",
            "message": f"图片已保存: {filename}",
            "size": len(img_data)
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/upload/audio', methods=['POST'])
def upload_audio():
    """音频上传测试 - 接收base64音频并保存"""
    data = request.get_json()

    if 'audio' not in data:
        return jsonify({"status": "error", "message": "缺少audio字段"}), 400

    try:
        # 解码base64
        audio_data = base64.b64decode(data['audio'])

        # 保存文件
        filename = f"audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
        filepath = os.path.join(UPLOAD_DIR, filename)
        with open(filepath, 'wb') as f:
            f.write(audio_data)

        print(f"[音频保存] {filepath} ({len(audio_data)} bytes)")

        return jsonify({
            "status": "ok",
            "message": f"音频已保存: {filename}",
            "size": len(audio_data)
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/chat', methods=['POST'])
def chat():
    """对话接口 - 模拟完整对话流程（暂时返回固定回复）"""
    data = request.get_json()
    print(f"[对话请求] {data}")

    # TODO: 后续接入阿里大模型
    # 现在先返回固定回复
    return jsonify({
        "status": "ok",
        "text": "你好！我是桌面宠物，很高兴见到你！",
        "expression": "happy",
        "audio_url": None  # 暂时没有TTS
    })


@app.route('/audio/<filename>', methods=['GET'])
def get_audio(filename):
    """下载音频文件"""
    filepath = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(filepath):
        return send_file(filepath, mimetype='audio/wav')
    else:
        return jsonify({"status": "error", "message": "文件不存在"}), 404


@app.route('/test_audio', methods=['GET'])
def test_audio():
    """生成测试音频并返回下载地址"""
    import struct
    import math

    # 生成一个简单的正弦波测试音频 (1秒, 440Hz)
    sample_rate = 16000
    duration = 1
    frequency = 440  # A4音符

    # 生成音频数据
    samples = []
    for i in range(sample_rate * duration):
        t = i / sample_rate
        value = int(32767 * 0.5 * math.sin(2 * math.pi * frequency * t))
        samples.append(struct.pack('<h', value))
    audio_data = b''.join(samples)

    # 创建WAV头
    byte_rate = sample_rate * 2
    block_align = 2
    file_size = len(audio_data) + 36

    header = b'RIFF'
    header += struct.pack('<I', file_size)
    header += b'WAVE'
    header += b'fmt '
    header += struct.pack('<I', 16)
    header += struct.pack('<H', 1)
    header += struct.pack('<H', 1)
    header += struct.pack('<I', sample_rate)
    header += struct.pack('<I', byte_rate)
    header += struct.pack('<H', block_align)
    header += struct.pack('<H', 16)
    header += b'data'
    header += struct.pack('<I', len(audio_data))

    wav_data = header + audio_data

    # 保存测试音频
    filename = "test_tone.wav"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, 'wb') as f:
        f.write(wav_data)

    print(f"[生成测试音频] {filepath} ({len(wav_data)} bytes)")

    return jsonify({
        "status": "ok",
        "audio_url": "/audio/" + filename,
        "size": len(wav_data),
        "message": "测试音频已生成 (440Hz, 1秒)"
    })


if __name__ == '__main__':
    import socket

    # 获取本机IP
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)

    print("=" * 50)
    print("K230 测试服务器")
    print("=" * 50)
    print(f"本机IP: {local_ip}")
    print(f"服务地址: http://{local_ip}:8080")
    print("-" * 50)
    print("测试端点:")
    print("  GET  /ping          - 心跳测试")
    print("  POST /echo          - JSON回显")
    print("  POST /upload/image  - 图片上传")
    print("  POST /upload/audio  - 音频上传")
    print("  POST /chat          - 对话接口")
    print("-" * 50)
    print("上传文件保存在:", UPLOAD_DIR)
    print("=" * 50)

    # 监听所有网卡，端口8080
    app.run(host='0.0.0.0', port=8080, debug=True)
