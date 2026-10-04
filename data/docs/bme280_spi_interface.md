---
tool: STM32CubeIDE/CubeMX
version: any
component: BME280
doc_type: datasheet
section: SPI interface and register access
publication_date: 2022-03-01
url: https://www.bosch-sensortec.com/products/environmental-sensors/humidity-sensors-bme280/
---

# BME280 SPI interface: summary

The BME280 environmental sensor can talk over I2C or SPI. SPI is selected by pulling the chip-select line low, and the device supports SPI modes 0 and 3 with a clock up to roughly 10 MHz. It accepts the usual four-wire connection and also a three-wire mode enabled by a configuration bit. The select line is active low and must toggle between separate transactions.

Register access uses the first byte of each transaction as an address. For a read, bit 7 of the register address is set to 1; for a write, bit 7 is cleared to 0, so the firmware sends the address ANDed with 0x7F. After the address byte the master clocks out data bytes, and consecutive registers are read in an auto-incrementing burst. The identification register at 0xD0 returns 0x60 on a healthy BME280, which makes it the best first check after wiring or configuring the bus.

Measurement is configured through the humidity control register (0xF2), the measurement control register (0xF4) and the config register (0xF5). Humidity oversampling written to 0xF2 only takes effect after a write to 0xF4. A soft reset is triggered by writing 0xB6 to register 0xE0. Calibration coefficients must be read from the trimming registers and applied with the compensation formulas in the datasheet before raw readings become physical units.