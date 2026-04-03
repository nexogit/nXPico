from machine import Pin
import neopixel
from micropython import const

RED     = (255, 0,   0)
GREEN   = (0,   255, 0)
BLUE    = (0,   0,   255)
WHITE   = (255, 255, 255)
YELLOW  = (255, 255, 0)
CYAN    = (0,   255, 255)
MAGENTA = (255, 0,   255)
ORANGE  = (255, 128, 0)
OFF     = (0,   0,   0)

# This is a simple wrapper around the neopixel library to control a single RGB LED built on the nXPico_M board
# This class can be used to set a specific color using set_color() method or to use a predefined color using the shortcut methods (red(), green(), blue(), white(), yellow(), cyan(), magenta(), orange(), off())
class Led():
    
    # Initialize the LED on pin 23 (WS2812) with 1 LED setting to off (0, 0, 0) as default value
    def __init__(self):
        self._leds = const(1)
        self._pin = Pin(23, Pin.OUT)
        self._value = [0,0,0]
        self._np = neopixel.NeoPixel(self._pin, self._leds)
        self.set_color([0,0,0])
    
    # Return a copy of the value of the LED as a list of 3 integers (r, g, b)
    def get_value(self) -> list:
        return self._value.copy()
    
    # Set the value of the LED with a list of 3 integers (r, g, b)
    def red(self) -> None:     self.set_color(list(RED))
    def green(self) -> None:   self.set_color(list(GREEN))
    def blue(self) -> None:    self.set_color(list(BLUE))
    def white(self) -> None:   self.set_color(list(WHITE))
    def yellow(self) -> None:  self.set_color(list(YELLOW))
    def cyan(self) -> None:    self.set_color(list(CYAN))
    def magenta(self) -> None: self.set_color(list(MAGENTA))
    def orange(self) -> None:  self.set_color(list(ORANGE))
    def off(self) -> None:     self.set_color(list(OFF))

    # Set the value of the LED with a list of 3 integers (r, g, b). 
    # Each value must be between 0 and 255, otherwise a ValueError is raised. 
    # The method updates the internal state of the LED and writes the new color to the hardware using the neopixel library.
    def set_color(self, value: list) -> None:
        if not isinstance(value, list) or len(value) != 3:
            raise ValueError("RGB value must be a list of 3 elements: (r, g, b)")
        val = value.copy()
        for v in value:
            if type(v)  is not int:
                raise ValueError("RGB values must be integers")
            if v < 0 or v > 255:
                raise ValueError("RGB values must be between 0 and 255")
        for i in range(self._leds):
            self._np[i] = val

        self._value = val
        self._np.write()



