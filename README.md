# Radial ZBrush

A radial menu for ZBrush, built as a study project and inspired by RadialZ. You press a hotkey, the menu opens at the cursor, and you pick a brush or a command.

It works with **ZBrush 2023/2024** through a ZScript bridge, and with **ZBrush 2026** through a Python bridge.

## How it works

There are two parts:

1. **External app** (`radial/`, Python + PySide6): listens for hotkeys, draws the menu and decides what was chosen.
2. **Bridge inside ZBrush**: runs the command inside ZBrush.
   - ZBrush 2023/2024: `zbrush_bridge/zscript/RadialBridge.txt` (ZScript), with `"protocol": "zscript"` in the config.
   - ZBrush 2026: `zbrush_bridge/radial_bridge.py` (Python), with `"protocol": "python"` in the config.

ZBrush has no way to "listen" for commands in the background. So the bridge is a **button** (`ZPlugin > Radial Bridge > Run`) with a hotkey. The app writes the command to `zbrush_bridge/data/` and presses that hotkey. The button reads the command, runs it and deletes the file.

```
Alt+Q -> menu at cursor -> choice -> data/command.txt -> Ctrl+Alt+Shift+J -> Run button -> brush changes
```

The app sends keys with the Win32 `SendInput` API (physical keys with scan codes), because ZBrush ignores the Unicode characters pynput sends for letters. Before sending, it also brings the ZBrush window to the foreground.

## Slot action types

| `type` | Field | What it does |
| --- | --- | --- |
| `press` | `item` | Presses a ZBrush interface item by item path (e.g. `Brush:Move`) |
| `brush_file` | `path` | Loads a brush from a `.ZBP` file |
| `keys` | `keys` | Only presses keys: native ZBrush hotkeys (e.g. `x`, `<shift>+f`, `b s t`) |

`keys` does not use the bridge, so it works even before the bridge is set up.

ZScript bridge limits: the command can be at most 250 characters long and may only use ASCII characters (no accents) in the path or item path. The app rejects the command and warns in the console if it goes over.

## Installation

Requirements: Windows and Python 3.11 or newer.

