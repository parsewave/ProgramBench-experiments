# csview -- CSV/TSV Pretty Printer

## Overview

csview is a high-performance command-line utility for pretty-printing CSV (Comma-Separated Values) and TSV (Tab-Separated Values) files as formatted tables in the terminal. Written in Rust, csview is designed for speed and low memory usage while providing correct rendering of CJK (Chinese, Japanese, Korean) characters and emoji, which occupy double the width of standard ASCII characters in terminal displays.

csview reads structured delimiter-separated data from either a file argument or standard input (stdin), parses it according to standard CSV conventions (RFC 4180), and renders it as a visually aligned table using configurable border styles, padding, indentation, and text alignment. It supports eight distinct table styles ranging from classic ASCII box drawing to Markdown-compatible output, and it provides fine-grained control over header and body text alignment independently.

The tool is particularly useful for:

- Quickly inspecting CSV/TSV data files in the terminal
- Formatting delimiter-separated output from other commands for readability
- Generating Markdown-compatible tables from CSV data
- Viewing data files that contain CJK or emoji characters with correct column alignment
- Parsing non-standard delimiter-separated formats (colon-separated, pipe-separated, semicolon-separated, etc.)

csview is licensed under the dual MIT/Apache-2.0 license and is available on multiple platforms including Linux, macOS, Windows, and ARM architectures.

---

## Command-Line Usage

csview accepts an optional file path as a positional argument. If no file is provided and stdin is not a terminal (i.e., data is being piped in), csview reads from stdin. If no file is provided and stdin is a terminal (interactive mode), csview prints an error message and exits with a non-zero status code.

### Basic Examples

Reading from a file:
```
csview data.csv
```

Reading from stdin via pipe:
```
cat data.csv | csview
```

Reading from stdin via redirection:
```
csview < data.csv
```

Combining with other commands:
```
head /etc/passwd | csview -H -d:
```

---

## Arguments

### `[FILE]`

An optional positional argument specifying the path to the input file to read. The file must exist and be readable. If the file does not exist, csview prints an error message to stderr and exits with exit code 1. If the file exists but is not readable (permission denied), csview prints an I/O error to stderr and exits with an appropriate error code.

If `FILE` is not provided:
- If stdin is connected to a pipe (non-terminal), csview reads from stdin.
- If stdin is a terminal (interactive), csview prints `no input file specified (use -h for help)` to stderr and exits with exit code 1.

The `FILE` argument supports standard file path conventions, including relative and absolute paths.

**Examples:**
```
csview mydata.csv
csview /path/to/data.csv
csview ../relative/path/data.tsv
```

The double-dash separator (`--`) can be used to explicitly mark the end of options, so that file names beginning with a dash are treated as positional arguments rather than flags:
```
csview -- -unusual-filename.csv
```

---

## Options

### `-d, --delimiter <CHAR>`

Specifies the field delimiter character used to separate columns in the input data. The default delimiter is a comma (`,`).

The delimiter must be exactly one character. Providing an empty string or a multi-character string will result in an error. The delimiter is specified as a single character value.

This option conflicts with the `--tsv` / `-t` flag. You cannot specify both `--delimiter` and `--tsv` simultaneously; attempting to do so will produce an error indicating that the two options are mutually exclusive.

**Default:** `,` (comma)

**Examples:**

Using a semicolon delimiter:
```
csview -d';' data.csv
csview --delimiter ';' data.csv
```

Using a colon delimiter (e.g., for `/etc/passwd`):
```
csview -d: /etc/passwd
csview --delimiter ':' /etc/passwd
```

Using a pipe delimiter:
```
csview -d'|' data.txt
csview --delimiter '|' data.txt
```

Using a space delimiter:
```
csview -d' ' data.txt
```

Using a tab character (equivalent to `--tsv`):
```
csview -d'	' data.tsv
```

Note: When specifying special characters like tab on the command line, you may need to use shell-specific quoting. For tab, it is generally easier to use the `--tsv` shorthand instead.

The flag-value can be provided in multiple equivalent forms:
```
csview -d,           # short flag, value directly attached
csview -d ','        # short flag, value as separate argument
csview --delimiter , # long flag, value as separate argument
csview --delimiter=, # long flag, value with equals sign
```

---

### `-t, --tsv`

A convenience shorthand that sets the delimiter to a tab character (`\t`). This is equivalent to `-d '\t'` but is easier to type and less prone to shell quoting issues.

This flag conflicts with `--delimiter` / `-d`. If both are specified, csview will produce an error.

**Default:** Off (comma delimiter is used unless overridden by `-d`)

**Examples:**

Reading a TSV file:
```
csview --tsv data.tsv
csview -t data.tsv
```

Reading tab-separated output from another command:
```
printf "Name\tAge\tCity\nAlice\t30\tNYC\nBob\t25\tLA\n" | csview --tsv
```

Output:
```
┌───────┬─────┬──────┐
│ Name  │ Age │ City │
├───────┼─────┼──────┤
│ Alice │ 30  │ NYC  │
│ Bob   │ 25  │ LA   │
└───────┴─────┴──────┘
```

---

### `-H, --no-headers`

Specifies that the input data does not have a header row. By default, csview treats the first row of the input as a header row. When this flag is set, all rows are treated as data rows and no header separator line is drawn between the first and second rows.

When headers are present (the default), the first row receives special formatting:
- It is rendered with center alignment by default (controllable via `--header-align`).
- A separator line (the "second" row separator) is drawn between the header row and the first data row.

When `--no-headers` is set:
- All rows are treated as data rows.
- All rows use the body alignment (controllable via `--body-align`).
- No "second" separator line is drawn between the first and second rows (unless the style includes mid-row separators, such as the Grid style).

**Default:** Off (first row is treated as a header)

**Examples:**

Data without headers:
```
printf "Alice,30,NYC\nBob,25,LA\n" | csview -H
```

Output:
```
┌───────┬────┬─────┐
│ Alice │ 30 │ NYC │
│ Bob   │ 25 │ LA  │
└───────┴────┴─────┘
```

Compare with headers (default):
```
printf "Name,Age,City\nAlice,30,NYC\nBob,25,LA\n" | csview
```

Output:
```
┌───────┬─────┬──────┐
│ Name  │ Age │ City │
├───────┼─────┼──────┤
│ Alice │ 30  │ NYC  │
│ Bob   │ 25  │ LA   │
└───────┴─────┴──────┘
```

The flag is commonly used when reading data formats that do not include a header row, such as `/etc/passwd`:
```
head -5 /etc/passwd | csview -H -d:
```

---

### `-n, --number`

Prepends a column of sequential line numbers to the table output. The line number column is labeled `#` in the header row (when headers are present). Line numbers start at 1 for the first data row and increment by 1 for each subsequent row.

This flag also has an alias `--seq`, so `--seq` and `--number` are interchangeable.

The width of the line number column is automatically calculated based on the total number of rows that will be displayed, ensuring proper alignment even for large datasets.

**Default:** Off

**Examples:**

With headers:
```
printf "Name,Age\nAlice,30\nBob,25\nCarol,28\n" | csview -n
```

Output:
```
┌───┬───────┬─────┐
│ # │ Name  │ Age │
├───┼───────┼─────┤
│ 1 │ Alice │ 30  │
│ 2 │ Bob   │ 25  │
│ 3 │ Carol │ 28  │
└───┴───────┴─────┘
```

Without headers:
```
printf "Alice,30\nBob,25\nCarol,28\n" | csview -H -n
```

Output:
```
┌───┬───────┬────┐
│ 1 │ Alice │ 30 │
│ 2 │ Bob   │ 25 │
│ 3 │ Carol │ 28 │
└───┴───────┴────┘
```

Using the `--seq` alias:
```
printf "Name,Age\nAlice,30\n" | csview --seq
```

---

### `-s, --style <STYLE>`

Sets the table border and rendering style. csview supports eight different table styles, each with distinct visual characteristics. Style names are case-insensitive: `Sharp`, `sharp`, `SHARP`, and `sHaRp` are all equivalent.

If an invalid style name is provided, csview will print an error message listing the valid possible values and exit with a non-zero status code.

**Default:** `Sharp`

**Available styles:** `None`, `Ascii`, `Ascii2`, `Sharp`, `Rounded`, `Reinforced`, `Markdown`, `Grid`

