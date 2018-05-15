#!/usr/bin/env python

import os
import sys
import time

from gnuradio import gr
from gnuradio import blocks
from gnuradio import digital
from gnuradio import uhd
from gnuradio import eng_notation
from gnuradio.eng_option import eng_option
from gnuradio import channels
import gnuradio.gr.gr_threading as _threading

from optparse import OptionParser

from mac_packetizer import *
import jk_macproto as proto
import mac_state as mac

DATA = "Hello World123\n"
MAC_ID = 65
MAC_ID_STR = chr(MAC_ID)

class top_block(gr.top_block):

    def __init__(self, freq, rx_callback):
        gr.top_block.__init__(self)

        ##################################################
        # Variables
        ##################################################
        self.freq = freq
        self.samp_rate = 1e6
        self.rxgain = 0
        self.txgain = 0

        ##################################################
        # Blocks
        ##################################################
        self.txpath = transmit_path()
        self.rxpath = receive_path(rx_callback)

        self.uhd_usrp_sink = uhd.usrp_sink(
            device_addr="",
            stream_args=uhd.stream_args(
                cpu_format="fc32",
                channels=range(1),
            ),
        )
        self.uhd_usrp_sink.set_samp_rate(self.samp_rate)
        self.uhd_usrp_sink.set_center_freq(self.freq, 0)
        self.uhd_usrp_sink.set_gain(self.rxgain, 0)
        self.uhd_usrp_sink.set_antenna("J1", 0)

        self.uhd_usrp_source = uhd.usrp_source(
            device_addr="",
            stream_args=uhd.stream_args(
                cpu_format="fc32",
                channels=range(1),
            ),
        )
        self.uhd_usrp_source.set_samp_rate(self.samp_rate)
        self.uhd_usrp_source.set_center_freq(self.freq, 0)
        self.uhd_usrp_source.set_gain(self.txgain, 0)
        self.uhd_usrp_source.set_antenna("J1", 0)

        ##################################################
        # Connections
        ##################################################
        self.connect(self.txpath, self.uhd_usrp_sink)
        self.connect(self.uhd_usrp_source, self.rxpath)

    def send_pkt(self, payload='', eof=False):
        return self.txpath.send_pkt(payload, eof)

    def clearq(self):
        self.txpath.clearq()

class transmit_path(gr.hier_block2):
    def __init__(self):
        gr.hier_block2.__init__(self, "transmit_path",
                gr.io_signature(0,0,0),
                gr.io_signature(1, 1, gr.sizeof_gr_complex))

        # VerA
        # Create Input Vector here
        # barker13_uni = [0, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 1, 0]
        # barker13_wpadding_uni = [0, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 1, 0, 0, 0, 0]
        # # sync_pattern = barker13_uni
        # sync_pattern = barker13_wpadding_uni
        # s = "Hello World\n"
        # msg = string_to_list.conv_string_to_1_0_list(s)
        # input_vector = sync_pattern + msg
        # self.input_vector_source = blocks.vector_source_b(input_vector, True, 1, [])
        # self.input_unpacked_to_packed = blocks.unpacked_to_packed_bb(1, gr.GR_MSB_FIRST)

        # VerB
        self.msgq_limit = msgq_limit = 2
        self.pkt_input = blocks.message_source(gr.sizeof_char, msgq_limit)

        self.mod = digital.gfsk_mod(
            samples_per_symbol=4,
            sensitivity=1.0,
            bt=0.35,
            verbose=False,
            log=False,
        )



        ##################################################
        # Connections
        ##################################################
        # VerA
        # self.connect(self.input_vector_source, self.input_unpacked_to_packed,  self.mod, self)

        # VerB
        self.connect(self.pkt_input, self.mod, self)


    def send_pkt(self, payload='', eof=False):
        if eof:
            msg = gr.message(1)  # tell self._pkt_input we're not sending any more packets
        else:
            msg = gr.message_from_string(payload)
        self.pkt_input.msgq().insert_tail(msg)
        # print "Message length: {}".format(msg.length())

    def clearq(self):
        self.pkt_input.msgq().flush()


