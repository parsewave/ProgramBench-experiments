# sd -- Intuitive Find & Replace CLI

## Overview

sd is a command-line find-and-replace tool written in Rust, designed as a simpler and more intuitive alternative to sed. Where sed requires arcane syntax with delimiter characters and POSIX-style regex, sd uses modern regex syntax (from the Rust `regex` crate, which is similar to the regex flavors used in JavaScript and Python) and provides a clean, straightforward interface for text substitution.

sd replaces all occurrences of a pattern by default, modifies files in-place when file arguments are provided, and reads from standard input when no files are specified. It is built for speed and simplicity, avoiding the complexity of sed's multi-command pipelines, line addressing, and control flow mechanisms.

The current version is 1.0.0.

---

## Input Sources

### Standard Input (stdin)

When no file arguments are given, sd reads from standard input and writes the transformed text to standard output. This makes sd composable with other Unix tools via pipes.

```
echo "hello world" | sd "world" "universe"
```

Output:

```
hello universe
```

sd can also receive input from file redirection:

```
sd "pattern" "replacement" < input.txt > output.txt
```

Or from heredocs:

```
sd "foo" "bar" <<EOF
foo baz foo
EOF
```

When reading from stdin, sd reads all input into memory (via a memory-mapped anonymous buffer) before performing the replacement, then writes the full result to stdout.

### File Arguments

When one or more file paths are specified, sd modifies each file in-place. The original file content is replaced with the result of the substitution.

```
sd "foo" "bar" file.txt
```

Multiple files:

```
sd "TODO" "DONE" file1.txt file2.txt file3.txt
```

Files are processed in parallel using the rayon library for improved performance on multi-core systems.

---

## Regex Engine

sd uses the Rust `regex` crate (specifically `regex::bytes`) for pattern matching. This regex engine provides:

- Full Unicode support by default
- Linear-time matching guarantees (no catastrophic backtracking)
- Syntax similar to regex flavors used in JavaScript, Python, and Perl
- Byte-level matching (works on any file content, including non-UTF-8)

The Rust `regex` crate does NOT support:

- Look-ahead assertions (`(?=...)`, `(?!...)`)
- Look-behind assertions (`(?<=...)`, `(?<!...)`)
- Backreferences (`\1`, `\2`, etc. in the search pattern)
- Possessive quantifiers (`a++`, `a*+`)
- Atomic groups (`(?>...)`)

These features are unavailable because the regex engine is based on finite automata, which guarantees linear-time matching but cannot express these constructs.

### Character Classes

Character classes match a single character from a defined set.

| Syntax | Description |
|--------|-------------|
| `[abc]` | Matches `a`, `b`, or `c` |
| `[^abc]` | Matches any character except `a`, `b`, or `c` |
| `[a-z]` | Matches any character in the range `a` through `z` |
| `[a-zA-Z0-9]` | Matches any alphanumeric character |
| `[a-z&&[^aeiou]]` | Set intersection: lowercase consonants |

Shorthand character classes:

| Shorthand | Equivalent | Description |
|-----------|------------|-------------|
| `\d` | `[0-9]` | Digit |
| `\D` | `[^0-9]` | Non-digit |
| `\w` | `[a-zA-Z0-9_]` | Word character |
| `\W` | `[^a-zA-Z0-9_]` | Non-word character |
| `\s` | `[\t\n\r\f\v ]` | Whitespace |
| `\S` | `[^\t\n\r\f\v ]` | Non-whitespace |

Note: when Unicode mode is active (the default), `\d`, `\w`, and `\s` match their Unicode-aware equivalents. For example, `\d` will match digit characters from all scripts, not just ASCII digits. To restrict to ASCII, use the explicit ranges like `[0-9]`.

### Anchors

Anchors match positions in the text rather than characters.

| Syntax | Description |
|--------|-------------|
| `^` | Beginning of a line (in multi-line mode, which is the default) |
| `$` | End of a line (in multi-line mode) |
| `\b` | Word boundary |
| `\B` | Non-word boundary |
| `\A` | Beginning of the entire input (unaffected by multi-line mode) |
| `\z` | End of the entire input (unaffected by multi-line mode) |

By default, sd enables multi-line mode, meaning `^` and `$` match at line boundaries. To disable this and make `^` and `$` match only at the start and end of the entire input, use the `-f e` flag.

### Repetition (Quantifiers)

Quantifiers control how many times a preceding element can match.

| Syntax | Description |
|--------|-------------|
| `*` | Zero or more (greedy) |
| `+` | One or more (greedy) |
| `?` | Zero or one (greedy) |
| `{n}` | Exactly n times |
| `{n,}` | n or more times |
| `{n,m}` | Between n and m times (inclusive) |
| `*?` | Zero or more (lazy/non-greedy) |
| `+?` | One or more (lazy/non-greedy) |
| `??` | Zero or one (lazy/non-greedy) |
| `{n,m}?` | Between n and m times (lazy) |

Greedy quantifiers match as much text as possible, while lazy quantifiers match as little as possible.

```
# Greedy: matches the entire string "aabab"
echo "aabab" | sd "a.*b" "X"

# Lazy: matches "aab" then "ab" separately
echo "aabab" | sd "a.*?b" "X"
```

### Alternation

The pipe character `|` acts as an OR operator between alternatives:

```
echo "cat dog bird" | sd "cat|dog" "animal"
```

Output:

```
animal animal bird
```

Alternation has the lowest precedence of any operator. Use grouping to limit the scope:

```
echo "gray grey" | sd "gr(a|e)y" "brown"
```

### Grouping

Parentheses serve two purposes: grouping sub-expressions and capturing matched text.

| Syntax | Description |
|--------|-------------|
| `(pattern)` | Capturing group (numbered) |
| `(?P<name>pattern)` | Named capturing group |
| `(?:pattern)` | Non-capturing group |

Non-capturing groups are useful when you need grouping for alternation or quantifiers but do not need to reference the matched text in the replacement.

### Escape Sequences

