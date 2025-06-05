# === CONTROLLER (ESP32-S3) ===
# main.py on controller

import time
import espnow
import network
from machine import Pin
from linecode import *  # Giả sử bạn đã có class scanner trong linecode
from ws2812 import *      # Giả sử bạn đã có class WS2812

# --- WiFi & ESP-NOW ---
wifi = network.WLAN(network.STA_IF)
wifi.active(True)

esp = espnow.ESPNow()
esp.active(True)

robot_mac = b'\xcc\xba\x97\n\xc1\xe8'  # Replace with actual MAC
esp.add_peer(robot_mac)


# --- Buttons ---
btn_a = Pin(13, Pin.IN, Pin.PULL_UP)
btn_b = Pin(12, Pin.IN, Pin.PULL_UP)
button_f = Pin(38, Pin.IN, Pin.PULL_UP)
button_b = Pin(35, Pin.IN, Pin.PULL_UP)
button_l = Pin(36, Pin.IN, Pin.PULL_UP)
button_r = Pin(37, Pin.IN, Pin.PULL_UP)

# --- Global State ---
mode = 4

COLOR_MAP = {
    'f': (0, 40, 0),     # Xanh lá
    'b': (0, 0, 40),     # Xanh dương
    'l': (40, 0, 0),     # Đỏ
    'r': (40, 40, 0),   # Vàng
}

def send_mode(new_mode):
    global mode
    mode = new_mode
    esp.send(robot_mac, str(mode))

def mode_0_laptrinh():
    print("[MODE 0] Lập trình điều khiển...")
    send_mode('0')
    command_list = []
    move_colors = []

    while True:
        # Quét mã 'x' để xóa lệnh
        if not btn_a.value():
            bits = scanner.read_binary()
            cmd = scanner.decode(bits)
            if cmd == 'XOA' and command_list:
                command_list.pop()
                move_colors.pop()
                leds.show_pattern(move_colors)
                print("Xóa lệnh:", command_list)
            elif cmd == '1':
                mode_1_dieukhien()
            elif cmd == '2':
                mode_2_hoc()
            elif cmd == '3':
                mode_3_ai()
            elif cmd == '4':
                mode_4_khac()
            else
                command_list.append(cmd)
            time.sleep(0.5)

        # Kiểm tra các nút: f, b, l, r
        for cmd, button in [('f', button_f), ('b', button_b), ('l', button_l), ('r', button_r)]:
            if not button.value():
                command_list.append(cmd)
                move_colors.append(COLOR_MAP[cmd])
                leds.show_pattern(move_colors)
                print("Lệnh:", command_list)
                time.sleep(0.3)

        # Gửi chuỗi lệnh nếu nhấn nút B
        if not btn_b.value():
            move_colors = []
            leds.show_pattern(move_colors)
            print("Gửi lệnh:", command_list)
            for cmd in command_list:
                esp.send(robot_mac, cmd)
                time.sleep(0.2)
            esp.send(robot_mac, b'END')
            command_list = []

def mode_1_dieukhien():
    print("[MODE 1] dieu khien")
    send_mode('1')
    while True:
        if not btn_a.value():
            bits = scanner.read_binary()
            cmd = scanner.decode(bits)
            if cmd == '0':
                mode_0_laptrinh()
            elif cmd == '2':
                mode_2_hoc()
            elif cmd == '3':
                mode_3_ai()
            elif cmd == '4':
                mode_4_khac()
            time.sleep(0.5)
        else:
            for cmd, button in [('f', button_f), ('b', button_b), ('l', button_l), ('r', button_r)]:
                if not button.value():
                    print("Gửi lệnh:", cmd)
                    esp.send(robot_mac, cmd)

def mode_2_hoc():
    print("[MODE 2] học")
    send_mode('2')
    
    while True:
        if not btn_a.value():
            bits = scanner.read_binary()
            cmd = scanner.decode(bits)
            if cmd == '0':
                mode_0_laptrinh()
            elif cmd == '1':
                mode_1_dieukhien()
            elif cmd == '3':
                mode_3_ai()
            elif cmd == '4':
                mode_4_khac()
            time.sleep(0.5)
        else:
            if not btn_a.value():
                bits = scanner.read_binary()
                id = scanner.decode(bits)
                esp.send(robot_mac, id)
                print("Gửi ID:", id)
                time.sleep(0.5)

def mode_3_ai():
    print("[MODE 3] Trò chuyện cùng AI")
    send_mode('3')
    bits = scanner.read()
    feature = scanner.decode(bits)
    esp.send(robot_mac, feature)

def mode_4_khac():
    print("[MODE 4] Gửi tính năng khác...")
    send_mode('4')
    bits = scanner.read_binary()
    feature = scanner.decode(bits)
    esp.send(robot_mac, feature)
# --- MAIN LOOP ---
try:
    while True:
        if not btn_a.value():
            print("Đang quét mode...")
            bits = scanner.read_binary()
            mode_id = scanner.decode(bits)
            print("Đã chọn mode:", mode_id)

            if mode_id == '0':
                mode_0_laptrinh()
            elif mode_id == '1':
                mode_1_hoc()
            elif mode_id == 4:
                mode_4_khac()
            # elif mode_id == 3:
            #     mode_3_ai()

            time.sleep(0.5)

except KeyboardInterrupt:
    print("Dừng chương trình.")
