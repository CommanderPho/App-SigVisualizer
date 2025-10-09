import sys
import logging
from PyQt5.QtCore import QSize, Qt, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QApplication, QMainWindow, QStatusBar, QTreeWidgetItem, QLabel)
from PyQt5.QtCore import QTimer

from ui_sigvisualizer import Ui_MainWindow

from PyQt5.QtCore import QTimer, QThreadPool, QRunnable, pyqtSlot
# ...existing code...


logger = logging.getLogger('phohale.sigvisualizer')


class UpdateStreamsTask(QRunnable):
    def __init__(self, update_func):
        super().__init__()
        self.update_func = update_func

    @pyqtSlot()
    def run(self):
        logger.info(f'UpdateStreamsTask run() started.')
        self.update_func()
        logger.info(f'UpdateStreamsTask run() finished.')
		

class SigVisualizer(QMainWindow):
	""" Main app window for the stream/signal visualizer 
	On the left side of the window is a tree widget that lists the available streams.
	On the right side of the window is a plot widget that displays the time series data for the selected stream.
	On the bottom of the window is a status bar that displays the sampling rate of the selected stream.
	On the top of the window is a toolbar that allows the user to toggle the panel and update the streams.
	
	"""

	stream_expanded = pyqtSignal(str)

	def __init__(self):
		super().__init__()
		logger.info(f'SigVisualizer initialized.')
		
		self.ui = Ui_MainWindow()
		self.ui.setupUi(self)
		self.setWindowTitle('Real Time Signal Visualizer')
		self.ui.treeWidget.setHeaderLabel('Streams')
		self.setWindowIcon(QIcon('sigvisualizer.ico'))

		self.statusBar = QStatusBar()
		self.setStatusBar(self.statusBar)

		self.threadpool = QThreadPool()

		self.ui.toggleButton.setIcon(QIcon("icons/chevron_left.svg"))
		self.ui.toggleButton.setIconSize(QSize(30, 30))

		self.ui.toggleButton.clicked.connect(self.toggle_panel)
		# self.ui.updateButton.clicked.connect(self.ui.widget.dataTr.update_streams)
		self.ui.updateButton.clicked.connect(self.manual_refresh_streams)
		self.ui.widget.dataTr.updateStreamNames.connect(self.update_metadata_widget)
		self.ui.widget.dataTr.updateStreamNames.connect(self.ui.widget.on_streams_updated)
		self.panelHidden = False

		self.ui.treeWidget.itemExpanded.connect(self.tree_item_expanded)
		self.ui.treeWidget.itemChanged.connect(self.tree_item_changed)
		self.stream_expanded.connect(self.ui.widget.dataTr.handle_stream_expanded)

		self.ui.btnShowDataStream.clicked.connect(self.toggle_data_stream_window)
		self.dataStreamHidden = False

		self.auto_refresh_timer = QTimer(self)
		self.auto_refresh_timer.timeout.connect(self.ui.widget.dataTr.update_streams)

		self.ui.chkEnableAutoUpdate.clicked.connect(self.toggle_auto_refresh_streams)
		self.toggle_auto_refresh_streams()


		self.ui.btnUpdateActivePlots.clicked.connect(self.perform_update_all_plots)



	

	def manual_refresh_streams(self):
		self.run_update_streams()
		if self.ui.chkEnableAutoUpdate.isChecked():
			self.auto_refresh_timer.start(2000) ## reset timer

	def run_update_streams(self):
		logger.info(f'SigVisualizer run_update_streams() started.')
		task = UpdateStreamsTask(self.ui.widget.dataTr.update_streams)
		self.threadpool.start(task)

	def toggle_auto_refresh_streams(self):
		logger.info(f'SigVisualizer toggle_auto_refresh_streams() started.')
		## toggle a timer to auto-refresh if should_auto_update
		should_auto_update: bool = self.ui.chkEnableAutoUpdate.isChecked()
		if should_auto_update:
			self.auto_refresh_timer.timeout.disconnect()
			self.auto_refresh_timer.timeout.connect(self.run_update_streams)
			self.auto_refresh_timer.start(2000)  # refresh every 2 seconds
		else:
			self.auto_refresh_timer.stop()
			

	def tree_item_expanded(self, widget_item):
		logger.info(f'SigVisualizer tree_item_expanded() started.')
		name = widget_item.text(0)
		enable_only_one_stream_expanded: bool = False
		if enable_only_one_stream_expanded:
			for it_ix in range(self.ui.treeWidget.topLevelItemCount()):
				item = self.ui.treeWidget.topLevelItem(it_ix)
				if item.text(0) != name:
					item.setExpanded(False)

		self.stream_expanded.emit(name)


	def update_metadata_widget(self, metadata, default_idx):
		""" called when the streams are changed (new streams/etc)
		1. Need to update the tree widget with the new streams and channels 
		2. Update the plotted graphs (building new ones/removing old ones if needed) so they can be displayed when updated date is received.

		TODO 2025-10-09 - moving away from single stream selection (specified by default_idx) to being able to preview multiple streams simultaneously.

		"""
		logger.info(f'SigVisualizer update_metadata_widget() started.')
		for s_ix, s_meta in enumerate(metadata):
			item = QTreeWidgetItem(self.ui.treeWidget)
			item.setText(0, s_meta["name"])

			for m in range(s_meta["ch_count"]):
				channel_item = QTreeWidgetItem(item)
				# channel_item.setText(0, 'Channel {}'.format(m+1))
				channel_name: str = s_meta["ch_labels"][m]
				if not channel_name:
					channel_name = f'Ch[{m}]'

				channel_item.setText(0, channel_name)
				channel_item.setToolTip(0, f'Channel[{m+1}]')
				channel_item.setCheckState(0, Qt.Checked)

			# item.setExpanded(True if s_ix == default_idx else False)
			self.ui.treeWidget.addTopLevelItem(item)

		# Expand all items recursively by default, without emitting selection changes
		self.ui.treeWidget.blockSignals(True)
		self.ui.treeWidget.expandAll()
		self.ui.treeWidget.blockSignals(False)
		self.ui.treeWidget.setAnimated(True)
		if (default_idx is not None) and (default_idx in metadata):		
			self.statusBar.showMessage("Sampling rate: {}Hz".format(metadata[default_idx]["srate"]))
		else:
			self.statusBar.showMessage("No valid sampling streams.")
			


	def perform_update_all_plots(self):
		logger.info(f'SigVisualizer perform_update_all_plots() started.')
		plot_widget = self.ui.widget
		plot_widget.reset()
		plot_widget.dataTr.update_streams()
		# plot_widget.get_data(sig_ts=self.ui.widget.dataTr.sig_ts, sig_buffer=self.ui.widget.dataTr.sig_buffer, marker_ts=self.ui.widget.dataTr.marker_ts, marker_buffer=self.ui.widget.dataTr.marker_buffer)
		logger.info(f'SigVisualizer perform_update_all_plots() finished.')
		# plot_widget.get_data()
			

	def tree_item_changed(self, item, column):
		"""Toggle channel visibility in the plot when a channel checkbox changes."""
		try:
			parent = item.parent()
			if parent is None:
				return
			stream_name = parent.text(0)
			channel_name = item.text(0)
			enabled = (item.checkState(0) == Qt.Checked)
			self.ui.widget.set_channel_enabled(stream_name, channel_name, enabled)
		except Exception as e:
			logger.exception("tree_item_changed failed: %s", e)

	def toggle_panel(self):
		logger.info(f'SigVisualizer toggle_panel() started.')
		if self.panelHidden:
			self.panelHidden = False
			self.ui.treeWidget.show()
			self.ui.updateButton.show()
			self.ui.toggleButton.setIcon(QIcon("icons/chevron_left.svg"))
			self.ui.toggleButton.setIconSize(QSize(30, 30))
		else:
			self.panelHidden = True
			self.ui.treeWidget.hide()
			self.ui.updateButton.hide()
			self.ui.toggleButton.setIcon(QIcon("icons/chevron_right.svg"))
			self.ui.toggleButton.setIconSize(QSize(30, 30))


	def toggle_data_stream_window(self):
		logger.info(f'SigVisualizer toggle_data_stream_window() started.')
		# Show/Hide the raw data stream
		# self.ui.nd = NewDialog(self)
		# self.ui.nd.show()
		self.secondWindow = SecondWindow()
		self.secondWindow.show()


class SecondWindow(QMainWindow):
    def __init__(self):
        super(SecondWindow, self).__init__()
        logger.info(f'SecondWindow initialized.')
        lbl = QLabel('Second Window', self)
        

# class NewDialog(QWidget):
# 	def __init__(self, parent):
# 		super(NewDialog, self).__init__(parent)

if __name__ == '__main__':
	app = QApplication(sys.argv)
	window = SigVisualizer()
	window.show()
	sys.exit(app.exec_())
