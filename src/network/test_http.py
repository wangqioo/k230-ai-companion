"""
K230 HTTP 请求测试 (使用socket实现)
部署到 /sdcard/pet/network/test_http.py
"""

import time
import json
import socket
from network import WLAN

# ============ 配置 ============
WIFI_SSID = "WQ's iPhone"
WIFI_PASSWORD = "12345678"
SERVER_IP = "172.20.10.3"
SERVER_PORT = 8080
# ==============================


def connect_wifi():
    """连接WiFi"""
    wlan = WLAN(0)
    if wlan.isconnected():
        print("WiFi已连接: " + wlan.ifconfig()[0])
        return wlan

    print("连接WiFi: " + WIFI_SSID)
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)

    timeout = 15
    start = time.time()
    while not wlan.isconnected():
        if time.time() - start > timeout:
            raise Exception("WiFi连接超时")
        time.sleep(0.5)

    print("已连接: " + wlan.ifconfig()[0])
    return wlan


def http_get(host, port, path):
    """发送HTTP GET请求"""
    addr = socket.getaddrinfo(host, port)[0][-1]
    s = socket.socket()
    s.connect(addr)

    request = "GET " + path + " HTTP/1.1\r\n"
    request += "Host: " + host + "\r\n"
    request += "Connection: close\r\n\r\n"
    s.send(request.encode())

    response = b""
    while True:
        chunk = s.recv(1024)
        if not chunk:
            break
        response += chunk
    s.close()

    # 分离header和body
    parts = response.split(b"\r\n\r\n", 1)
    header = parts[0].decode()
    body = parts[1].decode() if len(parts) > 1 else ""

    # 获取状态码
    status_line = header.split("\r\n")[0]
    status_code = int(status_line.split()[1])

    return status_code, body


def http_post_json(host, port, path, data):
    """发送HTTP POST JSON请求"""
    addr = socket.getaddrinfo(host, port)[0][-1]
    s = socket.socket()
    s.connect(addr)

    body = json.dumps(data)
    request = "POST " + path + " HTTP/1.1\r\n"
    request += "Host: " + host + "\r\n"
    request += "Content-Type: application/json\r\n"
    request += "Content-Length: " + str(len(body)) + "\r\n"
    request += "Connection: close\r\n"
    request += "\r\n"
    request += body
    s.send(request.encode())

    response = b""
    while True:
        chunk = s.recv(1024)
        if not chunk:
            break
        response += chunk
    s.close()

    # 分离header和body
    parts = response.split(b"\r\n\r\n", 1)
    header = parts[0].decode()
    resp_body = parts[1].decode() if len(parts) > 1 else ""

    # 获取状态码
    status_line = header.split("\r\n")[0]
    status_code = int(status_line.split()[1])

    return status_code, resp_body


def test_ping():
    """测试1: GET请求 - 心跳测试"""
    print("\n" + "=" * 40)
    print("测试1: GET /ping")
    print("=" * 40)

    try:
        url = "http://" + SERVER_IP + ":" + str(SERVER_PORT) + "/ping"
        print("请求: " + url)
        status, body = http_get(SERVER_IP, SERVER_PORT, "/ping")
        print("状态码: " + str(status))
        print("响应: " + body)
        return status == 200
    except Exception as e:
        print("错误: " + str(e))
        return False


def test_echo():
    """测试2: POST请求 - JSON回显"""
    print("\n" + "=" * 40)
    print("测试2: POST /echo")
    print("=" * 40)

    try:
        data = {
            "message": "Hello from K230",
            "timestamp": time.time()
        }
        url = "http://" + SERVER_IP + ":" + str(SERVER_PORT) + "/echo"
        print("请求: " + url)
        print("数据: " + str(data))

        status, body = http_post_json(SERVER_IP, SERVER_PORT, "/echo", data)
        print("状态码: " + str(status))
        print("响应: " + body)
        return status == 200
    except Exception as e:
        print("错误: " + str(e))
        return False


def test_large_post():
    """测试3: 大数据POST"""
    print("\n" + "=" * 40)
    print("测试3: 较大数据POST")
    print("=" * 40)

    try:
        fake_data = "A" * 1000
        data = {
            "type": "large_test",
            "size": len(fake_data),
            "data": fake_data
        }
        url = "http://" + SERVER_IP + ":" + str(SERVER_PORT) + "/echo"
        print("请求: " + url)
        print("数据大小: " + str(len(fake_data)) + " 字节")

        status, body = http_post_json(SERVER_IP, SERVER_PORT, "/echo", data)
        print("状态码: " + str(status))
        if len(body) > 200:
            print("响应(截断): " + body[:200] + "...")
        else:
            print("响应: " + body)
        return status == 200
    except Exception as e:
        print("错误: " + str(e))
        return False


if __name__ == "__main__":
    print("K230 HTTP 通信测试 (socket版)")
    print("服务器地址: http://" + SERVER_IP + ":" + str(SERVER_PORT))
    print()

    # 先连接WiFi
    try:
        connect_wifi()
    except Exception as e:
        print("WiFi连接失败: " + str(e))
        raise

    # 运行测试
    results = []
    results.append(("GET /ping", test_ping()))
    results.append(("POST /echo", test_echo()))
    results.append(("大数据POST", test_large_post()))

    # 汇总结果
    print("\n" + "=" * 40)
    print("测试结果汇总")
    print("=" * 40)
    for name, passed in results:
        if passed:
            status = "通过"
        else:
            status = "失败"
        print("  " + name + ": " + status)
    print()

    all_passed = all(r[1] for r in results)
    if all_passed:
        print("全部测试通过!")
    else:
        print("有测试失败，请检查网络配置")
