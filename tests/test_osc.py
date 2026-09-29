#!/usr/bin/env python3
"""OSC encoder / decoder / socket tests for VRLeft."""

import importlib.machinery
import importlib.util
import os
import socket
import struct
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "VRLeft")

loader = importlib.machinery.SourceFileLoader("vrleft", SCRIPT)
spec = importlib.util.spec_from_loader("vrleft", loader)
vrleft = importlib.util.module_from_spec(spec)
loader.exec_module(vrleft)


class EncodeTest(unittest.TestCase):
    def test_bool_true(self):
        self.assertEqual(vrleft.osc_encode("/a", "bool", True),
                         b"/a\0\0,T\0\0")

    def test_bool_false(self):
        self.assertEqual(vrleft.osc_encode("/a", "bool", False),
                         b"/a\0\0,F\0\0")

    def test_int(self):
        data = vrleft.osc_encode("/x", "int", 7)
        self.assertEqual(data[:4], b"/x\0\0")
        self.assertEqual(data[4:8], b",i\0\0")
        self.assertEqual(struct.unpack(">i", data[8:12])[0], 7)

    def test_float(self):
        data = vrleft.osc_encode("/x", "float", 1.5)
        self.assertEqual(struct.unpack(">f", data[8:12])[0], 1.5)

    def test_string_is_padded(self):
        data = vrleft.osc_encode("/x", "string", "hi")
        self.assertTrue(data.startswith(b"/x\0\0,s\0\0"))
        self.assertEqual(len(data) % 4, 0)
        self.assertTrue(data.endswith(b"hi\0\0"))

    def test_address_must_be_absolute(self):
        with self.assertRaises(ValueError):
            vrleft.osc_encode("avatar/parameters/X", "bool", True)

    def test_unknown_type(self):
        with self.assertRaises(ValueError):
            vrleft.osc_encode("/x", "blob", b"123")


class DecodeTest(unittest.TestCase):
    def roundtrip(self, osc_type, value):
        address, values = vrleft.osc_decode(
            vrleft.osc_encode("/avatar/parameters/Thing", osc_type, value))
        self.assertEqual(address, "/avatar/parameters/Thing")
        self.assertEqual(len(values), 1)
        return values[0]

    def test_roundtrip_bool(self):
        self.assertEqual(self.roundtrip("bool", True), ("T", True))
        self.assertEqual(self.roundtrip("bool", False), ("F", False))

    def test_roundtrip_int(self):
        self.assertEqual(self.roundtrip("int", -42), ("i", -42))

    def test_roundtrip_float(self):
        tag, value = self.roundtrip("float", 0.25)
        self.assertEqual(tag, "f")
        self.assertAlmostEqual(value, 0.25, places=5)

    def test_roundtrip_string(self):
        self.assertEqual(self.roundtrip("string", "wave"), ("s", "wave"))

    def test_rejects_garbage(self):
        with self.assertRaises(ValueError):
            vrleft.osc_decode(b"not osc")
        with self.assertRaises(ValueError):
            vrleft.osc_decode(b"/a\0\0no comma\0\0\0")

    def test_multiple_values(self):
        data = (vrleft._pad(b"/two\0") + b",is\0" + struct.pack(">i", 5)
                + vrleft._pad(b"ok\0"))
        address, values = vrleft.osc_decode(data)
        self.assertEqual(address, "/two")
        self.assertEqual(values, [("i", 5), ("s", "ok")])


class SocketTest(unittest.TestCase):
    def setUp(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server.bind(("127.0.0.1", 0))
        self.port = self.server.getsockname()[1]
        self.server.settimeout(2)

    def tearDown(self):
        self.server.close()

    def test_sender_delivers_a_datagram(self):
        sender = vrleft.OscSender("127.0.0.1", self.port)
        try:
            self.assertTrue(sender.send("/avatar/parameters/VRLeft", "bool", True))
            data, _ = self.server.recvfrom(4096)
            address, values = vrleft.osc_decode(data)
            self.assertEqual(address, "/avatar/parameters/VRLeft")
            self.assertEqual(values, [("T", True)])
            self.assertEqual(sender.sent, 1)
            self.assertIsNone(sender.last_error)
        finally:
            sender.close()

    def test_listener_reports_received_messages(self):
        got = []
        listener = vrleft.OscListener(0, lambda address, values: got.append(
            (address, values)))
        self.assertIsNone(listener.error)
        listener.start()
        try:
            port = listener._sock.getsockname()[1]
            client = vrleft.OscSender("127.0.0.1", port)
            client.send("/avatar/parameters/Ping", "string", "hello")
            client.close()
            deadline = time.time() + 2
            while not got and time.time() < deadline:
                time.sleep(0.02)
        finally:
            listener.close()
            listener.join(timeout=2)
        self.assertEqual(got, [("/avatar/parameters/Ping", [("s", "hello")])])

    def test_listener_reports_a_bind_error(self):
        # Same wildcard address on both sockets: every platform reports the
        # conflict (Windows only refuses *overlapping* binds reliably).
        blocker = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        blocker.bind(("", 0))
        port = blocker.getsockname()[1]
        try:
            listener = vrleft.OscListener(port, lambda *_: None)
            self.assertIsNotNone(listener.error)
        finally:
            blocker.close()


class ValueParsingTest(unittest.TestCase):
    def test_parse_bool(self):
        for text, expected in (("true", True), ("1", True), ("no", False),
                               ("FALSE", False), ("on", True)):
            self.assertEqual(vrleft.parse_value("bool", text), expected)

    def test_parse_numbers(self):
        self.assertEqual(vrleft.parse_value("int", "0x10"), 16)
        self.assertEqual(vrleft.parse_value("float", "1.5"), 1.5)
        self.assertEqual(vrleft.parse_value("string", " hi "), "hi")

    def test_bad_number_raises(self):
        with self.assertRaises(ValueError):
            vrleft.parse_value("int", "banana")

    def test_format_value(self):
        self.assertEqual(vrleft.format_value(True), "true")
        self.assertEqual(vrleft.format_value(0.5), "0.5")
        self.assertEqual(vrleft.format_value(3), "3")


if __name__ == "__main__":
    unittest.main(verbosity=2)
