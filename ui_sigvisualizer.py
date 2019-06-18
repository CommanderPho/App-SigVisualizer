# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file '/Users/pho/Repo/App-SigVisualizer/ui_sigvisualizer.ui'
#
# Created by: PyQt5 UI code generator 5.6
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1299, 800)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayout = QtWidgets.QGridLayout(self.centralwidget)
        self.gridLayout.setContentsMargins(-1, -1, -1, 12)
        self.gridLayout.setObjectName("gridLayout")
        self.widget = PaintWidget(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.widget.sizePolicy().hasHeightForWidth())
        self.widget.setSizePolicy(sizePolicy)
        self.widget.setObjectName("widget")
        self.gridLayout.addWidget(self.widget, 0, 2, 1, 1)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)
        self.horizontalLayout.setContentsMargins(0, -1, -1, -1)
        self.horizontalLayout.setSpacing(8)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.btnShowDataStream = QtWidgets.QToolButton(self.centralwidget)
        self.btnShowDataStream.setMinimumSize(QtCore.QSize(0, 22))
        self.btnShowDataStream.setMaximumSize(QtCore.QSize(156, 22))
        self.btnShowDataStream.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
        self.btnShowDataStream.setObjectName("btnShowDataStream")
        self.horizontalLayout.addWidget(self.btnShowDataStream)
        self.gridLayout.addLayout(self.horizontalLayout, 1, 2, 1, 1)
        self.toggleButton = QtWidgets.QPushButton(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.toggleButton.sizePolicy().hasHeightForWidth())
        self.toggleButton.setSizePolicy(sizePolicy)
        self.toggleButton.setMinimumSize(QtCore.QSize(20, 698))
        self.toggleButton.setMaximumSize(QtCore.QSize(20, 16777215))
        self.toggleButton.setBaseSize(QtCore.QSize(20, 698))
        self.toggleButton.setText("")
        self.toggleButton.setObjectName("toggleButton")
        self.gridLayout.addWidget(self.toggleButton, 0, 0, 2, 1)
        self.treeWidget = QtWidgets.QTreeWidget(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.treeWidget.sizePolicy().hasHeightForWidth())
        self.treeWidget.setSizePolicy(sizePolicy)
        self.treeWidget.setMaximumSize(QtCore.QSize(180, 16777215))
        self.treeWidget.setObjectName("treeWidget")
        self.treeWidget.headerItem().setText(0, "1")
        self.gridLayout.addWidget(self.treeWidget, 0, 1, 1, 1)
        self.updateButton = QtWidgets.QPushButton(self.centralwidget)
        self.updateButton.setMinimumSize(QtCore.QSize(100, 32))
        self.updateButton.setMaximumSize(QtCore.QSize(16777215, 32))
        self.updateButton.setObjectName("updateButton")
        self.gridLayout.addWidget(self.updateButton, 1, 1, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1299, 22))
        self.menubar.setObjectName("menubar")
        self.menuViews = QtWidgets.QMenu(self.menubar)
        self.menuViews.setObjectName("menuViews")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.actionShow_Received_Data_Stream = QtWidgets.QAction(MainWindow)
        self.actionShow_Received_Data_Stream.setObjectName("actionShow_Received_Data_Stream")
        self.menuViews.addAction(self.actionShow_Received_Data_Stream)
        self.menubar.addAction(self.menuViews.menuAction())

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.btnShowDataStream.setText(_translate("MainWindow", "Show Received Data Stream..."))
        self.updateButton.setText(_translate("MainWindow", "Update Streams"))
        self.menuViews.setTitle(_translate("MainWindow", "Views"))
        self.actionShow_Received_Data_Stream.setText(_translate("MainWindow", "Show Received Data Stream..."))

from paintwidget import PaintWidget
