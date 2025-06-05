import time
from machine import SoftI2C, Pin
import uasyncio as asyncio


class HT16K33(object):
    # *********** CONSTANTS **********

    HT16K33_GENERIC_DISPLAY_ON = 0x81
    HT16K33_GENERIC_DISPLAY_OFF = 0x80
    HT16K33_GENERIC_SYSTEM_ON = 0x21
    HT16K33_GENERIC_SYSTEM_OFF = 0x20
    HT16K33_GENERIC_DISPLAY_ADDRESS = 0x00
    HT16K33_GENERIC_CMD_BRIGHTNESS = 0xE0
    HT16K33_GENERIC_CMD_BLINK = 0x81

    # *********** PRIVATE PROPERTIES **********

    i2c = None
    address = 0
    brightness = 1
    flash_rate = 0

    # *********** CONSTRUCTOR **********

    def __init__(self, i2c, i2c_address):
        assert 0x00 <= i2c_address < 0x80, "ERROR - Invalid I2C address in HT16K33()"
        self.i2c = i2c
        self.address = i2c_address
        self.init_success = False
        self.power_on()

    # *********** PUBLIC METHODS **********

    def set_blink_rate(self, rate=0):
        """
        Set the display's flash rate.

        Only four values (in Hz) are permitted: 0, 2, 1, and 0,5.

        Args:
            rate (int): The chosen flash rate. Default: 0Hz (no flash).
        """
        assert rate in (
            0, 0.5, 1, 2), "ERROR - Invalid blink rate set in set_blink_rate()"
        self.blink_rate = rate & 0x03
        self._write_cmd(self.HT16K33_GENERIC_CMD_BLINK | rate << 1)

    def set_brightness(self, brightness=5):
        """
        Set the display's brightness (ie. duty cycle).

        Brightness values range from 0 (dim, but not off) to 15 (max. brightness).

        Args:
            brightness (int): The chosen flash rate. Default: 15 (100%).
        """
        if brightness < 0 or brightness > 15:
            brightness = 15
        self.brightness = brightness
        self._write_cmd(self.HT16K33_GENERIC_CMD_BRIGHTNESS | brightness)

    def draw(self):
        """
        Writes the current display buffer to the display itself.

        Call this method after updating the buffer to update
        the LED itself.
        """
        self._render()

    def update(self):
        """
        Alternative for draw() for backwards compatibility
        """
        self._render()

    def clear(self):
        """
        Clear the buffer.

        Returns:
            The instance (self)
        """
        for i in range(0, len(self.buffer)):
            self.buffer[i] = 0x00
        return self

    def power_on(self):
        """
        Power on the controller and display.
        """
        self._write_cmd(self.HT16K33_GENERIC_SYSTEM_ON)
        self._write_cmd(self.HT16K33_GENERIC_DISPLAY_ON)

    def power_off(self):
        """
        Power on the controller and display.
        """
        self._write_cmd(self.HT16K33_GENERIC_DISPLAY_OFF)
        self._write_cmd(self.HT16K33_GENERIC_SYSTEM_OFF)

    # ********** PRIVATE METHODS **********

    def _render(self):
        """
        Write the display buffer out to I2C
        """
        # print(self.init_success)
        # if not self.init_success:
        #    return

        buffer = bytearray(len(self.buffer) + 1)
        buffer[1:] = self.buffer
        buffer[0] = 0x00
        self.i2c.writeto(self.address, bytes(buffer))

    def _write_cmd(self, byte):
        """
        Writes a single command to the HT16K33. A private method.
        """
        # print(self.init_success)
        # if not self.init_success:
        #    return

        self.i2c.writeto(self.address, bytes([byte]))


