# A collection of constants and helpers for this particular protocol
import numpy as np

# Some building blocks
_barker13_bi = np.array([-1, -1, -1, -1, -1, 1, 1, -1, -1, 1, -1, 1, -1])
_barker13_wpadding_bi = np.array([-1, -1, -1, -1, -1, 1, 1, -1, -1, 1, -1, 1, -1, -1, -1, -1])
_barker13len_bits = len(_barker13_bi)
_barker13wpaddinglen_bits = len(_barker13_wpadding_bi)

# Pattern that is sent consists of:
#   Sync pattern + preambletype + datsz + content (length = pktlen)
#     (16 bits)     (16 bits)    (8bits)         (up to 255 BYTES)
SYNC_PATTERN_BIPOLAR = _barker13_wpadding_bi
SYNC_PATTERN_STRING = chr(6) + chr(80)
SYNCLEN_BITS = len(SYNC_PATTERN_BIPOLAR)
SYNC_TOLERANCE = 0

# Additional bytes to keep things synhronized, but also convey some meaning
# as to what "type" of packet this is (MAC control vs. content
MAC_PREAMBLE = "MC"
GEN_PREAMBLE = "JK"
PREAMBLELEN_BITS = len(GEN_PREAMBLE) * 8

PREAMBLES = [ GEN_PREAMBLE, MAC_PREAMBLE ]

DATASZLEN_BITS = 8
DATASZ_MAX_BYTES = 255
DATASZ_MAX_BITS = DATASZ_MAX_BYTES * 8

PKTHDRLEN_BITS = SYNCLEN_BITS + PREAMBLELEN_BITS + DATASZLEN_BITS
PKTHDRLEN_BYTES = PKTHDRLEN_BITS / 8

BEACON_BASE_PERIOD_MS = 0.2

def build_msg(datastr):
    sz_bytes = len(datastr)
    if sz_bytes > DATASZ_MAX_BYTES:
        sz_bytes = DATASZ_MAX_BYTES
        datastr = datastr[0:DATASZ_MAX_BYTES]
    return SYNC_PATTERN_STRING + GEN_PREAMBLE + chr(sz_bytes) + datastr

def build_maccmd(param):
    sz_bytes = len(param)
    if sz_bytes > DATASZ_MAX_BYTES:
        sz_bytes = DATASZ_MAX_BYTES
        param = param[0:DATASZ_MAX_BYTES]
    return SYNC_PATTERN_STRING + MAC_PREAMBLE + chr(sz_bytes) + param

def extract_datastr(msg):
    return msg[3:]

def get_beacon_period():
    return BEACON_BASE_PERIOD_MS + (np.random.rand() * 0.1)






