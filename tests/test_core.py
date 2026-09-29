#!/usr/bin/env python3
"""Engine / settings / monitor tests for VRLeft."""

import importlib.machinery
import importlib.util
import json
import os
import socket
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "VRLeft")

loader = importlib.machinery.SourceFileLoader("vrleft", SCRIPT)
spec = importlib.util.spec_from_loader("vrleft", loader)
vrleft = importlib.util.module_from_spec(spec)
loader.exec_module(vrleft)

UDP_PORT = 19221
LEFT_SHIFT, DIGIT_1, DIGIT_0 = 42, 2, 11


class FakeSender:
    def __init__(self):
        self.messages = []
        self.last_error = None
        self.sent = 0
        self.host = "fake"
        self.port = 0

    def send(self, address, osc_type, value):
        self.messages.append((address, osc_type, value))
        self.sent += 1
        return True

    def close(self):
        pass


def binding(binding_id, trigger, action):
    base = {"mode": "pulse", "pulse_ms": 50, "type": "bool",
            "value": True, "off_value": False}
    base.update(action)
    return {"id": binding_id, "enabled": True, "trigger": trigger,
            "action": base}


def make_settings(bindings, shift_digits=True):
    settings = vrleft.default_settings()
    settings["bindings"] = bindings
    settings["input"]["shift_digits"] = shift_digits
    return settings


def make_engine(bindings, shift_digits=True, start=1000.0):
    clock = {"now": start}
    sender = FakeSender()
    settings = make_settings(bindings, shift_digits=shift_digits)
    engine = vrleft.Engine(settings, sender, now=lambda: clock["now"])
    return engine, sender, clock


class PulseTest(unittest.TestCase):
    def setUp(self):
        self.engine, self.sender, self.clock = make_engine([
            binding(1, {"kind": "key", "code": 87, "device": "any"},
                    {"address": "/avatar/parameters/Pulse"})])

    def test_down_sends_value_and_up_sends_off(self):
        self.assertEqual(self.engine.handle((vrleft.EV_KEY, 87, 1, True)),
                         [("/avatar/parameters/Pulse", True)])
        self.assertEqual(self.sender.messages,
                         [("/avatar/parameters/Pulse", "bool", True)])
        self.clock["now"] += 0.05
        self.engine.tick()
        self.assertEqual(self.sender.messages[-1],
                         ("/avatar/parameters/Pulse", "bool", False))

    def test_tick_is_inert_before_the_deadline(self):
        self.engine.handle((vrleft.EV_KEY, 87, 1, True))
        self.clock["now"] += 0.01
        self.engine.tick()
        self.assertEqual(len(self.sender.messages), 1)

    def test_repeat_events_do_not_refire(self):
        self.engine.handle((vrleft.EV_KEY, 87, 1, True))
        self.engine.handle((vrleft.EV_KEY, 87, 2, True))
        self.engine.handle((vrleft.EV_KEY, 87, 2, True))
        self.assertEqual(len(self.sender.messages), 1)


class ToggleHoldSetTest(unittest.TestCase):
    def test_toggle_flips_each_press(self):
        engine, sender, _clock = make_engine([
            binding(2, {"kind": "key", "code": 88, "device": "any"},
                    {"address": "/avatar/parameters/Toggle", "mode": "toggle"})])
        engine.handle((vrleft.EV_KEY, 88, 1, True))
        engine.handle((vrleft.EV_KEY, 88, 0, True))
        engine.handle((vrleft.EV_KEY, 88, 1, True))
        self.assertEqual([m[2] for m in sender.messages], [True, False])

    def test_hold_sends_on_press_and_off_on_release(self):
        engine, sender, _clock = make_engine([
            binding(3, {"kind": "key", "code": 89, "device": "any"},
                    {"address": "/avatar/parameters/Hold", "mode": "hold"})])
        engine.handle((vrleft.EV_KEY, 89, 1, True))
        engine.handle((vrleft.EV_KEY, 89, 1, True))  # repeat while held
        engine.handle((vrleft.EV_KEY, 89, 0, True))
        self.assertEqual([m[2] for m in sender.messages], [True, False])
        self.assertEqual(engine.held, set())

    def test_set_always_sends_its_value(self):
        engine, sender, _clock = make_engine([
            binding(4, {"kind": "key", "code": 90, "device": "any"},
                    {"address": "/avatar/parameters/Set", "mode": "set",
                     "value": 2, "type": "int"})])
        engine.handle((vrleft.EV_KEY, 90, 1, True))
        engine.handle((vrleft.EV_KEY, 90, 1, True))
        self.assertEqual([m[2] for m in sender.messages], [2, 2])


