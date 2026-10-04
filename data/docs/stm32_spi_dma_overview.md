---
tool: STM32CubeIDE/CubeMX
version: any
component: STM32F401 SPI/DMA
doc_type: reference_manual
section: SPI and DMA controller overview
publication_date: 2023-01-01
url: https://www.st.com/resource/en/reference_manual/rm0368-stm32f401xbc-and-stm32f401xde-advanced-armbased-32bit-mcus-stmicroelectronics.pdf
---

# STM32F401 SPI with DMA: summary

The STM32F401 SPI peripherals can run as full-duplex masters. SPI1 sits on the APB2 bus, which can run up to 84 MHz, while SPI2 and SPI3 sit on the slower APB1 bus. The serial clock is the bus clock divided by a prescaler from 2 to 256, so the achievable SCK rates are discrete values. Clock polarity (CPOL) and clock phase (CPHA) select one of four SPI modes and must match the slave device.

DMA lets the CPU skip byte-by-byte servicing. For SPI1 the receive request is served by DMA2 and the transmit request by DMA2 as well, using channel 3 of the appropriate streams. In a full-duplex transfer the receive stream should be enabled so incoming data never overruns, and the transmit stream supplies bytes as the shift register empties. The DMA controller raises transfer-complete and transfer-error interrupts that the HAL turns into completion callbacks.

Practical points: with software chip select the firmware must drive the select GPIO low before starting the transfer and release it only after the transfer-complete callback, not right after starting the DMA call, since the call returns before the bytes are on the wire. Buffers must stay valid for the whole transfer. Verify by capturing SCK, MOSI, MISO and CS with a logic analyzer and checking that CS stays low for the full frame.