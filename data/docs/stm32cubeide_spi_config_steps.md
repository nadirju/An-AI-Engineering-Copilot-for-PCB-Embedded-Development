---
tool: STM32CubeIDE/CubeMX
version: "1.15"
component: SPI1 configuration
doc_type: official_doc
section: Configuring SPI with DMA in CubeMX
publication_date: 2024-01-01
url: https://www.st.com/en/development-tools/stm32cubeide.html
---

# Configuring SPI1 with DMA in STM32CubeIDE/CubeMX: summary

Open the .ioc file and go to Pinout & Configuration, then Connectivity, then SPI1. Set Mode to Full-Duplex Master. In Parameter Settings choose Data Size 8 Bits, First Bit MSB First, and select a Baud Rate Prescaler that keeps SCK within the slave limit; the tool shows the resulting baud rate. Set Clock Polarity and Clock Phase to match the device, for example CPOL Low and CPHA 1 Edge for SPI mode 0. Leave NSS Signal Type on Software when the chip select is driven from a GPIO.

For the chip select, configure a spare pin such as PA4 as GPIO Output, set its initial level to High, and give it a user label. In the DMA Settings tab of SPI1, add SPI1_RX and SPI1_TX requests, direction peripheral-to-memory for RX and memory-to-peripheral for TX, normal mode, byte data width, and increment memory address enabled. Then check the NVIC Settings tab so the DMA stream interrupts are enabled.

After generating code, the HAL provides HAL_SPI_TransmitReceive_DMA together with the completion callback HAL_SPI_TxRxCpltCallback and the error callback HAL_SPI_ErrorCallback. Verify the build finishes without errors, that the function returns HAL_OK, and that a logic analyzer shows CS low, eight SCK pulses per byte and the expected idle level on SCK.