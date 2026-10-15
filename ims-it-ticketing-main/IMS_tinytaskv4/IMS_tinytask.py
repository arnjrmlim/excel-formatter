import os
import sys
import json
import time
import ctypes
import threading
import platform
import tkinter as tk
import winreg

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from tkinter import (
    filedialog,
    messagebox
)
from urllib.parse import parse_qs, urlparse

from pynput import mouse, keyboard


# =========================================================
# CONFIG
# =========================================================

CONTROL_HOST = "127.0.0.1"
CONTROL_PORT = 8765
URL_PROTOCOL = "ims-tinytask"
APP_USER_MODEL_ID = "IMS.Format.TinyTask"
APP_ICON_FILE = "icon.ico"
WM_SETICON = 0x0080
ICON_SMALL = 0
ICON_BIG = 1
IMAGE_ICON = 1
LR_LOADFROMFILE = 0x0010

DEFAULT_SETTINGS = {
    "record_hotkey": "ctrl+alt+r",
    "playback_hotkey": "ctrl+alt+p",
    "recent_macros": []
}

IS_WINDOWS = platform.system().lower() == "windows"

if not IS_WINDOWS:
    raise RuntimeError("This macro engine only supports Windows.")


def get_app_data_dir():

    base_path = os.environ.get("APPDATA")

    if not base_path:
        base_path = os.path.expanduser("~")

    return os.path.join(base_path, "IMS TinyTask")


APP_DATA_DIR = get_app_data_dir()
SETTINGS_FILE = os.path.join(APP_DATA_DIR, "settings.json")
LEGACY_SETTINGS_FILE = "settings.json"


def resource_path(filename):

    # PyInstaller onefile extracts bundled files into sys._MEIPASS at runtime.
    # During source runs the same asset lives beside this script, so callers can
    # use one helper without caring whether the app is frozen or unpackaged.
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, filename)

    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)


def set_windows_app_id():

    # Windows uses the AppUserModelID for taskbar grouping and icon identity.
    # Set it before creating Tk so the shell does not fall back to python.exe.
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            APP_USER_MODEL_ID
        )
    except OSError:
        pass


def apply_window_icon(window):

    icon_path = resource_path(APP_ICON_FILE)

    if os.path.exists(icon_path):
        try:
            # Tk needs the .ico file at runtime for source runs and for any
            # frozen build that bundles icon.ico as data. The "default" option
            # also gives subsequently-created Tk child windows the same icon.
            window.iconbitmap(default=icon_path)
            set_native_window_icons_from_file(window, icon_path)
            return
        except tk.TclError:
            pass

    if not getattr(sys, "frozen", False):
        return

    # A --onefile build always has the .ico embedded by PyInstaller's --icon
    # option, even when the .ico is not also present as an extracted data file.
    # Extract that icon from the running EXE so Tk/Toplevel windows still show
    # the release icon on clean machines and direct GitHub Release downloads.
    try:
        large_icon = ctypes.c_void_p()
        small_icon = ctypes.c_void_p()
        extracted = ctypes.windll.shell32.ExtractIconExW(
            sys.executable,
            0,
            ctypes.byref(large_icon),
            ctypes.byref(small_icon),
            1
        )

        if extracted:
            for hwnd in get_window_hwnds(window):
                ctypes.windll.user32.SendMessageW(
                    hwnd,
                    WM_SETICON,
                    ICON_BIG,
                    large_icon
                )
                ctypes.windll.user32.SendMessageW(
                    hwnd,
                    WM_SETICON,
                    ICON_SMALL,
                    small_icon
                )
            window._ims_icon_handles = (large_icon, small_icon)

    except (OSError, tk.TclError):
        pass


def set_native_window_icons_from_file(window, icon_path):

    # Tk's iconbitmap() is enough for most windows, but setting WM_SETICON makes
    # Windows Explorer/taskbar/title-bar icon probes see the same handles on a
    # clean machine with no existing icon cache.
    try:
        load_image = ctypes.windll.user32.LoadImageW
        load_image.restype = ctypes.c_void_p

        large_icon = load_image(
            None,
            icon_path,
            IMAGE_ICON,
            32,
            32,
            LR_LOADFROMFILE
        )
        small_icon = load_image(
            None,
            icon_path,
            IMAGE_ICON,
            16,
            16,
            LR_LOADFROMFILE
        )

        if not large_icon and not small_icon:
            return

        for hwnd in get_window_hwnds(window):
            if large_icon:
                ctypes.windll.user32.SendMessageW(
                    hwnd,
                    WM_SETICON,
                    ICON_BIG,
                    large_icon
                )

            if small_icon:
                ctypes.windll.user32.SendMessageW(
                    hwnd,
                    WM_SETICON,
                    ICON_SMALL,
                    small_icon
                )

        window._ims_icon_handles = (large_icon, small_icon)

    except (OSError, tk.TclError):
        pass


def get_window_hwnds(window):

    # On Windows, Tk can expose both an inner Tk HWND and a window-manager frame
    # HWND. The visible title-bar/taskbar icon belongs to the frame, so update
    # both when possible.
    window.update_idletasks()

    handles = []

    raw_handles = []

    try:
        raw_handles.append(window.winfo_id())
    except tk.TclError:
        pass

    try:
        raw_handles.append(window.frame())
    except (AttributeError, tk.TclError):
        pass

    for raw_handle in raw_handles:
        try:
            hwnd = int(raw_handle, 0) if isinstance(raw_handle, str) else int(raw_handle)
        except (TypeError, ValueError):
            continue

        if hwnd and hwnd not in handles:
            handles.append(hwnd)

    return handles


