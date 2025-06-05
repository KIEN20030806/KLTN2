# === ROBOT (ESP32-S3) ===
# main.py on robot
import time
import espnow
import network
from robot import Robot
from rfid import rfid
import select
from audio import AudioPlayer
from ht16k33 import display
from ai_robot import AiRobot
import uasyncio as asyncio
from machine import ADC, Pin, I2S
import sys
import gc


i2s = I2S(0, sck=Pin(2), ws=Pin(1), sd=Pin(43),mode=I2S.TX, bits=16, format=I2S.MONO,rate=16000, ibuf=4096)
audio = AudioPlayer(i2s)
robot = Robot(audio)
app = AiRobot(i2s)
wifi = network.WLAN(network.STA_IF)
wifi.active(True)

esp = espnow.ESPNow()
esp.active(True)
controller_mac = b'\xcc\xba\x97\n\x8ap'  # replace with actual MAC

try:
    esp.add_peer(controller_mac)
except OSError as e:
    if e.args[0] == -12395:
        print("Peer already exists, skipping...")
    else:
        raise
mode = 0

def mode_0_program():
    display.show_emotion("NEUTRAL")
    print("[MODE 0] Nhận và thực thi lệnh lập trình...")
    asyncio.run(audio.play_wav("MODE0.wav"))
    command_list = []
    while True:
        peer, msg = esp.recv()
        if msg:
            if msg == b'END':
                print("Hoàn tất nhận lệnh:", command_list)
                for cmd in command_list:
                    print("Thực thi lệnh:", cmd)
                    display.show_emotion("NEUTRAL")
                    asyncio.run(audio.play_wav("STEP.wav"))
                    robot.move(cmd)
                command_list = []
                uid = rfid.scan_card()
                if uid:
                    asyncio.run(audio.play_wav(rfid.uid_wav(uid)))
            else:
                try:
                    cmd = msg.decode()
                
                    if cmd == '0':
                        continue
                    elif cmd == '1':
                        print("Chuyển sang mode 1 (điều khiển)")
                        mode_1_control()
                        return  # dừng mode 0 sau khi chuyển
                    elif cmd == '2':
                        print("Chuyển sang mode 2 (học)")
                        mode_2_learn()
                        return
                    elif cmd == '3':
                        print("Chuyển sang mode 3 (AI)")
                        mode_3_ai()
                        return
                    elif cmd == '4':
                        print("Chuyển sang mode 4 (khác)")
                        mode_4_khac()
                        return
                    else:
                        command_list.append(cmd)

                    # Lưu lệnh điều khiển
                    
                    
                except Exception as e:
                    print("Lỗi decode lệnh:", cmd, e)
                    continue
        
def mode_1_control():
    display.show_emotion("NEUTRAL")
    asyncio.run(audio.play_wav("MODE1.wav"))
    print("[MODE 1] Điều khiển trực tiếp")
    while True:
        peer, msg = esp.recv()
        if msg:
            try:
                cmd = msg.decode()

                # Ưu tiên xử lý lệnh điều khiển trước
                if cmd in ['f', 'b', 'l', 'r', 's']:
                    print("Điều khiển robot với lệnh:", cmd)
                    robot.control(cmd)
                    continue  # quay lại vòng lặp, không kiểm tra lệnh chuyển mode nữa

                if cmd == '0':
                    print("Chuyển sang mode 0 (lập trình)")
                    mode_0_program()
                elif cmd == '1':
                    continue
                elif cmd == '2':
                    print("Chuyển sang mode 2 (học)")
                    mode_2_learn()
                    return
                elif cmd == '3':
                    print("Chuyển sang mode 3 (AI)")
                    mode_3_ai()
                    return
                elif cmd == '4':
                    print("Chuyển sang mode 4 (khác)")
                    mode_4_khac()
                    return
            except Exception as e:
                print("Lỗi decode file id học:", msg, e)

def mode_2_learn():
    display.show_emotion("NEUTRAL")
    asyncio.run(audio.play_wav("MODE2.wav"))
    print("[MODE 2] Chế độ học")
    while True:
        peer, msg = esp.recv()
        if msg:
            try:
                cmd = msg.decode()

                if cmd == '0':
                    print("Chuyển sang mode 0 (lập trình)")
                    mode_0_program()
                elif cmd == '1':
                    print("Chuyển sang mode 1 (điều khiển)")
                    mode_1_control()
                    return  # dừng mode 0 sau khi chuyển
                elif cmd == '2':
                    continue
                elif cmd == '3':
                    print("Chuyển sang mode 3 (AI)")
                    mode_3_ai()
                    return
                elif cmd == '4':
                    print("Chuyển sang mode 4 (khác)")
                    mode_4_khac()
                    return
                # Nếu không phải lệnh chuyển mode, xử lý học âm thanh
                print("Phát âm thanh với ID:", cmd)
                if cmd[0] == '9':
                    display.show_emotion(cmd)
                    asyncio.run(robot.learn(cmd))
                else:
                    asyncio.run(robot.learn(cmd))

            
            except Exception as e:
                print("Lỗi decode file id học:", msg, e)


