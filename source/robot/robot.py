import machine
import time
from machine import PWM, Pin, ADC
from mpu6050 import mpu
from rfid import rfid
import uasyncio as asyncio

DISTANCE = 15

def wait_for(condition):
    while not condition():
        time.sleep_ms(50)
    return


def translate(value, left_min, left_max, right_min, right_max):
    # Figure out how 'wide' each range is
    left_span = left_max - left_min
    right_span = right_max - right_min
    # Convert the left range into a 0-1 range (float)
    value_scaled = float(value - left_min) / float(left_span)
    # Convert the 0-1 range into a value in the right range.
    return round(right_min + value_scaled * right_span)


class Robot:
    def __init__(self, audio, display):
        self.audio = audio
        self.display = display
        self.ina1 = PWM(Pin(12), freq=1500, duty=0)
        self.ina2 = PWM(Pin(11), freq=1500, duty=0)
        self.inb1 = PWM(Pin(14), freq=1500, duty=0)
        self.inb2 = PWM(Pin(13), freq=1500, duty=0)

        # parameters for precise moving
        self.fw_speed = 90  # move forward speed (80)
        self.fw_speed_start = self.fw_speed/4  # move forward speed
        self.fw_step_time = 1.47
        # speed adjustment rate for 2 wheels when moving straight forward
        self.fw_adjust_rate = 20
        self.min_speed = 60
        self.start_position = 0

        self.turn_speed_start = 90  # 80 # turn speed for turning right or left when start
        self.turn_speed_end = 60  # 60 # turn speed for turning right or left when near ending
        self.turn_angle_buffer = 5  # 5 # angle buffer to stop before limit when turn

        self.acc_angle_error = 0  # accumulated angle error while moving to adjust in next move

        self.line_left_adc = ADC(Pin(10))
        self.line_right_adc = ADC(Pin(7))
        self.line_left_adc.atten(ADC.ATTN_11DB)   # mở rộng dải đo (tùy theo phần cứng)
        self.line_right_adc.atten(ADC.ATTN_11DB)
        
        # Ngưỡng để phân biệt line hay không (bạn điều chỉnh phù hợp)
        self.line_thresholdl = 2000
        self.line_thresholdr = 800

        # Cảm biến vật cản analog trên IO9
        self.obstacle_sensor = ADC(Pin(9))
        self.obstacle_sensor.atten(ADC.ATTN_11DB)
        self.obstacle_threshold = 2000  # Ngưỡng vật cản, bạn điều chỉnh
        time.sleep(0.2)
        self.set_wheel_speed(0, 0)

    def set_wheel_speed(self, m1, m2, t=None):
        LEFT_WHEEL_COMPENSATION = 0.97
        RIGHT_WHEEL_COMPENSATION = 1.00

        m1 *= LEFT_WHEEL_COMPENSATION
        m2 *= RIGHT_WHEEL_COMPENSATION

        m1 = max(min(100, m1), -100)
        m2 = max(min(100, m2), -100)

        m1_adjusted = int(translate(abs(m1), 0, 100, 0, 1023))
        m2_adjusted = int(translate(abs(m2), 0, 100, 0, 1023))

        ina1 = ina2 = inb1 = inb2 = 0

        if m1 > 0:
            ina1 = m1_adjusted
            ina2 = 0
        elif m1 < 0:
            ina1 = 0
            ina2 = m1_adjusted
        else:
            ina1 = 0
            ina2 = 0

        if m2 > 0:
            inb1 = m2_adjusted
            inb2 = 0
        elif m2 < 0:
            inb1 = 0
            inb2 = m2_adjusted
        else:
            inb1 = 0
            inb2 = 0

        self.ina1.duty(ina1)
        self.ina2.duty(ina2)
        self.inb2.duty(inb2)
        self.inb1.duty(inb1)

        if t is not None:
            time.sleep(t)
            self.ina1.duty(0)
            self.ina2.duty(0)
            self.inb2.duty(0)
            self.inb1.duty(0)
            time.sleep_ms(50)

            
    def sign(self, x):
        return 3 if x > 0 else -3 if x < 0 else 0

    #------------------------------ROBOT PRIVATE MOVING METHODS--------------------------#
    def _calibrate_speed(self, speed):
        angle_error_min = 0.2
        angle_error_max = 10

        m1_speed = speed
        m2_speed = speed

        mpu.updateZ()
        z = mpu.get_angleZ()

        if abs(z) >= 360:
            z = (abs(z) - 360) * z / abs(z)
        if abs(z) > 180:
            z = z - 360 * z / abs(z)

        if abs(z) > angle_error_max:
            return

        if abs(z) > angle_error_min:
            self.set_wheel_speed(round(m1_speed - z * self.fw_adjust_rate), round(m2_speed + z * self.fw_adjust_rate))
            # print('Driving', z, z * self.fw_adjust_rate, round(m1_speed + z *self.fw_adjust_rate), round(m2_speed - z * self.fw_adjust_rate))
        else:
            self.set_wheel_speed(m1_speed, m2_speed)
            # print('Default', z, m1_speed, m2_speed)

        return

    def _go_straight(self, speed, t):
        t0 = 0

        try:
            time.sleep_ms(20)
            mpu.calibrateZ()
            mpu.begin()

            mpu.updateZ()
            self.start_position = mpu.get_angleZ()

            t0 = time.time_ns()
            # Start slowly
            if speed > 0:
                self.set_wheel_speed(self.fw_speed_start, self.fw_speed_start)
            else:
                self.set_wheel_speed(-self.fw_speed_start, -self.fw_speed_start)

            while time.time_ns() - t0 < t * 1e9:
                elapsed = time.time_ns() - t0
                remaining_ratio = (t * 1e9 - elapsed) / (t * 1e9)

                if remaining_ratio < 0.4:
                    # Giảm dần từ speed về 0 khi còn 30% thời gian
                    ratio = remaining_ratio / 0.3  # từ 1 xuống 0
                    dynamic_speed = int(speed * ratio)
                else:
                    dynamic_speed = speed

                self._calibrate_speed(dynamic_speed)
                time.sleep_ms(5)
        except Exception as err:
            print(err)

        finally:
            time.sleep_ms(20)
            print('Stop')
            self.stop()
            time.sleep_ms(20)
            self.set_wheel_speed(0, 0)


    def _turn_angle(self, angle):

        self.brake()

        time.sleep_ms(20)
        mpu.calibrateZ()
        mpu.begin()
        time.sleep_ms(50)

        if angle > 0:
            speed_factor = 1
            end_angle = abs(angle) - self.turn_angle_buffer - \
                self.acc_angle_error
        else:
            speed_factor = -1
            end_angle = abs(angle) - self.turn_angle_buffer + \
                self.acc_angle_error

        time_start = time.ticks_ms()
        last_time = time_start
        # print('Start: ', start_angle, 'End: ', end_angle)
        self.set_wheel_speed(-speed_factor*self.turn_speed_start, speed_factor*self.turn_speed_start)

        while True:
            now = time.ticks_ms()
            mpu.updateZ()
            current_angle = mpu.get_angleZ()
            distance = int(abs(current_angle))

            # print(current_angle, distance, now - last_time)
            if distance <= end_angle - 20:
                self.set_wheel_speed(-speed_factor * self.turn_speed_end, speed_factor * self.turn_speed_end)
            if distance <= end_angle - 10:
                self.set_wheel_speed(-speed_factor * (self.turn_speed_end // 1.5), speed_factor * (self.turn_speed_end // 1.5))
            if distance <= end_angle - 1:
                self.set_wheel_speed(-speed_factor * (self.turn_speed_end // 2), speed_factor * (self.turn_speed_end // 3))

            if distance >= end_angle:
                # print('Turn stop: ', current_angle, distance, now - last_time)
                break

            if now - time_start > 6000:
                print('Turn timeout')
                self.stop()
                # flash LED to notify error to user

                break
            last_time = now
        self.brake()
        time.sleep_ms(50)
        self.acc_angle_error += 0  # current_angle - angle
        # print('Turn error: ', current_angle - angle, 'acc: ', self.acc_angle_error)

    #------------------------------ROBOT PUBLIC DRIVING METHODS--------------------------#

    def forward(self, steps=1):
        if steps == None:
            self.set_wheel_speed(80, 80)
        else:
            self._go_straight(self.fw_speed, self.fw_step_time*steps)

    def backward(self, steps=1):
        if steps == None:
            self.set_wheel_speed(-80, -80)
        else:
            self._go_straight(-self.fw_speed, self.fw_step_time*steps)

    def turn_left(self, angle=-92):
        if angle == None:
            self.set_wheel_speed(50, -50)
        else:
            self._turn_angle(angle)

    def turn_right(self, angle=92):
        if angle == None:
            self.set_wheel_speed(-50, 50)
        else:
            self._turn_angle(angle)

    def brake(self):
        self.ina1.duty(1023)
        self.ina2.duty(1023)
        self.inb2.duty(1023)
        self.inb1.duty(1023)
        time.sleep_ms(100)

    def stop(self):
        self.brake()
        time.sleep_ms(50)

    def reset_acc_err(self):
        self.acc_angle_error = 0    
    
    def move(self, cmd):
        if cmd == 'f':
            self.forward()
        elif cmd == 'b':
            self.backward()
        elif cmd == 'l':
            self.turn_left()
        elif cmd == 'r':
            self.turn_right()
        else:
            print("Invalid command:", cmd)


    #------------------------------- Supported moving for dance ----------------#
    def turn_round(self, speed):
        self.set_wheel_speed(-speed, speed)
        time.sleep_ms(150)
        mpu.flush()
        while True:
            current_angle = abs(mpu.get_angle(False))
            if (speed > 0 and current_angle > 340) or (speed < 0 and current_angle < 25):
                # print('Turn stop: ', current_angle)
                break

        self.brake()

    def reset_turn(self):
        start_angle = mpu.get_angle()

        if start_angle > 0:
            speed_factor = 1
        else:
            speed_factor = -1

        self.set_wheel_speed(
            speed_factor*self.turn_speed_end, -speed_factor*self.turn_speed_end)
        mpu.flush()
        while True:
            current_angle = mpu.get_angle()
            # print(current_angle)
            if speed_factor*5 > speed_factor*current_angle:
                # print('Turn stop: ', current_angle)
                break

        self.brake()

    def go_straight(self, speed):
        self.set_wheel_speed(speed, speed)

    def left(self, speed):
        self.set_wheel_speed(speed, -speed)

    def right(self, speed):
        self.set_wheel_speed(-speed, speed)

    def control(self, action):
        self.last_cmd_time = time.ticks_ms()
        self.last_action = action

        if action == 'f':
            self.go_straight(100)
        elif action == 'b':
            self.go_straight(-100)
        elif action == 'l':
            self.left(80)
        elif action == 'r':
            self.right(80)
        elif action == 's':
            self.stop()
        else:
            print("Lệnh không hợp lệ:", action)
        time.sleep_ms(10)
        
    
    async def follow_line(self):
        eye_task = asyncio.create_task(self.display.show_emotion("NEUTRAL", loop=True))
        while True:  
            left_val = self.line_left_adc.read()
            right_val = self.line_right_adc.read()
            obstacle_val = self.obstacle_sensor.read()
            left_on_line = left_val < self.line_thresholdl
            right_on_line = right_val < self.line_thresholdr
            if obstacle_val < self.obstacle_threshold:
                print("Vật cản gần! Kết thúc chế độ dò line")
                self.stop()
                break
            uid = rfid.scan_card()
            if uid:
                uid_wav = rfid.uid_wav(uid)
                print(f"Phát âm thanh cho UID: {uid_wav}")
                self.stop()
                await asyncio.sleep(0.05)
                await self.audio.play_wav(uid_wav)
                self.set_wheel_speed(0, 0)

            if left_on_line and right_on_line:
                self.set_wheel_speed(35, 35)
            elif not left_on_line and right_on_line:
                self.set_wheel_speed(20, 80)
            elif left_on_line and not right_on_line:
                self.set_wheel_speed(80, 20)
            await asyncio.sleep(0.05)  # dùng await cho async loop



    async def avoid(self):
        eye_task = asyncio.create_task(self.display.show_emotion("NEUTRAL", loop=True))
        while True:
            obstacle_val = self.obstacle_sensor.read()
            print("Cảm biến vật cản:", obstacle_val)
            threshold = self.obstacle_threshold

            if obstacle_val < threshold:
                # Vật cản gần - né sang trái
                print("Vật cản gần! Né trái")
                self.set_wheel_speed(-100, 100)  # Quay trái
                await asyncio.sleep(0) 
            else:
                # Đường trống - đi thẳng
                self.set_wheel_speed(70, 70)

            await asyncio.sleep(0) 
            
    async def dance_async(self):
        print("Bắt đầu chế độ nhảy múa")
        eye_task = asyncio.create_task(self.display.show_emotion("NEUTRAL", loop=True))
        await asyncio.sleep(0)  # nhường CPU

        # Chạy nhạc và nhảy cùng lúc
        await asyncio.gather(
            self.audio.play_wav("BABYSHARK.wav"),
            self.dance_loop()
        )

        print("Kết thúc nhảy múa")

    async def dance_loop(self):
        while self.audio._playing:  # hoặc: while audio.is_playing():
            await self.dance_moves()


    async def dance_moves(self):
        print("Bắt đầu chế độ nhảy múa")
        self.go_straight(100)
        await asyncio.sleep(0.5)
        self.go_straight(-100)
        await asyncio.sleep(0.5)
        self.left(100)
        await asyncio.sleep(0.5)
        self.right(100)
        await asyncio.sleep(0.5)
        self.go_straight(100)
        await asyncio.sleep(0.5)
        self.go_straight(-100)
        await asyncio.sleep(0.5)
        self.right(100)
        await asyncio.sleep(0.5)
        self.left(100)
        await asyncio.sleep(2)
        self.stop()
        print("Kết thúc nhảy múa")
        
    async def learn(self, role):
        if role[0] == '9':
            eye_task = asyncio.create_task(self.display.show_emotion(f"{role[1:]}", loop=True))
            role = role[1:]
        else:
            eye_task = asyncio.create_task(self.display.show_emotion("NEUTRAL", loop=True))
        play_task = asyncio.create_task(self.audio.play_wav(f"{role}.wav"))
        while not play_task.done():  # Chạy line khi âm thanh đang phát
            left_val = self.line_left_adc.read()
            right_val = self.line_right_adc.read()    
            left_on_line = left_val < self.line_thresholdl
            right_on_line = right_val < self.line_thresholdr

            if left_on_line and right_on_line:
                self.set_wheel_speed(35,35)
            elif not left_on_line and right_on_line:
                self.set_wheel_speed(20, 80)
            elif left_on_line and not right_on_line:
                self.set_wheel_speed(80, 20)
            await asyncio.sleep(0.05)  # dùng await cho async loop

        # Khi âm thanh phát xong:
        self.set_wheel_speed(0, 0)  # Dừng robot

