import sys

from PyQt5.QtCore import QSize, Qt, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QApplication, QMainWindow, QStatusBar, QTreeWidgetItem, QLabel)

from ui_sigvisualizer import Ui_MainWindow


class SigVisualizer(QMainWindow):
	stream_expanded = pyqtSignal(str)

	def __init__(self):
		super().__init__()
		self.ui = Ui_MainWindow()
		self.ui.setupUi(self)
		self.setWindowTitle('Real Time Signal Visualizer')
		self.ui.treeWidget.setHeaderLabel('Streams')
		self.setWindowIcon(QIcon('sigvisualizer.ico'))

		self.statusBar = QStatusBar()
		self.setStatusBar(self.statusBar)

		self.ui.toggleButton.setIcon(QIcon("icons/chevron_left.svg"))
		self.ui.toggleButton.setIconSize(QSize(30, 30))

		self.ui.toggleButton.clicked.connect(self.toggle_panel)
		self.ui.updateButton.clicked.connect(self.ui.widget.dataTr.update_streams)
		self.ui.widget.dataTr.updateStreamNames.connect(self.update_metadata_widget)
		self.panelHidden = False

		self.ui.treeWidget.itemExpanded.connect(self.tree_item_expanded)
		self.stream_expanded.connect(self.ui.widget.dataTr.handle_stream_expanded)

		self.ui.btnShowDataStream.clicked.connect(self.toggle_data_stream_window)
		self.dataStreamHidden = False

	def tree_item_expanded(self, widget_item):
		name = widget_item.text(0)
		for it_ix in range(self.ui.treeWidget.topLevelItemCount()):
			item = self.ui.treeWidget.topLevelItem(it_ix)
			if item.text(0) != name:
				item.setExpanded(False)
		self.stream_expanded.emit(name)

	def update_metadata_widget(self, metadata, default_idx):
		for s_ix, s_meta in enumerate(metadata):
			item = QTreeWidgetItem(self.ui.treeWidget)
			item.setText(0, s_meta["name"])

			for m in range(s_meta["ch_count"]):
				channel_item = QTreeWidgetItem(item)
				# channel_item.setText(0, 'Channel {}'.format(m+1))
				channel_item.setText(0, s_meta["ch_labels"][m])
				channel_item.setToolTip(0, 'Channel {}'.format(m+1))
				channel_item.setCheckState(0, Qt.Checked)

			item.setExpanded(True if s_ix == default_idx else False)
			self.ui.treeWidget.addTopLevelItem(item)

		self.ui.treeWidget.setAnimated(True)
		if (default_idx is not None) and (default_idx in metadata):		
			self.statusBar.showMessage("Sampling rate: {}Hz".format(metadata[default_idx]["srate"]))
		else:
			self.statusBar.showMessage("No valid sampling streams.")
			


	def toggle_panel(self):
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
		# Show/Hide the raw data stream
		# self.ui.nd = NewDialog(self)
		# self.ui.nd.show()
		self.secondWindow = SecondWindow()
		self.secondWindow.show()


class SecondWindow(QMainWindow):
    def __init__(self):
        super(SecondWindow, self).__init__()
        lbl = QLabel('Second Window', self)
        

# class NewDialog(QWidget):
# 	def __init__(self, parent):
# 		super(NewDialog, self).__init__(parent)

if __name__ == '__main__':
	app = QApplication(sys.argv)
	window = SigVisualizer()
	window.show()
	sys.exit(app.exec_())