class receive_path(gr.hier_block2):
    def __init__(self, rx_callback):
        gr.hier_block2.__init__(self, "receive_path",
            gr.io_signature(1, 1, gr.sizeof_gr_complex),
            gr.io_signature(0, 0, 0))

        self.callback = rx_callback

        self.demod = digital.gfsk_demod(
            samples_per_symbol=4,
            sensitivity=1.0,
            gain_mu=0.175,
            mu=0.5,
            omega_relative_limit=0.005,
            freq_error=0.0,
            verbose=False,
            log=False,
        )

        self.packetizer = mac_packetizer()
        self.rcvd_pktq = gr.msg_queue()
        self.message_sink = blocks.message_sink(gr.sizeof_char, self.rcvd_pktq, False)
        self.queue_watcher_thread = _queue_watcher_thread(self.rcvd_pktq, self.callback)
        self.connect(self, self.demod, self.packetizer, self.message_sink)
        
        # self.connect(self, self.demod, self.frame_sync, self.output_unpacked_to_packed, self.message_sink)
        
        # NoQ version
        # self.output_file_sink = blocks.file_sink(gr.sizeof_char * 1, "output.txt", False)
        # self.output_file_sink.set_unbuffered(True)
        # self.output_unpacked_to_packed = blocks.unpacked_to_packed_bb(1, gr.GR_MSB_FIRST)
        # self.frame_sync = frame_sync()
        # self.output_file_sink = blocks.file_sink(gr.sizeof_char * 1, "output.txt", False)
        # self.output_file_sink.set_unbuffered(True)
        #
        # self.connect(self, self.demod, self.frame_sync, self.output_unpacked_to_packed, self.output_file_sink)

class tdd_mac(object):

    def __init__(self):
        self.tb = None
        self.pktcnt = 0
        self.state = mac.Beacon

    def set_top_block(self, tb):
        self.tb = tb

    def rx_callback(self, payload):
        # Stuff goes here like:
        # print payload
        print "Payload --> {}".format(proto.extract_datastr(payload))
        if self.state == mac.Beacon:
            if payload[0:2] == proto.MAC_PREAMBLE:
                otherid = ord(payload[3])
                if otherid > MAC_ID:
                    print "MAC control:  ceding TX to higher MAC ID ({})".format(otherid)
                    self.state = mac.Normal_RX
                else:
                    print "MAC control:  taking TX from lower MAC ID"
                    self.state = mac.Normal_TX


    def main_loop(self):

        while 1:
            if self.state == mac.Beacon:
                time.sleep(proto.get_beacon_period())
                self.tb.send_pkt(proto.build_maccmd(MAC_ID_STR))
            elif self.state == mac.Normal_TX:
                self.pktcnt += 1
                self.tb.send_pkt(proto.build_msg(str(self.pktcnt) + ": " + DATA))
                time.sleep(.1)


            ##################################################
            # Your Mac logic goes here                       #
            ##################################################
            # self.pktcnt += 1
            # self.tb.send_pkt(proto.build_msg(str(self.pktcnt) + ": " + DATA))
            # time.sleep(0.001)
            # pass

    def send_once(self):
        self.tb.send_pkt(self.msg)


class _queue_watcher_thread(_threading.Thread):
    def __init__(self, rcvd_pktq, callback):
        _threading.Thread.__init__(self)
        self.setDaemon(1)
        self.rcvd_pktq = rcvd_pktq
        self.callback = callback
        self.keep_running = True
        self.start()

    def run(self):
        while self.keep_running:
            #print "Packets in queue: {}".format(self.rcvd_pktq.count())
            msg = self.rcvd_pktq.delete_head()
            payload = msg.to_string()

            if self.callback:
                self.callback(payload)

def main():
    parser = OptionParser(option_class=eng_option, conflict_handler="resolve")
    parser.add_option("-f", "--freq", type="eng_float", default=None,
                      help="set center frequency to FREQ", metavar="FREQ")
    parser.add_option("-m", type="eng_float", default=1,
                        help = "set mode, tx or rx", metavar="MODE")

    (options, args) = parser.parse_args()

    freq = options.freq
    print "Freq = " + str(freq)

    if freq is None:
        raise ValueError("Center frequency not specified...")

    r = gr.enable_realtime_scheduling()
    if r != gr.RT_OK:
        print "Warning: failed to enable realtime scheduling"

    mac = tdd_mac()

    tb = top_block(freq, mac.rx_callback)
    mac.set_top_block(tb)

    tb.start()
    mac.main_loop()

    tb.stop()
    tb.wait()
    # tb.run()



if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass



