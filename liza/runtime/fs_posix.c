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
