# hck -- A Sharp cut(1) Replacement

## Overview

hck is a high-performance command-line utility written in Rust that serves as a modern replacement for the traditional Unix `cut` command. The name "hck" is derived from "hack," representing a rougher, more powerful evolution of `cut`. While maintaining compatibility with common `cut` idioms, hck introduces several features that close the gap between simple field extraction with `cut` and full-blown text processing with `awk`.

hck is designed for the common case: you have delimited data and you want to extract, reorder, or exclude specific fields quickly and efficiently. It handles this task with minimal ceremony while offering capabilities that `cut` lacks entirely, such as regex-based delimiters, field reordering, header-based field selection, automatic decompression of compressed input files, and optional gzip compression of output.

The tool is dual-licensed under the MIT license and the UNLICENSE, making it freely available for any use.

### Key Advantages Over cut

- **Regex delimiters**: Split fields using regular expression patterns, not just single characters.
- **Field reordering**: Output fields in any order you specify, not just the order they appear in the input.
- **Header-based selection**: Select fields by column name rather than position number.
- **Field exclusion**: Remove specific fields from output rather than listing all the ones you want to keep.
- **Auto-decompression**: Transparently read gzip, bzip2, xz, lz4, zstd, and other compressed files.
- **Output compression**: Optionally compress output in BGZF format (compatible with tabix).
- **Performance**: Memory-mapped I/O and optimized single-byte delimiter parsing make hck significantly faster than `cut` on large files.

### Design Philosophy

hck intentionally avoids full CSV/TSV parsing with quote handling. It treats delimiters literally (or as regex patterns) without awareness of quoting conventions. This keeps the tool simple, predictable, and fast. If you need quote-aware CSV processing, tools like `xsv` or `csvkit` are more appropriate. hck occupies the sweet spot between basic `cut` and complex `awk` workflows, making common delimiter-and-field tasks easy without requiring a full programming language.

---

## Installation

hck can be installed through multiple package managers or built from source.

### Package Managers

**Homebrew (macOS/Linux):**

```
brew install hck
```

**Conda:**

```
conda install -c conda-forge hck
```

**MacPorts (macOS):**

```
sudo port install hck
```

**Cargo (Rust):**

```
cargo install hck
```

### Building from Source

```
git clone https://github.com/sstadick/hck.git
cd hck
cargo build --release
```

The resulting binary will be at `target/release/hck`.

### Pre-built Binaries

Pre-built binaries with profile-guided optimizations (PGO) are available from the GitHub releases page. These binaries are typically 10-20% faster than a standard `cargo build --release` due to the PGO training data.

---

## Options Reference

This section documents every command-line option available in hck.

### Input/Output Options

#### Positional Arguments: `[FILE]...`

One or more input files to process. If no files are specified, hck reads from standard input. The special filename `-` also refers to standard input and can be mixed with regular filenames. Multiple files are processed in the order they are given, and their output is concatenated.

```
hck -f1 file1.txt file2.txt file3.txt
```

When combined with `-z`, file extensions are used to detect and apply the appropriate decompression method.

#### `-o, --output <PATH>`

Write output to the specified file instead of standard output. Supports `-` to explicitly write to stdout.

```
hck -f1,2 -o result.txt input.txt
```

### Delimiter Options

#### `-d, --delimiter <DELIM>`

Specify the input delimiter used to split each line into fields. The default delimiter is `\s+`, which is a regex pattern matching one or more whitespace characters (spaces, tabs, etc.).

By default, the delimiter is treated as a regular expression pattern. To treat it as a literal string, use the `-L` flag.

**Default behavior (regex):**

```
echo "alice   bob   carol" | hck -f2
```

Output:

```
bob
```

The `\s+` default regex matches one or more whitespace characters, so multiple spaces between fields are treated as a single delimiter.

**Custom delimiter:**

```
echo "alice:bob:carol" | hck -d: -f2
```

Output:

```
bob
```

Note: When a single character is given as the delimiter without `-L`, hck may still interpret it as a regex. However, most single characters (letters, digits, common punctuation) are valid as both regex and literal, so the result is the same. For guaranteed literal interpretation, always use `-L`.

**Regex delimiter:**

```
echo "alice123bob456carol" | hck -d'\d+' -f2
```

Output:

```
bob
```

The delimiter can be any valid Rust regex pattern. The regex crate used by hck supports a rich set of patterns including character classes, quantifiers, alternation, and more. Notably, it does not support lookahead or lookbehind assertions.

**Multi-character delimiter:**

```
echo "alice<=>bob<=>carol" | hck -d'<=>' -f2
```

Output:

```
bob
```

#### `-L, --delim-is-literal`

Treat the input delimiter as a literal string rather than a regex pattern. This has two benefits: it avoids the need to escape regex metacharacters in the delimiter, and it can significantly improve performance since literal string matching is faster than regex matching.

```
echo "alice.bob.carol" | hck -Ld'.' -f2
```

Output:

```
bob
```

Without `-L`, the `.` would be interpreted as a regex metacharacter matching any character, and the splitting behavior would be different.

When `-L` is used, hck can employ a faster single-byte delimiter parser (when the delimiter is exactly one byte) that uses `memchr` for hardware-accelerated searching.

#### `-D, --output-delimiter <DELIM>`

Specify the string used to join output fields. The default output delimiter is a tab character (`\t`).

```
echo "alice:bob:carol" | hck -Ld: -D, -f1,3
```

Output:

```
alice,carol
```

The output delimiter is always treated as a literal string, never as a regex.

**Multi-character output delimiter:**

```
echo "alice:bob:carol" | hck -Ld: -D' | ' -f1,2,3
```

Output:

```
alice | bob | carol
```

#### `-I, --use-input-delim`

Use the input delimiter as the output delimiter. This flag requires `-L` (the delimiter must be literal) and conflicts with `-D` (you cannot specify both).

```
echo "alice:bob:carol" | hck -Ld: -I -f1,3
```

Output:

```
alice:carol
```

This is a convenience flag equivalent to specifying `-D` with the same value as `-d`.

### Field Selection Options

#### `-f, --fields <FIELDS>`

Specify which fields to select from each line. Fields are 1-indexed (the first field is field 1, not field 0). The field specification supports several formats:

- **Single field**: `1`, `3`, `5`
- **Inclusive range**: `1-5` (fields 1 through 5)
- **Open-ended high range**: `3-` (field 3 through the last field)
- **Open-ended low range**: `-5` (field 1 through field 5)
- **Comma-separated**: `1,3,5` (fields 1, 3, and 5)
- **Mixed**: `1,3-5,8,10-` (field 1, fields 3-5, field 8, field 10 onward)

```
echo "a b c d e f g" | hck -f1,3,5-7
```

Output:

```
a	c	e	f	g
```

Fields can be specified in any order to reorder the output:

```
echo "a b c d e" | hck -f3,1,5
```

Output:

```
c	a	e
```

See the "Field Selection Syntax" section below for comprehensive details.

#### `-e, --exclude <FIELDS>`

Specify fields to exclude from the output. The syntax is the same as `-f`. Exclude fields take precedence over include fields: if a field appears in both `-f` and `-e`, it is excluded.

```
echo "a b c d e" | hck -e2,4
```

Output:

```
a	c	e
```

When `-e` is used without `-f`, all fields are included by default and then the specified fields are removed.

Exclude supports the same range syntax as `-f`:

```
echo "a b c d e f g" | hck -e3-5
```

Output:

```
a	b	f	g
```

#### `-F, --header-field <FIELDS>`

Select fields by matching against the header (first line) of the input. By default, header fields are matched as literal string comparisons. Use `-r` to treat them as regex patterns.

