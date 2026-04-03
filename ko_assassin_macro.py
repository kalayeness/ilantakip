"""
Knight Online - Assassin Rogue Makrosu
Minor + Skill (R) vuran otomatik makro

Gereksinimler:
    pip install pyautogui keyboard pynput

Kullanim:
    python ko_assassin_macro.py
    F6  -> Makroyu Baslat / Durdur
    F7  -> Programdan Cik
"""

import time
import threading
import pyautogui
import keyboard

# ─────────────────────────────────────────────────────────────────────────────
# AYARLAR - Kendi oyun ayarlariniza gore degistirin
# ─────────────────────────────────────────────────────────────────────────────

TUSLARA = {
    "minor":    "f1",   # Minor potion tus (oyunda ne atadiysan)
    "skill1":   "r",    # Birinci skill / combo baslangici
    "skill2":   "f2",   # Ikinci skill (varsa)
    "skill3":   "f3",   # Ucuncu skill (varsa)
}

GECIKMELER = {
    "minor_aralik":  4.0,   # Minor kac saniyede bir kullanilsin (sn)
    "skill_aralik":  1.8,   # Skill vuruslar arasi bekleme (sn)
    "tus_basma":     0.05,  # Tusa basip birakma suresi (sn)
}

SKILL_SIRASI = ["skill1", "skill2", "skill3"]  # Istedigin siraya koy

# ─────────────────────────────────────────────────────────────────────────────

pyautogui.FAILSAFE = True   # Fareyi sol ust koseye surersen dur
running = False
stop_event = threading.Event()


def tusa_bas(tus_adi: str):
    """Verilen mantiksal isme karsilik gelen tusa basar."""
    tus = TUSLARA.get(tus_adi)
    if tus:
        pyautogui.keyDown(tus)
        time.sleep(GECIKMELER["tus_basma"])
        pyautogui.keyUp(tus)


def minor_dongusu():
    """Arka planda belirli aralikla minor kullanir."""
    while not stop_event.is_set():
        tusa_bas("minor")
        print(f"[{zaman()}] Minor kullanildi ({TUSLARA['minor']})")
        stop_event.wait(GECIKMELER["minor_aralik"])


def skill_dongusu():
    """Skill sirasiyla skill tuslarini calistirir."""
    while not stop_event.is_set():
        for skill in SKILL_SIRASI:
            if stop_event.is_set():
                break
            if TUSLARA.get(skill):
                tusa_bas(skill)
                print(f"[{zaman()}] {skill.upper()} kullanildi ({TUSLARA[skill]})")
                stop_event.wait(GECIKMELER["skill_aralik"])


def zaman() -> str:
    return time.strftime("%H:%M:%S")


def makroyu_baslat():
    global running
    if running:
        return
    running = True
    stop_event.clear()
    print(f"\n[{zaman()}] *** MAKRO BASLADI *** (Durdurmak: F6)")

    t_minor = threading.Thread(target=minor_dongusu, daemon=True)
    t_skill = threading.Thread(target=skill_dongusu,  daemon=True)

    t_minor.start()
    t_skill.start()


def makroyu_durdur():
    global running
    if not running:
        return
    running = False
    stop_event.set()
    print(f"\n[{zaman()}] *** MAKRO DURDU ***")


def toggle(e):
    if running:
        makroyu_durdur()
    else:
        makroyu_baslat()


def cikis(e):
    makroyu_durdur()
    print(f"\n[{zaman()}] Programdan cikiliyor...")
    raise SystemExit


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 55)
    print("  Knight Online - Assassin Rogue Makrosu")
    print("=" * 55)
    print(f"  Minor tus   : {TUSLARA['minor']}  (her {GECIKMELER['minor_aralik']}sn)")
    print(f"  Skill sirasi: {[TUSLARA[s] for s in SKILL_SIRASI if TUSLARA.get(s)]}")
    print(f"  Skill aralik: {GECIKMELER['skill_aralik']}sn")
    print("-" * 55)
    print("  F6 -> Baslat / Durdur")
    print("  F7 -> Cik")
    print("=" * 55)
    print("\nOyunu on plana alin ve F6 ile makroyu baslatın.\n")

    keyboard.on_press_key("f6", toggle)
    keyboard.on_press_key("f7", cikis)
    keyboard.wait()
