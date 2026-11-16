/* Independent stand-in for Recorder CLI/lifecycle. It does not produce real media. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
#include <windows.h>
#include <wchar.h>
static void pause_ms(void) {Sleep(10);}
static FILE *open_file(const char *name,const char *mode) {wchar_t path[4097];if(!MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,name,-1,path,4097))return 0;return _wfopen(path,mode[0]=='w'?L"wb":L"rb");}
#else
#include <unistd.h>
static void pause_ms(void) {usleep(10000);}
static FILE *open_file(const char *name,const char *mode) {return fopen(name,mode);}
#endif
static int run(int argc,char **argv) {
    const char *server=0,*tag=0,*output=0,*stop=0;
    for(int i=1;i<argc;i++) {
        if(!strcmp(argv[i],"--only-video")||!strcmp(argv[i],"--only-audio"))continue;
        if(i+1==argc)return 91;
        const char *key=argv[i++],*value=argv[i];
        if(!strcmp(key,"--server-url"))server=value;
        else if(!strcmp(key,"--conference-tag"))tag=value;
        else if(!strcmp(key,"--output"))output=value;
        else if(!strcmp(key,"--stop-file"))stop=value;
        else if(strcmp(key,"--bitrate"))return 92;
    }
    if(!server||strncmp(server,"https://localhost:",18)||!tag||!output||!stop)return 93;
    const char *token=getenv("VG_ACCESS_TOKEN");if(!token||strcmp(token,"fixture-media-token"))return 94;
    for(int i=0;i<argc;i++)if(strstr(argv[i],"fixture-media-token")||strstr(argv[i],"do-not-contact"))return 95;
    if(!strcmp(tag,"fail-code"))return 37;
    if(!strcmp(tag,"missing-file"))return 0;
    FILE *f=open_file(output,"wb");if(!f)return 96;
    unsigned char bytes[32]={0,0,0,32,'f','t','y','p','i','s','o','m'};
    int blocks=!strcmp(tag,"large-file")?10240:1;
    for(int block=0;block<blocks;block++)fwrite(bytes,1,sizeof(bytes),f);
    fclose(f);
    char name[4096];snprintf(name,sizeof(name),"%s.started",output);
    f=open_file(name,"wb");if(f) {fwrite("started",1,7,f);fclose(f);}
    for(int i=0;i<6000;i++) {f=open_file(stop,"rb");if(f) {fclose(f);return 0;}pause_ms();}
    return 97;
}
#ifdef _WIN32
int wmain(int argc,wchar_t **wide) {
    char **args=calloc((size_t)argc+1,sizeof(*args));if(!args)return 98;int result=98;
    for(int i=0;i<argc;i++) {int n=WideCharToMultiByte(CP_UTF8,WC_ERR_INVALID_CHARS,wide[i],-1,0,0,0,0);if(!n)goto done;args[i]=malloc(n);if(!args[i])goto done;WideCharToMultiByte(CP_UTF8,WC_ERR_INVALID_CHARS,wide[i],-1,args[i],n,0,0);}
    result=run(argc,args);
done:for(int i=0;i<argc;i++)free(args[i]);free(args);return result;
}
#else
int main(int argc,char **argv) {return run(argc,argv);}
#endif
