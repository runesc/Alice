import os, sys
import requests
from os import listdir
from os.path import isfile, join
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import (QIcon, QPixmap, QFontDatabase, QFont)
from PyQt5.QtWidgets import (QMainWindow, QApplication, QStackedWidget, QWidget, QPushButton, QLabel, QVBoxLayout, QProgressBar)

PATH = os.path.dirname(os.path.realpath(__file__)) + os.path.sep + 'data'
SECRET_KEY = "0ad54909-ffdf-47c3-8754-f760eb62e279"

class Downloader(QThread):
    def __init__(self, arch, parent=None):
        super(Downloader, self).__init__(parent)
        # request to server the file and update percent in progress bar

class Installer(QThread):
    def __init__(self, arch, parent=None):
        super(Installer, self).__init__(parent)
        """
            Here is where i have to do the install proccess
        """

class StartApp(QWidget):
    def __init__(self, parent=None, *args):
        super(StartApp, self).__init__(parent)
        self.resize(parent.frameSize())
        self.setStyleSheet('color:#fff')

        # Background image config
        self.background = QLabel(self)
        self.background.resize(self.frameSize())
        self.background.setPixmap(QPixmap(PATH + '/images/bg-alt.png'))
        self.background.setScaledContents(True)

        # Text Box
        self.vertical_layout = QWidget(self)
        self.vertical_layout.setGeometry(0, 123, 800, 90)
        self.vertical_layout.setStyleSheet('background:transparent')
        self.box_layout = QVBoxLayout(self.vertical_layout)
        self.box_layout.setContentsMargins(0, 0, 0, 0)
        
        # Title
        self.app_title = QLabel('Alice', self.vertical_layout)
        self.app_title.setFont(parent.set_font("WorkSans Bold", 32))
        self.app_title.setAlignment(Qt.AlignCenter)
        
        # Subtitle
        self.app_subtitle = QLabel('Una nueva forma de interactuar con tus dispositivos.', self.vertical_layout)
        self.app_subtitle.setFont(parent.set_font("Roboto Regular", 12))
        self.app_subtitle.setAlignment(Qt.AlignCenter)

        # Insert into text box
        self.box_layout.addWidget(self.app_title)
        self.box_layout.addWidget(self.app_subtitle)

        # Install button 
        self.install = QPushButton('Comenzar', self)
        self.install.setFont(parent.set_font("WorkSans SemiBold", 11))
        self.install.setGeometry(330, 227, 140, 40)
        self.install.setStyleSheet('''
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
        ''')

class InstallWindow(QWidget):
    def __init__(self, parent=None, *args):
        super(InstallWindow, self).__init__(parent)
        self.parent = parent
        # layout config
        self.resize(self.parent.frameSize())
        self.setStyleSheet('color:#fff')
        
        # handle click on start and init ui
        self.parent.start_app.install.clicked.connect(self.start_download)
        self.initUI()
    
    def initUI(self):
        # Alternative Background image config
        self.background = QLabel(self)
        self.background.resize(self.frameSize())
        self.background.setPixmap(QPixmap(PATH + '/images/bg.png'))
        self.background.setScaledContents(True)

        # Text Box
        self.vertical_layout = QWidget(self)
        self.vertical_layout.setGeometry(40, 150, 281, 131)
        #self.vertical_layout.setStyleSheet('background:transparent')
        self.box_layout = QVBoxLayout(self.vertical_layout)
        self.box_layout.setContentsMargins(0, 0, 0, 0)

        # Title
        self.install_status = QLabel('Descargando...', self.vertical_layout)
        self.install_status.setFont(self.parent.set_font("WorkSans Bold", 20))
        self.install_status.setAlignment(Qt.AlignLeading | Qt.AlignLeft | Qt.AlignVCenter)

        # Subtitle
        self.install_info = QLabel('Gracias por descargar Alice, pronto podrás disfrutar de todas sus caracteristicas solo usando tu voz.', self.vertical_layout)
        self.install_info.setFont(self.parent.set_font("Roboto Medium", 8))
        self.install_info.setWordWrap(True)
        self.install_info.setAlignment(Qt.AlignLeading | Qt.AlignLeft)
        
        # Add labels to QVBoxLayout
        self.box_layout.addWidget(self.install_status)
        self.box_layout.addWidget(self.install_info)

        # Add StatusBar
        self.status_bar = QProgressBar(self)
        self.status_bar.setGeometry(40, 350, 720, 23)
        self.status_bar.setTextVisible(False)

    def start_download(self):
        # Detect Arch
        platforms = {
            'linux1' : 'Linux',
            'linux2' : 'Linux',
            'darwin' : 'OS X',
            'win32' : 'Windows'
        }
        if sys.platform in platforms:
            self.download = Downloader(platforms[sys.platform])
        else:
            self.install_status.setText("Error :(")
            self.install_info.setText("Tu sistema operativo no es compatible con Alice pero no te preocupes pronto lo será, mientras tanto puedes usarla en otros dispositivos.")
            self.status_bar.close()

