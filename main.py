import sys

from PyQt5.QtWidgets import (QApplication, QMainWindow, QStatusBar, QTreeWidgetItem, QLabel)

from sigvisualizer import SigVisualizer


def main():
    print("Hello from sigvisualizer!")
    window = SigVisualizer()
    window.show()
    return window                                

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window: SigVisualizer = main()
    sys.exit(app.exec_())

