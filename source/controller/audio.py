from machine import I2S, Pin, SDCard
import os
import uasyncio as asyncio
import time

class AudioPlayer:
    def __init__(self, i2s):
        try:
            self.i2s = i2s
            print("[INFO] I2S initialized")
        except Exception as e:
            print("[ERROR] I2S init failed:", e)

        try:
            self.sd = SDCard(slot=2, sck=Pin(37), miso=Pin(38), mosi=Pin(36), cs=Pin(35))
            os.mount(self.sd, "/sd")
            print("[INFO] SD card mounted at /sd")
        except Exception as e:
            print("[ERROR] Mount SD failed:", e)

        self._playing = False
        
    def play_w(self, filename):
        path = "/sd/" + filename
        try:
            with open(path, "rb") as f:
                f.read(44)  # Bỏ qua header WAV

                self._playing = True
                while self._playing:
                    data = f.read(1024)
                    if not data:
                        break
                    self.i2s.write(data)
            print(f"[INFO] Done playing {filename}")
        except Exception as e:
            print("[ERROR] Play failed:", e)
        finally:
            self._playing = False

    async def play_wav(self, filename):
        path = "/sd/" + filename
        try:
            with open(path, "rb") as f:
                f.read(44)  # Bỏ qua header WAV

                self._playing = True
                while self._playing:
                    data = f.read(1024)
                    if not data:
                        break
                    self.i2s.write(data)
                    await asyncio.sleep(0)  # Nhường CPU cho task khác
            print(f"[INFO] Done playing {filename}")
        except Exception as e:
            print("[ERROR] Play failed:", e)
        finally:
            self._playing = False


    def stop(self):
        self._playing = False
        
    def state(self):
        return self._playing

    def deinit(self):
        try:
            self.i2s.deinit()
            print("[INFO] I2S deinitialized")
        except:
            pass
        try:
            os.umount("/sd")
            print("[INFO] SD unmounted")
        except:
            pass
        
