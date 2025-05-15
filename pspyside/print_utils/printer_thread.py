from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QFont, QFontMetrics
from .device_functions import get_device_list, get_device_id, open_device, draw_image, get_preview_bitmap, print_image, close_device, load_font, draw_text2
from .cffi_defs import ffi, SMART_OPENDEVICE_BYID, PAGE_FRONT, PANELID_COLOR

class PrinterThread(QThread):
    finished = Signal()
    error = Signal(str)
    # preview_ready = Signal(object)  # 미리보기 이미지 전달용
    
    def __init__(self, file_name = None):
        super().__init__()
        self.file_name = file_name
        self.text = "Hello, World!"  # 기본 텍스트 설정
    
    
    def calculate_appropriate_font_width(self, text, max_width=208):
        """
        텍스트가 최대 너비(max_width)를 초과하지 않는 적절한 폰트 너비를 계산합니다.
        최대 너비를 텍스트 길이로 나누고 여유 공간을 위해 4를 더합니다.
        대문자 비율이 높으면 폰트 너비를 줄입니다.
        """
        if not text:
            return 25  # 텍스트가 없는 경우 기본값 반환
        
        if len(text) * 25 < max_width:
            font_width = 25
        else:
            font_width = max(1, int(max_width / len(text)) + 4)
        
        # 대문자 비율 계산
        uppercase_count = sum(1 for c in text if c.isupper())
        uppercase_ratio = uppercase_count / len(text) if text else 0
        
        # 대문자 비율이 50% 이상이면 폰트 너비 조정
        if uppercase_ratio >= 0.5:
            font_width = max(1, font_width - 1)
        
        # 대문자 비율이 80% 이상이면 추가로 폰트 너비 조정
        if uppercase_ratio >= 0.8:
            font_width = max(1, font_width - 1)
        
        return font_width
    
    def run(self):

        try:
            # 장치 목록 조회
            result, printer_list = get_device_list()
            if result != 0:
                self.error.emit("프린터 목록 가져오기 실패")
                return
                
            # 장치 선택
            device_index = 0
            device_id = get_device_id(printer_list, device_index)
            
            # 장치 열기
            result, device_handle = open_device(device_id, SMART_OPENDEVICE_BYID)
            if result != 0:
                self.error.emit("장치 열기 실패")
                return
                
            try:
                # 폰트 정보
                font_name = "Pretendard"
                font_size = 14  # 폰트 크기 고정
                
                # 한 글자당 적절한 폰트 너비 계산
                font_width = self.calculate_appropriate_font_width(self.text)
                
                print(font_width)
                result = draw_text2(device_handle, 
                                    PAGE_FRONT, 
                                    PANELID_COLOR, 
                                    220, 
                                    413, 
                                    208, 
                                    100, 
                                    font_name, 
                                    font_size, 
                                    font_width,  # 글자당 적절한 폰트 너비 전달
                                    0x01, 
                                    0x000000, 
                                    self.text,  # 사용자가 입력한 텍스트 사용
                                    0, 
                                    0x01, 
                                    0
                                    )
                if result != 0:
                    self.error.emit("텍스트 그리기 실패")
                    return
                
                result = draw_text2(device_handle, 
                                    PAGE_FRONT, 
                                    PANELID_COLOR, 
                                    220, 
                                    476, 
                                    208, 
                                    100, 
                                    font_name, 
                                    font_size, 
                                    font_width,  # 글자당 적절한 폰트 너비 전달
                                    0x01, 
                                    0x000000, 
                                    self.text,  # 사용자가 입력한 텍스트 사용
                                    0, 
                                    0x01, 
                                    0
                                    )
                if result != 0:
                    self.error.emit("텍스트 그리기 실패")
                    return
                
                # 이미지 인쇄
                result = print_image(device_handle)
                if result != 0:
                    self.error.emit("이미지 인쇄 실패")
                    return
                    
                self.finished.emit()
            finally:
                # 장치 닫기 (항상 실행)
                close_device(device_handle)
        except Exception as e:
            self.error.emit(f"인쇄 중 오류 발생: {str(e)}")