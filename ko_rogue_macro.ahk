; ============================================================
; Knight Online - Rogue Assassin Combo Makrosu
; AutoHotkey v2 Sürümü
; ============================================================
;
; Kullanım:
;   F10 → Makroyu başlat
;   F11 → Makroyu durdur
;
; Gereksinim: AutoHotkey v2.0+
;   https://www.autohotkey.com/
; ============================================================

#Requires AutoHotkey v2.0
#SingleInstance Force
SetWorkingDir A_ScriptDir

; Tuş gönderim modunu SendInput olarak sabitle (en stabil yöntem)
SendMode "Input"


; ============================================================
; KULLANICI AYARLARI - BURADAN DÜZENLEYİN
; ============================================================

; Combo sırası: [bar_tuşu, skill_tuşu]
; Bar tuşları  : F1, F2, F3, F4
; Skill tuşları: 3, 4, 5, 6, 7
global comboSeq := [
    ["F1", "3"],
    ["F3", "4"],
    ["F1", "4"],
    ["F2", "5"],
]

; Minor / Pot tuşları (HP ve Mana)
global minorKeys := ["9", "0", "8"]

; ---- ZAMANLAMA AYARLARI (milisaniye) ----
; Not: 0 ms gibi agresif değerler kullanmayın.
;      Oyunun input buffer'ını taşırmaz, stabiliteyi korur.

global barSwitchDelay  := 45    ; Bar tuşu (F1-F4) sonrası bekleme
global skillDelay      := 110   ; Skill tuşu sonrası bekleme
global rDelay          := 80    ; Basic attack (R) sonrası bekleme
global loopDelay       := 15    ; Combo adımları arası minimum bekleme

global minorKeyDelay   := 55    ; Minor tuşları arası gecikme
global minorLoopDelay  := 30    ; Minor döngü tekrar bekleme


; ============================================================
; GLOBAL DURUM (manuel değiştirmeyin)
; ============================================================

global isRunning  := false
global comboIdx   := 1
global minorIdx   := 1


; ============================================================
; HOTKEYS
; ============================================================

F10:: StartMacro()
F11:: StopMacro()


; ============================================================
; BAŞLAT / DURDUR
; ============================================================

StartMacro() {
    global isRunning

    if isRunning {
        ShowTip("Makro zaten çalışıyor!")
        return
    }

    isRunning := true
    ShowTip("✓ Makro BAŞLATILDI  |  F11 ile durdur")

    ; Her iki timer'ı ayrı ayrı başlat
    ; -1 = tek seferlik (kendi kendini yeniden programlar)
    SetTimer ComboLoop, -1
    SetTimer MinorLoop, -1
}

StopMacro() {
    global isRunning

    if !isRunning {
        ShowTip("Makro zaten durmuş!")
        return
    }

    isRunning := false

    ; Timer'ları devre dışı bırak
    SetTimer ComboLoop, 0
    SetTimer MinorLoop, 0

    ShowTip("✗ Makro DURDURULDU  |  F10 ile başlat")
}


; ============================================================
; YARDIMCI FONKSİYON
; ============================================================

ShowTip(msg) {
    ToolTip msg
    SetTimer () => ToolTip(), -2500   ; 2.5 saniye sonra ToolTip kapat
}


; ============================================================
; COMBO DÖNGÜSÜ
; ============================================================

ComboLoop() {
    global isRunning, comboIdx, comboSeq
    global barSwitchDelay, skillDelay, rDelay, loopDelay

    ; Durdurulduysa çık
    if !isRunning
        return

    ; Mevcut combo adımını al
    step     := comboSeq[comboIdx]
    barKey   := step[1]
    skillKey := step[2]

    ; Adım 1: Skill bar'ı değiştir (F1-F4)
    SendInput "{" barKey "}"
    Sleep barSwitchDelay

    ; Adım 2: Skill kullan (3-7)
    SendInput skillKey
    Sleep skillDelay

    ; Adım 3: Basic attack (R)
    SendInput "r"
    Sleep rDelay

    ; Sonraki combo adımına geç (dairesel)
    comboIdx := Mod(comboIdx, comboSeq.Length) + 1
    Sleep loopDelay

    ; Bir sonraki çalışmayı planla (tek seferlik timer — self-scheduling loop)
    if isRunning
        SetTimer ComboLoop, -1
}


; ============================================================
; MİNOR (HP + MANA POT) DÖNGÜSÜ
; ============================================================

MinorLoop() {
    global isRunning, minorIdx, minorKeys
    global minorKeyDelay, minorLoopDelay

    if !isRunning
        return

    ; Mevcut minor tuşunu bas
    key := minorKeys[minorIdx]
    SendInput key
    Sleep minorKeyDelay

    ; Sonraki tuşa geç (dairesel)
    minorIdx := Mod(minorIdx, minorKeys.Length) + 1
    Sleep minorLoopDelay

    ; Bir sonraki çalışmayı planla
    if isRunning
        SetTimer MinorLoop, -1
}
