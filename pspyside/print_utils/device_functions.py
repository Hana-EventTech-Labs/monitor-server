from .cffi_defs import ffi, lib
from pathlib import Path
import ctypes

# 연결된 프린터 목록을 가져오는 함수
def get_device_list():
    # SMART_PRINTER_LIST 구조체 메모리 할당
    printer_list = ffi.new("SMART_PRINTER_LIST *")
    # DLL의 SmartComm_GetDeviceList2 함수를 호출하여 프린터 목록을 채움
    result = lib.SmartComm_GetDeviceList2(printer_list)
    return result, printer_list

# 프린터 리스트에서 특정 인덱스에 해당하는 프린터의 ID를 반환하는 함수
def get_device_id(printer_list, index):
    return printer_list.item[index].id

# 지정한 디바이스 ID를 이용하여 프린터 장치를 열고 핸들을 반환하는 함수
def open_device(device_id, open_device_by):
    # HSMART 핸들용 메모리 할당
    device_handle = ffi.new("HSMART *")
    # DLL의 SmartComm_OpenDevice2 함수를 호출하여 장치를 열고 핸들을 받아옴
    result = lib.SmartComm_OpenDevice2(device_handle, device_id, open_device_by)
    return result, device_handle[0]

# 프린터에 이미지를 출력하기 위한 함수
def draw_image(device_handle, page, panel, x, y, cx, cy, image_filename):
    # Page = 0 : 앞면, 1 : 뒷면
    # panel = 컬러,레진,오버레이 어느 영역에 인쇄할지
    # cx,cy는 px단위, 0인 경우 원래 크기를 사용
    
    # 현재 파일의 경로를 기준으로 resources 폴더 내의 이미지 파일 경로 생성
    image_path = Path(__file__).parent / ".." / "resources" / image_filename
    image_path_str = str(image_path.resolve())
    # wchar_t 배열로 이미지 경로를 변환 (DLL 호출을 위해)
    image = ffi.new("wchar_t[]", image_path_str)
    # 출력 영역 정보 저장을 위한 RECT 구조체 메모리 할당
    rect_area = ffi.new("RECT *")
    # DLL의 SmartComm_DrawImage 함수를 호출하여 지정 영역에 이미지를 그림
    result = lib.SmartComm_DrawImage(device_handle, page, panel, x, y, cx, cy, image, rect_area)
    return result

# 프린터에서 미리보기 비트맵 데이터를 가져오는 함수
def get_preview_bitmap(device_handle, page):
    # BITMAPINFO 구조체에 대한 포인터 메모리 할당
    p_bitmap_info = ffi.new("BITMAPINFO **")
    # DLL의 SmartComm_GetPreviewBitmap 함수를 호출하여 비트맵 정보를 가져옴
    result = lib.SmartComm_GetPreviewBitmap(device_handle, page, p_bitmap_info)
    return result, p_bitmap_info[0]

# 프린터 장치에 인쇄 명령을 보내는 함수
def print_image(device_handle):
    result = lib.SmartComm_Print(device_handle)
    return result

# 열려있는 프린터 장치의 연결을 종료하는 함수
def close_device(device_handle):
    lib.SmartComm_CloseDevice(device_handle)

def get_printer_status(device_handle):
    """
    SmartComm_GetStatus 함수를 호출하여 프린터 상태를 가져오고, 플리퍼 장착 여부를 확인하는 함수
    """
    status = ffi.new("DWORD *")  # DWORD 타입 변수 생성
    result = lib.SmartComm_GetStatus(device_handle, status)

    if result != 0:
        print(f"SmartComm_GetStatus 호출 실패 (오류 코드: {result})")
        return None

    status_value = status[0]

    # 플리퍼 옵션 확인 (상태 값의 특정 비트 확인 필요)
    is_flipper_installed = (status_value & (1 << 3)) != 0  # 예제: 3번째 비트가 플리퍼 상태를 나타낸다고 가정

    return is_flipper_installed