def register_url_protocol():

    try:
        command = f'"{sys.executable}" "%1"'

        with winreg.CreateKey(
            winreg.HKEY_CURRENT_USER,
            rf"Software\Classes\{URL_PROTOCOL}"
        ) as key:
            winreg.SetValueEx(
                key,
                None,
                0,
                winreg.REG_SZ,
                "URL:IMS TinyTask"
            )
            winreg.SetValueEx(
                key,
                "URL Protocol",
                0,
                winreg.REG_SZ,
                ""
            )

        with winreg.CreateKey(
            winreg.HKEY_CURRENT_USER,
            rf"Software\Classes\{URL_PROTOCOL}\shell\open\command"
        ) as key:
            winreg.SetValueEx(
                key,
                None,
                0,
                winreg.REG_SZ,
                command
            )

    except OSError:
        pass


# =========================================================
# WINDOWS INPUT CONSTANTS
# =========================================================

user32 = ctypes.windll.user32
user32.SetProcessDPIAware()
timeBeginPeriod = ctypes.windll.winmm.timeBeginPeriod
timeBeginPeriod(1)

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_ABSOLUTE = 0x8000


# =========================================================
# WINDOWS INPUT STRUCTURES
# =========================================================

class MOUSEINPUT(ctypes.Structure):
    _fields_ = (
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))
    )


class KEYBDINPUT(ctypes.Structure):
    _fields_ = (
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))
    )


class INPUT(ctypes.Structure):

    class _I(ctypes.Union):
        _fields_ = [
            ("mi", MOUSEINPUT),
            ("ki", KEYBDINPUT)
        ]

    _anonymous_ = ("i",)

    _fields_ = [
        ("type", ctypes.c_ulong),
        ("i", _I)
    ]


# =========================================================
# MOUSE HELPERS
# =========================================================

def screen_size():
    return (
        user32.GetSystemMetrics(0),
        user32.GetSystemMetrics(1)
    )


def to_absolute(x, y):

    sx, sy = screen_size()

    abs_x = int(x * 65535 / max(1, sx - 1))
    abs_y = int(y * 65535 / max(1, sy - 1))

    return abs_x, abs_y


def send_mouse(flags, x=0, y=0, data=0):

    abs_x, abs_y = to_absolute(x, y)

    mi = MOUSEINPUT(
        abs_x,
        abs_y,
        data,
        flags | MOUSEEVENTF_ABSOLUTE,
        0,
        None
    )

    inp = INPUT(type=INPUT_MOUSE, mi=mi)

    user32.SendInput(
        1,
        ctypes.byref(inp),
        ctypes.sizeof(inp)
    )


def mouse_move(x, y):
    send_mouse(MOUSEEVENTF_MOVE, x, y)


def mouse_left_down(x, y):
    send_mouse(MOUSEEVENTF_MOVE | MOUSEEVENTF_LEFTDOWN, x, y)


def mouse_left_up(x, y):
    send_mouse(MOUSEEVENTF_MOVE | MOUSEEVENTF_LEFTUP, x, y)


def mouse_right_down(x, y):
    send_mouse(MOUSEEVENTF_MOVE | MOUSEEVENTF_RIGHTDOWN, x, y)


def mouse_right_up(x, y):
    send_mouse(MOUSEEVENTF_MOVE | MOUSEEVENTF_RIGHTUP, x, y)


def mouse_middle_down(x, y):
    send_mouse(MOUSEEVENTF_MOVE | MOUSEEVENTF_MIDDLEDOWN, x, y)


def mouse_middle_up(x, y):
    send_mouse(MOUSEEVENTF_MOVE | MOUSEEVENTF_MIDDLEUP, x, y)


def mouse_scroll(delta):

    mi = MOUSEINPUT(
        0,
        0,
        delta,
        MOUSEEVENTF_WHEEL,
        0,
        None
    )

    inp = INPUT(type=INPUT_MOUSE, mi=mi)

    user32.SendInput(
        1,
        ctypes.byref(inp),
        ctypes.sizeof(inp)
    )


# =========================================================
# KEYBOARD HELPERS
# =========================================================

MapVirtualKey = user32.MapVirtualKeyW

SPECIAL_KEYS = {
    keyboard.Key.ctrl_l: 0xA2,
    keyboard.Key.ctrl_r: 0xA3,

    keyboard.Key.alt_l: 0xA4,
    keyboard.Key.alt_r: 0xA5,

    keyboard.Key.shift: 0x10,
    keyboard.Key.shift_l: 0xA0,
    keyboard.Key.shift_r: 0xA1,

    keyboard.Key.cmd: 0x5B,
    keyboard.Key.cmd_l: 0x5B,
    keyboard.Key.cmd_r: 0x5C,

    keyboard.Key.enter: 0x0D,
    keyboard.Key.backspace: 0x08,
    keyboard.Key.tab: 0x09,
    keyboard.Key.esc: 0x1B,
    keyboard.Key.space: 0x20,

    keyboard.Key.up: 0x26,
    keyboard.Key.down: 0x28,
    keyboard.Key.left: 0x25,
    keyboard.Key.right: 0x27,

    keyboard.Key.delete: 0x2E,
    keyboard.Key.home: 0x24,
    keyboard.Key.end: 0x23,
    keyboard.Key.page_up: 0x21,
    keyboard.Key.page_down: 0x22,
    keyboard.Key.insert: 0x2D,
}


def get_vk(key):

    if key in SPECIAL_KEYS:
        return SPECIAL_KEYS[key]

    char = getattr(key, "char", None)

    if char and ord(char) < 32:
        vk = getattr(key, "vk", None)

        if vk is not None:
            return vk

        if "\x01" <= char <= "\x1a":
            return ord("A") + ord(char) - 1

    if char:
        vk = user32.VkKeyScanW(char)

        if vk != -1:
            return vk & 0xFF

    try:
        return key.vk
    except AttributeError:
        return None


def vk_to_scan(vk):

    scan = user32.MapVirtualKeyW(vk, 0)

    extended = vk in {
        0xA3,  # Right Ctrl
        0xA5,  # Right Alt
        0x2D,  # Insert
        0x2E,  # Delete
        0x24,  # Home
        0x23,  # End
        0x21,  # Page Up
        0x22,  # Page Down
        0x25,  # Left
        0x26,  # Up
        0x27,  # Right
        0x28,  # Down
        0x5B,  # Left Win
        0x5C,  # Right Win
    }

    return scan, extended


