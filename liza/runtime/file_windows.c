#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <string.h>
#define CAPACITY 2048u
static uint32_t file_error(DWORD e) {
    if (e == ERROR_FILE_NOT_FOUND || e == ERROR_PATH_NOT_FOUND) return 1;
    if (e == ERROR_ACCESS_DENIED || e == ERROR_SHARING_VIOLATION) return 2;
    if (e == ERROR_INVALID_NAME || e == ERROR_INVALID_PARAMETER) return 4;
    if (e == ERROR_FILENAME_EXCED_RANGE) return 5;
    if (e == ERROR_NO_DATA || e == ERROR_PIPE_BUSY) return 6;
    return 7;
}
uint64_t liza_rt_read_file(const uint8_t *path, uint32_t length, uint8_t *out) {
    memset(out, 0, CAPACITY);
    if (length == 0 || memchr(path, 0, length)) return (uint64_t)4 << 32;
    if (length > 4095) return (uint64_t)5 << 32;
    WCHAR name[4096];
    int n = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, (const char *)path,
                               (int)length, name, 4095);
    if (!n) return (uint64_t)4 << 32;
    name[n] = 0;
    HANDLE file = CreateFileW(name, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                              NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    if (file == INVALID_HANDLE_VALUE) return (uint64_t)file_error(GetLastError()) << 32;
    uint32_t count = 0, error = 0;
    for (;;) {
        uint8_t extra; DWORD got = 0;
        BOOL ok = ReadFile(file, count < CAPACITY ? out + count : &extra,
                           count < CAPACITY ? CAPACITY - count : 1, &got, NULL);
        if (!ok) {
            DWORD e = GetLastError();
            if (e != ERROR_HANDLE_EOF) error = file_error(e);
            break;
        }
        if (!got) break;
        if (count == CAPACITY) { error = 3; break; }
        count += got;
    }
    if (!CloseHandle(file) && !error) error = file_error(GetLastError());
    return ((uint64_t)error << 32) | count;
}

uint32_t liza_rt_file_open(const uint8_t *path, uint32_t length, uint64_t *handle) {
    *handle = 0;
    if (length == 0 || memchr(path, 0, length)) return 4;
    if (length > 4095) return 5;
    WCHAR name[4096];
    int n = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, (const char *)path,
                               (int)length, name, 4095);
    if (!n) return 4;
    name[n] = 0;
    HANDLE file = CreateFileW(name, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                              NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    if (file == INVALID_HANDLE_VALUE) return file_error(GetLastError());
    *handle = (uint64_t)(uintptr_t)file;
    return 0;
}
uint32_t liza_rt_file_close(uint64_t handle) {
    return CloseHandle((HANDLE)(uintptr_t)handle) ? 0 : file_error(GetLastError());
}
uint64_t liza_rt_read_chunk(uint64_t handle, uint8_t *out) {
    memset(out, 0, CAPACITY);
    DWORD got = 0;
    if (!ReadFile((HANDLE)(uintptr_t)handle, out, CAPACITY, &got, NULL)) {
        DWORD error = GetLastError();
        if (error == ERROR_HANDLE_EOF) return 0;
        return ((uint64_t)file_error(error) << 32) | got;
    }
    return got;
}

uint32_t liza_rt_file_open_native(const WCHAR *path,uint64_t *handle) {
    *handle=0;
    if(!path || !*path)return 4;
    HANDLE file=CreateFileW(path,GENERIC_READ,FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE,
                            NULL,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,NULL);
    if(file==INVALID_HANDLE_VALUE)return file_error(GetLastError());
    *handle=(uint64_t)(uintptr_t)file;return 0;
}