def set_surface_properties(device_handle):
    """
    SMART_SURFACE_PROPERTIES 값을 설정하고 출력하는 함수
    """
    surface_properties = ffi.new("SMART_SURFACE_PROPERTIES *")

    # 인쇄 면 설정 (앞면/뒷면)
    surface_properties.side = 0  # 또는 PAGE_BACK

    # 인쇄 방향 설정 (세로/가로)
    surface_properties.orientation =  1  # 또는 DMORIENT_LANDSCAPE

    # 리본 종류 설정 (테스트 값)
    surface_properties.ribbon = 0  # 예제 값
    surface_properties.ribbon_type = 1  # Standard 리본

    # 인쇄 용지 크기 설정 (예제 값)
    surface_properties.width = 1024
    surface_properties.height = 640

    # 설정된 값 확인
    print("🔹 SMART_SURFACE_PROPERTIES 설정 완료:")
    print(f"  - side: {'앞면' if surface_properties.side == 1 else '뒷면'}")
    print(f"  - orientation: {'세로' if surface_properties.orientation == 1 else '가로'}")
    print(f"  - ribbon: {surface_properties.ribbon}")
    print(f"  - ribbon_type: {'Standard' if surface_properties.ribbon_type == 1 else 'Premium'}")
    print(f"  - width: {surface_properties.width} px")
    print(f"  - height: {surface_properties.height} px")

    return surface_properties

def load_font(font_path):
    """
    지정된 TTF 폰트를 로드하여 사용 가능하게 만드는 함수
    """
    font_path = Path(font_path).resolve()  # 절대 경로 변환
    font_path_wchar = ctypes.c_wchar_p(str(font_path))  # ctypes를 사용하여 문자열 변환

    # Windows API - AddFontResourceEx 사용하여 폰트 등록
    GDI32 = ctypes.windll.gdi32
    FR_PRIVATE = 0x10  # 폰트를 시스템 전체가 아닌 로컬에서만 사용하도록 설정
    num_fonts = GDI32.AddFontResourceExW(font_path_wchar, FR_PRIVATE, None)

    if num_fonts == 0:
        print(f"❌ 폰트 로드 실패: {font_path}")
        return None

    # print(f"✅ 폰트 로드 성공: {font_path}")
    return Path(font_path).stem  # 폰트 파일명(확장자 제외)을 반환

def draw_text(device_handle, page, panel, x, y, font_name, font_size, font_style, text):
    """
    SmartComm_DrawText 함수를 사용하여 특정 위치에 텍스트를 출력하는 함수
    """

    # Unicode 변환
    font_wchar = ffi.new("wchar_t[]", font_name)
    text_wchar = ffi.new("wchar_t[]", text)

    # RECT 영역 (NULL 가능)
    rect_area = ffi.NULL

    # DLL 호출
    result = lib.SmartComm_DrawText(device_handle, page, panel, x, y, font_wchar, font_size, font_style, text_wchar, rect_area)

    if result != 0:
        print(f"❌ 텍스트 그리기 실패 (오류 코드: {result})")
    
    return result

def draw_text2(device_handle, page, panel, x, y, width, height, font_name, font_height, font_width, font_style, font_color, text, rotate=0, align=0, option=0):
    """
    SmartComm_DrawText2를 사용하여 텍스트 출력 (여러 줄 지원)
    """
    # DRAWTEXT2INFO 구조체 생성
    text_info = ffi.new("DRAWTEXT2INFO *")

    # ✅ 텍스트 출력 영역 설정
    text_info.x = x
    text_info.y = y
    text_info.cx = width
    text_info.cy = height  # ✅ 여러 줄을 지원하려면 충분한 높이 설정 필요

    # ✅ 텍스트 옵션 설정
    text_info.rotate = rotate  # 회전각 (0, 90, 180, 270)
    text_info.align = align  # 정렬 방식
    text_info.fontHeight = font_height
    text_info.fontWidth = font_width  # 0이면 자동 조정
    text_info.style = font_style  # (Bold, Italic 등)
    text_info.color = font_color  # 컬러값 (RGB 형식이 아님, COLORREF 사용)
    text_info.option = option  # 0(Nofit) or 4(Auto)

    # ✅ 폰트 이름 설정 (문자열을 리스트로 변환하여 할당)
    font_name_wchar = list(font_name[:31]) + ['\0']  # 최대 31자 + 널 문자
    text_info.szFaceName = font_name_wchar

    # ✅ 여러 줄 텍스트 변환
    text_wchar = ffi.new("wchar_t[]", text.replace("\\n", "\n"))  # 개행 문자 처리

    # ✅ SmartComm_DrawText2 호출
    result = lib.SmartComm_DrawText2(device_handle, page, panel, text_info, text_wchar)

    if result != 0:
        print(f"❌ SmartComm_DrawText2 호출 실패 (오류 코드: {result})")

    return result