# go-mod-outdated -- Display Outdated Go Dependencies

---

## 1. Overview

go-mod-outdated is a command-line utility written in Go that transforms the JSON output of `go list -u -m -json all` into a human-readable table format. It provides a clear, structured view of all Go module dependencies alongside their current versions, available updates, dependency type (direct or indirect), and timestamp validity.

Critically, go-mod-outdated does NOT query any package registries, resolve dependency versions, parse `go.mod` files, or interact with the Go module cache. It is purely a **formatter and filter** that consumes the structured JSON output produced by the Go toolchain. Its sole responsibility is to read a concatenated stream of JSON objects from standard input, apply optional filters, and render the result as a formatted table on standard output.

This design makes go-mod-outdated a composable Unix pipeline filter. It follows the Unix philosophy of doing one thing well: it takes structured data in and produces formatted, optionally filtered data out.

### 1.1 Primary Use Case

The primary use case is answering the question "which of my Go module dependencies are outdated?" in a format that is easy to read in a terminal or paste into a Markdown document. The tool is also suitable for CI/CD pipelines where a non-zero exit code should signal the presence of outdated dependencies.

### 1.2 Design Philosophy

go-mod-outdated adheres to several key design principles:

- **Single responsibility**: The tool only formats and filters. It delegates all version resolution and dependency graph analysis to `go list`.
- **Stdin/stdout pipeline**: The tool reads exclusively from stdin and writes exclusively to stdout. It does not read or write files, connect to networks, or invoke subprocesses.
- **Minimal configuration**: The tool accepts a small number of boolean and string flags. There are no configuration files, environment variables, or interactive prompts.
- **Predictable output**: The table format is deterministic given the same input and flags. The order of rows matches the order of JSON objects in the input stream.
- **Graceful degradation**: Parse errors are logged but do not cause a non-zero exit code (unless `-ci` mode is active and outdated dependencies exist in the successfully parsed portion).

---

## 2. Installation

### 2.1 Via go install

```bash
go install github.com/psampaz/go-mod-outdated@latest
```

This installs the binary into `$GOPATH/bin` (or `$GOBIN` if set). Ensure that directory is in your `PATH`.

### 2.2 Via go get (legacy, Go < 1.17)

```bash
GO111MODULE=on go get github.com/psampaz/go-mod-outdated
```

### 2.3 Pre-built Binaries

Pre-built binaries for Linux, macOS, and Windows are available on the GitHub releases page. Download the appropriate archive for your platform, extract it, and place the binary in a directory on your `PATH`.

### 2.4 Docker

The tool is available as a Docker image:

```bash
go list -u -m -json all | docker run --rm -i psampaz/go-mod-outdated [flags]
```

The `-i` flag is essential to allow stdin to be piped into the container. The `--rm` flag removes the container after execution.

---

## 3. Command-Line Usage

### 3.1 Basic Invocation

go-mod-outdated is designed exclusively as a Unix pipeline filter. It reads from standard input and writes to standard output. The canonical invocation is:

```bash
go list -u -m -json all | go-mod-outdated
```

This produces a table of all dependencies (excluding the main module) with their current version, available update version, direct/indirect status, and timestamp validity.

### 3.2 Flag Reference

The following flags are supported:

#### 3.3.1 `-update`

**Type**: Boolean (presence flag)
**Default**: `false`

