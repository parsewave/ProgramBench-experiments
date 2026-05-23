#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <signal.h>
#include <time.h>
#include <fcntl.h>
#include <termios.h>
#include <sys/ioctl.h>
#include <ctype.h>
#include <errno.h>

/* Reimplementation of cmatrix-like terminal effect. */

static int term_rows = 24, term_cols = 80;
static struct termios saved_tio;
static int tio_saved = 0;
static int in_fd = 0;

static void usage(void) {
    printf(" Usage: cmatrix -[abBcfhlsmVxk] [-u delay] [-C color] [-t tty] [-M message]\n");
    printf(" -a: Asynchronous scroll\n");
    printf(" -b: Bold characters on\n");
    printf(" -B: All bold characters (overrides -b)\n");
    printf(" -c: Use Japanese characters as seen in the original matrix. Requires appropriate fonts\n");
    printf(" -f: Force the linux $TERM type to be on\n");
    printf(" -l: Linux mode (uses matrix console font)\n");
    printf(" -L: Lock mode (can be closed from another terminal)\n");
    printf(" -o: Use old-style scrolling\n");
    printf(" -h: Print usage and exit\n");
    printf(" -n: No bold characters (overrides -b and -B, default)\n");
    printf(" -s: \"Screensaver\" mode, exits on first keystroke\n");
    printf(" -x: X window mode, use if your xterm is using mtx.pcf\n");
    printf(" -V: Print version information and exit\n");
    printf(" -M [message]: Prints your message in the center of the screen. Overrides -L's default message.\n");
    printf(" -u delay (0 - 10, default 4): Screen update delay\n");
    printf(" -C [color]: Use this color for matrix (default green)\n");
    printf(" -r: rainbow mode\n");
    printf(" -m: lambda mode\n");
    printf(" -k: Characters change while scrolling. (Works without -o opt.)\n");
    printf(" -t [tty]: Set tty to use\n");
}

static void version(void) {
    printf(" CMatrix version 2.0 (compiled %s, %s)\n", __TIME__, __DATE__);
    printf("Email: abishekvashok@gmail.com\n");
    printf("Web: https://github.com/abishekvashok/cmatrix\n");
}

static void invalid_color(void) {
    printf(" Invalid color selection\n");
    printf(" Valid colors are green, red, blue, white, yellow, cyan, magenta and black.\n");
}

/* Restore terminal on exit */
static void restore_term(void) {
    /* Cursor visible, default colors, clear screen, exit alt screen, reset */
    fputs("\033[?25h", stdout);
    fputs("\033[0m", stdout);
    fputs("\033[2J", stdout);
    fputs("\033[H", stdout);
    fputs("\033[?1049l", stdout);
    fflush(stdout);
    if (tio_saved) {
        tcsetattr(in_fd, TCSANOW, &saved_tio);
    }
}

static volatile sig_atomic_t got_resize = 0;
static volatile sig_atomic_t got_quit = 0;

static void on_winch(int sig) { (void)sig; got_resize = 1; }
static void on_sig(int sig) { (void)sig; got_quit = 1; }

static void update_size(void) {
    struct winsize ws;
    if (ioctl(1, TIOCGWINSZ, &ws) == 0 && ws.ws_row > 0 && ws.ws_col > 0) {
        term_rows = ws.ws_row;
        term_cols = ws.ws_col;
    }
}

/* state per column */
struct col_state {
    int head;     /* row of head (leading char) */
    int tail;     /* row where tail begins (above this stays) */
    int length;   /* trail length */
    int speed;    /* rows per tick */
    int active;
    int gap;      /* gap before next stream */
};

static int color_code = 32; /* green */

static int parse_color(const char *s) {
    if (!strcmp(s, "green")) return 32;
    if (!strcmp(s, "red")) return 31;
    if (!strcmp(s, "blue")) return 34;
    if (!strcmp(s, "white")) return 37;
    if (!strcmp(s, "yellow")) return 33;
    if (!strcmp(s, "cyan")) return 36;
    if (!strcmp(s, "magenta")) return 35;
    if (!strcmp(s, "black")) return 30;
    return -1;
}

static char rand_char(int lambda, int japanese) {
    (void)japanese;
    if (lambda) return 0; /* sentinel: print "λ" */
    /* printable ASCII range used by cmatrix */
    int r = rand() % 94;
    return (char)(33 + r);
}

