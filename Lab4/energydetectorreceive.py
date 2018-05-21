#!/usr/bin/env python2
# -*- coding: utf-8 -*-
##################################################
# GNU Radio Python Flow Graph
# Title: Energydetectorreceive
# Generated: Mon May 21 10:51:08 2018
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

import os
import sys
sys.path.append(os.environ.get('GRC_HIER_PATH', os.path.expanduser('~/.grc_gnuradio')))

from PyQt4 import Qt
from fftshift_for_logpower import fftshift_for_logpower  # grc-generated hier_block
from gnuradio import blocks
from gnuradio import eng_notation
from gnuradio import gr
from gnuradio import uhd
from gnuradio.eng_option import eng_option
from gnuradio.fft import logpwrfft
from gnuradio.filter import firdes
from optparse import OptionParser
import threading
import time


class energydetectorreceive(gr.top_block, Qt.QWidget):

    def __init__(self):
        gr.top_block.__init__(self, "Energydetectorreceive")
        Qt.QWidget.__init__(self)
        self.setWindowTitle("Energydetectorreceive")
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

        self.settings = Qt.QSettings("GNU Radio", "energydetectorreceive")
        self.restoreGeometry(self.settings.value("geometry").toByteArray())

        ##################################################
        # Variables
        ##################################################
        self.variable_function_probe_0 = variable_function_probe_0 = 0
        self.samp_rate = samp_rate = 1e6
	self.busy = busy = 0

        ##################################################
        # Blocks
        ##################################################
        self.blocks_probe_signal_vx_0 = blocks.probe_signal_vf(1024)
        def _variable_function_probe_0_probe():
            while True:
                val = self.blocks_probe_signal_vx_0.level()
		self.busy = val[512]
		print(self.busy)
                try:
                    self.set_variable_function_probe_0(val)
                except AttributeError:
                    pass
                time.sleep(1.0 / (10))
        _variable_function_probe_0_thread = threading.Thread(target=_variable_function_probe_0_probe)
        _variable_function_probe_0_thread.daemon = True
        _variable_function_probe_0_thread.start()
        self.uhd_usrp_source_0 = uhd.usrp_source(
        	",".join(("", "")),
        	uhd.stream_args(
        		cpu_format="fc32",
        		channels=range(1),
        	),
        )
        self.uhd_usrp_source_0.set_samp_rate(samp_rate)
        self.uhd_usrp_source_0.set_center_freq(5.34e9, 0)
        self.uhd_usrp_source_0.set_gain(30, 0)
        self.uhd_usrp_source_0.set_antenna("J1", 0)
        self.uhd_usrp_source_0.set_bandwidth(25e6, 0)
        self.logpwrfft_x_4 = logpwrfft.logpwrfft_c(
        	sample_rate=samp_rate,
        	fft_size=1024,
        	ref_scale=2,
        	frame_rate=30,
        	avg_alpha=1,
        	average=True,
        )
        self.fftshift_for_logpower_0 = fftshift_for_logpower(
            fft_size=1024,
        )
        self.blocks_vector_to_stream_2 = blocks.vector_to_stream(gr.sizeof_float*1, 1024)
        self.blocks_threshold_ff_2 = blocks.threshold_ff(-100, -85, 0)
        self.blocks_stream_to_vector_0 = blocks.stream_to_vector(gr.sizeof_float*1, 1024)

        ##################################################
        # Connections
        ##################################################
        self.connect((self.blocks_stream_to_vector_0, 0), (self.blocks_probe_signal_vx_0, 0))    
        self.connect((self.blocks_threshold_ff_2, 0), (self.blocks_stream_to_vector_0, 0))    
        self.connect((self.blocks_vector_to_stream_2, 0), (self.blocks_threshold_ff_2, 0))    
        self.connect((self.fftshift_for_logpower_0, 0), (self.blocks_vector_to_stream_2, 0))    
        self.connect((self.logpwrfft_x_4, 0), (self.fftshift_for_logpower_0, 0))    
        self.connect((self.uhd_usrp_source_0, 0), (self.logpwrfft_x_4, 0))    

    def closeEvent(self, event):
        self.settings = Qt.QSettings("GNU Radio", "energydetectorreceive")
        self.settings.setValue("geometry", self.saveGeometry())
        event.accept()


    def get_variable_function_probe_0(self):
        return self.variable_function_probe_0

    def set_variable_function_probe_0(self, variable_function_probe_0):
        self.variable_function_probe_0 = variable_function_probe_0

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.logpwrfft_x_4.set_sample_rate(self.samp_rate)
        self.uhd_usrp_source_0.set_samp_rate(self.samp_rate)


def main(top_block_cls=energydetectorreceive, options=None):

    from distutils.version import StrictVersion
    if StrictVersion(Qt.qVersion()) >= StrictVersion("4.5.0"):
        style = gr.prefs().get_string('qtgui', 'style', 'raster')
        Qt.QApplication.setGraphicsSystem(style)
    qapp = Qt.QApplication(sys.argv)

    tb = top_block_cls()
    tb.start()
    tb.show()

    def quitting():
        tb.stop()
        tb.wait()
    qapp.connect(qapp, Qt.SIGNAL("aboutToQuit()"), quitting)
    qapp.exec_()


if __name__ == '__main__':
    main()
