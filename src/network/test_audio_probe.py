"""
K230 音频模块探测
检测可用的音频API
"""

print("=" * 40)
print("K230 音频模块探测")
print("=" * 40)

modules_to_try = [
    "audio",
    "media.audio",
    "media.pyaudio",
    "pyaudio",
    "machine",
    "player",
    "recorder",
    "media.wave",
    "wave",
    "media.player",
    "media.recorder",
    "media",
]

for mod_name in modules_to_try:
    try:
        mod = __import__(mod_name)
        print("OK: " + mod_name)
        # 列出模块内容
        attrs = dir(mod)
        print("    -> " + str(attrs[:10]))  # 只显示前10个
    except ImportError:
        print("NO: " + mod_name)
    except Exception as e:
        print("ERR: " + mod_name + " - " + str(e))

print("\n" + "=" * 40)
print("检查 media 模块详情")
print("=" * 40)

try:
    import media
    print("media 模块内容:")
    for attr in dir(media):
        print("  - " + attr)
except:
    print("media 模块不存在")

print("\n" + "=" * 40)
print("检查 machine 模块音频相关")
print("=" * 40)

try:
    import machine
    attrs = dir(machine)
    audio_related = [a for a in attrs if 'audio' in a.lower() or 'i2s' in a.lower() or 'sound' in a.lower()]
    if audio_related:
        print("音频相关: " + str(audio_related))
    else:
        print("machine 模块中无明显音频相关API")
        print("全部属性: " + str(attrs))
except Exception as e:
    print("错误: " + str(e))