```
printf "name\tage\tcity\n" | hck -F name,city
```

This selects the columns whose header matches "name" or "city".

Multiple header patterns can be specified, separated by commas:

```
echo -e "id\tname\tage\temail" | hck -F 'name,email'
```

#### `-E, --exclude-header <FIELDS>`

Exclude fields by matching against the header (first line). This is the header-based equivalent of `-e`. Fields whose headers match the given patterns are removed from the output.

```
echo -e "id\tname\tage\temail" | hck -E age
```

This outputs all columns except the one with header "age".

#### `-r, --header-is-regex`

Treat header field patterns (used with `-F` and `-E`) as regular expressions instead of literal strings.

```
echo -e "user_id\tuser_name\tuser_age\tgroup" | hck -F '^user_' -r
```

This selects all columns whose headers start with "user_".

### Compression Options

#### `-z, --try-decompress`

Attempt to automatically decompress input files based on their file extensions. Supported formats and their recognized extensions:

| Format | Extensions |
|--------|-----------|
| gzip   | `.gz`     |
| bzip2  | `.bz2`    |
| xz     | `.xz`     |
| lz4    | `.lz4`    |
| zstd   | `.zst`    |
| brotli | `.br`     |

```
hck -z -f1,3 data.tsv.gz
```

If the file does not have a recognized extension, it is read as a plain file.

#### `-Z, --try-compress`

Compress the output using gzip in BGZF (Blocked GNU Zip Format). BGZF output is compatible with standard gzip decompressors and with tools like `tabix` that require block-compressed input.

```
hck -f1,3 -Z -o output.gz input.tsv
```

#### `-t, --compression-threads <N>`

Number of threads to use for compression when `-Z` is enabled. The default is 4 threads on systems with 4 or more CPU cores, or `num_cpus - 1` on systems with fewer cores. Setting this to 0 results in single-threaded compression.

```
hck -f1,3 -Z -t8 -o output.gz input.tsv
```

#### `-l, --compression-level <LEVEL>`

Set the compression level when `-Z` is enabled. The default is 6. Valid values range from 0 (no compression, fastest) to 9 (maximum compression, slowest).

```
hck -f1,3 -Z -l9 -o output.gz input.tsv
```

### Advanced Options

#### `--no-mmap`

Disable the use of memory-mapped I/O for reading input files. By default, hck attempts to use mmap for file input on supported platforms, which can be significantly faster for large files. This flag forces hck to use standard buffered reads instead.

Use `--no-mmap` when:

- Reading from pipes or FIFOs (mmap cannot be used with these)
- The input file might be modified while hck is running
- You are on a platform where mmap performance is poor
- You encounter issues with mmap on specific filesystems

```
hck --no-mmap -f1,3 largefile.tsv
```

Note: mmap is automatically disabled for stdin input regardless of this flag.

#### `--crlf`

Enable support for CRLF (carriage return + line feed) line endings, commonly found in files originating from Windows systems. When this flag is set, hck strips the trailing `\r` before processing each line.

```
hck --crlf -f1,3 windows_file.tsv
```

Without this flag, a trailing `\r` would be included as part of the last field on each line, which can cause subtle issues in output.

---

## Field Selection Syntax

hck uses a powerful and flexible field selection syntax that extends what traditional `cut` offers. Fields are specified as a comma-separated list of individual field numbers and/or ranges.

### Field Numbering

Fields are numbered starting from 1. Field 0 is invalid and will cause an error. The first field on each line is field 1, the second is field 2, and so on.

Given the input line:

```
alice	bob	carol	dave	eve
```

The fields are:

| Field Number | Value  |
|-------------|--------|
| 1           | alice  |
| 2           | bob    |
| 3           | carol  |
| 4           | dave   |
| 5           | eve    |

### Single Fields

Select individual fields by their number:

```
echo "a b c d e" | hck -f2
```

Output:

```
b
```

Multiple individual fields can be separated by commas:

```
echo "a b c d e" | hck -f1,3,5
```

Output:

```
a	c	e
```

### Ranges

A range is specified as `LOW-HIGH`, where both endpoints are inclusive. Both `LOW` and `HIGH` are 1-indexed field numbers.

```
echo "a b c d e f g" | hck -f2-5
```

Output:

```
b	c	d	e
```

The range `2-5` selects fields 2, 3, 4, and 5.

### Open-Ended High Ranges

The syntax `N-` (with no upper bound) selects from field N through the last field on the line. This is useful when you don't know how many fields each line has.

```
echo "a b c d e f g" | hck -f3-
```

Output:

```
c	d	e	f	g
```

This selects field 3 and everything after it.

### Open-Ended Low Ranges

The syntax `-N` (with no lower bound) selects from field 1 through field N.

```
echo "a b c d e f g" | hck -f-3
```

Output:

```
a	b	c
```

This is equivalent to `1-3`.

### The Universal Range

The syntax `-` (a bare hyphen) selects all fields, equivalent to `1-`. This outputs the entire line, which is primarily useful in combination with a changed delimiter:

```
echo "a:b:c:d" | hck -Ld: -D'	' -f-
```

Output:

```
a	b	c	d
```

### Mixed Specifications

Individual fields and ranges can be freely combined:

```
echo "a b c d e f g h" | hck -f1,3-5,8
```

Output:

```
a	c	d	e	h
```

### Field Reordering

Unlike traditional `cut`, which always outputs fields in their original order regardless of the order specified, hck outputs fields in the exact order they are listed in the `-f` argument.

```
echo "a b c d e" | hck -f5,3,1
```

Output:

```
e	c	a
```

This is one of hck's most useful features. With `cut`, achieving field reordering requires piping through `awk` or similar tools.

More complex reordering with ranges:

```
echo "a b c d e f g" | hck -f5-7,1-3
```

Output:

```
e	f	g	a	b	c
```

### Duplicate Fields

Fields can be repeated by specifying them multiple times:

```
echo "a b c" | hck -f1,1,1
```

Output:

```
a	a	a
```

This is useful for creating repeated columns or for padding output.

Note: When ranges overlap, hck's internal processing merges overlapping ranges. This means that in some cases, specifying overlapping ranges may not produce duplicate output for the overlapping fields. The behavior of overlapping ranges is:

```
echo "a b c d e" | hck -f1-3,2-4
```

The ranges `1-3` and `2-4` overlap at fields 2 and 3. Depending on the internal merge behavior, the output may or may not contain duplicates for the overlapping portion.

### Invalid Field Specifications

The following field specifications are invalid and will cause hck to exit with an error:

- **Field 0**: Fields are 1-indexed; `0` is not a valid field number.

  ```
  echo "a b c" | hck -f0
  # Error: invalid field specification
  ```

- **Reversed ranges**: The low end of a range must not exceed the high end.

  ```
  echo "a b c" | hck -f5-3
  # Error: invalid field order
  ```

- **Non-numeric values**: Field specifications must be numeric (or ranges of numbers).

  ```
  echo "a b c" | hck -f"abc"
  # Error: failed to parse field specification
  ```

### Interaction Between -f and -e

When both `-f` (include) and `-e` (exclude) are specified, the include list is processed first, and then the exclude list removes fields from the result. This means that `-e` takes precedence.

```
echo "a b c d e" | hck -f1-5 -e3
```

Output:

```
a	b	d	e
```

Here, `-f1-5` selects all five fields, and then `-e3` removes field 3 from the result.

The exclude operation handles four types of overlap between include ranges and exclude ranges:

1. **Partial overlap at the start**: The exclude range overlaps the beginning of an include range.
2. **Partial overlap at the end**: The exclude range overlaps the end of an include range.
3. **Complete containment**: The exclude range is entirely within an include range, splitting it into two.
4. **Complete enclosure**: The exclude range entirely covers an include range, removing it.

