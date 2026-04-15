import nrf9151, uasyncio
from modem import Modem


# ModemAsync extends Modem, replacing the blocking I/O layer with an async one.
#
# Architecture:
#   - __init__ calls super().__init__() for hardware setup, then adds async state
#   - start() launches a background _reader() task that reads chars continuously
#   - _reader() accumulates chars into lines and dispatches them:
#       * "#XMQTTMSG:" lines (+ payload line) → _msg_queue   (unsolicited)
#       * everything else                     → _cmd_buf     (command response)
#   - wait_response() awaits _cmd_event (set by _reader) instead of polling
#   - recv() awaits the next incoming MQTT message from _msg_queue
#
# Usage:
#   m = ModemAsync()
#   await m.start()          # launch reader task — call once
#   msg = await m.recv()     # (topic, payload) when a subscribed message arrives
class ModemAsync(Modem):

    _instance = None  # separate singleton from Modem

    def __init__(self):
        if self._initialized:
            return
        super().__init__()  # hardware init + sets _initialized = True
        # Command response state
        self._cmd_buf = ""
        self._cmd_expected = None
        self._cmd_event = uasyncio.Event()
        # Incoming MQTT messages: list of (topic, payload) tuples
        self._msg_queue = []
        self._msg_event = uasyncio.Event()

    # -------------------------------------------------------------------------
    # Async I/O layer (overrides Modem's blocking implementation)
    # -------------------------------------------------------------------------

    # Launch the background serial reader. Must be called once before any other method.
    async def start(self):
        uasyncio.create_task(self._reader())

    # Background task: reads one char at a time, accumulates lines.
    # After a complete "\r\n"-terminated line, calls _dispatch().
    # "#XMQTTMSG:" triggers a 3-line sequence:
    #   line 1: #XMQTTMSG: <topic_len>,<payload_len>
    #   line 2: <topic>
    #   line 3: <payload>
    async def _reader(self):
        line_buf = ""
        pending_state = None
        pending_topic = None
        while True:
            char = nrf9151.read_char()
            if char:
                line_buf += char.decode("utf-8")
                if line_buf.endswith("\r\n"):
                    line = line_buf
                    line_buf = ""
                    if not line:
                        continue
                    if pending_state == "topic":
                        pending_topic = line
                        pending_state = "payload"
                    elif pending_state == "payload":
                        self._msg_queue.append((pending_topic, line))
                        self._msg_event.set()
                        pending_state = None
                        pending_topic = None
                    elif line.startswith("#XMQTTMSG:"):
                        pending_state = "topic"
                    else:
                        self._dispatch(line)
            else:
                await uasyncio.sleep_ms(0)

    # Route a line to the active command response buffer.
    # Signals _cmd_event when the expected string or ERROR is found.
    def _dispatch(self, line: str):
        if self._cmd_expected is None:
            return
        self._cmd_buf += line + "\r\n"
        if self._cmd_expected in self._cmd_buf or "ERROR" in line:
            self._cmd_event.set()

    # Wait for a command response without blocking the event loop.
    # Returns the accumulated response string, "ERROR", or a timeout message.
    async def wait_response(self, expected: str = "OK", timeout_ms: int = 1000) -> str:
        if timeout_ms <= 0:
            raise ValueError("timeout_ms must be greater than 0")
        self._cmd_buf = ""
        self._cmd_expected = expected
        self._cmd_event.clear()
        try:
            await uasyncio.wait_for_ms(self._cmd_event.wait(), timeout_ms)
            if expected in self._cmd_buf:
                return self._cmd_buf
            return "ERROR"
        except uasyncio.TimeoutError:
            return f"No response from modem within {timeout_ms}ms"
        finally:
            self._cmd_expected = None

    async def send_cmd(self, command: str, expected: str = "OK", _num_bytes: int = 256, timeout_ms: int = 1000, is_bool: bool = True):
        self.send(command + "\r\n")
        response = await self.wait_response(expected, timeout_ms)
        if not is_bool:
            return response
        return expected in response

    # Wait for the next incoming MQTT message on any subscribed topic.
    # Returns (topic, payload) as strings.
    async def recv(self) -> tuple:
        while not self._msg_queue:
            self._msg_event.clear()
            await self._msg_event.wait()
        return self._msg_queue.pop(0)

    # -------------------------------------------------------------------------
    # Business methods (async overrides — validation reused from Modem._build_*)
    # -------------------------------------------------------------------------

    async def CFUN(self, mode: int) -> bool:
        cmd = self._build_cfun(mode)
        if await self.send_cmd(cmd, "OK", timeout_ms=5000):
            print("[Modem] CFUN set successfully to mode", mode)
            return True
        print("[Modem] Failed to set CFUN to mode", mode)
        return False

    async def mqtt_cfg(self, client_id: str, keep_alive: int = 60, clean_session: int = 0) -> bool:
        cmd = self._build_mqtt_cfg(client_id, keep_alive, clean_session)
        if await self.send_cmd(cmd, "OK", timeout_ms=1000):
            print("[Modem] MQTT configuration set successfully")
            return True
        return False

    async def get_mqtt_cfg(self) -> str:
        response = await self.send_cmd("AT#XMQTTCFG?", "OK", timeout_ms=1000, is_bool=False)
        if "ERROR" in response:
            print("[Modem] Failed to get MQTT configuration")
            return ""
        for line in response.split("\r\n"):
            if line.startswith("#XMQTTCFG"):
                print("[Modem] MQTT configuration retrieved successfully")
                return line
        return ""

    async def mqtt_conn(self, op: int, username: str, password: str, url: str, port: int, sec_tag: int = None) -> bool:
        cmd = self._build_mqtt_conn(op, username, password, url, port, sec_tag)
        if await self.send_cmd(cmd, "#XMQTTEVT: 0,0", timeout_ms=5000):
            print("[Modem] MQTT connection operation successful")
            return True
        return False

    async def is_mqtt_conn(self) -> bool:
        return await self.send_cmd("AT#XMQTTCON?", "#XMQTTCON: 1", timeout_ms=1000)

    async def mqtt_publish(self, topic: str, msg: str, qos: int = 0, retain: int = 0) -> bool:
        cmd = self._build_mqtt_publish(topic, msg, qos, retain)
        if await self.send_cmd(cmd, "OK", timeout_ms=5000):
            print("[Modem] MQTT publish successful")
            return True
        return False

    async def mqtt_subscribe(self, topic: str, qos: int = 0) -> bool:
        cmd = self._build_mqtt_subscribe(topic, qos)
        if await self.send_cmd(cmd, "#XMQTTEVT: 7,0", timeout_ms=5000):
            print("[Modem] MQTT subscribe successful")
            return True
        return False

    async def write_certificate(self, sec_tag: int, cert_type: int, content: str, psw: str = None, sha256: str = None) -> bool:
        cmd = self._build_write_certificate(sec_tag, cert_type, content, psw, sha256)
        if await self.send_cmd(cmd, "OK", timeout_ms=5000):
            print("[Modem] Certificate written successfully")
            return True
        return False

    async def list_certificate(self, sec_tag: int, cert_type: int = None) -> str:
        cmd = self._build_list_certificate(sec_tag, cert_type)
        response = await self.send_cmd(cmd, "OK", timeout_ms=5000, is_bool=False)
        if "ERROR" in response:
            print("[Modem] Failed to list certificate")
            return ""
        for line in response.split("\r\n"):
            if line.startswith(f"%CMNG: {sec_tag},{cert_type if cert_type is not None else ''}"):
                print("[Modem] Certificate listed successfully")
                return response
        return ""

    async def read_certificate(self, sec_tag: int, cert_type: int) -> str:
        cmd = self._build_read_certificate(sec_tag, cert_type)
        response = await self.send_cmd(cmd, "OK", timeout_ms=5000, is_bool=False)
        if "ERROR" in response:
            print("[Modem] Failed to read certificate")
            return ""
        for line in response.split("\r\n"):
            if line.startswith(f"%CMNG: {sec_tag},{cert_type}"):
                print("[Modem] Certificate read successfully")
                return response
        return ""

    async def delete_certificate(self, sec_tag: int, cert_type: int) -> bool:
        cmd = self._build_delete_certificate(sec_tag, cert_type)
        if await self.send_cmd(cmd, "OK", timeout_ms=5000):
            print("[Modem] Certificate deleted successfully")
            return True
        return False