int main(int argc, char *argv[]) {
    int opt_async = 0;
    int opt_bold = 0;       /* 0=none, 1=random bold, 2=all bold */
    int opt_screensaver = 0;
    int opt_lock = 0;
    int opt_rainbow = 0;
    int opt_lambda = 0;
    int opt_oldstyle = 0;
    int opt_kchange = 0;
    int opt_force_linux = 0;
    int opt_linux = 0;
    int opt_xwindow = 0;
    int opt_japanese = 0;   /* -c */
    int delay_ms = 40;      /* default 4 -> ~40ms */
    char *message = NULL;
    char *tty_path = NULL;

    int i;
    for (i = 1; i < argc; i++) {
        char *a = argv[i];
        if (a[0] != '-' || a[1] == '\0') {
            /* positional argument: ignore */
            continue;
        }
        /* support -? */
        if (!strcmp(a, "-?") || !strcmp(a, "-h")) {
            usage();
            return 0;
        }
        if (!strcmp(a, "-V")) {
            version();
            return 0;
        }
        /* options that take argument */
        if (!strcmp(a, "-u")) {
            if (i + 1 >= argc) { usage(); return 0; }
            int v = atoi(argv[++i]);
            if (v < 0) v = 0;
            if (v > 10) v = 10;
            delay_ms = v * 10;
            continue;
        }
        if (!strcmp(a, "-C")) {
            if (i + 1 >= argc) { usage(); return 0; }
            int c = parse_color(argv[++i]);
            if (c < 0) { invalid_color(); return 0; }
            color_code = c;
            continue;
        }
        if (!strcmp(a, "-t")) {
            if (i + 1 >= argc) { usage(); return 0; }
            tty_path = argv[++i];
            continue;
        }
        if (!strcmp(a, "-M")) {
            if (i + 1 >= argc) { usage(); return 0; }
            message = argv[++i];
            continue;
        }
        /* multi-flag e.g. -ba */
        int unknown = 0;
        for (int j = 1; a[j]; j++) {
            char c = a[j];
            switch (c) {
                case 'a': opt_async = 1; break;
                case 'b': if (opt_bold != 2) opt_bold = 1; break;
                case 'B': opt_bold = 2; break;
                case 'n': opt_bold = 0; break;
                case 's': opt_screensaver = 1; break;
                case 'L': opt_lock = 1; break;
                case 'r': opt_rainbow = 1; break;
                case 'm': opt_lambda = 1; break;
                case 'o': opt_oldstyle = 1; break;
                case 'k': opt_kchange = 1; break;
                case 'f': opt_force_linux = 1; break;
                case 'l': opt_linux = 1; break;
                case 'x': opt_xwindow = 1; break;
                case 'c': opt_japanese = 1; break;
                case 'h': case '?': usage(); return 0;
                case 'V': version(); return 0;
                default:
                    unknown = 1; break;
            }
        }
        if (unknown) { usage(); return 0; }
    }

    /* Mark unused as used to silence warnings */
    (void)opt_force_linux; (void)opt_linux; (void)opt_xwindow;
    (void)opt_japanese; (void)opt_lock; (void)message;
    (void)opt_oldstyle; (void)opt_kchange;

    /* Open tty for input/output */
    int out_fd = 1;
    FILE *outf = stdout;
    if (tty_path) {
        int fd = open(tty_path, O_RDWR);
        if (fd >= 0) {
            in_fd = fd;
            out_fd = fd;
            outf = fdopen(fd, "w");
            if (!outf) outf = stdout;
        }
    }

    /* Verify terminal */
    const char *term = getenv("TERM");
    if (!term || !*term || !strcmp(term, "unknown")) {
        fprintf(stderr, "Error opening terminal: %s.\n", term ? term : "");
        return 1;
    }

    /* Prepare terminal */
    if (tcgetattr(in_fd, &saved_tio) == 0) {
        tio_saved = 1;
        struct termios t = saved_tio;
        t.c_lflag &= ~(ICANON | ECHO);
        t.c_cc[VMIN] = 0;
        t.c_cc[VTIME] = 0;
        tcsetattr(in_fd, TCSANOW, &t);
    }

    update_size();

    signal(SIGWINCH, on_winch);
    signal(SIGINT, on_sig);
    signal(SIGTERM, on_sig);
    signal(SIGHUP, on_sig);
    signal(SIGQUIT, on_sig);

    atexit(restore_term);

    /* Enter alt screen, hide cursor */
    fprintf(outf, "\033[?1049h");
    fprintf(outf, "\033[?25l");
    fprintf(outf, "\033[2J");
    fprintf(outf, "\033[H");
    fflush(outf);

    srand((unsigned)time(NULL) ^ (unsigned)getpid());

    int max_cols = 1024;
    struct col_state *cols = calloc(max_cols, sizeof(struct col_state));
    if (!cols) return 1;

    int first_run = 1;

    while (!got_quit) {
        if (got_resize) {
            update_size();
            got_resize = 0;
            fprintf(outf, "\033[2J\033[H");
            first_run = 1;
        }
        if (term_cols > max_cols) {
            struct col_state *nc = realloc(cols, sizeof(*cols) * term_cols);
            if (nc) { cols = nc; max_cols = term_cols; }
        }
        if (first_run) {
            for (int c = 0; c < term_cols; c++) {
                cols[c].active = 0;
                cols[c].head = -(rand() % term_rows);
                cols[c].length = 5 + rand() % (term_rows / 2 + 1);
                cols[c].speed = opt_async ? (1 + rand() % 3) : 1;
                cols[c].tail = cols[c].head - cols[c].length;
                cols[c].active = 1;
                cols[c].gap = rand() % 20;
            }
            first_run = 0;
        }

        /* Input handling */
        unsigned char ch;
        ssize_t r = read(in_fd, &ch, 1);
        if (r == 1) {
            if (opt_screensaver) break;
            if (ch == 'q' && !opt_lock) break;
            if (ch == 'a') opt_async = !opt_async;
            else if (ch == 'b') opt_bold = 1;
            else if (ch == 'B') opt_bold = 2;
            else if (ch == 'n') opt_bold = 0;
            else if (ch >= '0' && ch <= '9') {
                delay_ms = (ch - '0') * 10;
            } else if (ch == '!') color_code = 31;
            else if (ch == '@') color_code = 32;
            else if (ch == '#') color_code = 33;
            else if (ch == '$') color_code = 34;
            else if (ch == '%') color_code = 35;
            else if (ch == '^') color_code = 36;
            else if (ch == '&') color_code = 37;
            else if (ch == ')') color_code = 30;
        }

        /* Render frame */
        for (int c = 0; c < term_cols; c++) {
            struct col_state *s = &cols[c];
            if (!s->active) {
                if (s->gap > 0) { s->gap--; continue; }
                s->head = 0;
                s->length = 5 + rand() % (term_rows / 2 + 1);
                s->speed = opt_async ? (1 + rand() % 3) : 1;
                s->tail = s->head - s->length;
                s->active = 1;
            }

            for (int sp = 0; sp < s->speed; sp++) {
                /* Erase tail row */
                int tr = s->tail;
                if (tr >= 0 && tr < term_rows) {
                    fprintf(outf, "\033[%d;%dH ", tr + 1, c + 1);
                }
                /* Draw new char at head if within screen */
                int hr = s->head;
                if (hr >= 0 && hr < term_rows) {
                    int color = opt_rainbow ? (31 + rand() % 7) : color_code;
                    int bold = (opt_bold == 2) || (opt_bold == 1 && (rand() & 1));
                    /* head: white bold */
                    fprintf(outf, "\033[%d;%dH\033[1;37m", hr + 1, c + 1);
                    if (opt_lambda) fputs("λ", outf);
                    else fputc(33 + rand() % 94, outf);
                    /* recolor previous head to color */
                    if (hr - 1 >= 0 && hr - 1 < term_rows) {
                        fprintf(outf, "\033[%d;%dH\033[%s%dm", hr, c + 1,
                                bold ? "1;" : "0;", color);
                        if (opt_lambda) fputs("λ", outf);
                        else fputc(33 + rand() % 94, outf);
                    }
                    fprintf(outf, "\033[0m");
                }
                s->head++;
                s->tail++;
                if (s->tail >= term_rows) {
                    s->active = 0;
                    s->gap = rand() % 30;
                    break;
                }
            }
        }

        fflush(outf);

        struct timespec ts;
        ts.tv_sec = delay_ms / 1000;
        ts.tv_nsec = (delay_ms % 1000) * 1000000L;
        if (delay_ms == 0) { ts.tv_sec = 0; ts.tv_nsec = 10000000L; }
        nanosleep(&ts, NULL);
    }

    free(cols);
    return 0;
}
