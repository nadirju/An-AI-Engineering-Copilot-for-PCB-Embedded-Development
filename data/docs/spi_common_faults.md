---
tool: STM32CubeIDE/CubeMX
version: any
component: SPI bus
doc_type: app_note
section: Common SPI bring-up faults and checks
publication_date: 2023-06-01
url: https://www.st.com/en/microcontrollers-microprocessors/stm32f4-series.html
---

# Common SPI bring-up faults: summary

Most failed SPI bring-ups come from a short list of causes. The clock polarity or phase does not match the slave, so data is sampled on the wrong edge and every byte appears shifted or inverted. The chip select never goes low, is released too early because it was deasserted right after a DMA call returned, or is on a pin that was not configured as an output. The clock is faster than the slave allows, which gives sporadic corruption that gets worse with long wires. MISO is floating or not wired, so the master reads all ones or all zeros.

Protocol-level mistakes follow next. Many sensors need the read bit set in the address byte, and forgetting it makes every read return the same value. Mixing up MOSI and MISO, using the wrong pin alternate function, or leaving the peripheral clock disabled all leave the bus silent. A missing common ground or a supply that is out of range gives odd results that look like software faults.

A sound order of checks is: supply and ground, pin functions and wiring, a logic-analyzer capture of CS, SCK, MOSI and MISO, SPI mode against the datasheet, then the device identification register. For the BME280 the ID register 0xD0 should read 0x60. On the capture, confirm CS falls before the first SCK edge, SCK idles at the expected level, and MISO changes on the expected edge.