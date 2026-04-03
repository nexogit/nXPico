#include "py/runtime.h"
#include "py/mphal.h"
#include <stdio.h>
#include "hardware/uart.h"
#include "pico/stdlib.h"
#include "pico/time.h"

//UART Connected to rp2350A
#define UART_ID0 uart0

// Write data to UART0 (nRF9151 TX)
static mp_obj_t write(mp_obj_t buf_obj) {
    mp_buffer_info_t bufinfo;
    mp_get_buffer_raise(buf_obj, &bufinfo, MP_BUFFER_READ);

    for (size_t i = 0; i < bufinfo.len; i++) {
        uart_putc(UART_ID0, ((uint8_t *)bufinfo.buf)[i]);
    }

    return mp_const_none;
}

// Read data from UART0 (nRF9151 RX) with a timeout. The provided buffer is filled with the data read, and the function returns the number of bytes read.
// function returns the number of bytes read, and fills the provided buffer with the data
size_t uart0_read_line(uint8_t *buffer, size_t max_len) {
    size_t i = 0;
    absolute_time_t start = get_absolute_time();

    while (i < max_len) {
        if (uart_is_readable(UART_ID0)) {
            uint8_t byte = uart_getc(UART_ID0);
            start = get_absolute_time();  // reset timeout

            buffer[i++] = byte;

        } else {
            if (absolute_time_diff_us(start, get_absolute_time()) > 50 * 1000) {
                break;
            }
            sleep_us(100);  // riduce uso CPU
        }
    }

    return i; 
}

// Read a line of data from UART0 (nRF9151 RX) with a timeout of 5 seconds.
// size of the line read is returned, and the len of provided buffer is filled with the data.
static mp_obj_t read(mp_obj_t max_len_obj) {
    size_t max_len = mp_obj_get_int(max_len_obj);

    uint8_t buffer[max_len];
    size_t received_len = uart0_read_line(buffer, max_len);

    return mp_obj_new_bytes(buffer, received_len);
}

// Read a single character from UART0 (nRF9151 RX)
static mp_obj_t read_char(void) {
    if (uart_is_readable(UART_ID0)) {
        uint8_t byte = uart_getc(UART_ID0);
        return mp_obj_new_bytes(&byte, 1);
    } 

    return mp_obj_new_bytes(NULL, 0);
}


// Init UART0 on Fixed GPIOs:
// GPIO16 = UART0 TX
// GPIO17 = UART0 RX
// GPIO18 = UART0 CTS
// GPIO19 = UART0 RTS
static mp_obj_t init(void) {
    stdio_init_all();

    uart_init(UART_ID0, 115200);

    // Set TX / RX
    gpio_set_function(16, GPIO_FUNC_UART);  // TX
    gpio_set_function(17, GPIO_FUNC_UART);  // RX

    // Set RTS / CTS
    gpio_set_function(18, GPIO_FUNC_UART);  // RTS
    gpio_set_function(19, GPIO_FUNC_UART);  // CTS

    // Enable hardware flow control
    uart_set_hw_flow(UART_ID0, true, true);

    return mp_const_true;
}

// === Definizione oggetti MicroPython ===
static MP_DEFINE_CONST_FUN_OBJ_1(write_obj, write);
static MP_DEFINE_CONST_FUN_OBJ_0(init_obj, init);
static MP_DEFINE_CONST_FUN_OBJ_1(read_obj, read);
static MP_DEFINE_CONST_FUN_OBJ_0(read_char_obj, read_char);

static const mp_rom_map_elem_t uart_pico_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR_init), MP_ROM_PTR(&init_obj) },
    { MP_ROM_QSTR(MP_QSTR_read), MP_ROM_PTR(&read_obj) },
    { MP_ROM_QSTR(MP_QSTR_read_char), MP_ROM_PTR(&read_char_obj) },
    { MP_ROM_QSTR(MP_QSTR_write), MP_ROM_PTR(&write_obj) },
};

static MP_DEFINE_CONST_DICT(nrf9151_module_globals, uart_pico_module_globals_table);

const mp_obj_module_t nrf9151_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&nrf9151_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_nrf9151, nrf9151_user_cmodule);