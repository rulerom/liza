#include <sys/stat.h>
#include <stdint.h>
#include <errno.h>
#include <unistd.h>
static uint32_t error_code(int e) {
    if(e==ENOENT)return 1;if(e==EACCES||e==EPERM)return 2;
    if(e==EEXIST)return 3;if(e==ENOTDIR)return 4;if(e==EISDIR)return 5;
    if(e==EINVAL||e==ENAMETOOLONG||e==ELOOP)return 6;
    if(e==ENOSPC)return 7;return 8;
}
uint32_t liza_rt_fs_stat(const char *path,uint32_t *kind,uint64_t *size) {
    *kind=0;*size=0;if(!path||!*path)return 6;
    struct stat s;if(lstat(path,&s)) {if(errno==ENOENT)return 0;return error_code(errno);}
    if(S_ISREG(s.st_mode)) {*kind=1;*size=(uint64_t)s.st_size;}
    else if(S_ISDIR(s.st_mode))*kind=2;
    else if(S_ISLNK(s.st_mode))*kind=3;
    else *kind=4;
    return 0;
}
uint32_t liza_rt_fs_op(const char *path,uint32_t op) {
    if(!path||!*path)return 6;
    if(op==1) {
        if(!mkdir(path,0700))return 0;
        int e=errno;
        if(e==EEXIST) {struct stat s;if(!lstat(path,&s)&&S_ISDIR(s.st_mode))return 0;}
        return error_code(e);
    }
    if(op==2) {if(!unlink(path))return 0;return error_code(errno);}
    return 6;
}
#include <string.h>

static uint32_t utf8_path(const uint8_t *p,uint32_t n,char *out) {
    if(!p||!n||n>4096)return 6;
    for(uint32_t i=0;i<n;i++)if(!p[i])return 6;
    if(n)memcpy(out,p,n);out[n]=0;return 0;
}
extern uint32_t liza_rt_file_open_native(const char*,uint64_t*);
extern uint32_t liza_rt_file_create_native(const char*,uint64_t*);
uint32_t liza_rt_fs_utf8_stat(const uint8_t *p,uint32_t n,uint32_t *kind,uint64_t *size) {
    char path[4097];*kind=0;*size=0;uint32_t e=utf8_path(p,n,path);
    return e?e:liza_rt_fs_stat(path,kind,size);
}
uint32_t liza_rt_fs_utf8_op(const uint8_t *p,uint32_t n,uint32_t op) {
    char path[4097];uint32_t e=utf8_path(p,n,path);return e?e:liza_rt_fs_op(path,op);
}
uint32_t liza_rt_fs_utf8_file(const uint8_t *p,uint32_t n,uint32_t create,uint64_t *handle) {
    char path[4097];*handle=0;uint32_t e=utf8_path(p,n,path);
    if(e)return 4;return create?liza_rt_file_create_native(path,handle):liza_rt_file_open_native(path,handle);
}
