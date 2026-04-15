import nrf9151, time

_CERT_VALID_TYPES = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13)
_CERT_TYPE_ERR = ("cert_type must be an integer: 0=Root CA, 1=Client cert, 2=Client private key, "
                  "3=PSK, 4=PSK identity, 5=Public key, 6=Device identity public key, 7=Reserved, "
                  "8=Endorsement key, 9=Ownership key, 10=Nordic identity root CA, "
                  "11=Nordic base public key, 13=Asset encryption key")


class Modem:

    _instance = None
    _CFUN_VALID_MODES = {1, 2, 4, 20, 21, 30, 31, 40, 41, 44}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        nrf9151.init()
        nrf9151.read(256)  # Clear any initial data from the modem

    # -------------------------------------------------------------------------
    # Low-level I/O
    # -------------------------------------------------------------------------

    def send(self, data: bytes) -> None:
        nrf9151.write(data)

    def read(self, num_bytes: int) -> bytes:
        if type(num_bytes) is not int:
            raise ValueError("num_bytes must be an integer")
        if num_bytes <= 0:
            raise ValueError("num_bytes must be greater than 0")
        return nrf9151.read(num_bytes)

    def wait_response(self, expected: str = "OK", num_bytes: int = 256, timeout_ms: int = 1000) -> str:
        if timeout_ms <= 0:
            raise ValueError("timeout_ms must be greater than 0")
        if num_bytes <= 0:
            raise ValueError("num_bytes must be greater than 0")
        deadline = time.ticks_add(time.ticks_ms(), timeout_ms)
        response = ""
        while time.ticks_diff(deadline, time.ticks_ms()) > 0:
            chunk = self.read(num_bytes)
            if chunk:
                response += chunk.decode("utf-8")
                if expected in response:
                    return response
                if "ERROR" in response:
                    return "ERROR"
            time.sleep_ms(10)
        return f"No response from modem within {timeout_ms}ms"

    def send_cmd(self, command: str, expected: str = "OK", num_bytes: int = 256, timeout_ms: int = 1000, is_bool: bool = True):
        self.send(command + "\r\n")
        if not is_bool:
            return self.wait_response(expected, num_bytes, timeout_ms)
        return expected in self.wait_response(expected, num_bytes, timeout_ms)

    # -------------------------------------------------------------------------
    # Private helpers: validate inputs and build AT command strings.
    # Shared with ModemAsync to avoid duplicating logic.
    # -------------------------------------------------------------------------

    def _build_cfun(self, mode: int) -> str:
        if type(mode) is not int:
            raise ValueError("mode must be an integer")
        if mode not in self._CFUN_VALID_MODES:
            raise ValueError(f"mode must be one of {sorted(self._CFUN_VALID_MODES)}")
        return f"AT+CFUN={mode}"

    def _build_mqtt_cfg(self, client_id: str, keep_alive: int, clean_session: int) -> str:
        if client_id is None or type(client_id) is not str:
            raise ValueError("client_id must be a string")
        if keep_alive <= 0:
            raise ValueError("keep_alive must be an integer greater than 0")
        if type(clean_session) is not int or clean_session not in (0, 1):
            raise ValueError("clean_session must be an integer and either 0 or 1")
        return f'AT#XMQTTCFG="{client_id}",{keep_alive},{clean_session}'

    def _build_mqtt_conn(self, op: int, username: str, password: str, url: str, port: int, sec_tag) -> str:
        if type(op) is not int or op not in (0, 1, 2):
            raise ValueError("op must be an integer and 0, 1 or 2: Disconnect, Connect IPv4, Connect IPv6")
        if type(username) is not str:
            raise ValueError("username must be a string")
        if type(password) is not str:
            raise ValueError("password must be a string")
        if type(url) is not str:
            raise ValueError("url must be a string")
        if type(port) is not int or port <= 0 or port > 65535:
            raise ValueError("port must be an integer greater than 0 and less than or equal to 65535")
        if sec_tag is not None and type(sec_tag) is not int:
            raise ValueError("sec_tag must be an integer")
        cmd = f'AT#XMQTTCONN={op},"{username}","{password}","{url}",{port}'
        if sec_tag is not None:
            cmd += f',{sec_tag}'
        return cmd

    def _build_mqtt_publish(self, topic: str, msg: str, qos: int, retain: int) -> str:
        if type(topic) is not str:
            raise ValueError("topic must be a string")
        if type(msg) is not str:
            raise ValueError("msg must be a string")
        if type(qos) is not int or qos not in (0, 1, 2):
            raise ValueError("qos must be an integer and either 0, 1 or 2")
        if type(retain) is not int or retain not in (0, 1):
            raise ValueError("retain must be an integer and either 0 or 1")
        return f'AT#XMQTTPUB="{topic}","{msg}",{qos},{retain}'

    def _build_mqtt_subscribe(self, topic: str, qos: int) -> str:
        if type(topic) is not str:
            raise ValueError("topic must be a string")
        if type(qos) is not int or qos not in (0, 1, 2):
            raise ValueError("qos must be an integer and either 0, 1 or 2")
        return f'AT#XMQTTSUB="{topic}",{qos}'

    def _build_write_certificate(self, sec_tag: int, cert_type: int, content: str, psw, sha256) -> str:
        if type(sec_tag) is not int or not 0 <= sec_tag <= 2552147483647:
            raise ValueError("sec_tag must be an integer and between 0 and 2552147483647")
        if type(cert_type) is not int or cert_type not in _CERT_VALID_TYPES:
            raise ValueError(_CERT_TYPE_ERR)
        if type(content) is not str:
            raise ValueError("content must be a string")
        if psw is not None and type(psw) is not str:
            raise ValueError("psw must be a string")
        if sha256 is not None and type(sha256) is not str:
            raise ValueError("sha256 must be a string")
        cmd = f'AT%CMNG=0,{sec_tag},{cert_type},"{content}"'
        if psw is not None:
            cmd += f',"{psw}"'
        if sha256 is not None:
            cmd += f',"{sha256}"'
        return cmd

    def _build_list_certificate(self, sec_tag: int, cert_type) -> str:
        if type(sec_tag) is not int or not 0 <= sec_tag <= 2552147483647:
            raise ValueError("sec_tag must be an integer and between 0 and 2552147483647")
        if cert_type is not None:
            if type(cert_type) is not int or cert_type not in _CERT_VALID_TYPES:
                raise ValueError(_CERT_TYPE_ERR)
        cmd = f'AT%CMNG=1,{sec_tag}'
        if cert_type is not None:
            cmd += f',{cert_type}'
        return cmd

    def _build_read_certificate(self, sec_tag: int, cert_type: int) -> str:
        if type(sec_tag) is not int or not 0 <= sec_tag <= 2552147483647:
            raise ValueError("sec_tag must be an integer and between 0 and 2552147483647")
        if type(cert_type) is not int or cert_type not in _CERT_VALID_TYPES:
            raise ValueError(_CERT_TYPE_ERR)
        return f'AT%CMNG=2,{sec_tag},{cert_type}'

    def _build_delete_certificate(self, sec_tag: int, cert_type: int) -> str:
        if type(sec_tag) is not int or not 0 <= sec_tag <= 2552147483647:
            raise ValueError("sec_tag must be an integer and between 0 and 2552147483647")
        if type(cert_type) is not int or cert_type not in _CERT_VALID_TYPES:
            raise ValueError(_CERT_TYPE_ERR)
        return f'AT%CMNG=3,{sec_tag},{cert_type}'

    # -------------------------------------------------------------------------
    # Business methods (synchronous)
    # -------------------------------------------------------------------------

    def CFUN(self, mode: int) -> bool:
        cmd = self._build_cfun(mode)
        if self.send_cmd(cmd, "OK", 16, timeout_ms=5000):
            print("[Modem] CFUN set successfully to mode", mode)
            return True
        print("[Modem] Failed to set CFUN to mode", mode)
        return False

    def mqtt_cfg(self, client_id: str, keep_alive: int = 60, clean_session: int = 0) -> bool:
        cmd = self._build_mqtt_cfg(client_id, keep_alive, clean_session)
        if self.send_cmd(cmd, "OK", 16, timeout_ms=1000):
            print("[Modem] MQTT configuration set successfully")
            return True
        return False

    def get_mqtt_cfg(self) -> str:
        response = self.send_cmd("AT#XMQTTCFG?", "OK", 256, timeout_ms=1000, is_bool=False)
        if "ERROR" in response:
            print("[Modem] Failed to get MQTT configuration")
            return ""
        for line in response.split("\r\n"):
            if line.startswith("#XMQTTCFG"):
                print("[Modem] MQTT configuration retrieved successfully")
                return line
        return ""

    def mqtt_conn(self, op: int, username: str, password: str, url: str, port: int, sec_tag: int = None) -> bool:
        cmd = self._build_mqtt_conn(op, username, password, url, port, sec_tag)
        if self.send_cmd(cmd, "#XMQTTEVT: 0,0", 16, timeout_ms=5000):
            print("[Modem] MQTT connection operation successful")
            return True
        return False

    def is_mqtt_conn(self) -> bool:
        return self.send_cmd("AT#XMQTTCON?", "#XMQTTCON: 1", 16, timeout_ms=1000)

    def mqtt_publish(self, topic: str, msg: str, qos: int = 0, retain: int = 0) -> bool:
        cmd = self._build_mqtt_publish(topic, msg, qos, retain)
        if self.send_cmd(cmd, "OK", 16, timeout_ms=5000):
            print("[Modem] MQTT publish successful")
            return True
        return False

    def mqtt_subscribe(self, topic: str, qos: int = 0) -> bool:
        cmd = self._build_mqtt_subscribe(topic, qos)
        if self.send_cmd(cmd, "#XMQTTEVT: 7,0", 16, timeout_ms=5000):
            print("[Modem] MQTT subscribe successful")
            return True
        return False

    def write_certificate(self, sec_tag: int, cert_type: int, content: str, psw: str = None, sha256: str = None) -> bool:
        cmd = self._build_write_certificate(sec_tag, cert_type, content, psw, sha256)
        if self.send_cmd(cmd, "OK", 16, timeout_ms=5000):
            print("[Modem] Certificate written successfully")
            return True
        return False

    def list_certificate(self, sec_tag: int, cert_type: int = None) -> str:
        cmd = self._build_list_certificate(sec_tag, cert_type)
        response = self.send_cmd(cmd, "OK", 1024, timeout_ms=5000, is_bool=False)
        if "ERROR" in response:
            print("[Modem] Failed to list certificate")
            return ""
        for line in response.split("\r\n"):
            if line.startswith(f"%CMNG: {sec_tag},{cert_type if cert_type is not None else ''}"):
                print("[Modem] Certificate listed successfully")
                return response
        return ""

    def read_certificate(self, sec_tag: int, cert_type: int) -> str:
        cmd = self._build_read_certificate(sec_tag, cert_type)
        response = self.send_cmd(cmd, "OK", 1024, timeout_ms=5000, is_bool=False)
        if "ERROR" in response:
            print("[Modem] Failed to read certificate")
            return ""
        for line in response.split("\r\n"):
            if line.startswith(f"%CMNG: {sec_tag},{cert_type}"):
                print("[Modem] Certificate read successfully")
                return response
        return ""

    def delete_certificate(self, sec_tag: int, cert_type: int) -> bool:
        cmd = self._build_delete_certificate(sec_tag, cert_type)
        if self.send_cmd(cmd, "OK", 16, timeout_ms=5000):
            print("[Modem] Certificate deleted successfully")
            return True
        return False
