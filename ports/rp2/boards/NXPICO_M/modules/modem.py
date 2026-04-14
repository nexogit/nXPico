import nrf9151, time

# Modem class to manage the nRF9151 modem, providing methods to send commands and read responses.
# Class use nrf9151 module writte in C to interact with the modem hardware on UART0.
# Class has simple write and read methods but also methods for functionality. this methods wait for the modem response and return True if the expected response is received, False otherwise.
class Modem:

    _instance = None

    # Implementing the singleton pattern to ensure that only one instance of the Modem class exists.
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    # The __init__ method initializes the modem by setting up valid CFUN modes and clearing any initial data from the modem. It ensures that the modem is ready for communication.
    def __init__(self):
        self._CFUN_VALID_MODES = {1, 2, 4, 20, 21, 30, 31, 40, 41, 44}
        nrf9151.init()
        nrf9151.read(256)  # Clear any initial data from the modem

        
    # Send data to the modem using UART0. Data must be bytes or a string
    # This methods does not controll if the message is correctly sent and parsed
    def send(self, data: bytes) -> None:
        nrf9151.write(data)

    # Read data from the modem using UART0. 
    # num_bytes must be a positive integer otherwise a ValueError is raised.
    # This method returns the raw bytes read from the modem, without any parsing or decoding.
    def read(self, num_bytes: int) -> bytes:
        if type(num_bytes) is not int:
            raise ValueError("num_bytes must be an integer")
        if num_bytes <= 0:
            raise ValueError("num_bytes must be greater than 0")
        return nrf9151.read(num_bytes)

    # Wait for a response from the modem, checking for an expected string in the response.
    # This method reads data from the modem in a loop until:
    #  - the expected string is found
    #  - "ERROR" is found
    #  - timeout occurs. 
    # The response is returned as a string.
    # timeout_ms must be a positive integer, otherwise a ValueError is raised.
    # num_bytes must be a positive integer, otherwise a ValueError is raised.
    # the maximum number of bytes read in each iteration is determined by num_bytes, which must be a positive integer. If num_bytes is not a positive integer, a ValueError is raised. 
    # The method will return a message indicating that no response was received within the timeout period if the timeout occurs.
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

    # Send a command to the modem and wait for an expected response.
    # This method sends a command to the modem and waits for a response that contains the expected string.
    # this method add at the end of the command the carriage return and line feed characters ("\r\n") to ensure that the modem correctly interprets the command.
    # The method returns True if the expected response is received, and False otherwise.
    # command must be a string, otherwise a TypeError is raised.
    # expected must be a string, otherwise a TypeError is raised.
    # num_bytes must be a positive integer, otherwise a ValueError is raised. num_of bytes is about the response
    def send_cmd(self, command: str, expected: str = "OK", num_bytes: int=256, timeout_ms: int = 1000, is_bool: bool=True) -> bool:
        self.send(command + "\r\n")
        if not is_bool:
            return self.wait_response(expected, num_bytes, timeout_ms)
        return True if expected in self.wait_response(expected, num_bytes, timeout_ms) else False


    # Set the modem's functionality level using the CFUN command. 
    # This method validates the input mode against a set of valid modes and sends the appropriate command to the modem.
    # The method returns True if the modem responds with the expected response, and False otherwise.
    # mode must be an integer and one of the valid modes defined in _CFUN_VALID_MODES, otherwise a ValueError is raised.
    def CFUN(self, mode: int) -> bool:
        if type(mode) is not int:
            raise ValueError("mode must be an integer")
        if mode not in self._CFUN_VALID_MODES:
            raise ValueError(f"mode must be one of {sorted(self._CFUN_VALID_MODES)}")
        if self.send_cmd(f"AT+CFUN={mode}", "OK", 16, timeout_ms=5000):
            print("[Modem] CFUN set successfully to mode", mode)
            return True
        else:
            print("[Modem] Failed to set CFUN to mode", mode)
            return False

    # Configure MQTT settings on the modem using the MQTTCFG command.
    # This method validates the input parameters and sends the appropriate command to the modem to configure MQTT 
    # The method returns True if the modem responds with the expected response, and False otherwise.
    # client_id must be a string, otherwise a ValueError is raised.
    # keep_alive must be an integer greater than 0, otherwise a ValueError is raised
    # clean_session must be an integer and either 0 or 1, otherwise a ValueError is raised.
    def mqtt_cfg(self, client_id: str, keep_alive: int=60, clean_session:int=0) -> bool:
        if client_id is None or type(client_id) is not str:
            raise ValueError("client_id must be a string")
        if keep_alive <= 0:
            raise ValueError("keep_alive must be an integer greater than 0")
        if type(clean_session) is not int or clean_session not in (0, 1):
            raise ValueError("clean_session must be an integer and either 0 or 1")
        if self.send_cmd(f'AT#XMQTTCFG="{client_id}",{keep_alive},{clean_session}', "OK", 16, timeout_ms=1000):
            print("[Modem] MQTT configuration set successfully")
            return True
        return False
    
    # Get the current MQTT configuration from the modem using the MQTTCFG? command.
    # This method sends a command to the modem to retrieve the current MQTT configuration and waits for the response. 
    # The method returns the MQTT configuration as a string if the modem responds successfully
        # Get the current MQTT configuration from the modem using the MQTTCFG? command.
    # This method sends a command to the modem to retrieve the current MQTT configuration and waits for the response. 
    # The method returns the MQTT configuration as a string if the modem responds successfully
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

    # Establish or disconnect an MQTT connection using the MQTTCONN command.
    # This method validates the input parameters and sends the appropriate command to the modem to manage the
    # MQTT connection. The method returns True if the modem responds with the expected response, and False otherwise.
    # op must be an integer and either 0, 1 or 2, otherwise a ValueError is raised. 0 for disconnect, 1 for connect IPv4, 2 for connect IPv6
    # username must be a string, otherwise a ValueError is raised.
    # password must be a string, otherwise a ValueError is raised.
    # url must be a string, otherwise a ValueError is raised.
    # port must be an integer greater than 0 and less than or equal to 65535, otherwise a ValueError is raised.
    # sec_tag must be an integer, otherwise a ValueError is raised. default value is None. if is None teh sec_tag is ignored.
    def mqtt_conn(self, op:int, username:str, password:str, url:str, port:int, sec_tag:int=None) -> bool:
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
        if sec_tag is not None and type(sec_tag) is not int :
            raise ValueError("sec_tag must be an integer")
        if sec_tag is None:
            if self.send_cmd(f'AT#XMQTTCONN={op},"{username}","{password}","{url}",{port}', "#XMQTTEVT: 0,0", 16, timeout_ms=5000):
                print("[Modem] MQTT connection operation successful")
                return True
        else:
            if self.send_cmd(f'AT#XMQTTCONN={op},"{username}","{password}","{url}",{port},{sec_tag}', "#XMQTTEVT: 0,0", 16, timeout_ms=5000):
                print("[Modem] MQTT connection operation successful")
                return True
        return False

    # Check if the modem is currently connected to an MQTT broker.
    # Return True if the modem is connected to an MQTT broker, and False otherwise.
    def is_mqtt_conn(self):
        return self.send_cmd("AT#XMQTTCON?", "#XMQTTCON: 1", 16, timeout_ms=1000)


    # Publish a message to an MQTT topic using the MQTTPUB command.
    # This method validates the input parameters and sends the appropriate command to the modem to publish a message to an MQTT topic. The method returns True if the modem responds with the expected response, and False otherwise.
    # topic must be a string, otherwise a ValueError is raised.
    # msg must be a string, otherwise a ValueError is raised.
    # qos must be an integer and either 0, 1 or 2, otherwise a ValueError is raised.
    # retain must be an integer and either 0 or 1, otherwise a ValueError is raised.
    # this method wait for 5 seconds a response with the expected string "OK" which indicate that the message was published successfully.
    def mqtt_publish(self, topic:str, msg:str, qos:int=0, retain:int=0) -> bool:
        if type(topic) is not str:
            raise ValueError("topic must be a string")
        if type(msg) is not str:
            raise ValueError("msg must be a string")
        if type(qos) is not int or qos not in (0, 1, 2):
            raise ValueError("qos must be an integer and either 0, 1 or 2")
        if type(retain) is not int or retain not in (0, 1):
            raise ValueError("retain must be an integer and either 0 or 1")
        if self.send_cmd(f'AT#XMQTTPUB="{topic}","{msg}",{qos},{retain}', "OK", 16, timeout_ms=5000):
            print("[Modem] MQTT publish successful")
            return True
        return False
        
    # Subscribe to an MQTT topic using the MQTTUB command.
    # This method validates the input parameters.
    # topic must be a string, otherwise a ValueError is raised.
    # qos must be an integer and either 0, 1 or 2, otherwise a ValueError is raised.
    # The method returns True if the modem responds with the expected response
    def mqtt_subscribe(self, topic:str, qos:int=0) -> bool:
        if type(topic) is not str:
            raise ValueError("topic must be a string")
        if type(qos) is not int or qos not in (0, 1, 2):
            raise ValueError("qos must be an integer and either 0, 1 or 2")
        if self.send_cmd(f'AT#XMQTTSUB="{topic}",{qos}', "#XMQTTEVT: 7,0", 16, timeout_ms=5000):
            print("[Modem] MQTT subscribe successful")
            return True
        return False


    # Write a certificate to the modem's secure storage using the CMNG command.
    # This method validates the input parameters and sends the appropriate command to the modem to write a certificate to the modem's secure storage. 
    # The method returns True if the modem responds with the expected response
    # sec_tag must be an integer and between 0 and 2552147483647, otherwise a ValueError is raised.
    # cert_type must be an integer and one of the following values: 0=Root CA, 1=Client cert, 2=Client private key, 3=PSK, 4=PSK identity, 5=Public key, 6=Device identity public  key, 7=Reserved, 8=Endorsement key, 9=Ownership key, 10=Nordic identity root CA, 11=Nordic base public key, 13=Asset encryption key. 
    # If cert_type is not one of these values, a ValueError is raised.
    # content must be a string, otherwise a ValueError is raised. Thihs is the certificate content that will be written to the modem's secure storage.
    # psw is an optional parameter that must be a string if provided, otherwise a ValueError is raised.
    # sha256 is an optional parameter that must be a string if provided, otherwise a ValueError is raised.
    def write_certificate(self, sec_tag:int, cert_type:int, content:str, psw:str=None, sha256:str=None) -> bool:
        if type(sec_tag) is not int or not 0 <= sec_tag <= 2552147483647:
            raise ValueError("sec_tag must be an integer and beetween 0 and 2552147483647")
        if type(cert_type) is not int or cert_type not in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13):
            raise ValueError("cert_type must be an integer: 0=Root CA, 1=Client cert, 2=Client private key, 3=PSK, 4=PSK identity, 5=Public key, 6=Device identity public key, 7=Reserved, 8=Endorsement key, 9=Ownership key, 10=Nordic identity root CA, 11=Nordic base public key, 13=Asset encryption key")
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
        if self.send_cmd(cmd, "OK", 16, timeout_ms=5000):
            print("[Modem] Certificate written successfully")
            return True
        return False


    # List certificates stored in the modem's secure storage using the CMNG command with opcode 1.
    # sec_tag must be an integer between 0 and 2552147483647, otherwise a ValueError is raised.
    # cert_type is optional. If provided, must be a valid type integer; only that credential type is listed.
    # Returns the raw modem response string on success, or an empty string on failure.
    def list_certificate(self, sec_tag:int, cert_type:int=None) -> str:
        if type(sec_tag) is not int or not 0 <= sec_tag <= 2552147483647:
            raise ValueError("sec_tag must be an integer and beetween 0 and 2552147483647")
        cmd = f'AT%CMNG=1,{sec_tag}'
        if cert_type is not None:
            if type(cert_type) is not int or cert_type not in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13):
                raise ValueError("type must be an integer: 0=Root CA, 1=Client cert, 2=Client private key, 3=PSK, 4=PSK identity, 5=Public key, 6=Device identity public key, 7=Reserved, 8=Endorsement key, 9=Ownership key, 10=Nordic identity root CA, 11=Nordic base public key, 13=Asset encryption key")
            cmd += f',{cert_type}'
        response = self.send_cmd(cmd, "OK", 1024, timeout_ms=5000, is_bool=False)
        if "ERROR" in response:
            print("[Modem] Failed to get certificate")
            return ""
        for line in response.split("\r\n"):
            if line.startswith(f"%CMNG: {sec_tag},{cert_type if cert_type is not None else ''}"):
                print("[Modem] Certificate listed successfully")
                return response
        return ""

    
    # Read the content of a specific certificate from the modem's secure storage using the CMNG command with opcode 2.
    # sec_tag must be an integer between 0 and 2552147483647, otherwise a ValueError is raised.
    # cert_type must be a valid type integer, otherwise a ValueError is raised.
    # Returns the raw modem response string on success, or an empty string on failure.
    def read_certificate(self, sec_tag:int, cert_type:int) -> str:
        if type(sec_tag) is not int or not 0 <= sec_tag <= 2552147483647:
            raise ValueError("sec_tag must be an integer and beetween 0 and 2552147483647")
        if type(cert_type) is not int or cert_type not in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13):
            raise ValueError("type must be an integer: 0=Root CA, 1=Client cert, 2=Client private key, 3=PSK, 4=PSK identity, 5=Public key, 6=Device identity public key, 7=Reserved, 8=Endorsement key, 9=Ownership key, 10=Nordic identity root CA, 11=Nordic base public key, 13=Asset encryption key")
        cmd = f'AT%CMNG=2,{sec_tag}, {cert_type}'
        print(cmd)
        response = self.send_cmd(cmd, "OK", 1024, timeout_ms=5000, is_bool=False)
        if "ERROR" in response:
            print("[Modem] Failed to get certificate")
            return ""
        for line in response.split("\r\n"):
            if line.startswith(f"%CMNG: {sec_tag},{cert_type if cert_type is not None else ''}"):
                print("[Modem] Certificate read successfully")
                return response
        return ""

    


    
    # Delete a specific certificate from the modem's secure storage using the CMNG command with opcode 3.
    # sec_tag must be an integer between 0 and 2552147483647, otherwise a ValueError is raised.
    # cert_type must be a valid type integer, otherwise a ValueError is raised.
    # Returns True if the modem responds with OK, False otherwise.
    def delete_certificate(self, sec_tag:int, cert_type:int) -> str:
        if type(sec_tag) is not int or not 0 <= sec_tag <= 2552147483647:
            raise ValueError("sec_tag must be an integer and beetween 0 and 2552147483647")
        if type(cert_type) is not int or cert_type not in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13):
            raise ValueError("type must be an integer: 0=Root CA, 1=Client cert, 2=Client private key, 3=PSK, 4=PSK identity, 5=Public key, 6=Device identity public key, 7=Reserved, 8=Endorsement key, 9=Ownership key, 10=Nordic identity root CA, 11=Nordic base public key, 13=Asset encryption key")
        if self.send_cmd(f'AT%CMNG=3,{sec_tag}, {cert_type}', "OK", 16, timeout_ms=5000):
            print("[Modem] Certificate deleted successfully")
            return True
        return False