---

## Delimiter Behavior

Understanding how hck handles delimiters is essential for getting the expected output from your data.

### Default Delimiter

The default input delimiter is the regex pattern `\s+`, which matches one or more whitespace characters. This means that by default, hck splits on any amount of whitespace, making it immediately useful for processing output from commands like `ps`, `ls -l`, `df`, and similar tools that use variable amounts of whitespace to align columns.

```
ps aux | hck -f1,2,11
```

This extracts the user, PID, and command fields from `ps aux` output, automatically handling the variable whitespace between columns.

### Literal String Delimiters

When the `-L` flag is set, the delimiter is treated as a literal string. No regex interpretation is performed.

```
echo "a..b..c" | hck -Ld'..' -f2
```

Output:

```
b
```

Without `-L`, the delimiter `..` would be interpreted as a regex matching any two characters.

### Regex Delimiters

Without `-L`, the delimiter is interpreted as a regex pattern using the Rust `regex` crate. This supports a wide range of patterns:

**Character classes:**

```
echo "a1b2c3d" | hck -d'[0-9]' -f2,3
```

Output:

```
b	c
```

**Alternation:**

```
echo "a:b;c:d" | hck -d'[:;]' -f2,3
```

Output:

```
b	c
```

**Quantifiers:**

```
echo "a---b--c----d" | hck -d'-+' -f1,2,3,4
```

Output:

```
a	b	c	d
```

**Complex patterns:**

```
echo "field1<SEP>field2<SEP>field3" | hck -d'<SEP>' -f2
```

Output:

```
field2
```

**Whitespace patterns:**

```
echo "a   b		c  d" | hck -d'\s+' -f1,2,3,4
```

Output:

```
a	b	c	d
```

This is the default behavior since `\s+` is the default delimiter.

### Output Delimiter Defaults

The output delimiter follows these rules:

1. If `-D` is explicitly specified, that value is used.
2. If `-I` is specified (with `-L`), the input delimiter is used as the output delimiter.
3. Otherwise, the default output delimiter is a tab character (`\t`).

This means that when using a regex input delimiter, the output delimiter is always tab unless explicitly set. This makes sense because a regex pattern is not a valid literal string to insert between output fields.

### Delimiter Edge Cases

**Empty fields between consecutive delimiters:**

When using a literal single-character delimiter, consecutive delimiters create empty fields:

```
echo "a::b:::c" | hck -Ld: -f1,2,3,4,5,6
```

Output:

```
a		b			c
```

Fields 2, 4, and 5 are empty strings. This matches the behavior of `cut`.

However, with the default regex delimiter `\s+`, consecutive whitespace characters are consumed as a single delimiter, so no empty fields are created:

```
echo "a   b   c" | hck -f1,2,3
```

Output:

```
a	b	c
```

**Lines without the delimiter:**

If a line does not contain the delimiter at all, the entire line is treated as a single field (field 1). Requesting any other field produces no output for that field.

```
echo "hello world" | hck -Ld: -f1
```

Output:

```
hello world
```

```
echo "hello world" | hck -Ld: -f2
```

Output (empty -- nothing is printed for the missing field):

```

```

**Tab as delimiter:**

Tab is not the default delimiter (the default is `\s+` regex), but tab-separated data is very common. To use a literal tab delimiter:

```
hck -Ld$'\t' -f1,3 data.tsv
```

Or, since `\s+` already matches tabs, the default often works:

```
hck -f1,3 data.tsv
```

The difference is that `\s+` will merge multiple consecutive tabs into one delimiter, while a literal tab will treat each tab as a separate delimiter (preserving empty fields).

---

## Header Mode

hck supports selecting fields by their column names using the header line (the first line of the input).

### Basic Header Selection

Use `-F` to specify field names to select:

```
printf "name\tage\tcity\njohn\t30\tnyc\njane\t25\tsf\n" | hck -F 'name,city'
```

Output:

```
name	city
john	nyc
jane	sf
```

The header line is included in the output. Fields are matched by exact string comparison (case-sensitive) by default.

### Regex Header Matching

Use `-r` in combination with `-F` to treat header patterns as regular expressions:

```
printf "user_id\tuser_name\tuser_age\tgroup_id\n1\talice\t30\t5\n" | hck -F '^user_' -r
```

Output:

```
user_id	user_name	user_age
1	alice	30
```

This selects all columns whose header starts with "user_".

Multiple regex patterns can be specified:

```
printf "id\tfirst_name\tlast_name\temail\tage\n" | hck -F '^(first|last)_,email' -r
```

### Header Exclusion

Use `-E` to exclude columns by header name:

```
printf "id\tname\tpassword\temail\n1\talice\tsecret\ta@b.com\n" | hck -E password
```

Output:

```
id	name	email
1	alice	a@b.com
```

With regex:

```
printf "id\tinternal_score\tname\tinternal_rank\n" | hck -E '^internal_' -r
```

Output:

```
id	name
```

### Combining Header and Index Selection

Header-based selection (`-F`) and index-based selection (`-f`) can be used together. When both are specified, header matching is performed first to determine the column indices, and then the results are combined with any index-based selections.

### Case Sensitivity

Header matching is case-sensitive by default. To perform case-insensitive matching, use the regex flag `-r` and include the `(?i)` inline flag in the pattern:

```
printf "Name\tAGE\tCity\n" | hck -F '(?i)name,(?i)city' -r
```

### Header Mode Limitations

- Header selection requires the first line to be a header. There is no way to specify that the header is on a different line.
- Piping gzipped stdin with header selections is not supported and will cause a runtime panic.
- If a header pattern matches no columns and `allow_missing` is not set, hck will exit with an error.

---

## Input Sources

hck supports reading from several types of input sources.

### Standard Input (stdin)

When no files are specified, hck reads from standard input:

```
cat data.tsv | hck -f1,3
```

Or equivalently:

```
hck -f1,3 < data.tsv
```

The special filename `-` explicitly refers to stdin:

```
hck -f1,3 -
```

### File Arguments

One or more files can be specified as positional arguments:

```
hck -f1,3 file1.tsv file2.tsv file3.tsv
```

Files are processed in order, and their output is concatenated. There is no separator between files in the output.

### Mixing stdin and Files

The `-` argument can be mixed with file arguments:

```
echo "extra	line" | hck -f1,2 file1.tsv - file2.tsv
```

This processes `file1.tsv`, then stdin, then `file2.tsv`, concatenating all output.

### Multiple File Processing

When processing multiple files, each file is opened and processed independently. If header mode (`-F`) is used, only the header from the first file is used for field selection. The header lines from subsequent files are treated as data and processed with the same field positions.

### File Access Errors

If a specified file does not exist or cannot be read, hck will exit with an error. Files are not pre-validated; the error occurs when hck attempts to open the file during processing.

---

## Auto-Decompression (-z)

hck can automatically detect and decompress compressed input files using the `-z` flag.

### Supported Formats

| Format | Extension | Library     |
|--------|-----------|-------------|
| gzip   | `.gz`     | flate2      |
| bzip2  | `.bz2`    | bzip2       |
| xz     | `.xz`     | xz          |
| lz4    | `.lz4`    | lz4         |
| zstd   | `.zst`    | zstd        |
| brotli | `.br`     | brotli      |

### Usage

```
hck -z -f1,3 data.tsv.gz
```

The decompression method is selected based on the file extension. If the file does not have a recognized compressed extension, it is read as a plain text file.

### Multiple Compressed Files

Each file is independently decompressed based on its extension:

```
hck -z -f1,3 data1.tsv.gz data2.tsv.bz2 data3.tsv
```

