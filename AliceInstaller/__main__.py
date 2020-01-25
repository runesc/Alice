import os
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import (QMainWindow, QApplication, QStackedWidget, QWidget, QPushButton, QLabel, QVBoxLayout)

# Functions section

PATH = os.path.dirname(os.path.realpath(__file__)) + os.path.sep + 'data'


class StartApp(QWidget):
    def __init__(self, parent=None, *args):
        super(StartApp, self).__init__(parent)
        self.resize(800,400)

        # Background image config
        self.background = QLabel(self)
        self.background.resize(self.frameSize())
        self.background.setPixmap(QPixmap(PATH + '/images/bg-alt.png'))
        self.background.setScaledContents(True)

        # Text Box
        self.vertical_layout = QWidget(self)
        self.vertical_layout.setGeometry(0, 123, 800, 90)
        self.vertical_layout.setStyleSheet("background:transparent")
        self.box_layout = QVBoxLayout(self.vertical_layout)
        
        # Title
        self.app_title = QLabel("Alice", self.vertical_layout)
        self.app_title.setAlignment(Qt.AlignCenter)
        
        # Subtitle
        self.app_subtitle = QLabel("Una nueva forma de interactuar con tus dispositivos.", self.vertical_layout)
        self.app_subtitle.setAlignment(Qt.AlignCenter)

        # Insert into text box
        self.box_layout.addWidget(self.app_title)
        self.box_layout.addWidget(self.app_subtitle)

        # Install button 
        self.install = QPushButton("Comenzar", self)
        self.install.setGeometry(330, 227, 140, 40)
        self.install.setStyleSheet("""
            QPushButton:hover:!pressed
            {
                background: #40C07D;
            }
            
            QPushButton{
                background:#00E291;
                color: #fff;
                border:none;
                border-radius:5px;
            }
        """)

class InstallWindow(QWidget):
    def __init__(self, parent=None, *args):
        super(InstallWindow, self).__init__(parent)

        self.btn = QPushButton("GO BACK!!", self)
        self.btn.setStyleSheet("background:white")

        self.end_install = QPushButton("End install layout", self)
        self.end_install.move(100,0)
        self.end_install.setStyleSheet("background:white")
        
class InstallComplete(QWidget):
    def __init__(self, parent=None, *args):
        super(InstallComplete, self).__init__(parent)
        self.btn = QPushButton("GO BACK TO START!!", self)
        self.btn.setStyleSheet("background:white")
        
        
class MainApp(QMainWindow):
    def __init__(self):
        super(MainApp, self).__init__()
        # App metadata
        self.setWindowTitle('Alice Installer')
        self.setWindowIcon(QIcon(PATH + '/images/icon.png'))
        self.setWindowFlags(Qt.WindowCloseButtonHint)
        self.setFixedSize(800, 400)

        # Set central widget and init ui
        self.central_widget = QWidget(self)
        self.central_widget.resize(self.frameSize())
        self.initUI()

    def initUI(self):
        self.stacked_widget = QStackedWidget(self.central_widget)
        self.stacked_widget.resize(self.frameSize())
        self.stacked_widget.setAutoFillBackground(False)
        self.stacked_widget.setStyleSheet("background-color: #111118;")

        # Import activities and add to stack
        self.start_app = StartApp()
        self.install_window = InstallWindow()
        self.install_complete = InstallComplete() 
        
        self.stacked_widget.addWidget(self.start_app)
        self.stacked_widget.addWidget(self.install_window)
        self.stacked_widget.addWidget(self.install_complete)
        
        # Set current activitie
        self.stacked_widget.setCurrentIndex(0)

        # Activities Triggers
        self.start_app.install.clicked.connect(lambda: self.switch_layout(1))
        self.install_window.btn.clicked.connect(lambda: self.switch_layout(0))


    def switch_layout(self, index):
        self.stacked_widget.setCurrentIndex(index)
 
if __name__ == '__main__':
    app = QApplication([])
    window = MainApp()
    window.show()
    app.exec_()
    