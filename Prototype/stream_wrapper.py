import threading
import time
from PIL import Image, ImageTk
from queue import Queue, Empty


class ScrcpyCanvasWrapper:

    def __init__(self, canvas, port=27183, max_size=1080, max_fps=24):
        self.canvas = canvas
        self.port = port
        self.max_size = max_size
        self.max_fps = max_fps

        self.stream = None
        self.running = False
        self.stream_thread = None
        self._display_after_id = None

        self.current_frame = None
        self.frame_lock = threading.Lock()

        # Touch bindings
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)

        # Keyboard bindings
        self.canvas.bind("<KeyPress>", self._on_key_press)
        self.canvas.bind("<KeyRelease>", self._on_key_release)

        self.touch_start_x = None
        self.touch_start_y = None
        self.is_dragging = False
        self.last_move_time = 0
        self.move_throttle = 0.010

        # Android keycodes for special keys
        self._special_keycodes = {
            'BackSpace': 67,
            'Delete': 112,
            'Return': 66,
            'Tab': 61,
            'Escape': 111,
            'Up': 19,
            'Down': 20,
            'Left': 21,
            'Right': 22,
            'Home': 3,
            'End': 123,
        }

    def start(self):
        if self.running:
            return

        self.running = True

        def run_stream():
            try:
                from stream_new import ScrcpyStream
                import cv2

                print("[*] Creating ScrcpyStream instance...")
                self.stream = ScrcpyStream(
                    port=self.port,
                    max_size=self.max_size,
                    max_fps=self.max_fps
                )

                original_display = self.stream.display_frames
                self.stream.display_frames = lambda: self._capture_frames()

                print("[*] Running ScrcpyStream (embedded mode)...")
                self.stream.run()
                print("[*] ScrcpyStream ended")
            except Exception as e:
                print(f"[!] Error in stream: {e}")
                import traceback
                traceback.print_exc()
            finally:
                self.running = False

        self.stream_thread = threading.Thread(target=run_stream, daemon=True)
        self.stream_thread.start()

        self._update_canvas()

    def _capture_frames(self):
        print("[*] Frame capture mode - displaying in Tkinter canvas")

        timeout = time.time() + 15
        while self.stream.running and self.stream.width is None and time.time() < timeout:
            time.sleep(0.1)

        if not self.stream.running or self.stream.width is None:
            print("[-] No frames received")
            return

        print(f"[+] Stream resolution: {self.stream.width}x{self.stream.height}")

        while self.running and self.stream and self.stream.running:
            try:
                frame = self.stream.frame_queue.get(timeout=0.1)

                with self.frame_lock:
                    self.current_frame = frame.copy()

            except Empty:
                pass
            except Exception as e:
                print(f"[!] Frame capture error: {e}")
                time.sleep(0.01)

        print("[*] Frame capture ended")

    def _update_canvas(self):
        if not self.running:
            return

        try:
            if not self.canvas.winfo_exists():
                return

            with self.frame_lock:
                frame = self.current_frame

            if frame is None:
                if self.running:
                    self._display_after_id = self.canvas.after(33, self._update_canvas)
                return

            import cv2
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(frame_rgb)

            cw = max(self.canvas.winfo_width(), 1)
            ch = max(self.canvas.winfo_height(), 1)

            img_w, img_h = image.size
            if img_w <= 0 or img_h <= 0:
                if self.running:
                    self._display_after_id = self.canvas.after(33, self._update_canvas)
                return

            scale = min(cw / img_w, ch / img_h)
            new_w = max(int(img_w * scale), 1)
            new_h = max(int(img_h * scale), 1)

            resized = image.resize((new_w, new_h), Image.Resampling.BILINEAR)
            photo = ImageTk.PhotoImage(resized)

            cx, cy = cw // 2, ch // 2
            if not hasattr(self, '_image_id'):
                self._image_id = self.canvas.create_image(cx, cy, image=photo)
            else:
                self.canvas.coords(self._image_id, cx, cy)
                self.canvas.itemconfig(self._image_id, image=photo)

            self.canvas.image = photo

        except Exception as e:
            print(f"[!] Canvas update error: {e}")

        if self.running and self.canvas.winfo_exists():
            self._display_after_id = self.canvas.after(33, self._update_canvas)

    def _canvas_to_device_coords(self, cx, cy):
        if not self.stream or self.stream.width is None:
            return None, None

        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        img_w, img_h = self.stream.width, self.stream.height

        scale = min(cw / img_w, ch / img_h)
        nw, nh = img_w * scale, img_h * scale
        ox, oy = (cw - nw) / 2, (ch - nh) / 2

        if cx < ox or cx > ox + nw or cy < oy or cy > oy + nh:
            return None, None

        x = (cx - ox) / scale
        y = (cy - oy) / scale

        x = max(0, min(int(x), img_w - 1))
        y = max(0, min(int(y), img_h - 1))

        # Return video-space coordinates directly.
        # scrcpy's server handles the mapping from video to device coords
        # using the screen_size fields in the touch message.
        return x, y

    # -------------------------------------------------------------------------
    # Touch events (now using control channel)
    # -------------------------------------------------------------------------

    def _on_canvas_click(self, event):
        # Give canvas focus so it receives keyboard events
        self.canvas.focus_set()

        x, y = self._canvas_to_device_coords(event.x, event.y)
        if x is not None and y is not None:
            self.touch_start_x, self.touch_start_y = x, y
            self.is_dragging = False
            if self.stream:
                self.stream.send_touch_event('down', x, y)
                print(f"[Touch] DOWN at ({x}, {y})")

    def _on_canvas_drag(self, event):
        self.is_dragging = True
        x, y = self._canvas_to_device_coords(event.x, event.y)
        if x is not None and y is not None and self.stream:
            now = time.time()
            if now - self.last_move_time >= self.move_throttle:
                self.last_move_time = now
                self.stream.send_touch_event('move', x, y)

    def _on_canvas_release(self, event):
        x, y = self._canvas_to_device_coords(event.x, event.y)
        if x is not None and y is not None and self.stream:
            self.stream.send_touch_event('up', x, y)
            print(f"[Touch] UP at ({x}, {y})")

        self.touch_start_x = None
        self.touch_start_y = None
        self.is_dragging = False

    # -------------------------------------------------------------------------
    # Keyboard events
    # -------------------------------------------------------------------------

    def _on_key_press(self, event):
        if not self.stream:
            return

        # Check if it's a special key that needs keycode injection
        if event.keysym in self._special_keycodes:
            keycode = self._special_keycodes[event.keysym]
            self.stream.send_keycode(keycode, action=0)  # DOWN
            return

        # For printable characters, use text injection
        if event.char and len(event.char) >= 1 and ord(event.char[0]) >= 32:
            self.stream.send_text(event.char)

    def _on_key_release(self, event):
        if not self.stream:
            return

        # Send key UP for special keys
        if event.keysym in self._special_keycodes:
            keycode = self._special_keycodes[event.keysym]
            self.stream.send_keycode(keycode, action=1)  # UP

    def stop(self):
        self.running = False
        
        if hasattr(self, "_display_after_id") and self._display_after_id:
            try:
                self.canvas.after_cancel(self._display_after_id)
            except Exception:
                pass
            self._display_after_id = None    

        if self.stream:
            self.stream.running = False
            self.stream = None

        if self._display_after_id:
            self.canvas.after_cancel(self._display_after_id)
            self._display_after_id = None