In this example, `data1.tsv.gz` is decompressed with gzip, `data2.tsv.bz2` with bzip2, and `data3.tsv` is read as plain text.

### stdin and Decompression

Auto-decompression based on file extension does not apply to stdin, since stdin has no filename. To process compressed stdin, pipe through an external decompressor:

```
zcat data.tsv.gz | hck -f1,3
```

### Decompression Performance

Decompression is performed inline as the file is read. The decompressed data is never fully materialized in memory; it is streamed through the parser. This means that decompressing and processing a file with hck uses approximately the same amount of memory as processing the uncompressed file.

When decompression is active, memory-mapped I/O is not used (since the file content must be decompressed sequentially).

---

## Output Compression (-Z)

hck can compress its output using the `-Z` flag. Output is written in BGZF (Blocked GNU Zip Format), which is a variant of gzip that is compatible with all standard gzip decompressors but also supports random access through tools like `tabix`.

### Usage

```
hck -f1,3 -Z -o output.tsv.gz input.tsv
```

### Compression Threads

Output compression supports multithreading via the `-t` flag:

```
hck -f1,3 -Z -t4 -o output.tsv.gz input.tsv
```

The default number of threads is 4 on systems with 4 or more CPU cores, or `num_cpus - 1` on smaller systems.

### Compression Level

The compression level is controlled by `-l`:

```
hck -f1,3 -Z -l9 -o output.tsv.gz input.tsv
```

| Level | Description                |
|-------|----------------------------|
| 0     | No compression (fastest)   |
| 1     | Minimal compression, fast  |
| 6     | Default, balanced          |
| 9     | Maximum compression, slow  |

### BGZF Compatibility

BGZF output is fully compatible with:

- `gzip -d` / `gunzip`
- `zcat`
- `tabix` (for indexed random access)
- `bgzip -d`

---

## Memory-Mapped I/O

hck uses memory-mapped I/O (mmap) by default for reading input files when conditions permit. This can significantly improve performance for large files by avoiding the overhead of system call-based reads.

### When mmap Is Used

mmap is used when all of the following conditions are met:

1. The input is a regular file (not stdin, not a pipe, not a FIFO).
2. The `--no-mmap` flag is not set.
3. The file is not compressed (decompression requires sequential reading).
4. The platform supports mmap and heuristics indicate it will be beneficial.

### Platform-Specific Behavior

- **64-bit Linux**: mmap is generally used when available and beneficial.
- **64-bit macOS**: mmap may be disabled due to platform-specific performance concerns. The hck codebase notes that "memory maps on macOS aren't great."
- **32-bit systems**: mmap is skipped entirely due to address space limitations.

### Disabling mmap

Use `--no-mmap` to force buffered I/O:

```
hck --no-mmap -f1,3 largefile.tsv
```

This is useful when:

- You are reading from a filesystem that does not support mmap well (e.g., network filesystems).
- The file might be modified concurrently (mmap requires the file to remain stable during reading; modifications can cause SIGBUS crashes).
- You are benchmarking and want to compare mmap vs buffered I/O performance.

### Fallback Behavior

If mmap creation fails (e.g., due to filesystem limitations), hck silently falls back to standard buffered reads. A debug-level log message is emitted indicating the fallback, but no error is reported to the user.

### Safety Considerations

Memory-mapped I/O requires that the underlying file is not modified while hck is reading it. If the file is modified during processing, the behavior is undefined and may include:

- Corrupted output
- A SIGBUS signal causing hck to crash
- Incorrect field extraction

For safety, ensure that input files are not being written to while hck is processing them.

---

## Comparison with cut

This section provides a detailed comparison between hck and the traditional Unix `cut` command.

### Feature Comparison

| Feature                     | cut                     | hck                      |
|----------------------------|-------------------------|--------------------------|
| Single-char delimiter      | Yes (`-d`)              | Yes (`-Ld`)              |
| Multi-char delimiter       | No                      | Yes (`-Ld`)              |
| Regex delimiter            | No                      | Yes (`-d`)               |
| Field selection            | Yes (`-f`)              | Yes (`-f`)               |
| Field reordering           | No (always in order)    | Yes                      |
| Field exclusion            | No (use `--complement`) | Yes (`-e`, `-E`)         |
| Header-based selection     | No                      | Yes (`-F`, `-E`, `-r`)   |
| Auto-decompression         | No                      | Yes (`-z`)               |
| Output compression         | No                      | Yes (`-Z`)               |
| Memory-mapped I/O          | No                      | Yes (default)            |
| Byte/character mode        | Yes (`-b`, `-c`)        | No                       |
| CRLF handling              | Varies                  | Yes (`--crlf`)           |
| Output delimiter           | Yes (`--output-delimiter`) | Yes (`-D`)            |
| Multiple input files       | Yes                     | Yes                      |
| stdin support              | Yes                     | Yes                      |
| Output to file             | No (use redirection)    | Yes (`-o`)               |

### Behavioral Differences

**Field reordering:**

`cut` always outputs fields in their original order, regardless of the order specified:

```
echo "a	b	c	d	e" | cut -f5,3,1
# Output: a	c	e  (always in ascending order)
```

hck outputs fields in the specified order:

```
echo "a	b	c	d	e" | hck -Ld$'\t' -f5,3,1
# Output: e	c	a  (in the order specified)
```

**Default delimiter:**

`cut` defaults to tab as the delimiter. hck defaults to `\s+` (one or more whitespace characters as a regex). This means that hck with no `-d` flag splits on any whitespace, while `cut` with no `-d` flag only splits on tabs.

To replicate `cut`'s exact default behavior in hck:

```
hck -Ld$'\t' -f1,3
```

**Missing fields:**

Both `cut` and hck handle lines with fewer fields than requested by simply omitting the missing fields from output. Neither produces an error for missing fields.

**Duplicate field specifications:**

`cut` deduplicates and sorts field specifications. `hck` preserves the order and may allow duplicates depending on whether ranges overlap.

### Migration from cut

Common `cut` commands and their hck equivalents:

```
# cut: Extract fields 1 and 3 from tab-separated data
cut -f1,3 data.tsv
hck -Ld$'\t' -f1,3 data.tsv

# cut: Use comma as delimiter
cut -d',' -f2,4 data.csv
hck -Ld',' -f2,4 data.csv

# cut: Extract fields 1 through 5
cut -f1-5 data.tsv
hck -Ld$'\t' -f1-5 data.tsv

# cut: Extract field 3 onward
cut -f3- data.tsv
hck -Ld$'\t' -f3- data.tsv
```

hck-specific enhancements with no `cut` equivalent:

```
# Reorder fields
hck -f3,1,2 data.tsv

# Use regex delimiter to split on any whitespace
ps aux | hck -f1,2,11

# Select by header name
hck -F 'name,email' data.tsv

# Process compressed file
hck -z -f1,3 data.tsv.gz

# Exclude specific fields
hck -e5,6 data.tsv
```

---

## Performance

hck is designed for high performance on large datasets. Several architectural decisions contribute to its speed.

### Single-Byte Delimiter Fast Path

When the following conditions are met, hck uses an optimized single-pass parser:

1. The delimiter is a single byte (i.e., `-L` is used and the delimiter is one character).
2. The line terminator is a single byte (the default newline).
3. Regex mode is not active.
4. Fields are specified in sorted order (no reordering).

In this mode, hck uses the `memchr2` function to simultaneously scan for both the delimiter byte and the newline byte in a single pass over the input. This eliminates the overhead of first splitting into lines and then splitting each line into fields.

Once the rightmost requested field has been found, the parser switches to searching only for newlines, skipping the remaining fields on the line entirely. This optimization is significant when only a few fields from wide lines are selected.

### Memory-Mapped I/O

As described in the "Memory-Mapped I/O" section, mmap avoids the overhead of `read()` system calls for file input. For large files that fit in available memory, mmap can be significantly faster because the operating system can use its virtual memory system to page in data as needed.

### Regex Compilation

When a regex delimiter is used, the regex is compiled once at startup and reused for every line. The Rust `regex` crate produces optimized finite automata that are fast to execute.

### Output Buffering

hck uses buffered I/O for output, reducing the number of `write()` system calls. The output buffer is flushed only when full or at the end of processing.

### Broken Pipe Handling

hck gracefully handles broken pipe errors (EPIPE), which occur when the downstream consumer of hck's output closes early (e.g., `hck -f1 largefile.tsv | head -n5`). When a broken pipe is detected, hck exits cleanly without printing an error message.

### Benchmark Results

On a benchmark with a 7-million-line CSV file, typical results show:

| Tool               | Single-char delimiter | Multi-char delimiter |
|--------------------|----------------------|---------------------|
| hck (literal)      | ~1.2s                | ~1.7s               |
| hck (regex)        | ~1.5s                | ~2.0s               |
| cut                | ~7.5s                | N/A (not supported) |
| awk                | ~8.5s                | ~8.6s               |

hck with a literal delimiter is approximately 5-6x faster than `cut` for simple field extraction tasks. With regex delimiters, hck is still faster than alternatives that require preprocessing (e.g., using `sed` to normalize delimiters before piping to `cut`).

### Performance Tips

1. **Use `-L` when possible**: Literal string matching is faster than regex matching. If your delimiter is a fixed string, always use `-L`.

2. **Use single-byte delimiters**: The single-byte fast path is the most optimized code path. When your delimiter is a single character, use `-L` to ensure hck can use this path.

3. **Avoid unnecessary reordering**: When fields are in sorted order, hck can use additional optimizations. If you don't need reordering, specify fields in ascending order.

4. **Use mmap (default)**: Don't disable mmap unless you have a specific reason. It generally improves performance for file input.

5. **Prefer `-e` over complex `-f`**: If you want most fields except a few, using `-e` to exclude is both easier to write and can be faster since hck doesn't need to track specific positions.

---

## Exit Codes

hck uses the following exit codes:

| Exit Code | Meaning                                                        |
|-----------|----------------------------------------------------------------|
| 0         | Success. All input was processed and output was written.       |
| Non-zero  | An error occurred during processing.                           |

### Common Error Conditions

- **Invalid field specification**: Specifying field 0, a reversed range (e.g., `5-3`), or a non-numeric field value.
- **Invalid regex**: Providing an invalid regex pattern as the delimiter.
- **Missing input file**: Specifying a file that does not exist or cannot be opened.
- **Permission error**: Specifying a file that exists but cannot be read due to permissions.
- **Decompression failure**: A file with a compressed extension cannot be decompressed (e.g., a `.gz` file that is not actually gzip-compressed).
- **Conflicting options**: Using `-I` without `-L`, or using both `-I` and `-D`.

### Broken Pipe Behavior

When hck's output is piped to a command that closes early (e.g., `head`), hck receives a broken pipe signal. In this case, hck exits with code 0 (success), not with an error. This matches the expected behavior for Unix pipelines.

---

## Error Handling

hck reports errors to standard error and exits with a non-zero exit code. Error messages include enough context to diagnose the problem.

### Invalid Field Specifications

```
$ hck -f0
error: invalid field specification: field numbers start at 1, not 0
```

```
$ hck -f5-3
error: invalid field specification: range start (5) is greater than range end (3)
```

```
$ hck -fabc
error: failed to parse field specification: invalid digit found in string
```

### Invalid Regex Delimiters

```
$ hck -d'[unclosed' -f1
error: invalid regex delimiter: unclosed character class
```

```
$ hck -d'(?P<name' -f1
error: invalid regex delimiter: unclosed group
```

The error message includes the specific reason the regex is invalid, as reported by the Rust regex crate.

### Missing Input Files

```
$ hck -f1 nonexistent.txt
error: No such file or directory (os error 2): nonexistent.txt
```

### Permission Errors

```
$ hck -f1 /root/secret.txt
error: Permission denied (os error 13): /root/secret.txt
```

### Decompression Failures

When `-z` is used and a file with a compressed extension cannot be decompressed:

```
$ hck -z -f1 corrupt.tsv.gz
error: decompression failed: invalid gzip header
```

### Conflicting Options

```
$ hck -I -D',' -f1
error: the argument '--use-input-delim' cannot be used with '--output-delimiter'
```

```
$ hck -I -f1
error: the argument '--use-input-delim' requires '--delim-is-literal'
```

---

## Edge Cases

This section documents how hck handles various edge cases and unusual input.

### Lines with Fewer Fields Than Selected

When a line has fewer fields than the field specification requests, the missing fields are simply omitted from the output. No error is raised.

```
printf "a\tb\tc\n" | hck -Ld$'\t' -f1,2,3,4,5
```

Output:

```
a	b	c
```

Fields 4 and 5 do not exist on this line, so they are silently omitted.

If a requested field is entirely beyond the available fields:

```
printf "a\tb\tc\n" | hck -Ld$'\t' -f10
```

Output (empty line):

```

```

### Empty Lines

Empty lines are passed through as-is. Since an empty line has no fields, selecting any field produces an empty line in the output.

```
printf "a\tb\n\nc\td\n" | hck -Ld$'\t' -f1
```

Output:

```
a

c
```

The empty line in the input produces an empty line in the output.

### Lines Without the Delimiter

If a line does not contain the delimiter at all, the entire line is treated as field 1.

```
printf "hello\n" | hck -Ld$'\t' -f1
```

Output:

```
hello
```

```
printf "hello\n" | hck -Ld$'\t' -f2
```

Output (empty -- no second field):

```

```

### Trailing Delimiters

A trailing delimiter at the end of a line creates an empty final field:

```
printf "a\tb\tc\t\n" | hck -Ld$'\t' -f1,2,3,4
```

Output:

```
a	b	c
```

Field 4 is an empty string (the text after the last tab).

### Leading Delimiters

A leading delimiter creates an empty first field:

```
printf "\ta\tb\n" | hck -Ld$'\t' -f1,2,3
```

Output:

```
	a	b
```

Field 1 is an empty string (the text before the first tab).

### Consecutive Delimiters with Literal Mode

With a literal delimiter, consecutive delimiters produce empty fields between them:

```
printf "a\t\t\tb\n" | hck -Ld$'\t' -f1,2,3,4
```

Output:

```
a			b
```

Fields 2 and 3 are empty strings.

### Consecutive Whitespace with Default Regex

With the default `\s+` delimiter, consecutive whitespace is treated as a single delimiter:

```
echo "a     b     c" | hck -f1,2,3
```

Output:

```
a	b	c
```

No empty fields are created.

### Very Long Lines

hck processes lines one at a time and does not impose a maximum line length. Very long lines are handled correctly, limited only by available memory.

### Very Wide Lines (Many Fields)

Lines with thousands of fields are handled efficiently. The field range processing uses vectors that grow as needed. Performance degrades linearly with the number of fields, not quadratically.

### Binary Data

hck processes input as bytes, not as Unicode text. Binary data (including null bytes) is handled without error. However, the delimiter matching uses the Rust `regex` crate or byte string matching, so the behavior with binary delimiters may be unexpected. The output will contain whatever bytes are between the matched delimiters.

### Unicode Content

hck operates on bytes, not Unicode code points. This means:

- Single-byte delimiters work correctly with UTF-8 content as long as the delimiter byte does not appear within multi-byte characters.
- Regex delimiters support Unicode patterns through the Rust regex crate, which is Unicode-aware by default.
- Field boundaries always fall on byte boundaries, not character boundaries. This is correct for UTF-8 delimiters like tabs, commas, and spaces, which are all single-byte ASCII characters.

```
echo "caf\xc3\xa9	na\xc3\xafve	r\xc3\xa9sum\xc3\xa9" | hck -Ld$'\t' -f1,3
```

Output:

```
cafe	resume
```

(Rendered with the proper accented characters in a UTF-8 terminal.)

### CRLF Line Endings

Files with Windows-style CRLF (`\r\n`) line endings can cause the carriage return to be included in the last field. Use `--crlf` to handle this:

```
printf "a\tb\r\nc\td\r\n" | hck --crlf -Ld$'\t' -f2
```

Output:

```
b
d
```

Without `--crlf`, the output would include the `\r` character:

```
b\r
d\r
```

### Single-Field Input

When the input has only one field per line (no delimiters present), field 1 contains the entire line and all other fields are empty.

```
printf "hello\nworld\n" | hck -Ld$'\t' -f1
```

Output:

```
hello
world
```

### Empty Input

If the input is completely empty (zero bytes), hck produces no output and exits with code 0.

```
echo -n "" | hck -f1
```

No output is produced.

### Single-Line Input Without Trailing Newline

hck handles input that does not end with a newline:

```
printf "a\tb\tc" | hck -Ld$'\t' -f2
```

Output:

```
b
```

The output may or may not include a trailing newline depending on the implementation.

---

## Regex Delimiter Reference

When using regex delimiters (without `-L`), hck supports the full syntax of the Rust `regex` crate. This section provides a reference for commonly used patterns.

### Basic Patterns

| Pattern      | Matches                                      |
|-------------|----------------------------------------------|
| `.`         | Any character except newline                  |
| `\d`        | Any digit (0-9)                               |
| `\D`        | Any non-digit                                 |
| `\w`        | Any word character (alphanumeric + underscore) |
| `\W`        | Any non-word character                         |
| `\s`        | Any whitespace character                       |
| `\S`        | Any non-whitespace character                   |

### Quantifiers

| Pattern      | Matches                          |
|-------------|----------------------------------|
| `*`         | Zero or more of the preceding    |
| `+`         | One or more of the preceding     |
| `?`         | Zero or one of the preceding     |
| `{n}`       | Exactly n of the preceding       |
| `{n,}`      | n or more of the preceding       |
| `{n,m}`     | Between n and m of the preceding |

### Character Classes

| Pattern        | Matches                                |
|---------------|----------------------------------------|
| `[abc]`       | Any of a, b, or c                      |
| `[^abc]`      | Any character except a, b, or c        |
| `[a-z]`       | Any lowercase letter                   |
| `[A-Za-z]`    | Any letter                             |
| `[0-9]`       | Any digit (same as `\d`)              |

### Alternation

| Pattern         | Matches                      |
|----------------|------------------------------|
| `cat\|dog`     | "cat" or "dog"               |
| `(a\|b)c`      | "ac" or "bc"                 |

### Anchors

Anchors are generally not useful in delimiter patterns since the delimiter is found within the line, not at line boundaries. However, they are supported:

| Pattern | Meaning                |
|---------|------------------------|
| `^`     | Start of line          |
| `$`     | End of line            |
| `\b`    | Word boundary          |
| `\B`    | Non-word boundary      |

### Escaping

To match regex metacharacters literally, escape them with a backslash:

| Pattern  | Matches literal |
|----------|----------------|
| `\.`     | `.`            |
| `\*`     | `*`            |
| `\+`     | `+`            |
| `\?`     | `?`            |
| `\(`     | `(`            |
| `\)`     | `)`            |
| `\[`     | `[`            |
| `\]`     | `]`            |
| `\{`     | `{`            |
| `\}`     | `}`            |
| `\\`     | `\`            |
| `\|`     | `\|`           |

### Common Delimiter Patterns

```
# One or more whitespace characters (default)
hck -d'\s+' -f1,2

# One or more commas
hck -d',+' -f1,2

# Comma optionally surrounded by whitespace
hck -d'\s*,\s*' -f1,2

# Any punctuation
hck -d'[[:punct:]]' -f1,2

# Pipe character (must be escaped in regex)
hck -d'\|' -f1,2

# Tab or comma
hck -d'[\t,]' -f1,2

# One or more digits
hck -d'\d+' -f1,2

# HTML-like tags
hck -d'<[^>]+>' -f1,2

# Multiple dashes or equals signs
hck -d'[-=]+' -f1,2
```

### Unsupported Regex Features

The Rust `regex` crate does not support:

- Lookahead assertions (`(?=...)`, `(?!...)`)
- Lookbehind assertions (`(?<=...)`, `(?<!...)`)
- Backreferences (`\1`, `\2`)
- Recursive patterns
- Conditional patterns

If you need these features, preprocess the input with a tool like `sed` or `perl` before piping to hck.

---

## Practical Examples

This section provides detailed, real-world examples of using hck for common tasks.

### Extracting Fields from /etc/passwd

The `/etc/passwd` file uses `:` as a delimiter. Extract usernames and home directories:

```
hck -Ld: -f1,6 /etc/passwd
```

Output:

```
root	/root
daemon	/usr/sbin
bin	/bin
...
```

To also get the shell (field 7):

```
hck -Ld: -f1,6,7 /etc/passwd
```

### Processing ps Output

Extract PID, user, and command from `ps aux`:

```
ps aux | hck -f2,1,11-
```

This reorders the output to show PID first, then user, then the command (which may contain spaces and spans from field 11 onward).

### Working with CSV Data

Process a CSV file, extracting specific columns:

```
hck -Ld, -f1,3,5 data.csv
```

Convert CSV to TSV:

```
hck -Ld, -D$'\t' -f- data.csv
```

Convert TSV to CSV:

```
hck -Ld$'\t' -D, -f- data.tsv
```

### Extracting Columns from Log Files

Apache access logs use spaces and quotes as delimiters. Extract the IP address (field 1), HTTP method and URL (within quotes), and status code:

```
hck -d'"' -f1 access.log | hck -f1
```

For more complex log parsing, use a regex delimiter:

```
hck -d'\s+' -f1,7,9 access.log
```

This extracts the IP address, requested path, and HTTP status code.

### Reordering Columns for Import

Rearrange columns to match the expected format of a database import:

```
hck -Ld$'\t' -f3,1,5,2,4 source.tsv > import.tsv
```

### Processing Compressed Genomics Data

Bioinformatics files are often compressed. Extract columns from a gzipped BED file:

```
hck -z -Ld$'\t' -f1,2,3 regions.bed.gz
```

Extract specific columns from a gzipped VCF-like file and compress the output:

```
hck -z -Ld$'\t' -f1,2,4,5 variants.tsv.gz -Z -o filtered.tsv.gz
```

### Using Header-Based Selection

When working with data that has a header row, select columns by name:

```
hck -F 'name,email,phone' contacts.tsv
```

Select all columns that match a pattern:

```
hck -F '^score_' -r results.tsv
```

This selects all columns whose names start with "score_".

Exclude sensitive columns:

```
hck -E 'password,ssn,credit_card' users.tsv
```

### Extracting Fields from Key-Value Data

Data with key-value pairs separated by `=`:

```
echo "name=alice age=30 city=nyc" | hck -d'[= ]+' -f2,4,6
```

Output:

```
alice	30	nyc
```

### Processing Multi-Character Delimiters

Some data formats use multi-character delimiters like `||` or `<>`:

```
echo "field1||field2||field3" | hck -Ld'||' -f1,3
```

Output:

```
field1	field3
```

With regex (escaping the pipe):

```
echo "field1||field2||field3" | hck -d'\|\|' -f1,3
```

### Duplicating a Column

Create a dataset with a duplicated column for validation:

```
hck -Ld$'\t' -f1,2,2,3 data.tsv
```

This outputs field 2 twice: once in its original position and once as an additional column.

### Removing Specific Columns

Remove columns 3 and 5 from a dataset, keeping everything else:

```
hck -Ld, -e3,5 data.csv
```

This is much easier than listing all the columns you want to keep with `-f`.

### Pipeline Integration

hck works well in Unix pipelines:

```
# Sort by the second column of a CSV
hck -Ld, -f2 data.csv | sort | uniq -c | sort -rn

