#!/usr/bin/env python2
# -*- coding: utf-8 -*-
##################################################
# GNU Radio Python Flow Graph
# Title: Top Block
# Generated: Sun Jun 17 13:11:29 2018
##################################################

if __name__ == '__main__':
    import ctypes
    import sys
    if sys.platform.startswith('linux'):
        try:
            x11 = ctypes.cdll.LoadLibrary('libX11.so')
            x11.XInitThreads()
        except:
            print "Warning: failed to XInitThreads()"

from PyQt4 import Qt
from gnuradio import blocks
from gnuradio import digital
from gnuradio import eng_notation
from gnuradio import fec
from gnuradio import gr
from gnuradio.eng_option import eng_option
from gnuradio.filter import firdes
from grc_gnuradio import blks2 as grc_blks2
from optparse import OptionParser
import limesdr
import sys


class top_block(gr.top_block, Qt.QWidget):

    def __init__(self, frame_sz_bytes=30):
        gr.top_block.__init__(self, "Top Block")
        Qt.QWidget.__init__(self)
        self.setWindowTitle("Top Block")
        try:
            self.setWindowIcon(Qt.QIcon.fromTheme('gnuradio-grc'))
        except:
            pass
        self.top_scroll_layout = Qt.QVBoxLayout()
        self.setLayout(self.top_scroll_layout)
        self.top_scroll = Qt.QScrollArea()
        self.top_scroll.setFrameStyle(Qt.QFrame.NoFrame)
        self.top_scroll_layout.addWidget(self.top_scroll)
        self.top_scroll.setWidgetResizable(True)
        self.top_widget = Qt.QWidget()
        self.top_scroll.setWidget(self.top_widget)
        self.top_layout = Qt.QVBoxLayout(self.top_widget)
        self.top_grid_layout = Qt.QGridLayout()
        self.top_layout.addLayout(self.top_grid_layout)

        self.settings = Qt.QSettings("GNU Radio", "top_block")
        self.restoreGeometry(self.settings.value("geometry").toByteArray())

        ##################################################
        # Parameters
        ##################################################
        self.frame_sz_bytes = frame_sz_bytes

        ##################################################
        # Variables
        ##################################################
        self.samp_rate = samp_rate = 32e3
        
        
        self.ccsds_encoder_var = ccsds_encoder_var = fec.ccsds_encoder_make(frame_sz_bytes * 8, 0, fec.CC_TAILBITING)
            
        
        
        self.cc_decoder_var = cc_decoder_var = fec.cc_decoder.make(frame_sz_bytes * 8, 7, 2, ([109,79]), 0, -1, fec.CC_TAILBITING, False)
            

        ##################################################
        # Blocks
        ##################################################
        self.limesdr_sink_0 = limesdr.sink(0,
        		       2,
        		       1,
        		       0,
        		       0,
        		       '',
        		       144e6,
        		       32e3,
        		       1,
        		       0,
        		       10e6,
        		       0,
        		       10e6,
        		       1,
        		       1,
        		       1,
        		       0,
        		       10e6,
        		       0,
        		       10e6,
        		       0,
        		       0,
        		       0,
        		       0,
        		       60,
        		       60)
        self.fec_extended_encoder_0 = fec.extended_encoder(encoder_obj_list=ccsds_encoder_var, threading='capillary', puncpat='11')
        self.digital_dxpsk_mod_0 = digital.dbpsk_mod(
        	samples_per_symbol=2,
        	excess_bw=0.35,
        	mod_code="gray",
        	verbose=True,
        	log=False)
        	
        self.blocks_unpack_k_bits_bb_0 = blocks.unpack_k_bits_bb(16)
        self.blocks_file_source_0 = blocks.file_source(gr.sizeof_char*1, '/home/jeff/EE420/FinalProj/testdat.txt', True)
        self.blks2_packet_encoder_1 = grc_blks2.packet_mod_b(grc_blks2.packet_encoder(
        		samples_per_symbol=2,
        		bits_per_symbol=1,
        		preamble='',
        		access_code='',
        		pad_for_usrp=False,
        	),
        	payload_length=0,
        )

        ##################################################
        # Connections
        ##################################################
        self.connect((self.blks2_packet_encoder_1, 0), (self.digital_dxpsk_mod_0, 0))    
        self.connect((self.blocks_file_source_0, 0), (self.blocks_unpack_k_bits_bb_0, 0))    
        self.connect((self.blocks_unpack_k_bits_bb_0, 0), (self.fec_extended_encoder_0, 0))    
        self.connect((self.digital_dxpsk_mod_0, 0), (self.limesdr_sink_0, 0))    
        self.connect((self.fec_extended_encoder_0, 0), (self.blks2_packet_encoder_1, 0))    

    def closeEvent(self, event):
        self.settings = Qt.QSettings("GNU Radio", "top_block")
        self.settings.setValue("geometry", self.saveGeometry())
        event.accept()

    def get_frame_sz_bytes(self):
        return self.frame_sz_bytes

    def set_frame_sz_bytes(self, frame_sz_bytes):
        self.frame_sz_bytes = frame_sz_bytes

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate

    def get_ccsds_encoder_var(self):
        return self.ccsds_encoder_var

    def set_ccsds_encoder_var(self, ccsds_encoder_var):
        self.ccsds_encoder_var = ccsds_encoder_var

    def get_cc_decoder_var(self):
        return self.cc_decoder_var

    def set_cc_decoder_var(self, cc_decoder_var):
        self.cc_decoder_var = cc_decoder_var


def argument_parser():
    parser = OptionParser(usage="%prog: [options]", option_class=eng_option)
    parser.add_option(
        "", "--frame-sz-bytes", dest="frame_sz_bytes", type="intx", default=30,
        help="Set Frame Size Bytes [default=%default]")
    return parser


def main(top_block_cls=top_block, options=None):
    if options is None:
        options, _ = argument_parser().parse_args()

    from distutils.version import StrictVersion
    if StrictVersion(Qt.qVersion()) >= StrictVersion("4.5.0"):
        style = gr.prefs().get_string('qtgui', 'style', 'raster')
        Qt.QApplication.setGraphicsSystem(style)
    qapp = Qt.QApplication(sys.argv)

    tb = top_block_cls(frame_sz_bytes=options.frame_sz_bytes)
    tb.start()
    tb.show()

    def quitting():
        tb.stop()
        tb.wait()
    qapp.connect(qapp, Qt.SIGNAL("aboutToQuit()"), quitting)
    qapp.exec_()


if __name__ == '__main__':
    main()
