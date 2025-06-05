import time
import math
import machine
from machine import SoftI2C
from micropython import const

PWR_MGMT_1   = const(0x6B)
SMPLRT_DIV   = const(0x19)
CONFIG       = const(0x1A)
GYRO_CONFIG  = const(0x1B)
ACCEL_CONFIG = const(0x1C)
INT_ENABLE   = const(0x38)
ACCEL_XOUT_H = const(0x3B)
ACCEL_YOUT_H = const(0x3D)
ACCEL_ZOUT_H = const(0x3F)
GYRO_XOUT_H  = const(0x43)
GYRO_YOUT_H  = const(0x45)
GYRO_ZOUT_H  = const(0x47)
TEMP_OUT_H   = const(0X41)

class MPU6050:
    def __init__(self, i2c, address=0x68):
        self._i2c = i2c
        self._addr = address

        #Close the sleep mode
        #Write to power management register to wake up mpu6050
        self.__register(PWR_MGMT_1, 0)

        #configurate the digital low pass filter
        self.__register(CONFIG, 1)

        
        #set the gyro scale to 500 deg/s: 250 deg/s (131) --> 0x00, 500 deg/s (65.5) --> 0x08, 1000 deg/s (32.8) --> 0x10, 2000 deg/s (16.4)--> 0x18
        self.__register(GYRO_CONFIG, 0x08)
        # self.scaleFactorGyro = 500.0 / 32768.0 #for 500 deg/s, check data sheet 65.536

        # #set the accelerometer scale to 4g: 2g (16384)--> 0x00, 4g (8192)--> 0x08, 8g (4096) --> 0x10, 16g (2048)--> 0x18
        self.__register(ACCEL_CONFIG, 0x08)
        # self.scaleFactorAccel = 4.0 / 32768.0 #for 4g, check data sheet

        #Set interrupt enable register to 0 .. disable interrupts
        #self.__register(INT_ENABLE, 0x00)

        self.__get_scale_range()

        self.gyroXoffs = self.gyroYoffs = self.gyroZoffs = 0

    def __get_scale_range(self):
        scale = 1
        
        #set the gyro scale to 500 deg/s: 250 deg/s (131) --> 0x00, 500 deg/s (65.5) --> 0x08, 1000 deg/s (32.8) --> 0x10, 2000 deg/s (16.4)--> 0x18
        x = self.__read_raw_data(GYRO_CONFIG, 1)
        if x == b'\x00':
            scale = 250
        elif x == b'\x08':
            scale = 500
        elif x == b'\x10':
            scale = 1000
        else:
            scale = 2000

        self.scaleFactorGyro = scale * 1.0 / 32768.0

        # #set the accelerometer scale to 4g: 2g (16384)--> 0x00, 4g (8192)--> 0x08, 8g (4096) --> 0x10, 16g (2048)--> 0x18
        x = self.__read_raw_data(ACCEL_CONFIG, 1)        
        if x == b'\x00':
            scale = 2
        elif x == b'\x08':
            scale = 4
        elif x == b'\x10':
            scale = 8
        else:
            scale = 16

        self.scaleFactorAccel = scale * 1.0 / 32768.0

    def __register(self, reg, data): #Write the registor of i2c device.
        self._i2c.start()
        self._i2c.writeto(self._addr, bytearray([reg, data]))
        self._i2c.stop()

    def __bytes_toint(self, firstbyte, secondbyte):
        if not firstbyte & 0x80:
            return firstbyte << 8 | secondbyte
        return - (((firstbyte ^ 255) << 8) | (secondbyte ^ 255) + 1)

    def __read_raw_data(self, addr, size):
        try:
            self._i2c.start()
            a = [0] * size
            a = self._i2c.readfrom_mem(self._addr, addr, size)
        finally:
            self._i2c.stop()
            return a

    def __get_raw_value(self, name=None):
        if name == None:
            raw_ints = self.__read_raw_data(ACCEL_XOUT_H, 14)
            vals = {}
            vals["AcX"] = self.__bytes_toint(raw_ints[0], raw_ints[1])
            vals["AcY"] = self.__bytes_toint(raw_ints[2], raw_ints[3])
            vals["AcZ"] = self.__bytes_toint(raw_ints[4], raw_ints[5])
            vals["Tmp"] = self.__bytes_toint(raw_ints[6], raw_ints[7]) / 340.00 + 36.53
            vals["GyX"] = self.__bytes_toint(raw_ints[8], raw_ints[9])
            vals["GyY"] = self.__bytes_toint(raw_ints[10], raw_ints[11])
            vals["GyZ"] = self.__bytes_toint(raw_ints[12], raw_ints[13])
            return vals

        a = [0,0]
        if (name == 'GyZ'):
            a = self.__read_raw_data(GYRO_ZOUT_H, 2)
        elif name == 'GyY':
            a = self.__read_raw_data(GYRO_YOUT_H, 2)
        elif name == 'GyX':
            a = self.__read_raw_data(GYRO_XOUT_H, 2)
        elif name == 'AcX':
            a = self.__read_raw_data(ACCEL_XOUT_H, 2)
        elif name == 'AcY':
            a = self.__read_raw_data(ACCEL_YOUT_H, 2)
        elif name == 'AcZ':
            a = self.__read_raw_data(ACCEL_ZOUT_H, 2)
        return self.__bytes_toint(a[0], a[1])
    
    def __get_value(self, name=None, n_samples=1, sleep=0):
        try:
            result = 0
            if name == None:
                vals = {}
                vals['AcX'] = vals['AcY'] = vals['AcZ'] = vals['GyX'] = vals['GyY'] = vals['GyZ'] = 0.0 
                for i in range(n_samples):
                    data = self.__get_raw_value()
                    vals['AcX'] += data['AcX'] * self.scaleFactorAccel / n_samples
                    vals['AcY'] += data['AcY'] * self.scaleFactorAccel / n_samples
                    vals['AcZ'] += data['AcZ'] * self.scaleFactorAccel / n_samples
                    vals['GyX'] += data['GyX'] * self.scaleFactorGyro / n_samples
                    vals['GyY'] += data['GyY'] * self.scaleFactorGyro / n_samples
                    vals['GyZ'] += data['GyZ'] * self.scaleFactorGyro / n_samples
                    if sleep:
                        time.sleep_ms(sleep)
                result = vals
            else:
                val = 0.0
                for i in range(n_samples):
                    val += self.__get_raw_value(name) / n_samples
                    if sleep:
                        time.sleep_ms(sleep)

                if name == 'AcX' or name == 'AcY' or name == 'AcZ':
                    val = val * self.scaleFactorAccel
                else:
                    val = val * self.scaleFactorGyro

                result = val
        finally:
            return result

    def begin(self):
        self.angleX = 0.0
        self.angleY = 0.0
        self.angleZ = 0.0
        self.update_time = time.time_ns()
    
    def calibrateZ(self, n_samples=2000): #calibrate for Z axis
        # print("Calib...") #TODO
        val = self.__get_raw_value('GyZ') * self.scaleFactorGyro
        self.gyroZoffs_min = self.gyroZoffs_max = val
        self.gyroZoffs = val
        Zoffs = val / n_samples
        for _ in range(n_samples - 1):
            val = self.__get_raw_value('GyZ') * self.scaleFactorGyro
            if self.gyroZoffs_min > val:
                self.gyroZoffs_min = val
            if self.gyroZoffs_max < val:
                self.gyroZoffs_max = val
            Zoffs += val / n_samples
        self.gyroZoffs = Zoffs
        # print(self.gyroZoffs)
        # print("...done") #TODO
        
    def updateZ(self):
        t_now = time.time_ns()
        gyrZ = self.__get_value('GyZ') - self.gyroZoffs
        deltaT = (t_now - self.update_time) * 1e-9
        self.update_time = t_now        
        self.angleZ += gyrZ * deltaT

    def calibrate(self, n_samples=1000, sleep=0): #calibrate for all axis
        data = self.__get_value(None, n_samples, sleep)
        self.acXoffs = data['AcX']
        self.acYoffs = data['AcY']
        self.acZoffs = data['AcZ']
        self.gyroXoffs = data['GyX']
        self.gyroYoffs = data['GyY']
        self.gyroZoffs = data['GyZ']

    def update(self):
        #The accelerometer data is reliable only on the long term, so a "low pass" filter has to be used.
        #The gyroscope data is reliable only on the short term, as it starts to drift on the long term.
        t_now = time.time_ns()
        data = self.__get_value()
        accX = data['AcX']
        accY = data['AcY']
        accZ = data['AcZ']
        gyrX = data['GyX'] - self.gyroXoffs
        gyrY = data['GyY'] - self.gyroYoffs
        gyrZ = data['GyZ'] - self.gyroZoffs

        ax = math.atan2(accX, math.sqrt( math.pow(accY, 2) + math.pow(accZ, 2) ) ) * 180 / 3.1415926
        ay = math.atan2(accY, math.sqrt( math.pow(accX, 2) + math.pow(accZ, 2) ) ) * 180 / 3.1415926
        
        deltaT = (t_now - self.update_time) * 1e-9
        self.update_time = t_now

        if accZ > 0:
          self.angleX -= gyrY * deltaT
          self.angleY += gyrX * deltaT
        else :
          self.angleX += gyrY * deltaT
          self.angleY -= gyrX * deltaT

        self.angleZ += gyrZ * deltaT

        # complementary filter
        # set 0.5sec = tau = deltaT * A / (1 - A)
        # so A = tau / (tau + deltaT)
        filter_coefficient = 0.5 / (0.5 + deltaT)
        self.angleX = self.angleX * filter_coefficient + ax * (1 - filter_coefficient)
        self.angleY = self.angleY * filter_coefficient + ay * (1 - filter_coefficient)

    def get_angleX(self):      
        return self.angleX

    def get_angleY(self):
        return self.angleY

    def get_angleZ(self, absolute=False): #by default angleZ returns value from 0 to 360 in anti-clockwise
        if absolute:
            return abs(self.angleZ)
        return self.angleZ
    
    def get_gyro_roll(self, n_samples=10):
        return round(self.__get_value('GyX', n_samples))

    def get_gyro_pitch(self, n_samples=10):
        return round(self.__get_value('GyY', n_samples))

    def get_gyro_yaw(self, n_samples=10):
        return round(self.__get_value('GyZ', n_samples))

    def get_accel(self, name, n_samples=10):
        if name == 'x':
            return self.get_accel_x(n_samples)
        if name == 'y':
            return self.get_accel_y(n_samples)
        return self.get_accel_z(n_samples)

    def get_accel_x(self, n_samples=10):        
        return max(min(100, round(self.__get_value('AcX', n_samples) * 100)), -100)

    def get_accel_y(self, n_samples=10):
        return max(min(100, round(self.__get_value('AcY', n_samples) * 100)), -100)

    def get_accel_z(self, n_samples=10):
        return max(min(100, round(self.__get_value('AcZ', n_samples) * 100 - 100)), -100)

    def get_accels(self, n_samples=1):
        data = self.__get_value(None, n_samples)
        return (data['AcX'], data['AcY'], data['AcZ'] - 1)

    def get_gyros(self, n_samples=1):
        data = self.__get_value(None, n_samples)
        return (data['GyX'] - self.gyroXoffs, data['GyY'] - self.gyroYoffs, data['GyZ'] - self.gyroZoffs)

    def reset_angle(self):
        self.begin()

    '''
        both_sign = True: Angle return will from -180 to 180
        both_sign = False: Angle return will be 0-360
    '''
    def get_angle(self, both_sign=True):
        pass

    def wait_angle(self, wait_angle):
        start_angle = self.get_angle(False)
        time_start = time.ticks_ms()
        
        while True:
            current_angle = self.get_angle(False)
            distance = current_angle - start_angle
            pprint(current_angle, distance)
            if wait_angle > 0:
                if distance > wait_angle:
                    return
            else:
                if distance < wait_angle:
                    return
                '''
                if angle < 1 or angle > 355:
                    #time.sleep_ms(10)
                    continue
                else:
                    angle = 360-angle
                    if angle > abs(wait_angle):
                        return
                    else:
                        #time.sleep_ms(10)
                        continue
                '''
            if time.ticks_ms() - time_start > 2500:
                print('Wait angle timeout')
                return

mpu = MPU6050(SoftI2C(scl=machine.Pin(47), sda=machine.Pin(21), freq=100000))