# Count unique values in the third column
hck -Ld$'\t' -f3 data.tsv | sort -u | wc -l

# Extract and transform data
hck -Ld: -f1 /etc/passwd | tr 'a-z' 'A-Z'

# Process multiple compressed files and combine results
hck -z -Ld$'\t' -f1,3 *.tsv.gz | sort -u > combined.txt
```

### Handling Mixed Delimiters

When fields are separated by varying amounts of whitespace (common in command output):

```
df -h | hck -f1,5,6
```

The default `\s+` regex handles the variable whitespace automatically.

### Converting Between Delimiter Formats

Convert pipe-delimited to comma-delimited:

```
hck -Ld'|' -D, -f- input.txt > output.csv
```

Convert semicolon-delimited to tab-delimited:

```
hck -Ld';' -D$'\t' -f- input.txt > output.tsv
```

### Extracting a Range of Columns

Extract the first 5 columns:

```
hck -f-5 data.tsv
```

Extract columns 10 through the last:

```
hck -f10- data.tsv
```

Extract columns 3 through 7:

```
hck -f3-7 data.tsv
```

### Processing Fixed-Width-ish Data

While hck is not a fixed-width parser, many fixed-width formats use consistent whitespace that the default `\s+` regex handles well:

```
# Process 'ls -l' output
ls -l | hck -f5,9
```

This extracts the file size and filename from `ls -l` output.

```
# Process 'netstat' output
netstat -tuln | hck -f4,6
```

### Working with PATH-Like Variables

Split PATH and extract specific entries:

```
echo "$PATH" | hck -Ld: -f1,2,3
```

### Extracting From Structured Log Formats

For log entries like `[2024-01-15 10:30:45] ERROR: Something went wrong`:

```
hck -d'[\[\] ]+' -f2,3,4- logfile.txt
```

This uses a regex to split on brackets and spaces, extracting the date, time, and message.

---

## Interaction with Shell Features

### Shell Quoting

Delimiters and field specifications often contain characters that are special to the shell. Proper quoting is essential.

**Single quotes** prevent all shell interpretation:

```
hck -d'\s+' -f1,2
```

**Double quotes** allow variable expansion but prevent word splitting:

```
hck -d"\t" -f1,2
```

**Dollar-single-quotes** (`$'...'`) enable escape sequences:

```
hck -Ld$'\t' -f1,2
```

This is the recommended way to specify a literal tab delimiter.

### Environment Variables in Field Specs

Field specifications can come from variables:

```
FIELDS="1,3,5"
hck -f"$FIELDS" data.tsv
```

### Piping and Redirection

hck supports standard Unix I/O redirection:

```
# Input from file, output to file
hck -f1,3 < input.tsv > output.tsv

# Pipe input
cat data.tsv | hck -f1,3

# Pipe output
hck -f1,3 data.tsv | sort

# Append to file
hck -f1,3 data.tsv >> results.tsv

# Error redirection
hck -f1,3 data.tsv 2>/dev/null
```

### Process Substitution

hck works with process substitution:

```
hck -f1,3 <(zcat data.tsv.gz)
```

Note: When using process substitution, mmap is not available since the input is a pipe (FIFO), not a regular file.

---

## Troubleshooting

### Common Issues and Solutions

**Issue: Output includes carriage return characters**

Symptom: Output looks correct in the terminal but has extra `^M` or `\r` characters when piped to another command.

Solution: Use the `--crlf` flag:

```
hck --crlf -f1,3 windows_file.tsv
```

**Issue: Fields are not split correctly**

Symptom: The entire line appears as a single field.

Solution: Check your delimiter. The default is `\s+` (regex whitespace), not tab. If your data uses a different delimiter, specify it:

```
hck -Ld, -f1,3 data.csv      # Comma-separated
hck -Ld$'\t' -f1,3 data.tsv  # Tab-separated (literal)
hck -Ld: -f1,3 data.txt      # Colon-separated
```

**Issue: Regex metacharacters in delimiter**

Symptom: Using a delimiter like `.` or `|` produces unexpected results.

Solution: Either escape the metacharacter or use `-L` for literal interpretation:

```
# Using -L (recommended for literal delimiters)
hck -Ld'.' -f1,3 data.txt

# Using regex escaping
hck -d'\.' -f1,3 data.txt
```

**Issue: Empty fields in output**

Symptom: Extra tabs or delimiters appear in the output.

Solution: This is correct behavior when consecutive delimiters exist in the input with literal delimiter mode. If you want to treat consecutive delimiters as one, use a regex with `+`:

```
hck -d',+' -f1,3 data.txt    # One or more commas as single delimiter
hck -d'\s+' -f1,3 data.txt   # One or more whitespace (default)
```

**Issue: "field numbers start at 1" error**

Symptom: Error when specifying `-f0`.

Solution: Fields are 1-indexed. The first field is `-f1`, not `-f0`.

**Issue: Performance is slower than expected**

Solution: Ensure you are using the optimal flags for your data:

```
# Fastest: literal single-byte delimiter, sorted fields
hck -Ld$'\t' -f1,2,3 data.tsv

# Slower: regex delimiter
hck -d'\s+' -f1,2,3 data.tsv

# Slowest: regex delimiter with reordering
hck -d'\s+' -f3,1,2 data.tsv
```

**Issue: mmap-related crashes or errors**

Symptom: Segfault or SIGBUS when processing files.

Solution: The file may be modified while hck is reading it. Use `--no-mmap`:

```
hck --no-mmap -f1,3 data.tsv
```

**Issue: Header selection finds no matching columns**

Symptom: Error about unmatched header patterns.

Solution: Check that the header names exactly match (case-sensitive). Use `-r` with a regex pattern for flexible matching:

```
hck -F '(?i)name' -r data.tsv   # Case-insensitive match
```

---

## Advanced Usage Patterns

### Combining Index and Header Selection

You can use both `-f` and `-F` together to select fields by both position and name:

```
hck -f1 -F 'email,phone' data.tsv
```

This selects field 1 (by index) plus any fields with headers matching "email" or "phone".

### Chaining hck Commands

For complex transformations, multiple hck invocations can be chained:

```
# First extract and reorder, then exclude
hck -f5,3,1,2,4,6- data.tsv | hck -e4
```

### Using hck in Scripts

hck is well-suited for use in shell scripts:

```bash
#!/bin/bash

INPUT="$1"
OUTPUT="$2"
COLUMNS="$3"

hck -Ld$'\t' -f"$COLUMNS" "$INPUT" > "$OUTPUT"
```

### Processing Very Large Files

For files that are many gigabytes:

```
# Use mmap (default) for best performance
hck -Ld$'\t' -f1,3 huge_file.tsv > output.tsv

# For compressed large files
hck -z -Ld$'\t' -f1,3 huge_file.tsv.gz > output.tsv

