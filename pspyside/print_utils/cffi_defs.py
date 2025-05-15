from pathlib import Path
from cffi import FFI

ffi = FFI()

ffi.cdef("""
#define MAX_SMART_PRINTER 32
         
#define SMART_OPENDEVICE_BYID 0
#define SMART_OPENDEVICE_BYDESC 1
         
#define PAGE_FRONT 0
#define PAGE_BACK 1
         
#define PANELID_COLOR 1
#define PANELID_BLACK 2
#define PANELID_OVERLAY 4
#define PANELID_UV 8

typedef void* HSMART;
         
typedef void* RECT;

typedef unsigned int DWORD;
typedef int LONG;
typedef unsigned short WORD;
typedef unsigned char BYTE;

typedef struct {
    wchar_t name[128];
    wchar_t id[64];
    wchar_t dev[64];
    wchar_t desc[256];
    int pid;
} SMART_PRINTER_ITEM;

typedef struct {
    int n;
    SMART_PRINTER_ITEM item[MAX_SMART_PRINTER];
} SMART_PRINTER_LIST;
         
typedef struct tagBITMAPINFOHEADER {
    DWORD biSize;
    LONG biWidth;
    LONG biHeight;
    WORD biPlanes;
    WORD biBitCount;
    DWORD biCompression;
    DWORD biSizeImage;
    LONG biXPelsPerMeter;
    LONG biYPelsPerMeter;
    DWORD biClrUsed;
    DWORD biClrImportant;
} BITMAPINFOHEADER;

typedef struct tagRGBQUAD {
    BYTE rgbBlue;
    BYTE rgbGreen;
    BYTE rgbRed;
    BYTE rgbReserved;
} RGBQUAD;

typedef struct tagBITMAPINFO {
    BITMAPINFOHEADER bmiHeader;
    RGBQUAD bmiColors[1];
} BITMAPINFO;

typedef struct {
    DWORD side;
    DWORD orientation;
    DWORD ribbon;
    DWORD ribbon_type;
    DWORD width;
    DWORD height;
} SMART_SURFACE_PROPERTIES;
         
int SmartComm_GetDeviceList2(SMART_PRINTER_LIST* pDevList);
int SmartComm_OpenDevice2(HSMART* pHandle, wchar_t* szDevice, int nDevType);
int SmartComm_DrawImage(HSMART hHandle, unsigned char page, unsigned char panel,
                        int x, int y, int cx, int cy, wchar_t* szImgPath, RECT* prcArea);
int SmartComm_GetPreviewBitmap(HSMART hHandle, unsigned char page, BITMAPINFO** const ppbi);
int SmartComm_Print(HSMART hHandle);
int SmartComm_CloseDevice(HSMART hHandle);
int SmartComm_GetStatus(HSMART hHandle, DWORD* pStatus);
int SmartComm_DrawText(
    HSMART hHandle, 
    BYTE page, 
    BYTE panel, 
    int x, 
    int y, 
    WCHAR* szFontName, 
    int nFontSize, 
    BYTE nFontStyle, 
    WCHAR* szText, 
    RECT* prcArea
);


typedef struct {
    int x;
    int y;
    int cx;
    int cy;
    int rotate;
    int align;
    int fontHeight;
    int fontWidth;
    int style;
    unsigned long color;
    int option;
    wchar_t szFaceName[32];
} DRAWTEXT2INFO;

int SmartComm_DrawText2(
    HSMART hHandle, 
    BYTE page, 
    BYTE panel, 
    DRAWTEXT2INFO* pdt2info, 
    wchar_t* szText
);

""")

dll_path = Path(__file__).parent / ".." / "resources" / "SmartComm2.dll"
lib = ffi.dlopen(str(dll_path.resolve()))

MAX_SMART_PRINTER = 32
SMART_OPENDEVICE_BYID = 0
SMART_OPENDEVICE_BYDESC = 1
PAGE_FRONT = 0
PAGE_BACK = 1
PANELID_COLOR = 1
PANELID_BLACK = 2
PANELID_OVERLAY = 4
PANELID_UV = 8