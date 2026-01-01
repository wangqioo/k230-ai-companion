"""
K230 WiFi 连接测试
部署到 /sdcard/pet/network/test_wifi.py
"""

import time
from network import WLAN

# ============ 配置 ============
WIFI_SSID = "WQ's iPhone"      # 修改为你的WiFi
WIFI_PASSWORD = "12345678"  # 修改为你的密码
# ==============================


def connect_wifi(ssid, password, timeout=15):
    """连接WiFi"""
    print("=" * 40)
    print("K230 WiFi 连接测试")
    print("=" * 40)

    wlan = WLAN(0)  # 0 = STA模式（连接路由器）

    # 如果已连接，先断开
    if wlan.isconnected():
        print("已有连接，断开中...")
        wlan.disconnect()
        time.sleep(1)

    print(f"正在连接: {ssid}")
    wlan.connect(ssid, password)

    # 等待连接
    start = time.time()
    while not wlan.isconnected():
        if time.time() - start > timeout:
            print("连接超时!")
            return None
        print(".", end="")
        time.sleep(0.5)

    print()
    config = wlan.ifconfig()
    print("-" * 40)
    print(f"连接成功!")
    print(f"  IP地址:  {config[0]}")
    print(f"  子网掩码: {config[1]}")
    print(f"  网关:    {config[2]}")
    print(f"  DNS:     {config[3]}")
    print("-" * 40)

    return wlan


if __name__ == "__main__":
    wlan = connect_wifi(WIFI_SSID, WIFI_PASSWORD)

    if wlan:
        print("WiFi连接成功，可以进行下一步测试")
        print("请记住K230的IP地址，用于调试")
    else:
        print("WiFi连接失败，请检查:")
        print("  1. WiFi名称和密码是否正确")
        print("  2. 路由器是否为2.4GHz（不支持5GHz）")
        print("  3. 信号是否足够强")