The backslash `\` escapes metacharacters to match them literally.

Characters that must be escaped to match literally:

```
. * + ? ( ) [ ] { } | ^ $ \
```

Example:

```
echo "price: $9.99" | sd '\$\d+\.\d+' 'REDACTED'
```

Output:

```
price: REDACTED
```

### Unicode Properties

The Rust regex crate supports Unicode property escapes for matching characters by their Unicode category or property.

| Syntax | Description |
|--------|-------------|
| `\p{L}` | Any Unicode letter |
| `\p{N}` | Any Unicode number |
| `\p{P}` | Any Unicode punctuation |
| `\p{S}` | Any Unicode symbol |
| `\p{Z}` | Any Unicode separator |
| `\p{M}` | Any Unicode mark |
| `\p{C}` | Any Unicode control/other |
| `\p{Ll}` | Lowercase letter |
| `\p{Lu}` | Uppercase letter |
| `\p{Lt}` | Titlecase letter |
| `\p{Nd}` | Decimal digit |

Script-specific matching:

| Syntax | Description |
|--------|-------------|
| `\p{Greek}` | Any Greek character |
| `\p{Cyrillic}` | Any Cyrillic character |
| `\p{Han}` | Any CJK ideograph |
| `\p{Arabic}` | Any Arabic character |
| `\p{Latin}` | Any Latin character |
| `\p{Hiragana}` | Any Hiragana character |
| `\p{Katakana}` | Any Katakana character |

Negation is done with `\P` (uppercase):

```
\P{L}    # Any character that is NOT a Unicode letter
```

Or with the `^` syntax inside the braces:

```
\p{^L}   # Same as \P{L}
```

### Dot (`.`)

The dot metacharacter matches any single character except newline by default.

```
echo "abc" | sd "a.c" "X"
```

Output:

```
X
```

To make `.` also match newline characters, use the `-f s` flag (dotall mode):

```
printf "a\nc" | sd -f s "a.c" "X"
```

Output:

```
X
```

---

## Capture Groups

Capture groups allow you to extract portions of matched text and reference them in the replacement string.

### Numbered Capture Groups

Parentheses create numbered capture groups, starting at 1. The entire match is group 0.

```
echo "2024-01-15" | sd "(\d{4})-(\d{2})-(\d{2})" "$2/$3/$1"
```

Output:

```
01/15/2024
```

Reference syntax:

| Syntax | Description |
|--------|-------------|
| `$0` | The entire match |
| `$1` | First capture group |
| `$2` | Second capture group |
| `$N` | Nth capture group |

### Named Capture Groups

Named capture groups use the syntax `(?P<name>pattern)` and are referenced in the replacement with `$name`.

```
echo "John Smith" | sd "(?P<first>\w+)\s+(?P<last>\w+)" "$last, $first"
```

Output:

```
Smith, John
```

### Disambiguating Capture References

When a capture group reference is followed by text that could be part of the reference name, use braces to disambiguate.

```
# Without braces: sd interprets $1st as a group named "1st"
echo "hello" | sd "(h)" "$1st"     # ERROR: invalid capture group

# With braces: unambiguous
echo "hello" | sd "(h)" "${1}st"
```

Output:

```
stello
```

This disambiguation is required whenever a numbered capture group reference is immediately followed by alphanumeric characters. sd 1.0.0 detects this ambiguity and produces a clear error message instructing you to use braces.

### Literal Dollar Sign

To insert a literal `$` in the replacement string (in regex mode), double it:

```
echo "price 100" | sd "(\d+)" "$$$1"
```

Output:

```
price $100
```

### Non-Capturing Groups

If you need grouping but do not need to reference the match, use non-capturing groups to avoid allocating unnecessary captures:

```
echo "foobar foobaz" | sd "foo(?:bar|baz)" "replaced"
```

Output:

```
replaced replaced
```

### Nested Capture Groups

Capture groups are numbered by the position of their opening parenthesis, left to right:

```
echo "abc123" | sd "((abc)(123))" "[$1][$2][$3]"
```

Output:

```
[abc123][abc][123]
```

Here, `$1` is the outer group `(abc123)`, `$2` is `(abc)`, and `$3` is `(123)`.

### Capture Groups with Quantifiers

When a capture group is quantified (e.g., `(\d)+`), only the last match of that group is captured:

```
echo "123" | sd "(\d)+" "[$1]"
```

Output:

```
[3]
```

The group `(\d)` matches `1`, then `2`, then `3`, but only the last value `3` is retained.

---

## Smart Case Sensitivity

By default, sd uses a smart case-sensitivity heuristic:

- If the search pattern contains any uppercase ASCII characters, the search is performed case-sensitively.
- If the search pattern is entirely lowercase (or contains no ASCII letters), the search is performed case-insensitively.

This behavior is designed to "do the right thing" in common cases. For example:

```
# Lowercase pattern: case-insensitive matching
echo "Hello hello HELLO" | sd "hello" "hi"
```

Output:

```
hi hi hi
```

```
# Pattern with uppercase: case-sensitive matching
echo "Hello hello HELLO" | sd "Hello" "Hi"
```

Output:

```
Hi hello HELLO
```

Smart case can be overridden with the `-f` flag:

```
# Force case-sensitive even with lowercase pattern
echo "Hello hello HELLO" | sd -f c "hello" "hi"
```

Output:

```
Hello hi HELLO
```

```
# Force case-insensitive even with uppercase pattern
echo "Hello hello HELLO" | sd -f i "Hello" "Hi"
```

Output:

```
Hi Hi Hi
```

Smart case detection is based on the search pattern only, not the replacement string.

---

## In-Place File Modification

When file paths are provided as arguments, sd modifies files in-place. The modification process is designed to be safe and atomic.

### Atomic Writes

sd does not modify files by writing directly to them. Instead, it follows this process:

1. Read the original file content using memory-mapped I/O.
2. Perform the substitution in memory.
3. Create a temporary file in the same directory as the target file.
4. Write the substituted content to the temporary file.
5. Copy the permissions (and on Unix, the ownership) from the original file to the temporary file.
6. Atomically rename the temporary file to replace the original file.

This approach ensures that if sd crashes or is interrupted during processing, the original file remains intact. The rename operation is atomic on most filesystems, so the file is either fully replaced or not touched at all.

### Symlink Handling

As of version 1.0.0, sd correctly handles symbolic links. When the target file is a symlink, sd follows the symlink, reads the target file, and writes the result back through the symlink. The symlink itself is preserved and not replaced with a regular file.

In versions prior to 1.0.0, modifying a symlink would replace the symlink with a regular file containing the modified content, which was a bug.

The path is canonicalized before writing, so the temporary file is created in the directory of the real target file, not in the directory of the symlink.

### Permission Preservation

sd copies the file permissions from the original file to the temporary file before performing the rename. On Unix systems, this includes the file mode (read/write/execute bits). The ownership (uid/gid) of the original file is also preserved on Unix systems.

### Memory-Mapped I/O

Since version 0.6.0, sd uses memory-mapped I/O (via the `memmap2` crate) to read file contents. This is particularly beneficial for large files because:

- The operating system handles paging file content in and out of memory as needed.
- The file does not need to be read entirely into a heap-allocated buffer.
- Multiple files can be processed efficiently in parallel.

For stdin input, sd reads all input into a buffer and then creates an anonymous memory map from it, providing a consistent interface for the replacement engine.

### Parallel Processing

When multiple files are specified, sd processes them in parallel using the `rayon` crate. This takes advantage of multiple CPU cores and can significantly speed up batch operations across many files.

### Error Handling for File Operations

If any file operations fail, sd collects the errors and reports them after processing all files. The error report includes the path of each file that failed and the corresponding error message. The exit code is 1 if any file processing failed.

Specific error conditions:

- **File not found**: sd reports `invalid path: <path>` if a specified file does not exist.
- **Permission denied**: reported as an I/O error.
- **Temporary file creation failure**: reported as a failed atomic file swap.
- **Rename failure**: reported as `failed to move file: <details>`.

---

## Preview Mode

The `-p` or `--preview` flag displays the changes that would be made without actually modifying any files (or, for stdin input, simply shows the transformed output).

```
sd -p "old_function" "new_function" source.py
```

The preview output shows the lines that would be changed, with the original and replacement text highlighted. The exact format of the preview output is subject to change in future versions.

Preview mode is useful for:

- Verifying that a complex regex pattern matches the intended text.
- Checking that capture group references produce the expected substitutions.
- Reviewing batch changes across multiple files before committing them.

---

## Escape Sequences in Patterns and Replacements

sd processes escape sequences in both the search pattern and the replacement string. The following escape sequences are recognized:

| Sequence | Character |
|----------|-----------|
| `\n` | Newline (line feed) |
| `\r` | Carriage return |
| `\t` | Tab |
| `\\` | Literal backslash |
| `\'` | Literal single quote |
| `\"` | Literal double quote |
| `\xHH` | Character with hex code HH (2 hex digits) |
| `\uHHHH` | Unicode character with hex code HHHH (4 hex digits) |