class HT16K33Matrix_16x08(HT16K33):
    """
    Micro/Circuit Python class for the Adafruit 0.8-in 16x8 LED matrix FeatherWing.

    Usage: https://smittytone.net/docs/ht16k33_matrixfeatherwing.html

    Version:    3.4.0
    Bus:        I2C
    Author:     Tony Smith (@smittytone)
    License:    MIT
    Copyright:  2022
    """

    # *********** CONSTANTS **********

    CHARSET = [
        [0x00,0x00,0x3C,0x7E,0x7E,0x3C,0x00,0x00],  # 0 - 'Rest Position'
        [0x00,0x18,0x3C,0x3C,0x3C,0x3C,0x18,0x00],  # 1 - 'Blink 1'
        [0x00,0x10,0x38,0x38,0x38,0x38,0x10,0x00],  # 2 - 'Blink 2'
        [0x00,0x10,0x30,0x30,0x30,0x30,0x10,0x00],  # 3 - 'Blink 3'
        [0x00,0x10,0x30,0x30,0x30,0x30,0x10,0x00],  # 4 - 'Blink 4'
        [0x00,0x00,0x3C,0x7E,0x7E,0x3C,0x00,0x00],   # 5
        b"\x00",  # 6
        b"\x00\x00\x7E\x81\x81\x99\x99\x7E",  # 7 - 'Right 2'
        b"\x00\x7E\x99\x99\x81\x81\x7E\x00",  # 8 - 'Left 1'
        b"\x7E\x99\x99\x81\x81\x7E\x00\x00",  # 9 - 'Left 2'

        b"\x00\x3E\x7E\x60\x60\x7E\x3E\x00",  # 10 - Surprised

        b"\x00\x7E\x81\x99\x99\x81\x7E\x00",  # 11 - 'Up 1'
        b"\x00\x7E\x81\xB1\xB1\x81\x7E\x00",  # 12 - 'Up 2'
        b"\x00\x7C\x82\xE2\xE2\x82\x7C\x00",  # 13 - 'Up 3'
        b"\x00\x7E\x81\x99\x99\x81\x7E\x00",  # 14 - 'Down 1'
        b"\x00\x7E\x81\x8D\x8D\x81\x7E\x00",  # 15 - 'Down 2'
        b"\x00\x3E\x41\x47\x47\x41\x3E\x00",  # 16 - 'Down 3'

        b"\x00\x7C\x82\xB1\xB1\x81\x7E\x00",  # 17 - 'Angry L 1'
        b"\x00\x78\x84\xB2\xB1\x81\x7E\x00",  # 18 - 'Angry L 2'
        b"\x00\x70\x88\xA4\xB2\x81\x7E\x00",  # 19 - 'Angry L 3'
        b"\x00\x60\x90\xA8\xB4\x82\x7F\x00",  # 20 - 'Angry L 4'
        b"\x00",  # 21
        b"\x00\x7E\x81\xB1\xB1\x82\x7C\x00",  # 22 - 'Angry R 1'
        b"\x00\x7E\x81\xB1\xB2\x84\x78\x00",  # 23 - 'Angry R 2'
        b"\x00\x7E\x81\xB2\xA4\x88\x70\x00",  # 24 - 'Angry R 3'
        b"\x00\x7F\x82\xB4\xA8\x90\x60\x00",  # 25 - 'Angry R 4'
        b"\x00",  # 26
        [0x08,0x1C,0x1C,0x3C,0x38,0x20,0x00, 0x00],  # 27 - 'Sad L 1'
        [0x00,0x00,0x20,0x38,0x3C,0x1C,0x1C,0x08],  # 28 - 'Sad L 2'
        [0x00,0x08,0x1C,0x1C,0x3C,0x38,0x20,0x00],  # 29 - 'Sad L 3'

        [0x00,0x20,0x38,0x3C,0x1C,0x1C,0x08,0x00],  # 30
        b"\x00",  # 31

        b"\x00\x3E\x41\x99\x99\x82\x7C\x00",  # 32 - 'Sad R 1'
        b"\x00\x1E\x21\x59\x9A\x84\x78\x00",  # 33 - 'Sad R 2'
        b"\x00\x1E\x21\x5A\x94\x88\x70\x00",  # 34 - 'Sad R 3'

        [0x00,0x0C,0x18,0x18,0x18,0x0C,0x0C,0x00],  # 35 - HAPPY L
        [0x00,0x00,0x0C,0x1C,0x18,0x18,0x0C,0x00],  # 36 - HAPPY R

        [0x00,0x00,0x18,0x38,0x30,0x30,0x18,0x00],  # 37 - 'Evil L 1'
        [0x00,0x18,0x30,0x30,0x38,0x18,0x00,0x00],  # 38 - 'Evil L 2'
        b"\x00\x7E\xC1\xB1\xB1\xC2\x7C\x00",  # 39 - 'Evil R 1'
        b"\x00\x60\x66\xB1\xB2\x68\x56\x00",  # 40 - 'Evil R 2'

        b"\x00\x00\x46\x4A\x52\x62\x00\x00",  # 41 - 'Sleepy'

        [0x00,0x00,0x18,0x24,0x24,0x18,0x00,0x00],  # 42 - wow1
        [0x00,0x3C,0x42,0x42,0x42,0x3C,0x00,0x00],  # 43 - wow2
        b"\x00\x60\x66\x72\x72\x66\x60\x00",  # 44 - 'Peering 1'

        b"\x00\x3E\x41\x5D\x55\x51\x1E\x00",  # 45 - 'Scared L'
        b"\x00\xFF\x81\xBD\xA5\xA1\xA1\xBF",  # 46 - 'Scared R'

        b"\x00\x00\x7e\x7e\x7e\x42\x42\x42",  # 47 - 'Low battery L'
        b"\x42\x42\x42\x42\x66\x3C\x00\x00",  # 48 - 'Low battery R'
    ]

    # eyes icon
    FRAME_TIME = 50
    EMOTIONS = {
        'LOWBAT': [
            None,
            (47, 48, FRAME_TIME*20),
            (0, 0, FRAME_TIME*10)
        ],
        'NEUTRAL': [
            None,
            (0, 0, FRAME_TIME),
            (1, 1, FRAME_TIME),
            (2, 2, FRAME_TIME),
            (3, 3, FRAME_TIME),
            (4, 4, FRAME_TIME),
            (5, 5, FRAME_TIME)
        ],
        '9LAUGH': [
            None,
            (36, 35 , 500),
            (38, 37 , 800),
        ],
        '9CRY': [
            None,
            (27, 28 , 500),
            (29, 30 , 500),
        ],
        '9OHNO': [
            None,
            (27, 28 , 500),
            (29, 30 , 500),
        ],
        '9WOW': [
            None,
            (42, 42 , 500),
            (43, 43 , 500),
        ],
        'WINK': [
            None,
            (0, 0, FRAME_TIME*20),
            (1, 0, FRAME_TIME),
            (2, 0, FRAME_TIME),
            (3, 0, FRAME_TIME),
            (4, 0, FRAME_TIME),
            (5, 0, FRAME_TIME),
        ]
    }

    # ********** PRIVATE PROPERTIES **********

    width = 16
    height = 8
    def_chars = None
    is_inverse = False

    # *********** CONSTRUCTOR **********

    def __init__(self, i2c):
        self.buffer = bytearray(self.width * 2)
        self.def_chars = []
        for i in range(32):
            self.def_chars.append(b"\x00")

        devices = i2c.scan()
        print("Thiết bị I2C tìm thấy:", devices)

        # HT16K33 thường nằm trong vùng từ 0x70 → 0x77
        for addr in range(0x70, 0x78):
            if addr in devices:
                i2c_address = addr
                break
        else:
            raise Exception("Không tìm thấy HT16K33! Địa chỉ tìm thấy: {}".format(devices))

        super(HT16K33Matrix_16x08, self).__init__(i2c, i2c_address)

        self.emotion = 'NEUTRAL'
        self.frame = None
        self.frame_index = 0
        self.last_frame_time = 0
        self.force_stop = False
        self.stop_animate = False

        self.clear().draw()

        self.set_emotion('NEUTRAL')

    # *********** PUBLIC METHODS **********

    def set_inverse(self):
        """
        Inverts the ink colour of the display

        Returns:
            The instance (self)
        """
        self.is_inverse = not self.is_inverse
        for i in range(self.width * 2):
            self.buffer[i] = (~ self.buffer[i]) & 0xFF
        return self

    def set_icon(self, glyph, column=0):
        """
        Present a user-defined character glyph at the specified digit.

        Glyph values are byte arrays of eight 8-bit values.
        This method updates the display buffer, but does not send the buffer to the display itself.
        Call 'draw()' to render the buffer on the display.

        Args:
            glyph (bytearray) The glyph pattern.
            column (int)      The column at which to write the icon. Default: 0

        Returns:
            The instance (self)
        """
        # Bail on incorrect row numbers or character values
        assert 0 < len(glyph) <= self.width * \
            2, "ERROR - Invalid glyph set in set_icon()"
        assert 0 <= column < self.width, "ERROR - Invalid column number set in set_icon()"

        for i in range(len(glyph)):
            buf_column = self._get_row(column + i)
            if buf_column is False:
                break
            self.buffer[buf_column] = glyph[i] if self.is_inverse is False else (
                (~ glyph[i]) & 0xFF)
        return self

    def set_character(self, ascii_value=32, column=0):
        """
        Display a single character specified by its Ascii value on the matrix.

        Args:
            ascii_value (int) Character Ascii code. Default: 32 (space)
            column (int)      Whether the icon should be displayed centred on the screen. Default: False

        Returns:
            The instance (self)
        """
        # Bail on incorrect row numbers or character values
        assert 0 <= ascii_value < 128, "ERROR - Invalid ascii code set in set_character()"
        assert 0 <= column < self.width, "ERROR - Invalid column number set in set_icon()"

        glyph = None
        if ascii_value < 32:
            # A user-definable character has been chosen
            glyph = self.def_chars[ascii_value]
        else:
            # A standard character has been chosen
            ascii_value -= 32
            if ascii_value < 0 or ascii_value >= len(self.CHARSET):
                ascii_value = 0
            glyph = self.CHARSET[ascii_value]
        return self.set_icon(glyph, column)

    def scroll_text(self, the_line, speed=0.1):
        """
        Scroll the specified line of text leftwards across the display.

        Args:
            the_line (string) The string to display
            speed (float)     The delay between frames
        """
        # Import the time library as we use time.sleep() here
        import time

        # Bail on zero string length
        assert len(the_line) > 0, "ERROR - Invalid string set in scroll_text()"

        # Calculate the source buffer size
        length = 0
        for i in range(len(the_line)):
            asc_val = ord(the_line[i])
            if asc_val < 32:
                glyph = self.def_chars[asc_val]
            else:
                glyph = self.CHARSET[asc_val - 32]
            length += len(glyph)
            if asc_val > 32:
                length += 1
        src_buffer = bytearray(length)

        # Draw the string to the source buffer
        row = 0
        for i in range(len(the_line)):
            asc_val = ord(the_line[i])
            if asc_val < 32:
                glyph = self.def_chars[asc_val]
            else:
                glyph = self.CHARSET[asc_val - 32]
            for j in range(len(glyph)):
                src_buffer[row] = glyph[j] if self.is_inverse is False else (
                    (~ glyph[j]) & 0xFF)
                row += 1
            if asc_val > 32:
                row += 1
        assert row == length, "ERROR - Mismatched lengths in scroll_text()"

        # Finally, a the line
        cursor = 0
        while True:
            a = cursor
            for i in range(self.width):
                self.buffer[self._get_row(i)] = src_buffer[a]
                a += 1
            self.draw()
            cursor += 1
            if cursor > length - self.width:
                break
            time.sleep(speed)

    def define_character(self, glyph, char_code=0):
        """
        Set a user-definable character.

        Args:
            glyph (bytearray) The glyph pattern.
            char_code (int)   The character’s ID code (0-31). Default: 0

        Returns:
            The instance (self)
        """
        # Bail on incorrect row numbers or character values
        assert 0 < len(glyph) < self.width * \
            2, "ERROR - Invalid glyph set in define_character()"
        assert 0 <= char_code < 32, "ERROR - Invalid character code set in define_character()"

        self.def_chars[char_code] = glyph
        return self

    def plot(self, x, y, ink=1, xor=False):
        """
        Plot a point on the matrix. (0,0) is bottom left as viewed.

        Args:
            x (integer)   X co-ordinate left to right
            y (integer)   Y co-ordinate bottom to top
            ink (integer) Pixel color: 1 = 'white', 0 = black. NOTE inverse video mode reverses this. Default: 1
            xor (bool)    Whether an underlying pixel already of color ink should be inverted. Default: False

        Returns:
            The instance (self)
        """
        # Bail on incorrect row numbers or character values
        assert (0 <= x < self.width) and (
            0 <= y < self.height), "ERROR - Invalid coordinate set in plot()"

        if ink not in (0, 1):
            ink = 1
        x2 = self._get_row(x)
        if ink == 1:
            if self.is_set(x, y) and xor:
                self.buffer[x2] ^= (1 << y)
            else:
                if self.buffer[x2] & (1 << y) == 0:
                    self.buffer[x2] |= (1 << y)
        else:
            if not self.is_set(x, y) and xor:
                self.buffer[x2] ^= (1 << y)
            else:
                if self.buffer[x2] & (1 << y) != 0:
                    self.buffer[x2] &= ~(1 << y)
        return self

    def is_set(self, x, y):
        """
        Indicate whether a pixel is set.

        Args:
            x (int) X co-ordinate left to right
            y (int) Y co-ordinate bottom to top

        Returns:
            Whether the
        """
        # Bail on incorrect row numbers or character values
        assert (0 <= x < self.width) and (
            0 <= y < self.height), "ERROR - Invalid coordinate set in is_set()"

        x = self._get_row(x)
        bit = (self.buffer[x] >> y) & 1
        return True if bit > 0 else False

    def set_emotion(self, emotion):
        self.emotion = emotion
        if emotion not in self.EMOTIONS:
            pprint('Invalid emotion')
            return
        self.frame_index = 1
        self.last_frame_time = 0
        self.frame = self.EMOTIONS[self.emotion][self.frame_index]

    async def show_emotion(self, emotion, loop=False):
        if emotion not in self.EMOTIONS:
            print('Invalid emotion')
            return
        self.emotion = emotion
        while True:
            for i in range(1, len(self.EMOTIONS[emotion])):
                self.frame = self.EMOTIONS[emotion][i]
                icon = self.CHARSET[self.frame[0]] + self.CHARSET[self.frame[1]]
                self.set_icon(icon).draw()
                await asyncio.sleep_ms(self.frame[2])
            if not loop:
                break
            # Nếu loop=True thì chờ 3 giây trước khi lặp lại
            await asyncio.sleep(2)

               

    def animate(self):
        from code_runner import code_runner

        # if no emotion is set, use Neutral
        if self.emotion == None:
            if code_runner.code_running:
                # no animation while running code
                return
            else:
                emotion = 'NEUTRAL'
        else:
            emotion = self.emotion

        now = time.ticks_ms()
        if (now - self.last_frame_time) > self.frame[2]:
            if self.frame_index == len(self.EMOTIONS[emotion]):
                self.frame_index = 1
                self.emotion = None
                return
            self.frame = self.EMOTIONS[emotion][self.frame_index]
            icon = self.CHARSET[self.frame[0]] + self.CHARSET[self.frame[1]]
            self.set_icon(icon).draw()
            self.frame_index += 1
            self.last_frame_time = now

    def process(self):
        while True:
            self.animate()
            time.sleep_ms(self.FRAME_TIME)

    # ********** PRIVATE METHODS **********

    def _get_row(self, x):
        """
        Convert a column co-ordinate to its memory location
        in the FeatherWing, and return the location.
        An out-of-range value returns False
        """
        a = 1 + (x << 1)
        if x < 8:
            a += 15
        if a >= self.width * 2:
            return False
        return a

i2c = SoftI2C(scl=Pin(47), sda=Pin(21), freq=100000)
display = HT16K33Matrix_16x08(i2c)
display.set_brightness(5)

