// Board and hardware specific configuration for UFG Elettronica nXPico M
//
// Hardware summary:
//   - RP2350A MCU (QFN-60)
//   - 4MB QSPI flash (W25Q32J)
//   - nRF9151 LTE-M/NB-IoT modem on UART1 (GPIO16-19)
//   - WS2812 RGB LED on GPIO23
//   - USB Type-C
//   - Raspberry Pi Pico-compatible 40-pin connector (CN1)
//
// Internal GPIO assignments:
//   GPIO16 = UART1 TX  -> nRF9151
//   GPIO17 = UART1 RX  <- nRF9151
//   GPIO18 = UART1 CTS <- nRF9151
//   GPIO19 = UART1 RTS -> nRF9151
//   GPIO23 = WS2812 RGB LED data
//   GPIO24 = nRF9151 buck converter ENABLE (WL_GPIO1)
//   GPIO25 = nRF9151 buck converter PS/SYNC (WL_GPIO2)
//   GPIO29 = nRF9151 nRESET

#define MICROPY_HW_BOARD_NAME                   "nXPico M"
#define MICROPY_HW_FLASH_STORAGE_BYTES          (PICO_FLASH_SIZE_BYTES - 1024 * 1024)