These escape sequences are processed by sd before the regex engine sees the pattern. This means you can use `\n` in the search pattern to match literal newlines and in the replacement string to insert newlines.

```
# Replace newlines with spaces (joining lines)
printf "line1\nline2\nline3" | sd '\n' ' '
```

Output:

```
line1 line2 line3
```

```
# Insert newlines
echo "a,b,c" | sd ',' '\n'
```

Output:

```
a
b
c
```

When an unrecognized escape sequence is encountered (e.g., `\q`), sd preserves the literal backslash and character rather than producing an error.

### Hex and Unicode Escapes

Hex escapes allow you to specify characters by their byte value:

```
# Match a specific byte value
echo "hello" | sd '\x68' 'H'
```

Output:

```
Hello
```

Unicode escapes allow you to specify characters by their Unicode code point:

```
echo "cafe" | sd 'e' '\u00e9'
```

Output:

```
caf\u00e9
```

(The actual output would contain the e-acute character.)

---

## Differences from sed

sd is designed as a modern, simplified alternative to sed. While sed is a full-featured stream editor with its own programming language, sd focuses solely on find-and-replace operations.

### Syntax Comparison

The most immediate difference is that sd does not use delimiters around the pattern and replacement:

| Operation | sed | sd |
|-----------|-----|-----|
| Simple replacement | `sed 's/foo/bar/g'` | `sd 'foo' 'bar'` |
| In-place file edit | `sed -i 's/foo/bar/g' file` | `sd 'foo' 'bar' file` |
| Case-insensitive | `sed 's/foo/bar/gI'` | `sd -f i 'foo' 'bar'` |
| Literal strings | `sed 's/\[foo\]/bar/g'` | `sd -F '[foo]' 'bar'` |
| Multiple files | `sed -i 's/foo/bar/g' f1 f2` | `sd 'foo' 'bar' f1 f2` |

### Regex Syntax Differences

sd uses a completely different regex dialect than sed. sed uses POSIX Basic Regular Expressions (BRE) by default (or Extended Regular Expressions with `-E`), while sd uses the Rust regex syntax which is closer to Perl/JavaScript/Python regex.

| Feature | sed (BRE) | sed (ERE, -E) | sd |
|---------|-----------|---------------|-----|
| Grouping | `\(\)` | `()` | `()` |
| Alternation | `\|` | `\|` | `\|` |
| One or more | `\+` | `+` | `+` |
| Zero or one | `\?` | `?` | `?` |
| Word boundary | `\b` (GNU) | `\b` (GNU) | `\b` |
| Non-greedy | Not supported | Not supported | `*?`, `+?`, `??` |
| Named groups | Not supported | Not supported | `(?P<name>...)` |
| Unicode props | Not supported | Not supported | `\p{L}`, etc. |
| Lookaheads | Not supported | Not supported | Not supported |
| Backreferences | `\1` in pattern | `\1` in pattern | Not supported |

### Feature Comparison

Features available in sed but NOT in sd:

| Feature | sed Syntax | sd Equivalent |
|---------|------------|---------------|
| Line addressing | `sed '3s/foo/bar/'` | Not supported |
| Range addressing | `sed '3,7s/foo/bar/'` | Not supported |
| Pattern addressing | `sed '/^#/d'` | Not supported |
| Delete lines | `sed '/pattern/d'` | Not supported |
| Insert text | `sed '3i\text'` | Not supported |
| Append text | `sed '3a\text'` | Not supported |
| Print specific lines | `sed -n '5p'` | Not supported |
| Multiple commands | `sed -e 's/a/b/' -e 's/c/d/'` | Not supported (pipe multiple sd commands) |
| Command scripting | `sed -f script.sed` | Not supported |
| Hold space/pattern space | `sed 'H;g'` | Not supported |
| Labels and branching | `sed ':loop ... b loop'` | Not supported |
| Case transformation | `sed 's/foo/\U&/'` | Not supported |
| Transliteration | `sed 'y/abc/xyz/'` | Not supported |

