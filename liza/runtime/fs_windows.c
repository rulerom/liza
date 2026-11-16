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

static uint32_t utf8_path(const uint8_t *p,uint32_t n,wchar_t *out) {
    if(!p||!n||n>4096)return 6;
    for(uint32_t i=0;i<n;i++)if(!p[i])return 6;
    if(!MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,(const char*)p,(int)n,out,4096))return 6;out[MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,(const char*)p,(int)n,0,0)]=0;return 0;
}
extern uint32_t liza_rt_file_open_native(const wchar_t*,uint64_t*);
extern uint32_t liza_rt_file_create_native(const wchar_t*,uint64_t*);
uint32_t liza_rt_fs_utf8_stat(const uint8_t *p,uint32_t n,uint32_t *kind,uint64_t *size) {
    wchar_t path[4097];*kind=0;*size=0;uint32_t e=utf8_path(p,n,path);
    return e?e:liza_rt_fs_stat(path,kind,size);
}
uint32_t liza_rt_fs_utf8_op(const uint8_t *p,uint32_t n,uint32_t op) {
    wchar_t path[4097];uint32_t e=utf8_path(p,n,path);return e?e:liza_rt_fs_op(path,op);
}
uint32_t liza_rt_fs_utf8_file(const uint8_t *p,uint32_t n,uint32_t create,uint64_t *handle) {
    wchar_t path[4097];*handle=0;uint32_t e=utf8_path(p,n,path);
    if(e)return 4;return create?liza_rt_file_create_native(path,handle):liza_rt_file_open_native(path,handle);
}
