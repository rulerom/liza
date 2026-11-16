#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
static uint32_t error_code(DWORD e) {
    if(e==ERROR_FILE_NOT_FOUND||e==ERROR_PATH_NOT_FOUND)return 1;
    if(e==ERROR_ACCESS_DENIED||e==ERROR_SHARING_VIOLATION)return 2;
    if(e==ERROR_ALREADY_EXISTS||e==ERROR_FILE_EXISTS)return 3;
    if(e==ERROR_DIRECTORY)return 4;
    if(e==ERROR_INVALID_NAME||e==ERROR_FILENAME_EXCED_RANGE)return 6;
    if(e==ERROR_DISK_FULL||e==ERROR_HANDLE_DISK_FULL)return 7;return 8;
}
uint32_t liza_rt_fs_stat(const wchar_t *path,uint32_t *kind,uint64_t *size) {
    *kind=0;*size=0;if(!path||!*path)return 6;
    WIN32_FILE_ATTRIBUTE_DATA data;
    if(!GetFileAttributesExW(path,GetFileExInfoStandard,&data)) {
        DWORD e=GetLastError();if(e==ERROR_FILE_NOT_FOUND||e==ERROR_PATH_NOT_FOUND)return 0;
        return error_code(e);
    }
    if(data.dwFileAttributes&FILE_ATTRIBUTE_REPARSE_POINT)*kind=3;
    else if(data.dwFileAttributes&FILE_ATTRIBUTE_DIRECTORY)*kind=2;
    else {*kind=1;*size=((uint64_t)data.nFileSizeHigh<<32)|data.nFileSizeLow;}
    return 0;
}
uint32_t liza_rt_fs_op(const wchar_t *path,uint32_t op) {
    if(!path||!*path)return 6;
    if(op==1) {
        if(CreateDirectoryW(path,0))return 0;DWORD e=GetLastError();
        if(e==ERROR_ALREADY_EXISTS) {DWORD a=GetFileAttributesW(path);if(a!=INVALID_FILE_ATTRIBUTES&&(a&FILE_ATTRIBUTE_DIRECTORY)&&!(a&FILE_ATTRIBUTE_REPARSE_POINT))return 0;}
        return error_code(e);
    }
    if(op==2) {
        DWORD a=GetFileAttributesW(path);if(a!=INVALID_FILE_ATTRIBUTES&&(a&FILE_ATTRIBUTE_DIRECTORY))return 5;
        if(DeleteFileW(path))return 0;return error_code(GetLastError());
    }
    return 6;
}