Features available in sd but NOT in (standard) sed:

| Feature | sd Syntax | Notes |
|---------|-----------|-------|
| Non-greedy matching | `*?`, `+?` | Standard sed has no non-greedy quantifiers |
| Named capture groups | `(?P<name>...)` | Not available in POSIX sed |
| Unicode property matching | `\p{L}` | Not available in POSIX sed |
| Smart case sensitivity | Default behavior | sed is always case-sensitive unless you add `I` flag |
| Preview mode | `-p` flag | sed has no built-in preview |
| Parallel file processing | Automatic | sed processes files sequentially |
| Atomic file writes | Automatic | sed with `-i` is not atomic on most implementations |
| Whole-word matching flag | `-f w` | sed requires manual `\b` usage (GNU only) |

### Common Task Translations

Below are translations for common tasks from sed to sd.

**Replace all occurrences in a file:**

```
# sed
sed -i 's/old/new/g' file.txt

# sd
sd 'old' 'new' file.txt
```

Note: sd replaces all occurrences by default; no `g` flag is needed.

**Replace with capture groups:**

```
# sed
sed -i 's/\(first\)-\(second\)/\2-\1/g' file.txt

# sd
sd '(first)-(second)' '$2-$1' file.txt
```

Note: sd uses `$1` notation for capture references instead of `\1`.

**Case-insensitive replacement:**

```
# sed (GNU)
sed -i 's/hello/world/gI' file.txt

# sd
sd -f i 'hello' 'world' file.txt
```

**Delete matching lines (workaround):**

```
# sed
sed -i '/pattern/d' file.txt

# sd (approximate equivalent: replace the entire line including newline)
sd '^.*pattern.*\n' '' file.txt
```

**Replace text containing special characters:**

```
# sed (must escape all special chars)
sed -i 's/\[error\]/\[warning\]/g' file.txt

# sd with -F (no escaping needed)
sd -F '[error]' '[warning]' file.txt
```

**Multi-line replacement:**

```
# sed (complex, platform-dependent)
sed -i ':a;N;$!ba;s/foo\nbar/baz/' file.txt

# sd (straightforward)
sd 'foo\nbar' 'baz' file.txt
```

**Pipe with other tools:**

```
# sed
cat file.txt | sed 's/foo/bar/g'

# sd
cat file.txt | sd 'foo' 'bar'
```

**Batch replace across many files:**

```
# sed with find
find . -name "*.txt" -exec sed -i 's/foo/bar/g' {} +

# sd with fd
fd -e txt -x sd 'foo' 'bar'
```

---

## Flag Combinations

Flags can be combined in a single `-f` argument. Here is a detailed explanation of how flags interact with each other.

### `-f ci` and `-f ic` -- Case-Sensitive and Case-Insensitive Together

When both `c` and `i` are specified, the last one specified takes effect. However, since the flags are processed as a set, the behavior is that `i` wins (case-insensitive). In practice, specifying both `c` and `i` together is contradictory and should be avoided.

### `-f ms` -- Multi-Line with Dotall

This combination is useful when you want `^` and `$` to match line boundaries (multi-line) while also allowing `.` to match newlines (dotall). This lets you write patterns that span multiple lines while still using line anchors:

```
printf "start\nmiddle\nend" | sd -f ms '^start.+end$' 'replaced'
```

### `-f es` -- Disable Multi-Line with Dotall

With `e`, the anchors `^` and `$` match only the very start and end of the entire input. Combined with `s`, `.` matches newlines. This means `^.*$` would match the entire input as a single string:

```
printf "line1\nline2" | sd -f es '^.*$' 'one line'
```

### `-f wi` -- Whole Word with Case-Insensitive

This combination finds whole-word matches case-insensitively:

```
echo "Cat category CAT" | sd -f wi 'cat' 'dog'
```

Output:

```
dog category dog
```

The pattern is wrapped in `\b` anchors (`\bcat\b`) and matched case-insensitively, so "Cat" and "CAT" match but "category" does not.

### `-f wc` -- Whole Word with Case-Sensitive

```
echo "Cat category cat" | sd -f wc 'cat' 'dog'
```

Output:

```
Cat category dog
```

Only the exact lowercase "cat" as a whole word matches.

### `-f ws` -- Whole Word with Dotall

Dotall mode only affects the `.` metacharacter. Since whole-word mode wraps the pattern in `\b` anchors, the combination is generally only useful if your pattern contains `.`:

```
printf "a.b\na\nb" | sd -f ws 'a.b' 'X'
```

### `-f wm` -- Whole Word with Multi-Line

Since multi-line is the default, this is equivalent to just `-f w`. The `m` flag is effectively a no-op.

---

## Edge Cases and Special Behaviors

### Empty Replacement String

An empty replacement string effectively deletes all matches:

```
echo "hello world" | sd "world" ""
```

Output:

```
hello
```

Note the trailing space remains because only "world" was deleted, not the preceding space. To remove the space as well, include it in the pattern:

```
echo "hello world" | sd " world" ""
```

Output:

```
hello
```

### Empty Search Pattern

An empty search pattern matches the zero-width position between every character and at the start and end of the input. This inserts the replacement text at every position:

```
echo "abc" | sd "" "-"
```

Output:

```
-a-b-c-
```

### Patterns Starting with a Hyphen

If the search pattern starts with a hyphen, sd may interpret it as a flag. Use `--` to signal the end of flags:

```
echo "a-b-c" | sd -- "-" "_"
```

Output:

```
a_b_c
```

### Patterns Containing Newlines

sd processes `\n` escape sequences in both the pattern and replacement, allowing matching across line boundaries:

```
printf "foo\nbar" | sd 'foo\nbar' 'baz'
```

Output:

```
baz
```

In the replacement string, `\n` inserts a newline:

```
echo "foo bar" | sd ' ' '\n'
```

Output:

```
foo
bar
```

### Patterns with Backslashes

To match a literal backslash in the input, you need to consider both shell escaping and regex escaping. In the regex, a literal backslash is `\\`. Depending on your shell, you may need additional escaping:

```
# Match a literal backslash
echo 'a\b' | sd '\\' '/'
```

Output:

```
a/b
```

