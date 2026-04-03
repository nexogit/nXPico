# cmake file for UFG Elettronica nXPico M
# RP2350A with nRF9151 LTE-M/NB-IoT modem, 4MB flash, WS2812 RGB LED

set(PICO_BOARD "pico2")

# Board specific frozen manifest
set(MICROPY_FROZEN_MANIFEST ${MICROPY_BOARD_DIR}/manifest.py)

# Automatically include board C modules (no USER_C_MODULES argument needed)
list(APPEND USER_C_MODULES ${MICROPY_BOARD_DIR}/cmodules)
