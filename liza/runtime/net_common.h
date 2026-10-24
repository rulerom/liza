/* Private blocking TCP boundary. No application allocation or payload copies. */
#include <stdint.h>
#include <limits.h>
#include <string.h>
#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include <winsock2.h>
#include <ws2tcpip.h>
typedef SOCKET net_socket;
#define NET_INVALID INVALID_SOCKET
#define net_os_close closesocket
static int net_start(void) { WSADATA data; return WSAStartup(MAKEWORD(2,2), &data); }
static void net_stop(void) { WSACleanup(); }
static uint32_t net_error(void) {
    switch (WSAGetLastError()) {
    case WSAEADDRINUSE:return 1; case WSAEACCES:return 2;
    case WSAEINTR:return 3; case WSAEWOULDBLOCK:return 4;
    case WSAECONNRESET:case WSAECONNABORTED:case WSAENOTCONN:case WSAESHUTDOWN:return 5;
    default:return 7;
    }
}
#else
#include <errno.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <fcntl.h>
typedef int net_socket;
#define NET_INVALID (-1)
#define net_os_close close
static int net_start(void) { return 0; }
static void net_stop(void) {}
static uint32_t net_error(void) {
    switch (errno) {
    case EADDRINUSE:return 1; case EACCES:case EPERM:return 2;
    case EINTR:return 3; case EAGAIN:return 4;
#if EWOULDBLOCK != EAGAIN
    case EWOULDBLOCK:return 4;
#endif
    case ECONNRESET:case ECONNABORTED:case EPIPE:case ENOTCONN:return 5;
    default:return 7;
    }
}
#endif
static uint64_t net_failure(uint32_t code) { return (uint64_t)code << 32; }
static uint32_t net_prepare(net_socket socket) {
#ifdef _WIN32
    (void)socket;
#else
    if (fcntl(socket,F_SETFD,FD_CLOEXEC)<0) return net_error();
#ifdef SO_NOSIGPIPE
    int yes=1;
    if (setsockopt(socket,SOL_SOCKET,SO_NOSIGPIPE,&yes,sizeof(yes))<0) return net_error();
#endif
#endif
    return 0;
}
uint32_t liza_rt_net_listen(uint16_t port, uint64_t *out) {
    *out=0;
    if (net_start()!=0) return 7;
    net_socket s=socket(AF_INET,SOCK_STREAM,IPPROTO_TCP);
    if (s==NET_INVALID) {uint32_t e=net_error();net_stop();return e;}
    uint32_t error=net_prepare(s);
#ifdef _WIN32
    int yes=1;
    if (!error && setsockopt(s,SOL_SOCKET,SO_EXCLUSIVEADDRUSE,(const char*)&yes,sizeof(yes))!=0) error=net_error();
#endif
    struct sockaddr_in address;
    memset(&address,0,sizeof(address));
    address.sin_family=AF_INET;address.sin_port=htons(port);address.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
    if (!error && bind(s,(struct sockaddr*)&address,sizeof(address))!=0) error=net_error();
    if (!error && listen(s,1)!=0) error=net_error();
    if (error) {net_os_close(s);net_stop();return error;}
    *out=(uint64_t)s;return 0;
}
uint32_t liza_rt_net_accept(uint64_t handle, uint64_t *out) {
    *out=0;
    if (net_start()!=0) return 7;
    net_socket s=accept((net_socket)handle,0,0);
    if (s==NET_INVALID) {uint32_t e=net_error();net_stop();return e;}
    uint32_t error=net_prepare(s);
    if (error) {net_os_close(s);net_stop();return error;}
    *out=(uint64_t)s;return 0;
}
uint64_t liza_rt_net_port(uint64_t handle) {
    struct sockaddr_in address;
#ifdef _WIN32
    int size=sizeof(address);
#else
    socklen_t size=sizeof(address);
#endif
    if (getsockname((net_socket)handle,(struct sockaddr*)&address,&size)!=0) return net_failure(net_error());
    return ntohs(address.sin_port);
}
uint64_t liza_rt_net_read(uint64_t handle, uint8_t *data, uint32_t capacity) {
    if (!capacity) return net_failure(6); /* Zero is reserved for peer EOF. */
    int count=capacity>INT_MAX?INT_MAX:(int)capacity;
#ifdef _WIN32
    int n=recv((net_socket)handle,(char*)data,count,0);
#else
    ssize_t n=recv((net_socket)handle,data,(size_t)count,0);
#endif
    if (n<0) return net_failure(net_error());
    return (uint32_t)n;
}
uint64_t liza_rt_net_write(uint64_t handle, const uint8_t *data, uint32_t length, uint32_t start, uint32_t count) {
    if (start>length || count>length-start) return net_failure(6);
    if (!count) return 0;
    int amount=count>INT_MAX?INT_MAX:(int)count;
#ifdef _WIN32
    int n=send((net_socket)handle,(const char*)data+start,amount,0);
#else
    int flags=0;
#ifdef MSG_NOSIGNAL
    flags=MSG_NOSIGNAL;
#endif
    ssize_t n=send((net_socket)handle,data+start,(size_t)amount,flags);
#endif
    if (n<0) return net_failure(net_error());
    if (!n) return net_failure(5);
    return (uint32_t)n;
}
uint32_t liza_rt_net_close(uint64_t handle) {
    /* Consume once even on error; retrying close may close a reused descriptor. */
    int result=net_os_close((net_socket)handle);
    uint32_t error=result==0?0:net_error();
    net_stop();return error;
}
