# nnn -- Terminal File Manager

## Overview

nnn (n cubed) is a full-featured terminal file manager. It is tiny, nearly 0-config, and incredibly fast. It is designed to be unobtrusive with smart workflows to match the trains of thought. nnn is a performance-optimized, feature-packed fork of noice (Nnn's Not Noice) with desktop integration, navigation enhancements, and a comprehensive plugin system.

nnn can analyze disk usage, batch rename files, launch applications, and pick files. The plugin system allows further extending its capabilities. There are many plugins to integrate with utilities and a wide variety of custom scripts can be run via the built-in command and shell execution infrastructure.

nnn is POSIX-compliant and follows Linux kernel coding standards. It typically requires less than 3.5MB of resident memory and has a binary size of approximately 100KB. It runs on Linux, macOS, BSD, Haiku, Cygwin, WSL, Raspberry Pi, and Termux on Android.

The core design philosophy of nnn is "don't memorize." Arrow keys, `/`, and `q` suffice for basic operation. Tab creates and cycles contexts. `?` lists all keyboard shortcuts.

---

## Options

### -a (auto NNN_FIFO)

Automatically create a unique FIFO file for each nnn instance. This is particularly useful when running multiple nnn instances simultaneously, as each instance gets its own FIFO path for preview communication. Without this option, all instances share the same `NNN_FIFO` path, which can cause conflicts when using live preview plugins.

### -A (no dir auto-enter on filter)

Disable the automatic directory entry behavior when a filter matches a single directory. By default, when the filter narrows the view down to a single directory, nnn automatically enters that directory. With `-A`, the user must explicitly press Enter or the right arrow key to enter the directory. This is useful when the user wants to perform operations on the directory itself rather than navigate into it.

### -b key (open bookmark key)

Open the bookmark corresponding to the specified key on startup. The key must be one of the keys defined in the `NNN_BMS` environment variable. This option takes precedence over `-s` and `-S` for determining the initial directory. For example, if `NNN_BMS` contains `d:$HOME/Documents`, then `nnn -b d` opens the Documents directory on startup.

### -B (use bsdtar for archives)

Use `bsdtar` instead of the default `tar` for archive operations. bsdtar (also known as libarchive) supports a wider range of archive formats than GNU tar and may be required on some systems (e.g., macOS) for proper archive handling. This affects archive creation, listing, and extraction operations.

### -c (cli-only NNN_OPENER)

Restrict the file opener to CLI-only mode. When this flag is set, nnn will not attempt to use desktop GUI applications to open files. Instead, it uses only command-line tools. This flag takes precedence over `-e`. This is particularly useful on headless servers or in SSH sessions where no graphical display is available. When combined with the `nuke` plugin as `NNN_OPENER`, it provides a comprehensive CLI-only file opening solution.

### -C (8-color scheme)

Use the 8-color scheme for the interface. This restricts the color palette to the 8 basic ANSI colors (black, red, green, yellow, blue, magenta, cyan, white) regardless of terminal capability. This is useful for terminals that do not support 256 colors or when a simpler color scheme is preferred.

### -d (detail mode)

Start nnn in detail mode. In detail mode, each file entry shows additional information including file permissions, owner, file size, and the last modification timestamp. This mode can also be toggled at runtime using the `d` key. The detail mode provides a view similar to `ls -l` output but within the nnn interface.

### -D (dirs in context color)

Display directory names using the context-specific color defined in `NNN_COLORS` rather than the default directory color. This helps visually distinguish directories when context colors are configured, making it easier to identify which context is currently active based on the color of directory entries.

### -e (text in $VISUAL/$EDITOR/vi)

Open text files in the editor specified by the `$VISUAL` environment variable, falling back to `$EDITOR`, and then to `vi` if neither is set. Without this option, text files are opened using the system's default opener (e.g., `xdg-open` on Linux). This flag is convenient for users who primarily work with text files and want quick access to their preferred editor.

### -E (internal edits in $EDITOR)

Use the `$EDITOR` environment variable for internal undetached edit operations. Internal edits are operations where nnn needs to open a file for editing and wait for the editor to close before continuing (e.g., editing the selection list). By default, nnn uses its own internal editor handling; this flag overrides that behavior.

### -f (readline history file)

Enable the use of a readline history file for the type-to-nav and filter prompts. With this option, previous filter strings and navigation inputs are saved and can be recalled using the up and down arrow keys at the prompt. The history file is stored in the nnn configuration directory.

### -F val (fifo mode)

Set the FIFO mode for preview communication. The value determines the behavior:
- `0`: Preview mode. nnn writes the full path of the currently hovered file to the FIFO whenever the cursor moves. This is used by preview plugins to display the content of the hovered file.
- `1`: Explore mode. Similar to preview mode but designed for plugins that explore or process files as the user navigates.

### -g (regex filters)

Use POSIX extended regular expressions for the filter prompt instead of the default substring matching. When this option is enabled, filter strings are interpreted as regex patterns, allowing more powerful and flexible filtering. For example, `^test.*\.py$` would match all Python files starting with "test". The regex engine supports PCRE2 when available, falling back to POSIX ERE.

### -H (show hidden files)

Show hidden files (files whose names begin with a dot) on startup. By default, nnn hides these files. Hidden file visibility can also be toggled at runtime using the `.` key. This option simply sets the initial state to visible.

### -i (show current file info)

Display detailed information about the currently hovered file. This includes file type, MIME type, size, permissions, ownership, timestamps, and other metadata. The information is shown in the configured pager.

### -J (disable auto-advance on selection)

Disable the automatic cursor advance after selecting a file with Space or `+`. By default, after selecting a file, the cursor moves down to the next entry, making it easy to select multiple consecutive files. With `-J`, the cursor stays on the current entry after selection. This can also be toggled at runtime with `^J`.

### -K (detect key collision)

Enable key collision detection mode. When this option is set, nnn checks for conflicting keybindings and reports them. This is useful when custom keybindings have been configured and the user wants to verify there are no conflicts between default and custom bindings.

### -l val (scroll lines)

Set the number of lines to scroll per scroll operation. By default, nnn scrolls one line at a time for individual key presses and a full page for page up/down. This option allows customizing the scroll increment for finer or coarser navigation control through large file listings.

### -n (type-to-nav mode)

Start nnn in type-to-nav mode. In this mode, typing any printable character immediately begins filtering the file list, without needing to press `/` first. This creates a rapid navigation experience where the user simply types part of a filename to jump to it. The mode can be toggled at runtime with `^N`.

### -N (native prompt)

Use the system's native prompt instead of nnn's custom prompt for input operations. This may improve compatibility with some terminal emulators or provide a more familiar input experience.

### -o (open files only on Enter)

Restrict file opening to only the Enter key. By default, pressing the right arrow key (`l` in vim mode) also opens the hovered file. With this option, the right arrow key only works for entering directories, and files must be opened explicitly with Enter. This prevents accidental file opening during rapid navigation.

### -p file (selection to file)

Write the list of selected file paths to the specified file on quit. If the file argument is `-`, the selection is written to standard output. This turns nnn into a file picker that can be integrated into shell scripts and pipelines. For example:

```bash
selected=$(nnn -p -)
echo "You selected: $selected"
```

### -P key (run plugin on startup)

Run the plugin mapped to the specified key immediately on startup. The key must correspond to a plugin defined in `NNN_PLUG`. This is useful for automatically launching preview plugins or other initialization plugins when nnn starts. For example, `nnn -P p` would run the plugin mapped to `p` on startup.

### -Q (no quit confirmation)

Disable the quit confirmation prompt. By default, nnn asks for confirmation before quitting when there are selected files or multiple active contexts. With this option, quitting is immediate without any confirmation dialog.

### -r (show cp/mv progress)

Show progress information during copy and move operations. This requires the `advcpmv` patched versions of `cp` and `mv` to be installed. When enabled, file transfer operations display a progress bar showing the percentage complete and transfer speed.

### -R (no rollover at edges)

Disable cursor rollover at the edges of the file list. By default, when the cursor reaches the last entry and the user presses down, it wraps around to the first entry (and vice versa). With `-R`, the cursor stops at the edges without wrapping.

### -s name (load session)

Load the named session on startup. Sessions store the state of all contexts, including their current directories, filters, sort modes, and hidden file settings. Sessions are stored as files in `${XDG_CONFIG_HOME:-$HOME/.config}/nnn/sessions/`. The session name corresponds to the filename.

### -S (persistent session)

Enable persistent session mode. In this mode, nnn automatically saves the session state on quit and restores it on the next startup. This provides a seamless experience where the user always returns to where they left off. The persistent session is stored with a predefined name in the sessions directory.

### -t secs (idle timeout for locker)

Set the idle timeout in seconds after which the terminal locker is activated. The locker command is specified by the `NNN_LOCKER` environment variable. If no locker is configured, this option has no effect. A value of 0 disables the timeout. This is useful for security in shared or public environments.

### -T key (sort order)

Set the initial sort order using a single character key:
- `a`: Sort by apparent disk usage
- `d`: Sort by disk usage (actual blocks allocated)
- `e`: Sort by file extension
- `r`: Reverse the current sort order
- `s`: Sort by file size
- `t`: Sort by time (access, change, or modification depending on the time type setting)
- `v`: Sort by version (numeric-aware string comparison)

### -u (use selection)

Use the current selection for file operations without prompting the user to confirm. By default, nnn asks whether to use the selection or the hovered file for operations like copy and move. With `-u`, the selection is always used when available.

### -U (show user and group)

Show the file owner username and group name in the file listing. This information appears alongside other file details and is useful for multi-user systems where file ownership is important.

### -x (notifications, selection sync, xterm title)

Enable multiple interface enhancements:
- Show desktop notifications on copy, move, and remove completion (requires `notify-send` or equivalent)
- Synchronize the selection across multiple nnn instances
- Update the xterm window title with the current directory path

This is a convenience flag that enables several quality-of-life features simultaneously.

### -z (fuzzy filters)

Enable ordered fuzzy matching for the filter. In fuzzy mode, characters in the filter string can match non-adjacent characters in filenames, but they must appear in the same order. For example, the filter "abc" would match "a_big_cat" because the characters a, b, and c appear in that order, even though they are not adjacent.

### -0 (null separator)

Use the NUL character (`\0`) as the separator in picker mode output instead of newline. This is useful when filenames contain newline characters and the output needs to be parsed reliably by tools that support NUL-delimited input (e.g., `xargs -0`).

### PATH (positional argument)

The startup directory or file path. When omitted, nnn opens in the current working directory. The behavior depends on whether the path exists and whether it ends with a `/`:
- Existing directory: Opens that directory
- Existing file: Opens the parent directory with the file highlighted
- Non-existent path ending in `/`: Creates the directory tree and opens it
- Non-existent path not ending in `/`: Creates parent directories, opens the parent, and prompts for file creation

---

## Environment Variables

nnn is configured entirely through environment variables. There is no configuration file. All configuration is done by setting environment variables in the user's shell profile (e.g., `.bashrc`, `.zshrc`, or `.profile`). The configuration directory is located at `${XDG_CONFIG_HOME:-$HOME/.config}/nnn/`.

### NNN_OPTS

A string of single-character CLI options to apply on every invocation, eliminating the need to type them repeatedly. Each character corresponds to a command-line flag (without the `-` prefix). For example:

```bash
export NNN_OPTS="cEnrx"
```

This is equivalent to running `nnn -c -E -n -r -x` every time. Only boolean flags (flags that do not take an argument) can be included in `NNN_OPTS`.

### NNN_BMS

Define bookmarks as semicolon-separated key-path pairs. Each bookmark consists of a single character key followed by a colon and the directory path. Bookmarks provide instant navigation to frequently visited directories.

```bash
export NNN_BMS="d:$HOME/Documents;D:$HOME/Downloads;u:/home/user/Uploads;m:/media"
```

Bookmarks are accessed at runtime by pressing `b` or `^/`, which presents a prompt where the user types the bookmark key to jump to the corresponding directory. The tilde (`~`) character is not expanded in bookmark paths; use the full `$HOME` expansion or absolute paths.

Multiple bookmarks can reference nested or related directories. The key can be any printable character, and the path can include environment variable expansions (since the variable is expanded by the shell when the profile is sourced).

### NNN_PLUG

Define plugins as semicolon-separated key-plugin pairs. Each mapping consists of a single character key followed by a colon and the plugin name. Plugins are invoked at runtime by pressing `;` followed by the assigned key, or by pressing `Alt` and the key simultaneously.

```bash
export NNN_PLUG='f:finder;o:fzopen;p:mocq;d:diffs;t:nmount;v:imgview'
```

Plugin names correspond to executable files in `${XDG_CONFIG_HOME:-$HOME/.config}/nnn/plugins/`. Several modifier prefixes and suffixes control plugin behavior:

- `-` prefix: Skip directory refresh after plugin execution. Use this for plugins that do not modify the filesystem.
- `!` prefix: Run an arbitrary CLI command as a plugin, rather than looking for a script in the plugins directory.
- `*` suffix: Skip user confirmation after execution.
- `&` suffix: Run the plugin as a GUI application (detached from the terminal).
- `|` suffix: Page non-interactive output through the configured pager.
- `>` suffix: Display output in a floating window.

For organizing large numbers of plugins, they can be grouped into sections using subdirectories:

```bash
NNN_PLUG_PERSONAL='g:personal/convert2zoom'
NNN_PLUG_WORK='j:work/prettyjson'
export NNN_PLUG="$NNN_PLUG_PERSONAL;$NNN_PLUG_WORK"
```

Pressing Enter at the plugin prompt without typing a key opens a browser listing all available unassigned plugins.

### NNN_OPENER

Specify a custom file opener to use instead of the system default (`xdg-open` on Linux, `open` on macOS, `cygstart` on Cygwin). The value should be the path to an executable that accepts a filename as its argument.

```bash
export NNN_OPENER="/path/to/custom/opener"
```

A common configuration on headless servers is to use the `nuke` plugin as the opener:

```bash
export NNN_OPENER="$HOME/.config/nnn/plugins/nuke"
```

When combined with the `-c` flag, this provides a comprehensive CLI-only file opening solution where the `nuke` plugin handles different file types using appropriate command-line tools.

### NNN_COLORS

Set the colors used for each of the contexts (tabs). The value is a string of color codes, one per context. nnn supports two color formats:

**8-color mode:** Each context color is specified by a single digit from 0-7:
- 0: Black
- 1: Red
- 2: Green
- 3: Yellow
- 4: Blue
- 5: Magenta
- 6: Cyan
- 7: White

```bash
export NNN_COLORS='1234'
```

This sets context 1 to red, context 2 to green, context 3 to yellow, and context 4 to blue.

**xterm 256-color mode:** Prefix the string with `#` and use two hexadecimal digits per context:

```bash
export NNN_COLORS='#0a1b2c3d'
```

**Mixed format:** Use 256-color codes with an 8-color fallback separated by a semicolon:

```bash
export NNN_COLORS='#0a1b2c3d;1234'
```

The colors affect the context indicator in the status bar and, when `-D` is used, the directory name colors.

### NNN_FCOLORS

Set colors for individual file types. The value is a string of 24 hexadecimal characters (2 hex digits per file type, 12 file types total). The file types are, in order:

1. Block device
2. Character device
3. Directory
4. Executable
5. Regular file
6. Hard link
7. Symbolic link
8. Missing file
9. Orphaned symbolic link
10. FIFO (named pipe)
11. Socket
12. Unknown type

```bash
export NNN_FCOLORS='c1e2272e006033f7c6d6abc4'
```

Each pair of hex digits represents an xterm 256-color code. The value `00` means use the default color. This variable provides fine-grained control over how different file types are displayed in the listing.

### NNN_ARCHIVE

Define a regular expression pattern for archive file extensions. Files matching this pattern are treated as archives, enabling archive-specific operations such as listing contents, extracting, and mounting.

```bash
export NNN_ARCHIVE="\\.(7z|bz2|gz|tar|tgz|xz|zip|zst|lz4|lzma|rar|iso|cab|ar|cpio|shar|Z)$"
```

When a file matches this pattern and the user opens it, nnn presents archive-specific options instead of the default file opener. The default pattern covers common archive formats, but this variable allows customization for specialized environments.

### NNN_SSHFS

Specify a custom `sshfs` command with options for remote filesystem mounting. The default command is `sshfs`, but additional options can be provided for features like reconnection, caching, or custom mount behavior.

```bash
export NNN_SSHFS='sshfs -o reconnect,idmap=user,follow_symlinks'
```

Remote mounts are initiated at runtime by pressing `c` and entering a hostname or `hostname:/path`. The mount point is created automatically in the nnn configuration directory. Up to 5 additional flags can be passed.

### NNN_RCLONE

Specify a custom `rclone` command with options for cloud storage mounting. rclone supports a wide variety of cloud storage providers including Google Drive, Dropbox, Amazon S3, and many others.

```bash
export NNN_RCLONE='rclone mount --read-only --vfs-cache-mode full'
```

Similar to SSHFS, rclone mounts are managed through the `c` key at runtime. The remote name must correspond to a configured rclone remote (set up via `rclone config`). Up to 5 additional flags can be specified.

### NNN_TRASH

Configure the trash mechanism used when deleting files with `x` or `^X`. The value determines which trash implementation is used:

- Not set or `0`: Use `rm` (permanent deletion, no trash)
- `1`: Use `trash-cli` (FreeDesktop.org trash specification)
- `2`: Use `gio trash` (GNOME I/O trash)
- Custom string: Use the specified command as the trash handler

```bash
export NNN_TRASH=1
```

When a trash utility is configured, deleted files are moved to the system trash rather than being permanently removed, allowing recovery. The `X` key always performs a force delete (`rm -rf`) regardless of this setting.

### NNN_SEL

Specify a custom path for the selection file. The selection file stores the list of currently selected file paths (NUL-separated). By default, the selection file is located at `${XDG_CONFIG_HOME:-$HOME/.config}/nnn/.selection`.

```bash
export NNN_SEL='/tmp/.nnn_selection'
```

This is useful for placing the selection file on a RAM disk for faster access or for sharing selections between different nnn instances or with external scripts.

### NNN_FIFO

Specify the path to a FIFO (named pipe) used for communicating the currently hovered file path to external programs. This is the foundation of the live preview system in nnn.

```bash
export NNN_FIFO='/tmp/nnn.fifo'
```

When set, nnn opens the FIFO and writes the full path of the currently hovered file every time the cursor moves. External programs (typically preview plugins) read from this FIFO and display the file content in a separate pane or window.

For single-instance usage, a fixed FIFO path is sufficient. For multiple simultaneous instances, use the `-a` flag to automatically generate unique FIFO paths per instance.

### NNN_LOCKER

Specify the terminal locker command to be used with the idle timeout (`-t` option). When the user has been idle for the specified number of seconds, nnn invokes this command to lock the terminal.

```bash
export NNN_LOCKER='vlock'
```

Common locker commands include `vlock`, `bashlock`, `lock`, and `saidar -c`. The locker must be a terminal-based program that blocks input until the user authenticates.

### NNN_TMPFILE

Specify the path to a temporary file where nnn writes the current directory path on quit. This enables the "cd on quit" feature, where the shell changes to the last directory visited in nnn after the program exits.

```bash
export NNN_TMPFILE="${XDG_CONFIG_HOME:-$HOME/.config}/nnn/.lastd"
```

To use this feature, the shell configuration must include a wrapper function or alias that reads the file after nnn exits and changes to the recorded directory. Example shell function:

```bash
n() {
    if [ -n "$NNNLVL" ] && [ "${NNNLVL:-0}" -ge 1 ]; then
        echo "nnn is already running"
        return
    fi

    NNN_TMPFILE="${XDG_CONFIG_HOME:-$HOME/.config}/nnn/.lastd"
    nnn "$@"

    if [ -f "$NNN_TMPFILE" ]; then
        . "$NNN_TMPFILE"
        rm -f "$NNN_TMPFILE" > /dev/null
    fi
}
```

The `^G` key can also be used within nnn to write the current directory to this file and quit.

### NNN_HELP

Specify a command whose output is displayed at the end of the help screen. This can be used to show custom information, tips, or even fortune cookies.

```bash
export NNN_HELP='fortune'
```

The command is executed when the user presses `?` to view help, and its output is appended to the standard help text.

### NNN_ORDER

Configure directory-specific default sort orders. This allows different directories to have different initial sort modes.

```bash
export NNN_ORDER='t:/home/user/Downloads;s:/home/user/Videos'
```

The format is `sort_key:/path`, where the sort key is one of:
- `a`: Apparent disk usage
- `d`: Disk usage
- `e`: Extension
- `r`: Reverse
- `s`: Size
- `t`: Time
- `v`: Version

Multiple entries are separated by semicolons. When nnn enters a directory that has a configured order, it automatically applies that sort mode.

### NNNLVL

This variable is set automatically by nnn to indicate the nesting level when shells are spawned from within nnn. It is not typically set by the user. The value is incremented each time a shell is launched from nnn, allowing the user's prompt to display the nesting depth:

```bash
[ -n "$NNNLVL" ] && PS1="N$NNNLVL $PS1"
```

### NNN_PIPE

This variable is set automatically by nnn when invoking plugins. It contains the path to a control pipe that plugins can write to in order to send commands back to nnn (such as changing directories or switching to list mode). This variable is not set by the user.

### NNN_MCLICK

Configure the action triggered by a middle mouse button click. The value can be a key binding string that nnn interprets as if the user had pressed that key.

```bash
export NNN_MCLICK='^R'
```

### NO_COLOR

When set to any value, disables all ANSI color output. This follows the NO_COLOR standard (https://no-color.org/) for CLI applications.

```bash
export NO_COLOR=1
```

---

## Navigation

### Basic Movement

nnn provides multiple navigation paradigms to suit different preferences:

**Arrow Keys:**
- Up / Down: Move the cursor up or down one entry
- Left: Go to the parent directory
- Right: Open the hovered file or enter the hovered directory

**Vim-style Keys:**
- `k`: Move up
- `j`: Move down
- `h`: Go to parent directory
- `l`: Open/enter hovered entry

**Scrolling:**
- Page Up / `^U`: Scroll up one page (or half page for `^U`)
- Page Down / `^D`: Scroll down one page (or half page for `^D`)
- Home / `g` / `^A`: Jump to the first entry
- End / `G` / `^E`: Jump to the last entry

**Quick Navigation Shortcuts:**
- `~`: Navigate to the home directory (`$HOME`)
- `` ` ``: Navigate to the root directory (`/`)
- `@`: Navigate to the initial start directory (the directory nnn was launched in)
- `-`: Navigate to the last visited directory (toggle between current and previous)
- `'`: Jump to the first file in the listing (skipping directories) or to the first filter match

### Enter and Backspace

Pressing Enter or the right arrow key on a directory enters it. Pressing Enter on a file opens it with the configured opener. Backspace or the left arrow key navigates to the parent directory, preserving the cursor position on the directory that was just exited.

### Jump to Entry

The `J` key allows jumping to a specific entry by typing a visible relative line offset. This is useful in long file listings where the target entry is visible but many entries away from the cursor.

### Directory History

nnn maintains a last-visited directory for each context. The `-` key toggles between the current directory and the previous one, providing a quick back-and-forth navigation mechanism similar to `cd -` in the shell.

### Smart Navigation Patterns

nnn supports several intelligent navigation behaviors:

- When a filter narrows the listing to a single directory, nnn automatically enters it (unless `-A` is set)
- When opening a path that does not exist, nnn creates necessary parent directories
- Symbolic links to directories are followed transparently
- Mount points are detected and handled appropriately for unmount operations

---

## Context System

### Overview

nnn supports up to 8 independent contexts (also called tabs or workspaces). Each context maintains its own state independently, including:

- Current directory path
- Last visited directory
- Current file cursor position
- Active filter expression
- Filter type (string, regex, or fuzzy)
- Sort mode and direction
- Hidden file visibility setting
- Color assignment

Contexts allow the user to work in multiple directories simultaneously without losing state when switching between them.

### Switching Contexts

Contexts are accessed using the number keys `1` through `8` (or `1` through `4` depending on the compile-time configuration). Each number directly switches to the corresponding context. If the context has not been used yet, it is initialized with the current directory.

The Tab key cycles forward through active contexts, while Shift-Tab either creates a new context or cycles backward through existing ones. New contexts inherit the directory of the context from which they were created.

### Context Colors

Each context can have a distinct color to provide a visual indicator of which context is active. Colors are configured via the `NNN_COLORS` environment variable. The context color appears in the status bar and, when `-D` is enabled, is applied to directory names in the listing.

The status bar displays the context numbers, with the active context highlighted. This provides an always-visible indicator of the current context and which other contexts are in use.

### Context Independence

Each context is fully independent. Changing the sort order, filter, hidden file visibility, or directory in one context does not affect any other context. This allows the user to have different views of the filesystem simultaneously -- for example, one context showing a project directory sorted by modification time with hidden files visible, and another context showing a downloads directory sorted by size.

### Closing Contexts

Pressing `q` closes the current context. If it is the last active context, `q` quits nnn (subject to quit confirmation unless `-Q` is set). `^Q` quits the entire application regardless of how many contexts are active.

---

## File Operations

### Selection Mechanism

The selection mechanism is central to file operations in nnn. Files must be selected before they can be copied, moved, or deleted. The selection is cross-context -- files selected in one context remain selected when switching to another context.

**Single Selection:** Press Space or `+` on a file to toggle its selection state. By default, the cursor advances to the next entry after selection (disable with `-J`).

**Range Selection:** Press `m` to mark the start of a range, navigate to the end of the range, and press `m` again to select all files in the range. The status bar shows `*` with a buffered count during range selection.

**Select All:** Press `a` to select all files in the current directory.

**Invert Selection:** Press `A` to invert the selection in the current directory (selected files become unselected and vice versa).

**Clear Selection:** Press Esc while in range selection mode (indicated by `*` in the status bar) to clear the range. The selection buffer can also be edited directly by pressing `E`.

**Selection Indicators:** Selected files are marked in the listing. The status bar shows `+` when files are selected, along with the count of selected files in parentheses.

### Selection File

Selected file paths are stored in a selection file (default: `${XDG_CONFIG_HOME:-$HOME/.config}/nnn/.selection`). The paths are NUL-separated. The location can be customized with the `NNN_SEL` environment variable. External scripts can read this file to access the current selection.

### Copy

Press `p` or `^P` to copy the selected files to the current directory. nnn uses `cp` (or the `advcpmv` patched version with `-r`) to perform the copy. If a file with the same name exists in the destination, the user is prompted to handle the conflict.

Press `w` or `^W` to copy files with the option to rename them at the destination. This prompts for a new name for each file being copied.

### Move

Press `v` or `^V` to move the selected files to the current directory. nnn uses `mv` (or the `advcpmv` patched version with `-r`) for the operation. Move operations that cross filesystem boundaries are handled transparently (copy + delete).

Press `w` or `^W` to move files with renaming, which prompts for a new name at the destination.

### Delete

Press `x` or `^X` to delete the selected files. The behavior depends on the `NNN_TRASH` configuration:
- If a trash utility is configured, files are moved to trash (recoverable)
- If no trash is configured, files are permanently deleted using `rm`

Press `X` to force delete files using `rm -rf`, bypassing the trash regardless of configuration. This operation is not recoverable.

### Rename

Press `^R` to rename the hovered file. nnn presents a prompt pre-filled with the current filename, allowing the user to edit it. If the user keeps the original name and confirms, nnn prompts for a second name, effectively duplicating the file.

### Batch Rename

Press `r` to batch rename files. This opens the list of filenames (either selected files or all files in the current directory) in the configured editor. The user edits the filenames in the editor, and upon saving and closing, nnn applies the renames. This is a powerful feature for bulk renaming operations using editor features like search-and-replace, macros, or multi-cursor editing.

### Archive Operations

nnn provides comprehensive archive support:

**Creating Archives:** Press `z` to create an archive from the selected files. nnn prompts for the archive format and filename. Supported formats depend on the installed archive utilities but typically include tar, tar.gz, tar.bz2, tar.xz, zip, and 7z.

**Listing Archive Contents:** When the hovered file matches the `NNN_ARCHIVE` pattern, pressing the right arrow or Enter lists the archive contents instead of attempting to open it.

**Extracting Archives:** Archive files can be extracted to the current directory. nnn supports extraction via `tar`, `unzip`, `bsdtar`, and other utilities depending on the archive format.

**Mounting Archives:** If `archivemount` and FUSE are available, archives can be mounted as virtual filesystems, allowing their contents to be browsed and accessed as regular files.

### Symbolic Links

Press `n` and choose the symlink option to create symbolic links. The user can create:
- A symbolic link to the hovered file
- Symbolic links to all selected files (batch link creation)
- Hard links to the hovered or selected files

When creating batch links, the user navigates to the target directory and can specify a prefix for the link names.

### Permissions

Press `*` to toggle the executable bit on the hovered file. This is a quick shortcut for `chmod +x` or `chmod -x`. For more complex permission changes, the user can use the shell command prompt (`!` or `^]`).

### File Creation

Press `n` to create a new file or directory. nnn prompts for the name:
- Names ending with `/` create a directory (with parent directory creation as needed)
- All other names create a regular empty file
- The prompt also offers options for creating symbolic and hard links

### File Details

Press `f` or `^F` to show detailed information about the hovered file, including:
- Full file path
- File type and MIME type
- Size (in bytes and human-readable format)
- Permissions (symbolic and octal)
- Owner and group
- Access, modification, and change timestamps
- Inode number and hard link count
- For symbolic links: the target path

### Export File List

Press `>` to export the current file listing to a file. This creates a text file containing all the filenames currently visible in the listing (respecting filters and hidden file settings).

---

## Sort Modes

nnn supports multiple sort modes that control the order of entries in the file listing. Directories always appear before files in the listing regardless of the sort mode.

### Available Sort Modes

**Name (default):** Entries are sorted alphabetically by name. The sort is case-insensitive (natural sort). Numeric sequences within filenames are compared numerically, so "file2" comes before "file10". This is the default sort mode.

**Size (`s`):** Entries are sorted by file size, largest first. This is useful for identifying large files or when looking for files of a specific size range.

**Time (`t`):** Entries are sorted by timestamp, most recent first. The specific timestamp used depends on the time type setting (see below). This is useful for finding recently modified or accessed files.

**Extension (`e`):** Entries are sorted alphabetically by their file extension. Files without extensions are grouped together. This is useful for grouping files of the same type.

**Version (`v`):** Entries are sorted using version-aware string comparison. This handles version numbers intelligently, so "v1.2.10" sorts after "v1.2.9". This uses `strverscmp()` or an equivalent algorithm.

**Apparent Disk Usage (`a`):** Entries are sorted by their apparent size (the logical size of the file content). This may differ from actual disk usage due to sparse files or filesystem block sizes.

**Disk Usage (`d`):** Entries are sorted by actual disk usage (blocks allocated). This reflects the true storage space consumed, which may be larger than the apparent size due to block allocation or smaller for sparse files.

### Time Types

When sorting by time, the specific timestamp can be selected by pressing `T`:

- **Modification time (default):** The last time the file content was modified (`mtime`)
- **Access time:** The last time the file was read (`atime`)
- **Change time:** The last time the file metadata (permissions, ownership, etc.) was changed (`ctime`)

### Reverse Sort

Press `r` or use the `-T r` option to reverse the current sort order. For example, reversing a size sort shows smallest files first. Reversing a time sort shows oldest files first.

### Sort Cycling

Press `t` or `^T` to cycle through the primary sort modes (name, size, time). This provides quick access to the most commonly used sort modes without needing to remember specific keys.

### Clearing Sort

Press `c` at the sort prompt to clear any custom sort and revert to the default filename-based sort.

### Status Bar Indicators

The current sort mode is indicated in the status bar:
- `M`: Sorted by modification time
- `A`: Sorted by access time
- `C`: Sorted by change time
- `S`: Sorted by size
- `E`: Sorted by extension
- `V`: Sorted by version
- `R`: Reverse sort is active
- `du`: Disk usage mode is active
- `au`: Apparent disk usage mode is active

### Directory-Specific Sort

Using the `NNN_ORDER` environment variable, different directories can have different default sort modes. When nnn enters a directory with a configured sort order, it automatically applies that mode. This is useful for directories where a specific sort makes the most sense, such as sorting Downloads by time or a media directory by size.

### Young File Indicator

Files created or modified within the last 5 minutes are shown with their timestamps in reverse video. This provides a visual indicator of very recently changed files.

---

## Filter System

nnn provides a powerful filtering system that allows rapid narrowing of the file listing. The filter prompt is activated by pressing `/`.

### Substring Filter (Default)

The default filter mode uses substring matching. Typing a string at the filter prompt shows only entries whose names contain that string as a substring. The matching is case-insensitive by default. For example, typing "doc" would match "Documents", "mydoc.txt", and "docker-compose.yml".

As characters are typed, the listing updates in real time, providing immediate feedback. Pressing Escape clears the filter and exits the prompt. Pressing Enter confirms the filter and returns to normal navigation with the filtered view.

### Regex Filter (-g)

When the `-g` flag is set, the filter prompt accepts POSIX extended regular expressions (ERE). This enables powerful pattern matching:

- `^test`: Files starting with "test"
- `\.py$`: Files ending with ".py"
- `^[A-Z].*\.md$`: Markdown files starting with an uppercase letter
- `(foo|bar)`: Files containing "foo" or "bar"

When PCRE2 support is compiled in, the full PCRE2 regex syntax is available, including lookaheads, lookbehinds, and other advanced features.

### Fuzzy Filter (-z)

When the `-z` flag is set, the filter uses ordered fuzzy matching. Characters in the filter string must appear in the filename in the same order, but they do not need to be adjacent. Spaces, underscores, and hyphens in the filter string are treated as flexible separators.

For example, the filter "prj" would match "project", "my_prj_file", and "p_r_j" because the characters p, r, and j appear in that order.

### Type-to-Nav Mode (-n)

Type-to-nav mode transforms the entire navigation experience. Instead of requiring `/` to enter the filter prompt, any printable character immediately begins filtering. This creates a rapid, search-as-you-type navigation experience.

In type-to-nav mode, pressing a character key immediately filters the listing. The filter updates with each keystroke. When the filter narrows to a single match, that match is automatically selected. If the single match is a directory, it is automatically entered (unless `-A` is set).

Type-to-nav mode can be toggled at runtime with `^N`. The status bar indicates when type-to-nav is active.

### Filter Persistence

Pressing `^L` toggles between the last active filter and an unfiltered view. This allows quickly switching between a filtered and full view without retyping the filter string.

### Auto-Enter on Unique Match

When a filter narrows the listing to a single directory, nnn automatically enters that directory. This behavior streamlines navigation when searching for a specific directory. The `-A` flag disables this behavior.

### Hidden Files in Filter

The `.` key toggles hidden file visibility within the filter context. This allows filtering to include or exclude hidden files without leaving the filter prompt.

### Case Sensitivity

The filter supports case-insensitive matching by default. Case sensitivity can be toggled at the filter prompt.

---

## Plugin System

### Overview

Plugins extend the capabilities of nnn without bloating the core program. They are executable scripts or binaries that nnn can communicate with and trigger via hotkeys. The plugin system is language-agnostic -- plugins can be written in any programming language (shell script, Python, Perl, compiled binaries, etc.).

Plugins are stored in `${XDG_CONFIG_HOME:-$HOME/.config}/nnn/plugins/`. They can be installed manually or via the included `getplugs` script:

```bash
sh -c "$(curl -Ls https://raw.githubusercontent.com/jarun/nnn/master/plugins/getplugs)"
```

### Plugin Configuration

Plugins are assigned to hotkeys via the `NNN_PLUG` environment variable:

```bash
export NNN_PLUG='f:finder;o:fzopen;p:mocq;d:diffs;t:nmount;v:imgview'
```

### Plugin Invocation

Plugins are invoked using one of these methods:
- Press `;` followed by the assigned key
- Press `Alt` and the assigned key simultaneously
- Press Enter at the plugin prompt to browse unassigned plugins
- Use `-P key` to run a plugin on startup

### Plugin Communication

When nnn executes a plugin, it provides several pieces of information:

**Positional Arguments:**
- `$1`: The name of the currently hovered file
- `$2`: The current working directory (non-canonical path)
- `$3`: The picker mode output file path (or `-` for stdout)

**Environment Variables:**
- `NNN_PIPE`: Path to a control pipe for sending commands back to nnn
- `NNN_INCLUDE_HIDDEN`: Set to `1` if hidden files are visible, `0` otherwise
- `NNN_PREFER_SELECTION`: Set to `1` if the user prefers to operate on the selection, `0` otherwise
- The selection file (`.selection` in the config directory) is readable and contains NUL-separated paths of selected files

### NNN_PIPE Command Protocol

Plugins can send commands back to nnn by writing to the `NNN_PIPE` FIFO. The command format is:

```
[<->]<ctxcode><opcode><data>
```

**Context Codes:**
- `+`: Smart context (use the next inactive context, or the current context if all are active)
- `0`: Current context
- `1` through `8`: Specific context number

**Opcodes:**
- `c`: Change directory to the path specified in data
- `l`: Switch to list mode and display the files specified in data
- `p`: Overwrite the picker output file with data

An optional `-` at the beginning of the command clears the current selection before executing.

Example: A plugin that changes nnn's current directory to `/tmp`:

```bash
echo "0c/tmp" > "$NNN_PIPE"
```

### FIFO-Based Preview

The `NNN_FIFO` mechanism enables live preview plugins. When configured, nnn continuously writes the full path of the hovered file to the FIFO. Preview plugins read from this FIFO in a loop and display the file content in a separate pane or window.

Two built-in preview approaches are available:
- The built-in text-based previewer, invoked with `-P`
- The `.npreview` plugin, which provides additional features and automatically overrides the built-in previewer

Popular preview plugins include:
- `preview-tui`: Uses tmux panes, terminal windows, or kitty panes for previewing. Supports multiple preview tools and ranger's `scope.sh`.
- `preview-tabbed`: Uses tabbed X windows with Xembed-capable programs (mpv for audio/video, sxiv for images, zathura for PDF).

### Plugin Modifiers

Plugin invocation can be modified with prefixes and suffixes in `NNN_PLUG`:

- `-` prefix: Do not refresh the directory listing after the plugin exits. Use for read-only plugins that do not modify the filesystem.
- `!` prefix: Execute an arbitrary CLI command as a plugin.
- `*` suffix: Skip the user confirmation prompt after execution.
- `&` suffix: Detach the plugin as a GUI application.
- `|` suffix: Pipe the plugin output through the configured pager.
- `>` suffix: Display the plugin output in a floating window.

### Writing Plugins

To create a new plugin:
1. Create an executable script in the plugins directory
2. Ensure it has execute permissions (`chmod +x`)
3. Assign it a hotkey in `NNN_PLUG`
4. The script receives the hovered filename as `$1` and the current directory as `$2`

Best practices for plugin development:
- Use POSIX-compliant shell scripts for maximum portability
- Include header comments documenting description, dependencies, and author
- Store plugin data in `${XDG_CACHE_HOME:-$HOME/.cache}/nnn/`
- Use the `nnn_cd` helper function for directory changes

### Available Plugins

nnn ships with over 60 plugins covering a wide range of functionality:

**Navigation and Search:**
- `autojump`: Integration with the autojump directory navigation tool
- `cdpath`: Navigate using CDPATH
- `fzcd`: Fuzzy directory navigation using fzf
- `fzopen`: Fuzzy file opening using fzf
- `fzhist`: Fuzzy history search
- `fzplug`: Fuzzy plugin selection
- `finder`: File finder integration
- `gitroot`: Navigate to git repository root

**File Operations:**
- `bulknew`: Bulk create files and directories
- `chksum`: Calculate and verify checksums
- `diffs`: Show file differences
- `dups`: Find duplicate files
- `fixname`: Fix filenames (remove special characters, normalize)
- `openall`: Open all files of a type
- `organize`: Organize files into directories by extension
- `renamer`: Advanced batch renaming
- `rsynccp`: Copy files using rsync (with progress)
- `splitjoin`: Split and join files
- `togglex`: Toggle executable permission

**Media and Content:**
- `boom`: Play audio files
- `cmusq`: cmus music player queue management
- `gutenread`: Browse Project Gutenberg books
- `imgview`: Image viewer integration
- `imgresize`: Resize images
- `imgur`: Upload images to Imgur
- `moclyrics`: Display lyrics for MOC player
- `mocq`: MOC music player queue
- `mp3conv`: Convert audio to MP3
- `pdfread`: Read PDF files in the terminal
- `ringtone`: Create ringtones from audio files
- `wallpaper`: Set desktop wallpaper

**System and Network:**
- `gsconnect`: GSConnect integration
- `ipinfo`: Display IP information
- `kdeconnect`: KDE Connect integration
- `mtpmount`: Mount MTP devices
- `nmount`: Network mount management
- `nuke`: Universal file opener (CLI-only)
- `pskill`: Process management
- `suedit`: Edit files with sudo
- `umounttree`: Unmount filesystem trees
- `upload`: Upload files to transfer.sh
- `xdgdefault`: Manage XDG default applications

**Preview:**
- `preview-tabbed`: X11 tabbed preview window
- `preview-tui`: Terminal-based preview pane

**Information:**
- `mimelist`: Show MIME type information
- `oldbigfile`: Find old or large files

---

## Session Management

### Overview

Sessions in nnn save and restore the complete state of all contexts, allowing the user to return to a previous working state. Session data includes the current directory, cursor position, filter, sort mode, and hidden file setting for each context.

### Named Sessions (-s)

Named sessions are created and loaded using the `-s` option:

```bash
nnn -s myproject
```

This loads the session named "myproject" if it exists, or creates a new session with that name. The session is stored as a file in `${XDG_CONFIG_HOME:-$HOME/.config}/nnn/sessions/`.

Multiple named sessions can coexist, allowing the user to maintain different workspace configurations for different tasks or projects. Sessions can be managed at runtime by pressing `s`, which presents options to save, load, or delete sessions.

### Persistent Sessions (-S)

The `-S` flag enables automatic session persistence. When enabled, nnn automatically saves the session state on quit and restores it on the next startup. This provides a seamless "resume where you left off" experience.

The persistent session uses a predefined name and is always overwritten on quit. This mode is ideal for users who always want to return to their last state.

### Session Priority

When both `-b` (bookmark), `-s` (named session), and `-S` (persistent session) are specified, the priority is:
1. `-b` (bookmark key) takes highest priority
2. `-s` (named session) is next
3. `-S` (persistent session) is used if neither `-b` nor `-s` is specified

### Runtime Session Management

Pressing `s` at runtime opens the session management prompt with options to:
- Save the current state as a named session
- Load an existing named session
- List available sessions

### Session File Format

Session files are stored in `${XDG_CONFIG_HOME:-$HOME/.config}/nnn/sessions/` and contain binary data including:
- Session format version number
- Per-context directory paths and their lengths
- Per-context current filename and filter strings
- Per-context configuration flags (sort mode, hidden files, etc.)

---

## Bookmarks

### Overview

nnn supports two types of bookmarks for quick directory access:

### Environment Variable Bookmarks (NNN_BMS)

Permanent bookmarks are configured via the `NNN_BMS` environment variable. These are semicolon-separated key-path pairs:

```bash
export NNN_BMS="d:$HOME/Documents;D:$HOME/Downloads;p:$HOME/Projects;m:/media"
```

These bookmarks are accessed by pressing `b` or `^/`, which shows a prompt where the user types the bookmark key to jump to that directory.

### Symlinked Bookmarks

Pressing `B` creates a symbolic link in `${XDG_CONFIG_HOME:-$HOME/.config}/nnn/bookmarks/` pointing to the current directory. These bookmarks persist across sessions and can be managed as regular files in the bookmarks directory.

### Directory Marks

Pressing `,` marks the current directory for quick return. This is a session-only mark (not persistent) that allows rapid back-and-forth navigation between two directories within a single nnn session. The `-` key is used to return to a marked directory.

---

## File Indicators and Status Bar

### File Type Symbols

nnn displays a single-character suffix after each filename to indicate its type:

| Symbol | File Type |
|--------|-----------|
| `/` | Directory |
| `*` | Executable file |
| `\|` | FIFO (named pipe) |
| `=` | Socket |
| `@` | Symbolic link to file |
| `b` | Block device |
| `c` | Character device |
| `?` | Unknown file type |

Hard links and symbolic links are displayed with dimmed text to distinguish them from regular files.

### Status Bar

The status bar at the bottom of the screen displays critical information about the current state:

- **Context indicators:** Numbers showing which contexts are active, with the current context highlighted
- **File position:** `x/y` showing the current cursor position and total file count
- **Selection indicator:** `+` appears when files are selected, with the count in parentheses; `*` indicates range selection mode with the buffered count
- **Sort indicator:** A letter or abbreviation showing the current sort mode (M, A, C, S, E, V, R, du, au)
- **Hidden indicator:** `H` appears when hidden files are visible
- **Link target:** `->` followed by the symlink target path for symbolic links
- **Hard link info:** `n-n` showing hard link count and inode number
- **Current path:** The full path of the current directory is shown at the top

### File Size Units

File sizes are displayed in human-readable format using binary prefixes:
- B (bytes)
- K (kibibytes, 1024 bytes)
- M (mebibytes, 1024 K)
- G (gibibytes, 1024 M)
- T (tebibytes, 1024 G)
- P (pebibytes, 1024 T)
- E (exbibytes, 1024 P)
- Z (zebibytes, 1024 E)
- Y (yobibytes, 1024 Z)

---

## Mouse Support

nnn includes mouse support for terminal emulators that report mouse events. Mouse interaction is compiled in by default and can be disabled at compile time by defining `NOMOUSE`.

### Mouse Actions

| Action | Effect |
|--------|--------|
| Left-click on context number | Switch to that context |
| Left-click on current path | Navigate to parent directory |
| Left-click on last 2 rows | Toggle type-to-nav mode |
| Left-click on entry | Select the entry (move cursor to it) |
| Left-double-click on entry | Open the entry (file or directory) |
| Right-click on entry | Add the entry to the selection |
| Middle-click | Configurable via `NNN_MCLICK` |

### Scroll Wheel

The mouse scroll wheel can be used to scroll through the file listing, providing a familiar scroll experience for users who prefer mouse interaction.

---

## Remote Mounting

nnn integrates with `sshfs` and `rclone` for transparent remote filesystem access.

### SSHFS

Remote systems can be mounted via SSH by pressing `c` and entering a hostname or `hostname:/remote/path`. nnn creates a mount point in the configuration directory and mounts the remote filesystem using `sshfs`.

Prerequisites:
- `sshfs` must be installed
- SSH keys or password authentication must be configured
- The `~/.ssh/config` file should contain host entries for convenient access

The `sshfs` command can be customized via `NNN_SSHFS`:

```bash
export NNN_SSHFS='sshfs -o reconnect,idmap=user,follow_symlinks'
```

### rclone

Cloud storage services can be mounted using `rclone` by pressing `c` and entering the rclone remote name. rclone supports dozens of cloud providers including Google Drive, Dropbox, Amazon S3, Microsoft OneDrive, and many others.

Prerequisites:
- `rclone` must be installed
- Remotes must be configured via `rclone config`

The `rclone` command can be customized via `NNN_RCLONE`:

```bash
export NNN_RCLONE='rclone mount --read-only --vfs-cache-mode full'
```

### Unmounting

Press `u` to unmount a previously mounted remote filesystem or archive. nnn uses `fusermount -u` (Linux) or `umount` (macOS) to cleanly unmount the filesystem.

---

## Disk Usage Analysis

nnn includes a built-in disk usage analyzer that can display the size of files and directories. The analyzer supports two modes:

### Block-Based Disk Usage

This mode shows the actual disk space consumed by files, accounting for filesystem block sizes, sparse files, and other storage-level details. It uses `du` to calculate sizes.

### Apparent Size

This mode shows the logical size of files as reported by `stat`. This is the actual data size and may differ from the block-based size for sparse files or files with internal compression.

### Usage

Disk usage analysis is integrated into the sort modes. Sorting by disk usage (`d`) or apparent disk usage (`a`) triggers the size calculation for all entries in the current directory. The sizes are displayed in the file listing and entries are sorted accordingly.

The status bar shows `du` or `au` to indicate which disk usage mode is active.

---

## Keyboard Shortcuts Reference

### Navigation

| Key | Action |
|-----|--------|
| Up / k | Move cursor up |
| Down / j | Move cursor down |
| Left / h | Go to parent directory |
| Right / l / Enter | Open file or enter directory |
| Page Up / ^U | Scroll up one page |
| Page Down / ^D | Scroll down one page |
| Home / g / ^A | Jump to first entry |
| End / G / ^E | Jump to last entry |
| ~ | Go to home directory |
| ` | Go to root directory |
| @ | Go to start directory |
| - | Go to last visited directory |
| ' | Jump to first file or first match |
| J | Jump to entry by offset |

### Filter and Search

| Key | Action |
|-----|--------|
| / | Enter filter prompt |
| Esc | Exit filter / clear prompt |
| . | Toggle hidden files |
| ^N | Toggle type-to-nav mode |
| ^L | Toggle last filter / redraw |

### Context and Session

| Key | Action |
|-----|--------|
| 1-8 | Switch to context 1-8 |
| Tab | Cycle to next context |
| Shift-Tab | Cycle backward or create new context |
| b / ^/ | Open bookmark prompt |
| B | Create symlinked bookmark |
| , | Mark current directory |
| s | Manage sessions |
| q | Quit current context |
| ^Q | Quit nnn |
| ^G | Quit and cd to current directory |
| Q | Quit with selection or error code |

### Selection

| Key | Action |
|-----|--------|
| Space / + | Toggle selection on hovered entry |
| m | Start / end range selection |
| a | Select all entries in current directory |
| A | Invert selection |
| E | Edit selection list in editor |
| S | Show total size of selection |
| Esc | Clear range selection / send selection to FIFO |

### File Operations

| Key | Action |
|-----|--------|
| p / ^P | Copy selected files to current directory |
| v / ^V | Move selected files to current directory |
| w / ^W | Copy or move with rename |
| x / ^X | Delete (trash or rm) |
| X | Force delete (rm -rf) |
| ^R | Rename hovered file |
| r | Batch rename |
| n | Create new file, directory, or link |
| z | Archive selected files |
| * | Toggle executable bit |
| e | Edit file in editor |
| o / ^O | Open with custom opener |
| f / ^F | Show file details |
| > | Export file list |

### Sort

| Key | Action |
|-----|--------|
| t / ^T | Cycle sort modes (name/size/time) |
| T | Change time type (access/change/modification) |

### Miscellaneous

| Key | Action |
|-----|--------|
| ; / Alt+key | Run plugin |
| = | Launch application |
| ! / ^] | Open shell in current directory |
| ] | Command prompt |
| c | Connect to remote (sshfs/rclone) |
| u | Unmount remote / archive |
| d | Toggle detail mode |
| 0 | Lock terminal |
| ? | Show help screen |

---

## Signals and Exit

### Exit Behavior

nnn provides several ways to exit:

- `q`: Quit the current context. If it is the last active context, quit nnn entirely (with confirmation unless `-Q` is set).
- `^Q`: Quit nnn immediately, closing all contexts.
- `Q`: Quit with exit code 1 if the selection is non-empty. Useful for scripting where the calling process needs to know whether files were selected.
- `^G`: Write the current directory to `NNN_TMPFILE` and quit. This is used for the cd-on-quit feature.

### Exit Codes

nnn uses the following exit codes:
- `0`: Normal exit
- `1`: Exit via `Q` with a non-empty selection, or error condition

### NNN_TMPFILE and cd-on-quit

The cd-on-quit feature allows the user's shell to change to the directory that was active in nnn when it exited. This is implemented via the `NNN_TMPFILE` mechanism:

1. The user sets `NNN_TMPFILE` to a file path in their shell profile
2. When the user presses `^G` to quit, nnn writes a `cd` command to this file
3. A shell wrapper function sources the file after nnn exits, changing the shell's working directory
4. The temporary file is then removed

This creates a seamless workflow where directory navigation in nnn carries over to the shell session.

### Quit Confirmation

By default, nnn prompts for confirmation before quitting when:
- There are selected files that have not been operated on
- Multiple contexts are active

The `-Q` flag disables this confirmation, allowing immediate quit in all cases.

### Signal Handling

nnn handles several POSIX signals:

- **SIGHUP**: Received when the terminal is closed. nnn performs cleanup and saves session state if persistent sessions are enabled.
- **SIGTSTP**: Received when the user presses `^Z` to suspend the process. nnn saves its terminal state and suspends itself, restoring the state when resumed with `fg`.
- **SIGWINCH**: Received when the terminal window is resized. nnn redraws the interface to fit the new terminal dimensions.
- **SIGINT**: Received when the user presses `^C`. nnn handles this gracefully without crashing.

During child process execution (e.g., when an editor or pager is running), nnn conditionally ignores or restores signal handlers to prevent interference with the child process.

---

## Configuration Directory Structure

nnn stores its data in `${XDG_CONFIG_HOME:-$HOME/.config}/nnn/` with the following structure:

```
nnn/
  .selection      # Current file selection (NUL-separated paths)
  .lastd          # Last directory for cd-on-quit (if NNN_TMPFILE points here)
  bookmarks/      # Symlinked bookmarks created with B
  plugins/        # Plugin scripts and binaries
  sessions/       # Saved session files
  mounts/         # Mount points for sshfs and rclone
```

---

## Dependencies

nnn has minimal dependencies for its core functionality, with additional optional dependencies for specific features:

### Required Dependencies

- **ncursesw**: Curses library with wide character support for the terminal interface
- **libc**: Standard C library

### Optional Dependencies

| Dependency | Purpose |
|------------|---------|
| `libreadline` | History support for filter and command prompts |
| `file` | MIME type detection for file details |
| `coreutils` (cp, mv, rm) | File copy, move, and delete operations |
| `xargs`, `sed` | Batch file operations |
| `GNU sed` | Copy/move operations on non-Linux systems |
| `tar`, `unzip`, `bsdtar` | Archive creation, listing, and extraction |
| `archivemount`, `fusermount` | Archive mounting as virtual filesystem |
| `sshfs` | Remote filesystem mounting via SSH |
| `rclone` | Cloud storage mounting |
| `gio trash` / `trash-cli` | FreeDesktop-compliant trash support |
| `vlock` / `bashlock` / `lock` | Terminal locking |
| `advcpmv` | Progress bars for copy/move operations |
| `$VISUAL` / `$EDITOR` / `$PAGER` | Text editing and viewing |
| `notify-send` | Desktop notifications (with `-x` flag) |

---

## Compilation and Build Options

nnn supports several compile-time options that modify its behavior:

- **O_NERD**: Enable Nerd Font icons in the file listing
- **O_EMOJI**: Enable emoji icons
- **O_ICONS**: Enable icon support (general)
- **O_NOMOUSE**: Disable mouse support
- **O_NOBATCH**: Disable batch rename functionality
- **O_NOFIFO**: Disable FIFO support
- **O_PCRE**: Use PCRE2 for regular expression matching instead of POSIX ERE

These options are passed as make variables during compilation:

```bash
make O_NERD=1 O_PCRE=1
```

---

## Terminal Compatibility

### Control Key Conflicts

Some terminal emulators intercept control key sequences before they reach nnn. Common conflicts include:

- `^S`: Typically mapped to XOFF (terminal stop). Fix: `stty stop undef`
- `^Q`: Typically mapped to XON (terminal start). Fix: `stty start undef`
- `^V`: Typically mapped to lnext (literal next). Fix: `stty lnext undef`

These conflicts can be diagnosed with `stty -a` and resolved by adding the appropriate `stty` commands to the shell profile.

### Terminal Emulator Configuration

For the best experience with nnn:
- Use a terminal that supports at least 256 colors for `NNN_COLORS` and `NNN_FCOLORS`
- Ensure the terminal reports mouse events correctly if mouse support is desired
- Configure the terminal to pass through control key sequences without interception
- For icon support (Nerd Fonts or emoji), use a terminal and font that support the required glyphs

### Minimum Terminal Size

nnn requires a minimum terminal size to function properly. When the terminal is too small, nnn displays a warning and may not render the full interface. Resizing the terminal triggers a `SIGWINCH` signal, and nnn redraws the interface to fit the new dimensions.

---

## Integration with External Tools

### Shell Integration

nnn integrates tightly with the user's shell. Key integration points include:

- **Subshell spawning:** Press `!` or `^]` to open a shell at the current directory. The `NNNLVL` variable indicates nesting depth.
- **Command execution:** Press `]` to run a shell command with full alias and pipe support.
- **cd-on-quit:** Using `NNN_TMPFILE` and a shell wrapper function, the shell can adopt nnn's last directory.
- **PWD synchronization:** Shell trap functions can synchronize the subshell's working directory with nnn.

### Editor Integration

nnn works with any terminal-based text editor. The editor is selected from:
1. `$VISUAL` environment variable
2. `$EDITOR` environment variable
3. `vi` (fallback)

The `-e` flag opens text files directly in the editor. The `-E` flag uses the editor for internal edit operations (like editing the selection list).

For non-blocking editor workflows, users can create wrapper scripts that open files in separate tmux panes, terminal tabs, or background processes.

### Vim/Neovim Integration

nnn includes a vim plugin that allows using nnn as the file explorer within vim/neovim. This replaces the built-in netrw file explorer with nnn's full feature set.

### File Picker Integration

The `-p` option turns nnn into a file picker for integration with other tools:

```bash
# Pick files and process them
nnn -p - | while IFS= read -r file; do
    process "$file"