When specified, only modules that have an available update are included in the output. Modules where the `Update` field is nil (or, in the case of replaced modules, where the replacement's `Update` field is nil) are excluded.

This flag answers the question: "Which of my dependencies have newer versions available?"

Example:

```bash
go list -u -m -json all | go-mod-outdated -update
```

Without `-update`, all dependencies are shown regardless of whether an update is available. The "NEW VERSION" column will simply be empty for modules without updates.

#### 3.3.2 `-direct`

**Type**: Boolean (presence flag)
**Default**: `false`

When specified, only direct dependencies are included in the output. A direct dependency is one where `Indirect` is `false` in the JSON input. Indirect dependencies (transitive dependencies not directly imported by the project) are excluded.

This flag answers the question: "Which of my direct dependencies need attention?"

Example:

```bash
go list -u -m -json all | go-mod-outdated -direct
```

#### 3.3.3 `-ci`

**Type**: Boolean (presence flag)
**Default**: `false`

Enables CI (Continuous Integration) mode. When this flag is set, the tool returns a non-zero exit code (specifically exit code 1) when at least one outdated dependency is found in the **filtered** list. Without this flag, the tool always exits with code 0 regardless of the output.

The word "outdated" in this context means "has an available update" -- that is, the `Update` field (or `Replace.Update` field for replaced modules) is not nil.

The CI check operates on the list AFTER all other filters have been applied. This means:

- `-ci` alone: exits 1 if ANY non-main dependency has an update.
- `-direct -ci`: exits 1 only if at least one DIRECT dependency has an update. Indirect dependencies with updates do not trigger the non-zero exit.
- `-update -ci`: exits 1 if the `-update` filter produces any output at all (which it will, by definition, if any dependency has an update).
- `-update -direct -ci`: exits 1 only if at least one direct dependency has an update.

Example:

```bash
go list -u -m -json all | go-mod-outdated -update -direct -ci
```

This is the most common CI pipeline invocation: "fail the build if any direct dependency has a newer version available."

#### 3.3.4 `-style <STYLE>`

**Type**: String
**Default**: `"default"`
**Accepted values**: `"default"`, `"markdown"`

Controls the output table style.

- `"default"`: Renders an ASCII table with box-drawing borders using `+`, `-`, and `|` characters. This is the standard table format provided by the `tablewriter` library.
- `"markdown"`: Renders a Markdown-compatible table without top/bottom borders. Uses `|` as column separators and `---` as header separators.

Any value other than `"markdown"` is treated as `"default"`. There is no validation error for unrecognized style values.

Example:

```bash
go list -u -m -json all | go-mod-outdated -style markdown
```

### 3.4 Flag Combination Matrix

The following table shows all meaningful combinations of the `-update`, `-direct`, and `-ci` flags and their behavior:

| `-update` | `-direct` | `-ci` | Modules Shown | Exit Code |
|-----------|-----------|-------|---------------|-----------|
| no | no | no | All non-main modules | 0 |
| yes | no | no | Only modules with updates | 0 |
| no | yes | no | Only direct modules | 0 |
| yes | yes | no | Only direct modules with updates | 0 |
| no | no | yes | All non-main modules | 1 if any has update, else 0 |
| yes | no | yes | Only modules with updates | 1 if any shown, else 0 |
| no | yes | yes | Only direct modules | 1 if any direct has update, else 0 |
| yes | yes | yes | Only direct modules with updates | 1 if any shown, else 0 |

Note that `-update -ci` will always exit 1 if ANY module with an update exists, because the `-update` filter guarantees that only modules with updates appear, and the `-ci` flag then checks whether the filtered list contains any modules with updates (which it does by definition if the list is non-empty).

### 3.5 Flag Parsing Details

go-mod-outdated uses Go's standard `flag` package for argument parsing. This has several implications:

1. **Single-dash only**: Flags must use single-dash syntax: `-update`, `-direct`, `-ci`, `-style`. Double-dash syntax (`--update`) is NOT supported and will produce an error.

2. **Boolean flag syntax**: Boolean flags can be specified as `-update`, `-update=true`, or `-update true`. The bare `-update` form sets the flag to `true`.

3. **String flag syntax**: The `-style` flag requires a value and can be specified as `-style markdown`, `-style=markdown`, or `-style "markdown"`.

4. **Flag ordering**: Flags can appear in any order. `-update -direct -ci` is equivalent to `-ci -direct -update`.

5. **Unknown flags**: Specifying an unrecognized flag causes the program to print an error message and exit with code 2 (standard `flag` package behavior).

6. **Non-flag arguments**: Any non-flag arguments after the flags are ignored. The tool reads exclusively from stdin and does not accept file path arguments.

---

## 4. Input Format

### 4.1 Expected Input

The tool expects the JSON output of `go list -u -m -json all` piped to its standard input. This is a **concatenated stream of JSON objects**, NOT a JSON array. Each object is a complete, self-contained JSON document representing a single Go module.

The distinction between a concatenated stream and a JSON array is important:

**Concatenated stream (what go list produces):**
```json
{
    "Path": "my/project",
    "Main": true,
    "GoVersion": "1.21"
}
{
    "Path": "github.com/example/foo",
    "Version": "v1.2.3"
}
{
    "Path": "github.com/example/bar",
    "Version": "v0.5.0"
}
```

**JSON array (NOT the format used):**
```json
[
    {"Path": "my/project", "Main": true},
    {"Path": "github.com/example/foo", "Version": "v1.2.3"},
    {"Path": "github.com/example/bar", "Version": "v0.5.0"}
]
```

go-mod-outdated uses Go's `json.Decoder` to read objects one at a time from the stream. This is the idiomatic Go approach for processing concatenated JSON streams and handles the format produced by `go list` without any additional parsing logic.

### 4.2 The Module Struct

Each JSON object in the input stream represents a Go module and conforms to the following structure (matching Go's `cmd/go` internal representation):

```go
type Module struct {
    Path       string       // Module path (e.g., "github.com/org/repo")
    Version    string       // Version string (e.g., "v1.2.3")
    Time       *time.Time   // Timestamp of the version
    Update     *Module      // Available update (nil if none)
    Replace    *Module      // Replacement module (nil if no replace directive)
    Main       bool         // True for the main module (project itself)
    Indirect   bool         // True if not directly imported
    Dir        string       // Local cache directory path
    GoMod      string       // Path to cached go.mod file
    GoVersion  string       // Required Go version
    Error      *ModuleError // Error information (nil if no error)
}
```

```go
type ModuleError struct {
    Err string // Error message text
}
```

### 4.3 Field Descriptions

#### 4.3.1 Path

**Type**: `string`
**Always present**: Yes

The module path is the canonical identifier for the module. It typically follows the format of a repository URL without the scheme, e.g., `github.com/psampaz/go-mod-outdated`. For the Go standard library, the path is `std`. For the main module, this is the module path declared in `go.mod`.

The `Path` field is used directly as the value in the MODULE column of the output table. Even when a module has a `Replace` directive, the original module's `Path` is shown, not the replacement's path.

#### 4.3.2 Version

**Type**: `string`
**Always present**: No (may be empty for the main module)

The current version string of the module. This follows Go's module versioning scheme:

- **Tagged versions**: `v1.2.3`, `v0.1.0`, `v2.0.0-beta.1`
- **Pseudo-versions**: `v0.0.0-20230115120000-abcdef123456`
- **Pre-release versions**: `v1.0.0-rc.1`
- **Major version suffixes**: For modules at v2 or higher, the path includes the major version (e.g., `github.com/example/mod/v2` at `v2.3.0`)

When the module has a `Replace` directive, the tool uses `Replace.Version` instead of `Version` for the VERSION column.

#### 4.3.3 Time

**Type**: `*time.Time` (nullable)
**Always present**: No

The timestamp associated with the version. For tagged releases, this is the commit timestamp of the tagged commit. For pseudo-versions, this is the commit timestamp encoded in the pseudo-version string.

This field is used in timestamp validation (see Section 8). If the field is nil, timestamp validation may behave differently depending on Go's time zero value semantics.

#### 4.3.4 Update

**Type**: `*Module` (nullable)
**Always present**: No (nil when no update is available)

When the `-u` flag is passed to `go list`, it populates this field with information about the latest available version of the module. The `Update` field itself is a `Module` struct containing at minimum `Path`, `Version`, and `Time`.

If no newer version is available, this field is nil (absent from the JSON). The presence or absence of this field is what determines whether the "NEW VERSION" column has a value and whether the module is considered "outdated" for `-update` and `-ci` purposes.

#### 4.3.5 Replace

**Type**: `*Module` (nullable)
**Always present**: No (nil when no replace directive applies)

When a `replace` directive in `go.mod` applies to this module, the `Replace` field contains the replacement module's information. This is a full `Module` struct and may itself contain `Update`, `Time`, and other fields.

Replace directives are a powerful Go modules feature that allows redirecting a dependency to a different module path, a local directory, or a specific version. The presence of a `Replace` field fundamentally changes how go-mod-outdated extracts version information (see Section 7).

#### 4.3.6 Main

**Type**: `bool`
**Default**: `false`

True for the main module -- the project whose dependencies are being listed. The main module always appears first in the `go list` output. go-mod-outdated always filters out the main module regardless of any flags. The main module never appears in the output table.

#### 4.3.7 Indirect

**Type**: `bool`
**Default**: `false`

True when the module is an indirect (transitive) dependency. An indirect dependency is one that is required by one of your direct dependencies but is not directly imported by your project's code. In `go.mod`, these are marked with the `// indirect` comment.

go-mod-outdated negates this field for the DIRECT column: `DIRECT = !Indirect`. So a module with `"Indirect": false` shows `true` in the DIRECT column, and vice versa.

#### 4.3.8 Dir

**Type**: `string`
**Always present**: No

The absolute path to the directory in the local module cache where the module's source code is stored. This field is informational and is not used by go-mod-outdated.

#### 4.3.9 GoMod

**Type**: `string`
**Always present**: No

The absolute path to the cached `go.mod` file for this module. This field is informational and is not used by go-mod-outdated.

#### 4.3.10 GoVersion

**Type**: `string`
**Always present**: No

The Go version required by this module, as declared in its `go.mod` file. For example, `"1.21"`. This field is informational and is not used by go-mod-outdated.

#### 4.3.11 Error

**Type**: `*ModuleError` (nullable)
**Always present**: No (nil when there is no error)

When `go list` encounters an error resolving or fetching a module, it populates this field with an error struct containing an `Err` string. Modules with errors are NOT specially handled by go-mod-outdated. They are included in the output table like any other module.

### 4.4 JSON Encoding Details

The JSON produced by `go list` uses Go's standard `encoding/json` marshaling with `omitempty` tags. This means:

- **Nil pointer fields** are omitted entirely from the JSON. A module without an update will not have an `"Update"` key at all, rather than having `"Update": null`.
- **False boolean fields** are omitted. A module that is not indirect will not have `"Indirect": false` in the JSON -- the key is simply absent.
- **Empty string fields** are omitted. A module without a version will not have `"Version": ""`.
- **Zero-value time fields** are omitted.

go-mod-outdated's JSON unmarshaling handles all of these cases correctly because Go's `json.Unmarshal` initializes missing fields to their zero values (nil for pointers, false for bools, empty string for strings, zero value for time.Time).

### 4.5 Complete Input Example

Below is a complete example of the JSON stream produced by `go list -u -m -json all` for a hypothetical project:

```json
{
    "Path": "github.com/myorg/myproject",
    "Main": true,
    "Dir": "/home/user/projects/myproject",
    "GoMod": "/home/user/projects/myproject/go.mod",
    "GoVersion": "1.21"
}
{
    "Path": "github.com/example/direct-dep",
    "Version": "v1.2.3",
    "Time": "2023-01-15T10:30:00Z",
    "Update": {
        "Path": "github.com/example/direct-dep",
        "Version": "v1.4.0",
        "Time": "2023-09-20T14:00:00Z"
    },
    "Dir": "/home/user/go/pkg/mod/github.com/example/direct-dep@v1.2.3",
    "GoMod": "/home/user/go/pkg/mod/cache/download/github.com/example/direct-dep/@v/v1.2.3.mod"
}
{
    "Path": "github.com/example/indirect-dep",
    "Version": "v0.8.1",
    "Time": "2022-11-03T08:15:00Z",
    "Indirect": true,
    "Dir": "/home/user/go/pkg/mod/github.com/example/indirect-dep@v0.8.1",
    "GoMod": "/home/user/go/pkg/mod/cache/download/github.com/example/indirect-dep/@v/v0.8.1.mod"
}
{
    "Path": "github.com/example/up-to-date",
    "Version": "v2.0.0",
    "Time": "2023-06-01T12:00:00Z",
    "Dir": "/home/user/go/pkg/mod/github.com/example/up-to-date@v2.0.0",
    "GoMod": "/home/user/go/pkg/mod/cache/download/github.com/example/up-to-date/@v/v2.0.0.mod"
}
{
    "Path": "github.com/example/replaced-dep",
    "Version": "v1.0.0",
    "Time": "2022-05-10T09:00:00Z",
    "Replace": {
        "Path": "github.com/myfork/replaced-dep",
        "Version": "v1.0.1-fork",
        "Time": "2023-02-14T16:30:00Z",
        "Update": {
            "Path": "github.com/myfork/replaced-dep",
            "Version": "v1.1.0-fork",
            "Time": "2023-08-01T10:00:00Z"
        }
    },
    "Dir": "/home/user/go/pkg/mod/github.com/myfork/replaced-dep@v1.0.1-fork",
    "GoMod": "/home/user/go/pkg/mod/cache/download/github.com/myfork/replaced-dep/@v/v1.0.1-fork.mod"
}
```

### 4.6 Empty Input

When the input is empty (immediate EOF with no data), the tool produces no output and exits with code 0. This is not treated as an error condition.

### 4.7 Malformed Input

When the JSON stream contains malformed JSON, the `json.Decoder` returns an error. go-mod-outdated logs this error via `log.Print` but does NOT exit with a non-zero code on account of the parse error alone. Any modules successfully parsed before the error are processed and displayed. The exit code is still determined by the usual rules: 0 unless `-ci` is set and outdated dependencies were found in the successfully parsed modules.

### 4.8 Input from Sources Other Than go list

While the tool is designed for `go list -u -m -json all` output, it can technically process any concatenated JSON stream that conforms to the Module struct format. This means you could construct synthetic input for custom workflows, feed it cached output from a previous `go list` run, or preprocess the JSON through `jq` or similar tools before piping it to go-mod-outdated.

However, the tool makes no guarantees about behavior with non-standard input beyond what is described in this document.

---

## 5. Output Format

### 5.1 Table Columns

The output table always has exactly five columns, in this order:

| Column | Description | Source |
|--------|-------------|--------|
| MODULE | Module path | `Path` field from the JSON object |
| VERSION | Current version in use | `Replace.Version` if replaced, else `Version` |
| NEW VERSION | Available update version | `Replace.Update.Version` if replaced, else `Update.Version`; empty if no update |
| DIRECT | Whether this is a direct dependency | Negation of `Indirect`: `"true"` if `Indirect` is false, `"false"` if `Indirect` is true |
| VALID TIMESTAMPS | Whether version timestamps are chronologically consistent | `"true"` if the update timestamp is NOT before the current timestamp; `"false"` if it is |

### 5.2 Default Style

The default style uses the `tablewriter` library (github.com/olekukonenko/tablewriter) to render an ASCII table with box-drawing borders. The table uses `+` for corners, `-` for horizontal borders, and `|` for vertical separators.

Example output:

```
+-------------------------------+----------+-------------+--------+------------------+
|            MODULE             | VERSION  | NEW VERSION | DIRECT | VALID TIMESTAMPS |
+-------------------------------+----------+-------------+--------+------------------+
| github.com/example/foo        | v1.0.0   | v1.2.0      | true   | true             |
| github.com/example/bar        | v0.5.0   |             | false  | true             |
| github.com/example/baz        | v2.1.0   | v2.3.0      | true   | false            |
+-------------------------------+----------+-------------+--------+------------------+
```

Key characteristics of the default style:

- Top border row: `+---+---+---+---+---+`
- Header row: `| MODULE | VERSION | ... |`
- Header separator: `+---+---+---+---+---+`
- Data rows: `| value | value | ... |`
- Bottom border row: `+---+---+---+---+---+`
- Column widths adjust automatically to fit content
- Header text is centered within each column
- Data text is left-aligned by default

### 5.3 Markdown Style

The markdown style produces a Markdown-compatible table that can be directly embedded in Markdown documents, GitHub issues, pull requests, or READMEs.

Example output:

```
|            MODULE             | VERSION  | NEW VERSION | DIRECT | VALID TIMESTAMPS |
|-------------------------------|----------|-------------|--------|------------------|
| github.com/example/foo        | v1.0.0   | v1.2.0      | true   | true             |
| github.com/example/bar        | v0.5.0   |             | false  | true             |
| github.com/example/baz        | v2.1.0   | v2.3.0      | true   | false            |
```

The markdown style is achieved by configuring the `tablewriter` library to:

- Disable the top border (no `+---+` row before the header)
- Disable the bottom border (no `+---+` row after the last data row)
- Set the center separator to `|` (instead of `+`)

This produces output that renders correctly as a table in any Markdown parser that supports the standard pipe-table syntax.

### 5.4 Row Ordering

Rows in the output table appear in the same order as the corresponding JSON objects in the input stream. go-mod-outdated does not sort the output. The order is determined by `go list`, which typically lists:

1. The main module (filtered out by go-mod-outdated)
2. Direct dependencies in lexicographic order by module path
3. Indirect dependencies in lexicographic order by module path

However, this ordering is an implementation detail of `go list` and is not guaranteed by go-mod-outdated.

### 5.5 Empty Results

If, after applying all filters (main module exclusion, `-update`, `-direct`), the resulting list of modules is empty, the table is NOT rendered at all. The output is completely empty -- no header row, no borders, no whitespace. This behavior was introduced in version 0.9.0.

Prior to v0.9.0, an empty table with only header rows would be rendered. The change to suppress empty tables was made to produce cleaner output in CI pipelines and scripts.

### 5.6 Column Value Details

#### 5.6.1 MODULE Column

This always contains the `Path` field from the original module JSON object. Even when a `Replace` directive redirects to a different module path or local directory, the MODULE column shows the original path, not the replacement path. This design decision ensures that the output table consistently shows what the project depends on conceptually, rather than where the code is sourced from.

Examples:
- `github.com/example/foo`
- `golang.org/x/text`
- `gopkg.in/yaml.v3`
- `github.com/example/mod/v2` (major version suffix)

#### 5.6.2 VERSION Column

This shows the currently-used version of the module. The logic for determining this value is:

```
if module has Replace directive:
    VERSION = Replace.Version
else:
    VERSION = module.Version
```

When a module is replaced by a local directory path (e.g., `replace github.com/example/foo => ../local-foo`), the replacement may not have a traditional version string. In such cases, the version might be empty or contain a directory path.

Examples:
- `v1.2.3` (standard semver)
- `v0.0.0-20230115120000-abcdef123456` (pseudo-version)
- `v2.0.0-beta.1` (pre-release)
- `v0.0.0` (when replaced by a local path with no version)

#### 5.6.3 NEW VERSION Column

This shows the version of the available update, if any. The logic is:

```
if module has Replace directive:
    if Replace has Update:
        NEW VERSION = Replace.Update.Version
    else:
        NEW VERSION = "" (empty)
else:
    if module has Update:
        NEW VERSION = Update.Version
    else:
        NEW VERSION = "" (empty)
```

When no update is available, this column is empty (not "N/A" or "none" -- simply an empty string).

#### 5.6.4 DIRECT Column

This is a string representation of the negation of the `Indirect` field:

```
DIRECT = "true"  if Indirect == false
DIRECT = "false" if Indirect == true
```

Note that the JSON field is `Indirect` (with the `// indirect` comment semantics from `go.mod`), but the output column is DIRECT (the logical negation). This is a deliberate design choice to make the output more intuitive: most users think in terms of "is this a direct dependency?" rather than "is this an indirect dependency?"

The values are the literal strings `"true"` and `"false"`, not `"yes"`/`"no"` or `"direct"`/`"indirect"`.

#### 5.6.5 VALID TIMESTAMPS Column

This column reports whether the version timestamps are chronologically consistent. The logic is:

```
VALID TIMESTAMPS = "true"  if NOT InvalidTimestamp
VALID TIMESTAMPS = "false" if InvalidTimestamp

where:
    InvalidTimestamp = Current.Time.After(Update.Time)
```

In other words, timestamps are considered INVALID when the current version's timestamp is AFTER the update version's timestamp. This would mean the "update" is actually an older build that happens to have a higher version number.

When there is no update available, the timestamp is considered valid (the column shows `"true"`).

See Section 8 for a detailed discussion of timestamp validation.

---

## 6. Main Module Filtering

### 6.1 Behavior

The main module (the project itself, where `Main: true` in the JSON) is ALWAYS excluded from the output table. This filtering is applied unconditionally, regardless of any flags. The rationale is that the main module is not a dependency -- it is the project being analyzed -- so including it in a table of dependencies would be misleading.

### 6.2 Position in Input

The main module always appears as the first JSON object in the `go list` output. However, go-mod-outdated does not rely on this ordering. It checks the `Main` field of every JSON object and excludes any object where `Main` is true.

### 6.3 Main Module JSON Example

```json
{
    "Path": "github.com/myorg/myproject",
    "Main": true,
    "Dir": "/home/user/projects/myproject",
    "GoMod": "/home/user/projects/myproject/go.mod",
    "GoVersion": "1.21"
}
```

Note that the main module typically does not have a `Version` field (since it is not a versioned dependency) and does not have `Update`, `Replace`, `Indirect`, or `Time` fields.

---

## 7. Replace Directive Handling

### 7.1 Overview of Replace Directives

Go modules support `replace` directives in `go.mod` that redirect a module to an alternative source. This is used for:

- Forking: Redirecting a dependency to a personal fork
- Local development: Redirecting to a local directory during development
- Version pinning: Forcing a specific version of a transitive dependency
- Module renaming: Handling modules that have moved to a new path

When a `replace` directive applies to a module, `go list` populates the `Replace` field in the JSON output with the replacement module's information.

### 7.2 Replace Directive Syntax in go.mod

```go
// Replace with a specific version of another module
replace github.com/original/module => github.com/fork/module v1.2.3

// Replace with a local directory
replace github.com/original/module => ../local-module

// Replace a specific version only
replace github.com/original/module v1.0.0 => github.com/fork/module v1.0.1
```

### 7.3 Impact on go-mod-outdated Output

When a module has a `Replace` field, go-mod-outdated changes its behavior for extracting version information. The tool provides four accessor methods (conceptually) that handle the replace logic:

#### 7.3.1 CurrentVersion()

```
if Replace != nil:
    return Replace.Version
else:
    return Version
```

This is used for the VERSION column. When a module is replaced, the replacement's version is what is actually being used, so that is what should be displayed.

#### 7.3.2 NewVersion()

```
if Replace != nil:
    if Replace.Update != nil:
        return Replace.Update.Version
    else:
        return ""
else:
    if Update != nil:
        return Update.Version
    else:
        return ""
```

This is used for the NEW VERSION column. When a module is replaced, what matters is whether the replacement has an update, not whether the original module has an update.

#### 7.3.3 HasUpdate()

```
if Replace != nil:
    return Replace.Update != nil
else:
    return Update != nil
```

This is used by the `-update` filter and `-ci` exit code logic. A replaced module is considered to have an update only if the REPLACEMENT module has an update.

#### 7.3.4 InvalidTimestamp()

```
if Replace != nil:
    return Replace.Time.After(Replace.Update.Time)
else:
    return Time.After(Update.Time)
```

This is used for the VALID TIMESTAMPS column. When a module is replaced, the timestamps that matter are the replacement's timestamps.

### 7.4 MODULE Column with Replace

Importantly, the MODULE column always shows the original module's `Path`, NOT the replacement's `Path`. This is because the `replace` directive is an implementation detail of the current project's `go.mod`. The conceptual dependency is still on the original module; the replace directive merely redirects where the code comes from.

For example, if `go.mod` contains:

```
replace github.com/original/module => github.com/myfork/module v1.0.1
```

The MODULE column will show `github.com/original/module`, the VERSION column will show `v1.0.1` (the fork's version), and the DIRECT column will reflect the original module's indirect status.

### 7.5 Replace to Local Directory

When a module is replaced with a local directory path:

```
replace github.com/original/module => ../local-module
```

The replacement may not have a standard version string. The `Replace.Version` field may be empty. The `Replace.Update` field will be nil (local directories do not have registry-based updates). In this case:

- VERSION column: empty or contains the local path
- NEW VERSION column: empty
- HasUpdate(): false
- VALID TIMESTAMPS: true (no update to compare against)

### 7.6 Replace with Update Available

When a replaced module has an update available for the replacement:

```json
{
    "Path": "github.com/original/module",
    "Version": "v1.0.0",
    "Replace": {
        "Path": "github.com/fork/module",
        "Version": "v1.0.1",
        "Time": "2023-01-15T00:00:00Z",
        "Update": {
            "Path": "github.com/fork/module",
            "Version": "v1.1.0",
            "Time": "2023-06-20T00:00:00Z"
        }
    }
}
```

Output for this module:

| MODULE | VERSION | NEW VERSION | DIRECT | VALID TIMESTAMPS |
|--------|---------|-------------|--------|------------------|
| github.com/original/module | v1.0.1 | v1.1.0 | true | true |

Note: VERSION shows `v1.0.1` (from Replace), NEW VERSION shows `v1.1.0` (from Replace.Update), but MODULE shows the original path.

### 7.7 Replace Edge Cases

#### 7.7.1 Replace with No Update on Original but Update on Replacement

If the original module has an `Update` field but the replacement does not, the module is NOT considered to have an update. The replacement's update status takes precedence.

#### 7.7.2 Replace with Update on Original but Not Shown

If the original module has `Update` but `Replace` exists, the original's `Update` is ignored entirely. Only `Replace.Update` matters.

#### 7.7.3 Nested Replace

Go modules do not support nested replace directives (a replacement cannot itself have a replace). However, the `Replace` field is a `Module` struct that structurally could contain a `Replace` field. go-mod-outdated does not recurse into nested replaces. Only the top-level `Replace` is considered.

#### 7.7.4 Replace Where Path Differs

When the replacement has a different `Path` than the original:

```json
{
    "Path": "github.com/original/module",
    "Version": "v1.0.0",
    "Replace": {
        "Path": "github.com/completely/different/module",
        "Version": "v3.0.0"
    }
}
```

The MODULE column still shows `github.com/original/module`. Only the version information comes from the replacement.

---

## 8. Timestamp Validation

### 8.1 Purpose

The VALID TIMESTAMPS column serves as a data quality indicator. In the Go module ecosystem, it is possible for an "update" to have an older timestamp than the currently-used version. This typically indicates a pseudo-version anomaly where version ordering does not correspond to chronological ordering.

### 8.2 The InvalidTimestamp Check

The timestamp validation logic is straightforward:

```
InvalidTimestamp = Current.Time.After(Update.Time)
```

Where:
- `Current.Time` is the timestamp of the currently-used version (from `Replace.Time` if replaced, else `Time`)
- `Update.Time` is the timestamp of the available update (from `Replace.Update.Time` if replaced, else `Update.Time`)

The timestamps are invalid (VALID TIMESTAMPS = `"false"`) when the current version's timestamp is strictly AFTER the update's timestamp.

### 8.3 When Invalid Timestamps Occur

#### 8.3.1 Pseudo-version Ordering

Go pseudo-versions encode a commit timestamp and hash:

```
v0.0.0-20230115120000-abcdef123456
```

The version string `v0.0.0-YYYYMMDDHHMMSS-hash` sorts lexicographically. However, the pseudo-version is typically generated from the commit timestamp, not the version number. If a tagged release (e.g., `v1.0.0`) was made from a commit older than the pseudo-version's commit, `go list -u` might report the tagged release as an "update" even though it has an older timestamp.

Example scenario:
1. Developer makes commit A on 2023-06-01, creating pseudo-version `v0.0.0-20230601000000-aaa`
2. Developer tags commit B (from 2023-01-15) as `v1.0.0`
3. `go list -u` sees `v1.0.0` as an update to the pseudo-version (higher semver)
4. But `v1.0.0`'s timestamp (2023-01-15) is BEFORE the pseudo-version's timestamp (2023-06-01)
5. go-mod-outdated flags this with VALID TIMESTAMPS = `"false"`

#### 8.3.2 Retracted Versions

When a module author retracts a version and publishes a new one, the new version might have a higher version number but could reference an older commit. This can also trigger invalid timestamp detection.

#### 8.3.3 Force-pushed Tags

If a module author force-pushes a tag to a different commit, the timestamp associated with the tag might change. This can create timestamp inconsistencies.

### 8.4 When No Update Exists

When a module has no available update (the `Update` field is nil), there is no update timestamp to compare against. In this case, `InvalidTimestamp` is `false`, and the VALID TIMESTAMPS column shows `"true"`. The absence of an update is not considered a timestamp issue.

### 8.5 Replaced Module Timestamps

For replaced modules, the timestamp comparison uses the replacement's timestamps:

```
if Replace != nil:
    InvalidTimestamp = Replace.Time.After(Replace.Update.Time)
else:
    InvalidTimestamp = Time.After(Update.Time)
```

This ensures that timestamp validation is consistent with the version information shown in the VERSION and NEW VERSION columns.

### 8.6 Practical Implications

An invalid timestamp does not necessarily mean the update should be ignored. It is an informational flag that alerts the user to an unusual situation worth investigating. Common responses include:

- Investigating whether the "update" is genuinely a newer release
- Checking whether the current pseudo-version should be replaced with the tagged release
- Verifying that the module author's tagging practices are correct

---

## 9. CI Mode

### 9.1 Overview

The `-ci` flag enables Continuous Integration mode. In this mode, go-mod-outdated uses its exit code to signal whether outdated dependencies were found. This allows CI pipelines to fail builds when dependencies are not up to date.

### 9.2 Exit Code Semantics

| Condition | Exit Code |
|-----------|-----------|
| Normal operation (no `-ci` flag) | 0 |
| `-ci` flag, no outdated dependencies in filtered list | 0 |
| `-ci` flag, at least one outdated dependency in filtered list | 1 |
| JSON parse error (with or without `-ci`) | 0 |

### 9.3 What Constitutes "Outdated"

A module is considered "outdated" for CI purposes when it has an available update. Specifically:

- If the module has a `Replace` directive: `Replace.Update != nil`
- Otherwise: `Update != nil`

This is the same `HasUpdate()` logic used by the `-update` filter.

### 9.4 Interaction with Filters

The CI check operates on the list AFTER all other filters have been applied. This is a critical detail that affects how the exit code is determined.

#### 9.4.1 `-ci` Alone

All non-main modules are in the filtered list. The exit code is 1 if ANY module has an update.

```bash
go list -u -m -json all | go-mod-outdated -ci
# Exits 1 if any dependency (direct or indirect) has an update
```

#### 9.4.2 `-direct -ci`

Only direct modules are in the filtered list. The exit code is 1 only if a DIRECT module has an update. Indirect modules with updates do NOT trigger the non-zero exit.

```bash
go list -u -m -json all | go-mod-outdated -direct -ci
# Exits 1 only if a direct dependency has an update
```

#### 9.4.3 `-update -ci`

Only modules with updates are in the filtered list (by the `-update` filter). The CI check then asks if any module in this list has an update -- which is trivially true for every module in the list (since the `-update` filter only includes modules with updates). Therefore, `-update -ci` exits 1 if and only if there is at least one module with an update, and exits 0 if no modules have updates (empty filtered list).

```bash
go list -u -m -json all | go-mod-outdated -update -ci
# Exits 1 if any dependency has an update (same as -ci alone, in practice)
```

#### 9.4.4 `-update -direct -ci`

Only direct modules with updates are in the filtered list. The CI check exits 1 if this list is non-empty, i.e., if any direct dependency has an update.

```bash
go list -u -m -json all | go-mod-outdated -update -direct -ci
# Exits 1 only if a direct dependency has an update
```

### 9.5 CI Pipeline Examples

#### 9.5.1 GitHub Actions

```yaml
- name: Check for outdated dependencies
  run: go list -u -m -json all | go-mod-outdated -update -direct -ci
```

#### 9.5.2 GitLab CI

```yaml
check-deps:
  script:
    - go list -u -m -json all | go-mod-outdated -update -direct -ci
```

#### 9.5.3 Jenkins

```groovy
stage('Dependency Check') {
    steps {
        sh 'go list -u -m -json all | go-mod-outdated -update -direct -ci'
    }
}
```

#### 9.5.4 CircleCI

```yaml
- run:
    name: Check outdated dependencies
    command: go list -u -m -json all | go-mod-outdated -update -direct -ci
```

### 9.6 CI Mode with Docker

```bash
go list -u -m -json all | docker run --rm -i psampaz/go-mod-outdated -update -direct -ci
```

The Docker container's exit code is propagated to the host, so CI pipelines can use the Docker invocation directly.

### 9.7 Handling CI Failures

When `-ci` causes a non-zero exit code, the output table is still printed to stdout. This allows CI logs to show which dependencies are outdated even as the step fails. The table output is produced before the exit code is set.

---

## 10. Pseudo-version Handling

### 10.1 What Are Pseudo-versions

Go pseudo-versions are version strings that encode a commit timestamp and hash for untagged commits. They follow one of three formats:

```
vX.0.0-YYYYMMDDHHMMSS-abcdefabcdef    (base version v0.0.0 or vX.0.0)
vX.Y.Z-pre.0.YYYYMMDDHHMMSS-abcdefabcdef  (based on a pre-release tag)
vX.Y.(Z+1)-0.YYYYMMDDHHMMSS-abcdefabcdef  (based on a release tag)
```

Where:
- `YYYYMMDDHHMMSS` is the UTC commit timestamp
- `abcdefabcdef` is the first 12 characters of the commit hash

### 10.2 Pseudo-versions in go-mod-outdated

go-mod-outdated treats pseudo-versions identically to tagged versions. The VERSION and NEW VERSION columns display the full pseudo-version string without any special formatting or abbreviation.

Example output with pseudo-versions:

```
+----------------------------------------------+----------------------------------------------+----------------------------------------------+--------+------------------+
|                    MODULE                    |                   VERSION                    |                 NEW VERSION                  | DIRECT | VALID TIMESTAMPS |
+----------------------------------------------+----------------------------------------------+----------------------------------------------+--------+------------------+
| golang.org/x/crypto                          | v0.0.0-20230115120000-abcdef123456           | v0.12.0                                      | true   | true             |
| golang.org/x/sys                             | v0.0.0-20230201000000-fedcba654321           | v0.0.0-20230901150000-111222333444           | false  | true             |
+----------------------------------------------+----------------------------------------------+----------------------------------------------+--------+------------------+
```

### 10.3 Pseudo-version to Tagged Version Updates

A common scenario is a dependency currently pinned at a pseudo-version with a tagged release available as an update:

```json
{
    "Path": "golang.org/x/text",
    "Version": "v0.0.0-20230115120000-abcdef123456",
    "Time": "2023-01-15T12:00:00Z",
    "Update": {
        "Path": "golang.org/x/text",
        "Version": "v0.12.0",
        "Time": "2023-07-20T00:00:00Z"
    }
}
```

In this case:
- VERSION: `v0.0.0-20230115120000-abcdef123456`
- NEW VERSION: `v0.12.0`
- VALID TIMESTAMPS: `"true"` (2023-07-20 is after 2023-01-15)

### 10.4 Pseudo-version Timestamp Anomalies

The most common cause of invalid timestamps involves pseudo-versions. Consider this scenario:

1. A module has no tagged releases
2. Your project depends on a pseudo-version from a recent commit
3. The module author tags an older commit as `v1.0.0`
4. `go list -u` reports `v1.0.0` as an update
5. But the tagged commit is older than the pseudo-version's commit

```json
{
    "Path": "github.com/example/new-module",
    "Version": "v0.0.0-20230601000000-aaa111bbb222",
    "Time": "2023-06-01T00:00:00Z",
    "Update": {
        "Path": "github.com/example/new-module",
        "Version": "v1.0.0",
        "Time": "2023-03-15T00:00:00Z"
    }
}
```

In this case:
- VERSION: `v0.0.0-20230601000000-aaa111bbb222`
- NEW VERSION: `v1.0.0`
- VALID TIMESTAMPS: `"false"` (2023-06-01 is after 2023-03-15)

This alerts the user that upgrading to `v1.0.0` would actually move to an older codebase (in terms of commit history), even though `v1.0.0` has a higher version number.

### 10.5 Pseudo-version to Pseudo-version Updates

When both the current version and the update are pseudo-versions:

```json
{
    "Path": "golang.org/x/net",
    "Version": "v0.0.0-20230201000000-aaa111222333",
    "Time": "2023-02-01T00:00:00Z",
    "Update": {
        "Path": "golang.org/x/net",
        "Version": "v0.0.0-20230901000000-bbb444555666",
        "Time": "2023-09-01T00:00:00Z"
    }
}
```

Here the timestamps will almost always be valid because the pseudo-version's embedded timestamp corresponds to the `Time` field, and a higher pseudo-version number inherently implies a later timestamp.

---

## 11. Error Handling

### 11.1 JSON Parse Errors

When the JSON input stream contains malformed data that cannot be parsed by `json.Decoder`, go-mod-outdated handles the error as follows:

1. The error is logged via Go's `log.Print` function. This writes the error message to stderr.
2. Any modules successfully parsed before the error are processed normally.
3. The program exits with code 0 (unless `-ci` is set and outdated dependencies were found among the successfully parsed modules).

This design choice means that a partial or corrupt input stream does not crash the program. It degrades gracefully by processing what it can.

### 11.2 Empty Input

Empty input (stdin is immediately at EOF with no data) is handled as a special case of "zero modules parsed." The tool produces no output and exits 0. This is not logged as an error.

### 11.3 Modules with Error Fields

When a module's JSON object includes an `Error` field (a `*ModuleError` struct with an `Err` string), go-mod-outdated does NOT treat this specially. The module is included in the output like any other module. The `Error` field is not displayed in the table and does not affect filtering.

This means that modules with resolution errors will appear in the table with whatever version information is available (which may be incomplete).

### 11.4 Missing or Zero-value Fields

Because Go's JSON unmarshaling initializes missing fields to zero values:

- Missing `Version`: empty string in VERSION column
- Missing `Time`: zero time value (`time.Time{}`), which may affect timestamp validation
- Missing `Indirect`: defaults to `false`, meaning the module is treated as direct
- Missing `Update`: treated as no update available
- Missing `Replace`: treated as no replacement
- Missing `Main`: treated as not the main module
- Missing `Path`: empty string in MODULE column (unusual but handled)

### 11.5 Exit Codes Summary

| Scenario | Exit Code |
|----------|-----------|
| Normal execution, no `-ci` | 0 |
| `-ci`, no outdated deps in filtered list | 0 |
| `-ci`, outdated deps in filtered list | 1 |
| JSON parse error, no `-ci` | 0 |
| JSON parse error, `-ci`, no outdated deps parsed | 0 |
| JSON parse error, `-ci`, outdated deps parsed before error | 1 |
| Empty input | 0 |
| Unknown flag | 2 (standard flag package behavior) |

---

## 12. Go Toolchain Integration

### 12.1 The Pipeline

go-mod-outdated is designed as the second stage of a two-stage pipeline:

```bash
go list -u -m -json all | go-mod-outdated [flags]
```

Stage 1 (`go list`) does all the heavy lifting: resolving the dependency graph, querying registries for updates, and producing structured JSON output. Stage 2 (go-mod-outdated) formats and filters.

### 12.2 go list Flags Explained

#### 12.2.1 `-u` (Update Information)

The `-u` flag tells `go list` to populate the `Update` field for each module with information about the latest available version. Without this flag, the `Update` field is always nil, and go-mod-outdated cannot determine whether updates are available.

This flag causes `go list` to query the Go module proxy (typically `proxy.golang.org`) for each dependency to check for newer versions. This makes `go list -u` significantly slower than `go list` alone, as it involves network requests.

#### 12.2.2 `-m` (Module Mode)

The `-m` flag switches `go list` from listing packages to listing modules. Without this flag, `go list` operates on Go packages (directories within modules), which is not what go-mod-outdated expects.

#### 12.2.3 `-json` (JSON Output)

The `-json` flag causes `go list` to output each item as a JSON object instead of a single line of text. This produces the concatenated JSON stream that go-mod-outdated expects.

#### 12.2.4 `all` (Dependency Scope)

The `all` argument tells `go list` to include all modules in the dependency graph, not just the main module. This includes both direct and indirect (transitive) dependencies.

Without `all`, only the main module is listed, which would produce an output consisting solely of the main module (which go-mod-outdated filters out), resulting in an empty table.

### 12.3 Alternative go list Invocations

While `go list -u -m -json all` is the canonical invocation, variations are possible:

#### 12.3.1 Without `-u`

```bash
go list -m -json all | go-mod-outdated
```

Without `-u`, no update information is available. The NEW VERSION column will be empty for all modules, `-update` will produce an empty table, and `-ci` will always exit 0. This is fast but not very useful.

#### 12.3.2 Specific Module

```bash
go list -u -m -json github.com/example/specific-module | go-mod-outdated
```

This checks only a single module. The output will contain at most one row (or zero if the module is the main module).

#### 12.3.3 With `-versions`

```bash
go list -u -m -json -versions all | go-mod-outdated
```

The `-versions` flag adds a `Versions` field listing all available versions. go-mod-outdated does not use this field, but its presence does not cause any issues (it is simply ignored during JSON unmarshaling if not defined in the struct).

### 12.4 Go Version Compatibility

#### 12.4.1 Go 1.11-1.12 (Early Modules)

The basic `go list -u -m -json all` pipeline works with Go 1.11 and 1.12. Module support was introduced as an experimental feature in Go 1.11 and became the default in Go 1.12 (with `GO111MODULE=on`).

#### 12.4.2 Go 1.13

Go 1.13 introduced the module proxy (`GOPROXY=https://proxy.golang.org,direct` by default) and checksum database. This does not affect go-mod-outdated's behavior but makes `go list -u` faster and more reliable.

#### 12.4.3 Go 1.14+ (Vendoring)

Go 1.14 introduced automatic vendoring when a `vendor` directory is present. With vendoring enabled, `go list -u -m -json all` may fail with an error like:

```
go list -m: can't determine available upgrades using the vendor directory
```

The workaround is to use `-mod=mod`:

```bash
go list -u -m -mod=mod -json all | go-mod-outdated
```

The `-mod=mod` flag tells `go list` to use the module cache instead of the vendor directory for the purpose of this listing.

#### 12.4.4 Go 1.16

Go 1.16 made module mode the default (`GO111MODULE=on`). No special configuration is needed.

#### 12.4.5 Go 1.17+

Go 1.17 changed the `go.mod` file format to include indirect dependencies separately. This does not affect go-mod-outdated because `go list` handles the translation.

### 12.5 GOPROXY and GONOSUMCHECK

The `go list -u` command respects standard Go environment variables:

- `GOPROXY`: Controls which module proxy to use for fetching module information
- `GONOSUMCHECK`: Controls which modules skip checksum verification
- `GOPRIVATE`: Controls which modules are fetched directly (not via proxy)
- `GONOSUMDB`: Controls which modules skip the checksum database

These variables affect `go list`'s behavior, not go-mod-outdated's. However, they can affect what update information is available. For example, private modules behind a corporate firewall might not have update information if the proxy cannot access them.

---

## 13. Docker Usage

### 13.1 Basic Docker Invocation

```bash
go list -u -m -json all | docker run --rm -i psampaz/go-mod-outdated
```

Key Docker flags:
- `--rm`: Removes the container after execution (cleanup)
- `-i`: Keeps stdin open, allowing the piped input to reach the go-mod-outdated process inside the container

### 13.2 Docker with Flags

All go-mod-outdated flags can be appended after the image name:

```bash
go list -u -m -json all | docker run --rm -i psampaz/go-mod-outdated -update -direct -ci
```

```bash
go list -u -m -json all | docker run --rm -i psampaz/go-mod-outdated -style markdown
```

### 13.3 Docker in CI Pipelines

Docker invocation is useful in CI environments where installing Go tools is inconvenient or where you want to use a specific version of go-mod-outdated:

```yaml
# GitHub Actions example
- name: Check outdated dependencies
  run: |
    go list -u -m -json all | docker run --rm -i psampaz/go-mod-outdated -update -direct -ci
```

### 13.4 Docker Image Versioning

Specific versions of the Docker image can be referenced by tag:

```bash
go list -u -m -json all | docker run --rm -i psampaz/go-mod-outdated:v0.9.0
```

Using a specific tag ensures reproducible behavior across CI runs.

---

## 14. Detailed Examples

### 14.1 Example: Basic Usage

Input (`go list -u -m -json all` output):

```json
{
    "Path": "github.com/myorg/myproject",
    "Main": true,
    "GoVersion": "1.21"
}
{
    "Path": "github.com/gin-gonic/gin",
    "Version": "v1.9.0",
    "Time": "2023-02-21T13:29:08Z",
    "Update": {
        "Path": "github.com/gin-gonic/gin",
        "Version": "v1.9.1",
        "Time": "2023-06-09T07:51:40Z"
    }
}
{
    "Path": "github.com/stretchr/testify",
    "Version": "v1.8.2",
    "Time": "2023-02-18T12:56:29Z",
    "Update": {
        "Path": "github.com/stretchr/testify",
        "Version": "v1.8.4",
        "Time": "2023-05-26T15:34:12Z"
    }
}
{
    "Path": "golang.org/x/text",
    "Version": "v0.9.0",
    "Time": "2023-04-13T18:38:40Z",
    "Indirect": true,
    "Update": {
        "Path": "golang.org/x/text",
        "Version": "v0.12.0",
        "Time": "2023-07-18T19:27:16Z"
    }
}
{
    "Path": "github.com/go-playground/validator/v10",
    "Version": "v10.14.0",
    "Time": "2023-05-16T20:00:00Z",
    "Indirect": true
}
```

Command:
```bash
go list -u -m -json all | go-mod-outdated
```

Output:
```
+-------------------------------------------+----------+-------------+--------+------------------+
|                  MODULE                   | VERSION  | NEW VERSION | DIRECT | VALID TIMESTAMPS |
+-------------------------------------------+----------+-------------+--------+------------------+
| github.com/gin-gonic/gin                  | v1.9.0   | v1.9.1      | true   | true             |
| github.com/stretchr/testify               | v1.8.2   | v1.8.4      | true   | true             |
| golang.org/x/text                         | v0.9.0   | v0.12.0     | false  | true             |
| github.com/go-playground/validator/v10    | v10.14.0 |             | false  | true             |
+-------------------------------------------+----------+-------------+--------+------------------+
```

### 14.2 Example: With -update Flag

Using the same input as above:

```bash
go list -u -m -json all | go-mod-outdated -update
```

Output:
```
+-------------------------------------------+----------+-------------+--------+------------------+
|                  MODULE                   | VERSION  | NEW VERSION | DIRECT | VALID TIMESTAMPS |
+-------------------------------------------+----------+-------------+--------+------------------+
| github.com/gin-gonic/gin                  | v1.9.0   | v1.9.1      | true   | true             |
| github.com/stretchr/testify               | v1.8.2   | v1.8.4      | true   | true             |
| golang.org/x/text                         | v0.9.0   | v0.12.0     | false  | true             |
+-------------------------------------------+----------+-------------+--------+------------------+
```

Note: `github.com/go-playground/validator/v10` is excluded because it has no update.

### 14.3 Example: With -direct Flag

```bash
go list -u -m -json all | go-mod-outdated -direct
```

Output:
```
+-------------------------------------------+----------+-------------+--------+------------------+
|                  MODULE                   | VERSION  | NEW VERSION | DIRECT | VALID TIMESTAMPS |
+-------------------------------------------+----------+-------------+--------+------------------+
| github.com/gin-gonic/gin                  | v1.9.0   | v1.9.1      | true   | true             |
| github.com/stretchr/testify               | v1.8.2   | v1.8.4      | true   | true             |
+-------------------------------------------+----------+-------------+--------+------------------+
```

Note: Both indirect dependencies (`golang.org/x/text` and `validator/v10`) are excluded.

### 14.4 Example: With -update -direct Flags

```bash
go list -u -m -json all | go-mod-outdated -update -direct
```

Output:
```
+-------------------------------------------+----------+-------------+--------+------------------+
|                  MODULE                   | VERSION  | NEW VERSION | DIRECT | VALID TIMESTAMPS |
+-------------------------------------------+----------+-------------+--------+------------------+
| github.com/gin-gonic/gin                  | v1.9.0   | v1.9.1      | true   | true             |
| github.com/stretchr/testify               | v1.8.2   | v1.8.4      | true   | true             |
+-------------------------------------------+----------+-------------+--------+------------------+
```

In this case, the output is the same as `-direct` alone because both direct dependencies happen to have updates.

### 14.5 Example: Markdown Style

```bash
go list -u -m -json all | go-mod-outdated -style markdown
```

Output:
```
|                  MODULE                   | VERSION  | NEW VERSION | DIRECT | VALID TIMESTAMPS |
|-------------------------------------------|----------|-------------|--------|------------------|
| github.com/gin-gonic/gin                  | v1.9.0   | v1.9.1      | true   | true             |
| github.com/stretchr/testify               | v1.8.2   | v1.8.4      | true   | true             |
| golang.org/x/text                         | v0.9.0   | v0.12.0     | false  | true             |
| github.com/go-playground/validator/v10    | v10.14.0 |             | false  | true             |
```

### 14.6 Example: CI Mode (Outdated Dependencies Present)

```bash
go list -u -m -json all | go-mod-outdated -update -direct -ci
echo $?
```

Output:
```
+-------------------------------------------+----------+-------------+--------+------------------+
|                  MODULE                   | VERSION  | NEW VERSION | DIRECT | VALID TIMESTAMPS |
+-------------------------------------------+----------+-------------+--------+------------------+
| github.com/gin-gonic/gin                  | v1.9.0   | v1.9.1      | true   | true             |
| github.com/stretchr/testify               | v1.8.2   | v1.8.4      | true   | true             |
+-------------------------------------------+----------+-------------+--------+------------------+
1
```

Exit code is 1 because outdated direct dependencies were found.

### 14.7 Example: CI Mode (No Outdated Dependencies)

If all dependencies were up to date:

```bash
go list -u -m -json all | go-mod-outdated -update -direct -ci
echo $?
```

Output:
```
0
```

No table is rendered (empty results), and exit code is 0.

### 14.8 Example: Replace Directive

Input:
```json
{
    "Path": "github.com/myorg/myproject",
    "Main": true
}
{
    "Path": "github.com/original/module",
    "Version": "v1.0.0",
    "Time": "2022-05-10T09:00:00Z",
    "Replace": {
        "Path": "github.com/myfork/module",
        "Version": "v1.0.1-patched",
        "Time": "2023-02-14T16:30:00Z",
        "Update": {
            "Path": "github.com/myfork/module",
            "Version": "v1.2.0-patched",
            "Time": "2023-08-01T10:00:00Z"
        }
    }
}
```

Command:
```bash
cat input.json | go-mod-outdated
```

Output:
```
+-------------------------------+-----------------+-----------------+--------+------------------+
|            MODULE             |     VERSION     |   NEW VERSION   | DIRECT | VALID TIMESTAMPS |
+-------------------------------+-----------------+-----------------+--------+------------------+
| github.com/original/module    | v1.0.1-patched  | v1.2.0-patched  | true   | true             |
+-------------------------------+-----------------+-----------------+--------+------------------+
```

Note:
- MODULE shows `github.com/original/module` (original path)
- VERSION shows `v1.0.1-patched` (from Replace)
- NEW VERSION shows `v1.2.0-patched` (from Replace.Update)

### 14.9 Example: Invalid Timestamps

Input:
```json
{
    "Path": "github.com/myorg/myproject",
    "Main": true
}
{
    "Path": "github.com/example/pseudo-version-dep",
    "Version": "v0.0.0-20230601120000-abcdef123456",
    "Time": "2023-06-01T12:00:00Z",
    "Update": {
        "Path": "github.com/example/pseudo-version-dep",
        "Version": "v1.0.0",
        "Time": "2023-03-15T00:00:00Z"
    }
}
```

Output:
```
+-------------------------------------------+----------------------------------------------+-------------+--------+------------------+
|                  MODULE                   |                   VERSION                    | NEW VERSION | DIRECT | VALID TIMESTAMPS |
+-------------------------------------------+----------------------------------------------+-------------+--------+------------------+
| github.com/example/pseudo-version-dep     | v0.0.0-20230601120000-abcdef123456           | v1.0.0      | true   | false            |
+-------------------------------------------+----------------------------------------------+-------------+--------+------------------+
```

VALID TIMESTAMPS is `false` because the current version's timestamp (2023-06-01) is after the update's timestamp (2023-03-15).

### 14.10 Example: Mixed Scenario

Input with a variety of dependency types:
```json
{
    "Path": "github.com/myorg/myproject",
    "Main": true,
    "GoVersion": "1.21"
}
{
    "Path": "github.com/direct/with-update",
    "Version": "v1.0.0",
    "Time": "2023-01-01T00:00:00Z",
    "Update": {
        "Path": "github.com/direct/with-update",
        "Version": "v2.0.0",
        "Time": "2023-12-01T00:00:00Z"
    }
}
{
    "Path": "github.com/direct/no-update",
    "Version": "v3.5.2",
    "Time": "2023-06-15T00:00:00Z"
}
{
    "Path": "github.com/indirect/with-update",
    "Version": "v0.1.0",
    "Time": "2022-01-01T00:00:00Z",
    "Indirect": true,
    "Update": {
        "Path": "github.com/indirect/with-update",
        "Version": "v0.3.0",
        "Time": "2023-10-01T00:00:00Z"
    }
}
{
    "Path": "github.com/indirect/no-update",
    "Version": "v1.1.1",
    "Time": "2023-03-20T00:00:00Z",
    "Indirect": true
}
{
    "Path": "github.com/replaced/module",
    "Version": "v1.0.0",
    "Time": "2022-05-01T00:00:00Z",
    "Replace": {
        "Path": "../local-replacement",
        "Version": "",
        "Time": "0001-01-01T00:00:00Z"
    }
}
```

No flags:
```
+---------------------------------+---------+-------------+--------+------------------+
|             MODULE              | VERSION | NEW VERSION | DIRECT | VALID TIMESTAMPS |
+---------------------------------+---------+-------------+--------+------------------+
| github.com/direct/with-update   | v1.0.0  | v2.0.0      | true   | true             |
| github.com/direct/no-update     | v3.5.2  |             | true   | true             |
| github.com/indirect/with-update | v0.1.0  | v0.3.0      | false  | true             |
| github.com/indirect/no-update   | v1.1.1  |             | false  | true             |
| github.com/replaced/module      |         |             | true   | true             |
+---------------------------------+---------+-------------+--------+------------------+
```

With `-update`:
```
+---------------------------------+---------+-------------+--------+------------------+
|             MODULE              | VERSION | NEW VERSION | DIRECT | VALID TIMESTAMPS |
+---------------------------------+---------+-------------+--------+------------------+
| github.com/direct/with-update   | v1.0.0  | v2.0.0      | true   | true             |
| github.com/indirect/with-update | v0.1.0  | v0.3.0      | false  | true             |
+---------------------------------+---------+-------------+--------+------------------+
```

With `-direct`:
```
+---------------------------------+---------+-------------+--------+------------------+
|             MODULE              | VERSION | NEW VERSION | DIRECT | VALID TIMESTAMPS |
+---------------------------------+---------+-------------+--------+------------------+
| github.com/direct/with-update   | v1.0.0  | v2.0.0      | true   | true             |
| github.com/direct/no-update     | v3.5.2  |             | true   | true             |
| github.com/replaced/module      |         |             | true   | true             |
+---------------------------------+---------+-------------+--------+------------------+
```

With `-update -direct`:
```
+---------------------------------+---------+-------------+--------+------------------+
|             MODULE              | VERSION | NEW VERSION | DIRECT | VALID TIMESTAMPS |
+---------------------------------+---------+-------------+--------+------------------+
| github.com/direct/with-update   | v1.0.0  | v2.0.0      | true   | true             |
+---------------------------------+---------+-------------+--------+------------------+
```

---

## 15. Integration Patterns

### 15.1 Shell Script Wrapper

A common pattern is to wrap go-mod-outdated in a shell script that provides additional functionality:

```bash
#!/bin/bash

echo "=== Outdated Direct Dependencies ==="
go list -u -m -json all | go-mod-outdated -update -direct

echo ""
echo "=== All Outdated Dependencies ==="
go list -u -m -json all | go-mod-outdated -update

echo ""
echo "=== Full Dependency Report ==="
go list -u -m -json all | go-mod-outdated
```

### 15.2 Markdown Report Generation

Generate a Markdown report suitable for inclusion in a pull request or issue:

```bash
echo "# Dependency Report"
echo ""
echo "## Outdated Direct Dependencies"
echo ""
go list -u -m -json all | go-mod-outdated -update -direct -style markdown
echo ""
echo "## All Dependencies"
echo ""
go list -u -m -json all | go-mod-outdated -style markdown
```

### 15.3 Combining with jq

You can preprocess the `go list` output with `jq` before piping to go-mod-outdated. However, note that `jq` must preserve the concatenated JSON stream format:

```bash
# Filter to only modules from a specific organization before formatting
go list -u -m -json all | jq -c 'select(.Path | startswith("github.com/myorg/"))' | go-mod-outdated
```

### 15.4 Caching go list Output

Since `go list -u` involves network requests and can be slow, caching the output can be useful during development:

```bash
# Cache the output
go list -u -m -json all > /tmp/modules.json

# View in different ways without re-running go list
cat /tmp/modules.json | go-mod-outdated
cat /tmp/modules.json | go-mod-outdated -update -direct
cat /tmp/modules.json | go-mod-outdated -style markdown
```

### 15.5 Pre-commit Hook

Use go-mod-outdated as a pre-commit hook to warn about outdated dependencies:

```bash
#!/bin/bash
# .git/hooks/pre-commit

if go list -u -m -json all | go-mod-outdated -update -direct -ci 2>/dev/null; then
    echo "All direct dependencies are up to date."
else
    echo "WARNING: Outdated direct dependencies detected."
    go list -u -m -json all | go-mod-outdated -update -direct
    echo ""
    echo "Consider updating before committing."
    # Don't block the commit, just warn
fi
```

### 15.6 Makefile Integration

```makefile
.PHONY: deps deps-check

deps:
	go list -u -m -json all | go-mod-outdated -update

deps-check:
	go list -u -m -json all | go-mod-outdated -update -direct -ci
```

### 15.7 Periodic Dependency Monitoring

Use cron or CI scheduled pipelines to periodically check for outdated dependencies:

```yaml
# GitHub Actions scheduled workflow
name: Dependency Check
on:
  schedule:
    - cron: '0 9 * * 1'  # Every Monday at 9 AM

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with:
          go-version: '1.21'
      - name: Check dependencies
        run: |
          echo "## Outdated Dependencies Report" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          go list -u -m -json all | go-mod-outdated -update -style markdown >> $GITHUB_STEP_SUMMARY
```

### 15.8 Multi-module Repository

For repositories with multiple Go modules (monorepos), run go-mod-outdated in each module directory:

```bash
#!/bin/bash
for dir in $(find . -name "go.mod" -exec dirname {} \;); do
    echo "=== Module: $dir ==="
    (cd "$dir" && go list -u -m -json all | go-mod-outdated -update)
    echo ""
done
```

---

## 16. Comparison with Alternative Tools

### 16.1 go list -u -m all (Plain Text)

Without the `-json` flag, `go list -u -m all` produces plain-text output where updates are shown in brackets:

```
github.com/example/foo v1.0.0 [v1.2.0]
github.com/example/bar v0.5.0
```

go-mod-outdated improves on this by:
- Providing a structured table format
- Adding the DIRECT column
- Adding timestamp validation
- Offering filtering capabilities (`-update`, `-direct`)
- Providing CI exit code support
- Supporting Markdown output

### 16.2 go-mod-outdated vs. Manual jq Processing

You could achieve similar results using `jq` to process the JSON:

```bash
go list -u -m -json all | jq -r 'select(.Main != true) | [.Path, .Version, (.Update.Version // "")] | @tsv'
```

However, this approach:
- Does not handle replace directives transparently
- Does not provide formatted table output
- Does not include timestamp validation
- Requires `jq` knowledge and a separate `jq` installation
- Does not provide CI exit code support

### 16.3 Advantages of the Pipeline Approach

By delegating version resolution to `go list`, go-mod-outdated avoids:
- Implementing registry querying logic
- Handling authentication for private modules
- Managing proxy configurations
- Parsing `go.mod` and `go.sum` files directly
- Implementing the Go module version resolution algorithm

This makes go-mod-outdated simpler, more maintainable, and less likely to produce results inconsistent with the Go toolchain.

---

## 17. The tablewriter Library

### 17.1 Overview

go-mod-outdated uses the `github.com/olekukonenko/tablewriter` library (v0.0.5) for rendering tables. This library provides configurable ASCII table rendering with support for borders, alignment, column width, and various formatting options.

### 17.2 Default Configuration

For the default style, go-mod-outdated uses tablewriter's default settings, which produce:

- Box borders (`+`, `-`, `|`)
- Auto-adjusted column widths based on content
- Center-aligned header row
- Left-aligned data rows
- Header separator between header and data

### 17.3 Markdown Configuration

For the markdown style, go-mod-outdated configures tablewriter with the following changes from defaults:

- **Borders**: Top and bottom borders are disabled (`.SetBorders(tablewriter.Border{Left: true, Top: false, Right: true, Bottom: false})`)
- **Center Separator**: Set to `|` instead of `+` (`.SetCenterSeparator("|")`)

These two changes transform the ASCII table into a valid Markdown table.

### 17.4 Dependencies

The tablewriter library has one transitive dependency:

- `github.com/mattn/go-runewidth`: Provides Unicode-aware string width calculation. This ensures that table columns align correctly even when module paths or version strings contain non-ASCII characters (though this is rare in practice).

---

## 18. Version History

### 18.1 v0.1.0 -- Initial Release

The initial release introduced the core functionality:
- Reading `go list -u -m -json all` output from stdin
- Rendering a table with MODULE, VERSION, NEW VERSION, DIRECT columns
- Basic replace directive handling

### 18.2 v0.2.0 -- Timestamp Validation

Added the VALID TIMESTAMPS column (the fifth column) to detect chronologically inconsistent version timestamps. This was particularly useful for identifying pseudo-version anomalies.

### 18.3 v0.3.0 -- CI Mode and macOS

- Added the `-ci` flag for CI pipeline integration
- Added macOS support in the build/release process

### 18.4 v0.4.0 -- Docker Support

- Published official Docker image at `psampaz/go-mod-outdated`
- Added Docker usage documentation

### 18.5 v0.5.0 -- Go 1.13 Support

- Updated for compatibility with Go 1.13's module changes
- Support for the new module proxy and checksum database defaults

### 18.6 v0.6.0 -- Markdown Style

- Added the `-style` flag
- Introduced `markdown` style for Markdown-compatible table output

### 18.7 v0.7.0 -- Go 1.15 Support

- Updated for compatibility with Go 1.15

### 18.8 v0.8.0 -- Go 1.16 Support

- Updated for compatibility with Go 1.16's default module mode

### 18.9 v0.9.0 -- Empty Table Suppression

- Changed behavior to skip rendering when the filtered result set is empty
- Previously, an empty table (header only) would be rendered
- Updated for compatibility with Go 1.19 and Go 1.20

---

## 19. Edge Cases and Corner Scenarios

### 19.1 Module with Only Main Entry

If `go list` produces only the main module (e.g., a project with no dependencies):

```json
{
    "Path": "github.com/myorg/myproject",
    "Main": true
}
```

go-mod-outdated filters out the main module, resulting in an empty list. No table is rendered (v0.9.0+ behavior). Exit code is 0.

### 19.2 All Dependencies Up to Date

When no dependencies have updates (all `Update` fields are nil):

- Default: Full table is rendered with empty NEW VERSION columns
- `-update`: Empty result, no table rendered
- `-ci`: Exit code 0 (no outdated dependencies)
- `-update -ci`: Exit code 0 (no modules pass the filter)

### 19.3 Single Dependency

```json
{
    "Path": "github.com/myorg/myproject",
    "Main": true
}
{
    "Path": "github.com/only/dependency",
    "Version": "v1.0.0"
}
```

A single-row table is rendered. The tool handles this without issue.

### 19.4 Very Long Module Paths

Module paths can be arbitrarily long (e.g., `github.com/organization/repository/submodule/deeply/nested/path/v2`). The tablewriter library auto-adjusts column widths to accommodate long strings, which may produce wide tables that wrap in narrow terminals. There is no truncation or abbreviation.

### 19.5 Pre-release Versions

Pre-release version strings like `v1.0.0-beta.1`, `v2.0.0-rc.1`, or `v0.0.0-alpha` are treated as regular version strings. They are displayed verbatim in the VERSION and NEW VERSION columns.

### 19.6 v0 and v1 Major Versions

Modules at major version v0 or v1 do not include the major version in their path (e.g., `github.com/example/module` at `v1.2.3`). Modules at v2 or higher include it (e.g., `github.com/example/module/v2` at `v2.3.0`). go-mod-outdated does not perform any version-path validation; it displays whatever is in the JSON.

### 19.7 Retracted Versions

Go 1.16+ supports version retraction via `retract` directives in `go.mod`. Retracted versions are not recommended by `go list -u` as updates. go-mod-outdated does not handle retraction directly; it relies on `go list` to exclude retracted versions from the `Update` field.

### 19.8 Deprecated Modules

Go 1.17+ supports module deprecation. Deprecated modules may still appear in go-mod-outdated output. The deprecation notice is in the `Deprecated` field of the module struct, which go-mod-outdated does not currently display.

### 19.9 Modules with Errors

When `go list` encounters an error resolving a module, it includes an `Error` field:

```json
{
    "Path": "github.com/deleted/module",
    "Version": "v1.0.0",
    "Error": {
        "Err": "module lookup disabled by GOPROXY=off"
    }
}
```

go-mod-outdated includes such modules in the output without any special handling. The error message is not displayed in the table. The module will have whatever version information was available despite the error.

### 19.10 Duplicate Module Paths

In normal `go list` output, each module path appears at most once. However, if synthetic input contains duplicate paths, go-mod-outdated processes each occurrence independently. Both entries appear in the output table. There is no deduplication.

### 19.11 Replace with Version Mismatch

When a replace directive specifies a version that does not exist or differs from the original:

```
replace github.com/original v1.0.0 => github.com/fork v999.0.0
```

go-mod-outdated displays whatever version string `go list` provides. It does not validate version string formats or existence.

### 19.12 Unicode in Module Paths

While uncommon, Go module paths can theoretically contain Unicode characters (though the Go module path specification restricts valid characters). The tablewriter library, through its go-runewidth dependency, handles Unicode width calculation for proper column alignment.

### 19.13 Large Dependency Graphs

go-mod-outdated processes modules sequentially from the JSON stream. Memory usage is proportional to the number of modules (it collects all modules into a slice before rendering). For projects with thousands of dependencies, this should not pose a problem on modern systems.

### 19.14 Concurrent go list Invocations

go-mod-outdated reads from stdin, so only one instance processes a given `go list` output at a time. However, you can run multiple instances in parallel on different module directories:

```bash
(cd module-a && go list -u -m -json all | go-mod-outdated) &
(cd module-b && go list -u -m -json all | go-mod-outdated) &
wait
```

### 19.15 Empty Version Strings

If a module has an empty `Version` field (which can happen for replaced modules or in unusual configurations), the VERSION column shows an empty cell. This is handled by tablewriter as a zero-width cell.

---

## 20. Troubleshooting

### 20.1 No Output

**Symptom**: go-mod-outdated produces no output at all.

**Possible causes**:
1. All modules were filtered out by `-update` and/or `-direct` flags
2. The only module in the input is the main module
3. The input is empty
4. The JSON input is malformed (check stderr for error messages)

**Resolution**: Run without flags to see all dependencies, then add flags incrementally.

### 20.2 "flag provided but not defined" Error

**Symptom**: Error message like `flag provided but not defined: -foo`

**Cause**: An unrecognized flag was provided. Remember that go-mod-outdated uses single-dash flags (Go standard `flag` package). Double-dash flags like `--update` are not supported.

**Resolution**: Use single-dash syntax: `-update`, `-direct`, `-ci`, `-style`.

### 20.3 Exit Code 2

**Symptom**: The tool exits with code 2.

**Cause**: This is the standard exit code from Go's `flag` package when an invalid flag is provided or `-help` is requested.

**Resolution**: Check your flag syntax. Use `-h` for help.

### 20.4 "go list -m: can't determine available upgrades using the vendor directory"

**Symptom**: `go list` fails when vendoring is enabled.

**Cause**: Go 1.14+ defaults to vendor mode when a `vendor` directory exists.

**Resolution**: Use `-mod=mod`:
```bash
go list -u -m -mod=mod -json all | go-mod-outdated
```

### 20.5 Incorrect VALID TIMESTAMPS

**Symptom**: A module shows VALID TIMESTAMPS as `false` but the update seems legitimate.

**Cause**: The update's commit timestamp is older than the current version's commit timestamp, even though the update has a higher version number. This is common with pseudo-versions.

**Resolution**: This is informational only. Investigate the specific module to understand why timestamps are inconsistent.

### 20.6 Table Formatting Issues in Narrow Terminals

**Symptom**: The table wraps awkwardly in narrow terminal windows.

**Cause**: Long module paths and version strings produce wide tables that exceed the terminal width.

**Resolution**: Use `-style markdown` for output that can be viewed in a text editor or Markdown renderer. Alternatively, use `-update` or `-direct` to reduce the number of rows, which may help if the width issue is caused by one particularly long module path.

### 20.7 Missing Update Information

**Symptom**: The NEW VERSION column is empty for all modules.

**Cause**: The `go list` command was invoked without the `-u` flag, so no update information was populated.

**Resolution**: Ensure you use `go list -u -m -json all` (with `-u`).

### 20.8 Private Modules Not Showing Updates

**Symptom**: Private/internal modules show no updates even though newer versions exist.

**Cause**: `go list -u` cannot query the module proxy for private modules.

**Resolution**: Configure `GOPRIVATE`, `GONOSUMDB`, and potentially a private module proxy. This is a `go list` configuration issue, not a go-mod-outdated issue.

---

## 21. Internal Architecture

### 21.1 Processing Pipeline

go-mod-outdated follows a linear processing pipeline:

1. **Parse flags**: Using Go's standard `flag` package
2. **Read and decode JSON**: Using `json.Decoder` to read modules from stdin one at a time
3. **Collect modules**: All modules are collected into a slice
4. **Filter**: Remove main module, apply `-update` and `-direct` filters
5. **Check for output**: If the filtered list is empty, skip rendering (v0.9.0+)
6. **Render table**: Using tablewriter with appropriate style configuration
7. **CI exit code**: If `-ci` is set, check filtered list for outdated modules and set exit code

### 21.2 Data Flow

```
stdin (JSON stream)
    |
    v
json.Decoder -> []Module (all modules)
    |
    v
Filter: Remove Main == true
    |
    v
Filter: If -direct, remove Indirect == true
    |
    v
Filter: If -update, remove HasUpdate() == false
    |
    v
If empty: exit (no output)
    |
    v
For each module: extract [Path, CurrentVersion(), NewVersion(), !Indirect, !InvalidTimestamp()]
    |
    v
tablewriter.Render() -> stdout
    |
    v
If -ci and any HasUpdate(): os.Exit(1)
```

### 21.3 Module Methods

The Module struct (or its equivalent) provides several accessor methods that encapsulate the replace directive logic:

- `CurrentVersion() string`: Returns the currently-used version, respecting replace directives
- `NewVersion() string`: Returns the available update version, respecting replace directives
- `HasUpdate() bool`: Returns whether an update is available, respecting replace directives
- `InvalidTimestamp() bool`: Returns whether the timestamps are inconsistent, respecting replace directives

These methods centralize the replace logic so that the rendering code does not need to be aware of replace directives.

---

## 22. Frequently Asked Questions

### 22.1 Can go-mod-outdated update my dependencies?

No. go-mod-outdated is purely a display/reporting tool. To update dependencies, use `go get -u` or edit your `go.mod` file directly.

### 22.2 Does go-mod-outdated need network access?

No. go-mod-outdated reads from stdin and writes to stdout. It does not make any network requests. Network access is needed by `go list -u`, which runs as the first stage of the pipeline.

### 22.3 Can I use go-mod-outdated without Go installed?

You can use the go-mod-outdated binary or Docker image without a Go installation, but you need some way to produce the JSON input. Without Go, you would need to obtain the `go list` output from another source (e.g., a cached file or a CI artifact).

### 22.4 Does go-mod-outdated support Go workspaces?

go-mod-outdated processes whatever JSON is piped to it. If `go list` is invoked in a workspace context (Go 1.18+), its output reflects the workspace's dependency graph. go-mod-outdated formats this output without any workspace-specific logic.

### 22.5 How does go-mod-outdated handle +incompatible versions?

Versions with the `+incompatible` suffix (e.g., `v3.0.0+incompatible`) are treated as regular version strings. The suffix is displayed verbatim in the VERSION and NEW VERSION columns.

### 22.6 Can I filter by specific module paths?

go-mod-outdated does not support filtering by module path. To achieve this, preprocess the JSON with `jq`:

```bash
go list -u -m -json all | jq -c 'select(.Path | startswith("github.com/myorg/"))' | go-mod-outdated
```

### 22.7 Why is the table empty when I use -update -direct?

This means none of your direct dependencies have available updates. All your direct dependencies are at their latest versions.

### 22.8 Does go-mod-outdated respect GOFLAGS?

go-mod-outdated does not read `GOFLAGS`. That environment variable affects `go` commands, not go-mod-outdated. However, `GOFLAGS` may affect the output of `go list -u` in the pipeline.

---

## 23. Summary of Behavior Reference

### 23.1 Column Derivation

| Column | Source Expression |
|--------|-------------------|
| MODULE | `module.Path` |
| VERSION | `module.Replace.Version` if `module.Replace != nil`, else `module.Version` |
| NEW VERSION | `module.Replace.Update.Version` if `module.Replace != nil` and `module.Replace.Update != nil`, else `module.Update.Version` if `module.Update != nil`, else `""` |
| DIRECT | `"true"` if `!module.Indirect`, else `"false"` |
| VALID TIMESTAMPS | `"false"` if current time is after update time, else `"true"` |

### 23.2 Filter Application Order

1. Exclude modules where `Main == true` (always applied)
2. If `-direct`: exclude modules where `Indirect == true`
3. If `-update`: exclude modules where `HasUpdate() == false`

### 23.3 Exit Code Decision Tree

```
if unknown flag:
    exit 2

parse JSON from stdin
apply filters

if -ci flag is set:
    if any module in filtered list has HasUpdate() == true:
        render table
        exit 1
    else:
        render table (if non-empty)
        exit 0
else:
    render table (if non-empty)
    exit 0
```

### 23.4 Output Style Decision

```
if -style == "markdown":
    configure tablewriter:
        borders: left=true, top=false, right=true, bottom=false
        center separator: "|"
else:
    use tablewriter defaults:
        borders: all enabled
        center separator: "+"
```

