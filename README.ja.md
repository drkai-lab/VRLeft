# VRLeft (ぶいあーるれふと)

[English](README.md) | **日本語**

VRChat の表情・ギミックをキーボードから発動させます。
[T1 ミニキーパッド（6 Keys 1 Knob RGB プログラミングマクロキーパッド）](https://ja.aliexpress.com/item/1005009812219099.html)
でも、キーパッドを接続していないときは **どのキーボードでも Shift+1..0** でも動きます。

押したキー 1 個につき VRChat OSC メッセージを 1 つ送るだけ。マウスは要らず、
VR 中にデスクトップへ手を伸ばす必要もありません。

* 単一ファイルの Python アプリ（標準ライブラリ + Tkinter、実行時依存なし）
* pulse / toggle / hold / set の 4 モード、bool / int / float / string 対応
* GUI 編集、監視デーモン、`--watch` キー検査、OSC 受信リスナー
* Linux（実機で動作確認済み）、Windows / macOS（CI でビルド・テスト）

## クイックスタート

```bash
./VRLeft            # GUI が開きます（tkinter が必要）
```

1. VRChat 側で **アクション → やること → OSC → 有効** にする。
2. VRLeft の **Start monitor** を押す。
3. **New** でトリガーを設定:
   * `shift_digit` + 数字 `1` … `9` / `0` - Shift 押し中のみ、どのキーボードでも発動
   * `key` → **Detect...** → T1（または任意のキーボード）のキーを押す
     （device が `t1` か `any` で記録されます）
4. アバターのパラメータ OSC アドレスを入力（例:
   `/avatar/parameters/VRLeft_Smile`）、type は `bool`、mode は `pulse`。
5. **Apply** → **Save** して VRChat 内でキーを押す。

`Shift+1..0` の 10 個は初期状態で **無効・アドレス空** で用意されています。
有効化して自分のアバターのパラメータを入れてください。

## トリガーとモード

| トリガー | 意味 |
| --- | --- |
| `shift_digit` | どのキーボードでも Shift + `1..9` / `0` |
| `key` | 1 つのキーコード。`device: t1` で T1 専用、`device: any` で全機器可 |

| モード | 動作 |
| --- | --- |
| `pulse` | 押下で値を送り、`pulse_ms` 後（既定 200ms）にオフ値を送る |
| `toggle` | 押下ごとに値とオフ値を交互に送る |
| `hold` | 押している間は値、離したらオフ値 |
| `set` | 押下のたびに値を送る（離しても何も送らない） |

| type | OSC typetag |
| --- | --- |
| `bool` | `T` / `F` |
| `int` | `i` |
| `float` | `f` |
| `string` | `s` |

## インストール

要件: Python 3.9 以上 + Tkinter。

```bash
# Linux / macOS
./install.sh                 # 本体 + デスクトップエントリ + udev ルール
./install.sh --autostart     # ログイン時にモニターを自動起動
./install.sh --input-group   # 全キーボードでの Shift+1..0 を許可

# Windows（python.org の Python なら Tk 同梱）
py -3 VRLeft --gui
```

インストーラを使わない場合はそのまま実行できます: `./VRLeft --gui`

プレビルドバイナリは push のたびに GitHub Actions が生成します
（Windows の `.exe`、macOS の `.app` と CLI（arm64 + x86_64）、Linux の tarball）。
**Actions** タブ、またはタグ付け時の **Releases** ページから取得できます。

## コマンドライン

```
VRLeft                 GUI（tkinter が無い環境ではモニターにフォールバック）
VRLeft --gui           設定 GUI
VRLeft --monitor       入力 → OSC デーモンをフォアグラウンドで実行
VRLeft --watch [SEC]   入力イベントを evdev 名つきで表示
VRLeft --selftest      設定・入力権限・OSC ポートをチェック
VRLeft --selftest --send-test   さらにテストメッセージを送信
VRLeft --send ADDRESS TYPE VALUE   1 送信して終了
VRLeft --scope all|t1  --watch の対象範囲
VRLeft --version
```

例:

```bash
VRLeft --send /avatar/parameters/VRLeft_Wave bool true
VRLeft --send /avatar/parameters/VRLeft_Smile int 2
VRLeft --watch 10 --scope t1
```

## 設定ファイル

| OS | 設定 | 状態 / ログ |
| --- | --- | --- |
| Linux | `~/.config/vrleft/settings.json` | `~/.local/state/vrleft/` |
| macOS | `~/Library/Application Support/VRLeft/settings.json` | `…/VRLeft/state/` |
| Windows | `%APPDATA%\VRLeft\settings.json` | `%APPDATA%\VRLeft\state\` |

モニターはファイルを監視し、変更されると自動で読み込みます。

## 入力のアクセス権

* **T1 キーパッド** - `install.sh` が
  `idVendor 1189 / idProduct 8890` に絞った udev ルールを
  （`/etc/udev/rules.d/60-vrleft-input.rules`）入れます。
* **全キーボード（Shift+1..0）** - `/dev/input/event*` を読める必要があります。
  多くのディストリは `input` グループのメンバーに許可しています:
  `./install.sh --input-group` を実行し、ログアウト → ログイン。
* **Windows / macOS** - 追加設定は不要（Raw Input / IOHID を使用）。

## プラットフォーム状況

| プラットフォーム | 入力バックエンド | ビルド | テスト | 備考 |
| --- | --- | --- | --- | --- |
| Linux | evdev（`/dev/input/event*`） | ローカル + CI | 53 | 実機（T1 + 自前のキーボード）で動作確認済み |
| Windows | Raw Input（`WM_INPUT`） | CI | 53 | CI が両 `.exe` をビルド・スモークテスト。実機入力は未検証 |
| macOS | IOHID manager | CI（arm64, x86_64） | 53 | CI が `.app` をビルド・スモークテスト。実機入力は未検証 |

## セキュリティに関する注意

* VRChat の OSC は localhost UDP・認証なし（VRChat 側の設計）です。
  VRLeft は設定した送信先（既定 `127.0.0.1:9000`）にしか送りません。
* udev ルールはキーパッドの vendor/product 組み合わせに限定しています。
* 全キーボードを読むため、ローカル上では全キー押下を認識できます。
  キーコードはメモリ内で照合され、送信されるのは設定した OSC アドレスと値だけです。
  キーパッドだけにしたい場合は `--scope t1` を使ってください。
* udev ルールの `MODE="0666"` はローカルの全ユーザーがキーパッドの入力ノードを
  読める、という意味です。付属ツールと同じ方針で、グループ設定や再ログインを
  不要にしています。

## 開発

```bash
ruff check .                        # tests
ruff check VRLeft --select F,E9     # 本体（拡張子なしファイル）
python3 tests/test_osc.py           # OSC の符号化・デコード・ソケット
python3 tests/test_core.py          # エンジン・設定・モニター連携・CLI
./VRLeft --selftest
VRLEFT_GUI_SMOKE=1 ./VRLeft --gui    # GUI を全部構築して即終了
```

構成: 1 ファイルに設定 / OSC / 入力バックエンド（Linux・Windows・macOS）/
トリガー `Engine` / `monitor_loop` / Tkinter GUI / CLI が入っています。
入力バックエンドはキーパッドの設定ツール
[t1-keyboard-config](https://github.com/drkai-lab/t1-keyboard-config) と共有です。

## 関連

* [t1-keyboard-config](https://github.com/drkai-lab/t1-keyboard-config) -
  T1 キーパッドの設定ツール（レイヤー・ダイヤル・照明・Flash）
* [6 Keys 1 Knob RGB Programming Macro Gaming Keypad](https://ja.aliexpress.com/item/1005009812219099.html)

## ライセンス

[MIT](LICENSE)
