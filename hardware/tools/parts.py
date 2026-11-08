"""Part list and netlist for the gecko carrier board - single source of truth
for the schematic and the PCB generator."""

LIB = "gecko_carrier"

# Symbol definitions: name -> (body width, body height, pins)
# pin: (number, name, side, slot)  side L/R/T/B, slot = position index along the side
SYMBOLS = {
    "R": dict(two_pin=True, prefix="R"),
    "C": dict(two_pin=True, prefix="C"),
    "CP": dict(two_pin=True, prefix="C", polar=True),
    "Fuse": dict(two_pin=True, prefix="F"),
    "Varistor": dict(two_pin=True, prefix="RV"),
    "WT32-ETH01": dict(prefix="U", w=20.32, pins=[
        ("12", "5V", "T", 0), ("3", "3V3", "T", 4), ("10", "3V3", "T", 5),
        ("2", "GND", "B", 0), ("9", "GND", "B", 1), ("11", "GND", "B", 2), ("14", "GND", "B", 3), ("23", "GND", "B", 4),
        ("4", "EN", "L", 0), ("5", "IO32/CFG", "L", 2), ("6", "IO33/485_EN", "L", 4), ("7", "IO5/RXD", "L", 5),
        ("8", "IO17/TXD", "L", 6), ("1", "CLK_EN", "L", 9), ("13", "LINK", "L", 10),
        ("26", "IO1/TXD0", "R", 0), ("25", "IO3/RXD0", "R", 1), ("24", "IO0", "R", 2),
        ("16", "IO4", "R", 4), ("22", "IO39", "R", 6), ("21", "IO36", "R", 7), ("20", "IO15", "R", 8),
        ("19", "IO14", "R", 9), ("18", "IO12", "R", 10), ("17", "IO35", "R", 11), ("15", "IO2", "R", 12)]),
    "ISO1540": dict(prefix="U", w=15.24, pins=[
        ("1", "VCC1", "T", 0), ("8", "VCC2", "T", 4), ("4", "GND1", "B", 0), ("5", "GND2", "B", 4),
        ("2", "SDA1", "L", 0), ("3", "SCL1", "L", 1), ("7", "SDA2", "R", 0), ("6", "SCL2", "R", 1)]),
    "MAX3485": dict(prefix="U", w=15.24, pins=[
        ("1", "RO", "L", 0), ("2", "~{RE}", "L", 1), ("3", "DE", "L", 2), ("4", "DI", "L", 3),
        ("6", "A", "R", 1), ("7", "B", "R", 2), ("8", "VCC", "T", 2), ("5", "GND", "B", 2)]),
    "SM712": dict(prefix="D", w=10.16, pins=[("1", "IO1", "L", 0), ("2", "IO2", "L", 1), ("3", "GND", "R", 0)]),
    "HLK-PM01": dict(prefix="PS", w=15.24, pins=[
        ("1", "AC/L", "L", 0), ("2", "AC/N", "L", 1), ("4", "+Vout", "R", 0), ("3", "-Vout", "R", 1)]),
    "Conn_2": dict(prefix="J", w=7.62, pins=[("1", "1", "L", 0), ("2", "2", "L", 1)]),
    "Conn_3": dict(prefix="J", w=7.62, pins=[("1", "1", "L", 0), ("2", "2", "L", 1), ("3", "3", "L", 2)]),
    "Conn_5": dict(prefix="J", w=7.62, pins=[(str(i), str(i), "L", i - 1) for i in range(1, 6)]),
    "Conn_PROG": dict(prefix="J", w=10.16, pins=[("2", "TX", "L", 0), ("3", "RX", "L", 1), ("4", "IO0", "L", 2),
                                                ("5", "EN", "L", 3), ("1", "GND", "L", 4)]),
    "Conn_2x4": dict(prefix="J", w=10.16, pins=[
        ("1", "NC", "L", 0), ("3", "SDA", "L", 1), ("5", "NC", "L", 2), ("7", "NC", "L", 3),
        ("2", "SCL", "R", 0), ("4", "5V", "R", 1), ("6", "12V", "R", 2), ("8", "GND", "R", 3)]),
    "MountingHole": dict(prefix="H", w=5.08, pins=[]),
}

