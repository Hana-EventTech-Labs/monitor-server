from PySide6.QtWidgets import QWidget, QLabel, QPushButton, QLineEdit, QApplication
from PySide6.QtGui import QPixmap
from PySide6.QtCore import QRect, Qt, QTimer
import requests
import urllib.parse
from print_utils.printer_thread import PrinterThread

class InputScreen(QWidget):
    def __init__(self, stack, screen_size, main_window):
        super().__init__()
        self.stack = stack
        self.screen_size = screen_size
        self.main_window = main_window
        
        # 원본 이미지 크기와 입력 영역 정의
        self.original_image_size = (2736, 1824)
        self.original_input_area = QRect(844, 884, 1889-844, 1129-884)
        
        # 프린터 스레드 관련 변수 초기화
        self.printer_thread = None
        self.is_printing = False
        
        self.setupUI()

    def setupUI(self):
        self.setupBackground()
        self.addCloseButton()
        self.addLineEdit()

    def setupBackground(self):
        pixmap = QPixmap("resources/input.jpg")  # 이미지 로드
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
    
    def get_scaled_input_area(self):
        """원본 이미지 크기를 기준으로 현재 화면 크기에 맞게 입력 영역을 조정"""
        x_ratio = self.screen_size[0] / self.original_image_size[0]
        y_ratio = self.screen_size[1] / self.original_image_size[1]
        
        scaled_x = int(self.original_input_area.x() * x_ratio)
        scaled_y = int(self.original_input_area.y() * y_ratio)
        scaled_width = int(self.original_input_area.width() * x_ratio)
        scaled_height = int(self.original_input_area.height() * y_ratio)
        
        return QRect(scaled_x, scaled_y, scaled_width, scaled_height)
    
    def addLineEdit(self):
        """투명한 입력 필드 추가"""
        input_area = self.get_scaled_input_area()
        
        self.line_edit = QLineEdit(self)
        self.line_edit.setGeometry(input_area)
        self.line_edit.setAlignment(Qt.AlignCenter)  # 텍스트 가운데 정렬
        self.line_edit.setStyleSheet("""
            QLineEdit {
                background-color: transparent;
                border: none;
                color: black;
                font-size: 56px;
            }
        """)
        # 엔터 키 이벤트 연결
        self.line_edit.returnPressed.connect(self.send_text_to_server)
        # 포커스 이벤트 연결
        self.line_edit.mousePressEvent = self.show_virtual_keyboard
        
    def show_virtual_keyboard(self, event):
        """라인에딧 클릭 시 가상 키보드 표시"""
        QLineEdit.mousePressEvent(self.line_edit, event)
        QApplication.inputMethod().show()
        
    def send_text_to_server(self):
        """엔터 키를 누르면 서버에 텍스트 전송하고 프린트"""
        text = self.line_edit.text()
        if text:
            # 가상 키보드 숨기기
            QApplication.inputMethod().hide()
            
            # 서버에 텍스트 전송
            encoded_text = urllib.parse.quote(text)
            url = f"https://port-0-monitor-server-m47pn82w3295ead8.sel4.cloudtype.app/items/add_test/?text={encoded_text}"
            try:
                response = requests.post(url)
                print(f"서버 응답: {response.status_code}")
                
                # 프린트 작업 시작
                self.print_text(text)
                
                self.line_edit.clear()
                self.stack.setCurrentIndex(3)
            except Exception as e:
                print(f"요청 중 오류 발생: {e}")
                
    def print_text(self, text):
        """텍스트를 프린터로 인쇄"""
        # 이미 인쇄 중인 경우 중복 실행 방지
        if self.is_printing:
            print("이미 인쇄 중입니다. 잠시 후 다시 시도하세요.")
            return
            
        self.is_printing = True
        
        # PrinterThread 인스턴스 생성
        self.printer_thread = PrinterThread()
        # PrinterThread 클래스 수정이 필요하면 여기서 텍스트 설정
        self.printer_thread.text = text + "'s"
        
        # 완료 및 에러 시그널 연결
        self.printer_thread.finished.connect(self.on_print_finished)
        self.printer_thread.error.connect(self.on_print_error)
        
        # 스레드 시작
        self.printer_thread.start()
        
    def on_print_finished(self):
        """인쇄 완료 처리"""
        self.is_printing = False
        print("인쇄가 완료되었습니다.")
        
    def on_print_error(self, error_message):
        """인쇄 오류 처리"""
        self.is_printing = False
        print(f"인쇄 오류: {error_message}")