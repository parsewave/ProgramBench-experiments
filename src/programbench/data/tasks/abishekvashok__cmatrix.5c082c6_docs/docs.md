# CMatrix - Terminal Matrix Animation

## Overview

CMatrix is a terminal-based program that simulates the iconic cascading green character streams seen in the 1999 film "The Matrix" and its sequels. The program renders columns of random characters that scroll downward across the terminal screen, creating a visual effect reminiscent of the "digital rain" depicted in the movie franchise. Originally written by Chris Allegretta in 1999, the project was later adopted and maintained by Abishek V Ashok.

CMatrix is built on top of the ncurses library, which provides portable, low-level terminal manipulation capabilities. The program takes control of the entire terminal window, clears the screen, and continuously renders frames of falling characters until the user quits. It supports a wide variety of configuration options including color selection, speed control, character set selection, bold rendering, and screensaver functionality.

The program is designed to be lightweight and efficient, using a simple render-sleep loop that consumes minimal CPU resources at reasonable update speeds. It dynamically adapts to terminal dimensions and handles window resizing gracefully. CMatrix can be used purely for entertainment, as a screensaver, or as a novelty display for terminals and console screens.

CMatrix is written in C and uses the POSIX signal handling API alongside ncurses for its implementation. It compiles on Linux, macOS, and other Unix-like systems with ncurses support. The binary has no runtime dependencies beyond the ncurses shared library.

---

## Options

### -a: Asynchronous Scroll Mode

The `-a` flag enables asynchronous scrolling. In the default synchronous mode, every column of characters updates at the same rate during each frame. This produces a uniform, lockstep scrolling effect where all columns move downward together.

When asynchronous mode is enabled, each column maintains its own independent update counter. On each frame, a column's counter is decremented; the column only updates its display when its counter reaches zero, at which point the counter is reset to a new random value (typically between 1 and 3). This causes different columns to scroll at different speeds, creating a more organic, varied visual effect. Some columns will appear to fall quickly while others lag behind, producing a staggered cascade that more closely resembles the film's visual style.

Asynchronous mode can also be toggled at runtime by pressing the `a` key.

### -b: Bold Characters On (Random Bold)

The `-b` flag enables random bold mode. When active, the "head" character of each falling stream (the bottommost, most recently generated character in each column) is rendered in bold. The remaining characters in the stream (the "tail") are rendered in the normal weight of the selected color.

This creates a visual distinction where the leading edge of each falling column appears brighter and more prominent than the trailing characters. In most terminal emulators, bold text is rendered either with a heavier font weight or with a brighter shade of the selected color (or both), making the head character stand out clearly.

Bold mode can be toggled at runtime by pressing the `b` key.

### -B: All Bold Characters

The `-B` flag enables all-bold mode. Unlike `-b` which only makes the head character bold, `-B` renders every character on the screen in bold. This produces a uniformly bright, high-intensity display where all characters have the same visual weight.

All-bold mode creates a more vivid, saturated appearance. On terminals where bold maps to brighter colors, this effectively makes the entire display use the "bright" variant of the chosen color.

All-bold mode can be toggled at runtime by pressing the `B` key. Pressing `n` at runtime turns off all bold rendering (both `-b` and `-B` modes).

### -c: Japanese Characters (Katakana Mode)

The `-c` flag switches the character set to half-width katakana characters. These are the Japanese characters that are famously associated with the visual style of The Matrix films. When this flag is active, instead of drawing Latin letters and digits, CMatrix draws characters from the Unicode half-width katakana range, approximately U+FF66 to U+FF9D.

The half-width katakana range includes characters such as:

- U+FF66: Wo (ｦ)
- U+FF67: Small A (ｧ)
- U+FF68: Small I (ｨ)
- U+FF69: Small U (ｩ)
- U+FF6A: Small E (ｪ)
- U+FF6B: Small O (ｫ)
- U+FF6C: Small Ya (ｬ)
- U+FF6D: Small Yu (ｭ)
- U+FF6E: Small Yo (ｮ)
- U+FF6F: Small Tsu (ｯ)
- U+FF70: Prolonged Sound Mark (ｰ)
- U+FF71 through U+FF9D: Standard katakana (ｱ through ﾝ)

This mode requires that the terminal emulator supports Unicode rendering and has a font that includes the half-width katakana glyphs. If the terminal lacks Unicode support, characters may render as replacement characters (often displayed as question marks or empty boxes).

### -f: Force Linux Terminal Type

The `-f` flag forces CMatrix to behave as if the `$TERM` environment variable is set to `linux`. This is primarily useful when running CMatrix on the Linux framebuffer console (as opposed to a graphical terminal emulator). The Linux console has different character rendering capabilities compared to xterm-compatible terminals, and this flag ensures CMatrix uses the appropriate rendering path.

When the Linux terminal type is forced, CMatrix may use console-specific character sets and rendering techniques that would not work correctly in a graphical terminal emulator. This flag is generally only needed when the `$TERM` variable is not correctly set for the actual console being used.

### -l: Linux Mode (Console Character Sets)

The `-l` flag enables Linux console mode. This is related to `-f` but specifically activates the use of special console character sets (sometimes called "langstrings" or alternate character set support). On the Linux text console, there are additional characters available through the console's built-in character set tables that are not available in standard terminal emulators.

When Linux mode is enabled, CMatrix can take advantage of these additional characters to create a display that uses console-specific glyphs. This mode is designed for use on actual Linux virtual consoles (tty1 through tty6, for example) and may produce garbled output if used in a graphical terminal emulator like xterm, gnome-terminal, or Konsole.

### -k: Classic Character Set

The `-k` flag selects the "classic" or "original" character set. This character set is a more limited selection of characters that was used in early versions of CMatrix from 1999. It provides a nostalgic rendering that matches the original program's appearance.

The classic character set typically includes a smaller pool of ASCII characters compared to the default set, producing a display with less character variety but matching the original aesthetic of the first CMatrix release.

### -m: Lambda Mode

The `-m` flag enables lambda mode. When active, the Greek letter lambda (λ) is mixed into the active character set. Lambda characters appear randomly among the normal characters in the falling streams, adding visual variety with a mathematical/scientific flavor.

Lambda mode can be combined with any character set (default, Japanese, or classic). The lambda characters are interspersed at random among the other characters in the pool.

Lambda mode can be toggled at runtime by pressing the `m` key.

### -M [message]: Message Display Mode

The `-M` flag accepts a string argument that specifies a custom message to display in the center of the screen. The message is rendered over the matrix animation, appearing as text superimposed on the falling character streams.

The message is positioned at the vertical and horizontal center of the terminal window. It is rendered in a way that makes it visible against the background of scrolling characters. The message remains static while the animation continues around and behind it.

Example usage:

```
cmatrix -M "Welcome to the Matrix"
```

The message display adapts to terminal resizing. If the terminal is resized, the message is repositioned to remain centered. If the message is longer than the terminal width, it may be truncated or wrap depending on the implementation.

### -o: Old-Style Scrolling

The `-o` flag enables old-style scrolling mode. This is a legacy rendering mode that uses a different algorithm for how characters appear and disappear on screen. The exact visual difference is subtle but affects the way new characters are introduced at the top of each column and how existing characters age and eventually disappear.

Old-style scrolling may produce a slightly different visual rhythm compared to the default rendering mode. It exists primarily for backward compatibility with earlier versions of CMatrix.

### -r: Rainbow Mode

The `-r` flag enables rainbow mode. When active, the matrix animation uses multiple colors simultaneously rather than a single uniform color. Each column or character may be rendered in a different color, cycling through all available colors (green, red, blue, yellow, cyan, magenta, white). The effect is a multicolored cascade of characters.

Rainbow mode overrides whatever single color is set via the `-C` flag. When rainbow mode is active, the `-C` color setting is ignored.

Rainbow mode can be toggled at runtime by pressing the `r` key.

### -s: Screensaver Mode

The `-s` flag starts CMatrix in screensaver mode. In this mode, the animation runs normally but the program will exit immediately upon any keypress. This makes CMatrix suitable for use as a terminal screensaver: it runs unattended and disappears as soon as the user touches the keyboard.

In screensaver mode, none of the normal runtime keyboard controls (color changing, bold toggling, speed adjustment, etc.) are functional because any keypress triggers an immediate exit.

### -x: X Window Mode

The `-x` flag enables adjustments for running inside an X Window System terminal emulator. This may affect how CMatrix handles certain terminal capabilities or character rendering that differs between X terminal emulators and the Linux console.

### -u [delay]: Update Delay

The `-u` flag accepts an integer argument from 0 to 10 that controls the speed of the animation. The delay value is used in the main loop to determine how long to pause between frame renders. The actual pause duration is calculated as `napms(delay * 10)` milliseconds.

Delay values and their corresponding frame rates:

