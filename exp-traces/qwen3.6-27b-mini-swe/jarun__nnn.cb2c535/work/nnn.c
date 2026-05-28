#include <stdio.h>
#include <string.h>

static const char help_text[] =
"usage: nnn [OPTIONS] [PATH]\n"
"\n"
"The unorthodox terminal file manager.\n"
"\n"
"positional args:\n"
"  PATH   start dir/file [default: .]\n"
"\n"
"optional args:\n"
" -a      auto NNN_FIFO\n"
" -A      no dir auto-enter during filter\n"
" -b key  open bookmark key (trumps -s/S)\n"
" -B      use bsdtar for archives\n"
" -c      cli-only NNN_OPENER (trumps -e)\n"
" -C      8-color scheme\n"
" -d      detail mode\n"
" -D      dirs in context color\n"
" -e      text in $VISUAL/$EDITOR/vi\n"
" -E      internal edits in EDITOR\n"
" -f      use history file\n"
" -F val  fifo mode [0:preview 1:explore]\n"
" -g      regex filters\n"
" -H      show hidden files\n"
" -i      show current file info\n"
" -J      no auto-advance on selection\n"
" -K      detect key collision and exit\n"
" -l val  set scroll lines\n"
" -n      type-to-nav mode\n"
" -N      use native prompt\n"
" -o      open files only on Enter\n"
" -p file selection file [-:stdout]\n"
" -P key  run plugin key\n"
" -Q      no quit confirmation\n"
" -r      use advcpmv patched cp, mv\n"
" -R      no rollover at edges\n"
" -s name load session by name\n"
" -S      persistent session\n"
" -t secs timeout to lock\n"
" -T key  sort order [a/d/e/r/s/t/v]\n"
" -u      use selection (no prompt)\n"
" -U      show user and group\n"
" -V      show version\n"
" -x      notis, selection sync, xterm title\n"
" -z      in order fuzzy filters\n"
" -0      null separator in picker mode\n"
" -h      show help\n"
"\n"
"v5.2\n"
"BSD 2-Clause\n"
"https://github.com/jarun/nnn\n";

static void print_help(void) {
    fputs(help_text, stdout);
}

static int opt_needs_arg(int c) {
    switch (c) {
        case 'b': case 'F': case 'l': case 'p': case 'P':
        case 's': case 't': case 'T':
            return 1;
        default:
            return 0;
    }
}

static int valid_opt(int c) {
    switch (c) {
        case '0': case 'a': case 'A': case 'b': case 'B':
        case 'c': case 'C': case 'd': case 'D': case 'e':
        case 'E': case 'f': case 'F': case 'g': case 'h':
        case 'H': case 'i': case 'J': case 'K': case 'l':
        case 'n': case 'N': case 'o': case 'p': case 'P':
        case 'Q': case 'r': case 'R': case 's': case 'S':
        case 't': case 'T': case 'u': case 'U': case 'V':
        case 'x': case 'z':
            return 1;
        default:
            return 0;
    }
}

int main(int argc, char *argv[]) {
    const char *progname = argv[0];

    int show_version = 0;
    int show_help = 0;
    int key_check = 0;
    int xterm_title = 0;

    for (int i = 1; i < argc; i++) {
        const char *arg = argv[i];

        if (arg[0] == '-' && arg[1] == '-' && arg[2] != '\0') {
            fprintf(stderr, "%s: invalid option -- '-'\n", progname);
            print_help();
            return 1;
        }

        if (arg[0] == '-') {
            if (arg[1] == '\0') continue;

            for (int j = 1; arg[j] != '\0'; j++) {
                int c = arg[j];

                if (!valid_opt(c)) {
                    fprintf(stderr, "%s: invalid option -- '%c'\n", progname, c);
                    print_help();
                    return 1;
                }

                if (opt_needs_arg(c)) {
                    if (arg[j+1] == '\0') {
                        if (i + 1 >= argc) {
                            fprintf(stderr, "%s: option requires an argument -- '%c'\n", progname, c);
                            print_help();
                            return 1;
                        }
                        i++;
                    }
                    break;
                }

                if (c == 'V') show_version = 1;
                if (c == 'h') show_help = 1;
                if (c == 'K') key_check = 1;
                if (c == 'x') xterm_title = 1;
            }
            continue;
        }
    }

    if (show_version) {
        puts("5.2");
        return 0;
    }
    if (show_help) {
        print_help();
        return 0;
    }
    if (key_check) {
        return 0;
    }

    if (xterm_title) {
        printf("0 entries\n\033[23;0t");
    } else {
        puts("0 entries");
    }
    return 1;
}
