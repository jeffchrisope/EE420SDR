#!/usr/bin/env python

import os
import sys
import time
import random

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
import jk_csmaca_macproto as proto
import mac_state as mac
import IDs as id

DATA = "Hello World123\n"
MAC_ID_STR = chr(id.MAC_ID)

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

        self.msgq_limit = msgq_limit = 10
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

        # Determine which radio we are
        if (id.MAC_ID == 1):
            self.RID = 1
            self.state = mac.R1_TX_Traffic
        elif (id.MAC_ID == 2):
            self.RID = 2
            self.state = mac.R2_SenseOnly
        else:
            raise ValueError

        print "Entering exchange as Radio{} ...".format(self.RID)

    def set_top_block(self, tb):
        self.tb = tb

    def rx_callback(self, payload):

        print "Payload --> {}".format(proto.extract_datastr(payload))

        if self.RID == 1:
            if self.state == mac.R1_TX_Traffic:
                print "Receiving messages while generating S1 traffic ... ignoring content."

            elif self.state == mac.R1_RX_Sense:
                print "Detecting possible codeword from R2 ..."
                self.state = mac.R1_Decode

            elif self.state == mac.R1_Decode:
                print "Payload received:  {}".format(payload)
                if payload==proto.CHANGE_CODEWORD:
                    print "Codeword detected, entering final state."
                    self.state = mac.R1_END
                else:
                    print "Wrong codeword, restarting state flow."
                    self.state = mac.R1_TX_Traffic

            elif self.state == mac.R1_END:
                print "Receiving messages while in final state ... ignoring content."

            else:
                print "In bizarre state ..."

        elif self.RID == 2:
            if self.state == mac.R2_SenseOnly:
                print "Message received but ignored - only frequency energy being used."

            elif self.state == mac.R2_TX_Codeword:
                print "Message received while codeword transmitted ... ignored."

            elif self.state == mac.R2_Listening:
                if payload == proto.FINAL_MSG_CONTENT:
                    print "In final state, final message received."
                else:
                    print "Change codewords sent, but resposnes not moved to final.  Reverting to initial state."
                    self.state = mac.R2_SenseOnly

            else:
                print "In bizarre state ..."

        else:
            raise ValueError("Bad radio ID in IDs.py.")


    def main_loop(self):

        while 1:
            if self.RID == 1:
                if self.state == mac.R1_TX_Traffic:
                    burstsize = random.randint(proto.S1R1_MIN_MSG_BURST_COUNT, proto.S1R1_MAX_MSG_BURST_COUNT)
                    newmsg = proto.build_msg(proto.INITIAL_MSG_CONTENT)
                    print "Sending message '{}' {} times ...".format(newmsg, burstsize)
                    for m in range(0, burstsize):
                        self.tb.send_pkt(newmsg)
                        time.sleep(proto.MSGQ_INTRA_MSG_GAP_S)

                    # Move to next state and listen
                    self.state = mac.R1_RX_Sense
                    self.time_enter_RX_Sense = time.time()

                elif self.state == mac.R1_RX_Sense:
                    # Waiting for callback indicating that something has come in
                    if (time.time() - self.time_enter_RX_Sense) > proto.S2R1_MAX_WAIT_TIME_S:
                        print "Nothing heard, reverting to traffic generation ..."
                        self.state = mac.R1_TX_Traffic

                elif self.state == mac.R1_Decode:
                    pass

                elif self.state == mac.R1_END:
                    print "Sending final message packet ..."
                    self.tb.send_pkt(proto.build_msg(proto.FINAL_MSG_CONTENT))
                    time.sleep(proto.MSGQ_INTRA_MSG_GAP_S)

            elif self.RID == 2:
                if self.state == mac.R2_SenseOnly:
                    # TODO:  add check for energy
                    self.isbusy = True
                    if self.isbusy:
                        backoff_time = proto.S1R2_RANDOM_BACKOFF_BASE_TIME_S + (random.random() * proto.S1R2_RANDOM_BACKOFF_RANDOM_FACTOR)
                        print "Channel busy, backing off {} seconds...".format(backoff_time)
                        time.sleep(backoff_time)

                    else:
                        print "Detected idle frequency, shifting to codeword transmit mode."
                        self.state = mac.R2_TX_Codeword


                elif self.state == mac.R2_TX_Codeword:
                    burstsize = random.randint(proto.S2R2_MIN_CW_BURST_COUNT, proto.S2R2_MAX_CW_BURST_COUNT)
                    newmsg = proto.build_msg(proto.CHANGE_CODEWORD)
                    for m in range(0, burstsize):
                        self.tb.send_pkt(newmsg)
                        time.sleep(proto.MSGQ_INTRA_MSG_GAP_S)

                    # Now revert to listening
                    print "Change codewords sent, listening for response ..."
                    self.state = mac.R2_Listening

                elif self.state == mac.R2_Listening:
                    pass

            else:
                raise ValueError("Bad radio ID in IDs.py.")

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