| Delay Value | Pause (ms) | Approximate FPS |
|-------------|-----------|-----------------|
| 0           | 0         | Maximum (unlimited) |
| 1           | 10        | ~100 fps |
| 2           | 20        | ~50 fps |
| 3           | 30        | ~33 fps |
| 4 (default) | 40        | ~25 fps |
| 5           | 50        | ~20 fps |
| 6           | 60        | ~17 fps |
| 7           | 70        | ~14 fps |
| 8           | 80        | ~12 fps |
| 9           | 90        | ~11 fps |
| 10          | 100       | ~10 fps |

Note that the actual frame rate will be slightly lower than these theoretical values because the rendering itself takes some time. At delay 0, the frame rate is limited only by the speed of the rendering code and terminal output.

At runtime, pressing the number keys `0` through `9` sets the delay to the corresponding value. Delay 10 can only be set via the command-line flag.

### -C [color]: Set Matrix Color

The `-C` flag accepts a color name string that sets the foreground color of the matrix characters. The valid color names are:

- `green` (default)
- `red`
- `blue`
- `white`
- `yellow`
- `cyan`
- `magenta`
- `black`

Color names are case-sensitive and must be provided in lowercase. If an invalid or unrecognized color name is provided, the program silently falls back to the default green color.

Example usage:

```
cmatrix -C red
cmatrix -C cyan
```

The color applies to all characters on screen (unless rainbow mode is active). The background is always black. On terminals that support `use_default_colors()`, the background may be transparent, allowing the terminal's own background to show through.

### -t [tty]: TTY Output

The `-t` flag accepts a tty device path as its argument. When specified, CMatrix directs its output to the given tty device instead of the current terminal. This allows CMatrix to render on a different terminal or virtual console.

Example usage:

```
cmatrix -t /dev/tty2
```

This would cause CMatrix to display its animation on the second virtual console (tty2) while the program is started from a different terminal. The user would need appropriate permissions to write to the target tty device.

This feature is useful for system administrators who want to display the matrix animation on a specific console, or for creating kiosk-like displays where the output terminal is different from the control terminal.

---

## Character Sets

### Default Character Set

The default character set is the most comprehensive set available in CMatrix. It draws from a pool of ASCII characters that includes:

- **Digits**: 0, 1, 2, 3, 4, 5, 6, 7, 8, 9
- **Uppercase Latin Letters**: A through Z
- **Lowercase Latin Letters**: a through z
- **Select Symbols and Punctuation**: Various ASCII symbols including but not limited to characters like `!`, `@`, `#`, `$`, `%`, `^`, `&`, `*`, and others

Characters are randomly selected from this pool each time a new character needs to be generated (whether for a new head position or for character mutation within the stream). The random selection uses the C standard library `rand()` function.

The default character set provides good visual variety and is universally supported across all terminal emulators since it uses only standard ASCII characters. No special font or Unicode support is required.

### Japanese Mode (-c)

Japanese mode replaces the default character set with half-width katakana characters from the Unicode Basic Multilingual Plane. The half-width katakana occupy the Unicode range from U+FF66 to U+FF9D, providing approximately 56 unique characters.

Half-width katakana are specifically chosen because they closely resemble the characters seen in The Matrix films. The production designers of The Matrix used a combination of half-width katakana, Latin characters, and Arabic numerals (all mirrored) for the "digital rain" effect. CMatrix's Japanese mode uses the katakana subset of these characters.

Half-width katakana differ from their full-width counterparts in that they occupy a single character cell in monospaced fonts, making them suitable for CMatrix's column-based rendering. Full-width katakana would occupy two character cells and break the column alignment.

Terminal requirements for Japanese mode:

- The terminal emulator must support Unicode (UTF-8 encoding)
- The terminal font must include half-width katakana glyphs
- The locale should be set to a UTF-8 locale (e.g., `en_US.UTF-8` or `ja_JP.UTF-8`)

If these requirements are not met, the characters may render as replacement characters (U+FFFD, often displayed as a question mark in a diamond or as an empty box), producing an unreadable display.

### Classic Mode (-k)

The classic character set is a callback to the original 1999 release of CMatrix. It uses a more limited selection of characters than the default set. The classic set was designed when terminal capabilities were more limited and the focus was on creating a simple but effective matrix rain effect.

The classic character set typically emphasizes digits and a smaller subset of letters and symbols. This produces a display that has less character variety but a cleaner, more uniform visual rhythm. Users who prefer the look of the original CMatrix from the late 1990s may prefer this mode.

### Lambda Mode (-m)

Lambda mode is an additive mode that mixes the Greek letter lambda (λ, U+03BB) into whatever base character set is currently active. This means lambda mode can be combined with:

- The default character set (default + λ)
- Japanese mode (`-c -m` produces katakana + λ)
- Classic mode (`-k -m` produces classic characters + λ)

When lambda mode is active, the lambda character is added to the character pool. During random character selection, there is a probability of selecting a lambda instead of a normal character from the base set. This produces a display where lambda characters are scattered throughout the falling streams at random intervals.

Lambda mode can be toggled on and off at runtime by pressing the `m` key, allowing the user to dynamically add or remove lambdas from the display without restarting the program.

---

## Color System

### Available Colors and ncurses Color Pairs

CMatrix uses the ncurses color system for rendering. ncurses provides eight basic colors, each identified by a constant:

| Color Name | ncurses Constant | Typical Appearance |
|-----------|-----------------|-------------------|
| Black     | COLOR_BLACK (0)  | Black (or dark gray) |
| Red       | COLOR_RED (1)    | Red |
| Green     | COLOR_GREEN (2)  | Green |
| Yellow    | COLOR_YELLOW (3) | Yellow (or brown on some terminals) |
| Blue      | COLOR_BLUE (4)   | Blue |
| Magenta   | COLOR_MAGENTA (5)| Magenta/Purple |
| Cyan      | COLOR_CYAN (6)   | Cyan |
| White     | COLOR_WHITE (7)  | White (or light gray) |

CMatrix uses color pairs, which define a foreground/background combination. The primary color pair uses the selected color as the foreground and black (COLOR_BLACK) as the background. When the terminal supports `use_default_colors()`, CMatrix may use -1 as the background color, which means "default" or "transparent." This allows the terminal's own background color or image to show through behind the matrix characters.

Color initialization happens during program startup after ncurses is initialized. CMatrix calls `start_color()` to enable color support and then defines color pairs using `init_pair()`. The exact number of color pairs defined depends on whether rainbow mode is expected to be available.

On terminals that do not support color (monochrome terminals), CMatrix will still function but all characters will be rendered in the terminal's default foreground color. The program checks for color support using `has_colors()` and degrades gracefully if colors are not available.

### Bold and Color Interaction

On many terminal emulators, enabling the bold attribute (via ncurses `A_BOLD`) for a colored character causes the terminal to display the "bright" variant of that color. For example:

- Green + Bold = Bright Green (lime)
- Red + Bold = Bright Red
- Blue + Bold = Bright Blue
- Yellow + Bold = Bright Yellow (true yellow, as opposed to brown/dark yellow)
- White + Bold = Bright White
- Cyan + Bold = Bright Cyan
- Magenta + Bold = Bright Magenta (pink)

This interaction between bold and color is a significant visual element of CMatrix's rendering. In random bold mode (`-b`), the head character of each column appears in bright/bold color while the tail characters appear in the normal (dimmer) color variant, creating a natural gradient effect where the leading edge of each stream is brighter than the trail.

### Rainbow Mode

Rainbow mode disables the single-color rendering and instead cycles through all available colors. The implementation assigns different colors to different columns or characters, creating a multicolored display.

When rainbow mode is active:

1. The single-color setting (from `-C` or runtime color changes) is temporarily overridden
2. Each column or character is assigned a color from the full palette
3. Colors may shift over time as the animation progresses, creating a slowly rotating color effect
4. The overall visual effect is a vibrant, multicolored cascade

Rainbow mode can be enabled at startup with the `-r` flag or toggled at runtime with the `r` key. When rainbow mode is disabled, the display returns to whatever single color was previously active.

### Runtime Color Changing

During program execution, the user can change the matrix color by pressing specific keys. Each key is mapped to a color:

| Key | Color | Mnemonic |
|-----|-------|----------|
| `!` | Red | Shift+1, "hot" |
| `@` | Green | Shift+2, default Matrix color |
| `#` | Yellow | Shift+3, "gold" |
| `$` | Blue | Shift+4, "money blue" |
| `%` | Magenta | Shift+5, "purple" |
| `^` | Cyan | Shift+6 |
| `&` | White | Shift+7 |

These keys are the shifted number keys on a standard US keyboard layout. Pressing any of these keys immediately changes the color of the entire display. The change takes effect on the next frame render, so the transition appears nearly instantaneous.