done

# Pick files into a variable
selected=$(nnn -p -)

# Pick files into a file
nnn -p /tmp/selected_files
```

The `-0` flag changes the separator from newline to NUL for filenames containing newlines.

---

## Detailed Examples

### Example: Setting Up a Complete Environment

```bash
# Shell profile configuration
export NNN_OPTS="cdeHrUx"
export NNN_BMS="d:$HOME/Documents;D:$HOME/Downloads;p:$HOME/Projects;c:$HOME/.config"
export NNN_PLUG='p:preview-tui;f:fzopen;d:diffs;c:chksum;m:nmount;n:nuke;o:organize'
export NNN_OPENER="$HOME/.config/nnn/plugins/nuke"
export NNN_COLORS='#0a1b2c3d'
export NNN_FCOLORS='c1e2272e006033f7c6d6abc4'
export NNN_ARCHIVE="\\.(7z|bz2|gz|tar|tgz|xz|zip|zst)$"
export NNN_FIFO='/tmp/nnn.fifo'
export NNN_TRASH=1
export NNN_TMPFILE="${XDG_CONFIG_HOME:-$HOME/.config}/nnn/.lastd"
export NNN_ORDER='t:/home/user/Downloads'

# cd-on-quit wrapper
n() {
    if [ -n "$NNNLVL" ] && [ "${NNNLVL:-0}" -ge 1 ]; then
        echo "nnn is already running"
        return
    fi
    nnn "$@"
    if [ -f "$NNN_TMPFILE" ]; then
        . "$NNN_TMPFILE"
        rm -f "$NNN_TMPFILE" > /dev/null
    fi
}