In fixed-string mode (`-F`), no regex escaping is needed, but shell escaping may still apply:

```
echo 'a\b' | sd -F '\' '/'
```

### Binary File Handling

sd operates at the byte level using `regex::bytes`, which means it can process files that are not valid UTF-8. The regex engine treats the input as a sequence of bytes, and the pattern is compiled for byte-level matching.

However, some considerations apply:

- Unicode character classes (`\p{L}`, `\w`, etc.) will only match valid UTF-8 sequences.
- The `.` metacharacter matches any byte, not any Unicode character, when used in byte mode.
- Replacement strings are expected to be valid UTF-8, but the regex engine will handle non-UTF-8 input gracefully.
- For truly binary files (containing null bytes, control characters, etc.), sd will process them but the results may not be meaningful if the replacement text is designed for text content.

### Very Large Files

Thanks to memory-mapped I/O, sd can handle very large files efficiently. The file is not loaded entirely into heap memory; instead, the operating system maps the file into the process's virtual address space and pages content in and out as needed.

For stdin input, however, the entire input must be read into memory before processing, so very large stdin inputs may consume significant memory.

### Unicode in Patterns and Replacements

sd has full Unicode support in both patterns and replacement strings:

```
echo "cafe" | sd "e$" "\u00e9"
```

Unicode property escapes work in patterns:

```
echo "abc123" | sd '\p{N}' '#'
```

Output:

```
abc###
```

Mixed-script text is handled correctly:

```
echo "Hello World" | sd 'World' 'World'
```

### Dollar Signs in Replacement Text

In regex mode, the `$` character in the replacement string has special meaning (it introduces capture group references). To insert a literal `$`, use `$$`:

```
echo "price 100" | sd '(\d+)' '$$${1}'
```

Output:

```
price $100
```

In fixed-string mode (`-F`), `$` has no special meaning:

```
echo "price 100" | sd -F '100' '$100'
```

Output:

```
price $100
```

### No Matches Found

When the search pattern does not match any text in the input, sd outputs the input unchanged. For file arguments, the file is not modified (the atomic write is not performed). The exit code is still 0 (success) because "no matches" is not considered an error.

### Replacement Limits

The `-n` flag limits the number of replacements per file:

```
echo "aaa" | sd -n 1 "a" "b"
```

Output:

```
baa
```

```
echo "aaa" | sd -n 2 "a" "b"
```

Output:

```
bba
```

The default value of 0 means no limit (replace all occurrences).

### Overlapping Matches

The regex engine does not find overlapping matches. Each match consumes the matched text, and the next search begins after the end of the previous match:

```
echo "aaa" | sd "aa" "b"
```

Output:

```
ba
```

The first "aa" is matched and replaced with "b", leaving "a". The remaining "a" does not match "aa", so it is left unchanged.

---

## Detailed Regex Syntax Reference

This section provides a comprehensive reference for the regex syntax supported by sd (the Rust `regex` crate).

### Literals

Any character that is not a metacharacter matches itself literally. The metacharacters are:

```
. * + ? ( ) [ ] { } | ^ $ \
```

To match a metacharacter literally, precede it with a backslash.

### Character Class Syntax

Character classes are enclosed in square brackets. Inside a character class, the following metacharacters apply:

| Character | Meaning inside `[...]` |
|-----------|------------------------|
| `]` | Closes the class (escape with `\]` or place first) |
| `\` | Escape character |
| `^` | Negation (only when first character) |
| `-` | Range (e.g., `a-z`; escape or place first/last for literal) |
| `&&` | Set intersection |

Examples:

```
[abc]          # Matches a, b, or c
[^abc]         # Matches anything except a, b, or c
[a-zA-Z]       # Matches any ASCII letter
[a-z&&[^m-p]]  # Matches a-l or q-z (intersection with complement)
[\[\]]         # Matches [ or ]
[-abc]         # Matches -, a, b, or c (literal - at start)
```

### POSIX Character Classes

The Rust regex crate supports ASCII POSIX classes with the `[:class:]` syntax inside brackets:

| Class | Equivalent |
|-------|------------|
| `[[:alnum:]]` | `[a-zA-Z0-9]` |
| `[[:alpha:]]` | `[a-zA-Z]` |
| `[[:ascii:]]` | `[\x00-\x7F]` |
| `[[:blank:]]` | `[\t ]` |
| `[[:cntrl:]]` | `[\x00-\x1F\x7F]` |
| `[[:digit:]]` | `[0-9]` |
| `[[:graph:]]` | `[!-~]` |
| `[[:lower:]]` | `[a-z]` |
| `[[:print:]]` | `[ -~]` |
| `[[:punct:]]` | ``[!-/:-@[-`{-~]`` |
| `[[:space:]]` | `[\t\n\v\f\r ]` |
| `[[:upper:]]` | `[A-Z]` |
| `[[:word:]]` | `[a-zA-Z0-9_]` |
| `[[:xdigit:]]` | `[0-9A-Fa-f]` |

### Greedy vs. Lazy Matching

All quantifiers are greedy by default: they match as much text as possible. Adding `?` after the quantifier makes it lazy: it matches as little text as possible.

```
# Greedy: matches "<b>bold</b>"
echo "<b>bold</b>" | sd "<.*>" "X"
# Output: X

# Lazy: matches "<b>" and "</b>" separately
echo "<b>bold</b>" | sd "<.*?>" "X"
# Output: XboldX
```

### Anchors in Multi-Line Mode

Since multi-line mode is enabled by default in sd, `^` and `$` match at line boundaries:

```
printf "line1\nline2\nline3" | sd '^line' 'LINE'
```

Output:

```
LINE1
LINE2
LINE3
```

To match only at the very beginning or end of the entire input, use `\A` and `\z`:

```
printf "line1\nline2\nline3" | sd '\Aline' 'LINE'
```

Output:

```
LINE1
line2
line3
```

Alternatively, use the `-f e` flag to disable multi-line mode.

### Word Boundaries

The `\b` anchor matches at positions where a word character is adjacent to a non-word character (or the start/end of the string). A word character is defined as `[a-zA-Z0-9_]`.

```
echo "cat scatter category" | sd '\bcat\b' 'dog'
```

Output:

```
dog scatter category
```

The `-f w` flag automatically wraps the pattern in `\b...\b`:

```
echo "cat scatter category" | sd -f w 'cat' 'dog'
```

Output:

```
dog scatter category
```

The `\B` anchor matches at positions where the adjacent characters are both word characters or both non-word characters:

```
echo "cat scatter" | sd '\Bcat' 'dog'
```

Output:

```
cat sdogter
```

### Repetition Ranges

Curly brace quantifiers specify exact counts or ranges:

```
# Exactly 3 digits
echo "12 123 1234" | sd '\b\d{3}\b' 'X'
# Output: 12 X 1234

# 2 to 4 digits
echo "1 12 123 1234 12345" | sd '\b\d{2,4}\b' 'X'
# Output: 1 X X X 12345

# 3 or more digits
echo "12 123 1234" | sd '\b\d{3,}\b' 'X'
# Output: 12 X X
```

### Alternation Precedence

Alternation has the lowest precedence. This means `cat|dog food` matches "cat" or "dog food", not "cat food" or "dog food":

```
echo "cat food, dog food" | sd 'cat|dog food' 'X'
```

Output:

```
X food, X
```

To match "cat food" or "dog food", use grouping:

```
echo "cat food, dog food" | sd '(cat|dog) food' 'X'
```

Output:

```
X, X
```

### Flags Inline in the Pattern

The Rust regex crate supports inline flag groups within the pattern itself using the `(?flags:...)` syntax:

| Syntax | Description |
|--------|-------------|
| `(?i:pattern)` | Case-insensitive for this group only |
| `(?s:pattern)` | Dotall mode for this group only |
| `(?m:pattern)` | Multi-line for this group only |
| `(?-i:pattern)` | Disable case-insensitive for this group |
| `(?is:pattern)` | Combine flags |

Example:

```
echo "HELLO world" | sd '(?i:hello) (?-i:world)' 'X'
```

Output:

```
X
```

The inline `(?i:hello)` matches "HELLO" case-insensitively, while `(?-i:world)` matches "world" case-sensitively.

You can also set flags for the rest of the pattern using `(?flags)` without a group:

```
echo "HELLO world" | sd '(?i)hello world' 'X'
```

Output:

```
X
```

---

## Error Handling

sd produces clear error messages for common error conditions.

### Invalid Regex

If the search pattern is not a valid regular expression, sd reports the error:

```
sd '(' 'replacement' file.txt
```

This produces an error message from the regex engine indicating that the group was not closed.

### Invalid Capture Group Reference

If the replacement string contains an ambiguous numbered capture group reference, sd produces an error:

```
echo "hello" | sd '(h)' '$1ello'
```

Error message (as of v1.0.0):

```
error: Invalid replace capture reference: "$1ello"
Use curly braces to disambiguate it `${1}ello`
```

### File Not Found

```
sd 'foo' 'bar' nonexistent.txt
```

Error:

```
invalid path: nonexistent.txt
```

### Permission Denied

If sd cannot read a file or write to it, the underlying I/O error is reported.

### Multiple File Errors

When processing multiple files, if some fail and others succeed, sd reports errors for all failed files and returns a non-zero exit code. The error message lists each failed file and its error:

```
Failed processing some inputs
  file1.txt: Permission denied
  file2.txt: invalid path: file2.txt
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success. All files were processed successfully, or stdin was processed successfully. This is returned even if no matches were found. |
| 1 | Error. One or more errors occurred during processing: invalid regex, file not found, permission denied, invalid capture group syntax, etc. |
| 101 | Panic. An unexpected internal error occurred (Rust panic). |

---

## Version History

### Version 1.0.0 (November 7, 2023)

This is the first stable release of sd. Major changes include:

**Breaking Changes:**
- The `--string-mode` / `-s` flag has been renamed to `--fixed-strings` / `-F`. The old flags continue to work but are deprecated and hidden from help output.
- Invalid capture group references in replacement text (e.g., `$1foo`) now produce an error message instructing the user to use braces (`${1}foo`). Previously, this would silently produce incorrect output.

**Improvements:**
- Fixed a bug where modifying a symlink would replace the symlink with a regular file. Symlinks are now preserved.
- Shell completions and man pages are now included in release artifacts (in the `gen/` directory).
- Improved error messages for replacement failures.
- Clarified that `$$` represents a literal `$` in replacement text.
- Enhanced help text describing in-place file modification.
- Automated man page generation using `clap_mangen`.

**Platform Support:**
- Added ARM targets: `arm-unknown-linux-gnueabihf`, `aarch64-apple-darwin`, `armv7-unknown-linux-gnueabihf`.
- Restored Windows builds for `x86_64-pc-windows-gnu` and `x86_64-windows-musl`.
- Added `aarch64-ubuntu-linux-musl` target.
- Release binaries are now stripped for reduced file size.

**Internal Changes:**
- Migrated from `structopt` to `clap` v4.
- Replaced deprecated `memmap` crate with `memmap2`.
- Replaced deprecated `atty` crate with `is-terminal`.
- Migrated to Rust 2021 edition.
- Moved asset generation to `cargo-xtask`.

### Version 0.6.2

**Bug Fixes:**
- Corrected pre-allocated memory buffer sizing.
- Resolved test failures.

### Version 0.6.0 (June 15, 2019)

**New Features:**
- Memory-mapped file processing for efficiently handling files of any size.
- Added `-p` / `--preview` flag for previewing changes before applying them.
- Added `w` regex flag for whole-word matching.

**Changes:**
- `--in-place` is now the default behavior when file arguments are provided (the flag is no longer needed).

### Version 0.5.0 (February 22, 2019)

**New Features:**
- Added Windows platform support.

### Version 0.4.2 (January 2, 2019)

**Improvements:**
- Extended Unicode and special character support in regex replacement expressions.
- Fixed edge cases with unescaped character handling.

### Version 0.4.1 (January 1, 2019)

**Performance:**
- Substantial performance improvements to the replacement engine.

### Version 0.4.0 (December 30, 2018)

**New Features:**
- Regex flag options (`-f` / `--flags`): multi-line (`m`), case-sensitive (`c`), case-insensitive (`i`).
- Smart case-sensitivity detection enabled by default.
- Support for processing multiple files simultaneously.

### Version 0.3.0 (December 29, 2018)

**Breaking Changes:**
- Restructured the CLI syntax. File paths are now provided as trailing positional arguments rather than via the `-i`/`--input` flag. The `-i` flag was renamed to `--in-place`.

**Improvements:**
- Implemented atomic file writing for data integrity during in-place modifications.

---

## Practical Usage Patterns

This section covers common real-world use cases and how to accomplish them with sd.

### Renaming Variables in Source Code

```
sd -f w 'oldVariable' 'newVariable' src/*.py
```

The `-f w` flag ensures that only whole-word matches are replaced, preventing unintended changes to variables like `oldVariableName`.

### Updating Import Paths

```
sd 'from "react"' 'from "preact"' src/**/*.js
```

Or use `fd` for recursive file discovery:

```
fd -e js -x sd 'from "react"' 'from "preact"'
```

### Reformatting Dates

```
# Convert YYYY-MM-DD to MM/DD/YYYY
sd '(\d{4})-(\d{2})-(\d{2})' '$2/$3/$1' data.csv
```

### Extracting and Reformatting Data

```
# Reformat "Last, First" to "First Last"
sd '(\w+),\s*(\w+)' '$2 $1' names.txt
```

### Removing Lines Matching a Pattern

sd does not have a "delete line" command like sed's `d`. However, you can approximate it by matching the entire line including the newline:

```
sd '^.*DEBUG.*\n' '' logfile.txt
```

Note that this also works without the trailing `\n` for the last line of a file, but lines in the middle of the file need the `\n` to avoid leaving a blank line.

### Commenting Out Lines

```
sd '^(.*important.*)$' '# $1' config.txt
```

This prepends `# ` to every line containing the word "important".

