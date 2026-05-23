# gron -- Make JSON Greppable

## Overview

gron transforms JSON into discrete assignment statements to make it easier to `grep` for
what you want and see the absolute path to it. It can also convert back from the assignment
format to JSON using its "ungron" mode. The name stands for "GReppable jsON."

JSON is a widely used data format, but it is notoriously difficult to search through with
standard Unix text-processing tools like `grep`, `sed`, and `awk`. The core problem is that
JSON is a hierarchical, tree-structured format, while these tools operate on flat,
line-oriented text. A value buried six levels deep in a JSON document has no self-contained
line that tells you both what the value is and how to reach it.

gron solves this by flattening JSON into a set of discrete assignment statements. Each
statement is a single line that contains the full path from the root of the document to a
leaf value, along with that value. This makes every value independently greppable.
After filtering the lines you want, gron can reassemble them back into valid JSON with
its `--ungron` flag.

The output of gron is also valid JavaScript. You can pipe it into `node` and it will
execute without error, building the same data structure in memory. This is by design: the
assignment syntax was chosen to be both human-readable and machine-executable.

### Motivating Example

Suppose you have a large JSON API response and you want to find where the user's email
address lives. With raw JSON, you would need to visually scan the nested structure or write
a jq query. With gron, you simply pipe the output through grep:

```bash
$ gron api_response.json | grep "email"
json.users[0].contact.email = "alice@example.com";
json.users[1].contact.email = "bob@example.com";
json.settings.notification_email = "admin@example.com";
```

Each line tells you the exact path to the value. You can then use `gron --ungron` to turn
the filtered output back into valid JSON:

```bash
$ gron api_response.json | grep "users\[0\]" | gron --ungron
{
  "users": [
    {
      "contact": {
        "email": "alice@example.com"
      }
    }
  ]
}
```

---

## Options Reference

### `-u, --ungron`

Activates un-gron mode. Instead of converting JSON to assignment statements, this mode
does the reverse: it reads gron-format assignment statements from the input source and
reconstructs the original JSON structure.

The input must consist of valid gron assignment statements, one per line. Each statement
is parsed, and the assignments are merged together to build a JSON object or array.
The resulting JSON is pretty-printed to standard output.

This flag is the inverse operation of the default gron behavior. The round-trip property
holds: gronning a JSON document and then ungronning the result produces a JSON document
that is semantically equivalent to the original (though formatting and key order may differ).

```bash
# Convert gron output back to JSON
echo 'json = {};
json.name = "Tom";
json.age = 30;' | gron --ungron
```

Output:
```json
{
  "age": 30,
  "name": "Tom"
}
```

### `-c, --colorize`

Forces colorized output even when standard output is not connected to a terminal. By
default, gron colorizes its output only when it detects that stdout is a TTY. The `-c`
flag overrides this detection and forces color codes into the output regardless.

This is useful when piping gron output into a pager that supports ANSI color codes:

```bash
gron large.json -c | less -R
```

The color scheme uses ANSI escape sequences to distinguish different token types in the
output. See the "Colorized Output" section for the full color mapping.

### `-m, --monochrome`

Forces monochrome (no color) output even when standard output is connected to a terminal.
This is the opposite of `-c`. When `-m` is specified, gron suppresses all ANSI color
escape sequences from its output.

This is useful when you want to redirect terminal output to a file without color codes,
or when your terminal does not support ANSI colors.

If both `-c` and `-m` are specified, the behavior is determined by flag precedence in the
implementation. Generally, `-m` takes priority, producing monochrome output.

### `-s, --stream`

Activates streaming mode. In this mode, gron treats each line of input as a separate,
independent JSON document. Each line is gronned individually, and the results for
successive lines are prefixed with array-index notation to distinguish them.

This is designed for newline-delimited JSON (NDJSON) input, where each line is a
self-contained JSON value. See the "Streaming Mode" section for detailed behavior.

```bash
echo '{"a": 1}
{"b": 2}' | gron --stream
```

Output:
```
json[0] = {};
json[0].a = 1;
json[1] = {};
json[1].b = 2;
```

### `-j, --json`

Switches the output format from gron assignment statements to a JSON stream
representation. Instead of producing lines like `json.name = "Tom";`, gron outputs a
JSON array for each statement, where the array contains the path components and the
value.

When used alone, this converts JSON input into a JSON-stream representation of the
assignments. When combined with `--ungron`, it reads JSON-stream format statements
and converts them back to regular JSON.

See the "JSON Output Mode" section for the detailed format specification.

### `-v, --values`

Outputs only the values (the right-hand side of each assignment), one per line. The
paths, equals signs, and semicolons are all omitted. Only scalar values are output;
container initializations (`{}` and `[]`) are skipped.

```bash
echo '{"name": "Tom", "age": 30}' | gron --values
```

Output:
```
"Tom"
30
```

### `--no-sort`

Disables sorting of the output. By default, gron sorts its output lines alphabetically
by the full assignment path. This produces deterministic, reproducible output regardless
of the order keys appear in the input JSON.

With `--no-sort`, gron outputs statements in the order they are encountered during the
depth-first traversal of the JSON structure. This can be faster for very large inputs
because it avoids the sorting step.

### `-k, --insecure`

Disables TLS certificate validation when fetching JSON from HTTPS URLs. This allows
gron to connect to servers with self-signed certificates, expired certificates, or
certificates that do not match the hostname.

This flag is only meaningful when the input source is an HTTPS URL. It has no effect
when reading from a file or stdin.

```bash
gron --insecure https://self-signed.example.com/api/data
```

### `-x, --proxy`

Sets the proxy URL to use for HTTP(S) requests. The value should be a full URL
including the protocol scheme (e.g., `http://proxy.example.com:8080`).

This flag only applies when fetching JSON from a URL. It overrides any proxy
configuration set via environment variables (`HTTP_PROXY`, `HTTPS_PROXY`).

```bash
gron --proxy http://myproxy:3128 https://api.example.com/data
```

### `--noproxy`

Specifies a comma-separated list of hostnames or host patterns that should bypass
the proxy. Traffic to these hosts is sent directly, even when a proxy is configured.

Supports wildcard suffix matching. For example, `*.example.com` matches all
subdomains of `example.com`.

```bash
gron --proxy http://myproxy:3128 --noproxy "localhost,*.internal.net" https://api.example.com/data
```

---

## Gron Assignment Format Specification

The core of gron is its assignment format. This section provides a complete specification
of the format, covering every aspect of how JSON is represented as discrete assignment
statements.

### General Structure

Each gron statement is a single line of text with the following structure:

```
<path> = <value>;
```

Where:
- `<path>` is a chain of property accesses and array index operations starting from the
  root identifier `json`
- `=` is the assignment operator, surrounded by single spaces
- `<value>` is a JSON-compatible value representation
- `;` is the statement terminator

Every statement ends with a semicolon and a newline. The equals sign is always
surrounded by exactly one space on each side.

### The Root Identifier

The root of every gron path is the bare identifier `json`. This serves as the variable
name for the top-level JSON value. Every gron output begins with a statement that
initializes this root:

- For a top-level object: `json = {};`
- For a top-level array: `json = [];`
- For a top-level scalar: `json = <value>;`

The root identifier is always `json` and cannot be changed via command-line options.

### Path Construction

Paths are built by chaining property access operations onto the root identifier. There
are three types of path components:

#### Dot Notation (Bare Identifiers)

When a JSON object key is a valid JavaScript identifier, it is accessed using dot
notation:

```
json.name = "Tom";
json.user.address.city = "NYC";
```

A key qualifies for dot notation when it satisfies all of the following conditions:

1. It is not empty.
2. It is not a JavaScript reserved word (see "Reserved Words" below).
3. Its first character is a valid identifier start character.
4. All subsequent characters are valid identifier continuation characters.

Valid identifier start characters include:
- Unicode letters (categories Lu, Ll, Lm, Lo, Nl)
- Dollar sign (`$`)
- Underscore (`_`)

Valid identifier continuation characters include all start characters plus:
- Unicode combining marks (categories Mn, Mc)
- Decimal digit numbers (category Nd)
- Connector punctuation (category Pc)

