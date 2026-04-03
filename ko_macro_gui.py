"""
Knight Online - Assassin Rogue Gelismis Makro  v3.0
Kozy / MRX tarzı — DirectInput (ctypes SendInput) tabanlı

Kurulum:
    pip install pillow opencv-python numpy keyboard

Kullanim:
    python ko_macro_gui.py
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import cv2
import numpy as np
import keyboard
import threading
import time
import json
import os
import ctypes
from ctypes import wintypes

# ─── DirectInput sabitleri ────────────────────────────────────────────────────
INPUT_MOUSE           = 0
INPUT_KEYBOARD        = 1
KEYEVENTF_SCANCODE    = 0x0008
KEYEVENTF_KEYUP       = 0x0002
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP   = 0x0010

# Klavye scan code tablosu (DirectInput)
SCAN = {
    "f1":  0x3B, "f2": 0x3C, "f3": 0x3D, "f4": 0x3E, "f5": 0x3F,
    "f6":  0x40, "f7": 0x41, "f8": 0x42, "f9": 0x43, "f10": 0x44,
    "1":   0x02, "2":  0x03, "3":  0x04, "4":  0x05, "5":  0x06,
    "6":   0x07, "7":  0x08, "8":  0x09, "9":  0x0A, "0":  0x0B,
    "a":   0x1E, "b":  0x30, "c":  0x2E, "d":  0x20, "e":  0x12,
    "r":   0x13, "t":  0x14, "y":  0x15, "u":  0x16, "z":  0x2C,
    "x":   0x2D, "v":  0x2F, "q":  0x10, "w":  0x11, "s":  0x1F,
    "num1":0x4F, "num2":0x50,"num3":0x51,"num4":0x4B,"num5":0x4C,
    "num6":0x4D, "num7":0x47,"num8":0x48,"num9":0x49,"num0":0x52,
}

# ── Doğru ctypes yapıları (Union ile — 32/64 bit uyumlu) ──────────────────────
class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx",          wintypes.LONG),
                ("dy",          wintypes.LONG),
                ("mouseData",   wintypes.DWORD),
                ("dwFlags",     wintypes.DWORD),
                ("time",        wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]

class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk",         wintypes.WORD),
                ("wScan",       wintypes.WORD),
                ("dwFlags",     wintypes.DWORD),
                ("time",        wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]

class _INPUT_UNION(ctypes.Union):
    _fields_ = [("mi", _MOUSEINPUT),
                ("ki", _KEYBDINPUT)]

class _INPUT(ctypes.Structure):
    _fields_ = [("type",   wintypes.DWORD),
                ("_input", _INPUT_UNION)]

_SendInput = ctypes.windll.user32.SendInput

def press_key(key: str, hold: float = 0.04):
    """DirectInput scan code ile tuşa bas + bırak."""
    sc = SCAN.get(key.lower())
    if sc is None:
        return
    extra = ctypes.c_ulong(0)
    for key_up in (False, True):
        flags = KEYEVENTF_SCANCODE | (KEYEVENTF_KEYUP if key_up else 0)
        ki  = _KEYBDINPUT(0, sc, flags, 0, ctypes.pointer(extra))
        inp = _INPUT(INPUT_KEYBOARD, _INPUT_UNION(ki=ki))
        _SendInput(1, ctypes.byref(inp), ctypes.sizeof(_INPUT))
        if not key_up:
            time.sleep(hold)

def right_click():
    """DirectInput sağ tık (SendInput)."""
    extra = ctypes.c_ulong(0)
    for flags in (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP):
        mi  = _MOUSEINPUT(0, 0, 0, flags, 0, ctypes.pointer(extra))
        inp = _INPUT(INPUT_MOUSE, _INPUT_UNION(mi=mi))
        _SendInput(1, ctypes.byref(inp), ctypes.sizeof(_INPUT))
        time.sleep(0.01)

# ─── Sabitleri ────────────────────────────────────────────────────────────────
import pyautogui  # sadece screenshot için
pyautogui.FAILSAFE = False
pyautogui.PAUSE    = 0

BARS        = ["F1", "F2", "F3", "F4", "F5"]
SLOTS       = 5          # Slot 3-7
SLOT_START  = 3
CONFIG_FILE = "ko_macro_config.json"
SPAM_KEYS   = ["8", "9", "0"]

BG          = "#12121c"
CARD        = "#1e1e2e"
CARD2       = "#252538"
ACCENT      = "#7c3aed"
GREEN       = "#16a34a"
RED         = "#dc2626"
FG          = "#e2e8f0"
MUTED       = "#64748b"
SLOT_EMPTY  = "#1a1a2e"
SLOT_FILLED = "#1a3020"


# ─────────────────────────────────────────────────────────────────────────────

class MacroApp:

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("KO Rogue Makro  v3.0  [DirectInput]")
        self.root.geometry("1060x660")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)

        # Slot verisi
        self.slot_paths     = {b: [None] * SLOTS for b in BARS}
        self.slot_templates = {b: [None] * SLOTS for b in BARS}
        self.slot_btns      = {b: []             for b in BARS}
        self.slot_lbls      = {b: []             for b in BARS}

        # Ayarlar
        self.act_key      = tk.StringVar(value="z")
        self.stop_key     = tk.StringVar(value="insert")
        self.minor_key    = tk.StringVar(value="2")      # minor/hp pot tuşu
        self.minor_sec    = tk.DoubleVar(value=3.5)      # kaç saniyede bir
        self.minor_on     = tk.BooleanVar(value=True)    # minor aktif mi
        self.confidence   = tk.DoubleVar(value=0.82)
        self.status_var   = tk.StringVar(value="Durduruldu")

        # Durum
        self.active     = False
        self.stop_ev    = threading.Event()
        self._last_minor = 0.0

        self._build_ui()
        self._load_config()
        self._register_stop_hotkey()

    # ─── UI ──────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Başlık
        hdr = tk.Frame(self.root, bg=ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="⚔  KO Rogue Makro  —  DirectInput",
                 font=("Segoe UI", 13, "bold"), bg=ACCENT, fg="white"
                 ).pack(side="left", padx=16, pady=10)
        self.status_lbl = tk.Label(hdr, textvariable=self.status_var,
                                   font=("Segoe UI", 10), bg=ACCENT, fg="#d4c0ff")
        self.status_lbl.pack(side="right", padx=16)

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=10, pady=8)

        # Sol: skill barları
        left = tk.Frame(body, bg=BG)
        left.pack(side="left", fill="both", expand=True)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("T.TNotebook",     background=BG,    borderwidth=0)
        style.configure("T.TNotebook.Tab", background=CARD2, foreground=FG,
                        font=("Segoe UI", 10, "bold"), padding=[14, 5])
        style.map("T.TNotebook.Tab",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", "white")])

        nb = ttk.Notebook(left, style="T.TNotebook")
        nb.pack(fill="both", expand=True)

        for bar in BARS:
            tab = tk.Frame(nb, bg=CARD, padx=10, pady=10)
            nb.add(tab, text=f"  {bar}  ")

            tk.Label(tab,
                     text=f"{bar} Barı  —  Slot 3-7 skill resimleri  "
                          f"(1=light feet, 2=minor — atlandı)",
                     font=("Segoe UI", 9), bg=CARD, fg=MUTED
                     ).pack(anchor="w", pady=(0, 8))

            row = tk.Frame(tab, bg=CARD)
            row.pack()

            for i in range(SLOTS):
                slot_num = SLOT_START + i
                cell = tk.Frame(row, bg=CARD, padx=4)
                cell.grid(row=0, column=i)

                btn = tk.Button(
                    cell,
                    text=f"＋\nSlot {slot_num}",
                    width=9, height=5,
                    bg=SLOT_EMPTY, fg="#5555aa",
                    font=("Segoe UI", 8), relief="flat", cursor="hand2",
                    activebackground="#252545",
                    command=lambda b=bar, idx=i: self._pick_image(b, idx)
                )
                btn.pack()
                self.slot_btns[bar].append(btn)

                lbl = tk.Label(cell, text="boş", bg=CARD,
                               fg="#383860", font=("Segoe UI", 7))
                lbl.pack()
                self.slot_lbls[bar].append(lbl)

            tk.Button(tab, text="🗑  Barı Temizle",
                      bg="#2a1a1a", fg="#cc6666",
                      font=("Segoe UI", 8), relief="flat", cursor="hand2",
                      command=lambda b=bar: self._clear_bar(b)
                      ).pack(anchor="w", pady=(10, 0))

        # Sağ: ayar paneli
        right = tk.Frame(body, bg=CARD, width=220, padx=14, pady=12)
        right.pack(side="right", fill="y", padx=(10, 0))
        right.pack_propagate(False)

        def sep():
            tk.Frame(right, bg="#2a2a3e", height=1).pack(fill="x", pady=5)

        def sec(text):
            tk.Label(right, text=text, font=("Segoe UI", 8, "bold"),
                     bg=CARD, fg=ACCENT).pack(anchor="w", pady=(6, 2))

        # ── Minor heal ──
        sec("Minor / HP Pot")
        minor_row = tk.Frame(right, bg=CARD)
        minor_row.pack(fill="x")
        tk.Checkbutton(minor_row, variable=self.minor_on, text="Aktif",
                       bg=CARD, fg=FG, selectcolor=CARD2,
                       activebackground=CARD, font=("Segoe UI", 8)
                       ).pack(side="left")
        tk.Entry(minor_row, textvariable=self.minor_key,
                 width=4, font=("Segoe UI", 11, "bold"),
                 bg=CARD2, fg="#86efac", insertbackground=FG,
                 justify="center", relief="flat"
                 ).pack(side="left", padx=4)
        tk.Label(minor_row, text="tuşu", bg=CARD, fg=MUTED,
                 font=("Segoe UI", 8)).pack(side="left")

        minor_sec_row = tk.Frame(right, bg=CARD)
        minor_sec_row.pack(fill="x", pady=2)
        tk.Label(minor_sec_row, text="Her  ", bg=CARD, fg=MUTED,
                 font=("Segoe UI", 8)).pack(side="left")
        tk.Spinbox(minor_sec_row, from_=0.5, to=30.0, increment=0.5,
                   textvariable=self.minor_sec,
                   width=5, font=("Segoe UI", 10),
                   bg=CARD2, fg=FG, buttonbackground=CARD2,
                   relief="flat"
                   ).pack(side="left")
        tk.Label(minor_sec_row, text=" sn'de bir", bg=CARD, fg=MUTED,
                 font=("Segoe UI", 8)).pack(side="left")

        sep()
        # ── Aktivasyon tuşu ──
        sec("Aktivasyon Tuşu  (basılı tut → skill)")
        ak_row = tk.Frame(right, bg=CARD)
        ak_row.pack(fill="x")
        tk.Entry(ak_row, textvariable=self.act_key,
                 width=5, font=("Segoe UI", 13, "bold"),
                 bg=CARD2, fg=FG, insertbackground=FG,
                 justify="center", relief="flat"
                 ).pack(side="left")
        tk.Label(ak_row, text=" basılı tut",
                 bg=CARD, fg=MUTED, font=("Segoe UI", 8)).pack(side="left")

        sep()
        # ── Durdurma tuşu ──
        sec("Acil Durdurma  (oyun içinden)")
        sk_row = tk.Frame(right, bg=CARD)
        sk_row.pack(fill="x")
        sk_entry = tk.Entry(sk_row, textvariable=self.stop_key,
                            width=9, font=("Segoe UI", 10, "bold"),
                            bg="#3a1a1a", fg="#ff8888",
                            insertbackground=FG, justify="center", relief="flat")
        sk_entry.pack(side="left")
        tk.Label(sk_row, text=" → DURDUR",
                 bg=CARD, fg=MUTED, font=("Segoe UI", 8)).pack(side="left")
        sk_entry.bind("<FocusOut>", lambda e: self._register_stop_hotkey())

        sep()
        # ── Hassasiyet ──
        sec("Eşleşme Hassasiyeti")
        tk.Scale(right, variable=self.confidence, from_=0.50, to=1.0,
                 resolution=0.01, orient="horizontal",
                 bg=CARD, fg=FG, troughcolor=CARD2,
                 highlightthickness=0, length=188
                 ).pack()
        self.conf_lbl = tk.Label(right, bg=CARD, fg=MUTED, font=("Segoe UI", 8))
        self.conf_lbl.pack()
        self.confidence.trace_add("write", self._update_conf_lbl)
        self._update_conf_lbl()

        sep()
        # ── Spam bilgisi ──
        tk.Label(right, text="Sürekli Spam (makro açıkken)",
                 bg=CARD, fg=ACCENT, font=("Segoe UI", 8, "bold")).pack(anchor="w")
        tk.Label(right, text="8  ·  9  ·  0  ·  Sağ Tık",
                 bg=CARD, fg="#9988cc", font=("Segoe UI", 10, "bold")
                 ).pack(anchor="w")

        sep()
        self.toggle_btn = tk.Button(
            right, text="▶   BAŞLAT",
            bg=GREEN, fg="white",
            font=("Segoe UI", 12, "bold"),
            relief="flat", cursor="hand2",
            width=16, height=2,
            activebackground="#15803d",
            command=self._toggle
        )
        self.toggle_btn.pack(pady=6, fill="x")

        tk.Button(right, text="💾  Kaydet",
                  bg=CARD2, fg="#86efac",
                  font=("Segoe UI", 9), relief="flat", cursor="hand2",
                  command=self._save_config
                  ).pack(fill="x", pady=2)

    def _update_conf_lbl(self, *_):
        self.conf_lbl.config(text=f"Hassasiyet: {self.confidence.get():.2f}")

    # ─── Resim seçme ─────────────────────────────────────────────────────────

    def _pick_image(self, bar, idx):
        path = filedialog.askopenfilename(
            title=f"{bar} Slot {SLOT_START+idx} — Skill Resmi Seç",
            filetypes=[("Resim", "*.png *.jpg *.jpeg *.bmp"), ("Tümü", "*.*")]
        )
        if path:
            self._load_slot(bar, idx, path)

    def _load_slot(self, bar: str, idx: int, path: str):
        try:
            pil = Image.open(path).convert("RGB")
            self.slot_paths[bar][idx] = path
            self.slot_templates[bar][idx] = cv2.cvtColor(
                np.array(pil), cv2.COLOR_RGB2BGR)
            thumb = pil.resize((64, 64), Image.LANCZOS)
            photo = ImageTk.PhotoImage(thumb)
            btn = self.slot_btns[bar][idx]
            btn.config(image=photo, text="", bg=SLOT_FILLED)
            btn.image = photo
            self.slot_lbls[bar][idx].config(
                text=os.path.basename(path)[:12], fg="#4ade80")
        except Exception as e:
            messagebox.showerror("Hata", f"Resim yüklenemedi:\n{e}")

    def _clear_bar(self, bar: str):
        for i in range(SLOTS):
            self.slot_paths[bar][i] = None
            self.slot_templates[bar][i] = None
            btn = self.slot_btns[bar][i]
            btn.config(image="", text=f"＋\nSlot {SLOT_START+i}",
                       bg=SLOT_EMPTY, fg="#5555aa")
            btn.image = None
            self.slot_lbls[bar][i].config(text="boş", fg="#383860")

    # ─── Makro aç/kapat ───────────────────────────────────────────────────────

    def _toggle(self):
        if not self.active:
            # Tkinter değişkenlerini MAIN THREAD'de oku, thread'e parametre olarak geç
            cfg = {
                "minor_on":   self.minor_on.get(),
                "minor_key":  self.minor_key.get().strip().lower(),
                "minor_sec":  float(self.minor_sec.get()),
                "act_key":    self.act_key.get().strip().lower(),
                "confidence": float(self.confidence.get()),
            }
            self.active = True
            self.stop_ev.clear()
            self._last_minor = 0.0
            self.toggle_btn.config(text="⏹   DURDUR", bg=RED,
                                   activebackground="#b91c1c")
            self._set_status("Aktif", "#a78bfa")
            threading.Thread(target=self._main_loop, args=(cfg,), daemon=True).start()
        else:
            self._do_stop()

    def _do_stop(self):
        self.active = False
        self.stop_ev.set()
        self.toggle_btn.config(text="▶   BAŞLAT", bg=GREEN,
                               activebackground="#15803d")
        self._set_status("Durduruldu", MUTED)

    def _set_status(self, text: str, color: str = FG):
        self.status_var.set(text)
        self.status_lbl.config(fg=color)

    def _register_stop_hotkey(self):
        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass
        sk = self.stop_key.get().strip().lower() or "insert"
        try:
            keyboard.add_hotkey(sk, lambda: self.root.after(0, self._emergency_stop))
        except Exception:
            pass

    def _emergency_stop(self):
        if self.active:
            self._do_stop()
            self._set_status("⛔ Durduruldu (acil)", "#f87171")

    # ─── Ana döngü ───────────────────────────────────────────────────────────

    def _main_loop(self, cfg: dict):
        """
        Sürekli çalışır (basılı tuş gerekmez):
          1. Spam : 8 · 9 · 0 · sağ tık
          2. Minor: her N saniyede bir
          3. Skill : aktivasyon tuşu basılıyken image match
        cfg: main thread'den alınan snapshot (thread-safe)
        """
        bar_key  = {"F1": "f1", "F2": "f2", "F3": "f3", "F4": "f4", "F5": "f5"}
        spam_idx = 0
        minor_on  = cfg["minor_on"]
        minor_key = cfg["minor_key"]
        minor_sec = cfg["minor_sec"]
        act_key   = cfg["act_key"]
        confidence= cfg["confidence"]

        while not self.stop_ev.is_set():
            now = time.time()

            # ── 1. Spam ──────────────────────────────────────────────────────
            press_key(SPAM_KEYS[spam_idx % len(SPAM_KEYS)], hold=0.02)
            spam_idx += 1
            right_click()

            # ── 2. Minor ─────────────────────────────────────────────────────
            if minor_on and minor_key and (now - self._last_minor >= minor_sec):
                press_key(minor_key, hold=0.04)
                self._last_minor = now
                self.root.after(0, self._set_status,
                               f"💊 Minor ({minor_key.upper()})", "#38bdf8")

            # ── 3. Skill (aktivasyon tuşu basılıyken) ────────────────────────
            try:
                ak_held = act_key and keyboard.is_pressed(act_key)
            except Exception:
                ak_held = False

            if ak_held:
                try:
                    screen_bgr = cv2.cvtColor(
                        np.array(pyautogui.screenshot()), cv2.COLOR_RGB2BGR)
                except Exception:
                    time.sleep(0.01)
                    continue

                skill_used = False
                for bar in BARS:
                    templates = [t for t in self.slot_templates[bar] if t is not None]
                    if not templates:
                        continue
                    hit = any(
                        cv2.minMaxLoc(cv2.matchTemplate(
                            screen_bgr, tmpl, cv2.TM_CCOEFF_NORMED))[1] >= confidence
                        for tmpl in templates
                        if tmpl.shape[0] <= screen_bgr.shape[0]
                        and tmpl.shape[1] <= screen_bgr.shape[1]
                    )
                    if hit:
                        fk = bar_key[bar]
                        press_key(fk, hold=0.03)
                        self.root.after(0, self._set_status,
                                       f"⚡ {bar} ({fk.upper()})", "#4ade80")
                        skill_used = True
                        break

                if not skill_used:
                    self.root.after(0, self._set_status,
                                   "⏳ Skill bekleniyor...", "#facc15")

            time.sleep(0.012)

    # ─── Kaydet / Yükle ───────────────────────────────────────────────────────

    def _save_config(self):
        cfg = {
            "activation_key": self.act_key.get(),
            "stop_key":       self.stop_key.get(),
            "minor_key":      self.minor_key.get(),
            "minor_sec":      self.minor_sec.get(),
            "minor_on":       self.minor_on.get(),
            "confidence":     self.confidence.get(),
            "slots":          {b: self.slot_paths[b] for b in BARS}
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        messagebox.showinfo("Kaydedildi", "Ayarlar kaydedildi.")

    def _load_config(self):
        if not os.path.exists(CONFIG_FILE):
            return
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            self.act_key.set(   cfg.get("activation_key", "z"))
            self.stop_key.set(  cfg.get("stop_key",        "insert"))
            self.minor_key.set( cfg.get("minor_key",       "2"))
            self.minor_sec.set( cfg.get("minor_sec",        3.5))
            self.minor_on.set(  cfg.get("minor_on",         True))
            self.confidence.set(cfg.get("confidence",       0.82))
            for bar in BARS:
                for i, path in enumerate(
                        cfg.get("slots", {}).get(bar, [None]*SLOTS)):
                    if path and os.path.exists(path):
                        self._load_slot(bar, i, path)
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    root = tk.Tk()
    app  = MacroApp(root)
    root.mainloop()