# ref, symbol, value, footprint, {pin: net}, sheet position (mm), extra
PARTS = [
    # --- Mains / power supply ---
    ("J1", "Conn_2", "230V AC (L, N)", "TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal",
     {"1": "L_IN", "2": "N"}, (40, 60)),
    ("F1", "Fuse", "T250mA 5x20", "Fuse:Fuseholder_Clip-5x20mm_Keystone_3517_Inline_P23.11x6.76mm_D1.70mm_Horizontal",
     {"1": "L_IN", "2": "L_F"}, (70, 50)),
    ("RV1", "Varistor", "275VAC 07D431K", "Varistor:RV_Disc_D7mm_W3.5mm_P5mm",
     {"1": "L_F", "2": "N"}, (95, 70)),
    ("PS1", "HLK-PM01", "HLK-PM01 (5V 0.6A)", "Converter_ACDC:Converter_ACDC_Hi-Link_HLK-PMxx",
     {"1": "L_F", "2": "N", "4": "+5V", "3": "GND"}, (130, 60)),
    ("C1", "CP", "220uF 10V", "Capacitor_THT:CP_Radial_D6.3mm_P2.50mm",
     {"1": "+5V", "2": "GND"}, (165, 62)),
    ("C2", "C", "100nF", "Capacitor_SMD:C_0805_2012Metric", {"1": "+5V", "2": "GND"}, (180, 62)),
    # --- WT32-ETH01 ---
    ("U1", "WT32-ETH01", "WT32-ETH01", "gecko_carrier:WT32-ETH01_Socket",
     {"1": None, "2": "GND", "3": "+3V3", "4": "EN", "5": "SCL_ESP", "6": "RS485_DE", "7": "RS485_RO",
      "8": "RS485_DI", "9": "GND", "10": "+3V3", "11": "GND", "12": "+5V", "13": None,
      "14": "GND", "15": None, "16": "SDA_ESP", "17": None, "18": None, "19": None, "20": None,
      "21": None, "22": None, "23": "GND", "24": "IO0", "25": "RXD0", "26": "TXD0"}, (70, 150)),
    ("J4", "Conn_PROG", "PROG (GND TX RX IO0 EN)", "Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Vertical",
     {"1": "GND", "2": "TXD0", "3": "RXD0", "4": "IO0", "5": "EN"}, (130, 140)),
    # --- I2C isolation ---
    ("U2", "ISO1540", "ISO1540", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
     {"1": "+3V3", "2": "SDA_ESP", "3": "SCL_ESP", "4": "GND",
      "8": "SPA_5V", "7": "SDA_SPA", "6": "SCL_SPA", "5": "GND_SPA"}, (260, 70)),
    ("R1", "R", "4k7", "Resistor_SMD:R_0805_2012Metric", {"1": "+3V3", "2": "SDA_ESP"}, (225, 55)),
    ("R2", "R", "4k7", "Resistor_SMD:R_0805_2012Metric", {"1": "+3V3", "2": "SCL_ESP"}, (235, 55)),
    ("C3", "C", "100nF", "Capacitor_SMD:C_0805_2012Metric", {"1": "+3V3", "2": "GND"}, (215, 55)),
    ("C4", "C", "100nF", "Capacitor_SMD:C_0805_2012Metric", {"1": "SPA_5V", "2": "GND_SPA"}, (305, 55)),
    ("R3", "R", "4k7 DNP", "Resistor_SMD:R_0805_2012Metric", {"1": "SPA_5V", "2": "SDA_SPA"}, (285, 55)),
    ("R4", "R", "4k7 DNP", "Resistor_SMD:R_0805_2012Metric", {"1": "SPA_5V", "2": "SCL_SPA"}, (295, 55)),
    ("J2", "Conn_2x4", "Gecko CO port", "Connector_IDC:IDC-Header_2x04_P2.54mm_Vertical",
     {"1": None, "3": "SDA_SPA", "5": None, "7": None, "2": "SCL_SPA", "4": "SPA_5V", "6": None, "8": "GND_SPA"},
     (330, 75)),
    # --- RS485 / Modbus ---
    ("U3", "MAX3485", "MAX3485", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
     {"1": "RS485_RO", "2": "RS485_DE", "3": "RS485_DE", "4": "RS485_DI",
      "8": "+3V3", "6": "RS485_A", "7": "RS485_B", "5": "GND"}, (260, 160)),
    ("C5", "C", "100nF", "Capacitor_SMD:C_0805_2012Metric", {"1": "+3V3", "2": "GND"}, (230, 140)),
    ("R5", "R", "120R", "Resistor_SMD:R_0805_2012Metric", {"1": "RS485_A", "2": "TERM"}, (300, 175)),
    ("JP1", "Conn_2", "TERM (jumper)", "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
     {"1": "TERM", "2": "RS485_B"}, (320, 190)),
    ("R6", "R", "680R", "Resistor_SMD:R_0805_2012Metric", {"1": "+3V3", "2": "RS485_A"}, (290, 140)),
    ("R7", "R", "680R", "Resistor_SMD:R_0805_2012Metric", {"1": "RS485_B", "2": "GND"}, (300, 140)),
    ("D1", "SM712", "SM712", "Package_TO_SOT_SMD:SOT-23", {"1": "RS485_A", "2": "RS485_B", "3": "GND"}, (290, 200)),
    ("J3", "Conn_3", "Modbus: D1(A+) D0(B-) 0V", "TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-3-5.08_1x03_P5.08mm_Horizontal",
     {"1": "RS485_A", "2": "RS485_B", "3": "GND"}, (345, 160)),
    # --- Mechanics ---
    ("H1", "MountingHole", "M3", "MountingHole:MountingHole_3.2mm_M3", {}, (360, 250)),
    ("H2", "MountingHole", "M3", "MountingHole:MountingHole_3.2mm_M3", {}, (370, 250)),
    ("H3", "MountingHole", "M3", "MountingHole:MountingHole_3.2mm_M3", {}, (380, 250)),
    ("H4", "MountingHole", "M3", "MountingHole:MountingHole_3.2mm_M3", {}, (390, 250)),
]

