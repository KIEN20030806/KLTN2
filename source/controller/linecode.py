from machine import ADC, Pin
import time

class LineCodeScanner:
    def __init__(self):
        # Chỉnh sửa chân ADC tùy bo mạch (ESP8266 chỉ có 1 ADC - pin A0)
        self.sensor_pins = [4, 5, 6, 7, 15, 8, 3, 9]  # ESP32 ADC pins
        self.sensors = [ADC(Pin(pin)) for pin in self.sensor_pins]

        # Cấu hình ADC (ESP32)
        for adc in self.sensors:
            adc.atten(ADC.ATTN_11DB)        # Đọc từ 0 đến 3.3V
            adc.width(ADC.WIDTH_12BIT)      # Độ phân giải 12-bit: 0–4095

        self.thresholds = [1000] * 8  # Khởi tạo ngưỡng mặc định
        self.calibrate()              # Tự động hiệu chỉnh threshold

    def read_avg(self, samples=10):
        """
        Đọc trung bình nhiều lần từ 8 cảm biến line.
        Trả về list giá trị trung bình ADC.
        """
        avg_values = []
        for sensor in self.sensors:
            total = 0
            for _ in range(samples):
                total += sensor.read()
                time.sleep_ms(2)
            avg_values.append(total // samples)
        return avg_values

    def read_binary(self):
        """
        Chuyển giá trị ADC sang bit 0/1 dựa vào ngưỡng threshold đã calibrate
        """
        values = self.read_avg()
        return [0 if val > th else 1 for val, th in zip(values, self.thresholds)]

    def calibrate(self):
        """
        Đọc giá trị min và max trong 10 lần đọc từ toàn bộ 8 cảm biến.
        Dùng chênh lệch lớn nhất để quyết định ngưỡng chung cho tất cả cảm biến.
        """
        print("[CALIB] Đang calibrate cảm biến (theo toàn bộ cảm biến)...")
        global_min = 4095
        global_max = 0

        for _ in range(10):
            vals = self.read_avg(samples=3)
            local_min = min(vals)
            local_max = max(vals)

            if local_min < global_min:
                global_min = local_min
            if local_max > global_max:
                global_max = local_max

            time.sleep_ms(1)

        delta = global_max - global_min
        if delta >= 400:
            threshold = (global_min + global_max) // 2
        else:
            threshold = max(130, global_min - 200)

        # Gán cùng threshold cho tất cả cảm biến
        self.thresholds = [threshold] * 8

        print("[CALIB] Global min:", global_min)
        print("[CALIB] Global max:", global_max)
        print("[CALIB] Threshold áp dụng:", threshold)



    def decode(self, bits):
        binary = ''.join(str(b) for b in bits)
        command_map = {
            '00000000': '0',
            '00000001': '1',
            '00000010': '2',
            '00000011': '3',
            '00000100': '4',
            '00000101': 'XOA',
            '00000110': 'LINE',
            '00000111': 'AVOID',
            '00001000': 'DANCE',
            '00001001': '9LAUGH',
            '00001010': '9CRY',
            '00001011': '9WOW',
            '00001100': '9OHNO',
            '00001101': 'ABC',
            '00001110': 'BABYSHARK',
            '00001111': 'BANANA0',
            '00010000': 'CUUDEN',
            '00010001': 'DOG0',
            '00010010': 'DOG1',
            '00010011': 'MOTCONVIT',
            '00010100': 'POLICE1',
            '00010101': 'MONKEY0'
        }
        return command_map.get(binary, 'UNKNOWN')

    def decode_mode(self, bits):
        binary = ''.join(str(b) for b in bits)
        try:
            return int(binary, 2)
        except:
            return 0

    def decode_uid(self, bits):
        return ''.join(str(b) for b in bits)

    def check_mode_change(self):
        bits = self.read_binary()
        binary = ''.join(str(b) for b in bits)
        return binary == '11111111'


scanner = LineCodeScanner()