```bat
cd J:\CODING\radial-zbrush
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

`run.bat` does all of this automatically on the first run.

## Step by step (ZBrush 2024)

### 1. Load the bridge

1. Open `zbrush_bridge/zscript/RadialBridge.txt` and check the `rbDir` line. It must point to the project's `zbrush_bridge/data/` folder, with forward slashes and a trailing `/`. The default is already `J:/CODING/radial-zbrush/zbrush_bridge/data/`.
2. In ZBrush: `ZScript > Load` and pick `RadialBridge.txt`. ZBrush compiles the file and creates `RadialBridge.zsc` next to it.
3. Open `ZPlugin > Radial Bridge`.

If ZBrush shows a syntax error on load, copy the message: it includes the line number.

### 2. Phase 0: test inside ZBrush

The test buttons live in `ZPlugin > Radial Bridge`:

- **Check**: tells you whether the Load Brush button (`Brush:Load Brush`) exists. If it does not, find the right name and change `rbLoadItem` in `RadialBridge.txt`.
- **Test Press**: asks for an item path (e.g. `Brush:Move`) and presses it. Use it to confirm the brush names in `config/menus.json`.
- **Test Load**: asks for the path of a `.ZBP` and loads it.

The item path is `Palette:Button name`, with the name as it appears in the interface (e.g. `Brush:Move`). If a name does not work in Test Press, try variations without spaces or with underscores (for example `Brush:Dam_Standard`).

### 3. Assign the Run button hotkey

1. **Ctrl+Alt+click** the **Run** button and press **Ctrl+Alt+Shift+J**. This is the config's `trigger_hotkey`.
2. Save it in `Preferences > Hotkeys > Store`.

If ZBrush does not accept that combination, use another one and also change `trigger_hotkey` in `config/menus.json`.

### 4. Run the app

```bat
run.bat
```

Or `python -m radial`. An icon shows up in the Windows tray, with **Reload config** and **Quit** options.

With ZBrush focused:

- **Alt+Q** opens the Sculpt menu and **Alt+W** opens the Tools menu.
- **Hold mode** (default): hold the hotkey, point and release.
- A **quick tap** keeps the menu open; then just click.
- **Flick**: move the mouse past the ring in the direction of the slot.
- **Esc** or **right click** closes the menu.

### 5. Load the bridge every time ZBrush starts

Copy the generated `RadialBridge.zsc` into the `ZStartup\ZPlugs64` folder inside your ZBrush 2024 installation (under `C:\Program Files\Maxon ZBrush 2024\`). Plugins in that folder load when ZBrush starts. If you change the `.txt`, load it again and copy the new `.zsc`.

## ZBrush 2026 (Python bridge)

In `config/menus.json`, use `"protocol": "python"`. In ZBrush, load `zbrush_bridge/radial_bridge.py` via `ZScript > Python Scripting > Load`. The test scripts are in `zbrush_bridge/phase0/`. `start_zbrush_with_bridge.bat` opens 2026 with the bridge already loaded. None of this works on 2023 or 2024.

## Configuration (`config/menus.json`)

- `bridge.protocol`: `zscript` (2023/2024) or `python` (2026).
- `bridge.trigger_hotkey`: the Run button's hotkey.
- `bridge.command_dir`: command folder. Relative to the project root. In the ZScript bridge it must match `rbDir`.
- `menus[].hotkey`: pynput format, for example `<alt>+q` or `<ctrl>+<shift>+e`. Pick combinations ZBrush does not use: the app does not block the key, so ZBrush receives it too.
- `selection.mode`: `hold` or `toggle`.
- `selection.hover_dwell_ms`: selects when the mouse rests on a slot (0 = off).
- `slots[].icon`: path to a PNG (optional). Without an icon, the slot shows its text.
- `slots[].color`: slot color (optional).

After editing the JSON by hand, use **Reload config** in the tray.

### Menu editor

Tray icon > **Edit menus…** opens the editor: add, remove and reorder menus and slots, set a menu's name and hotkey (click the field and press the combination), and set each slot's label, action, color and icon. **Save & reload** validates, writes `config/menus.json` and reloads the app. Appearance, selection and bridge settings are still edited in the JSON.

### Brush library

```bat
python -m radial.library "C:\path\to\brushes" --slots
python -m radial.library "C:\path\to\brushes" --find clay --slots
```

Writes `config/library.json` and prints the brushes in slot format, ready to paste into `menus.json`.

## Tests

```bat
pip install pytest
python -m pytest
```

The tests cover the logic without needing ZBrush or a keyboard: menu geometry, config validation, hotkey matching, the command format of both bridges, the bracket balance of `RadialBridge.txt` and the brush scan.

## Verification status

Confirmed working on ZBrush 2024: loading the bridge, the hotkey firing the Run button, and changing brushes from the menu (Alt+Q). Still worth checking on your setup:

| Item | How to check | Where to adjust |
| --- | --- | --- |
| The Load Brush button name (`Brush:Load Brush`) | **Check** button | `rbLoadItem` in `RadialBridge.txt` |
| Brush item paths (`Brush:ClayBuildup`, etc.) | **Test Press** button | `config/menus.json` |
| Autoload of `RadialBridge.zsc` from `ZStartup\ZPlugs64` | Restart ZBrush | step 5 |
| The Run hotkey persists after restarting ZBrush | `Hotkeys > Store` | step 3 |
| Native hotkeys in the Tools menu | Use the app | `config/menus.json` |

## Structure

```
radial/                       external app
  app.py                      wires everything together + system tray
  overlay.py                  menu window and drawing
  geometry.py                 angles, hit test, flick
  hotkeys.py                  global hotkeys and key sending
  sendinput.py                physical key events via Win32 SendInput
  winfocus.py                 brings ZBrush to the foreground
  bridge_client.py            writes the command and fires the bridge
  config.py                   JSON loading and validation
  library.py                  .ZBP brush scan
  editor.py                   menu editor window (PySide6)
  editing.py                  editor logic without Qt (hotkey conversion, list ops)
zbrush_bridge/
  zscript/RadialBridge.txt    bridge for ZBrush 2023/2024
  radial_bridge.py            bridge for ZBrush 2026
  phase0/                     Python API tests (2026 only)
  data/                       where the command is written
config/menus.json            sample menus
tests/                        automated tests
```

## Next steps (from the plan)

- Phase 4: a library popup with search and drag-to-slot.
- Phase 5: child slots, tags, live appearance controls, alphas, textures and materials.
