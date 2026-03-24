import subprocess
import socket
import time
import threading
import sys
import os
import numpy as np
from queue import Queue, Empty

try:
    import cv2
except ImportError:
    print("OpenCV not found. Install with: pip install opencv-python")
    sys.exit(1)

try:
    import av
except ImportError:
    print("PyAV not found. Install with: pip install av")
    sys.exit(1)


def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)


class ScrcpyStream:
    def __init__(self, port=27183, max_size=1080, max_fps=24):
        self.port = port
        self.max_size = max_size
        self.max_fps = max_fps
        self.scrcpy_server = get_resource_path("scrcpy-server-v3.3.4")
        self.remote_path = "/data/local/tmp/scrcpy-server-v3.3.4"
        self.width = None
        self.height = None
        self.server_socket = None
        self.running = False
        self.frame_queue = Queue(maxsize=2)
        self.conn = None
        # Touch support
        self.display_width = None
        self.display_height = None
        self.current_frame = None
        # Actual device screen resolution (for ADB input)
        self.device_screen_width = None
        self.device_screen_height = None
        # Touch tracking
        self.touch_active = False
        self.touch_device = None
        self.last_touch_time = 0
        self.touch_throttle = 0.016  # ~60 updates/sec

    def get_device_screen_size(self):
        try:
            result = subprocess.run(
                ['adb', 'shell', 'wm', 'size'],
                capture_output=True,
                text=True
            )
            override_size = None
            physical_size = None
            
            for line in result.stdout.strip().split('\n'):
                if 'Override size:' in line:
                    size_str = line.split(':')[-1].strip()
                    w, h = size_str.split('x')
                    override_size = (int(w), int(h))
                elif 'Physical size:' in line:
                    size_str = line.split(':')[-1].strip()
                    w, h = size_str.split('x')
                    physical_size = (int(w), int(h))
            
            if override_size:
                self.device_screen_width, self.device_screen_height = override_size
                print(f"[+] Device screen size (override): {self.device_screen_width}x{self.device_screen_height}")
            elif physical_size:
                self.device_screen_width, self.device_screen_height = physical_size
                print(f"[+] Device screen size (physical): {self.device_screen_width}x{self.device_screen_height}")
                
        except Exception as e:
            print(f"[-] Failed to get device screen size: {e}")
        
        if self.device_screen_width is None:
            print("[*] Using video dimensions for touch (no device size found)")

    def get_touch_device(self):
        """Find the touch input device on the Android device."""
        try:
            result = subprocess.run(
                ['adb', 'shell', 'getevent', '-pl'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            current_device = None
            for line in result.stdout.split('\n'):
                if line.startswith('add device'):
                    current_device = line.split(':')[-1].strip()
                elif 'ABS_MT_POSITION_X' in line or 'ABS_MT_TOUCH_MAJOR' in line:
                    if current_device:
                        self.touch_device = current_device
                        print(f"[+] Touch device: {self.touch_device}")
                        return
            
            for dev in ['/dev/input/event1', '/dev/input/event2', '/dev/input/event3']:
                self.touch_device = dev
                print(f"[*] Using fallback touch device: {self.touch_device}")
                return
                
        except Exception as e:
            print(f"[-] Failed to find touch device: {e}")
            self.touch_device = '/dev/input/event1'

    def map_to_device(self, frame_x, frame_y):
        """Map frame coordinates to device coordinates."""
        if self.width is None or self.height is None:
            return None, None
        
        frame_w = self.width
        frame_h = self.height
        dev_w = self.device_screen_width if self.device_screen_width else frame_w
        dev_h = self.device_screen_height if self.device_screen_height else frame_h
        
        device_x = int(frame_x * dev_w / frame_w)
        device_y = int(frame_y * dev_h / frame_h)
        
        device_x = max(0, min(device_x, dev_w - 1))
        device_y = max(0, min(device_y, dev_h - 1))
        
        return device_x, device_y

    def setup_adb_reverse(self):
        print("[*] Setting up adb reverse...")
        result = subprocess.run(
            ['adb', 'reverse', 'localabstract:scrcpy', f'tcp:{self.port}'],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"Failed to set up adb reverse: {result.stderr}")
        print("[+] ADB reverse configured")

    def start_listener(self):
        print(f"[*] Starting listener on port {self.port}...")
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('127.0.0.1', self.port))
        self.server_socket.listen(1)
        print(f"[+] Listener started on 127.0.0.1:{self.port}")

    def push_and_run_scrcpy(self):
        print("[*] Pushing scrcpy server to device...")
        push_result = subprocess.run(
            ['adb', 'push', self.scrcpy_server, '/data/local/tmp/'],
            capture_output=True,
            text=True
        )
        if push_result.returncode != 0:
            print(f"[-] Failed to push scrcpy: {push_result.stderr}")
            return

        print("[+] Scrcpy server pushed, starting...")
        
        cmd = [
            'adb', 'shell',
            f'CLASSPATH={self.remote_path}',
            'app_process', '/', 'com.genymobile.scrcpy.Server', '3.3.4',
            f'max_fps={self.max_fps}',
            'raw_stream=true',
            'control=false',
            'send_device_meta=false',
            'send_frame_meta=false',
            'tunnel_forward=false',
            'log_level=debug',
            f'max_size={self.max_size}',
            'video_codec=h264',
            'display_id=0',
            'lock_video_orientation=0'
        ]
        
        subprocess.run(cmd, capture_output=True)

    def find_nal_units(self, data):
        nal_units = []
        i = 0
        start = -1
        
        while i < len(data) - 3:
            if data[i:i+4] == b'\x00\x00\x00\x01':
                if start >= 0:
                    nal_units.append((start, i))
                start = i
                i += 4
            elif data[i:i+3] == b'\x00\x00\x01':
                if start >= 0:
                    nal_units.append((start, i))
                start = i
                i += 3
            else:
                i += 1
        
        return nal_units, start

    def decode_frames_thread(self, conn):
        print("[*] Starting H264 decoder with PyAV...")
        
        codec = av.CodecContext.create('h264', 'r')
        codec.options = {
            'flags': 'low_delay',
            'flags2': 'fast',
        }
        codec.skip_frame = 'NONREF'
        codec.thread_type = 'SLICE'
        
        frames_decoded = 0
        bytes_received = 0
        last_log = time.time()
        buffer = b''
        waiting_for_keyframe = True
        
        try:
            while self.running:
                try:
                    data = conn.recv(131072)
                    if not data:
                        print("[-] Connection closed by device")
                        break
                    
                    bytes_received += len(data)
                    buffer += data
                    
                    if time.time() - last_log > 3:
                        print(f"[*] Received {bytes_received/1024:.0f}KB, decoded {frames_decoded} frames, buffer: {len(buffer)} bytes")
                        last_log = time.time()
                    
                    nal_units, last_start = self.find_nal_units(buffer)
                    
                    if not nal_units:
                        continue
                    
                    for start, end in nal_units:
                        nal_data = buffer[start:end]
                        
                        if len(nal_data) > 4:
                            nal_type = nal_data[4] & 0x1F if nal_data[3] == 1 else nal_data[3] & 0x1F
                            
                            if nal_type in (5, 7, 8):
                                waiting_for_keyframe = False
                            
                            if waiting_for_keyframe:
                                continue
                        
                        packet = av.Packet(nal_data)
                        
                        try:
                            for frame in codec.decode(packet):
                                if self.width is None:
                                    self.width = frame.width
                                    self.height = frame.height
                                    print(f"[+] Detected resolution: {self.width}x{self.height}")
                                
                                img = frame.to_ndarray(format='bgr24')
                                
                                frames_decoded += 1
                                if frames_decoded == 1:
                                    print(f"[+] First frame decoded!")
                                
                                if self.frame_queue.full():
                                    try:
                                        self.frame_queue.get_nowait()
                                    except Empty:
                                        pass
                                
                                try:
                                    self.frame_queue.put_nowait(img)
                                except:
                                    pass
                                    
                        except av.error.InvalidDataError:
                            waiting_for_keyframe = True
                        except Exception as e:
                            if "Invalid data" not in str(e):
                                print(f"[*] Decode: {e}")
                    
                    if last_start >= 0:
                        buffer = buffer[last_start:]
                    else:
                        buffer = b''
                        
                except socket.error as e:
                    print(f"[-] Socket error: {e}")
                    break
                    
        except Exception as e:
            print(f"[-] Decoder error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            print(f"[*] Decoder stopped, decoded {frames_decoded} frames")

    def mouse_callback(self, event, x, y, flags, param):
        device_x, device_y = self.map_to_device(x, y)
        if device_x is None:
            return
        
        if event == cv2.EVENT_LBUTTONDOWN:
            self.touch_active = True
            self.send_touch_event('down', device_x, device_y)
            print(f"[>] touch DOWN ({device_x}, {device_y})")
            
        elif event == cv2.EVENT_LBUTTONUP:
            if self.touch_active:
                self.send_touch_event('up', device_x, device_y)
                self.touch_active = False
                print(f"[>] touch UP ({device_x}, {device_y})")
                
        elif event == cv2.EVENT_MOUSEMOVE and self.touch_active:
            now = time.time()
            if now - self.last_touch_time >= self.touch_throttle:
                self.send_touch_event('move', device_x, device_y)
                self.last_touch_time = now

    def send_touch_event(self, event_type, x, y):
        def send():
            if event_type == 'down':
                subprocess.run(
                    ['adb', 'shell', 'input', 'motionevent', 'DOWN', str(x), str(y)],
                    capture_output=True
                )
            elif event_type == 'up':
                subprocess.run(
                    ['adb', 'shell', 'input', 'motionevent', 'UP', str(x), str(y)],
                    capture_output=True
                )
            elif event_type == 'move':
                subprocess.run(
                    ['adb', 'shell', 'input', 'motionevent', 'MOVE', str(x), str(y)],
                    capture_output=True
                )
        
        threading.Thread(target=send, daemon=True).start()

    def display_frames(self):
        print("[*] Waiting for first frame...")
        timeout = time.time() + 15
        while self.running and self.width is None and time.time() < timeout:
            time.sleep(0.1)
        
        if not self.running or self.width is None:
            print("[-] No frames received, exiting display")
            return
            
        print(f"[*] Starting display ({self.width}x{self.height})")
        
        cv2.namedWindow('Scrcpy Stream', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Scrcpy Stream', self.width, self.height)
        cv2.setMouseCallback('Scrcpy Stream', self.mouse_callback)
        
        self.display_width = self.width
        self.display_height = self.height
        
        frames_displayed = 0
        
        while self.running:
            try:
                try:
                    frame = self.frame_queue.get(timeout=0.1)
                    frames_displayed += 1
                    
                    try:
                        rect = cv2.getWindowImageRect('Scrcpy Stream')
                        if rect[2] > 0 and rect[3] > 0:
                            self.display_width = rect[2]
                            self.display_height = rect[3]
                    except:
                        pass
                    
                    if frames_displayed == 1:
                        print("[+] Displaying first frame!")
                        print("[*] Touch support enabled - click to tap on device")
                    
                    cv2.imshow('Scrcpy Stream', frame)
                    
                except Empty:
                    pass
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print("[*] Quit requested")
                    self.running = False
                    break
                    
                try:
                    if cv2.getWindowProperty('Scrcpy Stream', cv2.WND_PROP_VISIBLE) < 1:
                        print("[*] Window closed")
                        self.running = False
                        break
                except:
                    pass
                    
            except Exception as e:
                print(f"[-] Display error: {e}")
                break
        
        print(f"[*] Display stopped, showed {frames_displayed} frames")
        cv2.destroyAllWindows()

    def run(self):
        """Main run method to start the scrcpy stream."""
        self.running = True
        
        try:
            self.setup_adb_reverse()
            
            self.get_device_screen_size()
            
            self.start_listener()
            
            def delayed_scrcpy():
                time.sleep(1)
                self.push_and_run_scrcpy()
            
            scrcpy_thread = threading.Thread(target=delayed_scrcpy, daemon=True)
            scrcpy_thread.start()
            
            print("[*] Waiting for scrcpy connection...")
            self.conn, addr = self.server_socket.accept()
            print(f"[+] Connection established from {addr}")
            
            decoder_thread = threading.Thread(
                target=self.decode_frames_thread,
                args=(self.conn,),
                daemon=True
            )
            decoder_thread.start()
            
            self.display_frames()
            
        except KeyboardInterrupt:
            print("\n[*] Interrupted by user")
        except Exception as e:
            print(f"[-] Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.cleanup()

    def cleanup(self):
        self.running = False
        print("[*] Cleaning up...")
        
        cv2.destroyAllWindows()
        
        if self.conn:
            try:
                self.conn.close()
            except:
                pass
        
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        subprocess.run(
            ['adb', 'reverse', '--remove', 'localabstract:scrcpy'],
            capture_output=True
        )
        
        print("[+] Cleanup complete")


def main():
    print("=" * 50)
    print("  Scrcpy Python Stream Viewer")
    print("=" * 50)
    
    stream = ScrcpyStream(
        port=27183,
        max_size=1080,
        max_fps=24
    )
    stream.run()


if __name__ == '__main__':
    main()
