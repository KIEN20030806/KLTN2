import network, socket, time, ujson, os
from machine import Pin, I2S, reset
import urequests

class ESP32AudioPlayer:
    def __init__(self):
        self.CRED_FILE = "wifi.json"
        self.SSID_AP = "ESP32_Config"
        self.STATE = "CONFIG"

        self.SERVER_IP = "192.168.1.100"  # Địa chỉ web server
        self.SERVER_PORT = 8000

        # I2S Output (Speaker)
        self.SAMPLE_RATE = 8000
        self.BUFFER_SIZE = 4096
        self.SPK_BCK = Pin(2)
        self.SPK_WS = Pin(1)
        self.SPK_SD = Pin(43)
        self.audio_out = I2S(
            0, sck=self.SPK_BCK, ws=self.SPK_WS, sd=self.SPK_SD,
            mode=I2S.TX, bits=16, format=I2S.MONO,
            rate=self.SAMPLE_RATE, ibuf=self.BUFFER_SIZE
        )

        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)

    def url_decode(self, s):
        s = s.replace('+', ' ')
        res = ''
        i = 0
        while i < len(s):
            if s[i] == '%' and i + 2 < len(s):
                try:
                    res += chr(int(s[i+1:i+3], 16))
                    i += 3
                except:
                    res += '%'
                    i += 1
            else:
                res += s[i]
                i += 1
        return res

    def start_ap_mode(self):
        ap = network.WLAN(network.AP_IF)
        ap.active(True)
        ap.config(essid=self.SSID_AP, authmode=network.AUTH_OPEN)
        print(f"📶 Đang phát WiFi: {self.SSID_AP}")
        self.start_config_server()

    def start_config_server(self):
        wlan_scan = network.WLAN(network.STA_IF)
        wlan_scan.active(True)
        networks = wlan_scan.scan()

        options = ""
        for net in networks:
            ssid = net[0].decode()
            options += f'<option value="{ssid}">{ssid}</option>'

        html_form = f"""
        <html><meta charset="UTF-8">
        <body><h2>WiFi Cấu hình</h2>
        <form action="/" method="post">
            SSID:
            <select name="ssid">{options}</select><br>
            Password: <input name="password"><br>
            <input type="submit" value="Kết nối">
        </form></body></html>
        """

        addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
        s = socket.socket()
        s.bind(addr)
        s.listen(1)
        print("🌐 Server cấu hình đang chạy trên http://192.168.4.1")

        while True:
            cl, addr = s.accept()
            data = cl.recv(1024).decode()
            if "POST" in data:
                try:
                    body = data.split("\r\n\r\n")[1]
                    params = {}
                    for pair in body.split("&"):
                        k, v = pair.split("=")
                        params[k] = v

                    ssid = self.url_decode(params.get("ssid", ""))
                    password = self.url_decode(params.get("password", ""))
                    creds = {"ssid": ssid, "password": password}
                    with open(self.CRED_FILE, "w") as f:
                        f.write(ujson.dumps(creds))

                    cl.send("HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n")
                    cl.send("<h3>✔️ Lưu thành công! Đang kết nối lại...</h3>")
                    cl.close()
                    time.sleep(2)
                    reset()
                except Exception as e:
                    cl.send("HTTP/1.1 500 Error\r\n\r\n")
                    cl.send(f"<h3>Lỗi: {str(e)}</h3>")
                    cl.close()
            else:
                cl.send("HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n")
                cl.send(html_form)
                cl.close()

    def connect_wifi_from_file(self):
        try:
            with open(self.CRED_FILE, "r") as f:
                creds = ujson.loads(f.read())
            ssid = creds["ssid"]
            password = creds["password"]

            self.wlan.connect(ssid, password)
            print(f"📡 Đang kết nối tới {ssid}...")
            for _ in range(15):
                if self.wlan.isconnected():
                    print("✅ Kết nối thành công:", self.wlan.ifconfig())
                    return True
                time.sleep(1)
            print("❌ Kết nối thất bại.")
            return False
        except:
            print("⚠️ Không tìm thấy file wifi.json")
            return False

    def stream_audio_from_web(self):
        url_check = f"http://{self.SERVER_IP}:{self.SERVER_PORT}/get_ready"
        url_audio = f"http://{self.SERVER_IP}:{self.SERVER_PORT}/get_audio_response"
        url_done = f"http://{self.SERVER_IP}:{self.SERVER_PORT}/end_audio"
        res = urequests.get(url_check)
        status = ujson.loads(res.text)
        res.close()
        if status.get("ready") == 1:
            print("🎵 Server sẵn sàng, tải âm thanh...")
            audio_res = urequests.get(url_audio, stream=True)
            while True:
                chunk = audio_res.raw.read(self.BUFFER_SIZE)
                if not chunk:
                    break
                self.audio_out.write(chunk)
            audio_res.close()
            print("🔊 Đã phát xong audio")
            return False
        else:
            print("🎵 Server không sẵn sàng")
            return False

    def connect(self):
        if self.CRED_FILE in os.listdir():
            if self.connect_wifi_from_file():
                self.STATE = "STREAM"
            else:
                self.STATE = "CONFIG"
        else:
            self.STATE = "CONFIG"
        if self.STATE == "CONFIG":
            self.start_ap_mode()

    def run(self):
        if self.STATE == "STREAM":
            self.stream_audio_from_web()

app = ESP32AudioPlayer()