If rainbow mode is currently active when a color key is pressed, the behavior depends on the implementation. Typically, pressing a specific color key deactivates rainbow mode and switches to the specified single color.

---

## Runtime Keyboard Controls

CMatrix uses ncurses non-blocking input to poll for keystrokes during the main animation loop. The input timeout is set to 0 via `timeout(0)`, meaning `getch()` returns immediately with `ERR` if no key has been pressed. This allows the animation to continue smoothly without waiting for user input.

### Complete Key Binding Reference

| Key | Action | Notes |
|-----|--------|-------|
| `q` | Quit the program | Clean exit with terminal restoration |
| `a` | Toggle asynchronous scroll mode | Switches between sync and async column updates |
| `b` | Toggle random bold mode | Head character rendered in bold |
| `B` | Toggle all-bold mode | All characters rendered in bold |
| `n` | Turn off bold | Disables both `-b` and `-B` bold modes |
| `0` | Set delay to 0 | Maximum speed, no pause between frames |
| `1` | Set delay to 1 | 10ms pause, ~100 fps |
| `2` | Set delay to 2 | 20ms pause, ~50 fps |
| `3` | Set delay to 3 | 30ms pause, ~33 fps |
| `4` | Set delay to 4 | 40ms pause, ~25 fps (default) |
| `5` | Set delay to 5 | 50ms pause, ~20 fps |
| `6` | Set delay to 6 | 60ms pause, ~17 fps |
| `7` | Set delay to 7 | 70ms pause, ~14 fps |
| `8` | Set delay to 8 | 80ms pause, ~12 fps |
| `9` | Set delay to 9 | 90ms pause, ~11 fps |
| `!` | Set color to red | Overrides current color |
| `@` | Set color to green | Overrides current color |
| `#` | Set color to yellow | Overrides current color |
| `$` | Set color to blue | Overrides current color |
| `%` | Set color to magenta | Overrides current color |
| `^` | Set color to cyan | Overrides current color |
| `&` | Set color to white | Overrides current color |
| `r` | Toggle rainbow mode | Cycles through all colors |
| `m` | Toggle lambda mode | Adds/removes lambda characters |
| `p` or `P` | Pause/unpause animation | Freezes/resumes rendering |

### Screensaver Mode Input Behavior

When CMatrix is started with the `-s` (screensaver) flag, the input handling behavior changes completely. Instead of processing individual key bindings, any keypress at all causes the program to exit immediately. This means that pressing `a`, `b`, `q`, or any other key has the same effect: the program terminates.

This behavior is intentional and designed for the screensaver use case, where the user simply wants the animation to stop and the terminal to return to normal as soon as they begin typing.

### Pause Functionality

Pressing `p` or `P` pauses the animation. When paused:

- The screen freezes in its current state
- No new characters are generated or moved
- The program continues to poll for keyboard input
- Pressing `p` or `P` again resumes the animation from where it left off
- Other keys may or may not be processed while paused (implementation-dependent)

Pausing is useful when the user wants to examine the current state of the display or temporarily freeze the animation.

---

## Display Mechanics

### Column-Based Rendering Architecture

CMatrix's rendering is fundamentally organized around columns. The terminal screen is conceptually divided into a series of vertical columns, each column being 2 character cells wide. This means that for a terminal that is 80 columns wide, CMatrix creates 40 virtual columns (80 / 2 = 40).

The 2-character-wide column approach has several effects:

1. **Character spacing**: Characters are separated by one blank column, creating a visual rhythm that prevents the display from looking too dense
2. **Performance**: Fewer columns to update means fewer rendering operations per frame
3. **Aesthetic**: The spacing creates a look that more closely matches the film's visual style, where individual character streams have space between them

The main rendering loop iterates through columns using a step of 2 (i.e., `for (j = 0; j < COLS; j += 2)`), processing each virtual column in turn.

### Column State Data Structures

Each column maintains several pieces of state:

1. **Stream length**: How many characters tall the current falling stream is. This is randomly determined when a new stream starts and may vary between columns.

2. **Head position**: The current vertical position (row number) of the bottommost character in the stream. This advances downward by one row per update cycle (subject to asynchronous timing).

3. **Tail position**: The top of the visible stream. Characters above this position have been "erased" (replaced with blank space). The tail follows the head at a distance determined by the stream length.

4. **Update counter** (asynchronous mode only): A per-column counter that determines when this column should update. The counter is decremented each frame; the column updates only when the counter reaches zero, at which point it is reset to a random value.

5. **Character buffer**: The actual characters currently displayed in each position of the column. These may change over time due to character mutation.

### The Main Render Loop

The main loop of CMatrix follows this general sequence:

```
1. Clear or prepare the frame
2. For each column (j = 0; j < COLS; j += 2):
   a. If in async mode, check the update counter for this column
   b. If the column should update:
      - Advance the head position downward by one row
      - Generate a new random character for the head position
      - Render the head character (possibly in bold/white)
      - If the stream has a tail, erase the topmost tail character
      - Optionally mutate random characters in the stream body
   c. Render the column's current state to the screen buffer
3. If a message is active (-M), render the message at screen center
4. Call refresh() to push the buffer to the terminal
5. Call napms(delay * 10) to pause
6. Poll for keyboard input with getch()
7. Process any keypress (mode toggles, speed changes, quit, etc.)
8. Repeat from step 1
```

### Frame Rendering Details

Each frame render involves writing characters to the ncurses screen buffer using `mvaddch()` or similar functions. The rendering uses these ncurses attributes:

- **A_BOLD**: Applied to characters that should be bold (head character in `-b` mode, all characters in `-B` mode)
- **COLOR_PAIR(n)**: Applied to set the foreground/background color for the character
- **A_NORMAL**: Applied to characters that should not be bold

The rendering process for a single column typically:

1. Writes the new head character at the head position with appropriate attributes (bold, color)
2. Changes the previous head position's character from "head" rendering (white/bold) to "body" rendering (normal color)
3. Erases (writes a space to) the tail position if the stream is long enough
4. Handles the case where the head has scrolled off the bottom of the screen, at which point only tail erasure continues until the stream is fully cleared, then a new stream begins at the top

---

## Character Lifecycle

### Birth: Character Generation

A new character is "born" when it is placed at the head position of a falling column stream. The character is randomly selected from the active character set's pool using `rand()`. The newly generated character is typically rendered with special emphasis:

- In bold mode (`-b`), the head character is rendered with the `A_BOLD` attribute, making it appear brighter than the trailing characters
- The head character may be rendered in white (COLOR_WHITE) regardless of the selected stream color, creating a bright "leading edge" effect that simulates the glowing head seen in the film

The birth of a new character occurs once per column update cycle. In synchronous mode, every column generates a new head character on every frame. In asynchronous mode, each column generates new characters at its own rate.

### Life: Character Display and Mutation

Once a character is placed in the stream, it transitions from the "head" state to a "body" state. The body state uses the selected color (green by default) without bold (unless `-B` all-bold mode is active).

During its lifetime in the stream body, a character may undergo **mutation**. Character mutation is the process where a character that was previously rendered changes to a different character in place, without moving. This creates a subtle flickering effect that adds visual dynamism to the display. Mutation simulates the idea that the "code" in the matrix is constantly changing, not just scrolling.

The mutation probability and frequency vary by implementation. Typically, on each frame, a small number of random positions within each column's visible stream may have their characters replaced with new randomly generated characters. The new character is rendered in the same position with the same attributes as the old one, creating a smooth visual transition.

### Death: Character Erasure

A character "dies" (disappears) when the tail of its stream passes over it. The tail is an invisible eraser that follows the head at a fixed distance determined by the stream's length. When the tail reaches a character's position, that position is overwritten with a space character, effectively erasing it from the display.

The tail advances at the same rate as the head (one row per column update cycle), maintaining a constant stream length. Once the head passes off the bottom edge of the screen, the tail continues to advance and erase until the entire stream has been cleared. After the stream is fully erased, the column either immediately begins a new stream at the top or waits for a random delay before starting a new one.

### Stream Lifecycle

A complete stream lifecycle follows this pattern:

1. **Initialization**: A new stream is created with a randomly determined length. The head starts at row 0 (top of screen) or slightly above.

2. **Growth phase**: The head advances downward, generating new characters. The tail remains at or above the top of the screen, so the visible stream grows longer with each frame.

3. **Steady state**: Once the stream reaches its full length, both the head and tail advance in lockstep. New characters appear at the head while old characters are erased at the tail. The visible length remains constant.

4. **Decay phase**: When the head passes below the bottom row of the screen, no new characters are generated. The tail continues to advance, erasing characters. The visible stream shrinks.

5. **Termination**: When the tail passes below the bottom of the screen, the stream is fully gone. The column may immediately start a new stream or wait for a random delay.

6. **New stream**: A new stream begins at the top of the screen with a new randomly determined length, and the cycle repeats.

---

## Bold Rendering Modes in Detail

