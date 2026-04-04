"""
Knight Online - Rogue Assassin Combo Makrosu
============================================
Python 3.x | Windows Only

Gereksinimler:
    pip install pydirectinput keyboard

Kullanım:
    python ko_rogue_macro.py
    F10 → Makroyu başlat
    F11 → Makroyu durdur
"""

import threading
import time
import sys

try:
    import pydirectinput
except ImportError:
    print("[HATA] pydirectinput bulunamadı. Kurmak için: pip install pydirectinput")
    sys.exit(1)

try:
    import keyboard
except ImportError:
    print("[HATA] keyboard bulunamadı. Kurmak için: pip install keyboard")
    sys.exit(1)


# ============================================================
# KULLANICI AYARLARI - BURADAN DÜZENLEYİN
# ============================================================

# Combo sırası: (bar_tuşu, skill_tuşu)
# Bar tuşları : f1, f2, f3, f4
# Skill tuşları: 3, 4, 5, 6, 7
COMBO_SEQUENCE = [
    ("f1", "3"),
    ("f3", "4"),
    ("f1", "4"),
    ("f2", "5"),
]

# Minor / Pot tuşları (HP ve Mana)
# Sırasıyla basılır, sonra tekrar başa döner
MINOR_KEYS = ["9", "0", "8"]

# ---- ZAMANLAMA AYARLARI (saniye cinsinden) ----
# Not: Agresif (çok düşük) değerler oyunu kasabilir veya
#      input buffer'ını taşırabilir. Güvenli aralıkta tutun.

BAR_SWITCH_DELAY = 0.045   # Bar tuşu (F1-F4) sonrası bekleme  ~45ms
SKILL_DELAY      = 0.110   # Skill tuşu sonrası bekleme         ~110ms
R_DELAY          = 0.080   # Basic attack (R) sonrası bekleme   ~80ms
LOOP_DELAY       = 0.015   # Combo adımları arası minimum bekleme ~15ms

MINOR_KEY_DELAY  = 0.055   # Minor tuşları arası gecikme        ~55ms
MINOR_LOOP_DELAY = 0.030   # Minor döngü tekrar bekleme         ~30ms

# ---- HOTKEY AYARLARI ----
START_KEY = "f10"   # Makroyu başlat
STOP_KEY  = "f11"   # Makroyu durdur


# ============================================================
# GLOBAL DURUM (manuel değiştirmeyin)
# ============================================================

_running       = False
_combo_thread  = None
_minor_thread  = None
_state_lock    = threading.Lock()


# ============================================================
# YARDIMCI FONKSİYON
# ============================================================

def safe_press(key: str, delay_after: float = 0.0) -> None:
    """
    Güvenli tuş basımı.
    Hata durumunda script kilitlenmez; hata loglanır ve devam eder.
    """
    try:
        pydirectinput.press(key)
        if delay_after > 0:
            time.sleep(delay_after)
    except Exception as exc:
        print(f"[UYARI] Tuş basımı başarısız ({key}): {exc}")


# ============================================================
# COMBO DÖNGÜSÜ
# ============================================================

def run_combo() -> None:
    """
    Ana combo döngüsü.

    COMBO_SEQUENCE dizisini baştan sona sırasıyla işler,
    ardından tekrar başa döner.

    Her adım:
        1. Bar tuşu (F1-F4)  →  BAR_SWITCH_DELAY
        2. Skill tuşu (3-7)  →  SKILL_DELAY
        3. Basic attack (R)  →  R_DELAY
        4. Sonraki adıma geç →  LOOP_DELAY
    """
    global _running
    print("[COMBO] Thread başlatıldı.")
    idx = 0

    while _running:
        bar_key, skill_key = COMBO_SEQUENCE[idx % len(COMBO_SEQUENCE)]

        # Adım 1: Skill bar'ı değiştir
        safe_press(bar_key, BAR_SWITCH_DELAY)

        # Adım 2: Skill kullan
        safe_press(skill_key, SKILL_DELAY)

        # Adım 3: Basic attack
        safe_press("r", R_DELAY)

        # Sonraki combo adımına geç
        idx += 1
        time.sleep(LOOP_DELAY)

    print("[COMBO] Thread durdu.")


