/* Independent executable used by the source-level tests. No shell or IPC pipes. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
#include <windows.h>
#include <wchar.h>
static void pause_ms(void) {Sleep(10);}
#else
#include <unistd.h>
static void pause_ms(void) {usleep(10000);}
#endif
static FILE *open_marker(const char *path) {
#ifdef _WIN32
    wchar_t wide[32768];if(!MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,path,-1,wide,32768))return 0;return _wfopen(wide,L"rb");
#else
    return fopen(path,"rb");
#endif
}
static int run(int argc,char **argv) {
    if(argc<2)return 0;
    if(!strcmp(argv[1],"exit"))return argc>2?atoi(argv[2]):0;
    if(!strcmp(argv[1],"hold")) {for(int i=0;i<6000;i++)pause_ms();return 90;}
    if(!strcmp(argv[1],"marker")) {
        if(argc!=3)return 91;
        for(int i=0;i<6000;i++) {FILE *f=open_marker(argv[2]);if(f) {fclose(f);return 0;}pause_ms();}
        return 92;
    }
    if(!strcmp(argv[1],"arguments")) {
        const char *expected[]={"", "a b", "\"quote\"", "trailing\\", "\\\"", ";$(touch forbidden)","Привет 🚀"};
        if(argc!=9)return 93;
        for(int i=0;i<7;i++)if(strcmp(argv[i+2],expected[i]))return 94;
        const char *token=getenv("LIZA_CHILD_TEST_TOKEN");
        if(!token||strcmp(token,"local-test-only"))return 95;
        return 0;
    }
    return 96;
}

#ifdef _WIN32
int wmain(int argc,wchar_t **wide) {
    char **args=calloc((size_t)argc+1,sizeof(*args));if(!args)return 97;
    int result=97;
    for(int i=0;i<argc;i++) {
        int n=WideCharToMultiByte(CP_UTF8,WC_ERR_INVALID_CHARS,wide[i],-1,0,0,0,0);
        if(!n)goto done;args[i]=malloc((size_t)n);if(!args[i])goto done;
        if(!WideCharToMultiByte(CP_UTF8,WC_ERR_INVALID_CHARS,wide[i],-1,args[i],n,0,0))goto done;
    }
    result=run(argc,args);
done:
    for(int i=0;i<argc;i++)free(args[i]);free(args);return result;
}
#else
int main(int argc,char **argv) {return run(argc,argv);}
#endif
