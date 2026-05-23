# htmlq -- Like jq, but for HTML

## Overview

htmlq is a command-line tool for extracting content from HTML using CSS selectors. It occupies the same conceptual niche as jq does for JSON: it reads structured data from standard input (or a file), applies a query expression, and writes the matching results to standard output. Where jq uses its own filter language to traverse JSON trees, htmlq uses CSS selectors -- the same query syntax used in web browsers and front-end JavaScript -- to locate elements within an HTML document.

htmlq is written in Rust. Internally, it uses the **kuchiki** HTML DOM library for tree manipulation and CSS selector matching, which itself is built on top of **html5ever**, the HTML5-compliant parser originally developed for Mozilla's Servo browser engine. This means htmlq benefits from a production-grade, specification-compliant HTML parser that handles malformed and incomplete HTML gracefully, exactly the way a modern web browser would.

The tool is designed to fit naturally into Unix pipelines. HTML is piped in through stdin (or read from a file with the `-f` flag), CSS selectors are provided as positional arguments, and matching content is written to stdout. The output can be the raw outer HTML of matched elements, just the text content (stripping all tags), or the value of a specific attribute. This makes htmlq ideal for web scraping workflows, data extraction pipelines, and any situation where you need to pull structured information out of HTML documents from the command line.

### Key Design Principles

- **Stdin/stdout pipeline integration**: htmlq reads from stdin and writes to stdout by default, making it composable with curl, wget, cat, and other Unix tools.
- **CSS selector familiarity**: Anyone who has written CSS or used `document.querySelector()` in JavaScript already knows the query language.
- **Lenient parsing**: Built on html5ever, htmlq handles real-world HTML -- including malformed, incomplete, or quirky markup -- without crashing or producing errors.
- **Single-purpose tool**: htmlq does one thing well. It selects elements from HTML. It does not fetch URLs, render pages, or execute JavaScript.

### Typical Workflow

A typical htmlq invocation looks like this:

```bash
curl -s https://example.com | htmlq 'h1'
```

This fetches a web page with curl, pipes the HTML into htmlq, and extracts all `<h1>` elements. The output is the full outer HTML of each matching element.

For more targeted extraction:

```bash
curl -s https://example.com | htmlq -a href 'a'
```

This extracts the `href` attribute from every `<a>` tag, producing one URL per line.

---

## Installation

htmlq is distributed as a Rust crate and can be installed via Cargo:

```bash
cargo install htmlq
```

This compiles the binary from source and places it in `~/.cargo/bin/`, which should be in your `$PATH` if Rust is installed via rustup.

Pre-built binaries may also be available from the project's GitHub releases page for common platforms (Linux x86_64, macOS).

### System Requirements

- A Rust toolchain (stable) for building from source
- No runtime dependencies beyond libc

---

## Arguments

### `<SELECTOR>...`

One or more CSS selectors to match against the parsed HTML document. Each selector is a separate positional argument. When multiple selectors are provided, htmlq processes each one independently against the same document and concatenates the results in document order.

