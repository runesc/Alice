from AliceInstaller.__main__ import *

if __name__ == '__main__':
    app = QApplication([])
    window = MainApp()
    window.show()
    app.exec_()
    