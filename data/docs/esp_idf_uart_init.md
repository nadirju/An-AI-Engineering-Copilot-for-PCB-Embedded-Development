---
tool: ESP-IDF
version: "5"
component: UART driver
doc_type: sdk_doc
section: UART driver initialization
publication_date: 2024-01-01
url: https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/peripherals/uart.html
---

# ESP-IDF UART initialization: summary

Setting up a UART in ESP-IDF involves four calls in order. First fill a uart_config_t with baud rate, data bits, parity, stop bits, flow control and clock source. Then call uart_param_config with the port number and the configuration. Next assign the TX, RX, RTS and CTS pins with uart_set_pin, using UART_PIN_NO_CHANGE for lines that are not used. Finally install the driver with uart_driver_install, which allocates the receive and optional transmit ring buffers.

The driver install call takes the RX buffer size, the TX buffer size, an event queue length and a pointer to an event queue handle, and the receive buffer must be larger than the hardware FIFO. Data is then read with uart_read_bytes with a tick timeout and written with uart_write_bytes. All of these return an esp_err_t or a byte count, and the return value should be checked rather than ignored.

Pin choice matters on the ESP32 family: some pins are strapping pins or are reserved for flash and should be avoided, and the default console UART0 should not be reused unless logging is redirected. Verify by looping TX to RX with a jumper and confirming that the bytes written equal the bytes read back, and by checking the baud rate with a logic analyzer.