# DOKAPON! Sword of Fury — EXE Analysis Report

> Last updated: 2026-03-16
> Based on static PE analysis, Capstone disassembly, and Frida runtime tracing

## Binary Identification

| Field | Value |
|-------|-------|
| Name | DOKAPON! Sword of Fury.exe |
| Size | ~12 MB |
| Type | PE32+ Windows GUI, x86-64 |
| Compile timestamp | 2025-09-24 07:31:21 UTC |
| Entry point | 0x5cb338 |
| Image base | 0x140000000 |
| ASLR | Yes (high-entropy VA) |
| Signed | No (no Authenticode) |

## Engine / Framework

**Custom native C++ engine: dkit / DKFramework**

NOT Unity, NOT Unreal. No CLR/.NET runtime.

### PDB Path
```
C:\usr\project\dkit\git\Program\Project\Windows\WindowsMain\x64\Final\WindowsMain.pdb
```

### Source Paths Found
```
c:\usr\project\dkit\git\program\source\kernel\platform\windows\k_cgraphics.cpp
c:\usr\project\dkit\git\program\source\kernel\platform\windows\k_cfile.cpp
c:\usr\project\dkit\git\program\source\kernel\platform\windows\k_cthread.cpp
c:\usr\project\dkit\git\program\source\kernel\platform\windows\k_cpad.cpp
c:\usr\project\dkit\git\program\source\application\winmain.cpp
```

### Internal Class Names (RTTI)
```
Kernel::CGraphics::CGraphics
Kernel::CGraphics::CreateBuffer
Kernel::CGraphics::_CreateTexture
Kernel::CFile::OpenFile
Kernel::CFile::_Read / _Write
Kernel::CThread::CreateThread
Kernel::CPad::_GetAxisRange
CoSetting, CoFileIO, CoPadSelect, CoBattleIn
DKITS_OnlineMain_1_34, DKITS_OnlineSub_1_35
```

## Subsystems

### Rendering: Direct3D 11
- `d3d11.dll` → `D3D11CreateDevice`
- `dxgi.dll` → `CreateDXGIFactory`
- Error strings for: SwapChain, RenderTarget, Texture2D, Shaders, InputLayout
- Function at 0x140544840–0x140547389 (renderer init)
- Fallback logic: tries D3D11 device creation twice

### Input
- `DINPUT8.dll` → DirectInput8Create (keyboard)
- `XINPUT1_4.dll` (controller)
- `IMM32.dll` (IME support)
- GUID_SysKeyboard at 0x14069b6a8

### Audio: WinMM
- `waveOutOpen` at 0x14055eb81
- PCM, 2 channels, 48000 Hz, 16-bit
- Block align 4, callback-function mode
- Critical section protected

### Steam Integration
- App ID: **3077020**
- `SteamAPI_RestartAppIfNecessary(0x2EF39C)` at startup
- 7 callback registrations (0x1404459f6–0x140445b10)
- Interfaces: SteamUser023, SteamNetworkingSockets012, SteamNetworkingUtils004
- Lobby/room system with join restrictions

### Save System
- Root: `.\GameData\Windows\Save`
- Slots: Auto, No_1 through No_9
- Path builder at 0x1400574e0
- Slot builder at 0x140057630

### Settings
- File: `Setting.ini`
- Loader at 0x1405638a0
- Default template embedded in EXE:
```ini
[Input]
ExchangeAB="0"
[State]
ScreenMode="0"
RememberWindow="0"
ButtonType="0"
```

## Asset Paths (from strings)

308 .spranm, 13 .tex, 10 .txd, 6 .ogv, 5 .mpd, 4 .pck, 1 .fnt, 1 .mdl

### Key patterns:
```
/Field/Face/%sFACE%02d%c_00.spranm
/Field/Face/%sFACE%02d%c_01.spranm
/Field/Player/F_C_%02d%c.spranm
/Field/Player/PL_DMG_00.spranm
```

### PCK Archives:
```
/BGM.pck    — Background music (47 tracks)
/SE.pck     — Sound effects
/Voice.pck  — Japanese voice lines
/Voice-en.pck — English voice lines
```

### Videos:
```
/Opening.ogv, /Opening-en.ogv, /Opening-ct.ogv, /Opening-cs.ogv
/Opening-ko.ogv, /Scenario.ogv
```

## Frida Runtime Tracing Results

### Section Name Copy Function
- Located at EXE+0x43720
- Called with: rcx=this, rdx=dest_buffer, r8=source_string

### Parts Parser Xrefs
- EXE+0x167C4A (path 1)
- EXE+0x17502A (path 2)

### Texture Sub-Section Flags (confirmed at runtime)
| Flag | Meaning | Data Format |
|------|---------|-------------|
| 0x4000 | PNG texture | Embedded PNG at offset 0x28 |
| 0x0080 | Indexed texture | LZ77-compressed pixel data |

### Runtime Observation
- All assets loaded during level/scene transitions
- No new .spranm files opened during gameplay
- Texture data re-accessed continuously during rendering
- "Load Anime Model Thread" string confirms background loading

## Key Function Addresses (from image base 0x140000000)

| Address | Function |
|---------|----------|
| 0x140048de0 | Steam bootstrap / startup |
| 0x1400574e0 | Save path builder |
| 0x140057630 | Slot-specific save path builder |
| 0x1405638a0 | Settings/config loader |
| 0x140544840 | D3D11 renderer initialization |
| 0x14055eb20 | WinMM audio initialization |
| 0x14055f990 | DirectInput keyboard initialization |
| 0x14044bd80 | Steam callback pump |
| 0x140043720 | Section name copy (spranm parser) |
| 0x140167C4A | Parts parser path 1 |
| 0x14017502A | Parts parser path 2 |
