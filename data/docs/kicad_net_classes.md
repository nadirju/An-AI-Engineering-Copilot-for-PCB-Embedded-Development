---
tool: KiCad
version: "8"
component: Net classes
doc_type: official_doc
section: Net classes and design rules
publication_date: 2024-01-01
url: https://docs.kicad.org/
---

# KiCad net classes: summary

A net class groups nets that share routing constraints such as track width, clearance, via size and differential pair width and gap. In KiCad 8 net classes are managed from the schematic setup under Project, Net Classes, while the board setup under Design Rules continues to hold constraints, custom rules and the pre-defined sizes. Earlier versions kept net classes in the board setup instead, so the dialog location depends on the version.

Nets are attached to a class using patterns. A pattern can be an exact net name or a wildcard, for example a prefix shared by all nets of a bus, and net class assignments can also be driven from the schematic with net class directives. The Default class applies to anything that is not assigned. Custom design rules allow conditions that go beyond what net classes can express.

Altium users will find the closest equivalent in the Rules dialog, where a net class scope is attached to width and clearance rules. In KiCad the constraints live in the class itself rather than in a separate rule, so one class carries several values at once. Verify by running Inspect, Design Rules Checker and checking that the violation count is zero after assigning nets.