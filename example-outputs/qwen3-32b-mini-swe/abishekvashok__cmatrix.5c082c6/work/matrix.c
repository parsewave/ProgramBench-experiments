#include <ncursesw/ncurses.h>
#include <stdlib.h>
#include <unistd.h>
#include <time.h>
#include <getopt.h>
#include <string.h>

#define MAX_COLS 256
#define ALPHA_SIZE 96

int bold = 0;
int color_mode = 0;
char alpha[ALPHA_SIZE] = " !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\]^_`abcdefghijklmnopqrstuvwxyz{|}~";
char katakana[] = "\xa1\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xab\xac\xad\xae\xaf\xb0\xb1\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xbb\xbc\xbd\xbe\xbf\xc0\xc1\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xcb\xcc\xcd\xce\xcf\xd0\xd1\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xdb\xdc\xdd\xde\xdf";
int columns[MAX_COLS];
int len = 0;
int delay = 4;
char colorstr[20] = "green";
int rainbow_mode = 0;
int lambda_mode = 0;
int change_chars = 0;
char message[256] = "";
char *ttyname = "/dev/tty";

void usage() {
    printf("Usage: matrix -[abBcfhlsmVxk] [-u delay] [-C color] [-t tty] [-M message]\n");
    printf("-a: Asynchronous scroll\n");
    printf("-b: Bold characters on\n");
    printf("-B: All bold characters\n");
    printf("-c: Japanese characters\n");
    printf("-f: Force linux TERM\n");
    printf("-l: Linux mode\n");
    printf("-L: Lock mode\n");
    printf("-o: Old-style scroll\n");
    printf("-h: Print help\n");
    printf("-n: No bold\n");
    printf("-s: Screensaver mode\n");
    printf("-x: X mode\n");
    printf("-V: Print version\n");
    printf("-C [color]: Set matrix color\n");
    printf("-u delay (0-10 default 4):\n");
    printf("-t [tty]: Set TTY\n");
    exit(EXIT_FAILURE);
}

void init_colors() {
    if (!has_colors()) {
        endwin();
        printf("Your terminal does not support color\n");
        exit(EXIT_FAILURE);
    }

    start_color();
    init_pair(1, COLOR_GREEN, COLOR_BLACK);
    init_pair(2, COLOR_RED, COLOR_BLACK);
    init_pair(3, COLOR_BLUE, COLOR_BLACK);
    init_pair(4, COLOR_CYAN, COLOR_BLACK);
    init_pair(5, COLOR_MAGENTA, COLOR_BLACK);
    init_pair(6, COLOR_YELLOW, COLOR_BLACK);
    init_pair(7, COLOR_WHITE, COLOR_BLACK);
}

int get_color_id(const char *color) {
    if (strcmp(color, "red") == 0) return 2;
    if (strcmp(color, "blue") == 0) return 3;
    if (strcmp(color, "cyan") == 0) return 4;
    if (strcmp(color, "magenta") == 0) return 5;
    if (strcmp(color, "yellow") == 0) return 6;
    if (strcmp(color, "white") == 0) return 7;
    return 1; // green
}

int main(int argc, char *argv[]) {
    int c;
    int async = 0;
    int oldstyle = 0;
    int lock = 0;
    int force_term = 0;
    int screensaver = 0;
    int xmode = 0;
    int verbose = 0;
    int japanese = 0;

    while (1) {
        int option_index = 0;
        static struct option long_options[] = {
            {"help", 0, 0, 'h'},
            {"version", 0, 0, 'V'},
            {0, 0, 0, 0}
        };

        c = getopt_long(argc, argv, "abBcfhlLmo:hsVxu:C:t:M:",
                        long_options, &option_index);
        if (c == -1) break;

        switch (c) {
            case 'a': async = 1; break;
            case 'b': bold = 1; break;
            case 'B': bold = 1; break;
            case 'c': japanese = 1; break;
            case 'f': force_term = 1; break;
            case 'l': oldstyle = 1; break;
            case 'L': lock = 1; break;
            case 'o': oldstyle = 1; break;
            case 'h': usage();
            case 'n': bold = 0; break;
            case 's': screensaver = 1; break;
            case 'x': xmode = 1; break;
            case 'V": 
                printf("cmatrix version 1.2a\n");
                exit(EXIT_SUCCESS);
            case 'C': 
                strncpy(colorstr, optarg, sizeof(colorstr)-1);
                color_mode = 1;
                break;
            case 'u': delay = atoi(optarg); break;
            case 't': strncpy(ttyname, optarg, sizeof(ttyname)-1); break;
            case 'M': strncpy(message, optarg, sizeof(message)-1); break;
            case 'r': rainbow_mode = 1; break;
            case 'm': lambda_mode = 1; break;
            case 'k': change_chars = 1; break;
            default: usage();
        }
    }

    initscr();
    if (has_colors()) init_pair(1, COLOR_GREEN, COLOR_BLACK);

    cbreak();
    noecho();
    nodelay(stdscr, screensaver);
    curs_set(0);

    int maxx, maxy;
    getmaxyx(stdscr, maxy, maxx);

    if (japanese) {
        memcpy(alpha, katakana, sizeof(katakana));
        ALPHA_SIZE = sizeof(katakana);
    }

    len = maxx;
    for (int i = 0; i < len; i++) {
        columns[i] = 0;
    }

    if (color_mode || rainbow_mode) {
        init_colors();
    }

    if (screensaver) {
        nodelay(stdscr, TRUE);
        clear();
        refresh();
    }

    if (lambda_mode) {
        mvprintw(maxy/2, (maxx - 7)/2, "LAMBDA" );
        refresh();
        sleep(1);
    }

    if (message[0] != '\0') {
        mvprintw(maxy/2, (maxx - strlen(message))/2, message);
        refresh();
        sleep(1);
    }

    int i = 0;
    while (1) {
        getmaxyx(stdscr, maxy, maxx);
        attr_t attrs = 0;
        short pair = 0;

        for (int x = 0; x < maxx; x++) {
            if (rand() % (delay + 2) == 0) {
                columns[x] = 1;
            }

            if (columns[x] > 0) {
                if (columns[x] == 1 || columns[x] == 20) {
                    if (bold) attrs |= A_BOLD;

                    int color = 1;
                    if (color_mode || rainbow_mode) {
                        if (rainbow_mode) {
                            color = (i % 7) + 1;
                        } else {
                            color = get_color_id(colorstr);
                        }
                        attron(COLOR_PAIR(color));
                        if (bold) attron(A_BOLD);
                        else attroff(A_BOLD);
                    }

                    if (columns[x] < 10) {
                        mvaddch(0, x, alpha[rand() % ALPHA_SIZE]);
                    }
                    columns[x]++;
                } else {
                    if (color_mode || rainbow_mode) {
                        attroff(COLOR_PAIR(color));
                    }
                    if (bold) attron(A_BOLD);
                    mvaddch(columns[x] - 1, x, ' ' );
                    attroff(A_BOLD);

                    if (columns[x] < maxy) {
                        if (change_chars) {
                            mvaddch(columns[x], x, alpha[rand() % ALPHA_SIZE]);
                        } else {
                            mvaddch(columns[x], x, alpha[rand() % ALPHA_SIZE]);
                        }
                    }
                    columns[x]++;
                }
            }

            if (columns[x] >= maxy + 20) {
                columns[x] = 0;
            }
        }

        if (screensaver) {
            int ch = getch();
            if (ch != ERR) break;
        }

        refresh();
        usleep(50000 / (delay + 1));
        i++;
    }

    endwin();
    return 0;
}
EOF && gcc /work/matrix.c -o /work/executable -lncurses