Selectors follow the CSS selector specification as implemented by the kuchiki/selectors crate (derived from Servo's selector engine). This includes element selectors, class selectors, ID selectors, attribute selectors, combinators, and many pseudo-classes.

If a selector contains characters that are special to the shell (such as `>`, `+`, `~`, `*`, `#`, or parentheses), it must be quoted:

```bash
htmlq 'div > p.intro' < page.html
htmlq 'a[href^="https"]' < page.html
htmlq '#main-content' < page.html
```

Single quotes are recommended to prevent shell expansion, though double quotes also work as long as dollar signs and backticks are escaped.

---

## Options

### `-a, --attribute <ATTR>`

Extract the value of the named attribute from each matched element, instead of outputting the element's HTML.

When this flag is specified, htmlq iterates over every element that matches the given selector(s) and, for each element, looks up the attribute named `<ATTR>`. If the attribute exists on the element, its value is printed on its own line. If the attribute does not exist on a particular element, that element is silently skipped (no output is produced for it, and no error is raised).

This is one of the most commonly used flags, especially for extracting URLs:

```bash
# Extract all link URLs from a page
curl -s https://example.com | htmlq -a href 'a'

# Extract all image source URLs
curl -s https://example.com | htmlq -a src 'img'

# Extract the content of meta description tags
curl -s https://example.com | htmlq -a content 'meta[name="description"]'

# Extract data attributes
cat page.html | htmlq -a data-id 'div.item'

# Extract class attribute values
cat page.html | htmlq -a class 'div'
```

The output is one attribute value per line, with no additional formatting or quoting. If an attribute value contains newlines (which is rare but technically valid in HTML), they are preserved in the output.

When used with the `-b` (base URL) flag on `href` or `src` attributes, relative URLs are resolved to absolute URLs before being printed.

**Interaction with other flags:**
- `-a` and `-t` (text mode) are mutually exclusive in practice. If both are specified, `-a` takes precedence: attribute values are extracted rather than text content.
- `-a` combined with `-p` (pretty-print) has no additional effect, since attribute values are plain strings without HTML structure to format.

### `-t, --text`

Extract only the text content of matched elements, stripping all HTML tags.

When this flag is set, instead of outputting the outer HTML of matched elements, htmlq walks the subtree of each matched element, collects all text nodes, and concatenates them. The result is the "visible text" of the element, as a human would see it rendered in a browser (minus any CSS-driven formatting, of course).

```bash
# Extract just the text from paragraphs
echo '<p>Hello <strong>world</strong></p>' | htmlq -t 'p'
# Output: Hello world

# Extract text from a complex element
echo '<div><h1>Title</h1><p>Body text</p></div>' | htmlq -t 'div'
# Output: TitleBody text

# Extract link text (not the URL)
echo '<a href="/about">About Us</a>' | htmlq -t 'a'
# Output: About Us
```

Text extraction concatenates all descendant text nodes directly, without inserting spaces or newlines between them. This means that text from adjacent inline elements runs together. For example, `<span>foo</span><span>bar</span>` produces `foobar`, not `foo bar`. Block-level elements similarly do not automatically produce line breaks in the output.

This flag is particularly useful in combination with `-r` (remove nodes) for cleaning up content before text extraction:

```bash
# Extract body text without script content
cat page.html | htmlq -r 'script' -r 'style' -t 'body'
```

### `-b, --base <URL>`

Set a base URL for resolving relative links and resource references.

Many HTML documents contain relative URLs in their `href` and `src` attributes -- paths like `/about`, `../images/logo.png`, or `#section-2`. When you extract these attribute values with `-a`, they are often not useful on their own without knowing the original page's URL.

The `-b` flag tells htmlq to resolve relative URLs against the provided base URL before outputting them. This makes the output immediately usable for further processing, downloading, or crawling.

```bash
# Without -b: relative URLs are output as-is
echo '<a href="/about">About</a>' | htmlq -a href 'a'
# Output: /about

# With -b: relative URLs are resolved
echo '<a href="/about">About</a>' | htmlq -b 'https://example.com' -a href 'a'
# Output: https://example.com/about

# Path resolution handles directory traversal
echo '<a href="../page">Link</a>' | htmlq -b 'https://example.com/dir/sub/' -a href 'a'
# Output: https://example.com/dir/page

# Fragment-only URLs
echo '<a href="#top">Top</a>' | htmlq -b 'https://example.com/page' -a href 'a'
# Output: https://example.com/page#top

# Already-absolute URLs are not modified
echo '<a href="https://other.com/page">Link</a>' | htmlq -b 'https://example.com' -a href 'a'
# Output: https://other.com/page
```

The base URL resolution follows the standard URL resolution algorithm (RFC 3986). The base URL should be a fully qualified URL including the scheme (e.g., `https://`).

**When `-b` takes effect:**
- `-b` only affects output when used together with `-a href` or similar attribute extraction. It does not rewrite URLs within the HTML output in default or pretty-print modes.
- The resolution applies to the attribute value being extracted, not to the document's internal link structure.

### `-p, --pretty`

Pretty-print the HTML output with indentation for improved readability.

By default, htmlq outputs the outer HTML of matched elements exactly as they exist in the parsed document tree (after html5ever's parsing and normalization). This means the output may be on a single line with no indentation, which can be difficult to read for complex nested elements.

The `-p` flag enables an indented output format where nested elements are indented to show the document structure clearly:

```bash
# Without -p
echo '<div><p>Hello</p><ul><li>One</li><li>Two</li></ul></div>' | htmlq 'div'
# Output: <div><p>Hello</p><ul><li>One</li><li>Two</li></ul></div>

# With -p
echo '<div><p>Hello</p><ul><li>One</li><li>Two</li></ul></div>' | htmlq -p 'div'
# Output:
# <div>
#   <p>
#     Hello
#   </p>
#   <ul>
#     <li>
#       One
#     </li>
#     <li>
#       Two
#     </li>
#   </ul>
# </div>
```

Pretty-printing is useful when you want to inspect the structure of matched elements, debug selectors, or produce human-readable output for reports.

**Interaction with other flags:**
- `-p` combined with `-t` (text mode) has no additional effect, since text output contains no HTML structure to format.
- `-p` combined with `-a` (attribute mode) has no additional effect for the same reason.
- `-p` is most useful in the default HTML output mode.

### `-r, --remove-nodes <SELECTOR>`

Remove elements matching the given CSS selector from the document before applying the main selector(s).

This is a preprocessing step. Before htmlq evaluates your main selector(s) to find matching elements, it first removes all elements matching the removal selector from the DOM tree. The removed elements and all their descendants are deleted entirely.

This flag can be specified multiple times to remove multiple types of elements:

```bash
# Remove script and style tags before extracting content
cat page.html | htmlq -r 'script' -r 'style' 'article'

# Remove navigation before extracting text
cat page.html | htmlq -r 'nav' -r 'footer' -t 'body'

# Remove ads and sidebars
cat page.html | htmlq -r '.ad-banner' -r '#sidebar' '.main-content'

# Remove all images before extracting HTML
cat page.html | htmlq -r 'img' 'div.content'
```

The removal selector supports the same CSS selector syntax as the main selector. You can use element selectors, class selectors, ID selectors, attribute selectors, and combinators.

**Order of operations:**
1. HTML is parsed into a DOM tree.
2. Elements matching each `-r` selector are removed from the tree.
3. The main selector(s) are evaluated against the modified tree.
4. Results are output according to the selected output mode.

This means that removal affects what the main selector can see. If the main selector would have matched an element inside a removed subtree, that element will not appear in the output.

### `-f, --filename <FILE>`

Read HTML from the specified file instead of from standard input.

```bash
# Read from a file
htmlq -f page.html 'h1'

# Equivalent to
htmlq 'h1' < page.html

# Also equivalent to
cat page.html | htmlq 'h1'
```

The file path can be absolute or relative to the current working directory. If the file does not exist or cannot be read, htmlq exits with a non-zero exit code and prints an error message to stderr.

This flag is provided as a convenience. There is no behavioral difference between reading from a file with `-f` and piping the same file's contents through stdin.

### `-w, --output-type <TYPE>`

An output type control flag. This flag controls the output format used by htmlq.

---

## CSS Selector Support

htmlq uses CSS selectors as implemented by the Servo project's `selectors` crate, which is the same selector engine used in the Firefox web browser (via Servo). This implementation supports a comprehensive subset of the CSS Selectors specification (primarily CSS Selectors Level 3, with some Level 4 features).

This section provides a thorough reference of the supported selector syntax with examples.

### Simple Selectors

#### Type (Element) Selectors

Match elements by their tag name. Tag names are case-insensitive in HTML.

```bash
# Match all paragraph elements
htmlq 'p' < page.html

# Match all div elements
htmlq 'div' < page.html

# Match all anchor elements
htmlq 'a' < page.html

# Match all list item elements
htmlq 'li' < page.html

# Match all table row elements
htmlq 'tr' < page.html

# Match all heading level 1 elements
htmlq 'h1' < page.html

# Match all input elements
htmlq 'input' < page.html

# Match all span elements
htmlq 'span' < page.html
```

Type selectors match every element of the given type in the document, regardless of where it appears in the tree.

#### Universal Selector

The `*` selector matches every element in the document.

```bash
# Match all elements (rarely useful on its own)
htmlq '*' < page.html

# More useful in combination: all direct children of .container
htmlq '.container > *' < page.html

# All elements inside a specific element
htmlq '#content *' < page.html
```

The universal selector is most useful in combination with combinators to express "any element in this position."

#### Class Selectors

Match elements that have a specific class in their `class` attribute. The class selector is prefixed with a dot (`.`).

```bash
# Match elements with class "highlight"
htmlq '.highlight' < page.html

# Match elements with class "nav-item"
htmlq '.nav-item' < page.html

# Match elements with multiple classes (must have both)
htmlq '.card.featured' < page.html

# Combine with element selector: only div elements with class "container"
htmlq 'div.container' < page.html

# Class selector with hyphenated names
htmlq '.my-component' < page.html

# Class selector with underscore names
htmlq '.my_component' < page.html
```

When multiple class selectors are chained without whitespace (e.g., `.card.featured`), the element must have all specified classes to match. The order of classes in the HTML `class` attribute does not matter.

An element's `class` attribute is a space-separated list of class names. The class selector `.foo` matches any element whose class list includes `foo`, regardless of what other classes are present.

#### ID Selectors

Match the element with a specific `id` attribute value. The ID selector is prefixed with a hash (`#`).

```bash
# Match the element with id "header"
htmlq '#header' < page.html

# Match the element with id "main-content"
htmlq '#main-content' < page.html

# Combine with element selector
htmlq 'div#sidebar' < page.html
```

In valid HTML, each `id` value should be unique within a document, so an ID selector should match at most one element. However, if the document contains duplicate IDs (which is invalid but common in the wild), htmlq will match all elements with that ID.

#### Attribute Selectors

Attribute selectors match elements based on the presence or value of their attributes. They are enclosed in square brackets.

##### Presence: `[attr]`

Matches elements that have the specified attribute, regardless of its value.

```bash
# Match all elements with an href attribute
htmlq '[href]' < page.html

# Match all elements with a data-id attribute
htmlq '[data-id]' < page.html

# Match all elements with a class attribute (any class)
htmlq '[class]' < page.html

# Match all elements with a disabled attribute
htmlq '[disabled]' < page.html

# Match all elements with a required attribute
htmlq '[required]' < page.html
```

##### Exact match: `[attr="value"]`

Matches elements where the attribute value is exactly equal to the given string.

```bash
# Match links pointing to a specific URL
htmlq '[href="https://example.com"]' < page.html

# Match inputs with a specific type
htmlq 'input[type="text"]' < page.html

# Match elements with a specific data attribute value
htmlq '[data-status="active"]' < page.html

# Match elements with specific role
htmlq '[role="navigation"]' < page.html
```

The value comparison is case-sensitive by default for most attributes. Attribute values can be quoted with single or double quotes. Unquoted values are also supported for simple identifiers but quoting is recommended.

##### Prefix match: `[attr^="value"]`

Matches elements where the attribute value starts with the given string.

```bash
# Match links starting with https
htmlq 'a[href^="https"]' < page.html

# Match links starting with a specific domain
htmlq 'a[href^="https://example.com"]' < page.html

# Match classes starting with "btn-"
htmlq '[class^="btn-"]' < page.html

# Match data attributes starting with a prefix
htmlq '[data-type^="user-"]' < page.html

# Match all external links (starting with http)
htmlq 'a[href^="http"]' < page.html
```

##### Suffix match: `[attr$="value"]`

Matches elements where the attribute value ends with the given string.

```bash
# Match links to PDF files
htmlq 'a[href$=".pdf"]' < page.html

# Match links to images
htmlq 'a[href$=".jpg"]' < page.html
htmlq 'a[href$=".png"]' < page.html

# Match image sources ending with specific extension
htmlq 'img[src$=".svg"]' < page.html

# Match links ending with a specific path
htmlq 'a[href$="/contact"]' < page.html
```

##### Substring match: `[attr*="value"]`

Matches elements where the attribute value contains the given string anywhere within it.

```bash
# Match links containing "example" anywhere in the URL
htmlq 'a[href*="example"]' < page.html

# Match elements whose class contains "btn"
htmlq '[class*="btn"]' < page.html

# Match links containing a query parameter
htmlq 'a[href*="utm_source"]' < page.html

# Match elements with "error" in their data attribute
htmlq '[data-message*="error"]' < page.html
```

##### Whitespace-separated match: `[attr~="value"]`

Matches elements where the attribute value is a whitespace-separated list of words, one of which is exactly the given value. This is particularly useful for matching individual class names (though the `.class` selector is more convenient for that purpose).

```bash
# Match elements where class list includes "active"
htmlq '[class~="active"]' < page.html

# Match elements with a specific rel value
htmlq 'link[rel~="stylesheet"]' < page.html
```

##### Hyphen-separated match: `[attr|="value"]`

Matches elements where the attribute value is either exactly the given value, or starts with the given value followed by a hyphen (`-`). This was designed for matching language codes like `en`, `en-US`, `en-GB`.

```bash
# Match elements with lang starting with "en"
htmlq '[lang|="en"]' < page.html

# This matches lang="en", lang="en-US", lang="en-GB", etc.
```

### Combinators

Combinators define relationships between selectors, allowing you to select elements based on their position relative to other elements in the document tree.

#### Descendant Combinator (space)

Selects elements that are descendants (children, grandchildren, etc.) of another element. The two selectors are separated by whitespace.

```bash
# All paragraphs inside a div
htmlq 'div p' < page.html

# All links inside the navigation
htmlq 'nav a' < page.html

# All list items inside an unordered list inside a div with class "menu"
htmlq 'div.menu ul li' < page.html

# All spans inside paragraphs inside articles
htmlq 'article p span' < page.html

# All images inside the main content area
htmlq '#content img' < page.html

# All emphasized text inside headings
htmlq 'h1 em' < page.html
```

The descendant combinator is the most commonly used combinator. The matched element can be at any depth within the ancestor; it does not need to be a direct child.

#### Child Combinator (`>`)

Selects elements that are direct children of another element. Unlike the descendant combinator, this does not match grandchildren or deeper descendants.

```bash
# Only direct child paragraphs of a div (not nested deeper)
htmlq 'div > p' < page.html

# Direct children list items of a specific ul
htmlq 'ul.top-level > li' < page.html

# Direct child divs of the body
htmlq 'body > div' < page.html

# Only immediate links inside nav (not nested in sub-menus)
htmlq 'nav > a' < page.html
```

The child combinator is useful for avoiding overly broad matches in deeply nested structures.

#### Adjacent Sibling Combinator (`+`)

Selects an element that is the immediately following sibling of another element. Both elements must share the same parent, and the second element must come directly after the first with no other element siblings in between.

```bash
# Paragraph immediately following an h2
htmlq 'h2 + p' < page.html

# List immediately following a heading
htmlq 'h3 + ul' < page.html

# Div immediately after a horizontal rule
htmlq 'hr + div' < page.html

# Label immediately followed by an input
htmlq 'label + input' < page.html
```

This combinator is useful for selecting the "first thing after" a specific marker element.

#### General Sibling Combinator (`~`)

Selects elements that are subsequent siblings of another element. Both elements must share the same parent, and the second element must come after the first, but not necessarily immediately after.

```bash
# All paragraphs that come after an h2 (same parent)
htmlq 'h2 ~ p' < page.html

# All list items after the first list item
htmlq 'li.first ~ li' < page.html

# All sibling divs after the header div
htmlq 'div.header ~ div' < page.html
```

Unlike the adjacent sibling combinator (`+`), the general sibling combinator matches all following siblings, not just the immediately next one.

### Pseudo-Classes

Pseudo-classes select elements based on their state or position within the document tree. htmlq supports structural pseudo-classes (those based on document structure), but not dynamic pseudo-classes (like `:hover` or `:focus`, which depend on user interaction and have no meaning in a non-interactive context).

#### `:first-child`

Matches an element that is the first child of its parent.

```bash
# First child paragraph in each container
htmlq 'p:first-child' < page.html

# First list item in each list
htmlq 'li:first-child' < page.html

# First div child of any element
htmlq 'div:first-child' < page.html
```

#### `:last-child`

Matches an element that is the last child of its parent.

```bash
# Last paragraph in each container
htmlq 'p:last-child' < page.html

# Last list item in each list
htmlq 'li:last-child' < page.html

# Last row in a table body
htmlq 'tbody tr:last-child' < page.html
```

#### `:nth-child(n)`

Matches elements based on their position among siblings. The argument can be a number, a keyword, or a formula.

```bash
# Third child element
htmlq ':nth-child(3)' < page.html

# Even-numbered children
htmlq 'tr:nth-child(even)' < page.html

# Odd-numbered children
htmlq 'tr:nth-child(odd)' < page.html

# Every third element starting from the first
htmlq 'li:nth-child(3n+1)' < page.html

# Every other row, starting from the second
htmlq 'tr:nth-child(2n)' < page.html

# First five elements
htmlq 'li:nth-child(-n+5)' < page.html

# Elements from the 4th onward
htmlq 'li:nth-child(n+4)' < page.html
```

The `An+B` formula works as follows:
- `n` is a counter starting at 0 and incrementing by 1.
- `A` is the step size (cycle length).
- `B` is the offset (starting position).
- The formula generates a set of positions: B, A+B, 2A+B, 3A+B, ...
- Only positive results are used (positions start at 1).

Examples of the formula:
- `2n`: positions 2, 4, 6, 8, ... (even)
- `2n+1`: positions 1, 3, 5, 7, ... (odd)
- `3n`: positions 3, 6, 9, 12, ...
- `3n+1`: positions 1, 4, 7, 10, ...
- `-n+3`: positions 3, 2, 1 (first three)
- `n+5`: positions 5, 6, 7, 8, ... (5th onward)

#### `:nth-last-child(n)`

Like `:nth-child()`, but counts from the end instead of the beginning.

```bash
# Second-to-last element
htmlq 'li:nth-last-child(2)' < page.html

# Last three elements
htmlq 'li:nth-last-child(-n+3)' < page.html
```

#### `:first-of-type`

Matches an element that is the first of its type (tag name) among its siblings.

```bash
# First paragraph in each container (even if other elements come before it)
htmlq 'p:first-of-type' < page.html

# First heading of each level
htmlq 'h2:first-of-type' < page.html
```

The difference between `:first-child` and `:first-of-type` is that `:first-child` requires the element to be the literal first child, while `:first-of-type` only requires it to be the first of its element type among siblings. For example, in `<div><span>...</span><p>...</p></div>`, the `<p>` is not `:first-child` but is `p:first-of-type`.

#### `:last-of-type`

Matches an element that is the last of its type among its siblings.

```bash
# Last paragraph in each container
htmlq 'p:last-of-type' < page.html
```

#### `:nth-of-type(n)`

Like `:nth-child()`, but only counts siblings of the same element type.

```bash
# Every other paragraph
htmlq 'p:nth-of-type(2n)' < page.html

# Third table of each type
htmlq 'table:nth-of-type(3)' < page.html
```

#### `:nth-last-of-type(n)`

Like `:nth-of-type()`, but counts from the end.

```bash
# Second-to-last paragraph
htmlq 'p:nth-last-of-type(2)' < page.html
```

#### `:only-child`

Matches an element that is the only child of its parent.

```bash
# Paragraphs that are the only child of their parent
htmlq 'p:only-child' < page.html
```

#### `:only-of-type`

Matches an element that is the only element of its type among its siblings.

```bash
# Images that are the only img inside their parent
htmlq 'img:only-of-type' < page.html
```

#### `:empty`

Matches elements that have no children (no child elements and no text nodes).

```bash
# Empty table cells
htmlq 'td:empty' < page.html

# Empty divs
htmlq 'div:empty' < page.html

# Empty spans
htmlq 'span:empty' < page.html
```

Note that an element with even a single space character of text content is not considered empty.

#### `:not(selector)`

Matches elements that do not match the given selector.

```bash
# All divs that are not hidden
htmlq 'div:not(.hidden)' < page.html

# All links that are not external
htmlq 'a:not([href^="http"])' < page.html

# All inputs that are not disabled
htmlq 'input:not([disabled])' < page.html

# List items that are not the first child
htmlq 'li:not(:first-child)' < page.html

# All elements except paragraphs inside an article
htmlq 'article :not(p)' < page.html

# Divs without a specific class
htmlq 'div:not(.ad)' < page.html
```

The `:not()` pseudo-class takes a simple selector as its argument. In CSS Selectors Level 3, the argument must be a simple selector (not a compound or complex selector).

#### `:root`

Matches the root element of the document (typically `<html>`).

```bash
# Select the root element
htmlq ':root' < page.html
```

### Selector Grouping (Multiple Selectors)

Multiple selectors can be combined with commas to match elements that match any of the listed selectors.

```bash
# Match all headings
htmlq 'h1, h2, h3, h4, h5, h6' < page.html

# Match paragraphs or blockquotes
htmlq 'p, blockquote' < page.html

# Match elements with either class
htmlq '.error, .warning' < page.html

# Match IDs
htmlq '#header, #footer' < page.html
```

When using comma-separated selectors within a single argument, all matching elements are returned in document order, without duplicates.

Note that in htmlq, you can also specify multiple selectors as separate arguments:

```bash
# These are equivalent
htmlq 'h1, h2, h3' < page.html
htmlq 'h1' 'h2' 'h3' < page.html
```

When provided as separate arguments, each selector is processed independently, and results are concatenated.

### Compound Selectors

Multiple simple selectors can be combined without whitespace to create compound selectors that all apply to the same element.

```bash
# Div element with class "container" and id "main"
htmlq 'div.container#main' < page.html

# Input element with type "text" and class "large"
htmlq 'input[type="text"].large' < page.html

# Anchor element with class "btn" that is not disabled
htmlq 'a.btn:not(.disabled)' < page.html

# First list item with class "special"
htmlq 'li.special:first-child' < page.html

# Span with both data attributes
htmlq 'span[data-x][data-y]' < page.html
```

### Complex Selectors

Complex selectors combine compound selectors with combinators to express relationships in the document tree.

```bash
# First paragraph inside a div with class "article" that is a direct child of main
htmlq 'main > div.article p:first-child' < page.html

# Links inside list items that are odd children of an unordered list
htmlq 'ul > li:nth-child(odd) a' < page.html

# Bold text inside the last paragraph of each section
htmlq 'section p:last-of-type strong' < page.html

# All spans that are direct children of divs with a data-role attribute
htmlq 'div[data-role] > span' < page.html

# Image immediately following a heading inside an article
htmlq 'article h2 + img' < page.html
```

---

## Input Handling

### Reading from Standard Input (Default)

By default, htmlq reads its entire HTML input from standard input (stdin). The input is read completely before parsing begins, meaning htmlq does not produce streaming output -- it reads the entire document, parses it into a DOM tree, evaluates the selector(s), and then produces output.

```bash
# Pipe from curl
curl -s https://example.com | htmlq 'title'

# Pipe from wget
wget -qO- https://example.com | htmlq 'h1'

# Pipe from cat
cat page.html | htmlq '.content'

# Redirect from file
htmlq '.content' < page.html

# Heredoc input
htmlq 'p' <<'EOF'
<html>
<body>
<p>Hello, world!</p>
</body>
</html>
EOF
```

### Reading from a File (`-f`)

The `-f` flag provides a direct way to read HTML from a file without shell redirection:

```bash
htmlq -f page.html 'h1'
htmlq -f /path/to/document.html 'div.content'
```

The behavior is identical to using shell input redirection (`< file`), but `-f` can be more convenient in some contexts, especially when building command strings programmatically.

If the specified file does not exist or is not readable, htmlq prints an error message to stderr and exits with a non-zero exit code.

### HTML Parsing Behavior

htmlq uses html5ever for parsing, which implements the full HTML5 parsing algorithm as specified in the WHATWG HTML Living Standard. This parser is designed to handle real-world HTML, including:

**Malformed HTML**: html5ever applies the same error-recovery rules as web browsers. Missing closing tags, improperly nested elements, and other markup errors are handled gracefully.

```bash
# Missing closing tags -- parsed correctly
echo '<p>First<p>Second' | htmlq 'p'
# Matches both paragraphs (the parser implicitly closes the first <p>)

# Improperly nested tags -- handled by the parser
echo '<b><i>text</b></i>' | htmlq 'i'
# The parser reconstructs a valid tree
```

**Incomplete documents**: You do not need to provide a complete HTML document. htmlq handles fragments:

```bash
# Just a fragment
echo '<span class="x">hello</span>' | htmlq 'span'
# Works fine

# Just a table row
echo '<tr><td>Cell</td></tr>' | htmlq 'td'
# Works fine
```

**Automatic structure**: The html5ever parser automatically adds structural elements (`<html>`, `<head>`, `<body>`) when they are missing. This means that even a bare `<p>Hello</p>` is parsed into a full document tree, and you can select `body > p` to match it.

```bash
# Bare content gets wrapped in html/head/body
echo '<p>Hello</p>' | htmlq 'body > p'
# Matches the paragraph
```

**Character encoding**: html5ever handles various character encodings. UTF-8 is the default and most common encoding for modern HTML. The parser also handles HTML entities:

```bash
# HTML entities are parsed correctly
echo '<p>&amp; &lt; &gt; &quot;</p>' | htmlq -t 'p'
# Output: & < > "
```

**Comments and processing instructions**: HTML comments (`<!-- ... -->`) are parsed and included in the DOM tree but are generally not matchable by CSS selectors (since CSS selectors only match elements). They are preserved in HTML output.

**DOCTYPE declarations**: DOCTYPE declarations are parsed and recognized but do not affect selector matching.

---

## Output Modes

htmlq has three primary output modes, controlled by the `-t` and `-a` flags. The default mode outputs HTML, `-t` outputs text, and `-a` outputs attribute values.

### Default Mode: HTML Output

In the default mode (no `-t` or `-a` flag), htmlq outputs the outer HTML of each matched element. "Outer HTML" means the element's opening tag, all its contents (including child elements), and its closing tag.

```bash
echo '<div><p class="intro">Hello <strong>world</strong></p></div>' | htmlq 'p'
# Output: <p class="intro">Hello <strong>world</strong></p>
```

If multiple elements match the selector, each element's outer HTML is output:

```bash
echo '<ul><li>One</li><li>Two</li><li>Three</li></ul>' | htmlq 'li'
# Output:
# <li>One</li>
# <li>Two</li>
# <li>Three</li>
```

The HTML output is serialized from the parsed DOM tree, not reproduced verbatim from the input. This means:

- Attribute order may differ from the original source.
- Whitespace within the HTML may be normalized.
- Self-closing tag syntax may be adjusted (e.g., `<br>` vs `<br />`).
- The parser's error recovery may alter the structure slightly.

### Text Mode (`-t`)

With the `-t` flag, htmlq outputs only the text content of matched elements, with all HTML tags stripped. Text content is obtained by concatenating all text nodes within the element's subtree.

```bash
echo '<p>Hello <strong>world</strong></p>' | htmlq -t 'p'
# Output: Hello world

echo '<div><h1>Title</h1><p>Para 1</p><p>Para 2</p></div>' | htmlq -t 'div'
# Output: TitlePara 1Para 2

echo '<a href="/about"><span class="icon">*</span> About Us</a>' | htmlq -t 'a'
# Output: * About Us
```

Key behaviors of text mode:

- All HTML tags are removed; only text node content remains.
- Text from different child elements is concatenated directly, without inserted separators.
- Leading and trailing whitespace within text nodes is preserved as it exists in the DOM.
- If multiple elements match, text from each element is output.

Text mode is particularly useful for extracting readable content:

```bash
# Get the page title
curl -s https://example.com | htmlq -t 'title'

# Get all paragraph text
curl -s https://example.com | htmlq -t 'p'

# Get text from a specific element, removing scripts first
curl -s https://example.com | htmlq -r 'script' -r 'style' -t '#content'
```

### Attribute Mode (`-a`)

With the `-a <ATTR>` flag, htmlq outputs the value of the specified attribute from each matched element, one value per line.

```bash
echo '<a href="/one">One</a><a href="/two">Two</a>' | htmlq -a href 'a'
# Output:
# /one
# /two

echo '<img src="a.jpg" alt="Photo A"><img src="b.jpg" alt="Photo B">' | htmlq -a alt 'img'
# Output:
# Photo A
# Photo B

echo '<div data-id="1" data-name="foo"></div>' | htmlq -a data-name 'div'
# Output: foo
```

If a matched element does not have the requested attribute, it is silently skipped:

```bash
echo '<a href="/link">Link</a><a>No href</a>' | htmlq -a href 'a'
# Output: /link
# (The second anchor is skipped because it has no href)
```

### Pretty-Print Mode (`-p`)

The `-p` flag modifies the HTML output mode to produce indented, human-readable HTML. Each level of nesting is indented, making it easier to visualize the document structure.

```bash
echo '<div><ul><li>One</li><li>Two</li></ul></div>' | htmlq -p 'div'
# Output:
# <div>
#   <ul>
#     <li>
#       One
#     </li>
#     <li>
#       Two
#     </li>
#   </ul>
# </div>
```

Pretty-printing is purely cosmetic and does not affect the content or structure of the output. It is useful for:

- Debugging selectors by inspecting matched element structure
- Producing readable output for documentation or reports
- Inspecting deeply nested HTML structures

---

## Base URL Resolution (`-b`)

### How It Works

The `-b` flag sets a base URL that is used to resolve relative URLs when extracting attribute values with `-a`. This is essential for web scraping workflows where you need fully qualified URLs.

URL resolution follows RFC 3986 (Uniform Resource Identifier: Generic Syntax). The algorithm handles all standard cases:

### Resolution Examples

Given a base URL of `https://example.com/dir/page.html`:

| Relative URL | Resolved URL |
|---|---|
| `/about` | `https://example.com/about` |
| `other.html` | `https://example.com/dir/other.html` |
| `../images/logo.png` | `https://example.com/images/logo.png` |
| `#section` | `https://example.com/dir/page.html#section` |
| `?q=search` | `https://example.com/dir/page.html?q=search` |
| `//cdn.example.com/file.js` | `https://cdn.example.com/file.js` |
| `https://other.com/page` | `https://other.com/page` (unchanged) |
| `mailto:user@example.com` | `mailto:user@example.com` (unchanged) |

### Practical Usage

```bash
# Download a page and extract all absolute link URLs
curl -s https://news.ycombinator.com | htmlq -b 'https://news.ycombinator.com' -a href 'a'

# Extract absolute image URLs
curl -s https://example.com/gallery | htmlq -b 'https://example.com/gallery' -a src 'img'

# Build a sitemap of absolute URLs
curl -s https://example.com | htmlq -b 'https://example.com' -a href 'a[href]' | sort -u

# Extract stylesheet URLs
curl -s https://example.com | htmlq -b 'https://example.com' -a href 'link[rel="stylesheet"]'
```

### Edge Cases in URL Resolution

- **Already-absolute URLs**: URLs that already have a scheme (like `https://...` or `http://...`) are not modified by `-b`.
- **Protocol-relative URLs**: URLs starting with `//` have the scheme from the base URL prepended.
- **Empty href**: An empty `href=""` resolves to the base URL itself.
- **JavaScript URLs**: URLs like `javascript:void(0)` are output as-is, since they are not relative paths.
- **Data URLs**: URLs starting with `data:` are output as-is.

---

## Node Removal (`-r`)

### Purpose

The `-r` (remove nodes) flag is a powerful preprocessing tool that modifies the document before the main selector is evaluated. It removes all elements matching the given CSS selector, along with their entire subtrees (all descendant elements and text).

### Why Remove Nodes?

Real-world HTML pages contain many elements that interfere with clean content extraction:

- **`<script>` tags**: Contain JavaScript code that appears as text content when using `-t`.
- **`<style>` tags**: Contain CSS that similarly pollutes text extraction.
- **Navigation menus**: Repetitive link text that clutters content extraction.
- **Advertisements**: Div elements with ad content.
- **Footers and sidebars**: Boilerplate content that isn't part of the main content.
- **Hidden elements**: Elements with `display: none` or `aria-hidden` that aren't visible on the page.

### Usage Examples

```bash
# Clean text extraction: remove scripts, styles, and nav
curl -s https://example.com | htmlq -r 'script' -r 'style' -r 'nav' -t 'body'

# Remove sidebar and ads before extracting article content
curl -s https://blog.example.com/post | htmlq -r '#sidebar' -r '.advertisement' 'article'

# Remove all images from the output
cat page.html | htmlq -r 'img' 'body'

# Remove SVG icons before extracting text
cat page.html | htmlq -r 'svg' -t '.content'

# Remove footer before extracting links
cat page.html | htmlq -r 'footer' -a href 'a'

# Remove hidden elements
cat page.html | htmlq -r '[aria-hidden="true"]' -t '.main'

# Remove specific classes of elements
cat page.html | htmlq -r '.no-print' -r '.screen-reader-only' 'body'
```

### Multiple Removals

The `-r` flag can be specified multiple times. Each removal selector is applied in sequence:

```bash
htmlq -r 'script' -r 'style' -r 'nav' -r 'footer' -r '.ad' -t 'body' < page.html
```

All removals happen before the main selector is evaluated, so the main selector only sees the remaining content.

### Interaction with Main Selector

Since removal happens before selection:

- If you remove an element that would have been matched by the main selector, it will not appear in the output.
- If you remove a parent of an element that would have been matched, the child is also gone.
- If you remove a sibling of a matched element, the sibling combinator results may change.

```bash
# If the page has <div class="content"><p>Text</p><div class="ad">Ad</div></div>
# Removing .ad means it won't appear in the output
echo '<div class="content"><p>Text</p><div class="ad">Ad</div></div>' | htmlq -r '.ad' '.content'
# Output: <div class="content"><p>Text</p></div>
```

---

## Exit Codes

htmlq uses conventional Unix exit codes:

| Exit Code | Meaning |
|---|---|
| 0 | Success. The program ran successfully, even if no elements matched the selector. |
| Non-zero | Error. An error occurred during execution. |

### Success (Exit Code 0)

htmlq exits with code 0 in all of the following cases:

- One or more elements matched the selector and were output.
- No elements matched the selector (empty output, but no error).
- The HTML was empty but parseable.

This design follows the principle that "no matches" is not an error condition. It is analogous to how `grep` with `-q` works or how `jq` handles queries that produce no output. The absence of results is a valid outcome, not a failure.

### Error (Non-Zero Exit Code)

htmlq exits with a non-zero code in error conditions such as:

- An invalid CSS selector was provided.
- The file specified with `-f` does not exist or cannot be read.
- An I/O error occurred while reading stdin or writing stdout.
- Invalid command-line arguments were provided.

### Using Exit Codes in Scripts

```bash
# Check if a selector produces any output
if curl -s https://example.com | htmlq 'div.special' | grep -q .; then
    echo "Found special divs"
else
    echo "No special divs found"
fi

# Note: cannot rely on exit code alone for "no matches" since it's still 0
# Use output presence instead
output=$(curl -s https://example.com | htmlq -t 'h1')
if [ -n "$output" ]; then
    echo "Page title: $output"
fi
```

---

## Error Handling

### Invalid CSS Selectors

If you provide a CSS selector that cannot be parsed, htmlq outputs an error message to stderr and exits with a non-zero exit code.

```bash
htmlq '!!!invalid' < page.html
# Error: invalid selector

htmlq '[' < page.html
# Error: invalid selector

htmlq 'div[attr=' < page.html
# Error: invalid selector
```

Common causes of invalid selectors:
- Unclosed brackets or parentheses
- Invalid pseudo-class names
- Syntax errors in attribute selectors
- Unrecognized tokens

### File Errors

When using `-f` with a nonexistent file:

```bash
htmlq -f nonexistent.html 'h1'
# Error: file not found or permission denied
```

### Empty Input

Empty input (zero bytes from stdin or an empty file) is handled gracefully. The HTML parser produces an empty document, no elements match any selector, and htmlq produces no output with exit code 0.

```bash
echo -n '' | htmlq 'p'
# (no output, exit code 0)
```

### Malformed HTML

As discussed in the HTML parsing section, malformed HTML is not an error condition. The html5ever parser applies the HTML5 error-recovery algorithm to produce the best possible DOM tree from the given input. htmlq never rejects input because it is "invalid HTML."

---

## Pipe-Friendly Design

htmlq is designed to be a well-behaved Unix citizen, fitting seamlessly into pipelines and scripting workflows.

### Standard I/O Conventions

- **stdin**: HTML input (default)
- **stdout**: Selected content (HTML, text, or attribute values)
- **stderr**: Error messages only

This separation means you can redirect stdout to a file or pipe it to another command without error messages contaminating the output:

```bash
# Errors go to stderr, not stdout
htmlq 'p' < page.html > output.txt 2> errors.txt
```

### Line-Oriented Output

When using `-a` (attribute mode), output is strictly one value per line, making it ideal for further processing with line-oriented tools:

```bash
# Count the number of links
curl -s https://example.com | htmlq -a href 'a' | wc -l

# Sort and deduplicate URLs
curl -s https://example.com | htmlq -a href 'a' | sort -u

# Filter URLs with grep
curl -s https://example.com | htmlq -a href 'a' | grep '\.pdf$'

# Process URLs in a loop
curl -s https://example.com | htmlq -a href 'a' | while read -r url; do
    echo "Found link: $url"
done
```

### Pipeline Composition

htmlq works naturally with other Unix tools:

```bash
# Fetch, extract, and download
curl -s https://example.com | htmlq -b 'https://example.com' -a href 'a[href$=".pdf"]' | xargs -I{} wget {}

# Extract and format with other tools
curl -s https://example.com | htmlq -t 'article p' | fmt -w 80

# Chain with jq for JSON APIs that return HTML
curl -s https://api.example.com/content | jq -r '.html' | htmlq -t '.body'

# Combine with sed for post-processing
curl -s https://example.com | htmlq -t 'h2' | sed 's/^/## /'

# Use with xargs for batch processing
cat urls.txt | xargs -I{} sh -c 'curl -s {} | htmlq -t "title"'

# Pipe HTML output through htmlq again for further refinement
curl -s https://example.com | htmlq '.content' | htmlq -t 'p'
```

### No Trailing Newline Issues

htmlq produces clean output that works well with other tools. Each line of output in attribute mode is terminated with a newline, ensuring compatibility with `read`, `wc`, `sort`, and other line-oriented utilities.

---

## Multiple Selector Handling

htmlq accepts multiple CSS selectors, either as comma-separated groups within a single argument or as multiple positional arguments.

### Comma-Separated Selectors (Single Argument)

```bash
# Select all h1, h2, and h3 elements
htmlq 'h1, h2, h3' < page.html
```

This follows standard CSS selector grouping. Elements matching any of the selectors are returned in document order.

### Multiple Positional Arguments

```bash
# Select h1, h2, and h3 as separate arguments
htmlq 'h1' 'h2' 'h3' < page.html
```

When multiple selectors are passed as separate arguments, each selector is processed independently against the same document. Results are concatenated in the order the selectors are given, with each selector's results appearing in document order.

### Behavioral Differences

When using comma-separated selectors within a single argument, the CSS selector engine handles deduplication naturally -- if an element matches multiple selectors in the group, it appears only once in the output, in its document order position.

When using multiple positional arguments, each selector is processed independently. The results are then concatenated, and elements may potentially appear more than once if they match multiple selectors. In practice, most well-constructed selectors target distinct elements, so duplicates are uncommon.

### Practical Examples

```bash
# Extract all heading levels for a table of contents
curl -s https://example.com | htmlq -t 'h1, h2, h3, h4'

# Extract multiple types of metadata
curl -s https://example.com | htmlq 'meta[name="description"]' 'meta[name="keywords"]' 'title'

# Extract both ordered and unordered lists
htmlq 'ul, ol' < page.html

# Extract links and images
htmlq 'a[href]' 'img[src]' < page.html
```

---

## Edge Cases and Special Behaviors

### No Matches

When no elements match the given selector, htmlq produces no output and exits with code 0. This is not an error condition.

```bash
echo '<p>Hello</p>' | htmlq 'div'
# (no output, exit code 0)

echo '<p>Hello</p>' | htmlq '#nonexistent'
# (no output, exit code 0)
```

### Nested Matches

When a selector matches elements at multiple levels of nesting, htmlq returns all matching elements. If both a parent and its child match the selector, both appear in the output.

```bash
echo '<div class="x"><div class="x">inner</div></div>' | htmlq '.x'
# Output includes both the outer and inner div
```

This means the inner div's content appears twice in the output: once as part of the outer div's HTML, and once as its own match. This is the correct behavior according to CSS selector semantics -- both elements individually match the selector.

### Self-Closing Tags

HTML5 defines certain elements as void elements that cannot have children: `<br>`, `<hr>`, `<img>`, `<input>`, `<meta>`, `<link>`, etc. These are serialized without closing tags:

```bash
echo '<div><br/><hr/><img src="x.jpg"/></div>' | htmlq 'div'
# Output may be: <div><br><hr><img src="x.jpg"></div>
# (html5ever normalizes self-closing syntax)
```

The parser normalizes self-closing tags according to HTML5 rules. Tags like `<br />`, `<br/>`, and `<br>` are all equivalent and produce the same parsed element.

### HTML Entities

HTML entities in the source document are parsed and represented as their actual characters in the DOM. When output, they may be serialized back as entities or as literal characters, depending on context:

```bash
echo '<p>&lt;tag&gt; &amp; &quot;quotes&quot;</p>' | htmlq -t 'p'
# Output: <tag> & "quotes"

echo '<p>&lt;tag&gt;</p>' | htmlq 'p'
# Output may preserve or decode entities depending on serialization
```

In text mode (`-t`), entities are always decoded to their character equivalents. In HTML output mode, the serializer may choose to re-encode characters that are special in HTML contexts.

### Unicode Content

htmlq fully supports Unicode content in HTML documents:

```bash
echo '<p>Hello, world!</p>' | htmlq -t 'p'
# Output: Hello, world!

echo '<p>Привет мир</p>' | htmlq -t 'p'
# Output: Привет мир

echo '<p>こんにちは世界</p>' | htmlq -t 'p'
# Output: こんにちは世界

echo '<div lang="ar">مرحبا بالعالم</div>' | htmlq -t 'div'
# Output: مرحبا بالعالم
```

Attribute values containing Unicode are also handled correctly:

```bash
echo '<a href="/page" title="cafe">Link</a>' | htmlq -a title 'a'
# Output: cafe
```

### Whitespace Handling

HTML whitespace handling follows the parsing rules of html5ever:

- Multiple consecutive whitespace characters in text content may be normalized to single spaces (following HTML whitespace rules).
- Whitespace between elements is treated as text nodes and preserved in the DOM.
- Preformatted content inside `<pre>` tags preserves whitespace.

```bash
echo '<pre>  line 1
  line 2
  line 3</pre>' | htmlq -t 'pre'
# Output preserves whitespace:
#   line 1
#   line 2
#   line 3

echo '<p>  multiple   spaces   here  </p>' | htmlq -t 'p'
# Output: whitespace handling depends on parser normalization
```

### Very Large Documents

htmlq reads the entire document into memory and builds a DOM tree. For very large HTML documents (hundreds of megabytes), this means memory usage will be proportional to the document size. There is no streaming mode.

For most practical use cases -- web pages, documentation, reports -- this is not a concern. A typical web page is well under 1 MB of HTML.

### Empty Elements

Elements that are present but empty produce output in HTML mode but no visible output in text mode:

```bash
echo '<p></p><p>Content</p>' | htmlq 'p'
# Output:
# <p></p>
# <p>Content</p>

echo '<p></p><p>Content</p>' | htmlq -t 'p'
# Output:
# (empty line from first p)
# Content
```

### Boolean Attributes

HTML5 boolean attributes like `disabled`, `checked`, `readonly`, etc. can appear as either `<input disabled>` or `<input disabled="disabled">` or `<input disabled="">`. They are all equivalent:

```bash
echo '<input disabled>' | htmlq -a disabled 'input'
# Output: (empty string or "disabled" depending on serialization)

echo '<input disabled="disabled">' | htmlq '[disabled]'
# Matches the element
```

### Comments in HTML

HTML comments are parsed and preserved in the DOM tree but are not matchable by CSS selectors:

```bash
echo '<!-- comment --><p>text</p>' | htmlq 'p'
# Output: <p>text</p>

# Comments may appear in HTML output of parent elements
echo '<div><!-- hidden --><p>visible</p></div>' | htmlq 'div'
# Output may include: <div><!-- hidden --><p>visible</p></div>
```

### CDATA Sections

In HTML5, CDATA sections are only valid inside SVG and MathML embedded content. The parser handles them according to the HTML5 specification.

### Doctype Declarations

DOCTYPE declarations are parsed but do not affect selector matching or output:

```bash
echo '<!DOCTYPE html><html><body><p>Hello</p></body></html>' | htmlq 'p'
# Output: <p>Hello</p>
```

---

## Common Use Cases

### Web Scraping Pipelines

htmlq is a natural fit for web scraping workflows built from Unix command-line tools. Here are common patterns:

#### Extracting Links from a Page

```bash
# Get all link URLs from a page
curl -s https://example.com | htmlq -a href 'a'

# Get absolute URLs
curl -s https://example.com | htmlq -b 'https://example.com' -a href 'a'

# Get only external links
curl -s https://example.com | htmlq -a href 'a[href^="http"]'

# Get links from the navigation only
curl -s https://example.com | htmlq -a href 'nav a'

# Get unique, sorted links
curl -s https://example.com | htmlq -b 'https://example.com' -a href 'a' | sort -u
```

#### Extracting Metadata

```bash
# Page title
curl -s https://example.com | htmlq -t 'title'

# Meta description
curl -s https://example.com | htmlq -a content 'meta[name="description"]'

# Open Graph title
curl -s https://example.com | htmlq -a content 'meta[property="og:title"]'

# Open Graph image
curl -s https://example.com | htmlq -a content 'meta[property="og:image"]'

# All meta tags
curl -s https://example.com | htmlq 'meta'

# Canonical URL
curl -s https://example.com | htmlq -a href 'link[rel="canonical"]'

# RSS/Atom feed URLs
curl -s https://example.com | htmlq -a href 'link[type="application/rss+xml"]'
curl -s https://example.com | htmlq -a href 'link[type="application/atom+xml"]'
```

#### Scraping Article Content

```bash
# Get article body text, cleaned up
curl -s https://blog.example.com/post | htmlq -r 'script' -r 'style' -r 'nav' -r 'footer' -r '.comments' -t 'article'

# Get article HTML for offline reading
curl -s https://blog.example.com/post | htmlq -p 'article.post-content'

# Get all image URLs from an article
curl -s https://blog.example.com/post | htmlq -b 'https://blog.example.com' -a src 'article img'
```

#### Downloading Resources

```bash
# Download all PDFs linked from a page
curl -s https://example.com/resources | \
    htmlq -b 'https://example.com' -a href 'a[href$=".pdf"]' | \
    xargs -I{} wget -q {}

# Download all images from a page
curl -s https://example.com/gallery | \
    htmlq -b 'https://example.com' -a src 'img' | \
    xargs -I{} wget -q {}

# Mirror stylesheets
curl -s https://example.com | \
    htmlq -b 'https://example.com' -a href 'link[rel="stylesheet"]' | \
    xargs -I{} wget -q {}
```

#### Building CSV/TSV from HTML Tables

```bash
# Extract table rows as tab-separated values
curl -s https://example.com/data | htmlq -t 'table tbody tr td' | paste - - - -

# Extract specific columns from a table
curl -s https://example.com/data | htmlq -t 'table tr td:nth-child(1)'
curl -s https://example.com/data | htmlq -t 'table tr td:nth-child(2)'

# Get table headers
curl -s https://example.com/data | htmlq -t 'table th'
```

#### Monitoring and Alerting

```bash
# Check if a page contains a specific element
if curl -s https://status.example.com | htmlq '.incident-active' | grep -q .; then
    echo "ALERT: Active incidents detected"
fi

# Extract version number from a release page
curl -s https://example.com/releases | htmlq -t '.release-version:first-child'

# Monitor price changes
price=$(curl -s https://store.example.com/product | htmlq -t '.price')
echo "Current price: $price"

# Check for new blog posts
curl -s https://blog.example.com | htmlq -t 'article h2:first-of-type'
```

### Processing Local HTML Files

```bash
# Extract data from saved HTML files
for f in pages/*.html; do
    echo "File: $f"
    htmlq -f "$f" -t 'title'
done

# Process HTML reports
htmlq -f report.html -t 'table.summary td'

# Extract content from HTML emails
htmlq -f email.html -r 'style' -t 'body'

# Analyze HTML documentation
htmlq -f docs.html -t 'h1, h2, h3' | head -20
```

### Integration with Other Tools

#### With curl

```bash
# Follow redirects and extract content
curl -sL https://example.com | htmlq 'article'

# Pass cookies for authenticated pages
curl -s -b cookies.txt https://example.com/dashboard | htmlq '.user-info'

# With custom headers
curl -s -H 'User-Agent: Mozilla/5.0' https://example.com | htmlq 'body'
```

#### With wget

```bash
# Download and extract in one go
wget -qO- https://example.com | htmlq -t 'h1'
```

#### With find and xargs

```bash
# Process all HTML files in a directory tree
find . -name '*.html' | xargs -I{} sh -c 'echo "{}:"; htmlq -f "{}" -t "title"'
```

#### With awk and sed

```bash
# Post-process extracted text
curl -s https://example.com | htmlq -t 'li' | awk '{print NR". "$0}'

# Clean up whitespace in extracted text
curl -s https://example.com | htmlq -t 'p' | sed 's/^[[:space:]]*//'
```

#### With jq

```bash
# When HTML is embedded in JSON
curl -s https://api.example.com/data | jq -r '.content' | htmlq 'p'

# Create JSON from extracted HTML data
curl -s https://example.com | htmlq -t 'h1' | jq -R '{title: .}'
```

#### With sort, uniq, wc

```bash
# Count unique link domains
curl -s https://example.com | htmlq -a href 'a[href^="http"]' | \
    awk -F/ '{print $3}' | sort | uniq -c | sort -rn

# Count elements of each type
curl -s https://example.com | htmlq -a class 'div[class]' | sort | uniq -c | sort -rn

# Count the number of images
curl -s https://example.com | htmlq -a src 'img' | wc -l
```

### Chaining Multiple htmlq Invocations

Since htmlq outputs HTML by default, you can pipe its output through another htmlq invocation for multi-step extraction:

```bash
# First extract the main content area, then get paragraphs from it
curl -s https://example.com | htmlq '.main-content' | htmlq -t 'p'

# Extract a section, remove unwanted elements, then get text
curl -s https://example.com | htmlq 'article' | htmlq -r '.author-bio' -t 'p'

# Narrow down progressively
curl -s https://example.com | htmlq '#content' | htmlq '.post' | htmlq -t 'h2'
```

---

## Comparison with Other Tools

### htmlq vs. pup

**pup** is another command-line HTML processor, written in Go. It also uses CSS selectors but has a different feature set.

| Feature | htmlq | pup |
|---|---|---|
| Language | Rust | Go |
| Selector syntax | CSS (Servo/kuchiki) | CSS (cascadia) |
| Text extraction | `-t` flag | `text{}` pseudo-selector |
| Attribute extraction | `-a <attr>` flag | `attr{<attr>}` pseudo-selector |
| Pretty-printing | `-p` flag | Default (or `--plain`) |
| Node removal | `-r` flag | Not built-in |
| Base URL resolution | `-b` flag | Not built-in |
| JSON output | No | `json{}` pseudo-selector |
| Color output | No | `--color` flag |
| Numbering/counting | No | `--number` flag |
| File input | `-f` flag | Not built-in (stdin only) |

**Key differences:**

- **pup** uses pseudo-selectors (`text{}`, `attr{}`, `json{}`) for output modes, while htmlq uses flags (`-t`, `-a`).
- **htmlq** has built-in node removal (`-r`), which pup lacks.
- **htmlq** has built-in base URL resolution (`-b`), which pup lacks.
- **pup** can output JSON representations of matched elements, which htmlq cannot.
- **pup** pretty-prints by default, while htmlq requires the `-p` flag.
- **htmlq** uses Rust's html5ever (Firefox's parser), while pup uses Go's cascadia library.

**When to choose htmlq:** When you need node removal before extraction, base URL resolution, or prefer a Rust-based tool with a Firefox-grade HTML parser.

**When to choose pup:** When you need JSON output or prefer the pseudo-selector syntax for output modes.

### htmlq vs. xidel

**xidel** is a more powerful (and complex) command-line tool that supports CSS selectors, XPath, and XQuery for querying HTML and XML documents.

| Feature | htmlq | xidel |
|---|---|---|
| Language | Rust | Pascal |
| CSS selectors | Yes | Yes |
| XPath | No | Yes (1.0, 2.0, 3.0) |
| XQuery | No | Yes |
| JSONiq | No | Yes |
| HTTP client | No (relies on curl) | Built-in |
| Following links | No | Yes (--follow) |
| Template extraction | No | Yes |
| Variables | No | Yes |
| Output formats | HTML, text, attributes | HTML, text, JSON, XML, bash |

**Key differences:**

- **xidel** is vastly more powerful, supporting XPath 3.0, XQuery, and JSONiq in addition to CSS selectors.
- **xidel** has a built-in HTTP client and can follow links across pages.
- **xidel** supports template-based extraction and variable binding.
- **htmlq** is simpler, lighter, and more focused -- it does one thing well.
- **htmlq** is easier to install (via Cargo) and has fewer dependencies.

**When to choose htmlq:** When you need a simple, fast CSS selector tool for basic HTML extraction in a pipeline.

**When to choose xidel:** When you need XPath, XQuery, multi-page crawling, or more complex query logic.

### htmlq vs. BeautifulSoup (Python)

For comparison with a programming-library approach:

```python
# BeautifulSoup equivalent of: htmlq -a href 'a.nav-link'
from bs4 import BeautifulSoup
soup = BeautifulSoup(html, 'html.parser')
for link in soup.select('a.nav-link'):
    print(link['href'])
```

```bash
# htmlq equivalent
htmlq -a href 'a.nav-link' < page.html
```

**When to choose htmlq:** For quick one-off extractions, shell scripts, and pipeline integration. No Python environment needed.

**When to choose BeautifulSoup:** For complex extraction logic, programmatic processing, or when you need to modify and re-serialize the HTML in sophisticated ways.

### htmlq vs. xpath (xmllint)

```bash
# xmllint --xpath equivalent (requires well-formed XML or XHTML)
xmllint --html --xpath '//a/@href' page.html 2>/dev/null

# htmlq equivalent (handles any HTML)
htmlq -a href 'a' < page.html
```

**Key differences:**
- `xmllint --xpath` uses XPath syntax, not CSS selectors.
- `xmllint` can be stricter about HTML formatting (even with `--html`).
- htmlq's html5ever parser is more lenient with malformed HTML.
- htmlq has a simpler interface for common operations.

### htmlq vs. hxselect (html-xml-utils)

The `hxselect` tool from the html-xml-utils package also supports CSS selectors:

```bash
# hxselect usage
hxnormalize -x page.html | hxselect 'div.content'

# htmlq usage
htmlq 'div.content' < page.html
```

**Key differences:**
- `hxselect` requires the input to be normalized XML first (via `hxnormalize -x`), while htmlq handles raw HTML directly.
- htmlq has more convenient flags for attribute and text extraction.
- htmlq uses a more modern and complete CSS selector implementation.

---

## Advanced Patterns and Recipes

### Extracting Structured Data

#### Table to CSV Conversion

```bash
# Extract a table and convert to CSV (simple tables without nested elements)
curl -s https://example.com/data | htmlq -t 'table tr' | while IFS= read -r row; do
    echo "$row"
done

# For more structured extraction, process cells individually
for i in $(seq 1 $(curl -s https://example.com/data | htmlq 'table tbody tr' | wc -l)); do
    row=$(curl -s https://example.com/data | htmlq "table tbody tr:nth-child($i)")
    col1=$(echo "$row" | htmlq -t 'td:nth-child(1)')
    col2=$(echo "$row" | htmlq -t 'td:nth-child(2)')
    echo "$col1,$col2"
done
```

#### Extracting Definition Lists

```bash
# Get terms from a definition list
htmlq -t 'dt' < page.html

# Get definitions
htmlq -t 'dd' < page.html

# Pair them together
paste <(htmlq -t 'dt' < page.html) <(htmlq -t 'dd' < page.html)
```

#### Extracting Navigation Structure

```bash
# Get top-level navigation links
curl -s https://example.com | htmlq -a href 'nav > ul > li > a'

# Get navigation link text
curl -s https://example.com | htmlq -t 'nav > ul > li > a'

# Build a navigation map
paste <(curl -s https://example.com | htmlq -t 'nav a') \
      <(curl -s https://example.com | htmlq -b 'https://example.com' -a href 'nav a')
```

### Multi-Step Extraction Workflows

#### Crawling a List of Pages

```bash
# Extract links from an index page, then extract content from each
curl -s https://example.com/index | \
    htmlq -b 'https://example.com' -a href '.article-list a' | \
    while read -r url; do
        echo "=== $url ==="
        curl -s "$url" | htmlq -r 'script' -r 'style' -t 'article'
        echo
    done
```

#### Comparing Content Across Pages

```bash
# Extract titles from multiple pages
for url in https://example.com/page1 https://example.com/page2 https://example.com/page3; do
    title=$(curl -s "$url" | htmlq -t 'h1')
    echo "$url: $title"
done
```

### Selective Content Extraction

#### Getting the Nth Match

```bash
# Get only the first matching element (using head)
htmlq 'p' < page.html | head -1

# Get only the second matching element (using sed)
htmlq 'p' < page.html | sed -n '2p'

# Use :nth-of-type to be more precise
htmlq 'p:nth-of-type(2)' < page.html
```

#### Conditional Extraction

```bash
# Extract content only if a certain element exists
html=$(curl -s https://example.com)
if echo "$html" | htmlq '.article' | grep -q .; then
    echo "$html" | htmlq -r 'script' -t '.article'
fi
```

### Working with Forms

```bash
# Extract form action URLs
htmlq -a action 'form' < page.html

# Get all input field names
htmlq -a name 'input' < page.html

# Get select option values
htmlq -a value 'select option' < page.html

# Get textarea content
htmlq -t 'textarea' < page.html

# Get hidden field values
htmlq -a value 'input[type="hidden"]' < page.html

# Map form field names to their types
paste <(htmlq -a name 'input[name]' < page.html) <(htmlq -a type 'input[name]' < page.html)
```

### Working with Embedded Data

```bash
# Extract JSON-LD structured data
htmlq -t 'script[type="application/ld+json"]' < page.html

# Extract inline styles
htmlq -a style '[style]' < page.html

# Extract data attributes
htmlq -a data-config '[data-config]' < page.html

# Extract embedded SVG
htmlq 'svg' < page.html
```

### Security Analysis

```bash
# Find all external scripts
curl -s https://example.com | htmlq -a src 'script[src]'

# Find inline event handlers (potential XSS)
curl -s https://example.com | htmlq '[onclick]'
curl -s https://example.com | htmlq '[onload]'

# Find forms submitting to external URLs
curl -s https://example.com | htmlq -a action 'form[action^="http"]'

# Find iframes
curl -s https://example.com | htmlq -a src 'iframe[src]'

# Check for Content Security Policy meta tag
curl -s https://example.com | htmlq -a content 'meta[http-equiv="Content-Security-Policy"]'
```

---

## Performance Considerations

### Memory Usage

htmlq reads the entire HTML document into memory and constructs a full DOM tree. Memory usage is approximately proportional to the size of the input document, with some overhead for the tree structure. For typical web pages (under 1 MB), memory usage is negligible.

For very large documents (tens or hundreds of megabytes), be aware that memory usage will be significant. If you need to process extremely large HTML files, consider splitting them first or using a streaming approach with a different tool.

### Processing Speed

Rust's zero-cost abstractions and html5ever's optimized parsing make htmlq fast for typical workloads. Parsing and selector matching are both linear in the size of the document for simple selectors. Complex selectors with multiple combinators may have higher costs but are still efficient for practical document sizes.

In pipeline use cases, the bottleneck is almost always the network (curl/wget) rather than htmlq's processing time.

### Optimizing Pipelines

```bash
# SLOWER: Multiple htmlq invocations on the same page
title=$(curl -s "$url" | htmlq -t 'title')
desc=$(curl -s "$url" | htmlq -a content 'meta[name="description"]')
links=$(curl -s "$url" | htmlq -a href 'a')

# FASTER: Fetch once, process multiple times
html=$(curl -s "$url")
title=$(echo "$html" | htmlq -t 'title')
desc=$(echo "$html" | htmlq -a content 'meta[name="description"]')
links=$(echo "$html" | htmlq -a href 'a')

# FASTEST for multiple extractions: use -f with a saved file
curl -s "$url" -o /tmp/page.html
title=$(htmlq -f /tmp/page.html -t 'title')
desc=$(htmlq -f /tmp/page.html -a content 'meta[name="description"]')
links=$(htmlq -f /tmp/page.html -a href 'a')
```

---

## Frequently Asked Questions

### How do I select elements by multiple classes?

Chain class selectors without spaces:

```bash
# Element must have both "btn" and "primary" classes
htmlq '.btn.primary' < page.html

# Element must have "card", "featured", and "active" classes
htmlq '.card.featured.active' < page.html
```

### How do I select elements that do NOT have a class?

Use the `:not()` pseudo-class:

```bash
# Divs without the "hidden" class
htmlq 'div:not(.hidden)' < page.html

# Links without an href attribute
htmlq 'a:not([href])' < page.html
```

### How do I extract the inner HTML (not outer HTML)?

htmlq outputs the outer HTML of matched elements by default. To get inner HTML, you can match the element and pipe through another htmlq call to select its children:

```bash
# Outer HTML of a div
htmlq 'div.content' < page.html

# Inner content: select all children
echo '<div class="content"><p>One</p><p>Two</p></div>' | htmlq 'div.content > *'
# Output:
# <p>One</p>
# <p>Two</p>
```

### How do I handle pages that require JavaScript?

htmlq does not execute JavaScript. It works on the raw HTML source. For pages that require JavaScript to render content (single-page applications, dynamically loaded content), you need a headless browser to render the page first:

```bash
# Use a headless browser to render JavaScript, then extract with htmlq
# (requires a separate tool like chromium, puppeteer, or playwright)
chromium --headless --dump-dom https://example.com | htmlq '.dynamic-content'
```

### Can I modify HTML with htmlq?

htmlq is primarily a read-only extraction tool. The `-r` flag removes elements, but only for the purpose of extraction -- it does not modify files in place. For HTML modification, consider tools like `sed`, `xmlstarlet`, or a programming language with an HTML library.

However, you can achieve basic modification-like behavior by combining extraction with shell tools:

```bash
# "Remove" script tags by extracting everything else
htmlq -r 'script' 'html' < page.html > cleaned.html
```

### Why does my selector not match anything?

Common reasons:

1. **The element is added by JavaScript**: htmlq sees only the raw HTML, not the DOM after JavaScript execution.
2. **The selector syntax is wrong**: Try a simpler selector first to verify the HTML structure.
3. **Shell quoting issues**: Make sure your selector is properly quoted to prevent shell expansion.
4. **Case sensitivity**: HTML tag names are case-insensitive, but class names and attribute values are case-sensitive.
5. **Parser normalization**: html5ever may restructure the HTML differently than expected.

Debug by inspecting the full HTML:

```bash
# See what htmlq receives as input
cat page.html | htmlq 'html' | head -50

# Try progressively broader selectors
htmlq 'body' < page.html
htmlq 'body *' < page.html
htmlq 'div' < page.html
```

### How do I match elements containing specific text?

CSS selectors do not have a "contains text" selector. You need to combine htmlq with grep:

```bash
# Find paragraphs containing "important"
htmlq 'p' < page.html | grep 'important'

# Find list items containing a specific word
htmlq -t 'li' < page.html | grep -i 'keyword'
```

### How do I get only the first match?

```bash
# Using head to limit output
htmlq 'p' < page.html | head -1

# Using :first-child or :first-of-type for structural matches
htmlq 'p:first-of-type' < page.html

# For attribute extraction
htmlq -a href 'a' < page.html | head -1
```

### How do I count the number of matches?

```bash
# Count matching elements (in HTML mode, each element is one "block")
# For simple single-line elements:
htmlq 'li' < page.html | wc -l

# For attribute values (one per line):
htmlq -a href 'a' < page.html | wc -l

# For text values:
htmlq -t 'p' < page.html | wc -l
```

### How do I handle character encoding issues?

htmlq and html5ever generally handle UTF-8 encoded documents correctly. If you encounter encoding issues:

```bash
# Convert encoding before piping to htmlq
iconv -f ISO-8859-1 -t UTF-8 page.html | htmlq 'p'

# For pages with explicit charset
curl -s https://example.com | iconv -f $(curl -sI https://example.com | grep -i charset | sed 's/.*charset=//') -t UTF-8 | htmlq 'p'
```

---

## Selector Quick Reference

This section provides a compact reference table of all supported CSS selectors.

### Simple Selectors

| Selector | Description | Example |
|---|---|---|
| `E` | Elements of type E | `p`, `div`, `a` |
| `*` | Any element | `*` |
| `.class` | Elements with class | `.highlight` |
| `#id` | Element with ID | `#header` |
| `[attr]` | Elements with attribute | `[href]` |
| `[attr="val"]` | Attribute equals | `[type="text"]` |
| `[attr^="val"]` | Attribute starts with | `[href^="https"]` |
| `[attr$="val"]` | Attribute ends with | `[href$=".pdf"]` |
| `[attr*="val"]` | Attribute contains | `[class*="btn"]` |
| `[attr~="val"]` | Attribute word match | `[class~="active"]` |
| `[attr\|="val"]` | Attribute hyphen match | `[lang\|="en"]` |

### Combinators

| Combinator | Description | Example |
|---|---|---|
| `A B` | B descendant of A | `div p` |
| `A > B` | B direct child of A | `ul > li` |
| `A + B` | B immediately after A | `h2 + p` |
| `A ~ B` | B sibling after A | `h2 ~ p` |

### Pseudo-Classes

| Pseudo-Class | Description | Example |
|---|---|---|
| `:first-child` | First child of parent | `li:first-child` |
| `:last-child` | Last child of parent | `li:last-child` |
| `:nth-child(n)` | Nth child of parent | `tr:nth-child(2n)` |
| `:nth-last-child(n)` | Nth child from end | `li:nth-last-child(2)` |
| `:first-of-type` | First of its type | `p:first-of-type` |
| `:last-of-type` | Last of its type | `p:last-of-type` |
| `:nth-of-type(n)` | Nth of its type | `p:nth-of-type(3)` |
| `:nth-last-of-type(n)` | Nth of type from end | `p:nth-last-of-type(2)` |
| `:only-child` | Only child of parent | `p:only-child` |
| `:only-of-type` | Only of its type | `img:only-of-type` |
| `:empty` | No children | `td:empty` |
| `:not(s)` | Does not match s | `div:not(.hidden)` |
| `:root` | Root element | `:root` |

### Selector Grouping

| Pattern | Description | Example |
|---|---|---|
| `A, B` | A or B | `h1, h2, h3` |

---

## Option Combination Matrix

This table shows which option combinations are meaningful and their behavior:

| Options | Behavior |
|---|---|
| (none) | Output outer HTML of matched elements |
| `-p` | Pretty-printed outer HTML of matched elements |
| `-t` | Text content only, tags stripped |
| `-a attr` | Attribute value, one per line |
| `-t -p` | Same as `-t` (pretty-print has no effect on text) |
| `-a attr -p` | Same as `-a attr` (pretty-print has no effect on attributes) |
| `-a attr -b url` | Attribute value with relative URLs resolved |
| `-r sel` | Remove elements before main selection (combinable with all above) |
| `-r sel -t` | Remove elements, then extract text |
| `-r sel -a attr` | Remove elements, then extract attributes |
| `-r sel -p` | Remove elements, then pretty-print HTML |
| `-r sel -a attr -b url` | Remove elements, resolve URLs, extract attributes |
| `-f file` | Read from file instead of stdin (combinable with all above) |

---

## Troubleshooting

### "No output" when expecting results

1. **Verify the HTML reaches htmlq**: Save the input to a file and inspect it.
   ```bash
   curl -s https://example.com > /tmp/debug.html
   wc -c /tmp/debug.html  # Should be non-zero
   htmlq -f /tmp/debug.html 'body' | head -5  # Should show something
   ```

2. **Try a broader selector**: Start with `'body'` or `'*'` and narrow down.

3. **Check for JavaScript rendering**: View the page source in your browser (not "Inspect Element") to see the raw HTML.

4. **Verify your selector**: Use a simpler selector to confirm matching works, then add complexity.

### Shell quoting issues

CSS selectors often contain characters special to the shell. Always single-quote your selectors:

```bash
# WRONG: shell interprets # as comment
htmlq #header < page.html

# RIGHT: quoted
htmlq '#header' < page.html

# WRONG: shell interprets > as redirect
htmlq div > p < page.html

# RIGHT: quoted
htmlq 'div > p' < page.html

# WRONG: shell interprets * as glob
htmlq div * < page.html

# RIGHT: quoted
htmlq 'div *' < page.html

# WRONG: shell interprets parentheses
htmlq :nth-child(2) < page.html

# RIGHT: quoted
htmlq ':nth-child(2)' < page.html
```

### Encoding problems

If output contains garbled characters:

```bash
# Check the input encoding
file page.html

# Convert to UTF-8 before processing
iconv -f WINDOWS-1252 -t UTF-8 page.html | htmlq 'p'
```

### Unexpected HTML structure

html5ever normalizes HTML according to the HTML5 specification. This can cause surprises:

```bash
# <table> content outside <tbody> is automatically wrapped
echo '<table><tr><td>Cell</td></tr></table>' | htmlq 'table > tr'
# May not match! The parser inserts a <tbody> element.
# Use: htmlq 'table > tbody > tr'

# <p> tags are auto-closed before block elements
echo '<p>Para<div>Block</div>' | htmlq 'p'
# The <p> is auto-closed before <div>, so <div> is not inside <p>

# Void elements cannot have children
echo '<br>text</br>' | htmlq 'br'
# <br> is void; the text is not a child of <br>
```

### Performance with large files

For very large HTML files:

```bash
# Check file size first
ls -lh huge.html

# Consider extracting just the section you need
htmlq -f huge.html 'article' > article-only.html
htmlq -f article-only.html 'p'
```

---

## Version and Compatibility

htmlq follows Semantic Versioning. The version can be checked with:

```bash
htmlq --version
```

htmlq is compatible with:
- Linux (x86_64, aarch64)
- macOS (x86_64, aarch64/Apple Silicon)
- Windows (x86_64)

The minimum supported Rust version (MSRV) for building from source depends on the specific release. Check the project's documentation for the current MSRV.

---

## Complete Examples

### Example 1: Extract All External Links from Hacker News

```bash
curl -s https://news.ycombinator.com | \
    htmlq -a href 'a.titlelink' | \
    grep '^http'
```

### Example 2: Build a Sitemap from a Website's Navigation

```bash
curl -s https://example.com | \
    htmlq -b 'https://example.com' -a href 'nav a[href]' | \
    sort -u | \
    while read -r url; do
        echo "<url><loc>$url</loc></url>"
    done
```

### Example 3: Extract and Clean Article Text

```bash
curl -s https://blog.example.com/post-123 | \
    htmlq -r 'script' -r 'style' -r 'nav' -r 'footer' -r '.sidebar' -r '.comments' \
    -t 'article.post-body'
```

### Example 4: Download All Images from a Gallery Page

```bash
curl -s https://example.com/gallery | \
    htmlq -b 'https://example.com' -a src '.gallery img' | \
    xargs -P4 -I{} wget -q -P ./images/ {}
```

### Example 5: Monitor a Page for Changes

```bash
while true; do
    content=$(curl -s https://status.example.com | htmlq -t '.current-status')
    echo "$(date): $content"
    sleep 60
done
```

### Example 6: Extract Table Data as TSV

```bash
curl -s https://example.com/data | \
    htmlq 'table tbody tr' | \
    while IFS= read -r row; do
        echo "$row" | htmlq -t 'td' | paste -s -d'\t' -
    done
```

### Example 7: Find Broken Image References

```bash
curl -s https://example.com | \
    htmlq -b 'https://example.com' -a src 'img' | \
    while read -r url; do
        status=$(curl -o /dev/null -s -w '%{http_code}' "$url")
        if [ "$status" != "200" ]; then
            echo "BROKEN ($status): $url"
        fi
    done
```

### Example 8: Extract RSS Feed URLs from Multiple Sites

```bash
cat sites.txt | while read -r site; do
    feed=$(curl -s "$site" | htmlq -b "$site" -a href 'link[type="application/rss+xml"]' | head -1)
    if [ -n "$feed" ]; then
        echo "$site -> $feed"
    fi
done
```

### Example 9: Compare Page Titles Across Languages

```bash
for lang in en de fr es ja; do
    title=$(curl -s "https://example.com/$lang/" | htmlq -t 'title')
    echo "$lang: $title"
done
```

### Example 10: Extract Structured Metadata into JSON

```bash
html=$(curl -s https://example.com/article)
title=$(echo "$html" | htmlq -t 'h1')
author=$(echo "$html" | htmlq -t '.author-name')
date=$(echo "$html" | htmlq -a datetime 'time')
description=$(echo "$html" | htmlq -a content 'meta[name="description"]')

printf '{"title":"%s","author":"%s","date":"%s","description":"%s"}\n' \
    "$title" "$author" "$date" "$description"
```

---

## Appendix A: HTML5 Void Elements

The following HTML elements are void elements (they cannot have children and do not have closing tags). htmlq and html5ever handle these according to the HTML5 specification:

| Element | Purpose |
|---|---|
| `<area>` | Image map area |
| `<base>` | Base URL for relative URLs |
| `<br>` | Line break |
| `<col>` | Table column |
| `<embed>` | Embedded content |
| `<hr>` | Horizontal rule |
| `<img>` | Image |
| `<input>` | Form input |
| `<link>` | External resource link |
| `<meta>` | Metadata |
| `<param>` | Object parameter |
| `<source>` | Media source |
| `<track>` | Text track |
| `<wbr>` | Word break opportunity |

These elements are serialized without closing tags in htmlq's HTML output (e.g., `<br>` rather than `<br></br>`).

---

## Appendix B: Common HTML Elements for Extraction

This appendix lists commonly targeted HTML elements and practical selectors for extracting information from them.

### Document Metadata

| Target | Selector | Flag |
|---|---|---|
| Page title | `title` | `-t` |
| Meta description | `meta[name="description"]` | `-a content` |
| Meta keywords | `meta[name="keywords"]` | `-a content` |
| Canonical URL | `link[rel="canonical"]` | `-a href` |
| Favicon | `link[rel="icon"]` | `-a href` |
| RSS feed | `link[type="application/rss+xml"]` | `-a href` |
| Charset | `meta[charset]` | `-a charset` |
| Viewport | `meta[name="viewport"]` | `-a content` |

### Open Graph Tags

| Target | Selector | Flag |
|---|---|---|
| OG title | `meta[property="og:title"]` | `-a content` |
| OG description | `meta[property="og:description"]` | `-a content` |
| OG image | `meta[property="og:image"]` | `-a content` |
| OG URL | `meta[property="og:url"]` | `-a content` |
| OG type | `meta[property="og:type"]` | `-a content` |
| OG site name | `meta[property="og:site_name"]` | `-a content` |

### Twitter Card Tags

| Target | Selector | Flag |
|---|---|---|
| Twitter card type | `meta[name="twitter:card"]` | `-a content` |
| Twitter title | `meta[name="twitter:title"]` | `-a content` |
| Twitter description | `meta[name="twitter:description"]` | `-a content` |
| Twitter image | `meta[name="twitter:image"]` | `-a content` |
| Twitter site | `meta[name="twitter:site"]` | `-a content` |

### Content Elements

| Target | Selector | Flag |
|---|---|---|
| All headings | `h1, h2, h3, h4, h5, h6` | `-t` |
| Paragraphs | `p` | `-t` |
| Links | `a[href]` | `-a href` |
| Images | `img[src]` | `-a src` |
| Image alt text | `img[alt]` | `-a alt` |
| Lists | `ul, ol` | (default) |
| List items | `li` | `-t` |
| Blockquotes | `blockquote` | `-t` |
| Code blocks | `pre code` | `-t` |
| Tables | `table` | (default) |
| Table headers | `th` | `-t` |
| Table cells | `td` | `-t` |

### Form Elements

| Target | Selector | Flag |
|---|---|---|
| Form action URLs | `form[action]` | `-a action` |
| Form methods | `form[method]` | `-a method` |
| Text inputs | `input[type="text"]` | `-a name` |
| Hidden inputs | `input[type="hidden"]` | `-a value` |
| Submit buttons | `input[type="submit"]` | `-a value` |
| Select dropdowns | `select` | `-a name` |
| Option values | `option` | `-a value` |
| Textarea content | `textarea` | `-t` |

### Embedded Resources

| Target | Selector | Flag |
|---|---|---|
| Stylesheets | `link[rel="stylesheet"]` | `-a href` |
| Scripts (external) | `script[src]` | `-a src` |
| Inline scripts | `script:not([src])` | `-t` |
| Inline styles | `style` | `-t` |
| Iframes | `iframe[src]` | `-a src` |
| Video sources | `video source` | `-a src` |
| Audio sources | `audio source` | `-a src` |

---

## Appendix C: The nth-child Formula Reference

The `:nth-child(An+B)` pseudo-class uses a formula to match elements at specific positions. This appendix provides a complete reference for the formula syntax.

### Formula Syntax

The general form is `An+B`, where:
- `A` is the step size (integer, can be negative)
- `n` is a counter that starts at 0 and increments by 1
- `B` is the offset (integer, can be negative)

The formula generates positions: B, A+B, 2A+B, 3A+B, ...
Only positions >= 1 are valid (elements are 1-indexed).

### Common Formulas

| Formula | Matching Positions | Description |
|---|---|---|
| `2n` | 2, 4, 6, 8, ... | Even elements |
| `2n+1` | 1, 3, 5, 7, ... | Odd elements |
| `even` | 2, 4, 6, 8, ... | Shorthand for 2n |
| `odd` | 1, 3, 5, 7, ... | Shorthand for 2n+1 |
| `3n` | 3, 6, 9, 12, ... | Every third element |
| `3n+1` | 1, 4, 7, 10, ... | Every third, starting from 1st |
| `3n+2` | 2, 5, 8, 11, ... | Every third, starting from 2nd |
| `4n` | 4, 8, 12, 16, ... | Every fourth element |
| `4n+1` | 1, 5, 9, 13, ... | Every fourth, starting from 1st |
| `n` | 1, 2, 3, 4, ... | All elements |
| `n+3` | 3, 4, 5, 6, ... | From 3rd onward |
| `n+5` | 5, 6, 7, 8, ... | From 5th onward |
| `-n+3` | 3, 2, 1 | First three elements |
| `-n+5` | 5, 4, 3, 2, 1 | First five elements |
| `5` | 5 | Only the 5th element |
| `1` | 1 | Only the 1st element |

### Formula Examples in htmlq

```bash
# Alternating table row colors (even rows)
htmlq 'tr:nth-child(even)' < page.html

# Every third list item
htmlq 'li:nth-child(3n)' < page.html

# First 10 results
htmlq '.result:nth-child(-n+10)' < page.html

# Results 11 and beyond
htmlq '.result:nth-child(n+11)' < page.html

# Results 5 through 10
# (combine nth-child with nth-last-child, or use head/tail)
htmlq '.result:nth-child(n+5)' < page.html | head -6

# Only the 3rd paragraph
htmlq 'p:nth-of-type(3)' < page.html

# Every other row in a table body, starting from the first
htmlq 'tbody tr:nth-child(odd)' < page.html
```

---

## Appendix D: Differences Between html5ever and Browser Parsing

While html5ever implements the HTML5 parsing algorithm, there are some practical differences between parsing HTML with htmlq/html5ever and viewing it in a browser:

1. **No JavaScript execution**: The browser executes JavaScript that can add, remove, or modify DOM elements. htmlq sees only the raw HTML source.

2. **No CSS processing**: The browser applies CSS to determine visibility, layout, and computed styles. htmlq does not process CSS (except for the `<style>` element's content, which is part of the DOM).

3. **No resource loading**: The browser loads external resources (images, scripts, stylesheets, iframes). htmlq does not fetch any external resources.

4. **No shadow DOM**: Web components may create shadow DOM trees that are not part of the main document. htmlq does not support shadow DOM.

5. **No template instantiation**: `<template>` elements in the source are parsed but their content is in a separate document fragment. htmlq matches against the main document tree.

6. **Identical tree construction**: For the raw HTML source, html5ever produces the same DOM tree as a browser would, because both implement the same specification. This includes:
   - Automatic insertion of `<html>`, `<head>`, and `<body>` elements
   - Foster parenting for misnested table content
   - Automatic closing of `<p>` before block-level elements
   - Insertion of `<tbody>` in tables
   - Handling of void elements
   - Error recovery for all types of malformed HTML

Understanding these differences is essential for effective use of htmlq with modern web pages that rely heavily on JavaScript rendering.