### Uncommenting Lines

```
sd '^# (.*)' '$1' config.txt
```

This removes the `# ` prefix from commented lines.

### Removing Trailing Whitespace

```
sd '\s+$' '' file.txt
```

### Converting Line Endings

```
# CRLF to LF
sd '\r\n' '\n' file.txt

# LF to CRLF
sd '\n' '\r\n' file.txt
```

### Wrapping Text in Tags

```
echo "important text" | sd '(.+)' '<p>$1</p>'
```

Output:

```
<p>important text</p>
```

### Collapsing Multiple Blank Lines

```
sd '\n{3,}' '\n\n' file.txt
```

This replaces runs of 3 or more consecutive newlines with exactly 2 newlines (one blank line).

### Extracting Information with Named Groups

```
echo 'User: john, Age: 30, Email: john@example.com' | \
  sd 'User: (?P<name>\w+), Age: (?P<age>\d+), Email: (?P<email>\S+)' \
     'Name=$name Age=$age Email=$email'
```

Output:

```
Name=john Age=30 Email=john@example.com
```

### Working with JSON

```
# Change a value in a simple JSON-like structure
echo '{"name": "old"}' | sd '"name": "old"' '"name": "new"'
```

For more complex JSON transformations, dedicated tools like `jq` are recommended, but sd works well for simple key-value replacements.

### Working with CSV Data

```
# Replace a column separator
sd ',' '\t' data.csv

# Quote a specific column (the third field)
sd '^([^,]*,[^,]*),([^,]*)' '$1,"$2"' data.csv
```

### Environment Variable Substitution in Config Files

```
sd 'DATABASE_HOST=localhost' 'DATABASE_HOST=production.db.example.com' .env
```

Or with fixed-string mode to avoid any regex interpretation:

```
sd -F 'DATABASE_HOST=localhost' 'DATABASE_HOST=production.db.example.com' .env
```

### Batch Renaming with fd

sd pairs well with `fd` (a fast file finder) for batch operations:

```
# Update all Python imports across a project
fd -e py -x sd 'import old_module' 'import new_module'

# Update version strings in all Cargo.toml files
fd -g 'Cargo.toml' -x sd 'version = "0\.9\.0"' 'version = "1.0.0"'

# Replace across specific file types
fd -e rs -e toml -x sd 'old_crate' 'new_crate'
```

---

## Advanced Regex Patterns

### Matching IP Addresses

```
sd '\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b' 'REDACTED' access.log
```

### Matching Email Addresses

```
sd '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}' 'REDACTED' contacts.txt
```

### Matching URLs

```
sd 'https?://[^\s]+' 'URL_REMOVED' document.txt
```

### Matching Quoted Strings

```
# Double-quoted strings
sd '"[^"]*"' '""' source.txt

# Single-quoted strings
sd "'[^']*'" "''" source.txt
```

### Matching HTML Tags

```
# Remove all HTML tags
sd '<[^>]+>' '' page.html

# Replace a specific tag
sd '<b>(.*?)</b>' '<strong>$1</strong>' page.html
```

### Matching Repeated Characters

```
# Collapse repeated characters
echo "heeellooo" | sd '(.)\1+' '$1'
```

Note: this does NOT work in sd because the Rust regex engine does not support backreferences in the search pattern. The `\1` syntax is not available. To collapse repeated characters, you would need to target specific characters:

```
echo "heeellooo" | sd 'e+' 'e' | sd 'o+' 'o' | sd 'l+' 'l'
```

### Matching Balanced Structures

The Rust regex engine does not support recursive patterns or balancing groups. Matching balanced parentheses, brackets, or nested structures is not possible with sd. For these tasks, consider dedicated parsers or tools.

### Zero-Width Assertions Available

While sd does not support look-ahead or look-behind, it does support these zero-width assertions:

| Assertion | Description |
|-----------|-------------|
| `\b` | Word boundary |
| `\B` | Non-word boundary |
| `^` | Start of line (or input with `-f e`) |
| `$` | End of line (or input with `-f e`) |
| `\A` | Start of input (always) |
| `\z` | End of input (always) |

---

## Shell Interaction

### Quoting Patterns

Different shells handle quoting differently. In general:

**Bash/Zsh:**
- Use single quotes for patterns to avoid shell expansion: `sd 'pattern' 'replacement'`
- For patterns containing single quotes, use `$'...'` syntax: `sd $'it\'s' "it is"`
- Double quotes allow variable expansion: `sd "$VAR" "replacement"`

**Fish:**
- Single and double quotes behave similarly: `sd 'pattern' 'replacement'`

**PowerShell:**
- Use single quotes for literal strings: `sd 'pattern' 'replacement'`

### Escaping Considerations

When using sd in a pipeline or script, be aware of the multiple layers of escaping:

