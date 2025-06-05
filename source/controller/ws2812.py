# ws2812.py
import neopixel
from machine import Pin
import time

class LEDRing:
    def __init__(self, pin=10, num_leds=16):
        """
        Khởi tạo vòng LED WS2812.
        :param pin: GPIO kết nối tín hiệu DIN của LED
        :param num_leds: số lượng LED trong vòng
        """
        self.num_leds = num_leds
        self.pin = Pin(pin, Pin.OUT)
        self.ring = neopixel.NeoPixel(self.pin, self.num_leds)
        self.clear()

    def clear(self):
        for i in range(self.num_leds):
            self.ring[i] = (0, 0, 0)
        self.ring.write()

    def fill(self, color):
        for i in range(self.num_leds):
            self.ring[i] = color
        self.ring.write()

    def set_color(self, index, color):
        if 0 <= index < self.num_leds:
            self.ring[index] = color
            self.ring.write()



    def show_pattern(self, pattern, delay=100):
        """
        Hiển thị một mẫu list màu (list các tuple RGB).
        8 LED đầu hiển thị theo thứ tự, 6 LED cuối đảo ngược.
        Tự động bù màu đen nếu pattern thiếu phần tử.
        """
        self.fill((0, 0, 0))

        for i in range(self.num_leds):
            if i < 8:
                # LED bình thường
                if i < len(pattern):
                    self.ring[i] = pattern[i]
                else:
                    self.ring[i] = (0, 0, 0)
            else:
                # LED bị đảo ngược
                reverse_index = 13 - (i - 8)
                if reverse_index < len(pattern):
                    self.ring[i] = pattern[reverse_index]
                else:
                    self.ring[i] = (0, 0, 0)

        self.ring.write()
        time.sleep_ms(delay)


    def wheel(self, pos):
        """Chuyển đổi giá trị 0-255 thành màu RGB với độ sáng tối đa ~40"""
        brightness = 0.156  # tương đương 40/255
        if pos < 85:
            r = int(pos * 3 * brightness)
            g = int((255 - pos * 3) * brightness)
            b = 0
        elif pos < 170:
            pos -= 85
            r = int((255 - pos * 3) * brightness)
            g = 0
            b = int(pos * 3 * brightness)
        else:
            pos -= 170
            r = 0
            g = int(pos * 3 * brightness)
            b = int((255 - pos * 3) * brightness)
        return (r, g, b)


    def rainbow_cycle(self, delay=50):
        self.clear()
        for i in range(self.num_leds):
            color = self.wheel((i * 256 // self.num_leds) & 255)

            if i < 8:
                # 8 LED đầu giữ nguyên
                self.ring[i] = color
            else:
                # 6 LED cuối đảo ngược thứ tự
                # LED 8 => ring[13], LED 9 => ring[12], ..., LED 13 => ring[8]
                self.ring[13 - (i - 8)] = color

            self.ring.write()
            time.sleep_ms(delay)

        time.sleep_ms(500)  # giữ nguyên trạng thái sáng một lúc
        self.clear()
      

leds = LEDRing(pin=16, num_leds= 14)