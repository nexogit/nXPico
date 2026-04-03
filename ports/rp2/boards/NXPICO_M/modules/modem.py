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
    def _wait_response(self, expected: str = "OK", num_bytes: int = 256, timeout_ms: int = 1000) -> str:
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
    # command must be a string, otherwise a ValueError is raised.
    # expected must be a string, otherwise a ValueError is raised.
    # num_bytes must be a positive integer, otherwise a ValueError is raised. num_of bytes is about the response
    def send_cmd(self, command: str, expected: str = "OK", num_bytes: int=256, timeout_ms: int = 1000) -> bool:
        self.send(command + "\r\n")
        return True if expected in self._wait_response(expected, num_bytes, timeout_ms) else False


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