def send_key(scan_code, extended=False, key_up=False):

    flags = KEYEVENTF_SCANCODE

    if extended:
        flags |= KEYEVENTF_EXTENDEDKEY

    if key_up:
        flags |= KEYEVENTF_KEYUP

    ki = KEYBDINPUT(
        0,
        scan_code,
        flags,
        0,
        None
    )

    inp = INPUT(
        type=INPUT_KEYBOARD,
        ki=ki
    )

    user32.SendInput(
        1,
        ctypes.byref(inp),
        ctypes.sizeof(inp)
    )


# =========================================================
# APP
# =========================================================

class MacroApp:

    COLORS = {
        "window": "#f3f6fb",
        "panel": "#ffffff",
        "panel_alt": "#f8fafc",
        "border": "#d7dfeb",
        "text": "#172033",
        "muted": "#667085",
        "blue": "#1f6feb",
        "blue_hover": "#1959bd",
        "green": "#067647",
        "green_hover": "#05603a",
        "red": "#b42318",
        "red_hover": "#912018",
        "amber": "#b54708"
    }

    def __init__(self):

        self.recording = False
        self.playing = False

        self.recorded_events = []
        self.recorded_duration = 0
        self.recording_stop_time = None
        self.recording_start_time = None
        self.recording_stopped_by_hotkey = False

        self.current_keys = set()

        self.settings = DEFAULT_SETTINGS.copy()

        self.last_hotkey_time = 0

        self.load_settings()

        self.build_ui()

        register_url_protocol()
        self.start_hotkey_listener()
        self.start_control_server()

    # =====================================================
    # SETTINGS
    # =====================================================

    def load_settings(self):

        settings_path = SETTINGS_FILE

        if (
            not os.path.exists(settings_path) and
            os.path.exists(LEGACY_SETTINGS_FILE)
        ):
            settings_path = LEGACY_SETTINGS_FILE

        if os.path.exists(settings_path):

            try:
                with open(settings_path, "r", encoding="utf-8") as f:
                    self.settings.update(json.load(f))

            except Exception:
                pass

    def save_settings(self):

        os.makedirs(APP_DATA_DIR, exist_ok=True)

        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, indent=4)

    def register_macro_file(self, filename):

        if not filename:
            return

        full_path = os.path.abspath(filename)
        recent_macros = [
            path
            for path in self.settings.get("recent_macros", [])
            if os.path.abspath(path) != full_path
        ]

        recent_macros.insert(0, full_path)
        self.settings["recent_macros"] = recent_macros[:12]
        self.save_settings()

    def get_recent_macros(self):

        recent_macros = []

        for index, path in enumerate(self.settings.get("recent_macros", [])):
            recent_macros.append({
                "index": index,
                "name": os.path.basename(path),
                "path": path,
                "exists": os.path.exists(path)
            })

        return recent_macros

    # =====================================================
    # HOTKEY PARSER
    # =====================================================

    def parse_hotkey(self, hotkey):

        mapping = {
            "ctrl": keyboard.Key.ctrl_l,
            "alt": keyboard.Key.alt_l,
            "shift": keyboard.Key.shift,
        }

        result = set()

        for part in hotkey.lower().split("+"):

            part = part.strip()

            if part in mapping:
                result.add(mapping[part])

            else:
                result.add(keyboard.KeyCode.from_char(part))

        return result

    def normalize_hotkey_key(self, key):

        modifier_aliases = {
            keyboard.Key.ctrl: "ctrl",
            keyboard.Key.ctrl_l: "ctrl",
            keyboard.Key.ctrl_r: "ctrl",
            keyboard.Key.alt: "alt",
            keyboard.Key.alt_l: "alt",
            keyboard.Key.alt_r: "alt",
            keyboard.Key.alt_gr: "alt",
            keyboard.Key.shift: "shift",
            keyboard.Key.shift_l: "shift",
            keyboard.Key.shift_r: "shift",
        }

        if key in modifier_aliases:
            return modifier_aliases[key]

        vk = getattr(key, "vk", None)

        if isinstance(vk, int):
            if 65 <= vk <= 90:
                return chr(vk).lower()

            if 48 <= vk <= 57:
                return chr(vk)

        char = getattr(key, "char", None)

        if char:
            return char.lower()

        return str(key).lower()

    def parse_hotkey_match(self, hotkey):

        return {
            part.strip().lower()
            for part in hotkey.split("+")
            if part.strip()
        }

    # =====================================================
    # RECORDING
    # =====================================================

    def start_recording(self):

        self.recorded_events.clear()
        self.recorded_duration = 0
        self.recording_stop_time = None
        self.recording_stopped_by_hotkey = False

        start_time = time.perf_counter()
        self.recording_start_time = start_time

        last_move_time = 0

        def timestamp():
            return time.perf_counter() - start_time

        def add_event(event_type, data, event_time=None):

            self.recorded_events.append({
                "type": event_type,
                "data": data,
                "time": timestamp() if event_time is None else event_time
            })

        # =================================================
        # KEYBOARD
        # =================================================

        def on_key_press(key):

            if not self.recording:
                return

            vk = get_vk(key)

            if vk is None:
                return

            scan, extended = vk_to_scan(vk)

            add_event("key_down", {
                "scan": scan,
                "extended": extended
            })

        def on_key_release(key):

            if not self.recording:
                return

            vk = get_vk(key)

            if vk is None:
                return

            scan, extended = vk_to_scan(vk)

            add_event("key_up", {
                "scan": scan,
                "extended": extended
            })

        # =================================================
        # MOUSE
        # =================================================

        def on_move(x, y):

            nonlocal last_move_time

            if not self.recording:
                return

            now = time.perf_counter()

            if now - last_move_time < 0.008:
                return

            last_move_time = now

            add_event("move", {
                "x": x,
                "y": y
            })

        def on_click(x, y, button, pressed):

            if not self.recording:
                return

            button_name = str(button)

            add_event(
                "mouse_down" if pressed else "mouse_up",
                {
                    "x": x,
                    "y": y,
                    "button": button_name
                }
            )

        def on_scroll(x, y, dx, dy):

            if not self.recording:
                return

            add_event("scroll", {
                "dx": dx,
                "dy": dy
            })

        # =================================================
        # LISTENERS
        # =================================================

        mouse_listener = mouse.Listener(
            on_move=on_move,
            on_click=on_click,
            on_scroll=on_scroll
        )

        keyboard_listener = keyboard.Listener(
            on_press=on_key_press,
            on_release=on_key_release
        )

        mouse_listener.start()
        keyboard_listener.start()

        while self.recording:
            time.sleep(0.001)

        stop_time = self.recording_stop_time or time.perf_counter()
        self.recorded_duration = max(0, stop_time - start_time)
        if self.recording_stopped_by_hotkey:
            self.trim_stop_hotkey_events()

        if self.recorded_events:
            add_event("recording_end", {}, self.recorded_duration)

        mouse_listener.stop()
        keyboard_listener.stop()

        if hasattr(self, "root"):
            self.root.after(0, self.refresh_macro_summary)

    def stop_recording(self, stopped_by_hotkey=False):

        if not self.recording:
            return

        if self.recording_stop_time is None:
            self.recording_stop_time = time.perf_counter()

        self.recording_stopped_by_hotkey = stopped_by_hotkey
        self.recording = False

    def get_hotkey_scans(self, hotkey):

        scans = set()

        for key in self.parse_hotkey(hotkey):
            vk = get_vk(key)

            if vk is None:
                continue

            scan, _extended = vk_to_scan(vk)
            scans.add(scan)

        return scans

    def trim_stop_hotkey_events(self):

        hotkey_scans = self.get_hotkey_scans(
            self.settings["record_hotkey"]
        )

        trim_after = max(0, self.recorded_duration - 0.75)

        while self.recorded_events:
            event = self.recorded_events[-1]
            event_type = event.get("type")
            data = event.get("data", {})

            if event_type not in {"key_down", "key_up"}:
                break

            if data.get("scan") not in hotkey_scans:
                break

            if event.get("time", 0) < trim_after:
                break

            self.recorded_events.pop()

    # =====================================================
    # PLAYBACK
    # =====================================================

    def playback_sleep_until(self, target_time):

        while self.playing:
            remaining = target_time - time.perf_counter()

            if remaining <= 0:
                return True

            time.sleep(min(remaining, 0.005))

        return False

    def get_recorded_duration(self):

        if self.recorded_duration:
            return self.recorded_duration

        if not self.recorded_events:
            return 0

        return max(
            event.get("time", 0)
            for event in self.recorded_events
        )

    def get_playback_events(self):

        return [
            event
            for event in self.recorded_events
            if event.get("type") not in {"recording_end", "hotkey_stop"}
        ]

    def playback(self):

        if not self.recorded_events:

            messagebox.showwarning(
                "Warning",
                "No macro recorded.",
                parent=self.root
            )

            self.stop_playback()
            return

        loop_text = self.loop_entry.get().strip()

        try:
            total_loops = (
                int(loop_text)
                if loop_text else float("inf")
            )

        except ValueError:
            total_loops = float("inf")

        current_loop = 1
        playback_events = self.get_playback_events()
        recorded_duration = self.get_recorded_duration()

        while self.playing and current_loop <= total_loops:

            self.loop_label.config(
                text=f"Loop: {current_loop}/"
                    f"{'∞' if total_loops == float('inf') else total_loops}"
            )

            loop_start_time = time.perf_counter()

            for event in playback_events:

                if not self.playing:
                    break

                target_time = loop_start_time + event["time"]

                if not self.playback_sleep_until(target_time):
                    break

                self.execute_event(event)

            if self.playing:
                self.playback_sleep_until(loop_start_time + recorded_duration)

            current_loop += 1

        self.stop_playback()

    # =====================================================
    # EVENT EXECUTION
    # =====================================================

    def execute_event(self, event):

        event_type = event["type"]
        data = event["data"]

        # =================================================
        # KEYBOARD
        # =================================================

        if event_type == "key_down":

            send_key(
                data["scan"],
                data.get("extended", False),
                False
            )

        elif event_type == "key_up":

            send_key(
                data["scan"],
                data.get("extended", False),
                True
            )

        # =================================================
        # MOUSE MOVE
        # =================================================

        elif event_type == "move":

            mouse_move(data["x"], data["y"])

        # =================================================
        # MOUSE BUTTONS
        # =================================================

        elif event_type == "mouse_down":

            button = data["button"]

            x = data["x"]
            y = data["y"]

            if "left" in button:
                mouse_left_down(x, y)

            elif "right" in button:
                mouse_right_down(x, y)

            elif "middle" in button:
                mouse_middle_down(x, y)

        elif event_type == "mouse_up":

            button = data["button"]

            x = data["x"]
            y = data["y"]

            if "left" in button:
                mouse_left_up(x, y)

            elif "right" in button:
                mouse_right_up(x, y)

            elif "middle" in button:
                mouse_middle_up(x, y)

        # =================================================
        # SCROLL
        # =================================================

        elif event_type == "scroll":

            mouse_scroll(int(data["dy"] * 120))

        elif event_type == "recording_end":
            pass

    # =====================================================
    # UI ACTIONS
    # =====================================================

    def set_status(self, text, state="idle"):

        colors = {
            "idle": "#172033",
            "recording": "#b42318",
            "playing": "#067647",
            "warning": "#b54708"
        }

        if hasattr(self, "status_label"):
            self.status_label.config(
                text=text,
                fg=colors.get(state, colors["idle"])
            )

        if hasattr(self, "status_bar"):
            bar_colors = {
                "idle": "#d7dfeb",
                "recording": "#f04438",
                "playing": "#12b76a",
                "warning": "#f79009"
            }

            self.status_bar.config(bg=bar_colors.get(state, "#d7dfeb"))

    def refresh_macro_summary(self):

        if not hasattr(self, "macro_summary_label"):
            return

        event_count = len(self.get_playback_events())
        duration = self.get_recorded_duration()

        self.macro_summary_label.config(
            text=f"{event_count} events / {duration:.1f}s duration"
        )

    def update_recording_ui_stopped(self):

        if hasattr(self, "record_button"):
            self.record_button.config(
                text="Record Macro",
                bg=self.COLORS["blue"],
                activebackground=self.COLORS["blue_hover"]
            )
            self.record_button.default_bg = self.COLORS["blue"]
            self.record_button.hover_bg = self.COLORS["blue_hover"]

        if hasattr(self, "play_button"):
            self.play_button.config(state="normal")

        self.set_status("Idle", "idle")
        self.refresh_macro_summary()

    def toggle_recording(self):

        if self.playing and not self.recording:
            self.set_status("Stop playback before recording", "warning")
            return

        if not self.recording:

            self.recording = True

            self.record_button.config(text="⏹ Stop")

            self.status_label.config(
                text="● Recording",
                fg="red"
            )

            threading.Thread(
                target=self.start_recording,
                daemon=True
            ).start()

        else:

            self.stop_recording()

            self.record_button.config(text="▶️ Record")

            self.status_label.config(
                text="Idle",
                fg="black"
            )

    def toggle_playback(self):

        if self.recording and not self.playing:
            self.set_status("Stop recording before playback", "warning")
            return

        self.playing = not self.playing

        if self.playing:

            self.play_button.config(text="⏹ Stop")

            self.status_label.config(
                text="▶ Playing",
                fg="green"
            )

            threading.Thread(
                target=self.playback,
                daemon=True
            ).start()

        else:
            self.stop_playback()

    def stop_playback(self):

        self.playing = False

        self.play_button.config(text="▶️ Play")

        self.status_label.config(
            text="Idle",
            fg="black"
        )

        self.loop_label.config(text="Loop: Done")

    def toggle_recording(self):

        if self.playing and not self.recording:
            self.set_status("Stop playback before recording", "warning")
            return

        if not self.recording:

            self.recording = True

            self.record_button.config(
                text="Stop Recording",
                bg=self.COLORS["red"],
                activebackground=self.COLORS["red_hover"]
            )
            self.record_button.default_bg = self.COLORS["red"]
            self.record_button.hover_bg = self.COLORS["red_hover"]

            self.play_button.config(state="disabled")

            self.set_status("Recording input", "recording")

            threading.Thread(
                target=self.start_recording,
                daemon=True
            ).start()

        else:

            self.stop_recording()

            self.record_button.config(
                text="Record Macro",
                bg=self.COLORS["blue"],
                activebackground=self.COLORS["blue_hover"]
            )
            self.record_button.default_bg = self.COLORS["blue"]
            self.record_button.hover_bg = self.COLORS["blue_hover"]

            self.play_button.config(state="normal")

            self.set_status("Idle", "idle")

            self.refresh_macro_summary()

    def toggle_playback(self):

        if self.recording and not self.playing:
            self.set_status("Stop recording before playback", "warning")
            return

        self.playing = not self.playing

        if self.playing:

            self.play_button.config(
                text="Stop Playback",
                bg=self.COLORS["red"],
                activebackground=self.COLORS["red_hover"]
            )
            self.play_button.default_bg = self.COLORS["red"]
            self.play_button.hover_bg = self.COLORS["red_hover"]

            self.record_button.config(state="disabled")

            self.set_status("Playing macro", "playing")

            threading.Thread(
                target=self.playback,
                daemon=True
            ).start()

        else:
            self.stop_playback()

    def stop_playback(self):

        self.playing = False

        self.play_button.config(
            text="Play Macro",
            bg=self.COLORS["green"],
            activebackground=self.COLORS["green_hover"],
            state="normal"
        )
        self.play_button.default_bg = self.COLORS["green"]
        self.play_button.hover_bg = self.COLORS["green_hover"]

        if hasattr(self, "record_button"):
            self.record_button.config(state="normal")

        self.set_status("Idle", "idle")

        self.loop_label.config(text="Loop: Done")

    # =====================================================
    # LOCAL FORMATTER BRIDGE
    # =====================================================

    def get_session_status(self):

        duration = self.get_recorded_duration()

        if self.recording and self.recording_start_time:
            duration = time.perf_counter() - self.recording_start_time

        if self.recording:
            state = "recording"
        elif self.playing:
            state = "playing"
        elif self.recorded_events:
            state = "ready"
        else:
            state = "idle"

        return {
            "ok": True,
            "state": state,
            "recording": self.recording,
            "playing": self.playing,
            "events": len(self.get_playback_events()),
            "duration": duration,
            "record_hotkey": self.settings["record_hotkey"],
            "playback_hotkey": self.settings["playback_hotkey"],
            "macros": self.get_recent_macros()
        }

    def run_on_ui_thread(self, callback):

        if hasattr(self, "root"):
            self.root.after(0, callback)

    def handle_control_command(self, action, params=None):

        params = params or {}

        def command():
            if action == "record":
                if not self.recording:
                    self.toggle_recording()

            elif action == "stop-record":
                if self.recording:
                    self.stop_recording()
                    self.update_recording_ui_stopped()

            elif action == "play":
                if not self.playing:
                    self.toggle_playback()

            elif action == "stop-play":
                if self.playing:
                    self.stop_playback()

            elif action == "stop":
                self.stop_recording()
                self.stop_playback()

                if not self.recording:
                    self.update_recording_ui_stopped()

            elif action == "load-macro":
                try:
                    index = int(params.get("index", ["-1"])[0])
                except ValueError:
                    index = -1

                self.load_recent_macro(index)

        self.run_on_ui_thread(command)

    def start_control_server(self):

        app = self

        class ControlHandler(BaseHTTPRequestHandler):

            def send_json(self, payload, status=200):
                body = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.end_headers()
                self.wfile.write(body)

            def do_OPTIONS(self):
                self.send_response(204)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.end_headers()

            def do_GET(self):
                parsed = urlparse(self.path)
                path = parsed.path.strip("/")
                params = parse_qs(parsed.query)

                if path in {"", "status"}:
                    self.send_json(app.get_session_status())
                    return

                if path.startswith("command/"):
                    action = path.split("/", 1)[1]

                    if action not in {
                        "record",
                        "stop-record",
                        "play",
                        "stop-play",
                        "stop",
                        "load-macro"
                    }:
                        self.send_json(
                            {"ok": False, "error": "Unknown command"},
                            404
                        )
                        return

                    app.handle_control_command(action, params)
                    self.send_json(app.get_session_status())
                    return

                self.send_json({"ok": False, "error": "Not found"}, 404)

            def log_message(self, _format, *_args):
                return

        try:
            server = ThreadingHTTPServer(
                (CONTROL_HOST, CONTROL_PORT),
                ControlHandler
            )

        except OSError:
            self.set_status("Formatter bridge already running", "warning")
            return

        thread = threading.Thread(
            target=server.serve_forever,
            daemon=True
        )
        thread.start()
        self.control_server = server

    # =====================================================
    # SAVE / LOAD
    # =====================================================

    def save_macro(self):

        if not self.recorded_events:

            messagebox.showwarning(
                "Warning",
                "No macro recorded.",
                parent=self.root
            )

            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            parent=self.root
        )

        if filename:

            with open(filename, "w") as f:

                json.dump({
                    "version": 3,
                    "events": self.recorded_events,
                    "duration": self.get_recorded_duration()
                }, f, indent=4)

            self.register_macro_file(filename)
            self.set_status("Macro saved", "idle")

    def load_macro(self):

        filename = filedialog.askopenfilename(
            filetypes=[("JSON Files", "*.json")],
            parent=self.root
        )

        if not filename:
            return

        with open(filename, "r") as f:

            data = json.load(f)

            self.recorded_events = data["events"]
            self.recorded_duration = 0
            self.recorded_duration = data.get(
                "duration",
                self.get_recorded_duration()
            )

        self.register_macro_file(filename)
        self.refresh_macro_summary()
        self.set_status("Macro loaded", "idle")

    def load_recent_macro(self, index):

        recent_macros = self.settings.get("recent_macros", [])

        if index < 0 or index >= len(recent_macros):
            return False

        filename = recent_macros[index]

        if not os.path.exists(filename):
            return False

        with open(filename, "r") as f:
            data = json.load(f)

        self.recorded_events = data["events"]
        self.recorded_duration = 0
        self.recorded_duration = data.get(
            "duration",
            self.get_recorded_duration()
        )

        self.register_macro_file(filename)
        self.refresh_macro_summary()
        self.set_status("Macro loaded", "idle")
        return True

    # =====================================================
    # HOTKEYS
    # =====================================================

    def global_key_press(self, key):

        self.current_keys.add(self.normalize_hotkey_key(key))

        # ESC = emergency stop
        if key == keyboard.Key.esc:

            self.stop_recording()
            self.stop_playback()
            return

        now = time.time()

        if now - self.last_hotkey_time < 0.5:
            return

        if all(
            k in self.current_keys
            for k in self.parse_hotkey_match(
                self.settings["record_hotkey"]
            )
        ):

            self.last_hotkey_time = now

            if self.recording:
                self.stop_recording(stopped_by_hotkey=True)
                self.update_recording_ui_stopped()
                return

            self.toggle_recording()

        if all(
            k in self.current_keys
            for k in self.parse_hotkey_match(
                self.settings["playback_hotkey"]
            )
        ):

            self.last_hotkey_time = now
            self.toggle_playback()

    def global_key_release(self, key):

        self.current_keys.discard(self.normalize_hotkey_key(key))

    def start_hotkey_listener(self):

        self.hotkey_listener = keyboard.Listener(
            on_press=self.global_key_press,
            on_release=self.global_key_release
        )

        self.hotkey_listener.daemon = True
        self.hotkey_listener.start()

    # =====================================================
    # SETTINGS WINDOW
    # =====================================================

    def update_hotkey_label(self):

        if hasattr(self, "hotkey_label"):
            self.hotkey_label.config(
                text=(
                    f"Record: {self.settings['record_hotkey']}    "
                    f"Play: {self.settings['playback_hotkey']}"
                )
            )

    def validate_hotkey_text(self, hotkey):

        parts = [part.strip() for part in hotkey.lower().split("+")]

        if not hotkey.strip() or any(not part for part in parts):
            return False

        try:
            self.parse_hotkey(hotkey)
        except Exception:
            return False

        return True

    def open_settings(self):

        if hasattr(self, "settings_window") and self.settings_window.winfo_exists():
            self.settings_window.lift()
            self.settings_window.focus_force()
            return

        colors = self.COLORS

        window = tk.Toplevel(self.root)
        self.settings_window = window
        window.title("Settings")
        window.configure(bg=colors["window"])
        window.resizable(False, False)
        window.transient(self.root)
        window.grab_set()
        apply_window_icon(window)

        panel = tk.Frame(
            window,
            bg=colors["panel"],
            padx=18,
            pady=16,
            highlightbackground=colors["border"],
            highlightthickness=1
        )
        panel.pack(padx=18, pady=18)

        tk.Label(
            panel,
            text="Settings",
            bg=colors["panel"],
            fg=colors["text"],
            font=("Segoe UI", 15, "bold")
        ).pack(anchor="w")

        tk.Label(
            panel,
            text="Customize the global hotkeys used by TinyTask.",
            bg=colors["panel"],
            fg=colors["muted"],
            font=("Segoe UI", 9)
        ).pack(anchor="w", pady=(2, 14))

        form = tk.Frame(panel, bg=colors["panel"])
        form.pack(fill="x")

        def add_hotkey_row(label_text, initial_value):
            row = tk.Frame(form, bg=colors["panel"])
            row.pack(fill="x", pady=(0, 10))

            tk.Label(
                row,
                text=label_text,
                bg=colors["panel"],
                fg="#344256",
                font=("Segoe UI", 9, "bold"),
                width=13,
                anchor="w"
            ).pack(side="left")

            entry = tk.Entry(
                row,
                width=22,
                relief="solid",
                bd=1,
                bg=colors["panel_alt"],
                fg=colors["text"],
                insertbackground=colors["text"],
                highlightthickness=1,
                highlightbackground=colors["border"],
                highlightcolor=colors["blue"],
                font=("Segoe UI", 10)
            )
            entry.insert(0, initial_value)
            entry.pack(side="left", fill="x", expand=True)
            return entry

        record_entry = add_hotkey_row(
            "Record",
            self.settings["record_hotkey"]
        )
        playback_entry = add_hotkey_row(
            "Playback",
            self.settings["playback_hotkey"]
        )

        hint_label = tk.Label(
            panel,
            text="Use plus signs, for example ctrl+alt+r.",
            bg=colors["panel_alt"],
            fg=colors["muted"],
            padx=10,
            pady=8,
            anchor="w",
            font=("Segoe UI", 9),
            highlightbackground=colors["border"],
            highlightthickness=1
        )
        hint_label.pack(fill="x", pady=(2, 12))

        button_frame = tk.Frame(panel, bg=colors["panel"])
        button_frame.pack(fill="x")

        def save_hotkeys():
            record_hotkey = record_entry.get().strip().lower()
            playback_hotkey = playback_entry.get().strip().lower()

            if not self.validate_hotkey_text(record_hotkey):
                messagebox.showwarning(
                    "Invalid Hotkey",
                    "Record hotkey must look like ctrl+alt+r.",
                    parent=window
                )
                record_entry.focus_set()
                return

            if not self.validate_hotkey_text(playback_hotkey):
                messagebox.showwarning(
                    "Invalid Hotkey",
                    "Playback hotkey must look like ctrl+alt+p.",
                    parent=window
                )
                playback_entry.focus_set()
                return

            self.settings["record_hotkey"] = record_hotkey
            self.settings["playback_hotkey"] = playback_hotkey
            self.save_settings()
            self.update_hotkey_label()
            self.set_status("Settings saved", "idle")
            window.destroy()

        self.create_button(
            button_frame,
            text="Save Settings",
            command=save_hotkeys,
            bg=colors["blue"],
            hover_bg=colors["blue_hover"],
            fg="#ffffff",
            width=15,
            side="left",
            padx=(0, 8)
        )

        self.create_button(
            button_frame,
            text="Cancel",
            command=window.destroy,
            width=12,
            side="left"
        )

        window.bind("<Return>", lambda _event: save_hotkeys())
        window.bind("<Escape>", lambda _event: window.destroy())

        window.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() // 2) - (window.winfo_width() // 2)
        y = self.root.winfo_rooty() + (self.root.winfo_height() // 2) - (window.winfo_height() // 2)
        window.geometry(f"+{max(0, x)}+{max(0, y)}")
        record_entry.focus_set()
    # =====================================================
    # UI
    # =====================================================

    def build_legacy_ui(self):

        self.root = tk.Tk()

        self.root.title("IMS TinyTask")
        apply_window_icon(self.root)

        self.root.resizable(False, False)

        container = tk.Frame(
            self.root,
            padx=10,
            pady=10
        )

        container.pack()

        self.status_label = tk.Label(
            container,
            text="Idle",
            font=("Arial", 12)
        )

        self.status_label.pack(pady=5)

        button_frame = tk.Frame(container)
        button_frame.pack(pady=5)

        self.record_button = tk.Button(
            button_frame,
            text="▶️ Record",
            width=12,
            command=self.toggle_recording
        )

        self.record_button.pack(side="left", padx=5)

        self.play_button = tk.Button(
            button_frame,
            text="▶️ Play",
            width=12,
            command=self.toggle_playback
        )

        self.play_button.pack(side="left", padx=5)

        tk.Label(
            container,
            text="Loop Count (blank = infinite)"
        ).pack()

        self.loop_entry = tk.Entry(
            container,
            width=10,
            justify="center"
        )

        self.loop_entry.pack(pady=3)

        self.loop_label = tk.Label(
            container,
            text="Loop: 0/0"
        )

        self.loop_label.pack(pady=3)

        tk.Button(
            container,
            text="💾 Save Macro",
            width=20,
            command=self.save_macro
        ).pack(pady=5)

        tk.Button(
            container,
            text="📂 Load Macro",
            width=20,
            command=self.load_macro
        ).pack(pady=5)

        tk.Button(
            container,
            text="⚙️ Settings",
            width=20,
            command=self.open_settings
        ).pack(pady=5)

    def create_button(
        self,
        parent,
        text,
        command,
        bg=None,
        hover_bg=None,
        fg=None,
        width=None,
        fill=None,
        side=None,
        padx=0,
        pady=0
    ):

        colors = self.COLORS
        bg = bg or colors["panel"]
        hover_bg = hover_bg or "#eef5ff"
        fg = fg or colors["text"]

        button = tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=hover_bg,
            activeforeground=fg,
            disabledforeground="#98a2b3",
            relief="solid" if bg == colors["panel"] else "flat",
            bd=1 if bg == colors["panel"] else 0,
            highlightthickness=0,
            width=width,
            padx=10,
            pady=8,
            cursor="hand2",
            font=("Segoe UI", 9, "bold")
        )

        button.default_bg = bg
        button.hover_bg = hover_bg

        def on_enter(_event):
            if button["state"] == "normal":
                button.config(bg=button.hover_bg)

        def on_leave(_event):
            if button["state"] == "normal":
                button.config(bg=button.default_bg)

        button.bind("<Enter>", on_enter)
        button.bind("<Leave>", on_leave)
        button.pack(fill=fill, side=side, padx=padx, pady=pady)

        return button

    def create_label(self, parent, text, size=9, weight="normal", color=None, bg=None):

        colors = self.COLORS

        return tk.Label(
            parent,
            text=text,
            bg=bg or colors["panel"],
            fg=color or colors["text"],
            font=("Segoe UI", size, weight)
        )

    def build_ui(self):

        self.root = tk.Tk()
        self.root.title("IMS TinyTask")
        apply_window_icon(self.root)

        self.root.resizable(False, False)
        self.root.configure(bg=self.COLORS["window"])

        container = tk.Frame(
            self.root,
            bg=self.COLORS["window"],
            padx=20,
            pady=18
        )

        container.pack()

        tk.Label(
            container,
            text="IMS TinyTask",
            bg=self.COLORS["window"],
            fg=self.COLORS["text"],
            font=("Segoe UI", 17, "bold")
        ).pack(anchor="w")

        tk.Label(
            container,
            text="Record and replay Windows input macros",
            bg=self.COLORS["window"],
            fg=self.COLORS["muted"],
            font=("Segoe UI", 9)
        ).pack(anchor="w", pady=(2, 14))

        card = tk.Frame(
            container,
            bg=self.COLORS["panel"],
            padx=16,
            pady=16,
            highlightbackground=self.COLORS["border"],
            highlightthickness=1
        )

        card.pack(fill="x")

        status_frame = tk.Frame(card, bg=self.COLORS["panel"])
        status_frame.pack(fill="x", pady=(0, 14))

        self.status_bar = tk.Frame(
            status_frame,
            bg=self.COLORS["border"],
            width=5,
            height=44
        )

        self.status_bar.pack(side="left", fill="y", padx=(0, 10))
        self.status_bar.pack_propagate(False)

        status_text_frame = tk.Frame(status_frame, bg=self.COLORS["panel"])
        status_text_frame.pack(side="left", fill="x", expand=True)

        self.status_label = tk.Label(
            status_text_frame,
            text="Idle",
            bg=self.COLORS["panel"],
            fg=self.COLORS["text"],
            font=("Segoe UI", 14, "bold")
        )

        self.status_label.pack(anchor="w")

        self.hotkey_label = tk.Label(
            status_text_frame,
            text=(
                f"Record: {self.settings['record_hotkey']}    "
                f"Play: {self.settings['playback_hotkey']}"
            ),
            bg=self.COLORS["panel"],
            fg=self.COLORS["muted"],
            font=("Segoe UI", 9)
        )

        self.hotkey_label.pack(anchor="w", pady=(2, 0))

        button_frame = tk.Frame(
            card,
            bg=self.COLORS["panel"]
        )

        button_frame.pack(fill="x", pady=(0, 12))

        self.record_button = self.create_button(
            button_frame,
            text="Record Macro",
            command=self.toggle_recording,
            bg=self.COLORS["blue"],
            hover_bg=self.COLORS["blue_hover"],
            fg="#ffffff",
            width=16,
            side="left",
            padx=(0, 8)
        )

        self.play_button = self.create_button(
            button_frame,
            text="Play Macro",
            command=self.toggle_playback,
            bg=self.COLORS["green"],
            hover_bg=self.COLORS["green_hover"],
            fg="#ffffff",
            width=16,
            side="left"
        )

        self.create_label(
            card,
            text="Loop count",
            weight="bold",
            color="#344256"
        ).pack(anchor="w")

        loop_frame = tk.Frame(
            card,
            bg=self.COLORS["panel"]
        )

        loop_frame.pack(fill="x", pady=(4, 8))

        self.loop_entry = tk.Entry(
            loop_frame,
            width=12,
            justify="center",
            relief="solid",
            bd=1,
            bg=self.COLORS["panel_alt"],
            fg=self.COLORS["text"],
            insertbackground=self.COLORS["text"],
            highlightthickness=1,
            highlightbackground=self.COLORS["border"],
            highlightcolor=self.COLORS["blue"],
            font=("Segoe UI", 11)
        )

        self.loop_entry.pack(side="left")

        tk.Label(
            loop_frame,
            text="Blank means infinite",
            bg=self.COLORS["panel"],
            fg=self.COLORS["muted"],
            font=("Segoe UI", 9)
        ).pack(side="left", padx=(10, 0))

        self.loop_label = tk.Label(
            card,
            text="Loop: 0/0",
            bg=self.COLORS["panel"],
            fg=self.COLORS["muted"],
            font=("Segoe UI", 9)
        )

        self.loop_label.pack(anchor="w", pady=(0, 10))

        self.macro_summary_label = tk.Label(
            card,
            text="0 events / 0.0s duration",
            bg=self.COLORS["panel_alt"],
            fg="#344256",
            padx=10,
            pady=8,
            anchor="w",
            font=("Segoe UI", 9, "bold"),
            highlightbackground=self.COLORS["border"],
            highlightthickness=1
        )

        self.macro_summary_label.pack(fill="x", pady=(0, 12))

        file_frame = tk.Frame(
            card,
            bg=self.COLORS["panel"]
        )

        file_frame.pack(fill="x")

        self.create_button(
            file_frame,
            text="Save Macro",
            command=self.save_macro,
            width=15,
            side="left",
            padx=(0, 8)
        )

        self.create_button(
            file_frame,
            text="Load Macro",
            command=self.load_macro,
            width=15,
            side="left"
        )

        self.create_button(
            card,
            text="Settings",
            command=self.open_settings,
            fill="x",
            pady=(10, 0)
        )

        self.refresh_macro_summary()

    # =====================================================
    # RUN
    # =====================================================

    def run(self):
        self.root.mainloop()


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    set_windows_app_id()
    app = MacroApp()
    app.run()
