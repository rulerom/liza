#ifndef LIZA_NET_PLATFORM_H
#define LIZA_NET_PLATFORM_H
/* Private blocking TCP and UDP boundary. No application allocation or payload copies. */
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
#endif
