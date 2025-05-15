from PySide6.QtWidgets import QWidget, QLabel, QPushButton
from PySide6.QtGui import QPixmap
from PySide6.QtCore import QRect
import os

class SplashScreen(QWidget):
    def __init__(self, stack, screen_size, main_window):
        super().__init__()
        self.stack = stack
        self.screen_size = screen_size
        self.main_window = main_window
        
        # 원본 이미지 크기와 타겟 클릭 영역 정의
        self.original_image_size = (2736, 1824)
        self.original_click_area = QRect(826, 1259, 1904-826, 1551-1259)
        
        self.setupUI()

    def setupUI(self):
        self.setupBackground()
        self.addCloseButton()

    def setupBackground(self):
        # main.py에서 이미 chdir을 실행했으므로 단순 상대 경로 사용
        pixmap = QPixmap("resources/splash.jpg")  # 이미지 로드
        background_label = QLabel(self)
        background_label.setPixmap(pixmap)
        background_label.setScaledContents(True)  # QLabel 크기에 맞게 이미지 조정
        background_label.resize(*self.screen_size)  # 전체 화면 크기로 설정

    def addCloseButton(self):
        """오른쪽 상단에 닫기 버튼 추가"""
        self.close_button = QPushButton("X", self)
        self.close_button.setFixedSize(200, 200)
        self.close_button.move(self.screen_size[0] - 50, 10)  # 오른쪽 상단 위치
        self.close_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 92, 92, 0);  /* 완전히 투명하게 설정 */
                color: rgba(255, 255, 255, 0);  /* 텍스트도 완전히 투명하게 설정 (보이지 않음) */
                font-weight: bold;
                border: none;
                border-radius: 20px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: rgba(224, 74, 74, 0);  /* 호버 시에도 완전히 투명하게 설정 */
            }
        """)
        self.close_button.clicked.connect(self.main_window.closeApplication)

    def get_scaled_click_area(self):
        """원본 이미지 크기를 기준으로 현재 화면 크기에 맞게 클릭 영역을 조정"""
        x_ratio = self.screen_size[0] / self.original_image_size[0]
        y_ratio = self.screen_size[1] / self.original_image_size[1]
        
        scaled_x = int(self.original_click_area.x() * x_ratio)
        scaled_y = int(self.original_click_area.y() * y_ratio)
        scaled_width = int(self.original_click_area.width() * x_ratio)
        scaled_height = int(self.original_click_area.height() * y_ratio)
        
        return QRect(scaled_x, scaled_y, scaled_width, scaled_height)

    def mousePressEvent(self, event):
        click_area = self.get_scaled_click_area()
        if click_area.contains(event.position().toPoint()):
            self.stack.setCurrentIndex(1)