See the [Table Styles](#table-styles) section below for detailed descriptions and visual examples of each style.

**Examples:**
```
csview -s ascii data.csv
csview --style markdown data.csv
csview -s rounded data.csv
csview --style=grid data.csv
```

---

### `-p, --padding <NUM>`

Sets the number of space characters used as padding on each side of every cell's content. The padding is applied between the cell content and the column separator characters.

**Default:** `1`

A padding of 0 means cell content is placed directly against the column separators with no spacing. Larger padding values add more whitespace around each cell, making the table wider but potentially more readable.

**Examples:**

Default padding (1):
```
printf "a,b,c\n1,2,3\n" | csview
```

Output:
```
┌───┬───┬───┐
│ a │ b │ c │
├───┼───┼───┤
│ 1 │ 2 │ 3 │
└───┴───┴───┘
```

Zero padding:
```
printf "a,b,c\n1,2,3\n" | csview -p0
```

Output:
```
┌─┬─┬─┐
│a│b│c│
├─┼─┼─┤
│1│2│3│
└─┴─┴─┘
```

Padding of 3:
```
printf "a,b,c\n1,2,3\n" | csview -p3
```

Output:
```
┌───────┬───────┬───────┐
│   a   │   b   │   c   │
├───────┼───────┼───────┤
│   1   │   2   │   3   │
└───────┴───────┴───────┘
```

Large padding of 5:
```
printf "a,b,c\n1,2,3\n" | csview --padding 5
```

Output:
```
┌───────────┬───────────┬───────────┐
│     a     │     b     │     c     │
├───────────┼───────────┼───────────┤
│     1     │     2     │     3     │
└───────────┴───────────┴───────────┘
```

The `--padding` flag can be specified in multiple equivalent forms:
```
csview -p1
csview -p 1
csview --padding 1
csview --padding=1
```

---

### `-i, --indent <NUM>`

Sets the number of space characters used as global left indentation for the entire table. The indent is applied as leading whitespace before every line of the table output, including separator rows.

**Default:** `0`

**Examples:**

Indent of 4:
```
printf "a,b,c\n1,2,3\n" | csview -i4
```

Output:
```
    ┌───┬───┬───┐
    │ a │ b │ c │
    ├───┼───┼───┤
    │ 1 │ 2 │ 3 │
    └───┴───┴───┘
```

Indent of 2:
```
printf "a,b,c\n1,2,3\n" | csview --indent 2
```

Output:
```
  ┌───┬───┬───┐
  │ a │ b │ c │
  ├───┼───┼───┤
  │ 1 │ 2 │ 3 │
  └───┴───┴───┘
```

The indentation is useful when embedding table output in documents or when the table needs to be visually offset from surrounding text.

---

### `--sniff <LIMIT>`

Controls how many rows csview reads ahead to determine optimal column widths. csview needs to examine cell contents to calculate the maximum width for each column. The sniff limit controls how many data rows are examined for this purpose.

**Default:** `1000`

When set to a positive number N, csview reads up to N data rows to determine column widths. Rows beyond this limit are still displayed but may cause columns to be wider than calculated if they contain longer values (though in practice, since the sniff buffer is consumed first and subsequent rows are rendered as-is, columns are sized only from the sniffed rows and the header).

When set to `0`, the limit is removed entirely and csview reads all rows before rendering. This guarantees that column widths are optimal for the entire dataset, but requires buffering the entire file in memory. The help text describes this as: specify "0" to cancel the limit.

For very large files, the default limit of 1000 provides a good balance between accurate column widths and memory efficiency. Reducing the sniff limit (e.g., `--sniff 1`) causes csview to determine column widths from only the first row (plus the header), which may result in columns that are too narrow for subsequent rows. Increasing it or setting it to 0 ensures more accurate column widths at the cost of higher memory usage and slower initial rendering.

**Examples:**

Default sniff (1000 rows):
```
csview data.csv
```

Sniff only 100 rows:
```
csview --sniff 100 data.csv
```

Sniff only 1 row:
```
csview --sniff 1 data.csv
```

Unlimited sniff (read all rows):
```
csview --sniff 0 data.csv
```

**Behavior detail:** When `--sniff` is set to a value N, csview reads the header (if present) and then up to N data rows. It calculates column widths based on these rows. The sniffed rows are buffered in memory and then yielded first during rendering, followed by any remaining rows read directly from the input. This means the total output always includes all rows, but column widths are determined only from the sniffed subset.

---

### `--header-align <ALIGNMENT>`

Specifies the text alignment for header row cells. This option only has effect when headers are present (i.e., `--no-headers` is not set).

**Default:** `Center`

**Available values:** `Left`, `Center`, `Right` (case-insensitive)

**Examples:**

Left-aligned header:
```
printf "Name,Age,City\nAlice,30,NYC\nBob,25,LA\n" | csview --header-align left
```

Output:
```
┌───────┬─────┬──────┐
│ Name  │ Age │ City │
├───────┼─────┼──────┤
│ Alice │ 30  │ NYC  │
│ Bob   │ 25  │ LA   │
└───────┴─────┴──────┘
```

Right-aligned header:
```
printf "Name,Age,City\nAlice,30,NYC\nBob,25,LA\n" | csview --header-align right
```

Output:
```
┌───────┬─────┬──────┐
│  Name │ Age │ City │
├───────┼─────┼──────┤
│ Alice │ 30  │ NYC  │
│ Bob   │ 25  │ LA   │
└───────┴─────┴──────┘
```

Center-aligned header (default):
```
printf "Name,Age,City\nAlice,30,NYC\nBob,25,LA\n" | csview --header-align center
```

Output:
```
┌───────┬─────┬──────┐
│ Name  │ Age │ City │
├───────┼─────┼──────┤
│ Alice │ 30  │ NYC  │
│ Bob   │ 25  │ LA   │
└───────┴─────┴──────┘
```

---

### `--body-align <ALIGNMENT>`

Specifies the text alignment for data (body) row cells. This controls the alignment of all non-header rows.

**Default:** `Left`

**Available values:** `Left`, `Center`, `Right` (case-insensitive)

**Examples:**

Right-aligned body:
```
printf "Name,Age,City\nAlice,30,NYC\nBob,25,LA\n" | csview --body-align right
```

Output:
```
┌───────┬─────┬──────┐
│ Name  │ Age │ City │
├───────┼─────┼──────┤
│ Alice │  30 │  NYC │
│   Bob │  25 │   LA │
└───────┴─────┴──────┘
```

Center-aligned body:
```
printf "Name,Age,City\nAlice,30,NYC\nBob,25,LA\n" | csview --body-align center
```

Output:
```
┌───────┬─────┬──────┐
│ Name  │ Age │ City │
├───────┼─────┼──────┤
│ Alice │ 30  │ NYC  │
│  Bob  │ 25  │  LA  │
└───────┴─────┴──────┘
```

Left-aligned body (default):
```
printf "Name,Age,City\nAlice,30,NYC\nBob,25,LA\n" | csview --body-align left
```

Combining header and body alignment:
```
printf "Name,Age,City\nAlice,30,NYC\nBob,25,LA\n" | csview --header-align left --body-align right
```

Output:
```
┌───────┬─────┬──────┐
│ Name  │ Age │ City │
├───────┼─────┼──────┤
│ Alice │  30 │  NYC │
│   Bob │  25 │   LA │
└───────┴─────┴──────┘
```

---

### `-P, --disable-pager`

Disables the automatic pager. By default, on Unix systems, when stdout is connected to a terminal (interactive mode), csview pipes its output through a pager program (by default `less` with the `-SF` flags, which enables horizontal scrolling and chop-long-lines mode). This flag disables that behavior, causing csview to print directly to stdout.

This option is only available on Unix systems when csview is compiled with the `pager` feature (which is enabled by default).

The pager can also be customized via the `CSVIEW_PAGER` environment variable. When set, csview uses the specified pager program instead of the default `less`.

**Default:** Off (pager is enabled when stdout is a terminal on Unix)

**Examples:**

Disable the pager:
```
csview -P data.csv
csview --disable-pager data.csv
```

---

## Table Styles

csview supports eight distinct table styles. Each style defines the characters used for borders, column separators, row separators, and corner/junction characters. Style names are case-insensitive when specified via the `--style` / `-s` option.

The following sample data is used in all style examples below:
```csv
Name,Age,City
Alice,30,NYC
Bob,25,LA
```

### Sharp Style (Default)

The Sharp style is the default style used by csview. It uses Unicode box-drawing characters with straight corners. The top border, header separator, and bottom border all use the standard box-drawing set. There are no separators between data rows.

Characters used:
- Column separator: `│` (U+2502, BOX DRAWINGS LIGHT VERTICAL)
- Horizontal line: `─` (U+2500, BOX DRAWINGS LIGHT HORIZONTAL)
- Top-left corner: `┌` (U+250C, BOX DRAWINGS LIGHT DOWN AND RIGHT)
- Top-right corner: `┐` (U+2510, BOX DRAWINGS LIGHT DOWN AND LEFT)
- Bottom-left corner: `└` (U+2514, BOX DRAWINGS LIGHT UP AND RIGHT)
- Bottom-right corner: `┘` (U+2518, BOX DRAWINGS LIGHT UP AND LEFT)
- Top junction: `┬` (U+252C, BOX DRAWINGS LIGHT DOWN AND HORIZONTAL)
- Bottom junction: `┴` (U+2534, BOX DRAWINGS LIGHT UP AND HORIZONTAL)
- Left junction: `├` (U+251C, BOX DRAWINGS LIGHT VERTICAL AND RIGHT)
- Right junction: `┤` (U+2524, BOX DRAWINGS LIGHT VERTICAL AND LEFT)
- Cross junction: `┼` (U+253C, BOX DRAWINGS LIGHT VERTICAL AND HORIZONTAL)

**Structure:**
- Top border row: present
- Header separator (second row separator): present
- Mid-row separators (between data rows): absent
- Bottom border row: present

**Example:**
```
csview -s sharp data.csv
```

Output:
```
┌───────┬─────┬──────┐
│ Name  │ Age │ City │
├───────┼─────┼──────┤
│ Alice │ 30  │ NYC  │
│ Bob   │ 25  │ LA   │
└───────┴─────┴──────┘
```

With no headers:
```
csview -s sharp -H data_no_header.csv
```

Output:
```
┌───────┬────┬─────┐
│ Alice │ 30 │ NYC │
│ Bob   │ 25 │ LA  │
└───────┴────┴─────┘
```

---

### Rounded Style

The Rounded style is similar to the Sharp style but uses rounded corner characters for the top-left, top-right, bottom-left, and bottom-right corners. All other characters (column separator, horizontal line, junctions) are the same as Sharp.

Characters used:
- Column separator: `│`
- Horizontal line: `─`
- Top-left corner: `╭` (U+256D, BOX DRAWINGS LIGHT ARC DOWN AND RIGHT)
- Top-right corner: `╮` (U+256E, BOX DRAWINGS LIGHT ARC DOWN AND LEFT)
- Bottom-left corner: `╰` (U+2570, BOX DRAWINGS LIGHT ARC UP AND RIGHT)
- Bottom-right corner: `╯` (U+256F, BOX DRAWINGS LIGHT ARC UP AND LEFT)
- All junction characters same as Sharp: `┬`, `┴`, `├`, `┤`, `┼`

**Structure:**
- Top border row: present (with rounded corners)
- Header separator: present
- Mid-row separators: absent
- Bottom border row: present (with rounded corners)

**Example:**
```
csview -s rounded data.csv
```

Output:
```
╭───────┬─────┬──────╮
│ Name  │ Age │ City │
├───────┼─────┼──────┤
│ Alice │ 30  │ NYC  │
│ Bob   │ 25  │ LA   │
╰───────┴─────┴──────╯
```

The Rounded style is visually softer and is a popular choice for decorative terminal output.

---

### Reinforced Style

The Reinforced style uses heavy (bold) box-drawing characters for the four outer corners while keeping all other characters the same as the Sharp style. This creates a visual emphasis on the table boundaries.

Characters used:
- Column separator: `│`
- Horizontal line: `─`
- Top-left corner: `┏` (U+250F, BOX DRAWINGS HEAVY DOWN AND RIGHT)
- Top-right corner: `┓` (U+2513, BOX DRAWINGS HEAVY DOWN AND LEFT)
- Bottom-left corner: `┗` (U+2517, BOX DRAWINGS HEAVY UP AND RIGHT)
- Bottom-right corner: `┛` (U+251B, BOX DRAWINGS HEAVY UP AND LEFT)
- All junction characters same as Sharp: `┬`, `┴`, `├`, `┤`, `┼`

**Structure:**
- Top border row: present (with heavy corners)
- Header separator: present
- Mid-row separators: absent
- Bottom border row: present (with heavy corners)

**Example:**
```
csview -s reinforced data.csv
```

Output:
```
┏───────┬─────┬──────┓
│ Name  │ Age │ City │
├───────┼─────┼──────┤
│ Alice │ 30  │ NYC  │
│ Bob   │ 25  │ LA   │
┗───────┴─────┴──────┛
```

---

### ASCII Style

The ASCII style uses only standard ASCII characters for all borders and separators. This style is compatible with any terminal or font and does not require Unicode support.

Characters used:
- Column separator: `|` (U+007C, VERTICAL LINE)
- Horizontal line: `-` (U+002D, HYPHEN-MINUS)
- All corners and junctions: `+` (U+002B, PLUS SIGN)

**Structure:**
- Top border row: present
- Header separator: present
- Mid-row separators: absent
- Bottom border row: present

**Example:**
```
csview -s ascii data.csv
```

Output:
```
+-------+-----+------+
| Name  | Age | City |
+-------+-----+------+
| Alice | 30  | NYC  |
| Bob   | 25  | LA   |
+-------+-----+------+
```

The ASCII style is the most portable option and is guaranteed to display correctly in any terminal emulator, text editor, or monospaced font environment.

With no headers:
```
printf "Alice,30,NYC\nBob,25,LA\n" | csview -s ascii -H
```

Output:
```
+-------+----+-----+
| Alice | 30 | NYC |
| Bob   | 25 | LA  |
+-------+----+-----+
```

---

### Ascii2 Style

The Ascii2 style is a minimal ASCII-based style that uses no left or right borders and shows only a header separator line. It resembles the output of the Unix `column` command or the header-separator style used by many database CLIs.

Characters used:
- Left column separator: ` ` (space, effectively no visible left border)
- Middle column separator: `|`
- Right column separator: ` ` (space, effectively no visible right border)
- Header separator horizontal line: `-`
- Header separator left junction: ` ` (space)
- Header separator cross junction: `+`
- Header separator right junction: ` ` (space)

**Structure:**
- Top border row: absent
- Header separator: present (a dashed line with `+` at column junctions)
- Mid-row separators: absent
- Bottom border row: absent

**Example:**
```
csview -s ascii2 data.csv
```

Output:
```
 Name  | Age | City
-------+-----+------
 Alice | 30  | NYC
 Bob   | 25  | LA
```

This style is particularly clean and uncluttered, making it suitable for embedding output in reports or documentation where heavy borders would be distracting.

With no headers:
```
printf "Alice,30,NYC\nBob,25,LA\n" | csview -s ascii2 -H
```

Output:
```
 Alice | 30 | NYC
 Bob   | 25 | LA
```

---

### Markdown Style

The Markdown style produces output that is compatible with GitHub Flavored Markdown (GFM) and most Markdown renderers. The table can be directly copied and pasted into Markdown documents.

Characters used:
- Column separator: `|`
- Header separator horizontal line: `-`
- Header separator left junction: `|`
- Header separator cross junction: `|`
- Header separator right junction: `|`

**Structure:**
- Top border row: absent
- Header separator: present (a dashed line with `|` at column boundaries)
- Mid-row separators: absent
- Bottom border row: absent

**Example:**
```
csview -s markdown data.csv
```

Output:
```
| Name  | Age | City |
|-------|-----|------|
| Alice | 30  | NYC  |
| Bob   | 25  | LA   |
```

This output, when rendered by a Markdown processor, produces:

| Name  | Age | City |
|-------|-----|------|
| Alice | 30  | NYC  |
| Bob   | 25  | LA   |

The Markdown style is particularly useful for generating documentation, README files, or issue reports from CSV data.

With custom alignment and padding:
```
csview -s markdown --header-align left --body-align right data.csv
```

Output:
```
| Name  | Age | City |
|-------|-----|------|
| Alice |  30 |  NYC |
|   Bob |  25 |   LA |
```

---

### Grid Style

The Grid style is similar to the Sharp style but adds separator lines between every data row, not just between the header and the first data row. This creates a full grid where every cell is visually enclosed.

Characters used:
- Same character set as Sharp style
- Column separator: `│`
- Horizontal line: `─`
- Corners: `┌`, `┐`, `└`, `┘`
- Junctions: `┬`, `┴`, `├`, `┤`, `┼`

**Structure:**
- Top border row: present
- Header separator: present
- Mid-row separators: present (between every pair of data rows)
- Bottom border row: present

**Example:**
```
csview -s grid data.csv
```

Output:
```
┌───────┬─────┬──────┐
│ Name  │ Age │ City │
├───────┼─────┼──────┤
│ Alice │ 30  │ NYC  │
├───────┼─────┼──────┤
│ Bob   │ 25  │ LA   │
└───────┴─────┴──────┘
```

The key difference between Grid and Sharp is the presence of mid-row separators. In the Sharp style, data rows are stacked without separators. In the Grid style, every row is separated by a horizontal line.

With more data:
```
printf "Name,Age,City\nAlice,30,NYC\nBob,25,LA\nCarol,28,SF\n" | csview -s grid
```

Output:
```
┌───────┬─────┬──────┐
│ Name  │ Age │ City │
├───────┼─────┼──────┤
│ Alice │ 30  │ NYC  │
├───────┼─────┼──────┤
│ Bob   │ 25  │ LA   │
├───────┼─────┼──────┤
│ Carol │ 28  │ SF   │
└───────┴─────┴──────┘
```

The Grid style uses the same junction characters for both the header separator and the mid-row separators (`├`, `┼`, `┤`). This is in contrast to the Sharp style's top border which uses `┌`, `┬`, `┐`.

---

### None Style

The None style removes all borders, separators, and column delimiters entirely. Only the cell content and padding/indentation are rendered. This produces clean, space-aligned columnar output with no visual decoration.

**Structure:**
- Top border row: absent
- Header separator: absent
- Mid-row separators: absent
- Bottom border row: absent
- Column separators: absent (no left, middle, or right separators)

**Example:**
```
csview -s none data.csv
```

Output:
```
 Name   Age  City
 Alice  30   NYC
 Bob    25   LA
```

The None style is useful when you want aligned columnar data without any table borders, similar to the output of `column -t`.

With zero padding:
```
csview -s none -p0 data.csv
```

Output:
```
Name Age City
Alice30  NYC
Bob  25  LA
```

---

### Style Comparison

The following table summarizes the differences between all eight styles:

| Style      | Top Border | Header Sep | Mid-Row Sep | Bottom Border | Left/Right Border | Unicode |
|------------|:----------:|:----------:|:-----------:|:-------------:|:-----------------:|:-------:|
| Sharp      | Yes        | Yes        | No          | Yes           | Yes               | Yes     |
| Rounded    | Yes        | Yes        | No          | Yes           | Yes               | Yes     |
| Reinforced | Yes        | Yes        | No          | Yes           | Yes               | Yes     |
| ASCII      | Yes        | Yes        | No          | Yes           | Yes               | No      |
| Ascii2     | No         | Yes        | No          | No            | No                | No      |
| Markdown   | No         | Yes        | No          | No            | Yes               | No      |
| Grid       | Yes        | Yes        | Yes         | Yes           | Yes               | Yes     |
| None       | No         | No         | No          | No            | No                | No      |

---

## Delimiter Handling

### Default Delimiter

By default, csview uses the comma (`,`) as the field delimiter. This is standard for CSV (Comma-Separated Values) files.

### Custom Delimiters

Any single ASCII character can be used as a delimiter via the `-d` / `--delimiter` option. Common delimiter characters include:

| Character | Flag Example | Common Format |
|-----------|-------------|---------------|
| `,`       | `-d,`       | CSV           |
| `\t` (tab)| `--tsv`     | TSV           |
| `:`       | `-d:`       | /etc/passwd, colon-separated |
| `;`       | `-d';'`     | European CSV (some locales use `;` instead of `,`) |
| `\|`      | `-d'\|'`    | Pipe-separated values |
| ` ` (space)| `-d' '`    | Space-separated values |

### Tab Delimiter Shorthand

The `--tsv` / `-t` flag is a convenience shorthand for `-d '\t'`. It sets the delimiter to a tab character without requiring shell-specific escape sequences.

The `--tsv` flag and `--delimiter` flag are mutually exclusive. If both are specified, csview produces an error:

```
error: the argument '--tsv' cannot be used with '--delimiter <DELIMITER>'
```

### Delimiter Validation

The delimiter must be exactly one character. csview rejects:
- Empty strings
- Multi-character strings

If an invalid delimiter is provided, csview produces an error message and exits with a non-zero status code.

### CSV Quoting Rules

csview uses the `csv` crate (Rust's standard CSV library by BurntSushi) for parsing, which follows RFC 4180 conventions:

1. **Quoted fields:** A field may be enclosed in double quotes (`"`). This is required when the field contains the delimiter character, a newline, or a double-quote character.

2. **Embedded delimiters:** If a field contains the delimiter character, the entire field must be enclosed in double quotes.
   ```csv
   Name,Description
   Widget,"Small, round, and blue"
   ```

3. **Embedded newlines:** If a field contains a newline character (CR, LF, or CRLF), the entire field must be enclosed in double quotes.
   ```csv
   Name,Address
   Alice,"123 Main St
   Apt 4"
   ```

4. **Embedded quotes:** Double-quote characters within a quoted field are escaped by doubling them.
   ```csv
   Name,Quote
   Alice,"She said ""hello"""
   ```

5. **Leading/trailing whitespace:** Whitespace within fields is preserved as-is. csview does not trim whitespace from field values.

**Example with quoted fields:**

Input (`data.csv`):
```csv
Year,Make,Model,Description,Price
1997,Ford,E350,"ac, abs, moon",3000.00
1999,Chevy,"Venture ""Extended Edition""","",4900.00
1999,Chevy,"Venture ""Extended Edition, Large""",,5000.00
1996,Jeep,Grand Cherokee,"MUST SELL! air, moon roof",4799.00
```

Output:
```
┌──────┬───────┬───────────────────────────────────┬───────────────────────────┬─────────┐
│ Year │ Make  │               Model               │        Description        │  Price  │
├──────┼───────┼───────────────────────────────────┼───────────────────────────┼─────────┤
│ 1997 │ Ford  │ E350                              │ ac, abs, moon             │ 3000.00 │
│ 1999 │ Chevy │ Venture "Extended Edition"        │                           │ 4900.00 │
│ 1999 │ Chevy │ Venture "Extended Edition, Large" │                           │ 5000.00 │
│ 1996 │ Jeep  │ Grand Cherokee                    │ MUST SELL! air, moon roof │ 4799.00 │
└──────┴───────┴───────────────────────────────────┴───────────────────────────┴─────────┘
```

Notice how:
- `"ac, abs, moon"` is displayed as `ac, abs, moon` (quotes removed, embedded comma preserved)
- `"Venture ""Extended Edition"""` is displayed as `Venture "Extended Edition"` (escaped quotes unescaped)
- Empty quoted field `""` and bare empty field `` both render as empty cells

---

## Header Handling

### Default Behavior (Headers Present)

By default, csview treats the first row of the input as a header row. The header row receives distinct formatting:

1. **Alignment:** The header row uses the alignment specified by `--header-align` (default: `Center`), which is independent of the body alignment.

2. **Separator line:** A separator line is drawn between the header row and the first data row (the "second" row separator). The appearance of this separator depends on the active style.

3. **No mid-row separator above header:** The header row is preceded by the top border (if the style includes one) and followed by the header separator. It is never preceded by a mid-row separator.

4. **Header-only tables:** If the input contains only a header row with no data rows, csview renders the header row with the top border and bottom border but omits the header separator. This is because the header separator is only drawn when there are data rows following the header.

**Example (header only):**
```
printf "a,ab,abc" | csview
```

Output:
```
┌───┬────┬─────┐
│ a │ ab │ abc │
└───┴────┴─────┘
```

### No Headers Mode

When `--no-headers` / `-H` is set:

1. All rows are treated as data rows.
2. The body alignment is used for all rows.
3. No header separator is drawn.
4. When combined with `--number` / `-n`, the `#` column header is not shown; instead, line numbers are simply prepended as data.

**Example:**
```
printf "Alice,30,NYC\nBob,25,LA\n" | csview -H
```

Output:
```
┌───────┬────┬─────┐
│ Alice │ 30 │ NYC │
│ Bob   │ 25 │ LA  │
└───────┴────┴─────┘
```

### Header Width Calculation

The header row participates in column width calculation. If a header cell is wider than all corresponding data cells, the column width is determined by the header width:

```
printf "LongHeaderName,X\na,1\n" | csview
```

Output:
```
┌────────────────┬───┐
│ LongHeaderName │ X │
├────────────────┼───┤
│ a              │ 1 │
└────────────────┴───┘
```

---

## Alignment

csview provides independent alignment control for header and body rows.

### Header Alignment (`--header-align`)

Controls the horizontal alignment of text within header cells.

- **Left:** Text is left-justified within the cell, with trailing spaces.
- **Center (default):** Text is centered within the cell, with balanced padding on both sides.
- **Right:** Text is right-justified within the cell, with leading spaces.

### Body Alignment (`--body-align`)

Controls the horizontal alignment of text within data (body) cells.

- **Left (default):** Text is left-justified within the cell.
- **Center:** Text is centered within the cell.
- **Right:** Text is right-justified within the cell.

### Alignment Combinations

Header and body alignment can be set independently, allowing for various visual effects:

**Header left, body right:**
```
printf "Product,Price,Qty\nWidget,9.99,100\nGadget,24.95,50\n" | csview --header-align left --body-align right
```

Output:
```
┌─────────┬───────┬─────┐
│ Product │ Price │ Qty │
├─────────┼───────┼─────┤
│  Widget │  9.99 │ 100 │
│  Gadget │ 24.95 │  50 │
└─────────┴───────┴─────┘
```

**Header right, body center:**
```
printf "Product,Price,Qty\nWidget,9.99,100\nGadget,24.95,50\n" | csview --header-align right --body-align center
```

Output:
```
┌─────────┬───────┬─────┐
│ Product │ Price │ Qty │
├─────────┼───────┼─────┤
│ Widget  │ 9.99  │ 100 │
│ Gadget  │ 24.95 │  50 │
└─────────┴───────┴─────┘
```

**Both center:**
```
printf "Product,Price,Qty\nWidget,9.99,100\nGadget,24.95,50\n" | csview --header-align center --body-align center
```

### Unicode-Aware Alignment

Alignment is performed using Unicode-aware width calculation. CJK characters and emoji, which typically occupy two terminal columns, are correctly accounted for when aligning text. This ensures that columns remain visually aligned even when mixing ASCII and wide characters.

---

## Line Numbers

The `-n` / `--number` (or `--seq`) flag prepends a column of sequential line numbers to the output. This is useful for referencing specific rows in the data.

### Behavior with Headers

When headers are present, the line number column receives the header label `#`. Line numbers for data rows start at 1:

```
printf "Name,Score\nAlice,95\nBob,87\nCarol,92\n" | csview -n
```

Output:
```
┌───┬───────┬───────┐
│ # │ Name  │ Score │
├───┼───────┼───────┤
│ 1 │ Alice │ 95    │
│ 2 │ Bob   │ 87    │
│ 3 │ Carol │ 92    │
└───┴───────┴───────┘
```

### Behavior without Headers

When `--no-headers` is set, there is no `#` label, and line numbers are simply prepended as data in each row:

```
printf "Alice,95\nBob,87\nCarol,92\n" | csview -H -n
```

Output:
```
┌───┬───────┬────┐
│ 1 │ Alice │ 95 │
│ 2 │ Bob   │ 87 │
│ 3 │ Carol │ 92 │
└───┴───────┴────┘
```

### Width Calculation

The width of the line number column adapts to the number of rows. For datasets with more than 9 rows, the column becomes wider to accommodate multi-digit numbers:

```
# 10-row dataset
printf "x\n1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n" | csview -n
```

The `#` column will be wide enough to fit the widest line number (e.g., `10`), ensuring alignment.

### Combining with Other Options

Line numbers can be combined with any style, padding, indent, and alignment options:

```
printf "Name,Score\nAlice,95\nBob,87\n" | csview -n -s ascii -p2 -i2
```

Output:
```
  +-----+---------+---------+
  |  #  |  Name   |  Score  |
  +-----+---------+---------+
  |  1  |  Alice  |  95     |
  +-----+---------+---------+
  |  2  |  Bob    |  87     |
  +-----+---------+---------+
```

---

## Input Handling

### File Input

When a file path is provided as a positional argument, csview opens and reads the file. The file is read as a byte stream and parsed as CSV.

```
csview data.csv
csview /path/to/data.tsv --tsv
```

### Standard Input (stdin)

When no file argument is provided, csview reads from stdin. This allows csview to be used in Unix pipelines:

```
cat data.csv | csview
generate_data | csview --tsv
curl -s https://example.com/data.csv | csview
```

If stdin is connected to a terminal (interactive mode) and no file argument is provided, csview prints an error message and exits:
```
csview: no input file specified (use -h for help)
```

### File Input and stdin Equivalence

Reading from a file and piping the same file's contents via stdin produce identical output:

```
csview data.csv
cat data.csv | csview
```

Both commands produce the same table output.

### RFC 4180 Compliance

csview's CSV parser is based on the `csv` crate (BurntSushi's rust-csv), which provides comprehensive RFC 4180 support:

1. **Quoted fields:** Fields enclosed in double quotes are parsed correctly, with the quotes removed from the output.

2. **Escaped quotes:** Double-quote characters within quoted fields are escaped by doubling them (`""` becomes `"`).

3. **Embedded newlines:** Newline characters within quoted fields are preserved. However, csview renders each record as a single table row, so embedded newlines within a field are displayed as part of the cell content.

4. **Various line endings:** csview handles LF (`\n`), CR (`\r`), and CRLF (`\r\n`) line endings transparently.

5. **BOM handling:** The CSV parser can handle UTF-8 BOM (Byte Order Mark, U+FEFF) at the beginning of files. The BOM is stripped and does not appear in the output.

### Encoding Requirements

csview requires UTF-8 encoded input. If the input contains bytes that are not valid UTF-8, csview prints an error message to stderr:

```
[error] input is not utf8 encoded
```

For files in other encodings, convert to UTF-8 first using `iconv`:

```
iconv -f iso-8859-1 -t UTF8//TRANSLIT input.csv | csview
```

Or check the encoding with `file`:
```
file -i data.csv
```

### Row Length Validation

csview enforces that all rows have the same number of fields. If a data row has a different number of fields than expected (based on the first row or header), csview produces an error:

```
[error] unequal lengths at (byte: N, line: N, record: N): expected length is X, but got Y
```

This strict validation helps catch malformed CSV files early.

---

## Output Formatting

### Column Width Calculation

csview automatically calculates the optimal width for each column based on the content of the cells. The width of a column is determined by the widest cell in that column (including the header, if present).

Width calculation is Unicode-aware: CJK characters and emoji that occupy two terminal columns are counted as width 2, while standard ASCII characters are counted as width 1. This ensures proper visual alignment in the terminal.

The number of rows examined for width calculation is controlled by the `--sniff` option (default: 1000). Only the first N rows (plus the header) are used to determine column widths.

### Padding

Padding adds space characters on both sides of every cell's content, between the content and the column separator. Padding is configurable via `--padding` / `-p` (default: 1).

The total width of a column in the rendered output is:
```
column_width = content_width + (padding * 2)
```

Where `content_width` is the maximum width of any cell in the column.

### Indentation

Indentation adds leading space characters before every line of the table output, including border and separator lines. Indentation is configurable via `--indent` / `-i` (default: 0).

### Text Truncation

When a cell's content is wider than the calculated column width (which can happen when `--sniff` is set to a value smaller than the total number of rows), the content is truncated using Unicode-aware truncation. The `unicode-truncate` crate ensures that truncation occurs at character boundaries and does not produce partial multi-byte characters.

### Output Destination

csview writes its output to stdout. On Unix systems with the `pager` feature enabled, when stdout is a terminal, csview automatically pipes output through a pager program (default: `less -SF`). This can be disabled with `-P` / `--disable-pager`.

---

## Pager Support

On Unix systems, csview includes built-in pager support (enabled by default via the `pager` Cargo feature). When stdout is connected to a terminal (not a pipe), csview automatically routes its output through a pager for comfortable viewing of large tables.

### Default Pager

The default pager is `less` with the following flags:
- `-S`: Chop long lines (horizontal scrolling instead of wrapping)
- `-F`: Quit if the entire output fits on one screen

### Custom Pager

The pager can be customized via the `CSVIEW_PAGER` environment variable:

```
CSVIEW_PAGER="less -RS" csview data.csv
CSVIEW_PAGER="more" csview data.csv
CSVIEW_PAGER="bat" csview data.csv
```

### Disabling the Pager

The pager can be disabled in several ways:

1. Using the `-P` / `--disable-pager` flag:
   ```
   csview -P data.csv
   ```

2. Piping output to another command (stdout is not a terminal):
   ```
   csview data.csv | head
   csview data.csv > output.txt
   ```

---

## Unicode Support

csview provides comprehensive Unicode support, with particular emphasis on correctly handling characters that have non-standard terminal widths.

### CJK Characters

CJK (Chinese, Japanese, Korean) characters typically occupy two terminal columns. csview uses the `unicode-width` crate with CJK-aware width calculation (`width_cjk`) to correctly determine the display width of these characters.

**Example:**
```
printf "Name,City\n李磊,北京\nJohn,NYC\n" | csview
```

Output:
```
┌──────┬──────┐
│ Name │ City │
├──────┼──────┤
│ 李磊 │ 北京 │
│ John │ NYC  │
└──────┴──────┘
```

Notice how `李磊` (4 terminal columns) and `北京` (4 terminal columns) are correctly aligned with `John` (4 terminal columns) and `NYC` (3 terminal columns, padded with one space).

### Emoji

Emoji characters, which also typically occupy two terminal columns, are handled correctly:

**Example:**
```
printf "Icon,Label\n💍,Ring\n🎉,Party\n" | csview
```

Output:
```
┌──────┬───────┐
│ Icon │ Label │
├──────┼───────┤
│ 💍   │ Ring  │
│ 🎉   │ Party │
└──────┴───────┘
```

### Mixed-Width Content

csview correctly handles cells containing a mix of ASCII and wide characters:

**Example:**
```
printf "Name,Location\n李磊(Jack),四川省成都市\nBob,NYC\n" | csview
```

Output:
```
┌────────────┬──────────────┐
│    Name    │   Location   │
├────────────┼──────────────┤
│ 李磊(Jack) │ 四川省成都市 │
│ Bob        │ NYC          │
└────────────┴──────────────┘
```

### Zero-Width Joiners

Some Unicode sequences, such as those using zero-width joiners (ZWJ), may affect display width in terminal-specific ways. csview calculates widths based on the Unicode standard widths reported by the `unicode-width` crate, which may differ from the actual rendering in certain terminal emulators.

### Latin Extended Characters

Latin extended characters (accented characters, diacritics, etc.) typically occupy one terminal column each:

```
printf "Name,City\nRene,Montreal\nJose,Bogota\n" | csview
```

---

## Error Handling

csview handles various error conditions and produces informative error messages on stderr.

### Missing File

When the specified file does not exist:

```
$ csview nonexistent.csv
csview: No such file or directory (os error 2)
```

Exit code: 1

### Permission Denied

When the specified file is not readable:

```
$ csview unreadable.csv
[error] io error: Permission denied (os error 13)
```

Exit code: defined by `exitcode::IOERR`

### No Input Specified

When no file argument is given and stdin is a terminal:

```
$ csview
csview: no input file specified (use -h for help)
```

Exit code: 1

### Invalid UTF-8

When the input contains bytes that are not valid UTF-8:

```
$ csview binary_data.csv
[error] input is not utf8 encoded
```

Exit code: defined by `exitcode::DATAERR`

### Unequal Row Lengths

When a data row has a different number of fields than the header or first row:

```
$ printf "a,b,c\n1,2\n" | csview
[error] unequal lengths at (byte: 10, line: 2, record: 1): expected length is 3, but got 2
```

Exit code: defined by `exitcode::DATAERR`

This also applies when a row has too many fields:

```
$ printf "a,b\n1,2,3\n" | csview
[error] unequal lengths at (byte: 8, line: 2, record: 1): expected length is 2, but got 3
```

### Invalid Style Name

When an invalid style name is specified:

```
$ csview -s invalid data.csv
error: invalid value 'invalid' for '--style <STYLE>'
  [possible values: none, ascii, ascii2, sharp, rounded, reinforced, markdown, grid]
```

Exit code: 2

### Invalid Delimiter

When an invalid delimiter is specified (empty string or multi-character):

```
$ csview -d '' data.csv
error: ...
```

Exit code: 2

### Mutually Exclusive Options

When both `--tsv` and `--delimiter` are specified:

```
$ csview --tsv -d';' data.csv
error: the argument '--tsv' cannot be used with '--delimiter <DELIMITER>'
```

Exit code: 2

### Unknown Flags

When an unknown flag is provided:

```
$ csview --unknown data.csv
error: unexpected argument '--unknown' found
```

Exit code: 2

### Broken Pipe

When the output pipe is closed prematurely (e.g., when piping to `head`), csview handles the `BrokenPipe` error gracefully and exits with exit code 0, rather than printing an error message.

```
csview large_data.csv | head -5
```

---

## Exit Codes

| Exit Code | Condition |
|-----------|-----------|
| 0         | Success, or broken pipe (output consumer closed) |
| 1         | General error (file not found, no input specified) |
| 2         | CLI argument error (invalid flag, invalid value, mutually exclusive options) |
| 65        | Data error (`exitcode::DATAERR` -- invalid UTF-8, unequal row lengths) |
| 74        | I/O error (`exitcode::IOERR` -- permission denied, read error) |

---

## Performance

csview is written in Rust and optimized for high performance and low memory usage.

### Benchmarks

Based on benchmarks from the csview project (using `hyperfine`):

**Small file** (10 rows, 4 columns, 695 bytes):

| Tool    | Mean Time | Memory  |
|---------|-----------|---------|
| csview  | 0.3ms     | 2.4 MB  |
| column  | 1.3ms     | 2.4 MB  |
| xsv     | 2.0ms     | 3.9 MB  |
| csvlook | 148.1ms   | 27.3 MB |

**Medium file** (10,000 rows, 10 columns, 624 KB):

| Tool    | Mean Time | Memory  |
|---------|-----------|---------|
| csview  | 17ms      | 2.8 MB  |
| xsv     | 31ms      | 4.4 MB  |
| column  | 52ms      | 9.9 MB  |
| csvlook | 2,664ms   | 46.8 MB |

**Large file** (1,000,000 rows, 10 columns, 61 MB):

| Tool    | Mean Time | Memory    |
|---------|-----------|-----------|
| csview  | 1,686ms   | 2.8 MB   |
| xsv     | 2,912ms   | 4.4 MB   |
| column  | 5,777ms   | 767.6 MB |
| csvlook | 20,665ms  | 1,105 MB |

### Memory Efficiency

csview achieves its low memory footprint through its sniffing mechanism. By default, only the first 1,000 rows are buffered in memory for width calculation. After the sniffed rows are consumed, subsequent rows are read and rendered in a streaming fashion, one at a time. This means csview uses approximately constant memory regardless of file size (after the sniff buffer).

With `--sniff 0` (unlimited), all rows are buffered in memory, which increases memory usage proportionally to the file size.

### Buffered Output

csview uses `BufWriter` to wrap stdout, reducing the number of system calls for output and improving write performance, especially for large tables.

---

## Edge Cases

### Empty Files

When an empty file (zero bytes) is provided, csview produces no output and exits successfully (exit code 0).

```
$ touch empty.csv && csview empty.csv
```

No output is produced.

### Empty stdin

When stdin is empty (e.g., from an empty pipe), csview produces no output and exits successfully.

```
$ echo -n | csview
```

### Files with Only Headers

When the input contains only a header row and no data rows, csview renders the header enclosed by the top and bottom borders, without the header separator:

```
$ printf "Name,Age,City" | csview
```

Output:
```
┌──────┬─────┬──────┐
│ Name │ Age │ City │
└──────┴─────┴──────┘
```

### Single Column CSV

csview correctly handles single-column CSV data:

```
$ printf "Name\nAlice\nBob\n" | csview
```

Output:
```
┌───────┐
│ Name  │
├───────┤
│ Alice │
│ Bob   │
└───────┘
```

### Single Row

When the input has only one data row (plus an optional header):

```
$ printf "Name,Age\nAlice,30\n" | csview
```

Output:
```
┌───────┬─────┐
│ Name  │ Age │
├───────┼─────┤
│ Alice │ 30  │
└───────┴─────┘
```

### Empty Fields

Empty fields are rendered as blank cells:

```
$ printf "a,b,c\n1,,3\n,2,\n" | csview
```

Output:
```
┌───┬───┬───┐
│ a │ b │ c │
├───┼───┼───┤
│ 1 │   │ 3 │
│   │ 2 │   │
└───┴───┴───┘
```

### Fields with Embedded Newlines

Fields containing newline characters within double quotes are parsed correctly. The newline characters become part of the cell content:

```csv
Name,Address
Alice,"123 Main St
Apt 4"
Bob,"456 Oak Ave"
```

The embedded newline in Alice's address is preserved in the parsed field.

### Very Long Cell Content

csview handles arbitrarily long cell content by expanding the column width to accommodate the longest cell. When the `--sniff` limit is set lower than the total number of rows, cells in later rows that exceed the calculated column width will be truncated to fit.

### Many Columns

csview handles tables with many columns. When the total table width exceeds the terminal width, the pager (when enabled) provides horizontal scrolling via `less -S`.

### Windows Line Endings (CRLF)

csview handles CRLF (`\r\n`) line endings transparently. Files created on Windows are parsed correctly without any special options:

```
$ printf "Name,Age\r\nAlice,30\r\nBob,25\r\n" | csview
```

Produces the same output as with LF line endings.

### Mixed Line Endings

Files with inconsistent line endings (some lines ending with LF, others with CRLF) are handled correctly.

### Trailing Delimiters

A trailing delimiter on a line creates an additional empty field. For example, a line ending with `,` has an empty last field:

```
$ printf "a,b,c\n1,2,\n" | csview
```

The last cell in the second row will be empty.

### Leading Delimiters

Similarly, a leading delimiter creates an empty first field:

```
$ printf "a,b,c\n,2,3\n" | csview
```

The first cell in the second row will be empty.

### BOM (Byte Order Mark)

UTF-8 files that begin with a BOM (byte sequence `EF BB BF`, representing U+FEFF) are handled correctly. The BOM is stripped and does not appear in the output or affect column width calculations.

### Whitespace in Fields

Whitespace within fields is preserved as-is. Leading and trailing spaces are not trimmed:

```
$ printf "a,b\n  hello  , world \n" | csview
```

The spaces within the fields are preserved in the output.

---

## CSV Parsing Details

### RFC 4180 Overview

RFC 4180 defines the standard format for CSV files. csview's parser (via the `csv` crate) implements this standard with the following rules:

1. Each record is on a separate line, delimited by a line break (CRLF or LF).
2. The last record in the file may or may not have an ending line break.
3. The first record may optionally be a header record (controlled by `--no-headers`).
4. Fields are separated by the delimiter character (default: comma).
5. Each field may or may not be enclosed in double quotes.
6. Fields containing line breaks, double quotes, or the delimiter must be enclosed in double quotes.
7. A double-quote within a quoted field is escaped by preceding it with another double-quote.

### Quote Handling

csview follows standard CSV quote handling:

**Simple quoted field:**
```csv
"hello world"
```
Parsed as: `hello world`

**Quoted field with embedded delimiter:**
```csv
"hello, world"
```
Parsed as: `hello, world`

**Quoted field with escaped quotes:**
```csv
"he said ""hi"""
```
Parsed as: `he said "hi"`

**Quoted field with embedded newline:**
```csv
"line 1
line 2"
```
Parsed as: `line 1\nline 2` (with literal newline)

**Empty quoted field:**
```csv
""
```
Parsed as: (empty string)

### Field Variations

All of the following represent valid ways to encode an empty field:

```csv
a,,c        # bare empty field
a,"",c      # quoted empty field
```

Both produce the same result: the middle field is empty.

### Trailing Newlines

A trailing newline at the end of the file does not create an additional empty record. This is consistent with RFC 4180 and standard CSV behavior.

```csv
a,b
1,2
```

And:

```csv
a,b
1,2

```

Both produce the same output (one header row and one data row).

---

## Environment Variables

### `CSVIEW_PAGER`

Controls which pager program csview uses when stdout is a terminal. When this variable is set, csview uses the specified command as the pager instead of the default `less`.

```
export CSVIEW_PAGER="less -RS"
export CSVIEW_PAGER="more"
export CSVIEW_PAGER="bat --paging=always"
```

When this variable is not set, csview defaults to `less` with the `-SF` flags.

### `NO_COLOR`

While csview does not add color to its table output (the table borders and content are rendered in the terminal's default color), the help output generated by clap may use ANSI color codes. The `NO_COLOR` convention may affect the help output styling, depending on the clap version.

---

## Comparison with Similar Tools

### csview vs. xsv

[xsv](https://github.com/BurntSushi/xsv) is a comprehensive CSV toolkit that includes a `table` subcommand for pretty-printing. Key differences:

| Feature          | csview                        | xsv table                  |
|------------------|-------------------------------|-----------------------------|
| Primary purpose  | CSV viewing/formatting        | CSV analysis and manipulation |
| Table styles     | 8 styles                      | Single style                |
| CJK/emoji support| Correct width calculation     | ASCII-only width            |
| Alignment control| Header and body independently | No                          |
| Line numbers     | Built-in (`-n`)               | Requires `xsv select`       |
| Performance      | Faster (0.3ms vs 2.0ms small) | Slower                      |
| Memory           | Lower (2.4MB vs 3.9MB)        | Higher                      |
| CSV analysis     | View only                     | Full suite (select, join, sort, etc.) |

### csview vs. column

The Unix `column` command (from util-linux) provides basic columnar formatting:

| Feature          | csview                        | column -t                   |
|------------------|-------------------------------|-----------------------------|
| Table borders    | Multiple styles               | No borders                  |
| CSV parsing      | Full RFC 4180                  | Basic delimiter splitting   |
| Quoted fields    | Correct handling              | No quote awareness          |
| CJK support      | Correct width calculation     | Varies by implementation    |
| Performance      | Faster                        | Slower for large files      |
| Memory           | Constant (with sniffing)      | Proportional to file size   |

### csview vs. csvlook

[csvlook](https://csvkit.readthedocs.io/) is part of the csvkit Python toolkit:

| Feature          | csview                        | csvlook                     |
|------------------|-------------------------------|-----------------------------|
| Language         | Rust                          | Python                      |
| Performance      | Very fast (0.3ms small)       | Slow (148ms small)          |
| Memory           | Very low (2.4MB)              | High (27.3MB)               |
| Table styles     | 8 styles                      | Single style                |
| Installation     | Single binary                 | Python package              |

### csview vs. miller (mlr)

[miller](https://github.com/johnkerl/miller) is a Swiss-army knife for data processing:

| Feature          | csview                        | miller                      |
|------------------|-------------------------------|-----------------------------|
| Primary purpose  | CSV viewing                   | Data processing             |
| Table formatting | Multiple styles               | Limited                     |
| Data manipulation| No                            | Full DSL                    |
| Performance      | Optimized for viewing         | Optimized for processing    |

### csview vs. prettytable / tabulate

Python libraries like `prettytable` and `tabulate` offer similar table formatting but as library APIs, not standalone CLI tools. csview provides comparable visual output with significantly better performance due to being a compiled Rust binary.

---

## Practical Usage Examples

### Viewing /etc/passwd

The `/etc/passwd` file uses colon (`:`) as a delimiter and has no header row:

```
head -5 /etc/passwd | csview -H -d:
```

Output:
```
┌────────────────────────┬───┬───────┬───────┬────────────────────────────┬─────────────────┐
│ root                   │ x │ 0     │ 0     │                            │ /root           │
│ bin                    │ x │ 1     │ 1     │                            │ /               │
│ daemon                 │ x │ 2     │ 2     │                            │ /               │
│ mail                   │ x │ 8     │ 12    │                            │ /var/spool/mail │
│ ftp                    │ x │ 14    │ 11    │                            │ /srv/ftp        │
└────────────────────────┴───┴───────┴───────┴────────────────────────────┴─────────────────┘
```

### Generating Markdown Tables

Convert a CSV file to a Markdown table for documentation:

```
csview -s markdown data.csv > table.md
```

### Viewing TSV Files with Line Numbers

```
csview --tsv -n data.tsv
```

### Compact View with No Padding

For a dense view with minimal whitespace:

```
csview -p0 data.csv
```

### Indented Table for Embedding

When embedding table output in other text:

```
csview -i4 -s rounded data.csv
```

### Right-Aligned Numeric Data

For tables with numeric data where right-alignment improves readability:

```
csview --body-align right data.csv
```

### Viewing Large Files Efficiently

For very large files, reduce the sniff limit for faster initial rendering:

```
csview --sniff 100 huge_data.csv
```

Or disable the pager and pipe to head for a quick peek:

```
csview -P huge_data.csv | head -20
```

### Pipeline Usage

csview integrates well with Unix pipelines:

```
# View first 10 rows of a CSV
head -11 data.csv | csview

# View output of a command as a table
docker ps --format "{{.Names}},{{.Status}},{{.Ports}}" | csview -H

# Convert between delimiters and view
tr ';' ',' < european.csv | csview

# Combine with jq for JSON-to-table conversion
cat data.json | jq -r '.[] | [.name, .age, .city] | @csv' | csview -H
```

### Full-Grid View for Small Datasets

For small datasets where visual separation between every row aids readability:

```
csview -s grid small_data.csv
```

### ASCII-Only Environments

For terminals or environments that do not support Unicode:

```
csview -s ascii data.csv
```

### Clean Columnar Output

For output similar to `column -t` but with proper CSV parsing:

```
csview -s none data.csv
```

---

## Detailed Style Reference

This section provides a comprehensive visual reference for every style, showing the exact characters used and their positions in the table structure.

### Sharp Style -- Character Map

```
Position:   TL  TOP  TJ  TOP  TR
            ┌────────┬────────┐
Borders:    LB  CELL  CS  CELL  RB
            │  data  │  data  │
Junction:   LJ  HDR  CJ  HDR  RJ
            ├────────┼────────┤
Borders:    LB  CELL  CS  CELL  RB
            │  data  │  data  │
Position:   BL  BOT  BJ  BOT  BR
            └────────┴────────┘

TL=┌ TOP=─ TJ=┬ TR=┐
LB=│ CS=│  RB=│
LJ=├ HDR=─ CJ=┼ RJ=┤
BL=└ BOT=─ BJ=┴ BR=┘
```

### Rounded Style -- Character Map

```
            ╭────────┬────────╮
            │  head  │  head  │
            ├────────┼────────┤
            │  data  │  data  │
            ╰────────┴────────╯

Differs from Sharp only in corners:
TL=╭ TR=╮ BL=╰ BR=╯
```

### Reinforced Style -- Character Map

```
            ┏────────┬────────┓
            │  head  │  head  │
            ├────────┼────────┤
            │  data  │  data  │
            ┗────────┴────────┛

Differs from Sharp only in corners:
TL=┏ TR=┓ BL=┗ BR=┛
```

### Grid Style -- Character Map

```
            ┌────────┬────────┐
            │  head  │  head  │
            ├────────┼────────┤
            │  data  │  data  │
            ├────────┼────────┤    <-- mid-row separator (same chars as header sep)
            │  data  │  data  │
            └────────┴────────┘

Same characters as Sharp, but adds mid-row separators between every data row.
```

### ASCII Style -- Character Map

```
            +--------+--------+
            |  head  |  head  |
            +--------+--------+
            |  data  |  data  |
            +--------+--------+

All borders use ASCII: + for junctions/corners, - for horizontal, | for vertical.
```

### Ascii2 Style -- Character Map

```
             head   |  head
            --------+--------
             data   |  data
             data   |  data

No top/bottom borders. No left/right borders.
Left and right column separators are spaces.
Middle column separator is |.
Only the header separator row is present, using - and +.
```

### Markdown Style -- Character Map

```
            |  head  |  head  |
            |--------|--------|
            |  data  |  data  |
            |  data  |  data  |

No top/bottom borders.
Left/right/middle column separators are all |.
Only the header separator row is present, using - and |.
```

### None Style -- Character Map

```
             head    head
             data    data
             data    data

No borders, no separators, no column dividers.
Content is space-padded to column widths.
```

---

## Advanced Topics

### Sniff Behavior in Detail

The sniff mechanism in csview works as follows:

1. Read the header row (if headers are enabled).
2. Initialize column widths from header cell widths.
3. Read up to `--sniff` data rows, updating column widths to the maximum seen width.
4. Buffer all sniffed rows in memory.
5. Begin rendering: output the top border, header row, header separator.
6. Output all buffered (sniffed) rows.
7. Continue reading remaining rows from the input source and output them immediately (streaming).

This means that for rows beyond the sniff limit, if a cell is wider than the calculated column width, the cell content will be truncated to fit the column. The truncation is Unicode-aware and uses the `unicode_truncate` crate.

When `--sniff 0` is specified, the limit is set to `usize::MAX` (effectively unlimited), causing all rows to be buffered before rendering begins. This guarantees optimal column widths but requires proportionally more memory.

### Width Calculation for CJK Characters

csview uses `UnicodeWidthStr::width_cjk` for width calculation. This function returns the number of terminal columns a string occupies, with CJK characters counted as width 2. This is the "CJK width" variant, which treats ambiguous-width characters as wide (2 columns) according to East Asian Width properties.

Standard ASCII characters have a width of 1. Most CJK ideographs have a width of 2. Most emoji have a width of 2. Combining characters and zero-width characters have a width of 0.

### Content Alignment Implementation

Alignment is performed using the `unicode_truncate` crate's `unicode_pad` function, which:

1. Calculates the actual display width of the cell content.
2. Determines the required padding on each side based on the alignment.
3. For left alignment: content is followed by spaces.
4. For right alignment: content is preceded by spaces.
5. For center alignment: spaces are distributed evenly on both sides (with the extra space on the right if the total padding is odd).
6. If the content exceeds the column width, it is truncated at a character boundary.

### Multiline Cell Rendering

While csview's CSV parser correctly handles fields containing embedded newlines (within double quotes), the table renderer treats each record as a single table row. Embedded newlines within a field become part of the cell's text content. The rendering behavior of these embedded newlines depends on the terminal: they may cause the cell content to span multiple terminal lines, which can disrupt the table layout.

For best results with multiline fields, the data should be preprocessed to replace embedded newlines with a visual indicator (e.g., `\n` literal or a space).

### Streaming Output

After the sniff phase, csview processes remaining rows in a streaming fashion. Each row is:

1. Read from the input source.
2. Parsed as a CSV record.
3. Formatted as a table row using the pre-calculated column widths.
4. Written to the output buffer.

This streaming approach means that csview can handle files much larger than available memory (with the default `--sniff 1000`), as only the sniff buffer and one row at a time need to be in memory.

### Broken Pipe Handling

csview handles the `BrokenPipe` error specially. When the output consumer (e.g., `head`, `less`, or another piped command) closes the pipe before csview finishes writing, the resulting `BrokenPipe` I/O error is caught and csview exits with exit code 0 (success). This prevents spurious error messages when using csview in pipelines:

```
csview huge_data.csv | head -5
```

Without this handling, the operating system would deliver a `SIGPIPE` signal or return a `BrokenPipe` error, which would cause csview to print an error message.

---

## Installation

### Package Managers

**Arch Linux (AUR):**
```
yay -S csview
```

**macOS (Homebrew):**
```
brew install csview
```

**NetBSD (pkgsrc):**
```
pkgin install csview
```

**Windows (Scoop):**
```
scoop install csview
```

### Pre-Built Binaries

Pre-built binaries for various architectures are available on the [GitHub releases page](https://github.com/wfxr/csview/releases). The `musl` variant is statically linked and recommended for maximum portability.

### From Source

With Rust toolchain installed:

```
cargo install --locked csview
```

Or clone the repository and build:

```
git clone https://github.com/wfxr/csview.git
cd csview
cargo build --release
```

The binary will be located at `target/release/csview`.

---

## Frequently Asked Questions

### How do I handle non-UTF-8 files?

csview requires UTF-8 input. For files in other encodings, use `iconv` to convert:

```
# Check the encoding
file -i data.csv

# Convert and pipe to csview
iconv -f iso-8859-1 -t UTF8//TRANSLIT data.csv | csview
```

### Why does my table look misaligned?

Table misalignment can occur due to:

1. **Terminal font:** Ensure you are using a monospaced font. Proportional fonts will cause misalignment.
2. **Unicode rendering:** Different terminal emulators may render CJK characters or emoji at different widths. csview calculates widths according to the Unicode standard, but some terminals may deviate.
3. **Sniff limit:** If `--sniff` is set too low, columns may be sized based on early rows and later rows with wider content may be truncated.

### Can I select specific columns?

The version at commit 8ac4de0 does not include a column selection feature. To select specific columns, preprocess the data using tools like `xsv select`, `cut`, or `awk`:

```
xsv select 1,3 data.csv | csview
cut -d, -f1,3 data.csv | csview
```

### Can I sort the data?

csview is a viewer, not a data manipulation tool. For sorting, preprocess with `sort`, `xsv sort`, or `miller`:

```
xsv sort -s Age data.csv | csview
```

### How do I use csview with TSV files?

Use the `--tsv` or `-t` flag:

```
csview --tsv data.tsv
csview -t data.tsv
```

### Why is the default style `sharp` and not `ascii`?

The Sharp style provides a cleaner, more modern appearance using Unicode box-drawing characters, which are widely supported by modern terminal emulators. The ASCII style is available for environments that lack Unicode support.

### How does csview compare to spreadsheet applications?

csview is a command-line viewer optimized for quick inspection of CSV data. For editing, formulas, or complex data manipulation, use a spreadsheet application. csview excels at:

- Quick data inspection without leaving the terminal
- Embedding formatted tables in documentation
- Processing pipeline output
- Handling large files efficiently

---

## Technical Details

### Dependencies

csview is built on the following Rust crates:

- **csv** (1.3): CSV parsing library by BurntSushi, providing RFC 4180-compliant parsing.
- **clap** (4.x): Command-line argument parser with derive macros, providing help generation, value validation, and flag conflict detection.
- **anyhow** (1.0): Error handling library for convenient error propagation.
- **unicode-width** (0.x): Provides Unicode-aware string width calculation, essential for correct alignment of CJK and emoji characters.
- **unicode-truncate** (2.0): Provides Unicode-aware string truncation and padding with alignment support.
- **itertools** (0.14): Iterator utilities, used for interspersing column separators.
- **exitcode** (1.1): Standard exit code constants (DATAERR, IOERR, etc.).
- **pager** (0.16, optional, Unix only): Pager integration for automatic output paging.

### Build Configuration

csview uses Release profile optimizations:
- **LTO** (Link-Time Optimization): Enabled for smaller binary size and better performance.
- **Codegen units**: Set to 1 for maximum optimization (at the cost of longer compile times).

### Feature Flags

- **pager** (default): Enables automatic pager support on Unix systems. Can be disabled with `--no-default-features` during build.

---

## Glossary

- **CSV**: Comma-Separated Values, a plain text format for tabular data.
- **TSV**: Tab-Separated Values, a variant of CSV using tab characters as delimiters.
- **RFC 4180**: The formal specification for the CSV format, published by the IETF.
- **CJK**: Chinese, Japanese, Korean -- character sets that use ideographic characters occupying two terminal columns.
- **BOM**: Byte Order Mark, a Unicode character (U+FEFF) sometimes placed at the beginning of a file to indicate byte order.
- **Sniffing**: The process of reading ahead in a file to determine characteristics (column widths, delimiter type, etc.).
- **Pager**: A program (like `less` or `more`) that displays output one screenful at a time, allowing scrolling.
- **Box-drawing characters**: Unicode characters (U+2500--U+257F) designed for drawing lines, borders, and tables in text.
- **Monospaced font**: A font where every character occupies the same horizontal space, essential for terminal-based table alignment.
- **Wide character**: A character that occupies two terminal columns (e.g., CJK ideographs, most emoji).
- **Zero-width joiner (ZWJ)**: A Unicode character (U+200D) used to combine multiple characters into a single visual glyph (e.g., emoji sequences).

---

## Appendix A: All Styles Side by Side

Using sample data `Name,Age,City\nAlice,30,NYC\nBob,25,LA\nCarol,28,SF`:

**Sharp (default):**
```
┌───────┬─────┬──────┐
│ Name  │ Age │ City │
├───────┼─────┼──────┤
│ Alice │ 30  │ NYC  │
│ Bob   │ 25  │ LA   │
│ Carol │ 28  │ SF   │
└───────┴─────┴──────┘
```

**Rounded:**
```
╭───────┬─────┬──────╮
│ Name  │ Age │ City │
├───────┼─────┼──────┤
│ Alice │ 30  │ NYC  │
│ Bob   │ 25  │ LA   │
│ Carol │ 28  │ SF   │
╰───────┴─────┴──────╯
```

**Reinforced:**
```
┏───────┬─────┬──────┓
│ Name  │ Age │ City │
├───────┼─────┼──────┤
│ Alice │ 30  │ NYC  │
│ Bob   │ 25  │ LA   │
│ Carol │ 28  │ SF   │
┗───────┴─────┴──────┛
```

**ASCII:**
```
+-------+-----+------+
| Name  | Age | City |
+-------+-----+------+
| Alice | 30  | NYC  |
| Bob   | 25  | LA   |
| Carol | 28  | SF   |
+-------+-----+------+
```

**Ascii2:**
```
 Name  | Age | City
-------+-----+------
 Alice | 30  | NYC
 Bob   | 25  | LA
 Carol | 28  | SF
```

**Markdown:**
```
| Name  | Age | City |
|-------|-----|------|
| Alice | 30  | NYC  |
| Bob   | 25  | LA   |
| Carol | 28  | SF   |
```

**Grid:**
```
┌───────┬─────┬──────┐
│ Name  │ Age │ City │
├───────┼─────┼──────┤
│ Alice │ 30  │ NYC  │
├───────┼─────┼──────┤
│ Bob   │ 25  │ LA   │
├───────┼─────┼──────┤
│ Carol │ 28  │ SF   │
└───────┴─────┴──────┘
```

**None:**
```
 Name   Age  City
 Alice  30   NYC
 Bob    25   LA
 Carol  28   SF
```

---

## Appendix B: Flag Equivalence Forms

Each flag in csview can be specified in multiple equivalent ways. The following forms are all equivalent for flags that take a value:

**Short flag with attached value:**
```
csview -d,
csview -p1
csview -smarkdown
```

**Short flag with separate value:**
```
csview -d ,
csview -p 1
csview -s markdown
```

**Long flag with separate value:**
```
csview --delimiter ,
csview --padding 1
csview --style markdown
```

**Long flag with equals sign:**
```
csview --delimiter=,
csview --padding=1
csview --style=markdown
```

For boolean flags (no value), only the flag itself is needed:
```
csview -H              # short form
csview --no-headers    # long form
csview -t              # short form
csview --tsv           # long form
csview -n              # short form
csview --number        # long form
csview --seq           # alias for --number
```

Flags can appear before or after the positional file argument:
```
csview -H data.csv      # flags before file
csview data.csv -H      # flags after file
csview -H -t data.csv   # multiple flags before file
```

Multiple short boolean flags cannot be combined into a single dash group in csview's current implementation. Each flag must be specified separately:
```
csview -H -t -n data.csv    # correct
```

---

## Appendix C: Rendering Algorithm

csview's table rendering follows this algorithm:

1. **Parse arguments:** Parse CLI arguments using clap.
2. **Open input:** Open the file or stdin as a byte stream reader.
3. **Configure CSV reader:** Set delimiter, header mode, and create a `csv::Reader`.
4. **Sniff widths:**
   a. Read the header (if present) and initialize column widths.
   b. Read up to N data rows (sniff limit), updating column widths.
   c. Buffer all sniffed rows.
   d. If line numbers are enabled, insert a `#` column width.
5. **Render top border:** Write the top row separator (if the style includes one).
6. **Render header:** If headers are present, write the header row with header alignment.
7. **Render header separator:** If headers are present and there are data rows, write the second row separator.
8. **Render data rows:**
   a. Yield buffered (sniffed) rows first.
   b. Continue reading from the input source.
   c. For each row, write the row with body alignment.
   d. Between data rows, write mid-row separators (if the style includes them).
9. **Render bottom border:** Write the bottom row separator (if the style includes one).
10. **Flush output:** Flush the BufWriter to ensure all output is written.

---

## Appendix D: Sample Datasets and Outputs

### Dataset 1: Product Inventory

Input (`products.csv`):
```csv
Product,Category,Price,Stock,Supplier
Widget A,Electronics,29.99,150,Acme Corp
Gadget B,Electronics,49.99,75,Beta Inc
Tool C,Hardware,15.50,200,Gamma LLC
Part D,Hardware,8.25,500,Delta Co
Service E,Software,99.00,999,Epsilon Ltd
```

Default output:
```
csview products.csv
```

```
┌───────────┬─────────────┬───────┬───────┬─────────────┐
│ Product   │  Category   │ Price │ Stock │  Supplier   │
├───────────┼─────────────┼───────┼───────┼─────────────┤
│ Widget A  │ Electronics │ 29.99 │ 150   │ Acme Corp   │
│ Gadget B  │ Electronics │ 49.99 │ 75    │ Beta Inc    │
│ Tool C    │ Hardware    │ 15.50 │ 200   │ Gamma LLC   │
│ Part D    │ Hardware    │ 8.25  │ 500   │ Delta Co    │
│ Service E │ Software    │ 99.00 │ 999   │ Epsilon Ltd │
└───────────┴─────────────┴───────┴───────┴─────────────┘
```

With line numbers and right-aligned body:
```
csview -n --body-align right products.csv
```

```
┌───┬───────────┬─────────────┬───────┬───────┬─────────────┐
│ # │  Product  │  Category   │ Price │ Stock │  Supplier   │
├───┼───────────┼─────────────┼───────┼───────┼─────────────┤
│ 1 │  Widget A │ Electronics │ 29.99 │   150 │   Acme Corp │
│ 2 │  Gadget B │ Electronics │ 49.99 │    75 │    Beta Inc │
│ 3 │    Tool C │    Hardware │ 15.50 │   200 │   Gamma LLC │
│ 4 │    Part D │    Hardware │  8.25 │   500 │    Delta Co │
│ 5 │ Service E │    Software │ 99.00 │   999 │ Epsilon Ltd │
└───┴───────────┴─────────────┴───────┴───────┴─────────────┘
```

As a Markdown table:
```
csview -s markdown products.csv
```

```
| Product   |  Category   | Price | Stock |  Supplier   |
|-----------|-------------|-------|-------|-------------|
| Widget A  | Electronics | 29.99 | 150   | Acme Corp   |
| Gadget B  | Electronics | 49.99 | 75    | Beta Inc    |
| Tool C    | Hardware    | 15.50 | 200   | Gamma LLC   |
| Part D    | Hardware    | 8.25  | 500   | Delta Co    |
| Service E | Software    | 99.00 | 999   | Epsilon Ltd |
```

### Dataset 2: International Names

Input (`names.csv`):
```csv
Name,Country,City
John Smith,USA,New York
Maria Garcia,Spain,Madrid
Yuki Tanaka,Japan,Tokyo
Li Wei,China,Beijing
```

Default output:
```
csview names.csv
```

```
┌──────────────┬─────────┬──────────┐
│     Name     │ Country │   City   │
├──────────────┼─────────┼──────────┤
│ John Smith   │ USA     │ New York │
│ Maria Garcia │ Spain   │ Madrid   │
│ Yuki Tanaka  │ Japan   │ Tokyo    │
│ Li Wei       │ China   │ Beijing  │
└──────────────┴─────────┴──────────┘
```

### Dataset 3: Quoted Fields with Special Characters

Input (`quotes.csv`):
```csv
Title,Author,Quote
"The Art of War","Sun Tzu","""Know yourself and you will win all battles."""
"Hamlet","Shakespeare","To be, or not to be"
"1984","George Orwell","War is peace. Freedom is slavery."
```

Default output:
```
csview quotes.csv
```

```
┌────────────────┬─────────────────┬────────────────────────────────────────────────┐
│     Title      │     Author      │                     Quote                      │
├────────────────┼─────────────────┼────────────────────────────────────────────────┤
│ The Art of War │ Sun Tzu         │ "Know yourself and you will win all battles."  │
│ Hamlet         │ Shakespeare     │ To be, or not to be                            │
│ 1984           │ George Orwell   │ War is peace. Freedom is slavery.              │
└────────────────┴─────────────────┴────────────────────────────────────────────────┘
```

---

## Appendix E: Troubleshooting

### "no input file specified" error

This error appears when csview is run interactively without a file argument and without piped input. Either specify a file or pipe data:

```
csview data.csv           # specify a file
cat data.csv | csview     # pipe data
```

### Table extends beyond terminal width

When the table is wider than the terminal, the pager (less -S) provides horizontal scrolling. Press the right arrow key to scroll right. If the pager is disabled, consider:

- Reducing padding: `csview -p0 data.csv`
- Using a style without borders: `csview -s none data.csv`
- Preprocessing to select fewer columns

### Misaligned columns with certain emoji

Some emoji sequences (particularly those using zero-width joiners, skin tone modifiers, or flag sequences) may appear misaligned because their actual rendered width in the terminal differs from the width calculated by the Unicode standard. This is a known limitation of terminal-based table rendering.

### "unequal lengths" error

This error indicates that a row has a different number of fields than expected. Check the input data for:

- Missing delimiters
- Extra delimiters
- Improperly quoted fields
- Inconsistent row structure

### Performance degradation with --sniff 0

Setting `--sniff 0` (unlimited sniffing) causes csview to buffer the entire input before rendering. For very large files, this significantly increases memory usage and delays the initial output. Use the default sniff limit of 1000 for large files.
