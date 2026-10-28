/* NB1-B only: separate stdin control pipe multiplexed with the UDP socket.
   Do not use as production runtime: Interrupted/WouldBlock encode test commands. */
#include <poll.h>
#include <errno.h>
#include <unistd.h>
#include <stdio.h>
#define liza_rt_net_udp_bind nb1c_original_udp_bind
#define liza_rt_net_udp_receive nb1b_original_udp_receive
#include "../../liza/runtime/net_common.h"
#undef liza_rt_net_udp_receive
#undef liza_rt_net_udp_bind
uint32_t liza_rt_net_udp_bind(uint32_t ip,uint16_t port,uint64_t *out) {
    uint32_t code=nb1c_original_udp_bind(ip,port,out);
    if(!code) {
        int rx=0,tx=0;socklen_t n=sizeof(int);
        if(getsockopt((int)*out,SOL_SOCKET,SO_RCVBUF,&rx,&n) || getsockopt((int)*out,SOL_SOCKET,SO_SNDBUF,&tx,&n)) {
            net_os_close((net_socket)*out);net_stop();*out=0;return 7;
        }
        fprintf(stderr,"socket_rcvbuf=%d\nsocket_sndbuf=%d\n",rx,tx);
    }
    return code;
}
uint32_t liza_rt_net_udp_receive(uint64_t handle,uint8_t *data,uint32_t capacity,uint64_t *out) {
    for (;;) {
        struct pollfd fds[2]={{STDIN_FILENO,POLLIN,0},{(int)handle,POLLIN,0}};
        int rc=poll(fds,2,-1);
        if(rc<0){if(errno==EINTR)continue;return 7;}
        if(fds[0].revents & (POLLIN|POLLHUP|POLLERR)) {
            char c;ssize_t n=read(STDIN_FILENO,&c,1);
            if(n!=1)return 7;
            if(c=='D')return 3;
            if(c=='S')return 4;
            return 7;
        }
        if(fds[1].revents & POLLIN) {
            uint32_t result=nb1b_original_udp_receive(handle,data,capacity,out);
            if(result==3 || result==4)continue;
            return result;
        }
        if(fds[1].revents & (POLLERR|POLLHUP|POLLNVAL))return 7;
    }
}
