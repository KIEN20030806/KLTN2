import time
import espnow
import network
from machine import Pin
from linecode import *  # Giả sử bạn đã có class scanner trong linecode
from ws2812 import *      # Giả sử bạn đã có class WS2812
from ai_controller import *

# --- WiFi & ESP-NOW ---
wifi = network.WLAN(network.STA_IF)
wifi.active(True)

esp = espnow.ESPNow()
esp.active(True)

robot_mac = b'\xcc\xba\x97\n\xc1\xe8'  # Replace with actual MAC

try:
    esp.add_peer(robot_mac)
except OSError as e:
    if e.args[0] == -12395:
        print("Peer already exists, skipping...")
    else:
        raise
                   
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
    time.sleep(0.5)
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
            elif cmd == '0':
                mode_0_laptrinh()
            elif cmd == '1':
                mode_1_dieukhien()
            elif cmd == '2':
                mode_2_hoc()
            elif cmd == '3':
                mode_3_ai()
            elif cmd == '4':
                mode_4_khac()
            time.sleep(0.1)

        # Kiểm tra các nút: f, b, l, r
        for cmd, button in [('f', button_f), ('b', button_b), ('l', button_l), ('r', button_r)]:
            if not button.value():
                command_list.append(cmd)
                move_colors.append(COLOR_MAP[cmd])
                leds.show_pattern(move_colors)
                print("Lệnh:", command_list)
                time.sleep(0.1)

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
            time.sleep(0.1)

def mode_1_dieukhien():
    print("[MODE 1] dieu khien")
    send_mode('1')
    time.sleep(0.5)

    prev_states = {
        'f': 1, 'b': 1, 'l': 1, 'r': 1
    }

    while True:
        if not btn_a.value():
            bits = scanner.read_binary()
            cmd = scanner.decode(bits)
            if cmd == '0':
                mode_0_laptrinh()
                return
            elif cmd == '1':
                mode_1_dieukhien()
                return
            elif cmd == '2':
                mode_2_hoc()
                return
            elif cmd == '3':
                mode_3_ai()
                return
            elif cmd == '4':
                mode_4_khac()
                return
            time.sleep(0.1)
        else:
            for cmd, button in [('f', button_f), ('b', button_b), ('l', button_l), ('r', button_r)]:
                current = button.value()

                # Nếu nhấn xuống (từ 1 → 0)
                if current == 0 and prev_states[cmd] == 1:
                    print("Gửi lệnh:", cmd)
                    esp.send(robot_mac, cmd)

                # Nếu thả ra (từ 0 → 1)
                elif current == 1 and prev_states[cmd] == 0:
                    print("Thả nút, gửi lệnh: s")
                    esp.send(robot_mac, 's')

                prev_states[cmd] = current

        time.sleep(0.05)  # giảm độ trễ, tăng độ nhạy

def mode_2_hoc():
    print("[MODE 2] học")
    send_mode('2')
    time.sleep(0.5)
    
    while True:
        if not btn_a.value():
            bits = scanner.read_binary()
            cmd = scanner.decode(bits)
            if cmd == '0':
                mode_0_laptrinh()
            elif cmd == '1':
                mode_1_dieukhien()
            elif cmd == '2':
                mode_2_hoc()
            elif cmd == '3':
                mode_3_ai()
            elif cmd == '4':
                mode_4_khac()
            time.sleep(0.1)
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
    app.connect()
    while True:
        if not btn_a.value():
            bits = scanner.read_binary()
            cmd = scanner.decode(bits)
            if cmd == '0':
                mode_0_laptrinh()
            elif cmd == '1':
                mode_1_dieukhien()
            elif cmd == '2':
                mode_2_hoc()
            elif cmd == '3':
                mode_3_ai()
            elif cmd == '4':
                mode_4_khac()
            time.sleep(0.1)
        else:
            app.run()

def mode_4_khac():
    print("[MODE 4] Gửi tính năng khác...")
    send_mode('4')
    time.sleep(0.5)
    while True:
        if not btn_a.value():
            bits = scanner.read_binary()
            cmd = scanner.decode(bits)
            if cmd == '0':
                mode_0_laptrinh()
            elif cmd == '1':
                mode_1_dieukhien()
            elif cmd == '2':
                mode_2_hoc()
            elif cmd == '3':
                mode_3_ai()
            elif cmd == '4':
                mode_4_khac()
            time.sleep(0.1)
        else:
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
                mode_1_dieukhien()
            elif mode_id == '2':
                mode_2_hoc()
            elif mode_id == '3':
                mode_3_ai()
            elif mode_id == '4':
                mode_4_khac()
            time.sleep(0.1)

except KeyboardInterrupt:
    print("Dừng chương trình.")

