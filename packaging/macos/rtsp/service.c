/* Copyright (c) 2026 Anton Golovkov udattsk@gmail.com
 * Distributed under the Boost Software License, Version 1.0.
 * Operational launcher only: never parses or transports media/configuration.
 */
#define _POSIX_C_SOURCE 200809L
#define _DARWIN_C_SOURCE 1
#include <sys/file.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <poll.h>
#include <signal.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include <inttypes.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define LINE 2048
#define LOG_BYTES (1024 * 1024)
#define LOG_FILES 4
#define STOP_MS 8000
static volatile sig_atomic_t stopping;
static int directory, logfd = -1;
static size_t log_size;
static bool io_failed;
static uint64_t generation, received, sent, last_input, last_output, health_at;
static unsigned last_error;
static bool ready;

static uint64_t clock_ms(void) {
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t)) _exit(70);
    return (uint64_t)t.tv_sec * 1000 + (uint64_t)t.tv_nsec / 1000000;
}
static void on_signal(int signum) { (void)signum; stopping = 1; }
static bool write_all(int fd, const char *p, size_t n) {
    while (n) {
        ssize_t k = write(fd, p, n);
        if (k < 0 && errno == EINTR) continue;
        if (k <= 0) return false;
        p += k; n -= (size_t)k;
    }
    return true;
}
static int create_file(const char *name, int flags) {
    int fd = openat(directory, name, (flags & ~O_TRUNC) | O_NOFOLLOW | O_CLOEXEC | O_NONBLOCK, 0600);
    struct stat st;
    if (fd < 0) return -1;
    if (fstat(fd, &st) || !S_ISREG(st.st_mode) || st.st_nlink != 1 ||
        st.st_uid != geteuid() || (st.st_mode & 077)) { close(fd); return -1; }
    if ((flags & O_TRUNC) && ftruncate(fd, 0)) { close(fd); return -1; }
    return fd;
}
static bool atomic_text(const char *name, const char *text) {
    int fd = create_file(".status.tmp", O_CREAT | O_TRUNC | O_WRONLY);
    if (fd < 0) return false;
    bool ok = write_all(fd, text, strlen(text));
    if (close(fd)) ok = false;
    if (ok && renameat(directory, ".status.tmp", directory, name) == 0) return true;
    unlinkat(directory, ".status.tmp", 0);
    return false;
}
static bool open_log(void) {
    logfd = create_file("service.log", O_CREAT | O_WRONLY | O_APPEND);
    struct stat st;
    if (logfd < 0 || fstat(logfd, &st)) return false;
    log_size = (size_t)st.st_size;
    return true;
}
static void log_line(const char *text) {
    if (io_failed) return;
    char line[LINE + 64];
    int n = snprintf(line, sizeof(line), "%lld %.*s\n", (long long)time(NULL), LINE - 1, text);
    if (n < 0 || (size_t)n >= sizeof(line)) { io_failed = true; return; }
    if (log_size + (size_t)n > LOG_BYTES) {
        close(logfd); logfd = -1;
        if (unlinkat(directory, "service.log.3", 0) && errno != ENOENT) { io_failed = true; return; }
        for (int i = LOG_FILES - 2; i >= 0; --i) {
            char a[40], b[40];
            if (i) snprintf(a, sizeof(a), "service.log.%d", i);
            else snprintf(a, sizeof(a), "service.log");
            snprintf(b, sizeof(b), "service.log.%d", i + 1);
            if (renameat(directory, a, directory, b) && errno != ENOENT) { io_failed = true; return; }
        }
        if (!open_log()) { io_failed = true; return; }
    }
    if (!write_all(logfd, line, (size_t)n)) io_failed = true;
    else log_size += (size_t)n;
}
static void parse_line(const char *line) {
    uint64_t g, a, b, c, d, e;
    int end = 0;
    if (sscanf(line, "RTSP session generation=%" SCNu64 " uptime_ms=%" SCNu64 "%n", &g, &a, &end) == 2 && !line[end]) {
        generation = g; ready = false; health_at = last_input = last_output = 0;
        received = sent = 0;
    }
    unsigned code;
    if (sscanf(line, "RTSP reconnect after error %u", &code) == 1) {
        ready = false; health_at = 0; last_error = code;
    }
    end = 0;
    if (sscanf(line, "LIZA_RTSP_HEALTH ready=%" SCNu64 " received=%" SCNu64 " sent=%" SCNu64
               " input_age_ms=%" SCNu64 " output_age_ms=%" SCNu64 "%n", &a, &b, &c, &d, &e, &end) == 5 && !line[end]) {
        health_at = clock_ms(); ready = a == 1; received = b; sent = c;
        last_input = d <= health_at ? health_at - d : 0;
        last_output = e <= health_at ? health_at - e : 0;
    }
}
static bool status(pid_t child, const char *state, const char *reason, const char *release, int code) {
    uint64_t now = clock_ms();
    char text[1536], input[40] = "null", output[40] = "null";
    if (last_input) snprintf(input, sizeof(input), "%" PRIu64, now - last_input);
    if (last_output) snprintf(output, sizeof(output), "%" PRIu64, now - last_output);
    snprintf(text, sizeof(text),
        "{\"schema\":1,\"state\":\"%s\",\"reason\":\"%s\",\"release\":\"%s\","
        "\"supervisor_pid\":%ld,\"child_pid\":%ld,\"updated_epoch_s\":%lld,"
        "\"generation\":%" PRIu64 ",\"received\":%" PRIu64 ",\"send_accepted\":%" PRIu64 ","
        "\"last_rtp_age_ms\":%s,\"last_send_age_ms\":%s,\"last_reconnect_error\":%u,\"exit_code\":%d}\n",
        state, reason, release, (long)getpid(), (long)child, (long long)time(NULL),
        generation, received, sent, input, output, last_error, code);
    return atomic_text("status.json", text);
}
static void latch(const char *reason) {
    /* Failure to persist (e.g. ENOSPC) still exits successfully, preventing
       launchd restart storms. status CLI treats stale files as unknown. */
    if (!atomic_text("attention", reason)) {
        static const char message[] = "Liza RTSP: cannot persist attention marker; check disk and permissions\n";
        (void)write_all(STDERR_FILENO, message, sizeof(message) - 1);
    }
}
int main(int argc, char **argv) {
    /* argv: executable, config PATH, private state DIRECTORY, release ID */
    if (argc != 5 || !argv[4][0] || strlen(argv[4]) > 96 ||
        strspn(argv[4], "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.") != strlen(argv[4])) return 0;
    umask(077);
    directory = open(argv[3], O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    struct stat st;
    if (directory < 0 || fstat(directory, &st) || st.st_uid != geteuid() || (st.st_mode & 077)) return 0;
    int lock = create_file("service.lock", O_CREAT | O_RDWR);
    if (lock < 0 || flock(lock, LOCK_EX | LOCK_NB)) return 0;
    if (fstatat(directory, "attention", &st, AT_SYMLINK_NOFOLLOW) == 0) {
        (void)status(0, "Attention required", "operator_restart_required", argv[4], 0); return 0;
    }
    if (!open_log() || log_size > LOG_BYTES || !status(0, "Recovering", "starting", argv[4], 0)) {
        latch("storage_or_permissions\n"); return 0;
    }
    int input = open(argv[2], O_RDONLY | O_CLOEXEC | O_NOFOLLOW | O_NONBLOCK);
    bool config_ok = input >= 0 && !fstat(input, &st) && S_ISREG(st.st_mode) && st.st_nlink == 1 &&
        st.st_uid == geteuid() && !(st.st_mode & 077) && st.st_size > 0 && st.st_size <= 4096;
    if (input >= 0) close(input);
    if (!config_ok) {
        latch("configuration_permissions\n"); (void)status(0, "Attention required", "configuration_permissions", argv[4], 2); return 0;
    }
    struct sigaction action; memset(&action, 0, sizeof(action)); action.sa_handler = on_signal;
    sigemptyset(&action.sa_mask); sigaction(SIGTERM, &action, NULL); sigaction(SIGINT, &action, NULL);
    signal(SIGPIPE, SIG_IGN);
    int pipefd[2];
    if (pipe(pipefd)) { latch("pipe_failed\n"); return 0; }
    fcntl(pipefd[0], F_SETFD, FD_CLOEXEC); fcntl(pipefd[1], F_SETFD, FD_CLOEXEC);
    pid_t child = fork();
    if (child == 0) {
        signal(SIGTERM, SIG_DFL); signal(SIGINT, SIG_DFL); signal(SIGPIPE, SIG_DFL);
        /* Remain in launchd's process group so launchd also reaps the child
           if this supervisor is killed. The RTSP application spawns no children. */
        int nullfd = open("/dev/null", O_RDONLY);
        if (nullfd < 0 || dup2(nullfd, STDIN_FILENO) < 0 ||
            dup2(pipefd[1], STDOUT_FILENO) < 0 || dup2(pipefd[1], STDERR_FILENO) < 0) _exit(126);
        close(nullfd); close(pipefd[0]); close(pipefd[1]);
        char *args[] = {argv[1], argv[2], NULL};
        char *env[] = {"PATH=/usr/bin:/bin", "LC_ALL=C", NULL};
        execve(argv[1], args, env); _exit(126);
    }
    close(pipefd[1]);
    if (child < 0) { close(pipefd[0]); latch("spawn_failed\n"); return 0; }
    fcntl(pipefd[0], F_SETFL, O_NONBLOCK);
    char line[LINE]; size_t used = 0; bool oversized = false;
    uint64_t stop_at = 0, report_at = 0; int child_status = 0;
    log_line("service: child started");
    for (;;) {
        uint64_t now = clock_ms();
        if ((stopping || io_failed) && !stop_at) { kill(child, SIGTERM); stop_at = now + STOP_MS; }
        if (stop_at && now >= stop_at) kill(child, SIGKILL);
        struct pollfd p = {pipefd[0], POLLIN, 0}; (void)poll(&p, 1, 100);
        /* Bounded reads ensure log floods cannot starve stop/status handling. */
        char data[8192]; ssize_t n = read(pipefd[0], data, sizeof(data));
        for (ssize_t i = 0; i < n; ++i) {
            if (data[i] == '\n') {
                line[used] = 0;
                if (!oversized) { parse_line(line); log_line(line); }
                else log_line("service: oversized diagnostic line discarded");
                used = 0; oversized = false;
            } else if (!oversized) {
                if (used < LINE - 1 && data[i] != 0) line[used++] = data[i];
                else { used = 0; oversized = true; }
            }
        }
        if (waitpid(child, &child_status, WNOHANG) == child) break;
        if (now >= report_at) {
            bool active = ready && health_at && now - health_at <= 7000 && last_input && last_output &&
                          now - last_input <= 7000 && now - last_output <= 7000;
            if (!status(child, stopping ? "Stopping" : active ? "Running" : "Recovering",
                        stopping ? "stop_requested" : active ? "rtp_and_local_send_active" : "waiting_for_media_or_network",
                        argv[4], 0)) io_failed = true;
            report_at = now + 1000;
        }
    }
    close(pipefd[0]);
    if (io_failed) {
        latch("storage_or_permissions\n");
        (void)status(0, "Attention required", "storage_or_permissions", argv[4], 74); return 0;
    }
    if (stopping) {
        (void)status(0, "Stopped", "operator_stop", argv[4], 0); return 0;
    }
    if (WIFSIGNALED(child_status)) {
        log_line("service: child crashed; launchd may restart");
        (void)status(0, "Recovering", "child_crashed", argv[4], 128 + WTERMSIG(child_status)); return 1;
    }
    int code = WIFEXITED(child_status) ? WEXITSTATUS(child_status) : 70;
    if (code) {
        latch("child_fatal_exit\n"); log_line("service: permanent failure; operator restart required");
        (void)status(0, "Attention required", "child_fatal_exit", argv[4], code); return 0;
    }
    (void)status(0, "Stopped", "application_completed", argv[4], 0); return 0;
}