1. **Shell escaping**: The shell interprets the command line first. Characters like `$`, `\`, `"`, `` ` ``, `!` may need quoting.
2. **sd unescape processing**: sd processes escape sequences like `\n`, `\t`, `\xHH`, `\uHHHH`.
3. **Regex escaping**: The regex engine interprets metacharacters.

For a literal backslash in the search pattern:

```
# Shell passes \\\\ to sd, sd sees \\, regex engine matches literal \
echo 'a\b' | sd '\\\\' '/'
```

But in practice, depending on the shell:

```
# In bash with single quotes, only regex escaping applies
echo 'a\b' | sd '\\' '/'
```

To avoid complexity, use `-F` for literal string matching whenever possible:

```
echo 'a\b' | sd -F '\' '/'
```

### Stdin from Pipes vs. Files

When using pipes, be aware that sd receives the piped data as stdin and writes to stdout. No files are modified. To save the result, redirect stdout:

```
cat input.txt | sd 'foo' 'bar' > output.txt
```

When file arguments are given, sd does NOT write to stdout (unless `-p` is used for preview). The files are modified in-place:

```
sd 'foo' 'bar' input.txt    # input.txt is modified
```

---

## Performance Considerations

sd is designed for high performance:

- **Memory-mapped I/O** avoids unnecessary memory allocation for file reading.
- **Parallel processing** via rayon processes multiple files simultaneously.
- **Efficient regex engine** with linear-time guarantees means patterns never cause exponential blowup.
- **Minimal overhead** compared to sed for simple replacements.

Benchmarks (from the sd README) show sd outperforming sed by roughly 2x-12x depending on the operation and input size. The performance advantage is most pronounced on large files and complex patterns.

For optimal performance:

- Process multiple files in a single sd invocation rather than calling sd once per file.
- Use `-F` for literal string matching when regex is not needed (avoids regex compilation overhead).
- Be specific with patterns to reduce the number of match attempts.

---

## Limitations

sd is intentionally limited in scope compared to sed. It does NOT support:

1. **Line addressing or ranges**: Cannot target specific line numbers or ranges of lines.
2. **Multiple commands**: Cannot chain multiple find-and-replace operations in a single invocation. Use pipes to chain multiple sd commands.
3. **Delete/insert/append commands**: Cannot delete, insert, or append lines.
4. **Hold space**: No concept of sed's hold space or pattern space.
5. **Labels and branching**: No control flow within a single invocation.
6. **Case transformation**: Cannot convert matched text to upper/lower case (sed's `\U`, `\L`).
7. **Transliteration**: Cannot perform character-by-character mapping (sed's `y///`).
8. **Look-around assertions**: The regex engine does not support look-ahead or look-behind.
9. **Backreferences in patterns**: Cannot reference earlier capture groups in the search pattern.
10. **In-place backup**: No option to create a backup of the original file before modification (unlike sed's `-i.bak`).
11. **Recursive directory processing**: sd does not traverse directories. Use `fd` or `find` to discover files, then pipe to sd.

These limitations are by design. sd focuses on doing one thing well: find and replace.

---

## Comparison with Other Tools

### sd vs. sed

See the detailed "Differences from sed" section above.

### sd vs. perl -pe

Perl's one-liner mode (`perl -pe 's/find/replace/g'`) is more powerful than sd (supporting look-ahead/behind, backreferences, and arbitrary Perl code in the replacement), but has a steeper learning curve and more complex syntax. sd is preferred when a simple, fast replacement is needed.

### sd vs. tr

`tr` performs character-by-character translation (transliteration), not pattern-based replacement. It cannot match multi-character patterns, use regex, or handle capture groups. sd and tr solve different problems.

### sd vs. awk

`awk` is a full programming language for text processing. While it can perform find-and-replace with `gsub()`, it is overkill for simple substitutions. sd is faster and simpler for pure find-and-replace tasks.

### sd vs. ripgrep (rg)

`rg` (ripgrep) is a search tool that uses the same Rust regex engine as sd. However, rg is for finding matches, while sd is for replacing them. They complement each other well:

```
# Find all matches first
rg 'pattern' src/

# Then replace
sd 'pattern' 'replacement' src/*.rs
```

---

## Troubleshooting

### "invalid regex" Error

Check your regex syntax. Common mistakes:

- Unmatched parentheses: `(` without `)`.
- Unmatched brackets: `[` without `]`.
- Invalid escape sequences in the regex.
- Using sed-specific syntax like `\(` for grouping (use `(` instead).
- Using features not supported by the Rust regex engine (look-ahead, backreferences).

### Replacement Not Working as Expected

- Check if smart case is interfering. Use `-f c` for explicit case-sensitive matching.
- Verify that the pattern matches what you expect using `-p` (preview mode).
- Remember that sd replaces all occurrences by default.
- Check if quantifiers are greedy when you want lazy, or vice versa.
- Remember that `^` and `$` match line boundaries by default (multi-line mode is on).

### Pattern Not Matching Across Lines

By default, `.` does not match newlines. Use `-f s` (dotall mode) to make `.` match newlines, or use `\n` explicitly in the pattern:

```
# Using dotall
printf "foo\nbar" | sd -f s 'foo.bar' 'replaced'

# Using explicit \n
printf "foo\nbar" | sd 'foo\nbar' 'replaced'
```

### Shell Eating Special Characters

If your pattern contains characters special to your shell (`$`, `!`, `\`, etc.), use single quotes in bash/zsh:

```
sd '$HOME' '/home/user' file.txt     # WRONG: shell expands $HOME
sd '$HOME' '/home/user' file.txt     # Also check that single quotes are used
```

Correct:

```
sd '\$HOME' '/home/user' file.txt    # Escape the $ for regex
sd -F '$HOME' '/home/user' file.txt  # Or use fixed-string mode
```

### Capture Group Ambiguity Error

If you see an error about invalid capture group references, wrap the group number in braces:

```
# Error: $1st is ambiguous
sd '(.)' '$1st'

# Fix: use braces
sd '(.)' '${1}st'
```

---

## Installation

sd can be installed through various methods:

**Via Cargo (Rust package manager):**

```
cargo install sd
```

**Via package managers:**

sd is available in many system package managers. Check [Repology](https://repology.org/project/sd-find-replace/versions) for availability on your platform.

