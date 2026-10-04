---
tool: Altium Designer
version: any
component: Differential pair routing rules
doc_type: official_doc
section: Defining differential pair rules and constraints
publication_date: 2024-01-01
url: https://www.altium.com/documentation/altium-designer
---

# Altium Designer differential pair rules: summary

Differential pairs are created from two nets, usually named with matching suffixes such as _P and _N. In the PCB editor the PCB panel can be switched to its Differential Pairs Editor mode, where pairs can be created from nets or generated from the schematic using directives. Once a pair exists it can be routed together with the interactive differential pair routing command.

Rules are defined through Design, Rules. Under the High Speed category the Matched Lengths rule sets length tolerances, and under the Routing category the Differential Pairs Routing rule sets minimum width, maximum width, preferred width, preferred gap and the maximum uncoupled length. Rule scopes can target a net class, a differential pair class or a query, so the tightest rule can be applied only where needed. Width and gap values depend on the layer stackup, so they should come from the fabricator's impedance calculator.

For single-ended buses such as SPI, the same Rules dialog can hold width, clearance and routing-layer rules scoped to a net class that groups SCK, MOSI, MISO and CS. Verify with Tools, Design Rule Check and confirm the report shows zero violations for the relevant rules. Use the interactive length tuning tools if a matched-length rule is violated.