def mode_3_ai():
    display.show_emotion("NEUTRAL")
    asyncio.run(audio.play_wav("MODE3.wav"))
    print("[MODE 3] Chế độ AI")
    app.connect()
    time.sleep(1)

    while True:
        print('ok')
        try:
            # Kiểm tra ESP có sẵn dữ liệu không (timeout 0.1 giây)
            r, _, _ = select.select([esp], [], [], 0.1)

            if r:
                peer, msg = esp.recv()
                print("[DEBUG] Nhận từ esp:", msg)

                if msg:
                    cmd = msg.decode()
                    if cmd == '0':
                        print("Chuyển sang mode 0 (lập trình)")
                        mode_0_program()
                        return
                    elif cmd == '1':
                        print("Chuyển sang mode 1 (điều khiển)")
                        mode_1_control()
                        return
                    elif cmd == '2':
                        print("Chuyển sang mode 2 (học)")
                        mode_2_learn()
                        return
                    elif cmd == '3':
                        continue
                        
                    elif cmd == '4':
                        print("Chuyển sang mode 4 (khác)")
                        mode_4_khac()
                        return
            else:
                # Không có dữ liệu từ ESP => gọi phát âm thanh
                app.stream_audio_from_web()

        except Exception as e:
            print("[ERROR] Trong vòng lặp mode 3:", e)

        time.sleep(0.1)


def mode_4_khac():
    display.show_emotion("NEUTRAL")
    print("[MODE 4] Chế độ khác")
    asyncio.run(audio.play_wav("MODE4.wav"))
    while True:
        peer, msg = esp.recv()
        if msg:
            try:
                cmd = msg.decode()
                if cmd == '0':
                    print("Chuyển sang mode 0 (lập trình)")
                    mode_0_program()
                elif cmd == '1':
                    print("Chuyển sang mode 1 (điều khiển)")
                    mode_1_control()
                    return  # dừng mode 0 sau khi chuyển
                elif cmd == '2':
                    print("Chuyển sang mode 2 (học)")
                    mode_2_learn()
                    return
                elif cmd == '3':
                    print("Chuyển sang mode 3 (AI)")
                    mode_3_ai()
                    return
                elif cmd == '4':
                    continue
                if cmd == 'LINE':
                    print("Chế độ theo dõi vạch")
                    asyncio.run(robot.follow_line())

                elif cmd == 'AVOID':
                    print("Chế độ tránh vật cản")
                    while True:
                        if vatcan.detect():
                            robot.avoid()

                elif cmd == 'DANCE':
                    print("Chế độ nhảy múa")
                    asyncio.run(robot.dance_async())
                    
            except Exception as e:
                print("Lỗi decode lệnh:", cmd, e)
        time.sleep(0.1)


adc = ADC(Pin(8))               # Dùng chân GPIO 34 (hoặc chân ADC bất kỳ)
adc.atten(ADC.ATTN_11DB)         # Cho phép đo lên đến ~3.3V
adc.width(ADC.WIDTH_12BIT)      # Độ phân giải 12 bit (0-4095)
raw = adc.read()  # Giá trị ADC từ 0–4095
print(raw)
if raw < 3800:
    asyncio.run(audio.play_wav("LOWBAT.wav"))

while raw < 3800:
    display.show_emotion("LOWBAT")
    raw = adc.read()  # Giá trị ADC từ 0–4095
display.show_emotion("NEUTRAL")
asyncio.run(audio.play_wav("POWERUP.wav"))
# === MAIN LOOP ===
while True:
    print("Waiting for mode...") 
    try:
        peer, msg = esp.recv(0)  # sẽ ném exception nếu không có dữ liệu
        if msg:
            cmd = msg.decode() if isinstance(msg, bytes) else msg

            if cmd == '0':
                mode_0_program()
            elif cmd == '1':
                mode_1_control()
            elif cmd == '2':
                mode_2_learn()
            elif cmd == '3':
                mode_3_ai()
            elif cmd == '4':
                mode_4_khac()
            else:
                print("Lệnh không hợp lệ, bỏ qua:", cmd)

    except OSError:
        pass  # không có dữ liệu thì không làm gì cả

    # Không cần time.sleep nếu hệ thống ổn định, nhưng nên có để tránh 100% CPU
    time.sleep(0.05)