class ShiftDigitTest(unittest.TestCase):
    def setUp(self):
        self.engine, self.sender, self._clock = make_engine([
            binding(1, {"kind": "shift_digit", "digit": 1},
                    {"address": "/avatar/parameters/One"}),
            binding(2, {"kind": "shift_digit", "digit": 0},
                    {"address": "/avatar/parameters/Zero"})],
            shift_digits=True)

    def test_shift_plus_digit_fires(self):
        self.engine.handle((vrleft.EV_KEY, LEFT_SHIFT, 1, False))
        self.engine.handle((vrleft.EV_KEY, DIGIT_1, 1, False))
        self.assertEqual(self.sender.messages,
                         [("/avatar/parameters/One", "bool", True)])

    def test_digit_alone_is_ignored(self):
        self.engine.handle((vrleft.EV_KEY, DIGIT_1, 1, False))
        self.assertEqual(self.sender.messages, [])

    def test_shift_release_then_digit_is_ignored(self):
        self.engine.handle((vrleft.EV_KEY, LEFT_SHIFT, 1, False))
        self.engine.handle((vrleft.EV_KEY, LEFT_SHIFT, 0, False))
        self.engine.handle((vrleft.EV_KEY, DIGIT_1, 1, False))
        self.assertEqual(self.sender.messages, [])

    def test_zero_digit(self):
        self.engine.handle((vrleft.EV_KEY, LEFT_SHIFT, 1, False))
        self.engine.handle((vrleft.EV_KEY, DIGIT_0, 1, False))
        self.assertEqual(self.sender.messages[0][0], "/avatar/parameters/Zero")

    def test_disabled_shift_digits_are_ignored(self):
        engine, sender, _clock = make_engine([
            binding(1, {"kind": "shift_digit", "digit": 1},
                    {"address": "/avatar/parameters/One"})],
            shift_digits=False)
        engine.handle((vrleft.EV_KEY, LEFT_SHIFT, 1, False))
        engine.handle((vrleft.EV_KEY, DIGIT_1, 1, False))
        self.assertEqual(sender.messages, [])

    def test_shift_release_releases_a_held_shift_binding(self):
        engine, sender, _clock = make_engine([
            binding(1, {"kind": "shift_digit", "digit": 1},
                    {"address": "/avatar/parameters/One", "mode": "hold"})])
        engine.handle((vrleft.EV_KEY, LEFT_SHIFT, 1, False))
        engine.handle((vrleft.EV_KEY, DIGIT_1, 1, False))
        engine.handle((vrleft.EV_KEY, LEFT_SHIFT, 0, False))
        self.assertEqual([m[2] for m in sender.messages], [True, False])


class DeviceFilterTest(unittest.TestCase):
    def test_t1_only_binding_ignores_other_keyboards(self):
        engine, sender, _clock = make_engine([
            binding(1, {"kind": "key", "code": 91, "device": "t1"},
                    {"address": "/avatar/parameters/T1Key"})])
        engine.handle((vrleft.EV_KEY, 91, 1, False))
        self.assertEqual(sender.messages, [])
        engine.handle((vrleft.EV_KEY, 91, 1, True))
        self.assertEqual(len(sender.messages), 1)

    def test_any_device_binding_fires_on_both(self):
        engine, sender, _clock = make_engine([
            binding(1, {"kind": "key", "code": 92, "device": "any"},
                    {"address": "/avatar/parameters/AnyKey"})])
        engine.handle((vrleft.EV_KEY, 92, 1, False))
        engine.handle((vrleft.EV_KEY, 92, 1, True))
        self.assertEqual(len(sender.messages), 2)

    def test_disabled_binding_is_skipped(self):
        engine, sender, _clock = make_engine([
            dict(binding(1, {"kind": "key", "code": 93, "device": "any"},
                         {"address": "/avatar/parameters/Off"}), enabled=False)])
        engine.handle((vrleft.EV_KEY, 93, 1, True))
        self.assertEqual(sender.messages, [])

    def test_empty_address_counts_as_skipped(self):
        engine, sender, _clock = make_engine([
            binding(1, {"kind": "key", "code": 94, "device": "any"},
                    {"address": ""})])
        engine.handle((vrleft.EV_KEY, 94, 1, True))
        self.assertEqual(sender.messages, [])
        self.assertEqual(engine.skipped, 1)

    def test_non_key_events_are_ignored(self):
        engine, sender, _clock = make_engine([
            binding(1, {"kind": "key", "code": 95, "device": "any"},
                    {"address": "/avatar/parameters/Rel"})])
        engine.handle((vrleft.EV_REL, 8, 1, True))
        self.assertEqual(sender.messages, [])


class SettingsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="vrleft-test-")
        self._saved = (vrleft.CONFIG_FILE, vrleft.CONFIG_DIR, vrleft.STATE_DIR)
        vrleft.CONFIG_DIR = self.tmp
        vrleft.CONFIG_FILE = os.path.join(self.tmp, "settings.json")
        vrleft.STATE_DIR = self.tmp

    def tearDown(self):
        (vrleft.CONFIG_FILE, vrleft.CONFIG_DIR, vrleft.STATE_DIR) = self._saved

    def test_defaults_have_ten_shift_bindings(self):
        settings = vrleft.default_settings()
        digits = sorted(b["trigger"]["digit"] for b in settings["bindings"]
                        if b["trigger"]["kind"] == "shift_digit")
        self.assertEqual(digits, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
        self.assertEqual(settings["osc"]["port"], 9000)
        self.assertEqual(settings["osc"]["listen_port"], 9001)

    def test_save_and_load_roundtrip(self):
        settings = vrleft.default_settings()
        settings["osc"]["port"] = 9999
        vrleft.save_settings(settings)
        loaded = vrleft.load_settings()
        self.assertEqual(loaded["osc"]["port"], 9999)
        self.assertEqual(len(loaded["bindings"]), 10)

    def test_corrupt_file_falls_back_to_defaults(self):
        with open(vrleft.CONFIG_FILE, "w") as fh:
            fh.write("{not json")
        loaded = vrleft.load_settings()
        self.assertEqual(loaded["osc"]["port"], 9000)

    def test_partial_file_keeps_defaults(self):
        with open(vrleft.CONFIG_FILE, "w") as fh:
            json.dump({"osc": {"port": 7000}}, fh)
        loaded = vrleft.load_settings()
        self.assertEqual(loaded["osc"]["port"], 7000)
        self.assertEqual(loaded["osc"]["host"], "127.0.0.1")
        self.assertEqual(len(loaded["bindings"]), 10)

    def test_new_binding_gets_unique_id(self):
        settings = vrleft.default_settings()
        first = vrleft.new_binding(settings, {"kind": "key", "code": 1, "device": "any"})
        second = vrleft.new_binding(settings, {"kind": "key", "code": 2, "device": "any"})
        self.assertNotEqual(first["id"], second["id"])
        self.assertIs(vrleft.find_binding(settings, second["id"]), second)
        self.assertIsNone(vrleft.find_binding(settings, 9999))

    def test_binding_label(self):
        shift = {"id": 1, "trigger": {"kind": "shift_digit", "digit": 3},
                 "action": {}}
        self.assertEqual(vrleft.binding_label(shift), "Shift+3")
        key = {"id": 2, "trigger": {"kind": "key", "code": 87, "device": "any"},
               "action": {}}
        self.assertEqual(vrleft.binding_label(key), "KEY_F11 (any)")
        odd = {"id": 3, "trigger": {"kind": "key", "code": 999, "device": "t1"},
               "action": {}}
        self.assertEqual(vrleft.binding_label(odd), "0x3e7")


class ScopeTest(unittest.TestCase):
    def test_shift_digits_force_the_all_scope(self):
        settings = make_settings([], shift_digits=True)
        self.assertEqual(vrleft.monitor_scope(settings), "all")

    def test_t1_only_without_shift_digits(self):
        settings = make_settings([
            binding(1, {"kind": "key", "code": 96, "device": "t1"},
                    {"address": "/x"})], shift_digits=False)
        self.assertEqual(vrleft.monitor_scope(settings), "t1")

    def test_any_device_key_forces_the_all_scope(self):
        settings = make_settings([
            binding(1, {"kind": "key", "code": 97, "device": "any"},
                    {"address": "/x"})], shift_digits=False)
        self.assertEqual(vrleft.monitor_scope(settings), "all")


class MonitorTest(unittest.TestCase):
    """Full chain: scripted input -> engine -> OSC datagram."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="vrleft-monitor-")
        cls._saved = (vrleft.CONFIG_FILE, vrleft.CONFIG_DIR, vrleft.STATE_DIR,
                      vrleft.open_input_source)
        vrleft.CONFIG_DIR = cls.tmp
        vrleft.CONFIG_FILE = os.path.join(cls.tmp, "settings.json")
        vrleft.STATE_DIR = cls.tmp
        cls.server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        cls.server.bind(("127.0.0.1", UDP_PORT))
        cls.server.settimeout(3)

    @classmethod
    def tearDownClass(cls):
        (vrleft.CONFIG_FILE, vrleft.CONFIG_DIR, vrleft.STATE_DIR,
         vrleft.open_input_source) = cls._saved
        cls.server.close()

    def setUp(self):
        self.drain()

    def drain(self):
        self.server.settimeout(0.1)
        try:
            while True:
                self.server.recvfrom(4096)
        except socket.timeout:
            pass
        self.server.settimeout(3)

    def run_monitor(self, bindings, events, expect):
        import threading

        settings = make_settings(bindings)
        settings["osc"].update({"host": "127.0.0.1", "port": UDP_PORT,
                                "listen": False, "listen_port": UDP_PORT + 1})
        vrleft.save_settings(settings)
        source = vrleft.QueueInputSource()
        vrleft.open_input_source = lambda scope="all": source
        stop = threading.Event()
        lines = []
        thread = threading.Thread(
            target=vrleft.monitor_loop,
            kwargs={"settings": settings, "stop_event": stop,
                    "emit": lines.append},
            daemon=True)
        thread.start()
        packets = []
        try:
            time.sleep(0.2)
            for event in events:
                source._push(event)
                time.sleep(0.08)
            deadline = time.time() + 3
            while len(packets) < expect and time.time() < deadline:
                try:
                    data, _ = self.server.recvfrom(4096)
                except socket.timeout:
                    break
                packets.append(data)
        finally:
            stop.set()
            thread.join(timeout=3)
            vrleft.open_input_source = self._saved[3]
        return packets, lines

    def test_shift_digit_reaches_udp(self):
        packets, lines = self.run_monitor(
            [binding(1, {"kind": "shift_digit", "digit": 1},
                     {"address": "/avatar/parameters/One"})],
            [(vrleft.EV_KEY, LEFT_SHIFT, 1, False),
             (vrleft.EV_KEY, DIGIT_1, 1, False)],
            expect=1)
        self.assertEqual(len(packets), 1)
        address, values = vrleft.osc_decode(packets[0])
        self.assertEqual(address, "/avatar/parameters/One")
        self.assertEqual(values, [("T", True)])
        self.assertTrue(any("avatar/parameters/One" in line for line in lines))

    def test_t1_key_binding_reaches_udp(self):
        packets, _lines = self.run_monitor(
            [binding(1, {"kind": "key", "code": 98, "device": "t1"},
                     {"address": "/avatar/parameters/Key1"})],
            [(vrleft.EV_KEY, 98, 1, True)],
            expect=1)
        self.assertEqual(len(packets), 1)
        self.assertEqual(vrleft.osc_decode(packets[0])[0], "/avatar/parameters/Key1")

    def test_pulse_release_is_sent(self):
        packets, _lines = self.run_monitor(
            [binding(1, {"kind": "key", "code": 99, "device": "any"},
                     {"address": "/avatar/parameters/Tap", "pulse_ms": 40})],
            [(vrleft.EV_KEY, 99, 1, True)],
            expect=2)
        self.assertGreaterEqual(len(packets), 2)
        self.assertEqual(vrleft.osc_decode(packets[0])[1], [("T", True)])
        self.assertEqual(vrleft.osc_decode(packets[1])[1], [("F", False)])


class CliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="vrleft-cli-")
        self._saved = (vrleft.CONFIG_FILE, vrleft.CONFIG_DIR, vrleft.STATE_DIR)
        vrleft.CONFIG_DIR = self.tmp
        vrleft.CONFIG_FILE = os.path.join(self.tmp, "settings.json")
        vrleft.STATE_DIR = self.tmp

    def tearDown(self):
        (vrleft.CONFIG_FILE, vrleft.CONFIG_DIR, vrleft.STATE_DIR) = self._saved

    def test_version_flag(self):
        self.assertEqual(vrleft.main(["--version"]), 0)

    def test_send_delivers_the_message(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server.bind(("127.0.0.1", 0))
        port = server.getsockname()[1]
        server.settimeout(2)
        settings = vrleft.default_settings()
        settings["osc"]["port"] = port
        vrleft.save_settings(settings)
        try:
            code = vrleft.main(["--send", "/avatar/parameters/Cli", "bool", "true"])
            data, _ = server.recvfrom(4096)
        finally:
            server.close()
        self.assertEqual(code, 0)
        self.assertEqual(vrleft.osc_decode(data),
                         ("/avatar/parameters/Cli", [("T", True)]))

    def test_send_rejects_a_bad_type(self):
        self.assertEqual(vrleft.main(["--send", "/x", "blob", "z"]), 1)

    def test_selftest_runs(self):
        vrleft.save_settings(vrleft.default_settings())
        self.assertIn(vrleft.main(["--selftest"]), (0, 1))


if __name__ == "__main__":
    unittest.main(verbosity=2)
