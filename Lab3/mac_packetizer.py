#!/usr/bin/env python
from gnuradio import gr
from gnuradio import blocks
from gnuradio import digital
import numpy as np

import jk_macproto as proto
import scan_state as state


np.set_printoptions(threshold=np.nan)

_tracep = False
def tprint(msg):
    if _tracep:
        print msg


class mac_packetizer(gr.basic_block):
    def __init__(self):
        gr.basic_block.__init__(self, name="frame_sync",
            in_sig=[np.uint8],
            out_sig=[np.uint8])

        ##################################################
        # Put Variables Here
        ##################################################
        self.state = state.Start
        self.bits_needed = proto.PKTHDRLEN_BITS

        self.currmsg_preamble = proto.MAC_PREAMBLE
        self.currmsg_datasz_bytes = 0

    def general_work(self, input_items, output_items):

        # Initial housekeeping
        in0 = input_items[0]
        out = output_items[0]
        ninput_items = len(in0)
        noutput_items = len(out)
        nmin_items = min(ninput_items, noutput_items)

        tprint("Input/Output Items:  {}/{}".format(ninput_items, noutput_items))

        # First, make sure the buffer has enough bits to be able to process
        if ninput_items < self.bits_needed:
            tprint("Not enough bits for current state ({}), waiting for next buffer fill.".format(self.bits_needed))
            self.consume_each(int(0))
            return 0

        if self.state == state.Start:
            # scan for sync pattern
            corr = np.correlate(in0.astype(np.int32) * 2 - 1, proto.SYNC_PATTERN_BIPOLAR)
            amax = np.argmax(corr)
            amax_val = corr[amax]
            tprint( "Amax {} found at {} ...".format(amax_val, amax))

            # if a lousy match, reset the buffers to try again
            if amax_val < (proto.SYNCLEN_BITS - proto.SYNC_TOLERANCE):
                tprint("Barker correlation insufficient, resetting buffer.")
                self.consume_each(int(ninput_items))
                return 0

            # Good match - do we have room?
            # TODO:  maybe have another interim state that allows us to avoid scanning for the Barker again
            if nmin_items < (amax + self.bits_needed):
                tprint("Barker found, but need more data - filling buffer.")
                self.consume_each(int(amax - 1))
                return 0

            # We have a full header in the buffer, let's parse
            preamble_bit_array = in0[amax + proto.SYNCLEN_BITS : amax + proto.SYNCLEN_BITS + proto.PREAMBLELEN_BITS]
            preamble_bytes = np.packbits(preamble_bit_array)
            poss_preamble = chr(preamble_bytes[0]) + chr(preamble_bytes[1])
            if poss_preamble not in proto.PREAMBLES:
                tprint("Invalid preamble ({}), dumping data.".format(poss_preamble))
                nitems_read = amax + proto.SYNCLEN_BITS + proto.PREAMBLELEN_BITS
                tprint(nitems_read)
                self.consume_each(int(nitems_read))
                return 0

            # Valid preamble found
            self.currmsg_preamble = poss_preamble
            datasz_bit_array = in0[amax + proto.SYNCLEN_BITS + proto.PREAMBLELEN_BITS :
                                   amax + proto.SYNCLEN_BITS + proto.PREAMBLELEN_BITS + proto.DATASZLEN_BITS]
            self.currmsg_datasz_bytes = np.packbits(datasz_bit_array)[0]

            self.state = state.Bundling
            self.bits_needed = self.currmsg_datasz_bytes * 8

            tprint("Message with preamble {}, data len {}, found ... loading buffer.".format(self.currmsg_preamble, self.currmsg_datasz_bytes))

            # Consume the packet header and return
            nitems_read = int(amax + proto.SYNCLEN_BITS + proto.PREAMBLELEN_BITS + proto.DATASZLEN_BITS)
            tprint("Consuming {} items (bits) ...".format(nitems_read))
            self.consume_each(int(nitems_read))
            return 0

        elif self.state == state.Bundling:
            # Once we get here, the buffer should have enough data
            msgdata_bits = in0[0 : self.currmsg_datasz_bytes * 8]
            msgdata_bytes = np.packbits(msgdata_bits)
            tprint(">>>>>>>>>>>>>>Rcvd data: {}".format(msgdata_bytes))

            # Now, pass the data on, as BYTES NOT BITS
            out[0] = ord(self.currmsg_preamble[0])
            out[1] = ord(self.currmsg_preamble[1])
            out[2] = self.currmsg_datasz_bytes

            out_idx = 3
            for b in msgdata_bytes:
                out[out_idx] = b
                out_idx += 1

            self.state = state.Start
            self.bits_needed = proto.PKTHDRLEN_BITS

            self.consume_each(int(self.currmsg_datasz_bytes * 8))
            nitems_written = proto.PKTHDRLEN_BYTES + self.currmsg_datasz_bytes - 2
            tprint("Writing {} bytes ...".format(nitems_written))
            return int(nitems_written)

        else:
            tprint("In a bizarre state ... resetting buffer and outputting nothing.")
            self.consume_each(int(ninput_items))
            return 0