# Compress output to save disk space
hck -Ld$'\t' -f1,3 huge_file.tsv -Z -o output.tsv.gz
```

### Parallel Processing with xargs

For processing many files in parallel:

```
ls *.tsv | xargs -P4 -I{} sh -c 'hck -Ld$"\t" -f1,3 {} > {}.out'
```

### Conditional Field Selection

Use shell logic to dynamically determine which fields to extract:

```bash
if [ "$FORMAT" = "full" ]; then
    FIELDS="1-"
else
    FIELDS="1,3,5"
fi

hck -f"$FIELDS" data.tsv
```

---

## Internal Architecture

This section describes the internal architecture of hck for users who want to understand how the tool works or who are considering contributing to the project.

### Processing Pipeline

hck follows a pipeline architecture:

1. **Argument parsing**: Command-line arguments are parsed using `clap` with derive macros.
2. **Field range compilation**: Field specifications are parsed into `FieldRange` objects, which are sorted and optionally merged.
3. **Header processing** (if applicable): The first line is read and parsed to map header names to field positions.
4. **Exclusion processing** (if applicable): Exclude ranges are subtracted from include ranges.
5. **Parser selection**: Based on the delimiter type and field order, hck selects the appropriate parser implementation.
6. **Line processing**: Each line is split and fields are extracted according to the compiled field ranges.
7. **Output assembly**: Selected fields are joined with the output delimiter and written to the output.

### Parser Implementations

hck has three parser implementations:

1. **SingleByteDelimParser**: Used when the delimiter is a single byte, the line terminator is a single byte, regex mode is off, and fields are in sorted order. This is the fastest parser, using `memchr2` for simultaneous delimiter and newline scanning.

2. **SubStrLineParser**: Used for literal string delimiters that are more than one byte. It uses byte-level substring matching to find delimiters.

3. **RegexLineParser**: Used when regex mode is active. It compiles the delimiter pattern into a regex and uses it to split each line.

### FieldRange Structure

Internally, fields are represented as `FieldRange` structs:

- `low`: The inclusive start of the range (0-indexed internally, despite 1-indexed user input).
- `high`: The inclusive end of the range (0-indexed internally; `usize::MAX` for open-ended ranges).
- `pos`: The position in the output order. This is what enables field reordering.

The `pos` field determines where in the output each range of fields appears. When fields are specified as `3,1,2`, the field range for field 3 has `pos=0`, field 1 has `pos=1`, and field 2 has `pos=2`.

### Shuffler Vector

To support field reordering, hck uses a "shuffler" vector. This is a vector of byte vectors, one for each output position. As fields are extracted from a line, they are placed into the shuffler at their designated position. After all fields are extracted, the shuffler entries are joined with the output delimiter to produce the output line.

### Range Merging

After parsing field specifications, hck sorts the ranges by their `low` value and merges overlapping or adjacent ranges. This optimization reduces the number of range lookups during line processing. However, this merging can interact with field reordering in subtle ways when ranges overlap.

---

## Compatibility Notes

### POSIX cut Compatibility

hck is not a drop-in replacement for POSIX `cut`. Key differences:

- The default delimiter is `\s+` (regex whitespace) in hck, vs tab in `cut`.
- hck does not support `-b` (bytes) or `-c` (characters) modes.
- hck does not support `--complement` (use `-e` instead for exclusion).
- Field reordering behavior differs: `cut` sorts fields; hck preserves the specified order.
- `cut` outputs each field at most once even if specified multiple times; hck may output duplicates.

### GNU cut Compatibility

GNU `cut` has some extensions beyond POSIX. hck does not aim for compatibility with these extensions but provides equivalent or superior functionality:

- GNU `cut --complement`: Use hck `-e` instead.
- GNU `cut --output-delimiter`: hck has `-D`.
- GNU `cut -z` (null-terminated lines): Not directly supported by hck; use `tr '\0' '\n'` as a workaround.

### Platform Compatibility

hck runs on:

- Linux (x86_64, aarch64)
- macOS (x86_64, aarch64/Apple Silicon)
- Windows (with limited mmap support)

---

## Environment Variables

hck does not currently read any environment variables for configuration. All behavior is controlled through command-line arguments.

However, the `RUST_LOG` environment variable can be set to enable debug logging, which is useful for troubleshooting:

```
RUST_LOG=debug hck -f1,3 data.tsv
```

This will print debug-level log messages to stderr, including information about mmap fallback behavior and other internal decisions.

---

## Frequently Asked Questions

### How does hck differ from awk?

`awk` is a full programming language capable of arbitrary text processing. hck is a specialized tool for field extraction and reordering. hck is significantly faster than `awk` for simple field operations but cannot perform calculations, conditional logic, or multi-pass processing.

Use hck when you need to extract or reorder fields quickly. Use `awk` when you need to transform field values, perform arithmetic, or apply complex logic.

### Can hck handle CSV files with quoted fields?

No. hck does not understand CSV quoting conventions. If a field contains the delimiter character within quotes (e.g., `"Smith, John",30,NYC`), hck will split on the comma inside the quotes. For proper CSV handling, use `xsv`, `csvkit`, or `miller`.

### Why is the default delimiter `\s+` instead of tab?

The `\s+` default makes hck immediately useful for processing command output (like `ps`, `df`, `ls -l`) without specifying a delimiter. Tab-separated data also works with `\s+` (since tab is whitespace), though multiple consecutive tabs would be treated as a single delimiter rather than creating empty fields.

For strict tab-delimited parsing, use `-Ld$'\t'`.

### Can I use hck as a filter in vim?

Yes. In vim, you can filter a selection through hck:

```
:'<,'>!hck -Ld$'\t' -f1,3
```

This replaces the selected lines with the output of hck.

### Does hck support reading from multiple pipes?

hck reads from stdin or from files. You can use process substitution to provide multiple "virtual files":

```
hck -f1,3 <(command1) <(command2)
```

### How do I get the last field on each line?

Use an open-ended range selecting just the last field. If you don't know the exact field number, you can use a large number:

```
hck -f1000- data.tsv
```

This selects from field 1000 onward. If lines have fewer fields, nothing is output for those lines. Alternatively, for consistent-width data, count the fields first.

### Can hck handle newlines within fields?

No. hck uses newline (or CRLF with `--crlf`) as the line terminator. Newlines within fields (common in some CSV formats) are treated as line breaks. For data with embedded newlines, use a proper CSV parser.

---

## Version History

hck follows semantic versioning. The version at the commit documented here is **0.11.5**.

Notable capabilities available in this version:

- Full regex delimiter support
- Header-based field selection with string literals and regex patterns
- Field exclusion by index and header
- Auto-decompression for multiple formats
- BGZF output compression with configurable threads and compression level
- Memory-mapped I/O with automatic fallback
- CRLF line ending support
- Output to file (`-o`)
- Literal delimiter mode (`-L`) with single-byte fast path
- Use-input-as-output-delimiter flag (`-I`)

---

## Summary

hck is a modern, high-performance replacement for `cut` that adds regex delimiter support, field reordering, header-based field selection, field exclusion, auto-decompression, output compression, and memory-mapped I/O. It maintains the simplicity and predictability of `cut` while closing the gap to `awk` for common field extraction tasks.

The tool is optimized for speed, with multiple parser implementations selected automatically based on the input characteristics. For single-byte literal delimiters with sorted fields, hck uses a highly optimized single-pass parser that is typically 5-6x faster than `cut`.

hck is ideal for:

- Extracting specific columns from delimited data
- Reordering columns for data transformation
- Processing command output with variable whitespace
- Working with compressed genomics and bioinformatics data
- Converting between delimiter formats
- Quick exploration of large datasets

For full CSV parsing with quote awareness, or for complex text transformations requiring programming logic, other tools like `xsv`, `csvkit`, `miller`, or `awk` are more appropriate.
