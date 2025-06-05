import network, time, ujson
import espnow
import urequests
from machine import I2S, Pin, reset

class WiFiSlave:
    def __init__(self, cred_file="wifi_slave.json", controller_mac=b'\xcc\xba\x97\n\x8ap'):
        self.cred_file = cred_file
        self.controller_mac = controller_mac
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)

        self.e = espnow.ESPNow()
        self.e.active(True)
        self.e.add_peer(controller_mac)

        # Setup I2S (chuẩn bị sẵn)
        self.audio_out = I2S(
            1, sck=Pin(33), ws=Pin(25), sd=Pin(26),
            mode=I2S.TX, bits=16, format=I2S.MONO,
            rate=16000, ibuf=4096
        )

        # Địa chỉ server (nên để static hoặc nhận từ ESP chủ)
        self.server_ip = "192.168.1.6"
        self.server_port = 8000

        print("🟢 Đang chờ nhận dữ liệu config qua ESP-NOW...")

    def get_url(self, path):
        return f"http://{self.server_ip}:{self.server_port}/{path}"

    def connect_wifi(self, ssid, password):
        self.wlan.disconnect()
        self.wlan.connect(ssid, password)
        print(f"📡 ESP phụ kết nối WiFi {ssid}...")
        for _ in range(15):
            if self.wlan.isconnected():
                print("✅ ESP phụ kết nối thành công:", self.wlan.ifconfig())
                return True
            time.sleep(1)
        print("❌ ESP phụ kết nối thất bại.")
        return False

    def save_config(self, creds):
        with open(self.cred_file, "w") as f:
            f.write(ujson.dumps(creds))

    def check_ready(self):
        try:
            response = urequests.get(self.get_url("get_ready"))
            if response.status_code == 200:
                data = response.json()
                return data.get('ready', 0)
            return 0
        except Exception as e:
            print(f"❌ ESP2: Lỗi khi kiểm tra ready: {e}")
            return 0

    def receive_and_play_audio(self):
        print("📥 ESP2: Đang tải âm thanh...")
        try:
            response = urequests.get(self.get_url("receive_audio"), stream=True)
            while True:
                chunk = response.raw.read(1024)
                if not chunk:
                    break
                self.audio_out.write(chunk)
            response.close()
            print("✅ ESP2: Phát âm thanh hoàn tất!")
        except Exception as e:
            print(f"❌ ESP2: Lỗi khi tải/phát âm thanh: {e}")

    def run_main_loop(self):
        print("🔁 Bắt đầu vòng lặp chính...")
        while True:
            if self.check_ready():
                self.receive_and_play_audio()
            time.sleep(1)

    def listen_for_config(self):
        while True:
            host, msg = self.e.recv()
            if msg:
                try:
                    data = ujson.loads(msg.decode())
                    print("🔵 Nhận config từ ESP chủ:", data)
                    ssid = data.get("ssid")
                    password = data.get("password")

                    self.save_config({
                        "ssid": ssid,
                        "password": password,
                    })

                    if self.connect_wifi(ssid, password):
                        print("🌐 Kết nối WiFi thành công, bắt đầu xử lý âm thanh")
                        self.e.send(self.controller_mac, b"ACK")
                        self.run_main_loop()
                    else:
                        print("⚠️ Kết nối WiFi ESP phụ thất bại, sẽ thử lại...")

                except Exception as err:
                    print("❌ Lỗi khi xử lý dữ liệu nhận được:", err)

            time.sleep(1)

# --- Chạy chương trình ---
slave = WiFiSlave()
slave.listen_for_config()
