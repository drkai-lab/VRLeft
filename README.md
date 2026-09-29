# VRLeft (ぶいあーるれふと)

**English** | [日本語](README.ja.md)

Trigger VRChat avatar expressions and gimmicks straight from the keyboard -
either from the [T1 mini keypad (6 Keys 1 Knob RGB Programming Macro Gaming Keypad)](https://ja.aliexpress.com/item/1005009812219099.html),
or with **Shift+1..0 on any keyboard** when the keypad is not plugged in.

One keypress sends one VRChat OSC message. No mouse, no menu diving, no
touching the desktop while you are in VR.

* single-file Python app: standard library + Tkinter, no runtime dependencies
* pulse / toggle / hold / set modes, bool / int / float / string values
* GUI editor, monitor daemon, `--watch` key inspector, OSC feedback listener
* Linux (verified on hardware), Windows and macOS (built and tested by CI)

## Quick start

```bash
./VRLeft            # opens the GUI (tkinter required)
```

1. In VRChat: **Actions → Options → OSC → Enabled**.
2. Press **Start monitor** in VRLeft.
3. **New** → pick a trigger:
   * `shift_digit` + digit `1` … `9` / `0` - fires while Shift is held, on any keyboard, or
   * `key` → **Detect...** → press a key on the T1 (or any keyboard; device shows `t1` or `any`).
4. Enter the OSC address of an avatar parameter, e.g.
   `/avatar/parameters/VRLeft_Smile`, choose type `bool` and mode `pulse`.
5. **Apply** → **Save**, then press the key in VRChat.

`Shift+1..0` bindings ship **disabled** with an empty address: enable them and
fill in your own avatar's parameters.

## Triggers and modes

| Trigger | Meaning |
| --- | --- |
| `shift_digit` | Shift + `1..9` / `0` on any keyboard |
| `key` | a single key code, optionally limited to the T1 (`device: t1`) or accepted from any keyboard (`device: any`) |

| Mode | Behaviour |
| --- | --- |
| `pulse` | send the value on press, the off value after `pulse_ms` (default 200 ms) |
| `toggle` | alternate between value and off value on every press |
| `hold` | value while the key is down, off value on release |
| `set` | send the value on every press, nothing on release |

| Type | OSC typetag |
| --- | --- |
| `bool` | `T` / `F` |
| `int` | `i` |
| `float` | `f` |
| `string` | `s` |

## Install

Requirements: Python 3.9+ and Tkinter.

```bash
# Linux / macOS
./install.sh                 # binary + desktop entry + udev rule
./install.sh --autostart     # also start the monitor at login
./install.sh --input-group   # also allow Shift+1..0 on every keyboard

# Windows (Python from python.org includes Tk)
py -3 VRLeft --gui
```

Or skip the installer and run the file in place: `./VRLeft --gui`.

Prebuilt binaries are produced by GitHub Actions for every push: a Windows
`.exe` (console + windowed), macOS `.app` and CLI (arm64 + x86_64) and a
Linux tarball - see the **Actions** tab, or the **Releases** page for tags.

## Command line

```
VRLeft                 GUI (falls back to the monitor without tkinter)
VRLeft --gui           configuration GUI
VRLeft --monitor       input -> OSC daemon in the foreground
VRLeft --watch [SEC]   print incoming input events with their evdev names
VRLeft --selftest      check config, input access and the OSC port
VRLeft --selftest --send-test   ... and send a test message to VRChat
VRLeft --send ADDRESS TYPE VALUE   send one message and exit
VRLeft --scope all|t1  device scope for --watch
VRLeft --version
```

Examples:

```bash
VRLeft --send /avatar/parameters/VRLeft_Wave bool true
VRLeft --send /avatar/parameters/VRLeft_Smile int 2
VRLeft --watch 10 --scope t1
```

## Configuration files

| OS | settings | state / log |
| --- | --- | --- |
| Linux | `~/.config/vrleft/settings.json` | `~/.local/state/vrleft/` |
| macOS | `~/Library/Application Support/VRLeft/settings.json` | `…/VRLeft/state/` |
| Windows | `%APPDATA%\VRLeft\settings.json` | `%APPDATA%\VRLeft\state\` |

The monitor watches the file and reloads it when it changes.

## Input access

* **T1 keypad** - `install.sh` installs a udev rule scoped to
  `idVendor 1189 / idProduct 8890` (`/etc/udev/rules.d/60-vrleft-input.rules`).
* **Every keyboard (Shift+1..0)** - your session must be able to read
  `/dev/input/event*`. Most distributions grant that to members of the
  `input` group: `./install.sh --input-group`, then log out and back in.
* **Windows / macOS** - no extra setup; the tool uses Raw Input and IOHID.

## Platform status

| Platform | Input backend | Build | Tests | Notes |
| --- | --- | --- | --- | --- |
| Linux | evdev (`/dev/input/event*`) | local + CI | 53 | verified on real hardware (T1 + own keyboard) |
| Windows | Raw Input (`WM_INPUT`) | CI | 53 | CI builds and smoke-tests both `.exe`; device I/O not verified on hardware |
| macOS | IOHID manager | CI (arm64, x86_64) | 53 | CI builds and smoke-tests the `.app`; device I/O not verified on hardware |

## Security notes

* VRChat OSC is unauthenticated localhost UDP by design - VRLeft only ever
  sends to the address/port you configure (default `127.0.0.1:9000`).
* The udev rule is scoped to the keypad's vendor/product pair.
* Reading *all* keyboards means VRLeft can see every keystroke locally; key
  codes are matched in memory and only the OSC addresses/values you configure
  leave the machine. Use `--scope t1` if you prefer keypad-only input.
* `MODE="0666"` on the udev rule means any local user can read the keypad's
  input node; this mirrors the vendor tool's behaviour and keeps the setup
  free of group/re-login steps.

## Development

```bash
ruff check .                        # tests
ruff check VRLeft --select F,E9     # the app itself (no .py extension)
python3 tests/test_osc.py           # OSC encode/decode/socket tests
python3 tests/test_core.py          # engine, settings, monitor chain, CLI
./VRLeft --selftest
VRLEFT_GUI_SMOKE=1 ./VRLeft --gui    # builds the whole GUI and exits
```

Layout: the app is one file - settings, OSC, input backends (Linux/Windows/
macOS), trigger `Engine`, `monitor_loop`, Tkinter GUI, CLI. The input backends
are shared with [t1-keyboard-config](https://github.com/drkai-lab/t1-keyboard-config),
the configuration tool for the keypad itself.

## Related

* [t1-keyboard-config](https://github.com/drkai-lab/t1-keyboard-config) -
  configure the T1 keypad (layers, dial, lighting, Flash)
* [6 Keys 1 Knob RGB Programming Macro Gaming Keypad](https://ja.aliexpress.com/item/1005009812219099.html)

## License

[MIT](LICENSE)