# Nesting level indicator
[ -n "$NNNLVL" ] && PS1="N$NNNLVL $PS1"
```

### Example: Using nnn as a File Picker in a Script

```bash
#!/bin/bash
# Select files with nnn and compress them
selected=$(nnn -p -)
if [ -n "$selected" ]; then
    echo "$selected" | tar czf archive.tar.gz -T -
    echo "Created archive.tar.gz"
fi
```

### Example: Live Preview with tmux

```bash
# Launch nnn with preview-tui in a tmux session
export NNN_FIFO='/tmp/nnn.fifo'
export NNN_PLUG='p:preview-tui'
nnn -a -P p
```

### Example: Batch Rename Workflow

1. Navigate to the directory containing files to rename
2. Select the files (Space for individual, `a` for all, `m` for range)
3. Press `r` to open the filenames in the editor
4. Edit the filenames using editor features (find/replace, macros, etc.)
5. Save and close the editor
6. nnn applies the renames

### Example: Remote Filesystem Access

```bash
# Configure sshfs with reconnection support
export NNN_SSHFS='sshfs -o reconnect,idmap=user'

# In nnn:
# 1. Press 'c' to connect
# 2. Type the hostname (e.g., 'myserver' or 'myserver:/data')
# 3. The remote filesystem is mounted and navigable
# 4. Press 'u' to unmount when done
```

### Example: Using Multiple Contexts

1. Start nnn in the home directory
2. Press `2` to switch to context 2, navigate to `/var/log`
3. Press `3` to switch to context 3, navigate to `/tmp`
4. Press `1` to return to context 1 (home directory preserved)
5. Select files in context 1
6. Press `2` to switch to context 2
7. Press `p` to copy selected files to `/var/log`

Each context remembers its own directory, filter, and sort state independently.

---

## Troubleshooting

### Common Issues

**nnn does not start or shows garbage characters:**
Ensure the terminal supports UTF-8 and the `ncursesw` library (with wide character support) is installed. Set the locale to a UTF-8 variant (e.g., `export LANG=en_US.UTF-8`).

**Control keys do not work:**
Check for terminal interception with `stty -a`. Common fixes:
```bash
stty start undef   # Free ^Q
stty stop undef    # Free ^S
stty lnext undef   # Free ^V
```

**Colors look wrong:**
Verify that the terminal supports the color mode being used (8-color vs 256-color). Check that `NNN_COLORS` and `NNN_FCOLORS` values are correctly formatted. Use `-C` to force 8-color mode if 256 colors are not supported.

**Files do not open with the expected application:**
Check the `NNN_OPENER` variable and the `-c`/`-e` flags. Verify that the opener command exists and is executable. On Linux, check `xdg-open` configuration with `xdg-mime`.

**Archives are not recognized:**
Verify that the `NNN_ARCHIVE` pattern matches the archive extension. Ensure the required archive utilities (`tar`, `unzip`, `bsdtar`) are installed.

**Remote mounts fail:**
Verify that `sshfs` or `rclone` is installed and configured. Check SSH key authentication. Verify that the FUSE kernel module is loaded. Check mount point permissions.

**Session files are corrupted:**
Delete the session file from `${XDG_CONFIG_HOME:-$HOME/.config}/nnn/sessions/` and start fresh. Session format changes between major versions can cause incompatibility.

### Debug Information

The help screen (`?`) displays the current configuration including:
- Active command-line options
- Configured environment variables
- Key bindings
- Plugin mappings
- Bookmark definitions

This information is useful for diagnosing configuration issues.

---

## Filesystem Monitoring

nnn monitors the current directory for changes and automatically refreshes the listing when files are created, deleted, modified, or moved. The monitoring mechanism is platform-specific:

- **Linux:** Uses `inotify` with `IN_CREATE`, `IN_DELETE`, `IN_MODIFY`, and `IN_MOVE_SELF` event flags
- **BSD/macOS:** Uses `kqueue` with `NOTE_DELETE`, `NOTE_EXTEND`, and `NOTE_WRITE` filter flags
- **Haiku:** Uses the native filesystem monitoring interface

When a change is detected, nnn re-reads the directory contents and updates the display. The cursor position is preserved when possible. Manual refresh can be triggered with `^L`.

---

## Security Considerations

nnn is designed with privacy in mind:
- No user data is collected or transmitted
- No network connections are made by the core program (only by explicitly invoked remote mount tools)
- The selection file is stored locally with user permissions
- Session files contain only directory paths and settings, no file contents
- Shell commands are executed with the user's permissions and environment

When running nnn with elevated privileges (`sudo`), the `-E` option preserves the user's environment variables:

```bash
sudo -E nnn -dH
```

---

## Performance

nnn is optimized for speed and low resource consumption:

- **Memory:** Typically uses less than 3.5MB of resident memory, even with thousands of files
- **Binary size:** Approximately 100KB
- **Startup time:** Near-instantaneous
- **Directory loading:** Optimized for large directories with thousands of entries
- **Filter responsiveness:** Real-time filtering with minimal latency even on large listings

The design philosophy prioritizes performance by keeping the core small and delegating complex functionality to plugins. Static analysis and profiling are used during development to maintain these performance characteristics.

Files created or modified within the last 5 minutes are flagged internally (`FILE_YOUNG`) and displayed with reversed timestamps for quick visual identification.

---

## Summary of Defaults

| Setting | Default Value |
|---------|---------------|
| Hidden files | Not shown |
| Sort order | Name (natural, case-insensitive) |
| Filter mode | Substring matching |
| Detail mode | Off (light mode) |
| Type-to-nav | Off |
| File opener | xdg-open / open / cygstart |
| Trash | Disabled (permanent delete) |
| Contexts | 1 active, up to 8 available |
| Session | None (no persistence) |
| Mouse | Enabled (if compiled with support) |
| Quit confirmation | Enabled |
| Auto-advance on selection | Enabled |
| Rollover at edges | Enabled |
| Dir auto-enter on filter | Enabled |