class InstallComplete(QWidget):
    def __init__(self, parent=None, *args):
        super(InstallComplete, self).__init__(parent)
        self.setStyleSheet("color: #fff;")
        self.box_icon = QLabel(self)
        self.box_icon.setGeometry(340, 70, 128, 128)
        self.box_icon.setPixmap(QPixmap(PATH + '/images/success.png'))
        self.box_icon.setScaledContents(True)

        
        # Title
        self.thanks = QLabel('¡Gracias!', self)
        self.thanks.setFont(parent.set_font("WorkSans Light", 23))
        self.thanks.setGeometry(200, 205, 400, 50)
        self.thanks.setAlignment(Qt.AlignCenter)

        # Subtitle
        self.install_complete = QLabel('Haz instalado Alice correctamente ahora estas a un clic de cambiar la forma en la que usas tus dispositivos.', self)
        self.install_complete.setFont(parent.set_font("Roboto Regular", 10))
        self.install_complete.setGeometry(210, 249, 400, 50)
        self.install_complete.setWordWrap(True)
        self.install_complete.setAlignment(Qt.AlignCenter)

        # Launch app button
        self.launch_app = QPushButton("Iniciar", self)
        self.launch_app.setFont(parent.set_font("WorkSans SemiBold", 11))
        self.launch_app.setGeometry(332, 313, 140, 40)
        self.launch_app.setStyleSheet('''
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
        ''')


    def launch_app(self):pass
        
        
class MainApp(QMainWindow):
    def __init__(self):
        super(MainApp, self).__init__()
        # App metadata
        self.setWindowTitle('Alice Installer')
        self.setWindowIcon(QIcon(PATH + '/images/icon.png'))
        self.setWindowFlags(Qt.WindowCloseButtonHint)
        self.setFixedSize(800, 400)

        self.load_fonts()

        # Set central widget and init ui
        self.central_widget = QWidget(self)
        self.central_widget.resize(self.frameSize())
        self.initUI()

    def initUI(self):
        self.stacked_widget = QStackedWidget(self.central_widget)
        self.stacked_widget.resize(self.frameSize())
        self.stacked_widget.setAutoFillBackground(False)
        self.stacked_widget.setStyleSheet('background-color: #111118;')

        # Import activities and add to stack
        self.start_app = StartApp(self)
        self.install_window = InstallWindow(self)
        self.install_complete = InstallComplete(self) 
        
        self.stacked_widget.addWidget(self.start_app)
        self.stacked_widget.addWidget(self.install_window)
        self.stacked_widget.addWidget(self.install_complete)

        # Activities Triggers
        self.start_app.install.clicked.connect(lambda: self.switch_layout(1))

    def load_fonts(self, path=PATH + '/fonts/'):
        fonts = [f for f in listdir(path) if isfile(join(path, f))]

        self.font_db = {}
        
        # For each font finded in /fonts add to Application and create a directory of fonts
        for font in fonts:
            self.font_id = QFontDatabase.addApplicationFont(path + font)
            self.font_db[font.replace("-", " ")[:-4]] = self.font_id
    
    def set_font(self, font_name, font_size):
        selected_font = QFontDatabase.applicationFontFamilies(self.font_db[font_name])
        font = QFont()
        font.setFamily(selected_font[0])
        font.setPointSize(int(font_size))
        return font        

    def switch_layout(self, index):
        self.stacked_widget.setCurrentIndex(index)
 
if __name__ == '__main__':
    app = QApplication([])
    window = MainApp()
    window.show()
    app.exec_()
    