#### Bracket Notation with Quoted Keys

When a JSON object key does not qualify as a valid JavaScript identifier, it is
accessed using bracket notation with a quoted string:

```
json["special-key"] = "value";
json["key with spaces"] = "value";
json["123numeric"] = "value";
json[""] = "value";
json["class"] = "value";
```

The quoted key inside brackets follows JSON string escaping rules. The key is
enclosed in double quotes within square brackets.

Keys that require bracket notation include:
- Keys containing hyphens, spaces, dots, or other punctuation
- Keys starting with a digit
- Keys that are JavaScript reserved words (`class`, `return`, `function`, etc.)
- Empty string keys
- Keys containing special characters like quotes or backslashes

#### Bracket Notation with Numeric Indices

Array elements are accessed using bracket notation with zero-based integer indices:

```
json[0] = "first";
json[1] = "second";
json[2] = "third";
```

Numeric indices are written without quotes inside the brackets. They are always
non-negative integers starting from zero, incrementing by one for each successive
element.

### Path Examples

Given this JSON:

```json
{
  "users": [
    {
      "name": "Alice",
      "tags": ["admin", "user"],
      "meta-data": {"created": "2024-01-01"}
    }
  ]
}
```

gron produces:

```
json = {};
json.users = [];
json.users[0] = {};
json.users[0].meta-data = {};        -- Note: bracket notation would be used here
json.users[0]["meta-data"] = {};
json.users[0]["meta-data"].created = "2024-01-01";
json.users[0].name = "Alice";
json.users[0].tags = [];
json.users[0].tags[0] = "admin";
json.users[0].tags[1] = "user";
```

Note that `meta-data` uses bracket notation because the hyphen makes it an invalid
JavaScript identifier, while `name`, `users`, `tags`, and `created` all use dot
notation because they are valid identifiers.

### Container Initialization Statements

Before any properties or elements of a container (object or array) can be assigned,
the container itself must be initialized. gron emits an initialization statement for
every container in the JSON structure:

- Objects are initialized as: `json.path = {};`
- Arrays are initialized as: `json.path = [];`

These initialization statements appear before any child assignments for that
container. They ensure that the ungron process can correctly reconstruct the types
of intermediate containers.

For example, a nested structure:

```json
{"a": {"b": [1, 2]}}
```

Produces:

```
json = {};
json.a = {};
json.a.b = [];
json.a.b[0] = 1;
json.a.b[1] = 2;
```

The `json = {};` line initializes the root object. The `json.a = {};` line initializes
the nested object. The `json.a.b = [];` line initializes the array. Only then do the
leaf values `1` and `2` appear.

---

## Value Representation

gron represents JSON values on the right-hand side of assignments using a syntax that
is compatible with both JSON and JavaScript.

### Strings

String values are enclosed in double quotes and use JSON-compatible escaping:

```
json.name = "Tom";
json.greeting = "Hello, World!";
json.empty = "";
```

The following escape sequences are used within strings:

| Character        | Escape Sequence |
|------------------|-----------------|
| Backslash (`\`)  | `\\`            |
| Double quote (`"`) | `\"`          |
| Newline          | `\n`            |
| Carriage return  | `\r`            |
| Tab              | `\t`            |
| Backspace        | `\b`            |
| Form feed        | `\f`            |
| Unicode U+2028 (Line Separator) | `\u2028` |
| Unicode U+2029 (Paragraph Separator) | `\u2029` |
| Other control characters (U+0000-U+001F) | `\uXXXX` |

The Unicode line separator (U+2028) and paragraph separator (U+2029) are explicitly
escaped to maintain JavaScript compatibility, since these characters are valid in JSON
strings but not in JavaScript string literals.

All other Unicode characters (including emoji, CJK characters, and other non-ASCII
characters) are passed through unescaped. gron does not escape characters that do not
require escaping.

### Numbers

Numbers are represented in their JSON-canonical form:

```
json.age = 30;
json.pi = 3.14;
json.negative = -42;
json.zero = 0;
json.scientific = 1e+100;
json.tiny = 1.5e-10;
```

Integer values are represented without a decimal point. Floating-point values retain
their decimal representation. Scientific notation is used when the JSON input uses it
or when the number's magnitude requires it.

gron preserves the numeric precision as provided by Go's `encoding/json` decoder,
which uses `json.Number` to avoid floating-point precision loss. Numbers are
represented as they appear in the JSON input, subject to Go's JSON decoder behavior.

Special cases:
- Negative zero (`-0`) is preserved as `-0`
- Very large or very small numbers use scientific notation (e.g., `1e+100`)
- Numbers are never quoted (that would make them strings)

### Booleans

Boolean values are represented as the bare tokens `true` and `false`:

```
json.active = true;
json.deleted = false;
```

### Null

The null value is represented as the bare token `null`:

```
json.value = null;
json.optional = null;
```

### Empty Object

An empty JSON object `{}` is represented as:

```
json.obj = {};
```

This is both a value and a container initialization. When an object has no keys,
only this single statement is emitted for it.

### Empty Array

An empty JSON array `[]` is represented as:

```
json.arr = [];
```

Similarly to empty objects, when an array has no elements, only this single statement
is emitted.

---

## Key Naming and Identifier Rules

### Valid JavaScript Identifiers

gron determines whether a JSON object key can be used with dot notation by checking
whether it is a valid JavaScript (ECMAScript) identifier. The rules follow the
ECMAScript specification:

1. The key must not be empty.
2. The key must not be a reserved word.
3. The first character must be a valid identifier start character.
4. All subsequent characters must be valid identifier part characters.

If all conditions are met, dot notation is used: `json.key`. Otherwise, bracket
notation is used: `json["key"]`.

### Reserved Words

The following 33 JavaScript reserved words always require bracket notation, even if
they would otherwise qualify as valid identifiers:

```
break       case        catch       class       const
continue    debugger    default     delete      do
else        export      extends     false       finally
for         function    if          import      in
instanceof  new         null        return      super
switch      this        throw       true        try
typeof      var         void        while       with
yield
```

Note that `true`, `false`, and `null` are in this list. A JSON key named `"true"` is
written as `json["true"]` in gron output, not `json.true`, to avoid ambiguity with the
boolean value `true`.

Examples:

```json
{"class": "A", "return": 0, "name": "Tom"}
```

Produces:

```
json = {};
json["class"] = "A";
json.name = "Tom";
json["return"] = 0;
```

### Unicode in Identifiers

gron follows the Unicode-aware identifier rules from ECMAScript. This means that keys
containing Unicode letters from various scripts are valid identifiers and use dot notation:

```json
{"nombre": "Juan", "ville": "Paris"}
```

Produces:

```
json = {};
json.nombre = "Juan";
json.ville = "Paris";
```

Keys using characters from other Unicode letter categories (e.g., Chinese, Japanese,
Arabic) also use dot notation as long as they satisfy the identifier rules.

### Numeric-Start Keys

Keys that begin with a digit always require bracket notation, because JavaScript
identifiers cannot start with a digit:

```json
{"0day": "exploit", "123": "numbers"}
```

Produces:

```
json = {};
json["0day"] = "exploit";
json["123"] = "numbers";
```

### Empty String Keys

JSON allows empty string keys, which always require bracket notation:

```json
{"": "empty key"}
```

Produces:

```
json = {};
json[""] = "empty key";
```

### Keys with Special Characters

Keys containing any character that is not valid in an identifier position require
bracket notation. Common examples:

```json
{
  "hyphen-key": 1,
  "dot.key": 2,
  "space key": 3,
  "quote\"key": 4,
  "slash/key": 5,
  "at@sign": 6
}
```

Produces:

```
json = {};
json["at@sign"] = 6;
json["dot.key"] = 2;
json["hyphen-key"] = 1;
json["quote\"key"] = 4;
json["slash/key"] = 5;
json["space key"] = 3;
```

Note that the double quote inside the key `quote"key` is escaped as `\"` in the
bracket notation output, following JSON string escaping rules.

---

## Sorting Behavior

### Default Sorted Output

By default, gron sorts its output alphabetically by the full path string. This
produces deterministic output: the same JSON input always produces the same gron
output, regardless of key order in the input.

The sorting uses a natural sort algorithm that is aware of numeric array indices.
This means that `json[2]` sorts before `json[10]`, not after it (as would happen
with naive string comparison where `"1"` comes before `"2"` comes before `"9"`
comes before... nothing, and `"10"` would sort between `"1"` and `"2"`).

The sorting compares statements token-by-token from left to right:

1. If the statements diverge at a numeric key token, integer comparison is used.
2. Otherwise, string comparison is used on the token text.
3. Container initialization statements (with `=` as the divergence point) sort
   before child statements.

Example showing natural sort order:

```
json = {};
json.items = [];
json.items[0] = "first";
json.items[1] = "second";
json.items[2] = "third";
json.items[9] = "ninth";
json.items[10] = "tenth";
json.items[11] = "eleventh";
json.items[100] = "hundredth";
```

Note how `json.items[10]` correctly appears after `json.items[9]`, not after
`json.items[1]`.

### Unsorted Output (`--no-sort`)

With the `--no-sort` flag, gron outputs statements in the order they are generated
during a depth-first traversal of the JSON structure. This order matches the order
that keys and array elements appear in the input JSON document.

For objects, keys are output in the order the JSON parser encounters them. For
arrays, elements are output in index order (which is the natural order).

Unsorted output can be slightly faster for large inputs because it skips the sorting
step. However, the output is no longer deterministic with respect to semantically
equivalent JSON inputs that differ only in key order.

Example with `--no-sort`:

```json
{"z": 1, "a": 2, "m": 3}
```

With default sorting:
```
json = {};
json.a = 2;
json.m = 3;
json.z = 1;
```

With `--no-sort`:
```
json = {};
json.z = 1;
json.a = 2;
json.m = 3;
```

---

## Ungron Mode

### Overview

Ungron is the inverse operation of gron. It takes gron-format assignment statements
as input and reconstructs the JSON structure they describe. The result is
pretty-printed JSON written to standard output.

Ungron is activated with the `-u` or `--ungron` flag:

```bash
gron -u input.gron
```

Or equivalently, via a pipeline:

```bash
cat statements.gron | gron --ungron
```

### Input Format

Ungron expects one assignment statement per line. Each line must follow the gron
assignment format:

```
json = {};
json.name = "Tom";
json.age = 30;
```

Blank lines and lines that cannot be parsed as valid gron statements may produce
errors or be silently skipped, depending on the nature of the malformation.

### Reconstruction Process

Ungron processes statements in order, building up a data structure incrementally:

1. The first statement typically initializes the root: `json = {};` or `json = [];`.
2. Each subsequent statement either:
   - Initializes a sub-container (`json.path = {};` or `json.path = [];`)
   - Assigns a scalar value to a path (`json.path.key = "value";`)

When two statements assign to the same path, the later statement wins. When
statements assign to paths that require intermediate containers that have not been
explicitly initialized, ungron creates them implicitly.

### Sparse Arrays

When ungron encounters array index assignments that skip indices, it fills the gaps
with `null` values:

```
json = [];
json[0] = "first";
json[5] = "sixth";
```

Produces:

```json
[
  "first",
  null,
  null,
  null,
  null,
  "sixth"
]
```

This preserves the index positions of the assigned values.

### Type Conflicts

If statements assign conflicting types to the same path (e.g., first initializing
a path as an object and then treating it as an array, or vice versa), the later
assignment overwrites the earlier one. The last type assigned to a given path
determines the final type in the output.

```
json = {};
json.x = {};
json.x = [];
json.x[0] = 1;
```

In this case, `json.x` ends up as an array `[1]` because the array initialization
and element assignment came after the object initialization.

### Ungron with Grep: The Core Workflow

The primary use case for ungron is in combination with grep. The typical workflow
is:

1. Run gron on a JSON document to get flat assignment statements.
2. Pipe the output through grep (or other text filters) to select the lines you want.
3. Pipe the filtered lines through `gron --ungron` to reassemble valid JSON.

```bash
gron data.json | grep "email" | gron --ungron
```

This workflow is powerful because it lets you use the full power of Unix text
processing tools on JSON data without learning a specialized query language.

#### Filtering by Path

```bash
# Extract only the "users" array
gron data.json | grep "^json.users" | gron --ungron

# Extract the first user
gron data.json | grep "^json.users\[0\]" | gron --ungron

# Extract all "name" fields at any depth
gron data.json | grep "\.name " | gron --ungron
```

#### Filtering by Value

```bash
# Find all paths that have the value "admin"
gron data.json | grep '"admin"'

# Find all numeric values greater than 100 (requires more complex grep/awk)
gron data.json | grep -E '= [0-9]+;' | awk -F'= |;' '$2 > 100'
```

#### Modifying JSON with sed

Since gron output is line-oriented, you can modify values with sed and then ungron
the result:

```bash
# Change all occurrences of "Tom" to "Thomas"
gron data.json | sed 's/"Tom"/"Thomas"/g' | gron --ungron
```

### Ungron from File

Ungron can read statements from a file:

```bash
gron --ungron statements.gron
```

The file should contain one gron statement per line, following the assignment format.

### Ungron and Grep Separators

When grep matches lines from gron output, it may insert separator lines (e.g., `--`)
between non-contiguous match groups when using `-C` (context) options. Ungron handles
these separators gracefully by skipping lines that do not parse as valid statements.

### Invocation via Symlink

gron can also be invoked in ungron mode by calling it through a symlink named `ungron`
or `norg` (which is "gron" reversed). When the binary name is `ungron` or `norg`,
gron automatically enters ungron mode without requiring the `-u` flag.

---

## URL Fetching

### Basic Usage

gron can fetch JSON directly from HTTP and HTTPS URLs:

```bash
gron https://api.github.com/users/tomnomnom
```

The URL detection is based on whether the input argument starts with `http://` or
`https://` (case-sensitive matching using a regular expression). If the argument
matches this pattern, gron treats it as a URL and fetches the content over HTTP.
Otherwise, it treats the argument as a file path.

### HTTP Request Details

When fetching a URL, gron sends an HTTP GET request with the following characteristics:

- **User-Agent**: gron identifies itself with a custom User-Agent header.
- **Accept header**: gron sends `application/json` in the Accept header to indicate
  it prefers JSON responses.
- **Timeout**: The HTTP client uses a 20-second timeout for the entire request
  (connection, TLS handshake, response headers, and response body).
- **Redirects**: gron follows HTTP redirects (301, 302, etc.) automatically, as
  provided by Go's standard `net/http` client.

### HTTPS and Certificate Validation

By default, gron validates TLS certificates when connecting to HTTPS URLs. If the
server's certificate is invalid (self-signed, expired, wrong hostname, etc.), gron
reports an error and exits.

The `-k` / `--insecure` flag disables certificate validation:

```bash
gron -k https://self-signed.example.com/data
```

When this flag is set, gron accepts any certificate presented by the server,
regardless of its validity. This is useful for development environments with
self-signed certificates, but should not be used in production as it disables
an important security check.

### Proxy Configuration

gron supports HTTP proxy configuration through multiple mechanisms, with the
following precedence (highest first):

1. **`--proxy` / `-x` flag**: Explicitly sets the proxy URL on the command line.
   This takes highest precedence and overrides all environment variables.

   ```bash
   gron -x http://proxy:8080 https://api.example.com/data
   ```

2. **Environment variables**: If no `--proxy` flag is given, gron respects the
   standard proxy environment variables:
   - `HTTP_PROXY` or `http_proxy`: Proxy for HTTP requests
   - `HTTPS_PROXY` or `https_proxy`: Proxy for HTTPS requests

3. **No proxy**: If no proxy is configured via flag or environment, gron connects
   directly.

### No-Proxy Configuration

Certain hosts can be excluded from proxying:

1. **`--noproxy` flag**: A comma-separated list of hostnames or patterns that
   should bypass the proxy.

   ```bash
   gron --proxy http://proxy:8080 --noproxy "localhost,*.internal.com" https://api.example.com/data
   ```

2. **`NO_PROXY` or `no_proxy` environment variable**: Standard environment variable
   for specifying no-proxy hosts.

Wildcard suffix matching is supported: `*.example.com` matches any subdomain of
`example.com`.

### URL Edge Cases

- **Query parameters**: URLs with query strings are supported and passed through
  unmodified:
  ```bash
  gron "https://api.example.com/search?q=test&limit=10"
  ```

- **Fragments**: URL fragments (`#section`) are included in the URL but typically
  have no effect on the HTTP request since fragments are client-side.

- **User info**: URLs with embedded credentials (`https://user:pass@host/path`)
  are passed to Go's HTTP client, which handles Basic authentication.

- **Long paths**: Very long URL paths are supported up to the limits of the
  underlying HTTP client.

- **Non-JSON responses**: If the server returns a non-JSON response (e.g., HTML),
  gron attempts to parse it as JSON and reports a parse error.

- **Empty responses**: An empty response body is treated as invalid JSON.

- **HTTP errors**: HTTP error status codes (404, 500, etc.) are reported as
  errors. gron writes an error message to stderr and exits with a non-zero
  status code.

- **Connection failures**: DNS resolution failures, connection refused errors,
  and timeouts all produce error messages on stderr.

- **Non-HTTP protocols**: Arguments that look like URLs but use unsupported
  protocols (e.g., `ftp://`) are not matched by the URL detection regex and
  are treated as file paths instead.

---

## Colorized Output

### Default Behavior

gron produces colorized output when it detects that standard output is connected
to a terminal (TTY). When stdout is redirected to a file or piped to another
command, color is automatically disabled.

### Color Scheme

gron uses ANSI escape sequences to colorize different components of its output.
The color mapping for gron (assignment) output is:

| Token Type          | Color          |
|---------------------|----------------|
| Bare keys           | Bold Blue      |
| String values       | Yellow         |
| Numeric values      | Red            |
| Boolean values      | Cyan           |
| Null                | Cyan           |
| Braces (`{}`, `[]`) | Magenta        |

When outputting JSON (with `--ungron` or `--json`), gron uses the `jsoncolor`
package to apply syntax highlighting to the JSON output, using the same color
scheme.

### Forcing Color

The `-c` / `--colorize` flag forces color output regardless of whether stdout is
a TTY:

```bash
gron data.json -c | less -R
```

The `-R` flag to `less` is necessary to interpret ANSI escape sequences as colors
rather than displaying them as raw text.

### Forcing Monochrome

The `-m` / `--monochrome` flag suppresses all color output regardless of whether
stdout is a TTY:

```bash
gron data.json -m > output.txt
```

### Flag Interactions

When both `-c` and `-m` are specified, monochrome takes precedence. The output
will be uncolored. Multiple `-m` flags have the same effect as a single one.

---

## Streaming Mode

### Overview

Streaming mode (`-s` / `--stream`) changes how gron processes its input. Instead
of treating the entire input as a single JSON document, streaming mode treats each
line of input as a separate, independent JSON value.

### Input Format

In streaming mode, gron expects newline-delimited input where each line is a
complete, self-contained JSON value. This is compatible with the NDJSON
(Newline-Delimited JSON) format, also known as JSON Lines.

Each line can be any valid JSON value:
- An object: `{"key": "value"}`
- An array: `[1, 2, 3]`
- A scalar: `42`, `"hello"`, `true`, `null`

### Output Format

Each line of input is gronned independently and wrapped in array-index notation
to distinguish the individual documents. The first line's assignments use `json[0]`,
the second line's use `json[1]`, and so on.

Example input (two JSON objects, one per line):

```
{"name": "Alice"}
{"name": "Bob"}
```

Output:

```
json[0] = {};
json[0].name = "Alice";
json[1] = {};
json[1].name = "Bob";
```

### Scalar Values in Streams

When a line contains a scalar JSON value (number, string, boolean, null), it is
assigned directly to the indexed position:

```
42
"hello"
true
null
```

Output:

```
json[0] = 42;
json[1] = "hello";
json[2] = true;
json[3] = null;
```

### Nested Structures in Streams

Each line is processed independently, so nested structures are fully expanded
within their indexed position:

```
{"user": {"name": "Alice", "scores": [95, 87]}}
{"user": {"name": "Bob", "scores": [72, 88]}}
```

Output:

```
json[0] = {};
json[0].user = {};
json[0].user.name = "Alice";
json[0].user.scores = [];
json[0].user.scores[0] = 95;
json[0].user.scores[1] = 87;
json[1] = {};
json[1].user = {};
json[1].user.name = "Bob";
json[1].user.scores = [];
json[1].user.scores[0] = 72;
json[1].user.scores[1] = 88;
```

### Error Handling in Streams

If a line in streaming mode contains invalid JSON, gron reports an error for that
line. The error is written to stderr and includes the problematic line content.

Empty lines, whitespace-only lines, and lines containing only tabs also produce
errors in streaming mode since they are not valid JSON values.

### Streaming with Other Flags

Streaming mode can be combined with other flags:

- **`--stream --json`**: Each line of JSON is converted to JSON-stream format
  instead of gron assignment format, with each entry indexed.

- **`--stream --no-sort`**: Streaming output without sorting within each entry's
  statements.

- **`--stream --monochrome`**: Streaming with color suppressed.

- **`--stream` and `--ungron`**: These flags are incompatible. Streaming mode
  processes JSON input line by line, while ungron mode expects gron assignment
  statements. Using both together produces an error.

### Use Cases for Streaming

1. **Log processing**: JSON-formatted log files where each line is a log entry.

2. **API pagination**: Concatenated JSON responses from paginated API calls.

3. **Real-time monitoring**: Processing JSON events as they arrive from a stream.

4. **Large datasets**: Processing datasets where each record is a separate JSON
   line, without buffering the entire file into memory.

```bash
# Process NDJSON log file
cat events.ndjson | gron --stream | grep "error" | gron --ungron

# Monitor a JSON event stream
tail -f events.json | gron --stream | grep "critical"
```

---

## Values Mode

### Overview

Values mode (`-v` / `--values`) extracts only the scalar values from gron
statements, stripping away the paths, equals signs, and semicolons. Each value
is printed on its own line.

### What Is Extracted

Only leaf scalar values are included in the output:

- String values (including their surrounding quotes)
- Numeric values
- Boolean values (`true`, `false`)
- Null values (`null`)

Container initializations (`{}` and `[]`) are excluded because they are structural
elements, not data values.

### Example

```json
{
  "name": "Tom",
  "age": 30,
  "active": true,
  "address": {
    "city": "London",
    "zip": null
  },
  "tags": ["developer", "go"]
}
```

```bash
gron data.json --values
```

Output:

```
true
"London"
null
"Tom"
30
"developer"
"go"
```

Note that the output is sorted (because gron's default is sorted), so values
appear in the order of their sorted paths, not in the order they appear in the
JSON input.

### String Values in Values Mode

String values are output with their double quotes intact and with escape sequences
preserved. This means the output is the JSON string representation, not the raw
unescaped string:

```json
{"message": "Hello\nWorld", "quote": "She said \"hi\""}
```

```bash
gron data.json --values
```

Output:

```
"Hello\nWorld"
"She said \"hi\""
```

### Values Mode with Streaming

Values mode can be combined with streaming mode. In this case, each line of the
input stream is processed, and only the scalar values from each entry are output:

```bash
echo '{"a": 1}
{"b": 2}' | gron --stream --values
```

Output:

```
1
2
```

---

## JSON Output Mode

### Overview

JSON output mode (`-j` / `--json`) changes gron's output format from assignment
statements to a JSON stream representation. Instead of producing human-readable
assignment lines, gron outputs a JSON array for each statement, where the elements
represent the path components and value.

### Format Specification

Each gron statement is represented as a JSON array on a single line. The array
elements represent, in order:

1. Path components (each as a JSON value):
   - Bare keys as strings: `"name"`
   - Quoted keys as objects: `{"key": "special-key"}`
   - Numeric indices as numbers: `0`, `1`, `2`

2. The final element is the assigned value (string, number, boolean, null, empty
   object `{}`, or empty array `[]`).

### Example

```json
{"name": "Tom", "items": [1, 2]}
```

Default gron output:

```
json = {};
json.items = [];
json.items[0] = 1;
json.items[1] = 2;
json.name = "Tom";
```

JSON mode output (`-j`):

```
[[],{}]
[["items"],[]]
[["items",0],1]
[["items",1],2]
[["name"],"Tom"]
```

Each line is a JSON array with two elements:
- The first element is an array of path components (empty for the root).
- The second element is the value at that path.

### JSON Mode with Ungron

When `-j` is combined with `-u` (`--ungron`), gron reads JSON-stream format input
(as produced by `gron -j`) and converts it back to regular JSON:

```bash
gron -j data.json | gron -u -j
```

This round-trips through the JSON-stream format.

### JSON Mode with Streaming

When combined with `--stream`, JSON mode produces indexed entries in JSON-stream
format:

```bash
echo '{"a": 1}
{"b": 2}' | gron --stream --json
```

### JSON Mode with No Sort

When combined with `--no-sort`, the JSON-stream entries are output in encounter
order rather than sorted order.

---

## Data Type Preservation and Edge Cases

### Top-Level Scalars

JSON allows top-level values that are not objects or arrays. gron handles these:

**Top-level string**:
```bash
echo '"hello"' | gron
```
```
json = "hello";
```

**Top-level number**:
```bash
echo '42' | gron
```
```
json = 42;
```

**Top-level boolean**:
```bash
echo 'true' | gron
```
```
json = true;
```

**Top-level null**:
```bash
echo 'null' | gron
```
```
json = null;
```

### Empty Containers

**Empty object**:
```bash
echo '{}' | gron
```
```
json = {};
```

**Empty array**:
```bash
echo '[]' | gron
```
```
json = [];
```

### Deeply Nested Structures

gron handles arbitrarily deep nesting. A structure nested 50 levels deep produces
50 levels of path components:

```
json = {};
json.a = {};
json.a.b = {};
json.a.b.c = {};
...
json.a.b.c.d.e.f.g.h.i.j.k.l = "deep";
```

There is no hard limit on nesting depth. The practical limit is determined by
available memory and stack space.

### Large Arrays

gron handles arrays with hundreds or thousands of elements. Each element gets
its own statement with the appropriate numeric index:

```
json = [];
json[0] = "element 0";
json[1] = "element 1";
...
json[999] = "element 999";
```

The natural sort ensures that `json[999]` appears after `json[99]`, not after
`json[9]`.

### Unicode Strings

gron preserves Unicode strings in their original form. Characters that do not
require escaping are passed through directly:

```json
{"emoji": "\ud83d\ude00", "chinese": "\u4f60\u597d"}
```

```
json = {};
json.chinese = "你好";
json.emoji = "😀";
```

### Number Precision

gron uses Go's `json.Number` type to avoid floating-point precision loss during
parsing. Numbers are preserved as the exact string representation from the
JSON input:

```json
{"big": 9999999999999999, "precise": 1.23456789012345}
```

```
json = {};
json.big = 9999999999999999;
json.precise = 1.23456789012345;
```

### Escape Sequences in Keys

When a JSON key contains characters that require escaping (quotes, backslashes,
control characters), the bracket-notation output uses the same JSON string
escaping rules:

```json
{"key\"with\"quotes": 1, "back\\slash": 2, "new\nline": 3}
```

```
json = {};
json["back\\slash"] = 2;
json["key\"with\"quotes"] = 1;
json["new\nline"] = 3;
```

### Multiple Types at Same Path (Ungron)

When ungronning, if multiple statements assign different types to the same path,
the last assignment wins:

```
json = {};
json.x = "string";
json.x = 42;
```

Produces:

```json
{
  "x": 42
}
```

### Negative Array Indices (Ungron)

Negative array indices in ungron input produce an error, since JSON arrays use
only non-negative integer indices.

---

## Pipeline Usage Patterns

### The Core gron-grep-ungron Pattern

The fundamental usage pattern for gron is a three-stage pipeline:

```bash
gron <input> | grep <pattern> | gron --ungron
```

This pattern:
1. Flattens JSON into greppable lines.
2. Filters for the lines you want.
3. Reassembles the filtered lines into valid JSON.

### Extracting Specific Fields

```bash
# Extract all email addresses from a complex JSON structure
gron users.json | grep "email" | gron -u

# Extract a specific nested field
gron config.json | grep "database.host" | gron -u

# Extract all items at a certain array position
gron data.json | grep "\[0\]" | gron -u
```

### Combining with fgrep for Literal Matches

When your search pattern contains regex metacharacters, use `fgrep` (or `grep -F`)
for literal string matching:

```bash
gron data.json | fgrep "special.key" | gron -u
```

### Negative Filtering

Use `grep -v` to exclude certain paths:

```bash
# Get everything except passwords
gron config.json | grep -v "password" | gron -u

# Get everything except a specific array
gron data.json | grep -v "^json.logs" | gron -u
```

### Counting Occurrences

```bash
# How many users are in the response?
gron users.json | grep -c "\.name "

# How many entries have errors?
gron log.json | grep "error" | wc -l
```

### Extracting and Transforming with awk

```bash
# Extract values and their paths side by side
gron data.json | awk -F' = ' '{print $1 "\t" $2}'

# Sum all numeric values at a certain path
gron data.json | grep "\.score " | awk -F' = ' '{gsub(/;/,"",$2); sum+=$2} END{print sum}'
```

### Modifying JSON with sed

```bash
# Rename a field by modifying the path
gron data.json | sed 's/\.old_name /\.new_name /' | gron -u

# Change all URLs from http to https
gron config.json | sed 's|"http://|"https://|g' | gron -u

# Increment all version numbers
gron package.json | sed -E 's/(\.version = ")([0-9]+)/echo "\1$((\2+1))"/ge' | gron -u
```

### Combining Multiple JSON Files

Since gron output is line-oriented, you can combine outputs from multiple files:

```bash
# Merge two JSON objects (later assignments win on conflict)
(gron file1.json; gron file2.json) | gron -u
```

### Diffing JSON Files

gron makes JSON diffing straightforward because each value has its own line:

```bash
diff <(gron old.json) <(gron new.json)
```

This shows exactly which paths changed, were added, or were removed:

```diff
< json.version = "1.0";
> json.version = "2.0";
> json.features[2] = "new-feature";
```

### Pretty-Printing JSON

gron can serve as a JSON pretty-printer:

```bash
# Via gron + ungron round-trip
gron data.json | gron -u

# Via the --json flag with ungron
echo '{"compact":"json"}' | gron | gron -u
```

### Checking for the Existence of a Path

```bash
# Check if a path exists (exit code indicates match/no match)
gron data.json | grep -q "\.admin\.email " && echo "Has admin email" || echo "No admin email"
```

### Working with API Responses

```bash
# Fetch and explore an API
gron https://api.github.com/users/octocat | head -20

# Fetch, filter, and reconstruct
gron https://api.github.com/users/octocat | grep "\.name\|\.bio\|\.location" | gron -u

# Fetch with authentication (via curl + pipe)
curl -s -H "Authorization: Bearer TOKEN" https://api.example.com/data | gron | grep "status"
```

### Processing JSON Logs

```bash
# Stream JSON logs and filter for errors
tail -f app.log | gron --stream | grep "error\|exception" | gron -u

# Count errors per minute in a log file
gron --stream < log.ndjson | grep "level.*error" | wc -l
```

### Extracting Specific Array Elements

```bash
# Get the third element of every array named "results"
gron data.json | grep "\.results\[2\]" | gron -u

# Get all elements of the "tags" array
gron data.json | grep "\.tags\[" | gron -u

# Get the last element (requires knowing the length)
LAST=$(gron data.json | grep "\.items\[" | tail -1 | grep -oP '\[\K[0-9]+')
gron data.json | grep "\.items\[$LAST\]" | gron -u
```

---

## Error Handling

### Invalid JSON

When the input is not valid JSON, gron writes an error message to stderr and
exits with exit code 3. The error message typically includes the position in the
input where the error was detected:

```bash
$ echo '{"invalid": }' | gron
Error: invalid character '}' looking for beginning of value
```

### Truncated JSON

Truncated or incomplete JSON produces a similar error:

```bash
$ echo '{"key": "val' | gron
Error: unexpected end of JSON input
```

### File Not Found

```bash
$ gron nonexistent.json
Error: open nonexistent.json: no such file or directory
```

### Network Errors

```bash
$ gron https://nonexistent.example.com/data
Error: ... no such host

$ gron https://localhost:9999/data
Error: ... connection refused
```

### Invalid Gron Statements (Ungron)

```bash
$ echo 'not a valid statement' | gron -u
Error: ...
```

### Empty Input

```bash
$ echo '' | gron
Error: ...
```

gron expects at least one valid JSON value in its input. An empty input is not
valid JSON and produces an error.

---

## Comparison with jq

gron and jq are both tools for working with JSON on the command line, but they
take fundamentally different approaches.

### Philosophy

**jq** is a full-featured JSON query language with its own syntax for filtering,
transforming, and constructing JSON. It is powerful but requires learning a
domain-specific language.

**gron** converts JSON to a flat, line-oriented format that can be processed with
standard Unix tools. It requires no new syntax -- just `grep`, `sed`, `awk`, and
the other tools you already know.

### When to Use gron

- **Exploration**: You have a large, unfamiliar JSON document and want to find
  where a value lives. gron's flat output makes this trivial with grep.

- **Simple filtering**: You want to extract a few paths from a JSON document.
  The gron-grep-ungron pipeline handles this without learning jq syntax.

- **JSON diffing**: gron's line-per-value output makes `diff` work naturally.

- **Quick modifications**: Simple `sed` substitutions on gron output can modify
  JSON values without complex jq expressions.

- **Teaching and debugging**: gron's output format makes JSON structure immediately
  visible and understandable.

### When to Use jq

- **Complex transformations**: Reshaping JSON, computing new fields, conditional
  logic -- jq's query language handles these natively.

- **Performance**: jq processes JSON in a single pass without converting to an
  intermediate format.

- **Type-aware operations**: jq understands JSON types and can perform arithmetic,
  string operations, and array manipulations directly.

- **Programmatic use**: jq expressions can be embedded in scripts for reliable,
  structured JSON processing.

### Side-by-Side Examples

**Extract a nested field**:

```bash
# gron
gron data.json | grep "\.name " | gron -u

# jq
jq '.name' data.json
```

**Filter array elements**:

```bash
# gron (find elements where status is "active")
gron data.json | grep "active" | gron -u

# jq
jq '.[] | select(.status == "active")' data.json
```

**Rename a field**:

```bash
# gron
gron data.json | sed 's/\.old_name/\.new_name/' | gron -u

# jq
jq '.new_name = .old_name | del(.old_name)' data.json
```

---

## The Assignment Format as Valid JavaScript

A notable property of gron's output is that it is valid JavaScript. If you
create a variable named `json` and then execute the gron output, it builds
the same data structure in memory:

```bash
$ echo '{"name": "Tom", "age": 30}' | gron
json = {};
json.age = 30;
json.name = "Tom";
```

This can be directly executed in Node.js:

```bash
$ echo '{"name": "Tom", "age": 30}' | gron | node -e "
  process.stdin.resume();
  process.stdin.setEncoding('utf8');
  let data = '';
  process.stdin.on('data', (chunk) => data += chunk);
  process.stdin.on('end', () => {
    eval(data);
    console.log(json);
  });
"
{ age: 30, name: 'Tom' }
```

This property is why gron uses JavaScript identifier rules for determining
dot notation vs. bracket notation, and why reserved words like `class` and
`return` must use bracket notation.

The semicolons at the end of each line are also part of this JavaScript
compatibility. Each line is a complete JavaScript statement.

---

## Statement Parsing Specification

This section describes the detailed rules for how gron parses its own output
format when performing ungron operations.

### Token Types

Each gron statement is composed of a sequence of tokens. The token types are:

| Token Type     | Description                           | Examples              |
|----------------|---------------------------------------|-----------------------|
| Bare           | Unquoted identifier                   | `json`, `name`, `age` |
| NumericKey     | Array index in brackets               | `[0]`, `[42]`         |
| QuotedKey      | Quoted key in brackets                | `["key"]`, `["a-b"]`  |
| Dot            | Property access operator              | `.`                   |
| LBrace         | Left square bracket                   | `[`                   |
| RBrace         | Right square bracket                  | `]`                   |
| Equals         | Assignment operator                   | `=`                   |
| Semi           | Statement terminator                  | `;`                   |
| String         | String value                          | `"hello"`             |
| Number         | Numeric value                         | `42`, `3.14`          |
| True           | Boolean true                          | `true`                |
| False          | Boolean false                         | `false`               |
| Null           | Null value                            | `null`                |
| EmptyArray     | Empty array literal                   | `[]`                  |
| EmptyObject    | Empty object literal                  | `{}`                  |

### Statement Grammar

A gron statement follows this grammar (informal):

```
statement    := path ' = ' value ';'
path         := 'json' accessor*
accessor     := '.' bare_ident | '[' numeric_key ']' | '["' quoted_key '"]'
value        := string | number | 'true' | 'false' | 'null' | '{}' | '[]'
bare_ident   := valid JavaScript identifier (non-reserved)
numeric_key  := non-negative integer
quoted_key   := JSON-escaped string
string       := '"' (escaped_char | unescaped_char)* '"'
number       := JSON number
```

### Parsing Process

When ungronning, each line of input is parsed as follows:

1. The line is tokenized into a sequence of tokens.
2. The first token must be the bare identifier `json`.
3. Subsequent tokens form path accessors (dot+bare, bracket+numeric, bracket+quoted).
4. An equals token separates the path from the value.
5. A value token represents the assigned value.
6. A semicolon terminates the statement.

If any step fails, the statement is considered invalid.

---

## Advanced String Escaping

### Escaping in String Values

String values in gron output follow JSON escaping rules. The following characters
are always escaped:

- `\` becomes `\\`
- `"` becomes `\"`
- Newline (U+000A) becomes `\n`
- Carriage return (U+000D) becomes `\r`
- Tab (U+0009) becomes `\t`
- Backspace (U+0008) becomes `\b`
- Form feed (U+000C) becomes `\f`

Additionally, these characters are escaped for JavaScript compatibility:

- Line Separator (U+2028) becomes `\u2028`
- Paragraph Separator (U+2029) becomes `\u2029`

All other control characters (U+0000 through U+001F, excluding those with named
escapes above) are escaped using the `\uXXXX` notation, where `XXXX` is the
four-digit hexadecimal Unicode code point.

All non-control Unicode characters are passed through unescaped. This includes
emoji, CJK characters, Cyrillic, Arabic, and other scripts. gron does not
unnecessarily escape characters that are valid in both JSON and JavaScript strings.

### Escaping in Quoted Keys

Quoted keys in bracket notation (`json["key"]`) use the same escaping rules as
string values. The key is treated as a JSON string and escaped accordingly:

```
json["key\twith\ttabs"] = 1;
json["key\nwith\nnewlines"] = 2;
json["key\"with\"quotes"] = 3;
json["key\\with\\backslashes"] = 4;
```

### Round-Trip Fidelity

The escaping rules ensure round-trip fidelity: gronning a JSON document and then
ungronning the result produces a JSON document with exactly the same string values
(byte-for-byte identical escape sequences, subject to the JSON encoder's choices).

---

## Statelessness and Idempotence

### Stateless Operation

Each invocation of gron is completely independent. gron does not maintain any
state between runs -- no configuration files, no caches, no history. The output
depends solely on the input and the command-line flags.

This means that running gron twice on the same input with the same flags always
produces exactly the same output (assuming sorted mode, which is the default).

### Idempotence of Round-Trips

The gron-ungron round-trip is semantically idempotent:

```bash
# These produce equivalent JSON (modulo formatting/key order):
cat data.json
gron data.json | gron -u
gron data.json | gron -u | gron | gron -u
```

Multiple round-trips through gron and ungron converge to a canonical form:
sorted keys, consistent formatting, and normalized number representations.

---

## Input Source Selection Logic

gron uses the following logic to determine its input source:

1. If no positional argument is provided, or if the argument is `-`, read from
   stdin.

2. If the argument matches the pattern `^https?://` (i.e., starts with `http://`
   or `https://`), treat it as a URL and fetch the content over HTTP.

3. Otherwise, treat the argument as a file path and open the file.

This means that a file named `https://something` on disk would be treated as a URL,
not a file. Similarly, a file named `-` on disk cannot be read directly (gron would
read from stdin instead). These are edge cases that are unlikely to occur in practice.

### Stdin Input

When reading from stdin, gron reads the entire input into memory before processing.
This means it cannot process infinite streams in normal (non-streaming) mode. For
infinite or very large streams, use `--stream` mode, which processes line by line.

```bash
# Pipe from another command
curl -s https://api.example.com/data | gron

# Redirect from a file
gron < data.json

# Here-document
gron <<EOF
{"inline": "json"}
EOF
```

### File Input

When reading from a file, gron opens the file, reads its entire contents, and
processes the JSON. If the file cannot be opened (does not exist, permission denied),
gron reports an error and exits with exit code 1.

```bash
gron data.json
gron /path/to/data.json
gron ./relative/path/data.json
```

---

## Internal Processing Pipeline

### Gron Mode

1. **Read**: Read the entire input (file, URL response, or stdin) into memory.
2. **Decode**: Parse the input as JSON using Go's `encoding/json` decoder with
   `UseNumber()` enabled for numeric precision.
3. **Generate statements**: Recursively traverse the decoded JSON structure,
   generating a statement for each container initialization and each leaf value.
4. **Sort** (unless `--no-sort`): Sort the statements alphabetically using the
   natural sort algorithm.
5. **Format**: Format each statement as a text line (with or without color).
6. **Output**: Write the formatted lines to stdout.

### Ungron Mode

1. **Read**: Read the entire input into memory.
2. **Parse**: Parse each line as a gron statement, extracting the path and value.
3. **Merge**: Merge all statements into a single data structure by applying each
   assignment in order.
4. **Encode**: Encode the merged data structure as pretty-printed JSON.
5. **Output**: Write the JSON (with or without color) to stdout.

### Stream Mode

1. **Read line**: Read one line from the input.
2. **Decode**: Parse the line as a JSON value.
3. **Generate statements**: Generate statements with the current stream index
   prepended to each path (e.g., `json[0].key`).
4. **Sort** (unless `--no-sort`): Sort the statements for this entry.
5. **Format and output**: Write the formatted lines immediately.
6. **Increment index**: Move to the next stream index.
7. **Repeat** until input is exhausted.

### Values Mode

1. **Read**: Read the entire input into memory.
2. **Parse**: Parse each line as a gron statement.
3. **Extract**: For each statement, extract the value token (right-hand side).
4. **Filter**: Skip container values (`{}`, `[]`).
5. **Output**: Write each scalar value on its own line.

---

## Handling of JSON Number Types

### Precision Preservation

gron uses Go's `json.Number` type (enabled via `Decoder.UseNumber()`) to read
numeric values from JSON input. This avoids the precision loss that would occur
if numbers were parsed as `float64` values.

For example, the number `9999999999999999` would lose precision if parsed as a
`float64` (IEEE 754 double-precision floating point can only represent integers
exactly up to 2^53). By using `json.Number`, gron preserves the exact string
representation from the input.

### Number Formatting

Numbers appear in gron output exactly as they appear in the JSON input (subject
to Go's JSON decoder behavior). This means:

- `42` remains `42` (not `42.0`)
- `3.14` remains `3.14`
- `-0` remains `-0`
- `1e100` remains `1e100` or may be normalized to `1e+100`
- `0.0001` remains `0.0001`

### Numbers in Ungron

When ungronning, numeric values in statements are preserved as-is. The ungron
process does not reparse numbers through a floating-point representation.

---

## Handling of Large JSON Documents

### Memory Usage

In normal (non-streaming) mode, gron reads the entire input into memory and
builds a complete internal representation. For very large JSON documents (hundreds
of megabytes or more), this can consume significant memory.

The memory usage is approximately:
- The size of the raw JSON input
- The decoded in-memory representation (typically 2-5x the raw size)
- The generated statements (one per leaf value and one per container)

### Performance Characteristics

**Sorting**: The default sorted output requires O(n log n) time where n is the
number of statements. For large documents with millions of statements, the
sorting step can be the dominant cost. Use `--no-sort` to skip this step.

**Statement generation**: Statement generation is O(n) where n is the total
number of JSON values (including intermediate containers).

**Ungron merging**: Statement merging in ungron mode is O(n * d) where n is the
number of statements and d is the average path depth.

### Streaming for Large Inputs

For very large inputs that consist of many independent JSON documents (NDJSON
format), streaming mode (`--stream`) processes one document at a time, keeping
memory usage proportional to the size of the largest single document rather than
the entire input.

---

## Compatibility Notes

### JSON Compliance

gron accepts any valid JSON as input, as defined by RFC 8259. This includes:

- Objects, arrays, strings, numbers, booleans, and null at the top level
- Unicode strings with escape sequences
- Numbers in integer, decimal, and scientific notation
- Nested structures to arbitrary depth
- Empty containers

gron does NOT accept:

- JSON with trailing commas (this is not valid JSON)
- JSON with comments (this is not valid JSON)
- JSON with single-quoted strings (this is not valid JSON)
- Bare identifiers as keys (this is not valid JSON)
- Multiple top-level values (unless using `--stream`)

### JavaScript Compatibility

gron's output is valid JavaScript. This means:

- All keys that are JavaScript identifiers use dot notation
- Reserved words use bracket notation
- String escaping is compatible with JavaScript string literals
- U+2028 and U+2029 are escaped (these are valid in JSON but not in JavaScript)
- Semicolons terminate each statement
- The output can be executed with `node` or any JavaScript runtime

### Platform Compatibility

gron is a statically compiled Go binary available for:

- Linux (amd64, arm, arm64, 386)
- macOS (amd64, arm64)
- Windows (amd64, 386)
- FreeBSD (amd64, 386)

It has no runtime dependencies and works identically across all platforms.

---

## Recipes and Cookbook

### Recipe: Find All Leaf Paths

List every path to a leaf value in a JSON document:

```bash
gron data.json | grep -v '= \[\]\|= {}' | awk -F' = ' '{print $1}'
```

### Recipe: Count Keys at Each Level

```bash
gron data.json | awk -F'.' '{print NF-1}' | sort -n | uniq -c
```

### Recipe: Extract All String Values

```bash
gron data.json | grep '= "' | awk -F' = ' '{gsub(/;$/,"",$2); print $2}'
```

### Recipe: Find Duplicate Values

```bash
gron data.json --values | sort | uniq -d
```

### Recipe: Compare Two API Responses

```bash
diff <(gron https://api.example.com/v1/data) <(gron https://api.example.com/v2/data)
```

### Recipe: Monitor a JSON Endpoint

```bash
watch -d "curl -s https://api.example.com/status | gron | grep 'healthy'"
```

### Recipe: Extract Schema-Like Information

Show the structure of a JSON document without values:

```bash
gron data.json | sed 's/ = .*/ = ...;/'
```

### Recipe: Flatten JSON for CSV Export

```bash
gron data.json | grep -v '= \[\]\|= {}' | awk -F' = ' '{gsub(/;$/,"",$2); print $1 "," $2}'
```

### Recipe: Find All Arrays and Their Lengths

```bash
gron data.json | grep '\[' | awk -F'[\\[\\]]' '{print $1 "[" $2 "]"}' | sort -u
```

### Recipe: Merge Multiple JSON Files

```bash
for f in *.json; do gron "$f"; done | gron -u
```

Note: later assignments overwrite earlier ones for the same path.

### Recipe: Validate JSON

gron can serve as a simple JSON validator:

```bash
gron data.json > /dev/null 2>&1 && echo "Valid JSON" || echo "Invalid JSON"
```

### Recipe: Transform NDJSON to JSON Array

```bash
cat events.ndjson | gron --stream | gron -u
```

This wraps the stream of JSON objects into a JSON array.

### Recipe: Find the Deepest Path

```bash
gron data.json | awk -F'[.\\[]' '{print NF, $0}' | sort -rn | head -1
```

### Recipe: Extract All Unique Keys

```bash
gron data.json | grep -oP '\.(\w+) =' | sort -u
```

---

## Frequently Asked Questions

### Why is the base identifier called "json"?

The identifier `json` was chosen because it is descriptive (the data came from
JSON), short, and is a valid JavaScript identifier. It cannot be changed via
a command-line option.

### Can gron handle YAML, TOML, or other formats?

No. gron only processes JSON input. To use gron with other formats, convert them
to JSON first (e.g., using `yq` for YAML).

### Does gron preserve key order?

In default (sorted) mode, no -- keys are sorted alphabetically. With `--no-sort`,
keys are output in the order encountered by Go's JSON decoder, which itself does
not guarantee preservation of the original source order (though in practice it
often matches).

### Can gron handle binary data in JSON strings?

JSON strings can contain any Unicode character. Binary data encoded as Base64
within a JSON string is handled correctly by gron (it is just a regular string
value). Raw binary data outside of a JSON string is not valid JSON and will
produce an error.

### What happens with very large numbers?

gron uses `json.Number` to preserve numeric precision. Numbers are stored and
output as strings internally, avoiding floating-point precision loss. This means
numbers like `9007199254740993` (which cannot be exactly represented as a float64)
are preserved correctly.

### Is gron's output deterministic?

In default (sorted) mode, yes. The same JSON input always produces the same gron
output. With `--no-sort`, the output depends on the JSON decoder's key ordering,
which may not be deterministic across different runs or platforms.

### Can I use gron in shell scripts?

Yes. gron is designed for pipeline use in shell scripts. Check the exit code to
detect errors:

```bash
if ! gron data.json > /dev/null 2>&1; then
    echo "Failed to process JSON"
    exit 1
fi
```

---

## Complete Transformation Examples

### Example 1: Simple Object

Input:
```json
{"name": "Tom", "age": 30, "active": true}
```

Output:
```
json = {};
json.active = true;
json.age = 30;
json.name = "Tom";
```

### Example 2: Nested Object with Array

Input:
```json
{
  "user": {
    "name": "Alice",
    "roles": ["admin", "editor"],
    "profile": {
      "bio": "Developer",
      "links": []
    }
  }
}
```

Output:
```
json = {};
json.user = {};
json.user.name = "Alice";
json.user.profile = {};
json.user.profile.bio = "Developer";
json.user.profile.links = [];
json.user.roles = [];
json.user.roles[0] = "admin";
json.user.roles[1] = "editor";
```

### Example 3: Array of Objects

Input:
```json
[
  {"id": 1, "name": "Alice"},
  {"id": 2, "name": "Bob"},
  {"id": 3, "name": "Charlie"}
]
```

Output:
```
json = [];
json[0] = {};
json[0].id = 1;
json[0].name = "Alice";
json[1] = {};
json[1].id = 2;
json[1].name = "Bob";
json[2] = {};
json[2].id = 3;
json[2].name = "Charlie";
```

### Example 4: Special Keys

Input:
```json
{
  "normal": 1,
  "with-hyphen": 2,
  "with space": 3,
  "123start": 4,
  "class": 5,
  "": 6,
  "_under": 7,
  "$dollar": 8
}
```

Output:
```
json = {};
json[""] = 6;
json["123start"] = 4;
json["class"] = 5;
json.$dollar = 8;
json.normal = 1;
json["with space"] = 3;
json["with-hyphen"] = 2;
json._under = 7;
```

### Example 5: All Data Types

Input:
```json
{
  "string": "hello",
  "integer": 42,
  "float": 3.14,
  "negative": -1,
  "boolean_true": true,
  "boolean_false": false,
  "null_value": null,
  "empty_object": {},
  "empty_array": [],
  "nested": {"key": "value"}
}
```

Output:
```
json = {};
json.boolean_false = false;
json.boolean_true = true;
json.empty_array = [];
json.empty_object = {};
json.float = 3.14;
json.integer = 42;
json.negative = -1;
json.nested = {};
json.nested.key = "value";
json.null_value = null;
json.string = "hello";
```

### Example 6: Deep Nesting

Input:
```json
{"a": {"b": {"c": {"d": {"e": {"f": "deep"}}}}}}
```

Output:
```
json = {};
json.a = {};
json.a.b = {};
json.a.b.c = {};
json.a.b.c.d = {};
json.a.b.c.d.e = {};
json.a.b.c.d.e.f = "deep";
```

### Example 7: GitHub API Response (Abbreviated)

Input:
```json
{
  "login": "octocat",
  "id": 1,
  "type": "User",
  "name": "The Octocat",
  "company": "GitHub",
  "blog": "https://github.blog",
  "location": "San Francisco",
  "email": null,
  "bio": null,
  "public_repos": 8,
  "followers": 10000,
  "following": 9
}
```

Output:
```
json = {};
json.bio = null;
json.blog = "https://github.blog";
json.company = "GitHub";
json.email = null;
json.followers = 10000;
json.following = 9;
json.id = 1;
json.location = "San Francisco";
json.login = "octocat";
json.name = "The Octocat";
json.public_repos = 8;
json.type = "User";
```

### Example 8: Streaming Two Objects

Input (each on its own line):
```
{"color": "red"}
{"color": "blue"}
```

Command:
```bash
echo '{"color": "red"}
{"color": "blue"}' | gron -s
```

Output:
```
json[0] = {};
json[0].color = "red";
json[1] = {};
json[1].color = "blue";
```

### Example 9: Full Pipeline

Starting JSON (`users.json`):
```json
{
  "users": [
    {"name": "Alice", "role": "admin", "email": "alice@example.com"},
    {"name": "Bob", "role": "user", "email": "bob@example.com"},
    {"name": "Charlie", "role": "admin", "email": "charlie@example.com"}
  ]
}
```

Find all admin users and reconstruct JSON:
```bash
$ gron users.json | grep "admin"
json.users[0].role = "admin";
json.users[2].role = "admin";

$ gron users.json | grep "users\[0\]\|users\[2\]" | gron -u
{
  "users": [
    {
      "email": "alice@example.com",
      "name": "Alice",
      "role": "admin"
    },
    null,
    {
      "email": "charlie@example.com",
      "name": "Charlie",
      "role": "admin"
    }
  ]
}
```

### Example 10: Values Mode

Input:
```json
{"name": "Tom", "scores": [95, 87, 92], "active": true}
```

Command:
```bash
echo '{"name": "Tom", "scores": [95, 87, 92], "active": true}' | gron --values
```

Output:
```
true
"Tom"
95
87
92
```

---

## Glossary

**Assignment statement**: A single line of gron output representing the full path
to a JSON value and the value itself, in the form `path = value;`.

**Bare identifier**: A JSON key that qualifies as a valid JavaScript identifier and
is therefore written with dot notation (`json.key`).

**Bracket notation**: The `["key"]` syntax used for JSON keys that are not valid
JavaScript identifiers.

**Container**: An object (`{}`) or array (`[]`) in JSON. Containers are initialized
with assignment statements before their children.

**gron**: The forward operation: converting JSON to assignment statements.

**Leaf value**: A scalar JSON value (string, number, boolean, or null) at the end
of a path. Leaf values have no children.

**Natural sort**: A sorting algorithm that treats numeric substrings as numbers
rather than text, so `[2]` sorts before `[10]`.

**NDJSON**: Newline-Delimited JSON. A format where each line is a self-contained
JSON value. Also known as JSON Lines.

**Path**: The left-hand side of a gron assignment, representing the chain of
property accesses from the root `json` identifier to a specific value.

**Root identifier**: The `json` identifier that begins every gron path.

**Scalar**: A non-container JSON value: string, number, boolean, or null.

**Statement**: Synonym for assignment statement.

**Ungron**: The reverse operation: converting gron assignment statements back to
JSON.
