"""
桌面宠物服务器 - 接入阿里通义千问
运行方式: python app.py
"""

import os
import base64
import json
import asyncio
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from openai import OpenAI
import dashscope
from dashscope.audio.asr import Recognition
from dashscope.audio.asr.recognition import RecognitionCallback

# ============ 配置 ============
DASHSCOPE_API_KEY = "sk-46315e07b380467fa625f276681ba77e"
MODEL_NAME = "qwen-turbo"  # 可选: qwen-turbo, qwen-plus, qwen-max

# 设置DashScope API Key
dashscope.api_key = DASHSCOPE_API_KEY

# 系统提示词 - 定义桌宠人设
SYSTEM_PROMPT = """你是一个可爱的桌面宠物，名叫"小豆"。你的性格特点：
- 活泼可爱，喜欢用简短的句子回复
- 偶尔会撒娇，用"嘿嘿"、"呀"等语气词
- 回复要简洁，通常1-2句话，不超过50个字
- 会关心主人的状态，比如问主人累不累

记住：你是通过语音和主人交流的，所以回复要口语化，适合朗读。"""
# ==============================

app = Flask(__name__)

# 存储目录
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'uploads')
AUDIO_DIR = os.path.join(os.path.dirname(__file__), 'audio')
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)

# 初始化通义千问客户端
qwen_client = OpenAI(
    api_key=DASHSCOPE_API_KEY,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

# 对话历史（简单版，生产环境应该用数据库）
conversation_history = []


class ASRCallback(RecognitionCallback):
    """ASR回调类"""
    def on_open(self):
        pass
    def on_close(self):
        pass
    def on_event(self, result):
        pass
    def on_error(self, result):
        pass
    def on_complete(self):
        pass


def speech_to_text(audio_file):
    """使用阿里云Paraformer进行语音识别"""
    try:
        callback = ASRCallback()
        recognition = Recognition(
            model='paraformer-realtime-v2',
            format='wav',
            sample_rate=16000,
            callback=callback,
            language_hints=['zh']
        )

        result = recognition.call(audio_file)

        if result.status_code == 200:
            # 提取识别文本
            if result.output and 'sentence' in result.output:
                sentences = result.output['sentence']
                text = ''.join([s.get('text', '') for s in sentences])
                return text.strip()
            return ""
        else:
            print(f"[ASR错误] {result.code}: {result.message}")
            return ""

    except Exception as e:
        print(f"[ASR异常] {e}")
        return ""


def chat_with_qwen(user_message):
    """调用通义千问进行对话"""
    global conversation_history

    # 添加用户消息到历史
    conversation_history.append({
        "role": "user",
        "content": user_message
    })

    # 只保留最近10轮对话
    if len(conversation_history) > 20:
        conversation_history = conversation_history[-20:]

    # 构建消息
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(conversation_history)

    try:
        response = qwen_client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            max_tokens=100,
            temperature=0.8
        )

        assistant_message = response.choices[0].message.content

        # 添加助手回复到历史
        conversation_history.append({
            "role": "assistant",
            "content": assistant_message
        })

        return assistant_message

    except Exception as e:
        print(f"[通义千问错误] {e}")
        return "哎呀，我好像有点迷糊了，再说一遍好吗？"


def text_to_speech_edge(text, output_file):
    """使用Edge-TTS进行语音合成，输出WAV格式（K230兼容）"""
    import edge_tts
    import subprocess

    # 中文女声
    voice = "zh-CN-XiaoxiaoNeural"

    # 先生成临时MP3
    mp3_file = output_file.replace('.wav', '_temp.mp3')

    async def _tts():
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(mp3_file)

    asyncio.run(_tts())

    # 转换为WAV (16kHz, 16bit, mono - K230兼容格式)
    # -fflags +bitexact: 去掉metadata，生成干净的44字节WAV头
    subprocess.run([
        'ffmpeg', '-y', '-i', mp3_file,
        '-ar', '16000', '-ac', '1', '-sample_fmt', 's16',
        '-fflags', '+bitexact',
        output_file
    ], capture_output=True)

    # 删除临时MP3
    if os.path.exists(mp3_file):
        os.remove(mp3_file)

    return output_file


# ============ API 端点 ============

@app.route('/ping', methods=['GET'])
def ping():
    """心跳测试"""
    return jsonify({
        "status": "ok",
        "message": "服务器正常运行",
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })


@app.route('/chat/text', methods=['POST'])
def chat_text():
    """文字对话接口（测试用）"""
    data = request.get_json()
    user_text = data.get("text", "")

    if not user_text:
        return jsonify({"status": "error", "message": "缺少text字段"}), 400

    print(f"[用户] {user_text}")

    # 调用通义千问
    reply = chat_with_qwen(user_text)
    print(f"[小豆] {reply}")

    return jsonify({
        "status": "ok",
        "text": reply,
        "expression": "happy"
    })


