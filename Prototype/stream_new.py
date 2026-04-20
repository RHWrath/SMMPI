import subprocess
import socket
import struct
import time
import threading
import sys
import os
import numpy as np
from queue import Queue, Empty
from utils import get_scrcpy_server_path, get_adb_path

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


class ScrcpyStream:
    def __init__(self, port=27183, max_size=1080, max_fps=24):
        self.port = port
        self.max_size = max_size
        self.max_fps = max_fps
        self.scrcpy_server = get_scrcpy_server_path()
        self.remote_path = "/data/local/tmp/scrcpy-server-v3.3.4"
        self.width = None
        self.height = None
        self.server_socket = None
        self.running = False
        self.frame_queue = Queue(maxsize=2)
        self.video_conn = None
        self.control_conn = None
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
        # Control channel lock (multiple threads may send control messages)
        self.control_lock = threading.Lock()

    def get_device_screen_size(self):
        try:
            adb_path = get_adb_path()
            if not adb_path:
                print("[-] ADB path could not be resolved")
                return

            result = subprocess.run(
                [adb_path, 'shell', 'wm', 'size'],
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
        adb_path = get_adb_path()
        print(f"[*] Setting up adb reverse using: {adb_path}")

        if not adb_path:
            raise RuntimeError("ADB path could not be resolved")

        result = subprocess.run(
            [adb_path, 'reverse', 'localabstract:scrcpy', f'tcp:{self.port}'],
            capture_output=True,
            text=True
        )

        print(f"[DEBUG] adb reverse return code: {result.returncode}")
        print(f"[DEBUG] adb reverse stdout: {result.stdout}")
        print(f"[DEBUG] adb reverse stderr: {result.stderr}")

        if result.returncode != 0:
            raise RuntimeError(f"Failed to set up adb reverse: {result.stderr}")

        print("[+] ADB reverse configured")

    def start_listener(self):
        print(f"[*] Starting listener on port {self.port}...")
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('127.0.0.1', self.port))
        self.server_socket.listen(2)  # Accept both video and control connections
        print(f"[+] Listener started on 127.0.0.1:{self.port}")

    def push_and_run_scrcpy(self):
        adb_path = get_adb_path()

        print(f"[*] Using adb: {adb_path}")
        print(f"[*] Using scrcpy server: {self.scrcpy_server}")

        if not adb_path:
            print("[-] ADB path could not be resolved")
            return

        if not self.scrcpy_server:
            print("[-] scrcpy server path could not be resolved")
            return

        if not os.path.exists(self.scrcpy_server):
            print(f"[-] scrcpy server file does not exist: {self.scrcpy_server}")
            return

        print("[*] Pushing scrcpy server to device...")
        push_result = subprocess.run(
            [adb_path, 'push', self.scrcpy_server, '/data/local/tmp/'],
            capture_output=True,
            text=True
        )

        print(f"[DEBUG] push return code: {push_result.returncode}")
        print(f"[DEBUG] push stdout: {push_result.stdout}")
        print(f"[DEBUG] push stderr: {push_result.stderr}")

        if push_result.returncode != 0:
            print(f"[-] Failed to push scrcpy: {push_result.stderr}")
            return

        print("[+] Scrcpy server pushed, starting...")

        cmd = [
            adb_path, 'shell',
            f'CLASSPATH={self.remote_path}',
            'app_process', '/', 'com.genymobile.scrcpy.Server', '3.3.4',
            f'max_fps={self.max_fps}',
            'raw_stream=false',
            'control=true',
            'audio=false',
            'send_device_meta=true',
            'send_frame_meta=true',
            'tunnel_forward=false',
            'log_level=debug',
            f'max_size={self.max_size}',
            'video_codec=h264',
            'display_id=0',
            'lock_video_orientation=0'
        ]

        run_result = subprocess.run(cmd, capture_output=True, text=True)

        print(f"[DEBUG] server start return code: {run_result.returncode}")
        print(f"[DEBUG] server start stdout: {run_result.stdout}")
        print(f"[DEBUG] server start stderr: {run_result.stderr}")

    # -------------------------------------------------------------------------
    # Control channel: sending messages
    # -------------------------------------------------------------------------

    def _send_control_msg(self, data):
        """Send raw bytes on the control socket (thread-safe)."""
        if not self.control_conn:
            return
        with self.control_lock:
            try:
                self.control_conn.sendall(data)
            except Exception as e:
                print(f"[!] Failed to send control message: {e}")

    def send_text(self, text):
        """
        Inject text via INJECT_TEXT control message (type 1).
        Supports full UTF-8 including special characters.
        Max 300 bytes per message.
        """
        text_bytes = text.encode('utf-8')[:300]
        # Type 1 (INJECT_TEXT) + 4-byte text length + text bytes
        msg = struct.pack('>BI', 1, len(text_bytes)) + text_bytes
        self._send_control_msg(msg)

    def send_keycode(self, keycode, action=0, repeat=0, metastate=0):
        """
        Inject a keycode via INJECT_KEYCODE control message (type 0).
        action: 0 = DOWN, 1 = UP
        Common keycodes: BACKSPACE=67, ENTER=66, DEL=112, ESCAPE=111, TAB=61
        """
        # Type 0 (INJECT_KEYCODE) + action + keycode + repeat + metastate
        msg = struct.pack('>BBIII', 0, action, keycode, repeat, metastate)
        self._send_control_msg(msg)

    def send_touch_event(self, event_type, x, y):
        """
        Send touch event via INJECT_TOUCH_EVENT control message (type 2).
        Coordinates should be in video-frame space (not device screen space).
        The server uses the screen_size fields to map from video to device coords.
        """
        # Map action string to Android MotionEvent action codes
        action_map = {
            'down': 0,   # ACTION_DOWN
            'up': 1,     # ACTION_UP
            'move': 2,   # ACTION_MOVE
        }
        action = action_map.get(event_type)
        if action is None:
            return

        # Use VIDEO dimensions, not device screen dimensions.
        # scrcpy server maps from video coords to device coords internally.
        video_w = self.width or 1080
        video_h = self.height or 1920

        # Clamp coordinates to video space
        x = max(0, min(int(x), video_w - 1))
        y = max(0, min(int(y), video_h - 1))

        # INJECT_TOUCH_EVENT format (32 bytes):
        # type(1) + action(1) + pointer_id(8) + x(4) + y(4) +
        # screen_w(2) + screen_h(2) + pressure(2) + action_button(4) + buttons(4)
        POINTER_ID_GENERIC_FINGER = 0xFFFFFFFFFFFFFFFF - 1  # -2 as uint64

        # Pressure: 1.0 for down/move, 0.0 for up (encoded as uint16, 0xFFFF = 1.0)
        pressure = 0xFFFF if action != 1 else 0x0000

        msg = struct.pack('>BBQiiHHHII',
            2,                          # type: INJECT_TOUCH_EVENT
            action,                     # action
            POINTER_ID_GENERIC_FINGER,  # pointer id
            x,                          # position x (int32)
            y,                          # position y (int32)
            video_w,                    # video width (uint16)
            video_h,                    # video height (uint16)
            pressure,                   # pressure (uint16 fixed-point)
            0,                          # action button
            0,                          # button state
        )
        self._send_control_msg(msg)

    # -------------------------------------------------------------------------
    # Video stream: reading and decoding
    # -------------------------------------------------------------------------

    def _recv_exact(self, conn, n):
        """Read exactly n bytes from a socket. Returns bytes or None on failure."""
        data = b''
        while len(data) < n:
            try:
                chunk = conn.recv(n - len(data))
                if not chunk:
                    return None
                data += chunk
            except socket.error:
                return None
        return data

    def _read_device_meta(self, conn):
        """Read the 64-byte device name sent on the first socket."""
        meta = self._recv_exact(conn, 64)
        if meta:
            device_name = meta.decode('utf-8', errors='ignore').rstrip('\x00')
            print(f"[+] Device name: {device_name}")
        return meta is not None

    def _read_codec_meta(self, conn):
        """
        Read 12 bytes of codec metadata from the video socket:
        codec_id (u32) + initial_width (u32) + initial_height (u32)
        """
        meta = self._recv_exact(conn, 12)
        if meta is None:
            return False
        codec_id, width, height = struct.unpack('>III', meta)
        codec_names = {0x68323634: 'h264', 0x68323635: 'h265', 0x00617631: 'av1'}
        codec_name = codec_names.get(codec_id, f'unknown(0x{codec_id:08x})')
        print(f"[+] Codec: {codec_name}, initial resolution: {width}x{height}")
        self.width = width
        self.height = height
        return True

    def decode_frames_thread(self, conn):
        """
        Decode H264 frames from the video socket using frame meta headers.
        Each frame is prefixed with a 12-byte header:
          - 8 bytes: PTS with flags in MSBs (config flag, keyframe flag)
          - 4 bytes: packet size
        """
        print("[*] Starting H264 decoder with PyAV (frame-meta mode)...")

        codec = av.CodecContext.create('h264', 'r')
        codec.options = {
            'flags': 'low_delay',
            'flags2': 'fast',
        }
        codec.skip_frame = 'NONREF'
        codec.thread_type = 'SLICE'

        frames_decoded = 0
        packets_received = 0
        last_log = time.time()

        try:
            while self.running:
                # Read 12-byte frame header
                header = self._recv_exact(conn, 12)
                if header is None:
                    print("[-] Video connection closed")
                    break

                pts_and_flags, packet_size = struct.unpack('>qI', header)

                # Extract flags from PTS MSBs
                # Bit 63: config packet flag
                # Bit 62: key frame flag
                is_config = bool(pts_and_flags & (1 << 63))
                is_keyframe = bool(pts_and_flags & (1 << 62))
                # Clear flag bits to get actual PTS
                pts = pts_and_flags & 0x3FFFFFFFFFFFFFFF

                if packet_size == 0:
                    continue

                # Read the actual packet data
                packet_data = self._recv_exact(conn, packet_size)
                if packet_data is None:
                    print("[-] Video connection closed during packet read")
                    break

                packets_received += 1

                if time.time() - last_log > 3:
                    print(f"[*] Packets: {packets_received}, decoded: {frames_decoded} frames")
                    last_log = time.time()

                # Config packets contain SPS/PPS — feed to decoder but don't expect frames
                # Key frames and regular frames — decode normally
                packet = av.Packet(packet_data)

                try:
                    for frame in codec.decode(packet):
                        if self.width is None or self.width != frame.width or self.height != frame.height:
                            self.width = frame.width
                            self.height = frame.height
                            print(f"[+] Resolution: {self.width}x{self.height}")

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
                    # Can happen on first packets before SPS/PPS are received
                    pass
                except Exception as e:
                    if "Invalid data" not in str(e):
                        print(f"[*] Decode: {e}")

        except Exception as e:
            print(f"[-] Decoder error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            print(f"[*] Decoder stopped, decoded {frames_decoded} frames from {packets_received} packets")

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
                        print("[*] Keyboard support enabled - type to inject text")

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
        """Main run method to start the scrcpy stream with control channel."""
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

            # Connection order (with audio=false): video first, then control
            print("[*] Waiting for video connection...")
            self.video_conn, addr = self.server_socket.accept()
            print(f"[+] Video connection established from {addr}")

            print("[*] Waiting for control connection...")
            self.control_conn, addr = self.server_socket.accept()
            print(f"[+] Control connection established from {addr}")

            # Read device metadata (64 bytes device name on first socket)
            if not self._read_device_meta(self.video_conn):
                print("[-] Failed to read device metadata")
                return

            # Read codec metadata (12 bytes: codec_id + width + height)
            if not self._read_codec_meta(self.video_conn):
                print("[-] Failed to read codec metadata")
                return

            # Start decoder thread (now reads frame-meta prefixed packets)
            decoder_thread = threading.Thread(
                target=self.decode_frames_thread,
                args=(self.video_conn,),
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

        if self.video_conn:
            try:
                self.video_conn.close()
            except:
                pass

        if self.control_conn:
            try:
                self.control_conn.close()
            except:
                pass

        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass

        adb_path = get_adb_path()
        if adb_path:
            subprocess.run(
                [adb_path, 'reverse', '--remove', 'localabstract:scrcpy'],
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