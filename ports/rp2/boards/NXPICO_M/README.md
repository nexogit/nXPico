# nXPico M — MicroPython Board Definition

**Vendor:** neXo
**MCU:** RP2350A (ARM Cortex-M33 dual-core / RISC-V dual-core, 150 MHz)  

---

## Hardware Overview

| Component | Details |
|-----------|---------|
| MCU | RP2350A QFN-60 |
| Flash | W25Q32J — 4 MB QSPI |
| Modem | nRF9151 — LTE-M / NB-IoT / GPS |
| RGB LED | WS2812 (NeoPixel-compatible) |
| USB | Type-C (USB 2.0) |
| Connector | CN1 — 40-pin Raspberry Pi Pico-compatible |
| Crystal | 12 MHz (Y1) |

---

## Pin Map

### CN1 — User GPIO (Pico-compatible connector)

| CN1 Pin | MicroPython Name | GPIO | Notes |
|---------|-----------------|------|-------|
| 1 | `GP0` | GPIO0 | |
| 2 | `GP1` | GPIO1 | |
| 4 | `GP2` | GPIO2 | |
| 5 | `GP3` | GPIO3 | |
| 6 | `GP4` | GPIO4 | |
| 7 | `GP5` | GPIO5 | |
| 9 | `GP6` | GPIO6 | |
| 10 | `GP7` | GPIO7 | |
| 11 | `GP8` | GPIO8 | |
| 12 | `GP9` | GPIO9 | |
| 14 | `GP10` | GPIO10 | |
| 15 | `GP11` | GPIO11 | |
| 16 | `GP12` | GPIO12 | |
| 17 | `GP13` | GPIO13 | |
| 19 | `GP14` | GPIO14 | |
| 20 | `GP15` | GPIO15 | |
| 21–25 | — | GPIO16–19 | Reserved — nRF9151 UART |
| 26 | `GP20` | GPIO20 | |
| 27 | `GP21` | GPIO21 | |
| 29 | `GP22` | GPIO22 | |
| 30 | RUN | — | Reset |
| 31 | `GP26` | GPIO26 | ADC0 |
| 32 | `GP27` | GPIO27 | ADC1 |
| 34 | `GP28` | GPIO28 | ADC2 |

### Internal GPIO (not on CN1)

| MicroPython Name | GPIO | Function |
|-----------------|------|---------|
| `MODEM_TX` | GPIO16 | UART1 TX → nRF9151 |
| `MODEM_RX` | GPIO17 | UART1 RX ← nRF9151 |
| `MODEM_CTS` | GPIO18 | UART1 CTS ← nRF9151 |
| `MODEM_RTS` | GPIO19 | UART1 RTS → nRF9151 |
| `MODEM_RESET` | GPIO29 | nRF9151 nRESET (active low) |
| `MODEM_PWR_EN` | GPIO24 | nRF9151 buck converter ENABLE |
| `MODEM_PWR_SYNC` | GPIO25 | nRF9151 buck converter PS/SYNC |
| `LED` / `NEOPIXEL` | GPIO23 | WS2812 RGB LED data |

---

## Building

### Prerequisites

- [MicroPython build environment](https://docs.micropython.org/en/latest/develop/gettingstarted.html)
- ARM GCC toolchain (`arm-none-eabi-gcc`)
- CMake ≥ 3.13

### Build (ARM Cortex-M33)

```bash
make -C mpy-cross/ -j 16
make -C ports/rp2 BOARD=NXPICO_M clean
make -C ports/rp2 BOARD=NXPICO_M submodules
make -C ports/rp2 BOARD=NXPICO_M -j 16
```

### Flashing

Hold **BOOTSEL** while plugging in the USB cable (or run `machine.bootloader()` at the REPL), then copy the `.uf2` file to the mass storage device that appears.

---

## Usage Examples

### RGB LED (NeoPixel)

```python
import neopixel
from machine import Pin

np = neopixel.NeoPixel(Pin("NEOPIXEL"), 1)
np[0] = (255, 0, 0)   # red
np.write()
```

### nRF9151 Modem — Basic AT Commands

```python
from machine import UART, Pin

# Power on the modem
pwr_en   = Pin("MODEM_PWR_EN",   Pin.OUT, value=1)
pwr_sync = Pin("MODEM_PWR_SYNC", Pin.OUT, value=0)
reset    = Pin("MODEM_RESET",    Pin.OUT, value=1)

# Open UART to modem
modem = UART(1, baudrate=115200,
             tx=Pin("MODEM_TX"), rx=Pin("MODEM_RX"),
             cts=Pin("MODEM_CTS"), rts=Pin("MODEM_RTS"))

# Send AT command
modem.write(b"AT\r\n")
print(modem.read(64))
```

### ADC

```python
from machine import ADC, Pin

adc0 = ADC(Pin("GP26"))
print(adc0.read_u16())
```
