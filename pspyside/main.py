import os
import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget
from PySide6.QtCore import Qt, QCoreApplication
from screens.splash_screen import SplashScreen
from screens.main_screen import MainScreen
from screens.input_screen import InputScreen
from screens.complete_screen import CompleteScreen

class PSApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PSApp")
        
        # 배포 환경과 개발 환경에 따라 화면 크기 설정
        if getattr(sys, 'frozen', False):
            # 배포 환경 (executable)
            self.screen_size = (2736, 1824)
            self.base_dir = os.path.dirname(os.path.abspath(sys.executable))
        else:
            # 개발 환경 (__file__)
            self.screen_size = (1920, 1080)
            self.base_dir = os.path.dirname(os.path.abspath(__file__))
            
        self.setFixedSize(*self.screen_size)
        self.showFullScreen()
        
        os.chdir(self.base_dir)

        self.stack = QStackedWidget()
        self.setupStack()

        self.setCentralWidget(self.stack)

    def setupStack(self):
        self.stack = QStackedWidget()
        self.splash_screen = SplashScreen(self.stack, self.screen_size, self)
        self.main_screen = MainScreen(self.stack, self.screen_size, self)
        self.input_screen = InputScreen(self.stack, self.screen_size, self)
        self.complete_screen = CompleteScreen(self.stack, self.screen_size, self)

        self.stack.addWidget(self.splash_screen)
        self.stack.addWidget(self.main_screen)
        self.stack.addWidget(self.input_screen)
        self.stack.addWidget(self.complete_screen)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
    
    def closeApplication(self):
        """앱 종료 동작"""
        QCoreApplication.instance().quit() 

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PSApp()
    window.show()
    sys.exit(app.exec())