# ============================================================
# MİNOR (HP + MANA POT) DÖNGÜSÜ
# ============================================================

def run_minor() -> None:
    """
    HP / Mana pot döngüsü.

    MINOR_KEYS dizisini sırasıyla basar, ardından tekrar başa döner.
    Ana combo thread'inden bağımsız çalışır; birbirini bloklamaz.
    """
    global _running
    print("[MINOR] Thread başlatıldı.")
    idx = 0

    while _running:
        key = MINOR_KEYS[idx % len(MINOR_KEYS)]
        safe_press(key, MINOR_KEY_DELAY)
        idx += 1
        time.sleep(MINOR_LOOP_DELAY)

    print("[MINOR] Thread durdu.")


# ============================================================
# BAŞLAT / DURDUR
# ============================================================

def start_macro() -> None:
    """
    Makroyu başlatır.
    Zaten çalışıyorsa ikinci kez başlatmaz.
    """
    global _running, _combo_thread, _minor_thread

    with _state_lock:
        if _running:
            print("[UYARI] Makro zaten çalışıyor. (F11 ile durdur)")
            return

        _running = True
        print("\n[SİSTEM] ✓ Makro BAŞLATILDI  |  Durdurmak için F11'e bas")

        # Combo thread — daemon=True: ana program kapanınca thread de kapanır
        _combo_thread = threading.Thread(
            target=run_combo,
            name="ComboThread",
            daemon=True,
        )
        _combo_thread.start()

        # Minor/pot thread — combo'dan bağımsız
        _minor_thread = threading.Thread(
            target=run_minor,
            name="MinorThread",
            daemon=True,
        )
        _minor_thread.start()


def stop_macro() -> None:
    """
    Makroyu güvenli şekilde durdurur.
    Thread'lerin kendi döngüsünü tamamlamasını bekler (max 2 sn).
    """
    global _running

    with _state_lock:
        if not _running:
            print("[UYARI] Makro zaten durmuş. (F10 ile başlat)")
            return

        _running = False
        print("\n[SİSTEM] ✗ Makro DURDURULDU  |  Başlatmak için F10'a bas")

    # Thread'lerin kapanmasını bekle
    if _combo_thread and _combo_thread.is_alive():
        _combo_thread.join(timeout=2.0)

    if _minor_thread and _minor_thread.is_alive():
        _minor_thread.join(timeout=2.0)


# ============================================================
# ANA PROGRAM
# ============================================================

def main() -> None:
    print("=" * 55)
    print("  Knight Online — Rogue Assassin Combo Makrosu")
    print("  Python sürümü | pydirectinput + keyboard")
    print("=" * 55)
    print(f"  Başlat : {START_KEY.upper()}")
    print(f"  Durdur : {STOP_KEY.upper()}")
    print(f"  Combo  : {COMBO_SEQUENCE}")
    print(f"  Minor  : {MINOR_KEYS}")
    print("=" * 55)
    print("[SİSTEM] Hotkey'ler kayıt edildi. Bekleniyor...\n")

    # pydirectinput FAILSAFE — köşeye gittiğinde durma (opsiyonel)
    pydirectinput.FAILSAFE = False

    # Global hotkey kayıtları
    keyboard.add_hotkey(START_KEY, start_macro, suppress=True)
    keyboard.add_hotkey(STOP_KEY,  stop_macro,  suppress=True)

    # Ana thread'i canlı tut — keyboard.wait() Ctrl+C ile çıkışa izin verir
    try:
        keyboard.wait()
    except KeyboardInterrupt:
        stop_macro()
        print("\n[SİSTEM] Program kapatıldı.")


if __name__ == "__main__":
    main()