### No Bold (Default)

When no bold flags are set (`-b` is not used and `-B` is not used), all characters are rendered with normal weight. This produces a uniform, moderately bright display. The head character is not visually distinguished from the body characters by weight, though it may still be rendered in a different color (white) depending on the implementation.

In no-bold mode, the visual distinction between the head and body of each stream comes primarily from color (if the head is rendered in white) rather than from font weight.

### Random Bold Mode (-b)

Random bold mode creates a two-tier visual hierarchy:

1. **Head character**: Rendered with `A_BOLD | COLOR_PAIR(head_color)`. This makes the leading edge of each stream appear brighter and more prominent.
2. **Body characters**: Rendered with `COLOR_PAIR(body_color)` without bold. These appear in the normal (dimmer) variant of the selected color.

The "random" in "random bold" refers to the fact that the bold attribute follows the randomly positioned head of each stream. As the head moves, the bold attribute moves with it, creating a cascading bright spot that flows down each column.

The visual effect is a clear gradient from bright (head) to dim (tail) within each stream, which is the classic CMatrix look and closely approximates the film's visual style.

### All-Bold Mode (-B)

All-bold mode applies `A_BOLD` to every character rendered on screen. There is no visual distinction between head and body characters based on font weight. The entire display appears uniformly bright.

On most terminal emulators, all-bold mode produces a display that uses the "bright" variant of the selected color for every character. For example, with green selected, all characters appear in bright/lime green rather than the standard green.

All-bold mode is useful when the user wants maximum visual intensity or when the terminal's normal (non-bold) color is too dim to read comfortably.

### Bold Mode Interaction

The three bold states are mutually exclusive in practice:

- Pressing `b` at runtime enables random bold and disables all-bold
- Pressing `B` at runtime enables all-bold and disables random bold
- Pressing `n` at runtime disables both random bold and all-bold

The command-line flags `-b` and `-B` set the initial bold state. If both are specified, the behavior depends on parsing order (typically the last one specified takes precedence).

---

## Message Display Mode (-M)

### Message Rendering

When CMatrix is started with `-M "message text"`, a custom message is displayed at the center of the screen. The message rendering works as follows:

1. **Positioning**: The message is centered both horizontally and vertically on the screen. The vertical center is calculated as `LINES / 2` and the horizontal center is calculated as `(COLS - message_length) / 2`.

2. **Rendering**: The message is drawn on top of the matrix animation. Each character of the message overwrites whatever matrix character would normally appear at that position. The message is typically rendered in a contrasting color or with bold attributes to ensure visibility against the animated background.

3. **Persistence**: The message is re-rendered on every frame, ensuring it remains visible as the matrix animation updates around it. Without re-rendering, the matrix characters would overwrite the message.

4. **Interaction with animation**: The matrix animation continues to run behind the message. Columns that pass through the message area have their characters temporarily replaced by the message characters at the appropriate positions. Characters above and below the message in those columns render normally.

### Message and Terminal Resize

When the terminal is resized (SIGWINCH), the message position is recalculated to keep it centered in the new terminal dimensions. This ensures the message always appears at the visual center regardless of terminal size changes.

### Message Content

The message can be any ASCII string passed as a command-line argument. There are no special formatting codes or escape sequences supported within the message. The message is displayed as-is.

If the message contains spaces, it must be quoted on the command line:

```
cmatrix -M "Hello World"
```

Without quotes, only the first word would be captured as the message argument.

---

## TTY Mode (-t)

### TTY Output Redirection

The `-t` flag allows CMatrix to render its output on a different terminal device than the one from which it was launched. This is accomplished by opening the specified tty device for output and initializing ncurses to use that device.

### Use Cases

1. **Remote console display**: An administrator can start CMatrix on their working terminal but display it on a public-facing console (e.g., a lobby display or kiosk).

2. **Multi-terminal setups**: In environments with multiple physical terminals connected to a single system, CMatrix can be directed to any of them.

3. **Virtual console manipulation**: On Linux systems, CMatrix can be directed to any of the virtual consoles (`/dev/tty1` through `/dev/tty63`).

### Requirements

- The user must have write permissions to the target tty device
- The target terminal must support ncurses operations
- The target terminal's dimensions determine the rendering area (not the launching terminal's dimensions)

### Example

```
sudo cmatrix -t /dev/tty3
```

This starts CMatrix and renders it on virtual console 3. The user would need to switch to tty3 (Ctrl+Alt+F3 on most Linux systems) to see the animation.

---

## Linux Console Mode (-f, -l)

### Linux Console vs. Terminal Emulator

There is a fundamental difference between the Linux text console (the tty you get when no graphical desktop is running, or when you switch to a virtual console with Ctrl+Alt+Fn) and a terminal emulator running inside a graphical desktop (like xterm, GNOME Terminal, or Konsole).

The Linux text console:
- Renders text using the kernel's built-in console driver
- Has its own character set tables (loaded with `setfont`)
- Supports a limited but extensible character set through the console font
- Reports `$TERM` as `linux`
- Has different color handling than xterm-compatible terminals

Terminal emulators:
- Render text using the X11 or Wayland graphical system
- Use TrueType/OpenType fonts with full Unicode support
- Report `$TERM` as `xterm`, `xterm-256color`, or similar
- Support extended color palettes (256 colors, true color)

### -f: Force Linux Terminal Type

The `-f` flag tells CMatrix to treat the current terminal as a Linux console regardless of what `$TERM` reports. This is useful in scenarios where:

- The `$TERM` variable has been incorrectly set
- CMatrix is being piped or redirected in a way that obscures the terminal type
- The user wants to force console-mode behavior in a non-standard terminal environment

When `-f` is active, CMatrix will:
- Use console-specific character set handling
- Assume console-level color capabilities (8 colors)
- Use console-compatible rendering techniques

### -l: Linux Console Character Sets

The `-l` flag activates the use of Linux console-specific character sets. The Linux console supports alternate character set (ACS) characters and can have custom fonts loaded via `setfont`. When `-l` is active, CMatrix may use additional characters from the console font that are not available in standard terminal emulators.

This mode is specifically designed for the Linux framebuffer console and may produce garbled or incorrect output when used in a graphical terminal emulator. The additional characters available depend on the currently loaded console font.

The Linux console mode and the standard terminal emulator mode represent two different rendering paths in CMatrix. The program detects which path to use based on the `$TERM` variable (or the `-f` flag) and adjusts its character selection and rendering accordingly.

---

## Edge Cases and Quirks

### Terminal Width and Column Alignment

Because CMatrix uses 2-character-wide columns (stepping by 2 in the rendering loop), terminals with an odd number of columns will have one unused column on the right edge. This column remains blank and does not participate in the animation. For example, a terminal that is 81 columns wide will have 40 active CMatrix columns using 80 character cells, with the 81st column unused.

### Very Small Terminals

When the terminal is very small (fewer than 4 columns or fewer than 4 rows), CMatrix may not render correctly. The program does not enforce a minimum terminal size, so extremely small terminals may produce garbled output, display no visible animation, or cause rendering artifacts.

### Very Large Terminals

On very large terminals (hundreds of columns and rows), CMatrix's CPU usage increases proportionally because more characters must be generated, rendered, and updated per frame. At high terminal sizes combined with low delay values (fast animation), the CPU usage can become noticeable. The relationship is roughly linear: doubling the terminal area approximately doubles the per-frame rendering cost.

### Resize During Rendering

When the terminal is resized during rendering, CMatrix receives a SIGWINCH signal and must reinitialize its data structures. During this reinitialization:

1. All current column state is discarded
2. New column arrays are allocated for the new terminal dimensions
3. The screen is cleared
4. New streams are initialized with random positions and lengths
5. Rendering resumes with the new dimensions

This means that a terminal resize causes a visible "reset" of the animation. All current streams are lost and new ones begin from scratch. There may be a brief visual glitch or blank frame during the transition.

### Character Encoding Issues

When Japanese mode (`-c`) is used with a terminal that does not support UTF-8 or does not have a font containing half-width katakana glyphs, the display may show:

- Replacement characters (U+FFFD, appearing as `?` in a diamond or box)
- Garbled multi-byte sequences rendered as multiple incorrect characters
- Missing characters (blank spaces where katakana should appear)

The program does not validate that the terminal supports the requested character set before attempting to render it.

### Color on Monochrome Terminals

On terminals that do not support color (where `has_colors()` returns false), CMatrix operates in monochrome mode. All characters are rendered in the terminal's default foreground color. The `-C` flag and runtime color-changing keys have no effect. Rainbow mode is effectively disabled. The animation still works, but without color differentiation.

### Bold on Terminals Without Bold Support

Some terminals do not support bold rendering or implement bold differently. On such terminals:

- Bold may be ignored entirely (no visual difference between bold and normal)
- Bold may be rendered as the same weight but with a brighter color
- Bold may be rendered with a different font (some terminals use a separate bold font)
- Bold may have no effect on some characters but work on others

CMatrix does not check whether bold is supported; it simply sets the `A_BOLD` attribute and relies on the terminal to handle it.

### Delay Value 0 Behavior

Setting the delay to 0 (either via `-u 0` or by pressing `0` at runtime) calls `napms(0)`. The behavior of `napms(0)` is implementation-defined in ncurses. On most systems, it returns immediately without any delay, effectively making CMatrix render at the maximum speed the system can sustain. This can result in:

- Very high CPU usage (one core at or near 100%)
- Extremely fast, potentially hard-to-read animation
- Frames rendering as fast as the terminal can accept output

On some systems, `napms(0)` may impose a minimum delay (such as 1ms), slightly limiting the maximum speed.

### Signal Race Conditions

CMatrix registers signal handlers for SIGINT, SIGWINCH, and SIGTERM. In rare cases, a signal may arrive during a critical section of the rendering code (such as during memory allocation for a resize). Most implementations handle this by setting a flag in the signal handler and checking the flag in the main loop, rather than performing complex operations directly in the signal handler.

### Multiple Instance Conflicts

Running multiple instances of CMatrix on the same terminal (e.g., in different tmux panes that share the same underlying tty) can cause display corruption. Each instance will write to the same terminal device independently, with their ncurses buffers conflicting. This is not specific to CMatrix but is a general limitation of ncurses-based applications.

### Pipe and Redirect Behavior

CMatrix is designed for interactive terminal use and does not produce meaningful output when its stdout is piped to another program or redirected to a file. ncurses requires a real terminal (or at least something that responds to terminal queries) and will fail or produce garbage when stdout is not a tty.

---

## Comparison with the Movie's Visual Style

### The Film's "Digital Rain"

In The Matrix films (1999, 2003), the "digital rain" or "Matrix code" is a visual representation of the Matrix's underlying code. The production design used the following elements:

1. **Character set**: A mix of half-width katakana, Latin letters, Arabic numerals, and other symbols, all horizontally mirrored (reversed). The mirroring was done intentionally to create an alien, unfamiliar look.

2. **Color**: Predominantly green on a black background, with varying shades of green creating depth. The brightest characters appear at the leading edge of each stream, with trailing characters fading to darker green.

3. **Motion**: Characters cascade vertically from top to bottom at varying speeds. Different streams move at different rates, creating a parallax-like depth effect.

4. **Character mutation**: Characters change randomly even within a static position, creating a constant visual flux that suggests active computation.

5. **Density**: The film's effect is quite dense, with minimal spacing between columns.

6. **Depth layers**: The film uses multiple layers of cascading characters at different sizes and speeds to create a three-dimensional effect.

### How CMatrix Approximates the Film

CMatrix captures the essence of the film's effect within the constraints of a text terminal:

1. **Character set**: The `-c` flag provides half-width katakana, the most recognizable characters from the film. However, CMatrix does not mirror the characters as the film does.

2. **Color**: CMatrix defaults to green on black, matching the film. The bold head character creates a brightness gradient similar to the film's bright-to-dim stream effect.

3. **Motion**: CMatrix's asynchronous mode (`-a`) approximates the film's varied scroll speeds. In synchronous mode, all columns move at the same rate, which is less visually similar to the film.

4. **Character mutation**: CMatrix implements character mutation where characters change in place, matching the film's visual flux.

5. **Density**: CMatrix uses 2-character-wide columns with 1 character of spacing, creating a somewhat sparser display than the film. This is a necessary compromise for readability in a text terminal.

6. **Depth**: CMatrix cannot create true 3D depth effects within a text terminal. All characters are the same size and on the same plane. The varying stream speeds in async mode provide a limited sense of depth through motion parallax.

### Differences from the Film

Several aspects of the film's effect cannot be reproduced in a text terminal:

- **Mirrored characters**: CMatrix displays characters in their normal orientation, not mirrored
- **Smooth motion**: Terminal rendering is cell-based, so characters jump from one row to the next. The film uses smooth, sub-pixel animation.
- **Variable font sizes**: The film uses characters at different scales to create depth. CMatrix is limited to the terminal's fixed character size.
- **Glow effects**: The film's characters have a soft glow/bloom effect. Terminal characters have hard edges.
- **True color gradients**: The film uses continuous green gradients. CMatrix can only use the 8 basic colors (or 256 colors on supported terminals, though CMatrix uses the basic 8).
- **3D depth**: The film's code appears to recede into the distance. CMatrix is strictly 2D.

---

## Terminal Compatibility Notes

### Supported Terminal Emulators

CMatrix works with any terminal emulator that supports ncurses. This includes virtually all modern terminal emulators:

- **xterm**: Full support including color and Unicode (for Japanese mode)
- **GNOME Terminal (VTE-based)**: Full support. Bold typically renders as bright colors.
- **Konsole (KDE)**: Full support. Bold may render as both heavy weight and bright color.
- **iTerm2 (macOS)**: Full support. Excellent Unicode rendering for Japanese mode.
- **Terminal.app (macOS)**: Full support, though color rendering may differ slightly from Linux terminals.
- **Alacritty**: Full support. GPU-accelerated rendering handles CMatrix's rapid updates efficiently.
- **kitty**: Full support. Kitty's protocol extensions are not used; CMatrix relies on standard ncurses.
- **tmux/screen**: CMatrix works inside multiplexers but the `$TERM` variable should be set correctly (e.g., `screen-256color` or `tmux-256color`).
- **Windows Terminal (with WSL)**: Full support when running inside WSL.
- **PuTTY**: Supported but Unicode rendering may require font configuration for Japanese mode.
- **Linux framebuffer console**: Supported, especially with `-f` and `-l` flags.

### TERM Variable Requirements

CMatrix relies on the `$TERM` environment variable to determine terminal capabilities. Common values and their effects:

| TERM Value | Color Support | Unicode | Bold | Notes |
|-----------|--------------|---------|------|-------|
| xterm | 8 colors | Yes | Yes | Basic xterm |
| xterm-256color | 256 colors | Yes | Yes | Most common modern value |
| linux | 8 colors | Limited | Yes | Linux console |
| vt100 | No color | No | Limited | Very basic terminal |
| dumb | Nothing | No | No | Minimal terminal, CMatrix may not work |
| screen | 8 colors | Varies | Yes | Inside screen/tmux |
| tmux-256color | 256 colors | Yes | Yes | Inside tmux |

CMatrix primarily uses the basic 8 colors, so 256-color or true-color support is not required for full functionality. However, the terminal must support at least basic color for the colored display to work.

### Locale and Character Encoding

For Japanese mode (`-c`), the system locale must be configured for UTF-8 encoding. The relevant environment variables are:

- `LANG` (e.g., `en_US.UTF-8`)
- `LC_ALL` (overrides all other locale settings)
- `LC_CTYPE` (character encoding specifically)

If the locale is set to a non-UTF-8 encoding (such as `C`, `POSIX`, or a Latin-1 locale), ncurses may not correctly handle the multi-byte katakana characters, resulting in display corruption.

To check the current locale:

```
locale
```

To temporarily set a UTF-8 locale for CMatrix:

```
LC_ALL=en_US.UTF-8 cmatrix -c
```

### Font Requirements

For the default and classic character sets, any monospaced font that includes ASCII characters will work. This includes virtually every terminal font.

For Japanese mode, the terminal font must include half-width katakana glyphs (U+FF66-U+FF9D). Most modern Unicode fonts include these characters, but some older or minimal fonts may not. Recommended fonts for Japanese mode:

- Noto Sans Mono (Google)
- DejaVu Sans Mono
- Hack
- Source Code Pro
- JetBrains Mono
- Any CJK-capable monospaced font

If the font lacks the required glyphs, the terminal's fallback font mechanism may supply them from a different font. If no fallback is available, the characters will render as replacement glyphs.

### SSH and Remote Sessions

CMatrix works over SSH connections, but several factors affect the experience:

1. **Latency**: The rapid screen updates of CMatrix can be noticeably laggy over high-latency connections. The terminal output is transmitted as a stream of ncurses escape sequences, and each frame generates significant output.

2. **Bandwidth**: At high speeds (low delay values), CMatrix can generate substantial terminal output. On low-bandwidth connections, this can cause buffer overflows, display lag, or dropped frames.

3. **TERM forwarding**: SSH forwards the `$TERM` variable from the local machine. If the remote system does not have the corresponding terminfo entry, CMatrix may fail or render incorrectly. Using `TERM=xterm-256color` is generally safe.

4. **Unicode over SSH**: Japanese mode works over SSH as long as both the local terminal and the SSH connection handle UTF-8 correctly. This usually "just works" on modern systems.

### Terminal Multiplexers (tmux, screen)