# PCB placement: ref -> (x, y, rotation deg, side) in board mm, origin top-left of the board
PLACEMENT = {
    "J1": (6, 9, 0, "F"),
    "F1": (4, 22, 0, "F"),
    "RV1": (9, 33, 0, "F"),
    "PS1": (22, 47, 0, "F"),
    "C1": (60, 64, 90, "F"),
    "C2": (60, 55, 90, "F"),
    "U1": (80, 52.5, 0, "F"),
    "J4": (97, 47, 0, "F"),
    "U2": (102, 22, 0, "F"),
    "R1": (96.5, 14, 90, "F"),
    "R2": (96.5, 30, 90, "F"),
    "C3": (96.5, 22, 90, "F"),
    "C4": (107, 32, 90, "F"),
    "R3": (107, 14, 90, "F"),
    "R4": (107, 26, 90, "F"),
    "J2": (113.5, 9, 0, "F"),
    "U3": (54, 22, 0, "F"),
    "C5": (60, 19, 90, "F"),
    "R5": (60, 12, 0, "F"),
    "JP1": (64, 10, 0, "F"),
    "R6": (48, 18, 90, "F"),
    "R7": (48, 26, 90, "F"),
    "D1": (54, 31, 0, "F"),
    "J3": (44, 5, 0, "F"),
    "H1": (42, 76, 0, "F"),
    "H2": (116, 76, 0, "F"),
    "H3": (116, 45, 0, "F"),
    "H4": (34, 4, 0, "F"),
}

BOARD_W = 120.0
BOARD_H = 80.0

# Notch under the WT32-ETH01's RJ45 jack. The jack body sticks out below the
# module further than the short header pins at that end (LINK, GND), so the
# module only sits flat if the carrier is cut away there. Open to the bottom edge.
RJ45_NOTCH = (70.4, 64.4, 89.6, BOARD_H)  # x0, y0, x1, y1

NETCLASSES = {
    "Mains": dict(clearance=2.0, width=1.0, nets=["L_IN", "L_F", "N"]),
    "Power": dict(clearance=0.25, width=0.6, nets=["+5V", "+3V3", "GND", "SPA_5V", "GND_SPA"]),
}