@app.route('/chat/audio', methods=['POST'])
def chat_audio():
    """语音对话接口 - 接收音频，返回音频回复"""
    data = request.get_json()

    if 'audio' not in data:
        return jsonify({"status": "error", "message": "缺少audio字段"}), 400

    try:
        # 1. 解码并保存上传的音频
        audio_data = base64.b64decode(data['audio'])
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        input_file = os.path.join(UPLOAD_DIR, f"input_{timestamp}.wav")

        with open(input_file, 'wb') as f:
            f.write(audio_data)
        print(f"[收到音频] {input_file} ({len(audio_data)} bytes)")

        # 2. 语音识别 (ASR) - 使用阿里云Paraformer
        user_text = speech_to_text(input_file)
        print(f"[ASR识别] {user_text}")

        if not user_text:
            return jsonify({
                "status": "error",
                "message": "无法识别语音内容"
            }), 400

        # 3. 调用通义千问
        reply = chat_with_qwen(user_text)
        print(f"[小豆回复] {reply}")

        # 4. 语音合成 (TTS)
        output_file = os.path.join(AUDIO_DIR, f"reply_{timestamp}.wav")
        text_to_speech_edge(reply, output_file)
        print(f"[TTS生成] {output_file}")

        # 5. 返回结果
        return jsonify({
            "status": "ok",
            "user_text": user_text,
            "text": reply,
            "expression": "happy",
            "audio_url": f"/audio/reply_{timestamp}.wav"
        })

    except Exception as e:
        print(f"[错误] {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/audio/<filename>', methods=['GET'])
def get_audio(filename):
    """下载音频文件"""
    # 先在audio目录找
    filepath = os.path.join(AUDIO_DIR, filename)
    if os.path.exists(filepath):
        return send_file(filepath)

    # 再在uploads目录找
    filepath = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(filepath):
        return send_file(filepath)

    return jsonify({"status": "error", "message": "文件不存在"}), 404


@app.route('/upload/image', methods=['POST'])
def upload_image():
    """图片上传"""
    data = request.get_json()

    if 'image' not in data:
        return jsonify({"status": "error", "message": "缺少image字段"}), 400

    try:
        img_data = base64.b64decode(data['image'])
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
    """音频上传"""
    data = request.get_json()

    if 'audio' not in data:
        return jsonify({"status": "error", "message": "缺少audio字段"}), 400

    try:
        audio_data = base64.b64decode(data['audio'])
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


@app.route('/test_audio', methods=['GET'])
def test_audio():
    """生成TTS测试音频"""
    try:
        text = "你好呀，我是小豆，很高兴见到你！"
        filename = "test_tts.wav"
        filepath = os.path.join(AUDIO_DIR, filename)

        text_to_speech_edge(text, filepath)

        print(f"[测试TTS] {filepath}")

        return jsonify({
            "status": "ok",
            "audio_url": f"/audio/{filename}",
            "text": text,
            "message": "TTS测试音频已生成"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/test_asr', methods=['POST'])
def test_asr():
    """测试ASR语音识别"""
    data = request.get_json()

    if 'audio' not in data:
        return jsonify({"status": "error", "message": "缺少audio字段"}), 400

    try:
        # 解码并保存音频
        audio_data = base64.b64decode(data['audio'])
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        input_file = os.path.join(UPLOAD_DIR, f"asr_test_{timestamp}.wav")

        with open(input_file, 'wb') as f:
            f.write(audio_data)

        # 语音识别
        text = speech_to_text(input_file)

        return jsonify({
            "status": "ok",
            "text": text,
            "message": "ASR识别完成"
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == '__main__':
    import socket

    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)

    print("=" * 50)
    print("桌面宠物服务器 - 通义千问版")
    print("=" * 50)
    print(f"本机IP: {local_ip}")
    print(f"服务地址: http://{local_ip}:8080")
    print("-" * 50)
    print("API端点:")
    print("  GET  /ping           - 心跳测试")
    print("  POST /chat/text      - 文字对话")
    print("  POST /chat/audio     - 语音对话(完整流程)")
    print("  POST /test_asr       - 测试语音识别")
    print("  GET  /test_audio     - 测试TTS")
    print("  GET  /audio/<file>   - 下载音频")
    print("-" * 50)
    print(f"LLM模型: {MODEL_NAME}")
    print("ASR模型: paraformer-v2")
    print("TTS引擎: Edge-TTS")
    print("=" * 50)

    app.run(host='0.0.0.0', port=8080, debug=True)
