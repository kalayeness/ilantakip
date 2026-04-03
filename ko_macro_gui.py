"""
Knight Online - Assassin Rogue Gelismis Makro
Kozy / MRX tarzı goruntu tanıma tabanlı skill makrosu

Kurulum:
    pip install pyautogui keyboard pynput pillow opencv-python numpy

Kullanim:
    python ko_macro_gui.py
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import pyautogui
import cv2
import numpy as np
import keyboard
import threading
import time
import json
import os
from pynput.mouse import Button, Controller as MouseController

# Pyautogui gecikme kaldir - maksimum hiz
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0

mouse = MouseController()

BARS        = ["F1", "F2", "F3", "F4", "F5"]
SLOTS       = 5          # Her barda kac slot (3-7 arası, 1=light feet, 2=hp pot atlandı)
SLOT_START  = 3          # Gösterimde ilk slot numarası
CONFIG_FILE = "ko_macro_config.json"
SPAM_KEYS   = ["8", "9", "0"]

# Renkler
BG     = "#12121c"
CARD   = "#1e1e2e"
CARD2  = "#252538"
ACCENT = "#7c3aed"
GREEN  = "#16a34a"
RED    = "#dc2626"
FG     = "#e2e8f0"
MUTED  = "#64748b"
SLOT_EMPTY  = "#1a1a2e"
SLOT_FILLED = "#1a3020"


# ─────────────────────────────────────────────────────────────────────────────

class MacroApp:

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("KO Rogue Makro  v2.0")
        self.root.geometry("1000x620")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)

        # Slot verisi
        self.slot_paths     = {b: [None] * SLOTS for b in BARS}
        self.slot_templates = {b: [None] * SLOTS for b in BARS}
        self.slot_btns      = {b: []             for b in BARS}
        self.slot_lbls      = {b: []             for b in BARS}

        # Ayarlar
        self.act_key    = tk.StringVar(value="z")
        self.confidence = tk.DoubleVar(value=0.82)
        self.status_var = tk.StringVar(value="Durduruldu")

        # Durum
        self.active     = False
        self.stop_ev    = threading.Event()

        self._build_ui()
        self._load_config()

    # ─── UI ──────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Başlık çubuğu ──
        hdr = tk.Frame(self.root, bg=ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        tk.Label(hdr, text="⚔  KO Rogue Makro",
                 font=("Segoe UI", 13, "bold"), bg=ACCENT, fg="white"
                 ).pack(side="left", padx=16, pady=10)

        self.status_lbl = tk.Label(hdr, textvariable=self.status_var,
                                   font=("Segoe UI", 10), bg=ACCENT, fg="#d4c0ff")
        self.status_lbl.pack(side="right", padx=16)

        # ── Ana alan ──
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=10, pady=8)

        # Sol: Skill barları
        left = tk.Frame(body, bg=BG)
        left.pack(side="left", fill="both", expand=True)

        # Notebook stil
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("T.TNotebook",        background=BG,    borderwidth=0)
        style.configure("T.TNotebook.Tab",    background=CARD2, foreground=FG,
                        font=("Segoe UI", 10, "bold"), padding=[14, 5])
        style.map("T.TNotebook.Tab",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", "white")])

        nb = ttk.Notebook(left, style="T.TNotebook")
        nb.pack(fill="both", expand=True)

        for bar in BARS:
            tab = tk.Frame(nb, bg=CARD, padx=10, pady=10)
            nb.add(tab, text=f"  {bar}  ")

            tk.Label(tab, text=f"{bar} Barı  —  Slot 3-7 arası skill resimleri  (1=light feet, 2=hp pot atlandı)",
                     font=("Segoe UI", 9), bg=CARD, fg=MUTED).pack(anchor="w", pady=(0, 8))

            row = tk.Frame(tab, bg=CARD)
            row.pack()

            for i in range(SLOTS):
                slot_num = SLOT_START + i   # 3, 4, 5, 6, 7
                cell = tk.Frame(row, bg=CARD, padx=4)
                cell.grid(row=0, column=i)

                btn = tk.Button(
                    cell,
                    text=f"＋\nSlot {slot_num}",
                    width=8, height=5,
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

            # Temizle butonu
            tk.Button(tab, text="🗑  Barı Temizle",
                      bg="#2a1a1a", fg="#cc6666",
                      font=("Segoe UI", 8), relief="flat", cursor="hand2",
                      command=lambda b=bar: self._clear_bar(b)
                      ).pack(anchor="w", pady=(10, 0))

        # Sağ: Ayar paneli
        right = tk.Frame(body, bg=CARD, width=210, padx=14, pady=12)
        right.pack(side="right", fill="y", padx=(10, 0))
        right.pack_propagate(False)

        def sep():
            tk.Frame(right, bg="#2a2a3e", height=1).pack(fill="x", pady=6)

        def sec(text):
            tk.Label(right, text=text, font=("Segoe UI", 8, "bold"),
                     bg=CARD, fg=ACCENT).pack(anchor="w", pady=(6, 2))

        sec("Aktivasyon Tuşu")
        ak_row = tk.Frame(right, bg=CARD)
        ak_row.pack(fill="x")
        tk.Entry(ak_row, textvariable=self.act_key,
                 width=5, font=("Segoe UI", 13, "bold"),
                 bg=CARD2, fg=FG, insertbackground=FG,
                 justify="center", relief="flat"
                 ).pack(side="left")
        tk.Label(ak_row, text=" tuşuna basılı tut",
                 bg=CARD, fg=MUTED, font=("Segoe UI", 8)).pack(side="left")

        sep()
        sec("Eşleşme Hassasiyeti")
        tk.Scale(right, variable=self.confidence, from_=0.50, to=1.0,
                 resolution=0.01, orient="horizontal",
                 bg=CARD, fg=FG, troughcolor=CARD2,
                 highlightthickness=0, length=178
                 ).pack()
        self.conf_lbl = tk.Label(right, bg=CARD, fg=MUTED,
                                 font=("Segoe UI", 8))
        self.conf_lbl.pack()
        self.confidence.trace_add("write", self._update_conf_lbl)
        self._update_conf_lbl()

        sep()
        sec("Sürekli Spam (her zaman aktif)")
        tk.Label(right,
                 text="8  ·  9  ·  0  ·  Sağ Tık",
                 bg=CARD, fg="#9988cc", font=("Segoe UI", 10, "bold")
                 ).pack(anchor="w")

        sep()
        self.toggle_btn = tk.Button(
            right,
            text="▶   BAŞLAT",
            bg=GREEN, fg="white",
            font=("Segoe UI", 12, "bold"),
            relief="flat", cursor="hand2",
            width=16, height=2,
            activebackground="#15803d",
            command=self._toggle
        )
        self.toggle_btn.pack(pady=8, fill="x")

        tk.Button(right, text="💾  Ayarları Kaydet",
                  bg=CARD2, fg="#86efac",
                  font=("Segoe UI", 9), relief="flat", cursor="hand2",
                  command=self._save_config
                  ).pack(fill="x", pady=2)

        sep()
        sec("Nasıl Kullanılır?")
        help_txt = (
            "① Her F barına skill\n"
            "   ekran görüntüsü ekle\n"
            "② BAŞLAT'a bas\n"
            "③ Aktivasyon tuşunu\n"
            "   basılı tut\n"
            "④ F1→F2→... sırasıyla\n"
            "   skill arar, bulursa\n"
            "   o barı basar\n"
            "⑤ 8/9/0/sağtık her zaman"
        )
        tk.Label(right, text=help_txt, bg=CARD, fg="#4a4a6a",
                 font=("Segoe UI", 8), justify="left").pack(anchor="w")

    def _update_conf_lbl(self, *_):
        self.conf_lbl.config(text=f"Hassasiyet: {self.confidence.get():.2f}")

    # ─── Resim seçme ─────────────────────────────────────────────────────────

    def _pick_image(self, bar, idx):
        path = filedialog.askopenfilename(
            title=f"{bar} Slot {idx+1} — Skill Resmi Seç",
            filetypes=[("Resim Dosyaları", "*.png *.jpg *.jpeg *.bmp"), ("Tümü", "*.*")]
        )
        if path:
            self._load_slot(bar, idx, path)

    def _load_slot(self, bar: str, idx: int, path: str):
        try:
            pil = Image.open(path).convert("RGB")
            self.slot_paths[bar][idx] = path
            # cv2 template
            self.slot_templates[bar][idx] = cv2.cvtColor(
                np.array(pil), cv2.COLOR_RGB2BGR)
            # Küçük resim
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
            slot_num = SLOT_START + i   # 3, 4, 5, 6, 7
            self.slot_paths[bar][i] = None
            self.slot_templates[bar][i] = None
            btn = self.slot_btns[bar][i]
            btn.config(image="", text=f"＋\nSlot {slot_num}",
                       bg=SLOT_EMPTY, fg="#5555aa")
            btn.image = None
            self.slot_lbls[bar][i].config(text="boş", fg="#383860")

    # ─── Makro aç/kapat ───────────────────────────────────────────────────────

    def _toggle(self):
        if not self.active:
            self.active = True
            self.stop_ev.clear()
            self.toggle_btn.config(text="⏹   DURDUR", bg=RED,
                                   activebackground="#b91c1c")
            self._set_status("Aktif — tuşa basılı tut", "#a78bfa")
            threading.Thread(target=self._spam_loop,  daemon=True).start()
            threading.Thread(target=self._skill_loop, daemon=True).start()
        else:
            self.active = False
            self.stop_ev.set()
            self.toggle_btn.config(text="▶   BAŞLAT", bg=GREEN,
                                   activebackground="#15803d")
            self._set_status("Durduruldu", MUTED)

    def _set_status(self, text: str, color: str = FG):
        self.status_var.set(text)
        self.status_lbl.config(fg=color)

    # ─── Spam döngüsü ─────────────────────────────────────────────────────────

    def _spam_loop(self):
        """8 · 9 · 0 · sağ tık — aktivasyon tuşundan bağımsız sürekli spam"""
        while not self.stop_ev.is_set():
            for k in SPAM_KEYS:
                pyautogui.keyDown(k)
                pyautogui.keyUp(k)
            mouse.click(Button.right)
            time.sleep(0.015)   # ~66 iterasyon/sn

    # ─── Skill döngüsü ────────────────────────────────────────────────────────

    def _skill_loop(self):
        """
        Aktivasyon tuşu basılıyken:
          F1 barını tara → resim varsa bas, yoksa F2 → F3 → …
        """
        bar_key = {"F1": "f1", "F2": "f2", "F3": "f3", "F4": "f4", "F5": "f5"}

        while not self.stop_ev.is_set():
            ak = self.act_key.get().strip().lower()
            if not ak or not keyboard.is_pressed(ak):
                time.sleep(0.008)
                continue

            # Tek ekran görüntüsü al
            try:
                screen_bgr = cv2.cvtColor(
                    np.array(pyautogui.screenshot()), cv2.COLOR_RGB2BGR)
            except Exception:
                continue

            conf = self.confidence.get()
            pressed = False

            for bar in BARS:
                templates = [t for t in self.slot_templates[bar] if t is not None]
                if not templates:
                    continue        # Barda resim yok

                found = False
                for tmpl in templates:
                    h, w = tmpl.shape[:2]
                    sh, sw = screen_bgr.shape[:2]
                    if h > sh or w > sw:
                        continue
                    res = cv2.matchTemplate(screen_bgr, tmpl, cv2.TM_CCOEFF_NORMED)
                    if cv2.minMaxLoc(res)[1] >= conf:
                        found = True
                        break

                if found:
                    fk = bar_key[bar]
                    pyautogui.keyDown(fk)
                    time.sleep(0.025)
                    pyautogui.keyUp(fk)
                    self.root.after(0, self._set_status,
                                   f"⚡ {bar} ({fk.upper()}) vuruldu", "#4ade80")
                    pressed = True
                    break

            if not pressed and keyboard.is_pressed(ak):
                self.root.after(0, self._set_status,
                               "⏳ Skill bekleniyor...", "#facc15")

            time.sleep(0.012)   # ~80 tarama/sn

    # ─── Kaydet / Yükle ───────────────────────────────────────────────────────

    def _save_config(self):
        cfg = {
            "activation_key": self.act_key.get(),
            "confidence":     self.confidence.get(),
            "slots": {b: self.slot_paths[b] for b in BARS}
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        messagebox.showinfo("Kaydedildi", "Ayarlar başarıyla kaydedildi.")

    def _load_config(self):
        if not os.path.exists(CONFIG_FILE):
            return
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            self.act_key.set(cfg.get("activation_key", "z"))
            self.confidence.set(cfg.get("confidence", 0.82))
            for bar in BARS:
                for i, path in enumerate(cfg.get("slots", {}).get(bar, [None]*SLOTS)):
                    if path and os.path.exists(path):
                        self._load_slot(bar, i, path)
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    root = tk.Tk()
    app  = MacroApp(root)
    root.mainloop()
