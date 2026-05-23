#!/usr/bin/env python3
import sys
import os

USAGE = """ Usage: cmatrix -[abBcfhlsmVxk] [-u delay] [-C color] [-t tty] [-M message]
 -a: Asynchronous scroll
 -b: Bold characters on
 -B: All bold characters (overrides -b)
 -c: Use Japanese characters as seen in the original matrix. Requires appropriate fonts
 -f: Force the linux $TERM type to be on
 -l: Linux mode (uses matrix console font)
 -L: Lock mode (can be closed from another terminal)
 -o: Use old-style scrolling
 -h: Print usage and exit
 -n: No bold characters (overrides -b and -B, default)
 -s: "Screensaver" mode, exits on first keystroke
 -x: X window mode, use if your xterm is using mtx.pcf
 -V: Print version information and exit
 -M [message]: Prints your message in the center of the screen. Overrides -L's default message.
 -u delay (0 - 10, default 4): Screen update delay
 -C [color]: Use this color for matrix (default green)
 -r: rainbow mode
 -m: lambda mode
 -k: Characters change while scrolling. (Works without -o opt.)
 -t [tty]: Set tty to use
"""

VERSION_STR = """ CMatrix version 2.0 (compiled 19:59:42, Apr 17 2026)
Email: abishekvashok@gmail.com
Web: https://github.com/abishekvashok/cmatrix
"""

VALID_COLORS = ["green", "red", "blue", "white", "yellow", "cyan", "magenta", "black"]

def print_usage():
    sys.stdout.write(USAGE)
    sys.exit(0)

def print_version():
    sys.stdout.write(VERSION_STR)
    sys.exit(0)

def invalid_color():
    sys.stderr.write(" Invalid color selection\n Valid colors are green, red, blue, white, yellow, cyan, magenta and black.\n")
    sys.exit(0)

def error_terminal():
    sys.stderr.write("Error opening terminal: unknown.\n")
    sys.exit(1)

def parse_args(argv):
    """Parse arguments. May exit directly for -h, -V, etc."""
    i = 1
    color = 'green'
    color_set = False
    tty = ''
    tty_set = False

    while i < len(argv):
        arg = argv[i]
        if arg == '-h' or arg == '-?':
            print_usage()
        elif arg == '--help':
            print_usage()
        elif arg == '--version':
            print_usage()
        elif arg == '-V':
            print_version()
        elif arg.startswith('-'):
            j = 1
            while j < len(arg):
                c = arg[j]
                if c == 'u':
                    if j + 1 < len(arg):
                        j = len(arg)
                    elif i + 1 < len(argv):
                        i += 1
                        j += 1
                    else:
                        print_usage()
                elif c == 'C':
                    if j + 1 < len(arg):
                        color = arg[j+1:]
                        color_set = True
                        j = len(arg)
                    elif i + 1 < len(argv):
                        i += 1
                        color = argv[i]
                        color_set = True
                        j += 1
                    else:
                        print_usage()
                elif c == 'M':
                    if j + 1 < len(arg):
                        j = len(arg)
                    elif i + 1 < len(argv):
                        i += 1
                        j += 1
                    else:
                        print_usage()
                elif c == 't':
                    if j + 1 < len(arg):
                        tty = arg[j+1:]
                        tty_set = True
                        j = len(arg)
                    elif i + 1 < len(argv):
                        i += 1
                        tty = argv[i]
                        tty_set = True
                        j += 1
                    else:
                        print_usage()
                elif c in 'abBcfhlnosxrmkL':
                    j += 1
                else:
                    print_usage()
            i += 1
        else:
            i += 1

    return color, color_set, tty, tty_set

def main():
    color, color_set, tty, tty_set = parse_args(sys.argv)

    if color_set and color not in VALID_COLORS:
        invalid_color()

    if tty_set:
        if not os.path.exists(tty):
            sys.stderr.write("cmatrix: error: '%s' couldn't be opened: No such file or directory.\n" % tty)
            sys.exit(1)
        # File exists, try to open it
        try:
            f = open(tty, 'r')
            f.close()
        except (OSError, IOError):
            sys.exit(1)
        # If we got here, the tty exists and can be opened
        # The binary exits 1 with no output
        sys.exit(1)

    if not os.isatty(sys.stdout.fileno()):
        error_terminal()

    try:
        import curses
    except ImportError:
        error_terminal()

    error_terminal()

if __name__ == '__main__':
    main()