CMatrix works inside tmux and screen, but there are some considerations:

1. **Window resize**: When a tmux pane is resized, tmux sends SIGWINCH to the program. CMatrix handles this signal and reinitializes.

2. **Color support**: Ensure the multiplexer's TERM variable supports colors. `screen-256color` or `tmux-256color` are recommended.

3. **Unicode passthrough**: tmux and screen may need configuration to pass through UTF-8 characters correctly for Japanese mode. In tmux, ensure `set -g default-terminal "tmux-256color"` is in the config.

4. **Key binding conflicts**: Some key bindings used by CMatrix may conflict with tmux or screen key bindings. For example, the prefix key in tmux (often Ctrl+B) is not a CMatrix key, but other keys might conflict if custom bindings are configured.

---

## Detailed Rendering Algorithm

### Initialization Phase

When CMatrix starts, the following initialization sequence occurs:

1. **Parse command-line arguments**: All flags and arguments are processed using getopt(). Invalid flags are silently ignored or cause a usage message to be displayed.

2. **Initialize ncurses**:
   ```c
   initscr();      // Initialize the ncurses library and terminal
   cbreak();       // Disable line buffering, pass keys immediately
   noecho();       // Don't echo typed characters to the screen
   keypad(stdscr, TRUE);  // Enable function key interpretation
   curs_set(0);    // Hide the cursor
   timeout(0);     // Non-blocking input mode
   ```

3. **Initialize colors**:
   ```c
   start_color();                    // Enable color support
   use_default_colors();             // Enable transparent background
   init_pair(1, selected_color, -1); // Define the primary color pair
   // Additional pairs for rainbow mode, head character, etc.
   ```

4. **Allocate data structures**:
   - Allocate arrays for column state (head positions, tail positions, stream lengths)
   - Allocate the update counter array for asynchronous mode
   - Initialize each column with random starting values

5. **Seed the random number generator**:
   ```c
   srand(time(NULL));
   ```

6. **Register signal handlers**:
   ```c
   signal(SIGINT, signal_handler);
   signal(SIGWINCH, resize_handler);
   signal(SIGTERM, signal_handler);
   ```

7. **Clear the screen and begin the main loop**

### Per-Frame Rendering

Each frame of the animation follows a specific rendering pipeline:

#### Step 1: Column Iteration

The rendering loop iterates over each column from left to right:

```c
for (j = 0; j < COLS; j += 2) {
    // Process column j
}
```

The step of 2 means that CMatrix processes every other terminal column, creating the characteristic spacing between character streams.

#### Step 2: Asynchronous Check

If asynchronous mode is active, each column has an update counter that is decremented each frame. The column is only updated when its counter reaches zero:

```c
if (async_mode) {
    updates[j]--;
    if (updates[j] > 0) continue;  // Skip this column this frame
    updates[j] = rand() % 3 + 1;   // Reset counter to 1, 2, or 3
}
```

This means in asynchronous mode, each column updates every 1 to 3 frames, creating the staggered scrolling effect.

#### Step 3: Head Advancement

The head position of the column's stream advances downward by one row:

```c
head[j]++;
```

#### Step 4: New Character Generation

A new character is randomly selected from the active character set and placed at the head position:

```c
new_char = charset[rand() % charset_length];
```

The character is rendered with head-specific attributes:

```c
attron(COLOR_PAIR(head_color) | A_BOLD);
mvaddch(head[j], j, new_char);
attroff(COLOR_PAIR(head_color) | A_BOLD);
```

#### Step 5: Previous Head Update

The character that was at the previous head position (one row above the current head) transitions from "head" rendering to "body" rendering:

```c
attron(COLOR_PAIR(body_color));
mvaddch(head[j] - 1, j, existing_char);
attroff(COLOR_PAIR(body_color));
```

In random bold mode, this step removes the bold attribute from the character. The character remains on screen but changes from bright/bold to normal/dim.

#### Step 6: Tail Erasure

If the stream has reached its full length, the tail position also advances, and the character at the tail is erased:

```c
if (head[j] - tail[j] >= stream_length[j]) {
    mvaddch(tail[j], j, ' ');
    tail[j]++;
}
```

#### Step 7: Character Mutation (Optional)

At random intervals, characters within the body of the stream are replaced with new random characters. This creates the flickering effect:

```c
if (rand() % MUTATION_RATE == 0) {
    int mutate_row = tail[j] + rand() % (head[j] - tail[j]);
    new_char = charset[rand() % charset_length];
    mvaddch(mutate_row, j, new_char);
}
```

#### Step 8: End-of-Screen Handling

When the head passes below the last visible row, the column enters its decay phase:

```c
if (head[j] >= LINES) {
    // Don't generate new characters, just continue erasing the tail
    // When the tail also passes below the last row, reset the column
    if (tail[j] >= LINES) {
        // Reset column: new stream at top with new random length
        head[j] = 0;
        tail[j] = 0;
        stream_length[j] = rand() % (LINES - 3) + 3;
    }
}
```

#### Step 9: Screen Refresh

After all columns have been processed, the screen buffer is flushed to the terminal:

```c
refresh();
```

#### Step 10: Delay

The program pauses for the configured delay:

```c
napms(update * 10);
```

#### Step 11: Input Processing

The program checks for keyboard input:

```c
int ch = getch();
if (ch != ERR) {
    // Process the key
}
```

### Stream Length Determination

When a new stream is created for a column, its length is randomly determined. The length is typically bounded by the terminal height:

- Minimum length: 3 characters (to ensure the stream is visible)
- Maximum length: `LINES - 3` (to ensure the stream doesn't fill the entire screen and create a static block)

The random distribution of stream lengths creates visual variety: some columns have short, quick streams while others have long, flowing streams.

### Head Character Rendering

The head character of each stream receives special rendering treatment. There are typically two visual strategies for the head:

1. **White head**: The head character is rendered in white (COLOR_WHITE) regardless of the selected stream color. This creates a bright "hot spot" at the leading edge that stands out against the colored body.

2. **Bold head**: The head character is rendered in the selected color but with the bold attribute, making it brighter than the body characters. This is the rendering used in `-b` mode.

Some implementations combine both strategies, rendering the head in bold white for maximum contrast.

### Body Character Rendering

Body characters (everything between the head and tail) are rendered in the selected color with attributes determined by the bold mode:

- No bold: Normal weight, selected color
- Random bold (`-b`): Normal weight, selected color (only head is bold)
- All bold (`-B`): Bold weight, selected color

Body characters may undergo mutation at random intervals, where they are replaced with new characters without changing position or attributes.

---

## Signal Handling

### SIGINT (Interrupt, Ctrl+C)

When the user presses Ctrl+C, CMatrix receives SIGINT. The signal handler performs a clean shutdown:

1. Calls `curs_set(1)` to restore cursor visibility
2. Calls `endwin()` to restore the terminal to its pre-ncurses state
3. Exits with code 0

This ensures the terminal is left in a usable state. Without proper SIGINT handling, the terminal could be left with echo disabled, cursor hidden, and in raw input mode.

### SIGWINCH (Window Resize)

When the terminal window is resized, the operating system sends SIGWINCH to the foreground process. CMatrix's SIGWINCH handler:

1. Calls `endwin()` to end the current ncurses session
2. Calls `initscr()` (or `refresh()`) to reinitialize ncurses with the new dimensions
3. Reads the new `LINES` and `COLS` values
4. Frees the old column state arrays
5. Allocates new arrays sized for the new dimensions
6. Reinitializes all column state (random stream lengths, positions, etc.)
7. Clears the screen
8. Resumes the main loop

The resize operation causes a visible reset of the animation. All current streams are lost and new ones begin from scratch in the resized window.

### SIGTERM (Terminate)

SIGTERM is handled similarly to SIGINT: the signal handler performs a clean shutdown by restoring the terminal and exiting. SIGTERM is the standard termination signal sent by `kill` and system shutdown procedures.

---

## Terminal Management

### ncurses Initialization

CMatrix uses a specific sequence of ncurses calls to set up the terminal for animation:

1. **initscr()**: Initializes the ncurses library, allocates memory for the screen data structures, and determines the terminal type from `$TERM`.

2. **cbreak()**: Disables the terminal's line buffering. In normal terminal operation, input is buffered until the user presses Enter. With cbreak, each keypress is available immediately, which is essential for CMatrix's runtime controls.

3. **noecho()**: Prevents typed characters from being echoed to the screen. Without this, pressing keys during the animation would cause characters to appear on screen, disrupting the display.

4. **keypad(stdscr, TRUE)**: Enables the interpretation of function keys (F1, arrow keys, etc.) as single values rather than escape sequences. While CMatrix doesn't use function keys, this is a standard initialization step.

5. **curs_set(0)**: Hides the terminal cursor. The blinking cursor would be distracting during the animation.

6. **timeout(0)**: Sets input to non-blocking mode. `getch()` returns immediately with `ERR` if no key has been pressed, allowing the animation to continue without waiting for input.

### Terminal Restoration

On exit (whether by pressing `q`, receiving a signal, or screensaver mode exit), CMatrix restores the terminal:

1. **curs_set(1)**: Restores cursor visibility
2. **endwin()**: Restores the terminal to its state before `initscr()` was called. This re-enables echo, disables cbreak, and restores the terminal's original attributes.

If CMatrix crashes or is killed with SIGKILL (which cannot be caught), the terminal may be left in an inconsistent state. In this case, the user can restore the terminal by running `reset` or `stty sane`.

### Screen Buffer Management

ncurses maintains a virtual screen buffer that represents the desired state of the terminal. CMatrix writes to this buffer using functions like `mvaddch()`, `attron()`, and `attroff()`. The actual terminal is only updated when `refresh()` is called, which computes the minimal set of terminal output needed to transform the current physical screen into the desired virtual screen.

This buffered approach is essential for CMatrix's performance. Without it, each character write would generate immediate terminal output, resulting in visible flickering and much higher bandwidth usage.

---

## Exit Behavior

### Normal Exit

A normal exit occurs when:

- The user presses `q`
- The user presses any key in screensaver mode (`-s`)
- The program receives SIGINT (Ctrl+C) or SIGTERM

In all normal exit cases:

1. The terminal is restored to its pre-CMatrix state via `endwin()`
2. The cursor is made visible again
3. Dynamic memory is freed
4. The program exits with exit code 0

### Abnormal Exit

An abnormal exit can occur if:

- CMatrix receives SIGKILL (which cannot be caught)
- CMatrix crashes due to a bug
- The system runs out of memory

In abnormal exit cases, the terminal may be left in an inconsistent state. The user can recover by:

```
reset          # Full terminal reset
stty sane      # Restore sane terminal settings
tput cnorm     # Make cursor visible
```

---

## Error Handling

### Invalid Color Names

If an unrecognized color name is passed to `-C`, CMatrix does not produce an error message. Instead, it silently falls back to the default green color. This means that:

```
cmatrix -C purple   # "purple" is not recognized, defaults to green
cmatrix -C green    # Recognized, uses green
cmatrix -C RED      # Case-sensitive, "RED" may not be recognized
```

Valid color names are lowercase: `green`, `red`, `blue`, `white`, `yellow`, `cyan`, `magenta`, `black`.

### Invalid Delay Values

The `-u` flag expects an integer between 0 and 10. Behavior with out-of-range values:

- Negative values: Implementation-defined, may cause unexpected behavior or be treated as unsigned
- Values greater than 10: May cause very slow animation or be truncated
- Non-numeric values: The argument parsing may produce undefined results

### Terminal Capability Errors

If the terminal does not support required capabilities:

- **No color support**: CMatrix runs in monochrome mode without explicit warning
- **No ncurses support**: CMatrix fails to start (initscr() fails)
- **Terminal too small**: CMatrix may render incorrectly without warning

### Memory Allocation Failures

If memory allocation fails (malloc returns NULL), the program may crash with a segmentation fault. Most implementations do not explicitly check for allocation failures, as they are extremely rare on modern systems with overcommit enabled.

---

## Build System

### Prerequisites

Building CMatrix requires:

1. A C compiler (gcc or clang)
2. ncurses development headers (`libncurses-dev` or `ncurses-devel`)
3. GNU autotools (autoconf, automake) for building from a git checkout

On Debian/Ubuntu:
```
apt-get install build-essential libncurses-dev autotools-dev automake
```

On Fedora/RHEL:
```
dnf install gcc ncurses-devel autoconf automake
```

On macOS with Homebrew:
```
brew install ncurses autoconf automake
```

### Building from Source

From a fresh git checkout:

```
autoreconf -i    # Generate configure script from configure.ac
./configure      # Detect system capabilities and generate Makefile
make             # Compile the binary
sudo make install  # Install to /usr/local/bin (optional)
```

The `configure` script detects:

- The C compiler and its flags
- ncurses library location and version
- Terminal capability database (terminfo/termcap)
- System-specific features

The resulting binary is a single executable (`cmatrix`) with a runtime dependency on the ncurses shared library (`libncurses.so` on Linux, `libncurses.dylib` on macOS).

### Compilation Flags

The default compilation uses standard optimization flags. Users can customize the build:

```
CFLAGS="-O2 -march=native" ./configure   # Optimize for current CPU
./configure --prefix=/opt/cmatrix          # Install to custom location
```

---

## Memory Management

### Dynamic Allocation

CMatrix dynamically allocates several arrays whose sizes depend on the terminal dimensions:

1. **Column head positions**: An integer array of size `COLS / 2`, storing the current row of each column's head character.

2. **Column tail positions**: An integer array of size `COLS / 2`, storing the current row of each column's tail eraser.

3. **Stream lengths**: An integer array of size `COLS / 2`, storing the length of each column's current stream.

4. **Update counters** (asynchronous mode): An integer array of size `COLS / 2`, storing each column's update counter for staggered rendering.

5. **Character buffer** (some implementations): A 2D array of size `LINES * COLS` storing the current character at each screen position.

### Resize Reallocation

When the terminal is resized, all dynamically allocated arrays must be freed and reallocated to match the new dimensions:

1. Free old arrays with `free()`
2. Calculate new array sizes based on updated `LINES` and `COLS`
3. Allocate new arrays with `malloc()` or `calloc()`
4. Initialize new arrays with random values

This process ensures that CMatrix always has correctly sized data structures for the current terminal dimensions.

### Cleanup on Exit

On normal exit, CMatrix frees all dynamically allocated memory:

1. Free column state arrays
2. Free update counter arrays
3. Free any character buffers
4. Call `endwin()` which frees ncurses internal data structures

While modern operating systems will reclaim all process memory on exit regardless, explicit cleanup is good practice and aids in detecting memory leaks with tools like Valgrind.

---

## Performance Characteristics

### CPU Usage

CMatrix's CPU usage is determined by several factors:

1. **Terminal size**: More columns and rows mean more characters to process per frame. CPU usage scales roughly linearly with the total number of character cells (`LINES * COLS`).

2. **Update delay**: Lower delay values cause more frames per second, linearly increasing CPU usage. At delay 0, CMatrix runs as fast as possible and can consume significant CPU.

3. **Asynchronous mode**: In asynchronous mode, not all columns update every frame, which slightly reduces per-frame CPU usage. However, the overhead of checking update counters partially offsets this saving.

4. **Rainbow mode**: Rainbow mode requires additional color pair management, slightly increasing per-frame overhead.

Typical CPU usage:

| Scenario | Approximate CPU Usage |
|----------|----------------------|
| 80x24, delay 4 | < 1% |
| 80x24, delay 0 | 2-5% |
| 200x50, delay 4 | 1-3% |
| 200x50, delay 0 | 5-15% |
| 400x100, delay 0 | 15-40% |

These values vary significantly based on hardware, terminal emulator efficiency, and system load.

### Memory Usage

CMatrix's memory usage is minimal:

- ncurses internal structures: ~50-100 KB
- Column state arrays: ~4 bytes per column * number of columns * number of arrays
- Character buffer (if used): ~1 byte per cell * LINES * COLS

For a typical 80x24 terminal, total memory usage is well under 1 MB. Even for very large terminals (400x100), memory usage remains under a few MB.

### Terminal Output Bandwidth

CMatrix generates a stream of terminal escape sequences (ANSI/ncurses) that is sent to the terminal emulator. The bandwidth depends on:

1. **Characters changed per frame**: ncurses computes the minimal diff between frames, sending only changed characters. This is much more efficient than redrawing the entire screen.

2. **Color changes**: Each color change requires an escape sequence. Rainbow mode generates more color changes than single-color mode.

3. **Attribute changes**: Bold on/off transitions require escape sequences.

4. **Frame rate**: Higher frame rates generate proportionally more output.

For a typical 80x24 terminal at default speed, the output is approximately 1-10 KB per second. At maximum speed on a large terminal, this can increase to 100+ KB per second, which can be a concern over slow network connections (SSH over high-latency links).

### Randomness and Entropy

CMatrix uses `rand()` for all random number generation (character selection, stream lengths, async timing, mutation). The random number generator is seeded once at startup with `srand(time(NULL))`.

The quality of randomness from `rand()` is sufficient for CMatrix's purposes (visual decoration), but it means:

- Two CMatrix instances started within the same second will produce identical animations
- The random sequence is deterministic given the same seed
- The distribution of `rand() % N` may not be perfectly uniform for values of N that do not evenly divide `RAND_MAX`, but this has no visible impact on the animation quality

---

## Advanced Usage Patterns

### Using CMatrix as a Screen Lock Visual

CMatrix can be combined with screen locking tools to create a Matrix-themed lock screen:

```bash
# Lock the terminal with vlock while running CMatrix on another tty
cmatrix -s &
vlock
```

Or with a simple wrapper script:

```bash
#!/bin/bash
cmatrix -s
# After CMatrix exits (any keypress), prompt for password
read -sp "Password: " pass
# ... validate password ...
```

### Embedding in Shell Scripts

CMatrix can be used in shell scripts for visual effect:

```bash
#!/bin/bash
echo "Initializing system..."
cmatrix -s -u 2 &
MATRIX_PID=$!
sleep 5
kill $MATRIX_PID
wait $MATRIX_PID 2>/dev/null
echo "System ready."
```

### Combining with tmux

CMatrix can be run in a tmux pane alongside other tools:

```bash
tmux new-session -d -s matrix
tmux send-keys -t matrix 'cmatrix -a -b -C green' C-m
tmux split-window -h -t matrix
tmux send-keys -t matrix 'htop' C-m
tmux attach -t matrix
```

### Custom Color Schemes at Runtime

Users can create visual effects by rapidly switching colors during runtime:

1. Start CMatrix: `cmatrix -a -b`
2. Press `!` for red (alarm/alert theme)
3. Press `$` for blue (cool/calm theme)
4. Press `@` for green (classic Matrix theme)
5. Press `r` for rainbow (party theme)

### Performance Tuning

For systems where CMatrix is consuming too many resources:

- Increase the delay: `cmatrix -u 8` (80ms per frame, ~12 fps)
- Reduce terminal size before starting CMatrix
- Avoid delay 0 on large terminals

For systems where CMatrix appears sluggish:

- Decrease the delay: `cmatrix -u 1` (10ms per frame)
- Use a GPU-accelerated terminal emulator (Alacritty, kitty)
- Close other terminal-intensive applications
- Ensure the terminal emulator's scrollback buffer is not excessively large (scrollback processing can slow down terminal output)

---

## Internal Constants and Configuration

### Compile-Time Constants

CMatrix defines several internal constants that affect its behavior:

1. **Character set arrays**: The arrays of characters for each mode (default, classic, Japanese, lambda) are defined at compile time. The size of these arrays determines the character pool size.

2. **Minimum/maximum stream lengths**: The bounds for random stream length generation are typically hardcoded. Minimum is usually 3-5 characters; maximum is `LINES - 3` or similar.

3. **Async update range**: The range of random values for async update counters (typically 1 to 3) is hardcoded.

4. **Mutation rate**: The probability of character mutation per frame per character position is determined by a hardcoded constant.

### Runtime State Variables

The following global state variables are maintained throughout execution:

1. **update**: The current delay value (0-10)
2. **bold_mode**: Current bold mode (none, random, all)
3. **color**: Current selected color
4. **rainbow**: Whether rainbow mode is active
5. **async_mode**: Whether asynchronous mode is active
6. **lambda_mode**: Whether lambda mode is active
7. **screensaver**: Whether screensaver mode is active
8. **message**: The message string for `-M` mode (or NULL)
9. **paused**: Whether the animation is currently paused

These variables are modified by both command-line argument parsing and runtime keyboard input.

---

## Frequently Encountered Behaviors

### First Frame Appearance

When CMatrix first starts, the screen is cleared and columns begin with their heads at various random positions near the top of the screen. This means the first few frames show short, growing streams. After a few seconds, the display reaches a steady state where streams of various lengths are continuously falling, being erased, and regenerating.

### Steady-State Visual Pattern

In steady state, the display typically shows:

- 30-60% of columns actively displaying a falling stream
- 10-20% of columns in their decay phase (tail erasing, no new characters)
- 20-40% of columns in their blank phase (waiting to start a new stream) or just beginning

The exact distribution depends on the stream length range and terminal height. Taller terminals have longer streams relative to the screen, creating a more filled appearance.

### Color Transition Behavior

When changing colors at runtime (via keystroke), the transition is not instantaneous across the entire screen. Instead:

1. The new color is set for the color pair
2. On the next `refresh()`, ncurses recalculates which characters need to be redrawn
3. Characters that were already on screen may or may not be immediately redrawn in the new color
4. As characters are naturally updated (head advancement, tail erasure, mutation), they are rendered in the new color
5. Within one or two seconds, the entire display transitions to the new color

The transition speed depends on how quickly the entire screen's worth of characters is cycled through normal updates.

### Pause and Resume

When the animation is paused (via `p`):

1. The screen freezes in its current state
2. The main loop continues running but skips the rendering and advancement steps
3. Input polling continues, allowing the user to unpause or quit
4. CPU usage drops to near zero (only the input polling loop runs)

When resumed, the animation continues exactly from where it left off. There is no jump or discontinuity; characters resume falling from their paused positions.

---

## Known Limitations

1. **No configuration file**: CMatrix does not read a configuration file. All settings must be specified via command-line flags or runtime keystrokes. There is no way to persist preferred settings across invocations without a wrapper script.

2. **No custom character sets**: Users cannot define custom character sets. The available sets (default, classic, Japanese, lambda) are compiled into the binary.

3. **No custom colors**: Beyond the 8 basic ncurses colors, CMatrix does not support custom RGB colors or 256-color mode extended palettes.

4. **No variable column width**: The 2-character column width is hardcoded and cannot be changed.

5. **No vertical speed variation per column in sync mode**: In synchronous mode, all columns fall at exactly the same speed. Only asynchronous mode provides speed variation.

6. **Single message only**: The `-M` flag supports only one message string. Multiple messages, scrolling messages, or animated text are not supported.

7. **No mouse support**: CMatrix does not process mouse input of any kind.

8. **No logging or output capture**: CMatrix's output is strictly terminal-based and cannot be meaningfully captured to a file or piped to another program.

9. **No true transparency**: While `use_default_colors()` provides some transparency on supported terminals, CMatrix cannot render semi-transparent characters or layer effects.

10. **No sound**: CMatrix is a purely visual program with no audio output.

---

## Relationship to Other Matrix Terminal Programs

CMatrix is one of several programs that simulate the Matrix digital rain effect in a terminal:

- **CMatrix** (this program): The original and most widely known C implementation. Uses ncurses.
- **unimatrix**: A Python implementation with more character set options and true color support.
- **neo**: A Rust implementation with additional visual effects.
- **tmatrix**: Another C++ terminal matrix implementation.

CMatrix distinguishes itself by being the original implementation, having minimal dependencies (just ncurses), being extremely lightweight, and having a long history of maintenance and widespread availability in Linux distribution package repositories.

---

## Summary of Runtime Keys

| Key | Action |
|-----|--------|
| `q` | Quit |
| `a` | Toggle async mode |
| `b` | Toggle random bold |
| `B` | Toggle all bold |
| `n` | Disable all bold |
| `0`-`9` | Set delay |
| `!` | Red |
| `@` | Green |
| `#` | Yellow |
| `$` | Blue |
| `%` | Magenta |
| `^` | Cyan |
| `&` | White |
| `r` | Toggle rainbow |
| `m` | Toggle lambda |
| `p`/`P` | Pause/unpause |

---

## Glossary

- **Column**: A vertical strip of the terminal, 2 character cells wide, that contains one falling character stream.
- **Head**: The bottommost, most recently generated character in a falling stream. Often rendered in bold or white for emphasis.
- **Tail**: The topmost visible character in a falling stream. As the stream falls, the tail advances downward, erasing characters above it.
- **Stream**: A sequence of characters falling down a single column. Has a head, a body, and a tail.
- **Stream length**: The number of characters visible in a stream at any given time (distance from head to tail).
- **Mutation**: The random replacement of a character within a stream body without changing its position.
- **Async mode**: A mode where each column updates at an independent rate, creating staggered scrolling.
- **Sync mode**: The default mode where all columns update simultaneously on every frame.
- **Color pair**: An ncurses concept that defines a foreground/background color combination for rendering characters.
- **napms()**: An ncurses function that pauses execution for a specified number of milliseconds.
- **Digital rain**: The colloquial name for the cascading character effect seen in The Matrix films.
- **Half-width katakana**: Japanese characters from the Unicode range U+FF66-U+FF9D that occupy a single character cell in monospaced fonts.
- **SIGWINCH**: The Unix signal sent to a process when its controlling terminal changes size.
- **endwin()**: The ncurses function that restores the terminal to its pre-ncurses state.
- **Screensaver mode**: A CMatrix mode where any keypress causes immediate program exit.
- **Lambda mode**: A mode that mixes Greek lambda characters into the active character set.
- **Rainbow mode**: A mode that cycles through all available colors for a multicolored display.
- **Update delay**: The pause between animation frames, measured in units of 10 milliseconds.
- **Frame**: A single complete rendering pass of the entire screen.
- **Refresh**: The ncurses operation that pushes the virtual screen buffer to the physical terminal.
