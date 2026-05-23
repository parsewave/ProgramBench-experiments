# muffet -- Fast Website Link Checker

## Overview

muffet is a high-performance website link checker written in Go. It crawls a given website starting from a root URL, discovers all links on each page, and reports any that are broken. muffet leverages Go's goroutine-based concurrency model to check many links in parallel, making it significantly faster than sequential link checkers.

The core workflow is straightforward: you provide muffet with a starting URL, and it fetches that page, extracts all links (anchors, images, scripts, stylesheets, media sources), and then recursively crawls pages on the same domain while also probing external links for reachability. When it finishes, it reports every broken link it found, grouped by the source page where the link appeared.

muffet is designed for use in continuous integration pipelines, documentation validation, and general website maintenance. Its exit codes, JSON output mode, and flexible filtering make it easy to integrate into automated workflows.

### Key Features

- Concurrent link checking using Go goroutines with configurable parallelism
- Recursive crawling within the same domain
- External link validation without recursive crawling of external sites
- Support for multiple HTML element types (anchors, images, scripts, stylesheets, media)
- Fragment (anchor) checking to verify that `#id` targets exist on the destination page
- robots.txt and sitemap.xml support
- Configurable rate limiting and connection pooling
- HTTP proxy support
- Custom header injection
- JSON output for programmatic consumption
- URL exclusion via regular expression patterns
- TLS certificate verification control
- Colorized terminal output

---

## Installation

muffet is distributed as a single static binary compiled from Go source. It can be installed via Go's toolchain:

```
go install github.com/raviqqe/muffet/v2@latest
```

Alternatively, pre-built binaries may be available from the project's GitHub releases page. On macOS, it may also be installable via Homebrew:

```
brew install muffet
```

Docker images are also available for containerized usage:

```
docker run -it raviqqe/muffet https://example.com
```

---

## Command-Line Usage

### Positional Arguments

#### `<URL>`

The root URL to start checking from. This must be a valid HTTP or HTTPS URL including the scheme. muffet will begin by fetching this page, extracting all links, and then recursively following internal links while checking external links for reachability.

Examples of valid URLs:
- `https://example.com`
- `http://localhost:8080`
- `https://docs.example.com/en/latest/`
- `http://192.168.1.1:3000/docs`

The URL must include the scheme (`http://` or `https://`). Providing a bare hostname like `example.com` without a scheme will result in an error.

If the URL includes a path component (e.g., `https://example.com/docs/`), muffet begins crawling from that path. Internal link discovery and recursive crawling still operate based on the hostname, not the path prefix, so muffet may crawl pages outside the initial path but within the same domain.

---

## Options Reference

### `--buffer-size <NUM>`

Sets the size of the HTTP response buffer. This controls how many pages can be buffered in memory while waiting to be processed. A larger buffer size can improve throughput when there is high latency between fetching pages and processing them, at the cost of increased memory usage.

The buffer size determines how many HTTP responses muffet will hold in its internal channel before blocking on new fetches. When the buffer fills up, goroutines that have fetched pages will block until the processing goroutine consumes entries from the buffer.

For most websites, the default buffer size is sufficient. You may want to increase it when checking very large websites (tens of thousands of pages) to maintain maximum throughput, or decrease it on memory-constrained systems.

```
muffet --buffer-size 256 https://example.com
```

### `--color`

Forces colorized output even when stdout is not connected to a terminal. By default, muffet auto-detects whether it is writing to a terminal and enables colors accordingly. This flag overrides the auto-detection and always produces ANSI-colored output.

This is useful when piping muffet's output through tools that support ANSI codes (e.g., `less -R`) or when capturing output that will later be displayed in a terminal-aware viewer.

```
muffet --color https://example.com | less -R
```

### `--no-color`

Disables colorized output entirely. This overrides both the auto-detection and the `--color` flag. The output will contain no ANSI escape sequences.

Use this flag when redirecting output to a file or piping to tools that do not understand ANSI codes.

```
muffet --no-color https://example.com > results.txt
```

### `--concurrency <NUM>`

Sets the maximum number of concurrent goroutines used for fetching and checking links. This controls the overall parallelism of muffet's operation. Higher values result in faster checking but consume more system resources (memory, file descriptors, CPU).

The concurrency value determines how many HTTP requests can be in-flight simultaneously across all hosts. It works in conjunction with `--max-connections` and `--max-connections-per-host` to control resource usage.

If you set concurrency very high but max-connections-per-host very low, you may have many goroutines waiting for connections to specific hosts. Conversely, setting concurrency low negates the benefit of high connection limits.

```
muffet --concurrency 50 https://example.com
```

Recommended values:
- Small sites (< 100 pages): 10-20
- Medium sites (100-1000 pages): 20-50
- Large sites (1000+ pages): 50-200

Very high values (500+) may cause issues with file descriptor limits on some operating systems. If you encounter "too many open files" errors, either reduce concurrency or increase your system's file descriptor limit (`ulimit -n`).

### `-e, --exclude <PATTERN>`

Excludes URLs matching the given regular expression pattern from checking. Any URL (both the source page URL and the linked URL) that matches the pattern will be skipped entirely -- muffet will neither fetch it nor report it as broken.

The pattern uses Go's `regexp` syntax, which is based on RE2. This means it supports most common regex features but does not support backreferences or lookahead/lookbehind assertions.

This flag can be specified multiple times to provide multiple exclusion patterns. A URL is excluded if it matches any of the provided patterns.

```
# Exclude all URLs containing "logout"
muffet -e "logout" https://example.com

# Exclude external links to twitter.com
muffet -e "https?://twitter\\.com" https://example.com

# Exclude PDF files and a specific path
muffet -e "\\.pdf$" -e "/admin/" https://example.com

# Exclude all external links (only check internal)
muffet -e "^https?://(?!example\\.com)" https://example.com
```

Common exclusion patterns:

| Pattern | Effect |
|---------|--------|
| `\\.pdf$` | Skip PDF file links |
| `\\.zip$` | Skip ZIP archive links |
| `/api/` | Skip API endpoint links |
| `https?://twitter\\.com` | Skip Twitter links |
| `https?://linkedin\\.com` | Skip LinkedIn links |
| `mailto:` | Skip mailto links |
| `#` | Skip fragment-only links |
| `localhost` | Skip localhost links |
| `192\\.168\\.` | Skip private network links |

Note that the pattern is matched against the entire URL string. You do not need to anchor the pattern with `^` and `$` unless you want an exact match. A pattern like `twitter` will match any URL containing the substring "twitter".

### `--follow-robots-txt`

When this flag is enabled, muffet fetches and respects `robots.txt` files from each domain it encounters. Pages that are disallowed by `robots.txt` directives will be skipped during crawling.

muffet identifies itself with a user agent string when fetching `robots.txt`. The `robots.txt` rules that apply to muffet's user agent (or the wildcard `*` agent) will be honored.

This flag is useful when checking websites that use `robots.txt` to prevent crawlers from accessing certain sections. Without this flag, muffet ignores `robots.txt` entirely and will attempt to fetch all discovered URLs.

```
muffet --follow-robots-txt https://example.com
```

When `--follow-robots-txt` is active:
1. Before fetching any page on a new domain, muffet first fetches `https://domain/robots.txt`
2. The robots.txt content is parsed according to the Robots Exclusion Protocol
3. Each URL is checked against the parsed rules before fetching
4. Disallowed URLs are silently skipped (not reported as errors)

### `--follow-sitemap-xml`

When enabled, muffet reads `sitemap.xml` files and adds the URLs found in them to the crawl queue. This ensures that pages listed in the sitemap are checked even if they are not linked from any other page.

Sitemaps can reference other sitemaps (sitemap index files), and muffet will follow these references recursively. Both plain XML sitemaps and gzipped sitemaps are supported.

```
muffet --follow-sitemap-xml https://example.com
```

This flag is particularly useful for:
- Catching orphan pages that exist but are not linked from the main navigation
- Ensuring all pages in a large site are checked, even those only accessible through the sitemap
- Validating that the sitemap itself contains valid, working URLs

### `-H, --header <HEADER>`

Adds a custom HTTP header to every request muffet makes. The header must be in the format `"Name: Value"`. This flag can be specified multiple times to add multiple headers.

```
# Add an authorization header
muffet -H "Authorization: Bearer token123" https://example.com

# Add multiple headers
muffet -H "Authorization: Bearer token123" -H "Accept-Language: en-US" https://example.com

# Add a custom user agent
muffet -H "User-Agent: MyBot/1.0" https://example.com

# Add a cookie
muffet -H "Cookie: session=abc123; user=john" https://example.com
```

Common use cases for custom headers:
- **Authentication**: Pass API keys, bearer tokens, or basic auth credentials
- **Session cookies**: Check authenticated pages by passing session cookies
- **Accept headers**: Control content negotiation (e.g., request JSON vs HTML)
- **Custom user agent**: Identify muffet differently to web servers
- **Cache control**: Force fresh responses with `Cache-Control: no-cache`
- **Language selection**: Request specific language versions with `Accept-Language`

The headers are added to every request, including requests to external domains. Be cautious about sending authentication tokens to external sites. If you need to restrict headers to specific domains, consider using the `--exclude` flag to skip external domains entirely.

### `--ignore-fragments`

Disables fragment (anchor) checking. By default, when muffet encounters a URL with a fragment (the `#` portion), it not only checks that the page loads successfully but also verifies that an HTML element with a matching `id` attribute exists on the destination page.

With `--ignore-fragments`, muffet only checks that the page itself is reachable. It does not inspect the HTML content for matching element IDs. This can speed up checking and reduce false positives on pages where fragments are handled dynamically by JavaScript.

```
muffet --ignore-fragments https://example.com
```

Fragment checking works as follows (when NOT ignored):
1. muffet fetches the destination page
2. It parses the HTML response
3. It searches for an element with an `id` attribute matching the fragment
4. If no matching element is found, the link is reported as broken

Reasons to use `--ignore-fragments`:
- Single-page applications (SPAs) where fragments are handled by client-side routing
- Pages that use JavaScript to dynamically generate anchor targets
- Reducing false positives when fragment targets are created at runtime
- Improving checking speed by skipping HTML parsing for fragment validation

### `--json`

Outputs results in JSON format instead of the default human-readable format. This is useful for programmatic processing of results, integration with other tools, or storage in structured log systems.

```
muffet --json https://example.com
```

The JSON output format produces a JSON array where each element represents a page with broken links. Each element contains the source URL and a list of broken links found on that page, with their URLs and error descriptions.

Example JSON output:

```json
[
  {
    "url": "https://example.com/page1",
    "links": [
      {
        "url": "https://example.com/missing",
        "error": "404"
      },
      {
        "url": "https://example.com/slow",
        "error": "timeout"
      }
    ]
  },
  {
    "url": "https://example.com/page2",
    "links": [
      {
        "url": "https://external.com/gone",
        "error": "410"
      }
    ]
  }
]
```

JSON output is particularly useful for:
- Parsing results in CI/CD pipelines with `jq`
- Feeding results into dashboards or monitoring systems
- Comparing results between runs to detect regressions
- Generating reports in other formats (HTML, CSV, etc.)

### `--max-connections <NUM>`

Sets the maximum total number of TCP connections muffet will maintain simultaneously across all hosts. This is a global limit that caps the total number of open sockets.

This differs from `--concurrency` in that concurrency controls the number of goroutines (logical threads), while max-connections controls the actual number of network connections. A single goroutine may be waiting for a connection from the pool, so you can have more goroutines than connections.

```
muffet --max-connections 100 https://example.com
```

If you are running muffet on a system with limited file descriptors or behind a firewall that limits concurrent connections, reducing this value can help avoid errors. Conversely, increasing it can improve throughput when checking sites with many external links across different hosts.

### `--max-connections-per-host <NUM>`

Sets the maximum number of concurrent TCP connections to any single host. This prevents muffet from overwhelming individual web servers with too many simultaneous requests.

This is an important courtesy setting when checking live websites. Many web servers will rate-limit or block clients that open too many concurrent connections. By default, muffet limits connections per host to a reasonable value, but you can adjust it based on the target server's capacity.

```
# Be gentle with external servers
muffet --max-connections-per-host 2 https://example.com

# Allow more connections to a high-capacity server
muffet --max-connections-per-host 10 https://example.com
```

This setting only affects the number of simultaneous connections to a single host. The total number of connections across all hosts is controlled by `--max-connections`.

Guidelines for setting this value:
- **1-2**: Very conservative; use for checking sites you do not control and want to be respectful to
- **3-5**: Moderate; suitable for most external websites
- **5-10**: Aggressive; use only for servers you control or that can handle the load
- **10+**: Very aggressive; only for high-capacity servers on local networks

### `--max-redirections <NUM>`

Sets the maximum number of HTTP redirections muffet will follow for a single URL before reporting an error. The default is 64.

When muffet encounters an HTTP redirect response (301, 302, 307, 308), it follows the redirect to the new location. If the redirect chain exceeds this limit, muffet reports the URL as broken with a "too many redirections" error.

```
muffet --max-redirections 10 https://example.com
```

Lowering this value helps detect redirect loops more quickly. A redirect loop occurs when URL A redirects to URL B, which redirects back to URL A (or through a longer chain that eventually loops). The default of 64 is generous enough to handle legitimate redirect chains while still catching loops.

Common redirect scenarios:
- HTTP to HTTPS upgrades (1 redirect)
- www to non-www canonicalization (1 redirect)
- URL shortener chains (2-5 redirects)
- Legacy URL migrations (1-3 redirects)
- Locale/language detection redirects (1-2 redirects)

Setting this to a very low value (e.g., 1) will cause legitimate redirects to be reported as errors. A value of 5-10 is sufficient for most real-world websites.

### `--max-response-body-size <NUM>`

Sets the maximum response body size in bytes that muffet will read. Responses larger than this limit are truncated or skipped. This prevents muffet from consuming excessive memory when encountering very large files (e.g., large downloads, media files).

```
# Limit response body to 10MB
muffet --max-response-body-size 10485760 https://example.com
```

This setting is useful when checking sites that link to large binary files, video content, or data downloads. Without a limit, muffet might attempt to read very large responses into memory, leading to high memory usage.

Note that even with this limit, muffet still makes the HTTP request and receives the response headers. The limit only applies to how much of the response body is read. The link is still checked for reachability -- the status code and headers are processed regardless of the body size limit.

### `--one-page-only`

Restricts muffet to checking links only on the initial page specified by the root URL. It does not recursively crawl to other pages on the same domain.

```
muffet --one-page-only https://example.com
```

With this flag:
1. muffet fetches the root URL
2. It extracts all links from that page
3. It checks each extracted link for reachability (fetches them to verify they return a successful status code)
4. It does NOT follow internal links to discover additional pages

This is useful for:
- Quick spot-checks of a single page
- Checking a specific landing page or blog post
- Reducing check time when you only care about one page
- Debugging link issues on a particular page without the overhead of a full site crawl

### `--proxy <URL>`

Routes all HTTP requests through the specified HTTP proxy. The proxy URL must include the scheme (http:// or https://).

```
muffet --proxy http://proxy.example.com:8080 https://example.com
```

All requests -- both internal page fetches and external link checks -- are routed through the proxy. This includes the initial root URL fetch, all recursive crawling, and all external link verification.

Use cases for proxy support:
- Corporate networks that require HTTP proxy access
- Debugging with an intercepting proxy (e.g., mitmproxy, Fiddler, Charles)
- Routing through a VPN endpoint
- Testing from different geographic locations via geo-distributed proxies
- Rate limiting at the proxy level

### `--rate-limit <NUM>`

Sets the maximum number of HTTP requests per second. This provides global rate limiting across all hosts to prevent muffet from generating excessive traffic.

```
# Maximum 10 requests per second
muffet --rate-limit 10 https://example.com
```

Rate limiting is applied globally, not per host. If you set a rate limit of 10 and are checking links across 5 different hosts, each host will receive an average of 2 requests per second (though the actual distribution depends on the link mix).

Rate limiting is particularly important when:
- Checking live production websites that might be affected by the load
- Avoiding triggering rate limiters or WAFs (Web Application Firewalls)
- Running muffet as a scheduled job where speed is not critical
- Checking websites hosted on shared infrastructure

The rate limit interacts with concurrency settings. Even if you set concurrency to 100, a rate limit of 5 means muffet will only initiate 5 new requests per second. The goroutines will wait for their turn, effectively throttling the overall checking speed.

### `--skip-tls-verification`

Disables TLS certificate verification for HTTPS connections. When this flag is set, muffet accepts any TLS certificate regardless of its validity, including self-signed certificates, expired certificates, and certificates with mismatched hostnames.

```
muffet --skip-tls-verification https://staging.example.com
```

**WARNING**: This flag reduces security. Only use it in controlled environments such as:
- Testing against staging servers with self-signed certificates
- Checking internal sites with corporate CAs not in the system trust store
- Development environments with local HTTPS servers
- Sites behind TLS-terminating proxies with internal certificates

Do not use this flag when checking production websites over the public internet, as it exposes the connection to potential man-in-the-middle attacks.

### `-t, --timeout <SECONDS>`

Sets the timeout for each individual HTTP request in seconds. The default is 10 seconds. If a request (including connection establishment, TLS handshake, and response reading) takes longer than this timeout, it is aborted and reported as a timeout error.

```
# Set timeout to 30 seconds for slow servers
muffet -t 30 https://example.com

# Set a very short timeout to find slow-loading pages
muffet -t 3 https://example.com
```

The timeout applies to each individual HTTP request, not to the entire crawl. If a redirect chain involves 3 requests, each request has its own independent timeout.

Considerations for setting the timeout:
- **Short (1-3 seconds)**: Identifies very slow pages; may produce false positives on legitimate but slow pages
- **Medium (5-15 seconds)**: Good default range for most websites
- **Long (30-60 seconds)**: Use when checking servers known to be slow, or when checking large files
- **Very long (60+ seconds)**: Only for exceptional cases; most legitimate HTTP servers respond within 30 seconds

If you frequently see timeout errors, consider:
1. Increasing the timeout value
2. Checking if the target server is rate-limiting your requests (try reducing concurrency or adding rate limiting)
3. Checking your network connectivity
4. Verifying that the target server is actually running

### `-v, --verbose`

Enables verbose output. In verbose mode, muffet shows all checked URLs, including those that return successful status codes. Without this flag, muffet only reports broken links.

```
muffet -v https://example.com
```

Verbose output is useful for:
- Debugging: seeing exactly which URLs muffet checks
- Auditing: getting a complete inventory of all links on a site
- Verifying: confirming that specific pages are being checked
- Troubleshooting exclusion patterns: confirming that expected URLs are being excluded

In verbose mode, successful links are shown alongside broken ones, typically with their HTTP status code (200, 301, etc.) or a success indicator.

---

## Crawling Behavior

### How muffet Discovers Links

muffet starts from the root URL and performs a breadth-first crawl of the website. At each page, it extracts links from multiple HTML element types:

#### Anchor Links (`<a href="...">`)

Standard hyperlinks are the primary source of URLs for crawling. muffet extracts the `href` attribute from every `<a>` element in the page. These links may point to internal pages (which are added to the crawl queue), external pages (which are checked for reachability), or non-HTTP resources (which may be skipped).

#### Image Sources (`<img src="...">`)

Image tags have their `src` attributes extracted and checked. This validates that all images referenced on the page are actually accessible. Broken image links are a common website issue and muffet catches them effectively.

#### Script Sources (`<script src="...">`)

External JavaScript files referenced via `<script src="...">` are checked for accessibility. This catches broken references to JavaScript libraries, CDN resources, or application scripts.

#### Stylesheet Links (`<link href="...">`)

CSS stylesheets and other linked resources (icons, alternate pages, etc.) referenced via `<link href="...">` are checked. This includes:
- CSS files (`<link rel="stylesheet" href="...">`)
- Favicons (`<link rel="icon" href="...">`)
- Canonical URLs (`<link rel="canonical" href="...">`)
- Alternate language pages (`<link rel="alternate" hreflang="..." href="...">`)

#### Media Sources (`<source src="...">`)

HTML5 media elements (`<video>`, `<audio>`) may contain `<source>` child elements. muffet checks the `src` attribute of these elements to verify that media files are accessible.

#### Srcset Attributes

The `srcset` attribute (used on `<img>` and `<source>` elements for responsive images) contains one or more image URLs with optional size descriptors. muffet parses the `srcset` attribute, extracts all URLs, and checks each one.

Example of an element with srcset:
```html
<img srcset="small.jpg 300w, medium.jpg 600w, large.jpg 1200w"
     src="medium.jpg" alt="Example">
```

muffet would check `small.jpg`, `medium.jpg`, and `large.jpg` from the srcset, as well as `medium.jpg` from the src attribute.

### Internal vs. External Links

muffet distinguishes between internal and external links based on the hostname:

- **Internal links**: URLs whose hostname matches the root URL's hostname. These are crawled recursively -- muffet fetches the page, extracts links, and adds newly discovered internal pages to the crawl queue.
- **External links**: URLs whose hostname differs from the root URL's hostname. These are checked for reachability (muffet fetches them and checks the status code) but are NOT crawled recursively. muffet does not extract links from external pages.

This distinction is based strictly on the hostname. Subdomains are treated as different hosts. For example, if you start crawling at `https://www.example.com`, links to `https://docs.example.com` are treated as external.

### URL Resolution

muffet resolves relative URLs against the base URL of the page where they are found. This means:

- A link `href="/about"` on page `https://example.com/docs/intro` resolves to `https://example.com/about`
- A link `href="next"` on page `https://example.com/docs/intro` resolves to `https://example.com/docs/next`
- A link `href="../index.html"` on page `https://example.com/docs/intro` resolves to `https://example.com/index.html`
- A link `href="//cdn.example.com/file.js"` inherits the scheme from the current page

### URL Normalization

muffet normalizes URLs to avoid checking the same resource multiple times:

- Trailing slashes are handled consistently
- URL encoding is normalized (e.g., `%20` vs space)
- Default ports are removed (`:80` for HTTP, `:443` for HTTPS)
- Fragment identifiers are separated from the base URL for de-duplication purposes (the base URL is checked once, but multiple fragments may be verified)

### Crawl Queue and Deduplication

muffet maintains a set of already-visited URLs to avoid checking the same URL twice. When a new URL is discovered:

1. The URL is resolved to an absolute URL
2. It is checked against the exclusion patterns
3. It is checked against the set of already-visited URLs
4. If it passes both checks, it is added to the crawl queue

This deduplication happens at the URL level, meaning that the same URL linked from multiple pages is only fetched once. However, if it is broken, it may be reported under each source page where it was found.

### Skipped URL Schemes

muffet only checks HTTP and HTTPS URLs. The following URL schemes are silently skipped:

- `mailto:` -- Email links
- `javascript:` -- Inline JavaScript
- `data:` -- Data URIs (inline content)
- `tel:` -- Telephone links
- `ftp:` / `ftps:` -- FTP links
- Other non-HTTP schemes

These are not reported as errors; they are simply ignored during link extraction.

---

## Output Format

### Default Human-Readable Output

muffet's default output groups broken links by the source page where they were found. Each group starts with the source page URL on its own line, followed by indented lines showing the error and the broken link URL:

```
https://example.com/page1
        404     https://example.com/missing-page
        timeout https://example.com/slow-page
https://example.com/page2
        403     https://example.com/forbidden
        200 (fragment not found) https://example.com/page3#nonexistent
```

The indentation uses a tab character. The error description is followed by a tab and then the broken link URL.

Error descriptions include:
- HTTP status codes (`404`, `403`, `500`, etc.)
- Network errors (`timeout`, `connection refused`, `DNS lookup failed`)
- TLS errors (`certificate expired`, `certificate signed by unknown authority`)
- Fragment errors when a page loads successfully but the fragment target does not exist
- Redirect errors (`too many redirections`)

### Colorized Output

When connected to a terminal (and `--no-color` is not specified), muffet colorizes its output:
- Source page URLs are displayed in one color
- Error codes and messages are highlighted (typically in red or yellow)
- Successful checks (in verbose mode) use a different color (typically green)

Colors follow standard ANSI escape sequences and work in most modern terminals.

### JSON Output

With `--json`, muffet produces a JSON array. Each element is an object with two fields:

- `url`: The source page URL (string)
- `links`: An array of objects, each with:
  - `url`: The broken link URL (string)
  - `error`: The error description (string)

```json
[
  {
    "url": "https://example.com/page1",
    "links": [
      {
        "url": "https://example.com/missing-page",
        "error": "404"
      },
      {
        "url": "https://example.com/slow-page",
        "error": "timeout"
      }
    ]
  }
]
```

When there are no broken links, muffet outputs an empty JSON array `[]` (with `--json` flag) and exits with code 0.

### Verbose Output

With `-v` or `--verbose`, muffet also outputs information about successfully checked links. This provides a complete picture of all links discovered and their status. In verbose mode, the output includes both broken and working links, each with their status or result.

---

## Concurrency Model

### Goroutine Architecture

muffet uses Go's goroutine model for concurrent link checking. The architecture consists of several cooperating components:

1. **Crawler goroutines**: Fetch pages and extract links. When a page is fetched, its HTML is parsed, and all discovered links are sent to a central coordinator.

2. **Checker goroutines**: Receive URLs to check and perform HTTP requests to verify reachability. Multiple checker goroutines run in parallel, bounded by the `--concurrency` flag.

3. **Coordinator**: Manages the crawl queue, deduplication, and result collection. It distributes work to checker goroutines and collects results.

4. **Connection pool**: Manages TCP connections to various hosts. The pool enforces `--max-connections` and `--max-connections-per-host` limits.

### Concurrency Controls

muffet provides four levels of concurrency control:

#### `--concurrency`

Controls the number of goroutines actively performing work. This is the primary parallelism knob. Each goroutine can fetch a page, parse it, and extract links.

#### `--max-connections`

Controls the total number of TCP connections in the connection pool. This is a hard limit on the number of simultaneous network connections, regardless of how many goroutines are active. When all connections are in use, goroutines block until a connection becomes available.

#### `--max-connections-per-host`

Controls the maximum number of connections to any single host. This prevents muffet from overwhelming individual servers. Even if the total connection pool has capacity, a goroutine will block if the per-host limit is reached for its target host.

#### `--rate-limit`

Controls the rate of new HTTP requests globally. Even if goroutines and connections are available, muffet will not exceed this rate. Rate limiting uses a token bucket algorithm that allows bursts up to the configured rate while maintaining a steady average.

### How the Controls Interact

These four settings form a hierarchy of constraints. The effective throughput is determined by the most restrictive setting:

```
Effective rate = min(
    concurrency (goroutines available),
    max-connections (connections available),
    sum of max-connections-per-host (connections available per host),
    rate-limit (requests per second)
)
```

For example, if you set:
- `--concurrency 100`
- `--max-connections 50`
- `--max-connections-per-host 5`
- `--rate-limit 10`

Then even though you have 100 goroutines and 50 connections available, you will never exceed 10 requests per second due to the rate limit. And no single host will receive more than 5 concurrent requests.

### Recommended Configurations

#### Gentle Checking (Production Sites)

```
muffet --concurrency 10 --max-connections-per-host 2 --rate-limit 5 https://example.com
```

Low concurrency, strict per-host limits, and rate limiting to be respectful to production servers.

#### Fast Internal Checking (Development/Staging)

```
muffet --concurrency 100 --max-connections-per-host 10 https://staging.example.com
```

Higher concurrency and per-host limits for servers you control.

#### Balanced Checking (Mixed Internal/External)

```
muffet --concurrency 50 --max-connections-per-host 3 --rate-limit 20 https://example.com
```

Moderate concurrency with per-host limits and rate limiting to balance speed with politeness for external servers.

---

## Exclusion Patterns

### Pattern Syntax

muffet uses Go's `regexp` package for URL exclusion, which implements the RE2 regular expression syntax. RE2 is designed to be safe and efficient with guaranteed linear-time matching.

Key features of Go's regexp syntax:

| Syntax | Meaning |
|--------|---------|
| `.` | Any character |
| `*` | Zero or more of the preceding element |
| `+` | One or more of the preceding element |
| `?` | Zero or one of the preceding element |
| `^` | Start of string |
| `$` | End of string |
| `[abc]` | Character class |
| `[^abc]` | Negated character class |
| `(abc)` | Capturing group |
| `(?:abc)` | Non-capturing group |
| `a\|b` | Alternation (a or b) |
| `\\.` | Literal dot |
| `\\d` | Digit character |
| `\\w` | Word character |
| `\\s` | Whitespace character |

Notable limitations (compared to PCRE):
- No backreferences (`\1`, `\2`)
- No lookahead (`(?=...)`, `(?!...)`)
- No lookbehind (`(?<=...)`, `(?<!...)`)
- No atomic groups
- No possessive quantifiers

### Pattern Matching Behavior

The exclusion pattern is matched against the full URL string, including the scheme, host, path, query string, and fragment. The pattern does not need to match the entire URL; a partial match anywhere in the URL string is sufficient for exclusion.

For example, the pattern `example` would match all of these URLs:
- `https://example.com/page`
- `https://foo.com/example/page`
- `https://foo.com/page?ref=example`

### Common Exclusion Strategies

#### Exclude Specific Domains

```
# Exclude a single domain
muffet -e "https?://(www\\.)?twitter\\.com" https://example.com

# Exclude multiple social media domains
muffet \
  -e "https?://(www\\.)?twitter\\.com" \
  -e "https?://(www\\.)?facebook\\.com" \
  -e "https?://(www\\.)?linkedin\\.com" \
  -e "https?://(www\\.)?instagram\\.com" \
  https://example.com
```

#### Exclude File Types

```
# Exclude PDF files
muffet -e "\\.pdf$" https://example.com

# Exclude multiple file types
muffet -e "\\.(pdf|zip|tar\\.gz|dmg|exe)$" https://example.com
```

#### Exclude URL Paths

```
# Exclude admin section
muffet -e "/admin/" https://example.com

# Exclude API endpoints
muffet -e "/api/v[0-9]+/" https://example.com

# Exclude user profile pages
muffet -e "/users/[^/]+" https://example.com
```

#### Exclude Query Parameters

```
# Exclude URLs with tracking parameters
muffet -e "\\?.*utm_" https://example.com

# Exclude paginated pages beyond page 5
muffet -e "page=[6-9]|page=[0-9]{2,}" https://example.com
```

#### Exclude Everything External

```
# Only check internal links (skip all external)
muffet -e "^https?://(?!example\\.com)" https://example.com
```

Note: Since Go's regexp does not support negative lookahead (`(?!...)`), you may need alternative approaches depending on the exact behavior desired.

---

## Header Injection

### Use Cases

Custom headers allow muffet to access pages that require authentication or special request parameters.

#### Basic Authentication

```
# Using Authorization header with base64-encoded credentials
muffet -H "Authorization: Basic dXNlcjpwYXNz" https://example.com
```

The value `dXNlcjpwYXNz` is the base64 encoding of `user:pass`.

#### Bearer Token Authentication

```
muffet -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." https://example.com
```

This is common for APIs and single-page applications that use JWT tokens.

#### API Key Authentication

```
muffet -H "X-API-Key: your-api-key-here" https://api.example.com
```

#### Cookie-Based Sessions

```
muffet -H "Cookie: session_id=abc123; csrf_token=xyz789" https://example.com
```

To obtain the session cookie, you would typically log in via a browser or curl first, then copy the cookie value.

#### Content Negotiation

```
# Request JSON responses
muffet -H "Accept: application/json" https://api.example.com

# Request a specific API version
muffet -H "Accept: application/vnd.example.v2+json" https://api.example.com
```

#### Custom User Agent

```
# Identify as a specific bot
muffet -H "User-Agent: MySiteChecker/1.0 (https://example.com/bot)" https://example.com
```

Some websites block requests from unknown user agents. Setting a descriptive user agent can help avoid blocks.

### Security Considerations

Custom headers are sent with every request, including requests to external domains. This means:

- **Authentication tokens** will be sent to external sites. If you are checking a site with links to external domains, your credentials will be leaked to those external domains.
- **Session cookies** will be sent to external sites, potentially allowing session hijacking.
- **API keys** will be sent to external sites.

To mitigate this, consider:
1. Using `--exclude` to skip external links when using authentication headers
2. Using short-lived or read-only tokens
3. Using tokens scoped to the specific domain being checked
4. Revoking tokens after the check completes

---

## Fragment Checking

### How Fragment Checking Works

URL fragments (the portion after `#`) reference specific elements within an HTML page. For example, `https://example.com/docs#installation` links to the element with `id="installation"` on the `/docs` page.

muffet's fragment checking process:

1. Parse the URL to extract the fragment identifier
2. Fetch the target page (the URL without the fragment)
3. Parse the HTML response
4. Search for an element with a matching `id` attribute
5. If no match is found, also check for `<a name="...">` elements (legacy anchor syntax)
6. Report the link as broken if no matching element exists

### Fragment Checking Examples

Given this HTML at `https://example.com/docs`:

```html
<h2 id="installation">Installation</h2>
<h2 id="usage">Usage</h2>
<h3 id="basic-usage">Basic Usage</h3>
<a name="legacy-anchor">Legacy Section</a>
```

The following links would be valid:
- `https://example.com/docs#installation`
- `https://example.com/docs#usage`
- `https://example.com/docs#basic-usage`
- `https://example.com/docs#legacy-anchor`

The following would be reported as broken:
- `https://example.com/docs#setup` (no element with id="setup")
- `https://example.com/docs#Install` (case-sensitive; does not match "installation")

### When to Disable Fragment Checking

Use `--ignore-fragments` when:

- **Single-page applications**: SPAs use fragments for client-side routing (e.g., `#/dashboard`, `#/settings`). These fragments are handled by JavaScript and do not correspond to HTML element IDs.
- **Dynamic content**: Pages where anchor targets are generated dynamically by JavaScript after the initial HTML load.
- **Scroll-to-top links**: Some sites use `#` or `#top` as links that do not correspond to specific element IDs.
- **Third-party pages**: External pages where you cannot control the fragment targets and they frequently change.
- **Performance**: Fragment checking requires parsing HTML content. Disabling it reduces processing time.

---

## Redirect Handling

### HTTP Redirect Status Codes

muffet follows standard HTTP redirect responses:

| Status Code | Name | Meaning |
|-------------|------|---------|
| 301 | Moved Permanently | Resource has been permanently moved. Clients should update bookmarks. |
| 302 | Found | Resource temporarily located elsewhere. Original URL should still be used. |
| 307 | Temporary Redirect | Like 302, but the request method must not change. |
| 308 | Permanent Redirect | Like 301, but the request method must not change. |

### Redirect Following Behavior

When muffet encounters a redirect response:

1. It reads the `Location` header from the response
2. It resolves the location URL (which may be relative) against the request URL
3. It makes a new request to the resolved URL
4. This process repeats until a non-redirect response is received or the redirect limit is hit

Each step in the redirect chain counts toward the `--max-redirections` limit. If the chain exceeds the limit, the original URL is reported as broken.

### Redirect Chains

A redirect chain is a sequence of redirects. For example:

```
https://example.com/old
  -> 301 -> https://example.com/new
  -> 302 -> https://example.com/current
  -> 200 OK
```

This is a chain of length 2 (two redirects). muffet follows both redirects and considers the link valid since the final response is 200 OK.

### Redirect Loops

A redirect loop occurs when the redirect chain leads back to a previously visited URL:

```
https://example.com/a
  -> 302 -> https://example.com/b
  -> 302 -> https://example.com/a   (loop!)
```

muffet detects redirect loops and reports them as errors when the `--max-redirections` limit is exceeded.

### Cross-Domain Redirects

Redirects can cross domain boundaries. For example, `http://old-domain.com/page` might redirect to `https://new-domain.com/page`. muffet follows these cross-domain redirects. However, the final destination is treated according to its domain:
- If it matches the root domain, the page is crawled for additional links
- If it is external, only the reachability is verified

---

## TLS Handling

### Certificate Validation

By default, muffet validates TLS certificates according to the system's certificate trust store. This includes checking:

- **Certificate chain**: The certificate must chain to a trusted root CA
- **Expiration**: The certificate must not be expired or not-yet-valid
- **Hostname matching**: The certificate's Common Name (CN) or Subject Alternative Names (SANs) must match the requested hostname
- **Revocation**: Depending on the Go runtime configuration, certificate revocation may also be checked

### TLS Error Types

When TLS validation fails, muffet reports specific error messages:

| Error | Description |
|-------|-------------|
| `x509: certificate signed by unknown authority` | The certificate's issuer is not in the system trust store |
| `x509: certificate has expired or is not yet valid` | The certificate's validity period does not include the current time |
| `x509: certificate is valid for X, not Y` | The certificate does not match the requested hostname |
| `x509: cannot validate certificate for X because it doesn't contain any IP SANs` | IP address used but certificate lacks IP SANs |
| `tls: handshake failure` | General TLS handshake failure |

### Skipping TLS Verification

When `--skip-tls-verification` is used, all TLS certificate validation is disabled. muffet will connect to any HTTPS server regardless of its certificate. The connection is still encrypted, but the identity of the server is not verified.

This is equivalent to setting `InsecureSkipVerify: true` in Go's `tls.Config`.

---

## Proxy Support

### HTTP Proxy Configuration

The `--proxy` flag configures muffet to route all HTTP and HTTPS requests through an HTTP proxy server.

```
muffet --proxy http://proxy.example.com:8080 https://example.com
```

The proxy URL format is:
```
http://[user:password@]host:port
```

Examples:
```
# Simple proxy
muffet --proxy http://proxy.local:3128 https://example.com

# Proxy with authentication
muffet --proxy http://user:pass@proxy.local:3128 https://example.com
```

### How Proxy Routing Works

When a proxy is configured:

1. For HTTP requests: muffet sends the full URL in the HTTP request line to the proxy, and the proxy forwards the request to the destination server.
2. For HTTPS requests: muffet sends a CONNECT request to the proxy, establishing a tunnel to the destination server, and then performs the TLS handshake through the tunnel.

### Use Cases

- **Corporate networks**: Many corporate environments require HTTP proxy access for external network resources
- **Debugging**: Route traffic through an intercepting proxy like mitmproxy, Burp Suite, or Charles to inspect request/response details
- **Geographic testing**: Route through proxies in different regions to test geo-restricted content
- **Privacy**: Hide muffet's source IP address behind a proxy

---

## robots.txt Support

### Robots Exclusion Protocol

The Robots Exclusion Protocol (robots.txt) is a standard that allows website owners to indicate which parts of their site should not be accessed by web crawlers. The file is located at the root of the website (`/robots.txt`).

### How muffet Handles robots.txt

When `--follow-robots-txt` is enabled:

1. **Discovery**: Before crawling any page on a new domain, muffet first fetches `https://domain/robots.txt`
2. **Parsing**: The robots.txt file is parsed according to the standard protocol, extracting `User-agent`, `Disallow`, and `Allow` directives
3. **Matching**: muffet matches its user agent against the rules. If no specific rule matches muffet's user agent, the wildcard (`*`) rules are used
4. **Enforcement**: URLs that are disallowed by the matching rules are skipped silently
5. **Caching**: The robots.txt file is cached per domain and only fetched once

### Example robots.txt

```
User-agent: *
Disallow: /admin/
Disallow: /private/
Disallow: /api/

User-agent: muffet
Disallow: /slow-section/
Allow: /admin/public/
```

With `--follow-robots-txt`, muffet would skip `/admin/`, `/private/`, `/api/`, and `/slow-section/` pages, but would be allowed to access `/admin/public/`.

### Interaction with Exclusion Patterns

robots.txt exclusions and `--exclude` pattern exclusions are independent. A URL is skipped if it matches either:
- Any `--exclude` pattern, OR
- Any robots.txt Disallow directive (when `--follow-robots-txt` is enabled)

### When to Use robots.txt Support

- **Respecting website owners' wishes**: Enable this when checking third-party websites to be a polite crawler
- **Avoiding honeypots**: Some websites use robots.txt to mark crawler traps. Respecting these directives avoids wasting time on trap pages
- **Reducing load**: robots.txt often disallows resource-intensive pages (search, admin panels). Respecting these reduces load on the target server

---

## sitemap.xml Support

### Sitemap Protocol

Sitemaps are XML files that list the URLs on a website, along with optional metadata (last modification date, change frequency, priority). They help crawlers discover pages that might not be reachable through link-following alone.

### How muffet Handles sitemap.xml

When `--follow-sitemap-xml` is enabled:

1. **Fetching**: muffet fetches `https://domain/sitemap.xml`
2. **Parsing**: The XML content is parsed to extract URLs
3. **Sitemap indexes**: If the sitemap is a sitemap index (a sitemap that references other sitemaps), muffet follows those references recursively
4. **URL addition**: All discovered URLs are added to the crawl queue alongside URLs discovered through link extraction
5. **Deduplication**: URLs from the sitemap are subject to the same deduplication as link-discovered URLs

### Sitemap Formats

muffet handles standard sitemap XML format:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://example.com/page1</loc>
    <lastmod>2024-01-15</lastmod>
  </url>
  <url>
    <loc>https://example.com/page2</loc>
  </url>
</urlset>
```

And sitemap index format:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap>
    <loc>https://example.com/sitemap-pages.xml</loc>
  </sitemap>
  <sitemap>
    <loc>https://example.com/sitemap-posts.xml</loc>
  </sitemap>
</sitemapindex>
```

### Benefits of Sitemap Support

- **Complete coverage**: Discover orphan pages not linked from any other page
- **Sitemap validation**: Verify that all URLs listed in the sitemap are actually working
- **Deep page discovery**: Find pages buried deep in the site structure that might not be reached through limited-depth crawling

---

## Exit Codes

muffet uses specific exit codes to indicate the outcome of the check:

| Exit Code | Meaning |
|-----------|---------|
| 0 | Success: all checked links are valid |
| 1 | Failure: one or more broken links were found |
| 2 | Error: muffet encountered an error that prevented it from running (invalid arguments, network failure on root URL, etc.) |

### Exit Code Usage in Scripts

```bash
#!/bin/bash

muffet https://example.com
EXIT_CODE=$?

case $EXIT_CODE in
  0)
    echo "All links are valid"
    ;;
  1)
    echo "Broken links found"
    ;;
  2)
    echo "muffet encountered an error"
    ;;
esac
```

### CI/CD Integration with Exit Codes

The exit codes make muffet suitable for CI/CD pipelines:

```yaml
# GitHub Actions example
- name: Check links
  run: muffet https://example.com
  # The step fails if muffet returns non-zero
```

A non-zero exit code causes the CI step to fail, which can block merges or deployments when broken links are detected.

---

## Error Types

### HTTP Status Code Errors

When a link returns a non-successful HTTP status code, muffet reports the status code as the error. The following categories of status codes are considered errors:

#### 4xx Client Errors

| Status Code | Name | Common Cause |
|-------------|------|-------------|
| 400 | Bad Request | Malformed URL or request |
| 401 | Unauthorized | Authentication required |
| 403 | Forbidden | Access denied |
| 404 | Not Found | Page does not exist |
| 405 | Method Not Allowed | HTTP method not supported |
| 406 | Not Acceptable | Content negotiation failure |
| 408 | Request Timeout | Server timed out waiting for request |
| 410 | Gone | Resource permanently removed |
| 429 | Too Many Requests | Rate limited by server |
| 451 | Unavailable For Legal Reasons | Blocked for legal reasons |

#### 5xx Server Errors

| Status Code | Name | Common Cause |
|-------------|------|-------------|
| 500 | Internal Server Error | Server-side bug or crash |
| 501 | Not Implemented | Feature not supported |
| 502 | Bad Gateway | Proxy/load balancer error |
| 503 | Service Unavailable | Server temporarily down |
| 504 | Gateway Timeout | Upstream server timeout |
| 520-530 | Cloudflare Errors | Various CDN-specific errors |

### Network Errors

Network-level errors occur when muffet cannot establish a connection to the server or the connection fails during the request.

#### DNS Resolution Failures

```
lookup example.invalid: no such host
```

This occurs when the domain name cannot be resolved to an IP address. Common causes:
- Misspelled domain name
- Domain has expired
- DNS server is unreachable
- Domain does not exist

#### Connection Refused

```
dial tcp 192.0.2.1:443: connect: connection refused
```

The server is reachable at the IP level but is not accepting connections on the specified port. Common causes:
- Web server is not running
- Firewall is blocking the port
- Wrong port specified

#### Connection Reset

```
read tcp 192.0.2.1:443: read: connection reset by peer
```

The server accepted the connection but then abruptly closed it. Common causes:
- Server crash
- Firewall timeout
- Server-side rate limiting
- WAF blocking the request

#### Timeout Errors

```
timeout
```

The request did not complete within the configured timeout period (set by `-t`). Common causes:
- Server is slow to respond
- Network congestion
- Server is overloaded
- DNS resolution is slow
- Large response that takes too long to download

#### Network Unreachable

```
dial tcp: network is unreachable
```

Cannot route to the destination network. Common causes:
- No internet connection
- Network misconfiguration
- IPv6 address used on IPv4-only network (or vice versa)

### TLS Errors

TLS-specific errors occur during the HTTPS handshake:

- **Certificate expired**: `x509: certificate has expired or is not yet valid`
- **Unknown CA**: `x509: certificate signed by unknown authority`
- **Hostname mismatch**: `x509: certificate is valid for X, not Y`
- **Self-signed**: `x509: certificate signed by unknown authority` (self-signed certificates are a special case of unknown CA)
- **Handshake failure**: `tls: handshake failure`
- **Protocol version**: `tls: protocol version not supported`

### Redirect Errors

```
too many redirections
```

The redirect chain exceeded the `--max-redirections` limit. This typically indicates a redirect loop.

### Fragment Errors

When fragment checking is enabled and the target fragment does not exist on the page:

```
200 (fragment not found)
```

The page itself loaded successfully (HTTP 200), but no element with the specified fragment ID was found in the HTML.

### Response Size Errors

When `--max-response-body-size` is set and a response exceeds the limit, the response may be truncated or the URL may be reported with a size-related error.

---

## Rate Limiting

### How Rate Limiting Works

muffet's rate limiting uses a token bucket algorithm. The bucket has a capacity equal to the `--rate-limit` value, and tokens are replenished at the rate-limit rate per second.

When muffet wants to make an HTTP request:
1. It attempts to take a token from the bucket
2. If a token is available, the request proceeds immediately
3. If no token is available, the goroutine blocks until a token becomes available

This allows short bursts of requests up to the bucket capacity while maintaining a steady average rate over time.

### Rate Limiting vs. Concurrency

Rate limiting and concurrency control different aspects of muffet's behavior:

- **Concurrency** controls how many requests can be in-flight simultaneously. A request is "in-flight" from when the HTTP request is sent to when the response is fully received.
- **Rate limiting** controls how many new requests are initiated per second, regardless of how many are in-flight.

High concurrency with a rate limit means many goroutines may be waiting for tokens. Low concurrency with no rate limit means the rate is bounded by the number of goroutines and server response times.

### Choosing a Rate Limit

| Rate Limit | Use Case |
|------------|----------|
| 1-5 | Very gentle; checking production sites you do not own |
| 5-20 | Moderate; checking sites where you want to be polite |
| 20-50 | Aggressive; checking sites you control |
| 50-100 | Very aggressive; local or high-capacity servers |
| Unlimited | No rate limit; maximum throughput (default) |

### Rate Limiting and External Hosts

The rate limit is global across all hosts. When checking a site with many external links, the rate limit is shared between requests to the internal site and requests to external sites. This means that checking many external links can slow down internal crawling, and vice versa.

If you need different rate limits for internal and external hosts, consider running muffet twice:
1. Once with `--one-page-only` or limited crawling for external links at a low rate
2. Once with external links excluded (`--exclude`) for internal links at a higher rate

---

## Performance

### Go's Concurrency Advantages

muffet is written in Go, which provides several performance advantages for a link checker:

1. **Goroutines**: Lightweight user-space threads that enable tens of thousands of concurrent operations with low overhead. Each goroutine uses only a few kilobytes of stack space.

2. **Channels**: Built-in communication primitives that coordinate work between goroutines without explicit locking.

3. **Net/HTTP package**: Go's standard HTTP client is highly optimized with built-in connection pooling, keep-alive support, and efficient TLS implementation.

4. **Static binary**: muffet compiles to a single static binary with no runtime dependencies, simplifying deployment and reducing startup time.

### Connection Pooling

muffet uses Go's built-in HTTP connection pooling. When a response is received and the connection is still healthy, it is returned to the pool for reuse. This avoids the overhead of TCP handshake and TLS negotiation for subsequent requests to the same host.

Key aspects of connection pooling:
- Connections are pooled per host
- Keep-alive connections are reused automatically
- Idle connections are closed after a timeout
- `--max-connections` and `--max-connections-per-host` control pool sizes

### Memory Efficiency

muffet is designed to be memory-efficient:
- HTML responses are parsed in a streaming fashion where possible
- The URL deduplication set uses efficient data structures
- `--max-response-body-size` limits memory usage per response
- `--buffer-size` controls the internal channel buffer size

### Throughput Optimization Tips

To maximize muffet's throughput:

1. **Increase concurrency**: Set `--concurrency` to a high value (50-200) to keep many requests in-flight
2. **Increase connections**: Set `--max-connections` high enough to support the concurrency level
3. **Tune per-host connections**: Set `--max-connections-per-host` based on server capacity
4. **Remove rate limiting**: Do not set `--rate-limit` unless necessary
5. **Skip fragment checking**: Use `--ignore-fragments` to avoid HTML parsing overhead
6. **Exclude unnecessary URLs**: Use `--exclude` to skip URLs that are not important (e.g., social media links that are known to return 403 to bots)
7. **Increase timeout**: Paradoxically, a short timeout can slow things down if it causes retries. Set a reasonable timeout that avoids premature failures

---

## Edge Cases

### Self-Referencing Links

Pages that link to themselves (e.g., `<a href="#top">`) are handled by muffet's deduplication. The page is only fetched once, and the self-reference is checked like any other link.

### Fragment-Only Links

Links like `<a href="#section">` are resolved against the current page's URL. If the current page is `https://example.com/docs`, the link resolves to `https://example.com/docs#section`, and the fragment is checked on the current page.

### mailto: Links

Links with the `mailto:` scheme are silently skipped. muffet does not validate email addresses.

### javascript: Links

Links with the `javascript:` scheme are silently skipped. These are inline JavaScript handlers and are not checkable URLs.

### data: URLs

Data URLs (e.g., `data:image/png;base64,...`) embed content directly in the URL. muffet skips these as they do not reference external resources.

### Relative URLs

Relative URLs are resolved against the base URL of the page where they are found. muffet handles all forms of relative URLs:
- Root-relative: `/path/to/page`
- Path-relative: `path/to/page`
- Parent-relative: `../other/page`
- Current-relative: `./page`
- Protocol-relative: `//cdn.example.com/file.js`

### URL Encoding

muffet handles URL-encoded characters in both the URL itself and in HTML attributes. Common encoded characters include:
- `%20` (space)
- `%2F` (forward slash)
- `%3F` (question mark)
- `%26` (ampersand)
- `%23` (hash/pound sign)
- `%3D` (equals sign)

HTML entities in URLs (e.g., `&amp;` in HTML attributes) are decoded before URL resolution.

### Internationalized Domain Names (IDN)

Internationalized domain names use Unicode characters (e.g., `https://example.xn--com`). muffet handles these by using the Punycode-encoded form (ACE form) for DNS resolution while preserving the Unicode form for display.

### Very Long URLs

Extremely long URLs (thousands of characters) are handled by muffet, though they may be rejected by web servers (most servers have URL length limits around 2000-8000 characters). If a server rejects a long URL, muffet reports the error as it would for any other HTTP error.

### Infinite Redirect Loops

Redirect loops are detected by the `--max-redirections` limit. When the redirect chain exceeds this limit, muffet stops following redirects and reports the error. muffet does not attempt to detect loops by tracking visited URLs within a redirect chain; it relies solely on the count limit.

### Empty or Invalid href Values

muffet handles various edge cases in href attribute values:
- Empty href (`href=""`): Resolves to the current page URL
- Hash-only href (`href="#"`): Resolves to the current page with an empty fragment
- Whitespace in href (`href="  /page  "`): Whitespace is typically trimmed
- Invalid URLs: Reported as errors

### Non-HTML Content Types

When muffet fetches a page that does not return HTML content (e.g., a JSON API endpoint, a plain text file, or a binary file), it cannot extract links from it. The page is still checked for reachability (status code), but no link extraction occurs.

When checking fragments on non-HTML pages, the fragment check may report an error since there are no HTML elements to match against.

### Query Strings and Deduplication

URLs with different query strings are treated as different URLs for deduplication purposes:
- `https://example.com/page` and `https://example.com/page?v=2` are treated as different URLs
- Both will be fetched and checked independently

### Concurrent Modification of Pages

muffet performs a point-in-time check of the website. If pages change while muffet is running (e.g., a deployment happens mid-crawl), the results may be inconsistent. Some pages may reflect the old version and some the new version.

---

## Integration with CI/CD Pipelines

### General Principles

muffet integrates well with CI/CD systems due to its:
- Clear exit codes (0 for success, 1 for broken links, 2 for errors)
- JSON output mode for programmatic processing
- Single binary with no dependencies
- Configurable timeouts and rate limits suitable for CI environments

### GitHub Actions

```yaml
name: Check Links
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 6 * * 1'  # Every Monday at 6 AM

jobs:
  link-check:
    runs-on: ubuntu-latest
    steps:
      - name: Install muffet
        run: go install github.com/raviqqe/muffet/v2@latest

      - name: Start local server
        run: |
          # Start your documentation server
          cd docs && python -m http.server 8080 &
          sleep 2

      - name: Check links
        run: |
          muffet \
            --concurrency 20 \
            --timeout 30 \
            --rate-limit 10 \
            -e "linkedin\\.com" \
            -e "twitter\\.com" \
            http://localhost:8080

      - name: Check links (JSON report)
        if: failure()
        run: |
          muffet \
            --json \
            --concurrency 20 \
            --timeout 30 \
            http://localhost:8080 > broken-links.json || true
          cat broken-links.json | jq '.'

      - name: Upload report
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: broken-links-report
          path: broken-links.json
```

### GitLab CI

```yaml
link-check:
  image: golang:latest
  stage: test
  script:
    - go install github.com/raviqqe/muffet/v2@latest
    - cd docs && python3 -m http.server 8080 &
    - sleep 2
    - muffet --concurrency 20 --timeout 30 http://localhost:8080
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == "main"
    - if: $CI_PIPELINE_SOURCE == "schedule"
  allow_failure: false
```

### Jenkins

```groovy
pipeline {
    agent any

    stages {
        stage('Install muffet') {
            steps {
                sh 'go install github.com/raviqqe/muffet/v2@latest'
            }
        }

        stage('Start server') {
            steps {
                sh '''
                    cd docs
                    python3 -m http.server 8080 &
                    sleep 2
                '''
            }
        }

        stage('Check links') {
            steps {
                sh '''
                    muffet \
                        --concurrency 20 \
                        --timeout 30 \
                        --rate-limit 10 \
                        http://localhost:8080
                '''
            }
        }
    }

    post {
        failure {
            sh '''
                muffet --json --timeout 30 http://localhost:8080 > broken-links.json || true
            '''
            archiveArtifacts artifacts: 'broken-links.json', allowEmptyArchive: true
        }
    }
}
```

### Docker-Based CI

```dockerfile
FROM golang:alpine AS builder
RUN go install github.com/raviqqe/muffet/v2@latest

FROM alpine:latest
COPY --from=builder /root/go/bin/muffet /usr/local/bin/muffet
ENTRYPOINT ["muffet"]
```

Usage in CI:

```bash
docker run --network host muffet-image \
  --concurrency 20 \
  --timeout 30 \
  http://localhost:8080
```

### Best Practices for CI/CD Integration

#### Use Exclusion Patterns Liberally

External services often block automated requests or are unreliable. Exclude known problematic domains:

```bash
muffet \
  -e "linkedin\\.com" \
  -e "twitter\\.com" \
  -e "x\\.com" \
  -e "facebook\\.com" \
  -e "instagram\\.com" \
  -e "reddit\\.com" \
  https://example.com
```

#### Set Appropriate Timeouts

CI environments may have slower or more variable network performance:

```bash
muffet --timeout 30 https://example.com
```

#### Use Rate Limiting

Avoid overwhelming target servers and triggering rate limits:

```bash
muffet --rate-limit 10 --max-connections-per-host 2 https://example.com
```

#### Generate Machine-Readable Output

Use `--json` to generate output that can be parsed and processed:

```bash
muffet --json https://example.com > results.json
broken_count=$(cat results.json | jq 'map(.links | length) | add // 0')
echo "Found $broken_count broken links"
```

#### Run on a Schedule

Link rot happens over time. Schedule regular link checks even if code has not changed:

```yaml
# GitHub Actions schedule
on:
  schedule:
    - cron: '0 6 * * 1'  # Every Monday at 6 AM
```

#### Separate Internal and External Checks

Run separate checks for internal and external links with different settings:

```bash
# Internal links only: fast, no rate limit
muffet -e "^https?://(?!example\\.com)" --concurrency 50 https://example.com

# External links only: slower, rate limited
muffet --one-page-only --rate-limit 5 --max-connections-per-host 2 https://example.com
```

#### Handle Flaky External Links

External links can be temporarily unreliable. Consider:
1. Allowing CI to pass with warnings for external link failures
2. Running external link checks on a schedule rather than on every PR
3. Using `--exclude` for known-flaky external services
4. Retrying the check before failing the pipeline

---

## Crawling Algorithm Details

### Breadth-First Search

muffet uses a breadth-first search (BFS) algorithm for crawling. Starting from the root URL, it:

1. Fetches the root page
2. Extracts all links from the root page
3. Adds all unvisited internal links to the crawl queue
4. Checks all external links for reachability
5. Dequeues the next internal page and repeats from step 2

This approach ensures that pages closer to the root (in terms of link depth) are checked first. Combined with concurrent goroutines, the BFS effectively becomes a parallel BFS where multiple pages at the same depth level are processed simultaneously.

### URL Frontier Management

The URL frontier (crawl queue) is managed internally using Go channels. New URLs are sent to the frontier through a channel, and crawler goroutines receive URLs from the channel. This provides natural backpressure: when the frontier is full (channel buffer exhausted), producers block until consumers process some URLs.

The frontier interacts with the deduplication set:
1. Before adding a URL to the frontier, it is checked against the visited set
2. URLs already in the visited set are silently dropped
3. URLs not in the visited set are added to both the visited set and the frontier

This ensures that each URL is processed at most once, even if it is discovered from multiple source pages.

### Page Processing Pipeline

Each page goes through a pipeline:

1. **Fetch**: HTTP request is made, response is received
2. **Status check**: HTTP status code is evaluated
3. **Content type check**: Response Content-Type header is examined
4. **Parse**: HTML content is parsed to extract links
5. **Link resolution**: Relative URLs are resolved to absolute URLs
6. **Classification**: Links are classified as internal or external
7. **Deduplication**: Links are checked against the visited set
8. **Dispatch**: New internal links go to the frontier; external links go to the checker

### Depth Tracking

muffet does not limit crawl depth by default. It will follow internal links to any depth, constrained only by:
- The number of unique internal pages on the site
- Deduplication (each page is visited once)
- Exclusion patterns
- robots.txt rules (if enabled)

The `--one-page-only` flag effectively sets the depth limit to 0 (only the root page is crawled).

### Link Extraction Parsing

muffet parses HTML to extract links from specific element/attribute combinations:

| Element | Attribute | Example |
|---------|-----------|---------|
| `a` | `href` | `<a href="/page">` |
| `img` | `src` | `<img src="/image.png">` |
| `img` | `srcset` | `<img srcset="/small.png 300w, /large.png 1200w">` |
| `script` | `src` | `<script src="/app.js">` |
| `link` | `href` | `<link href="/style.css">` |
| `source` | `src` | `<source src="/video.mp4">` |
| `source` | `srcset` | `<source srcset="/img-480.webp 480w">` |

The parser handles:
- Standard HTML attributes
- Single and double quoted attribute values
- HTML entities within attribute values
- Malformed HTML (graceful degradation)

---

## HTTP Status Code Handling

### Successful Status Codes

Status codes in the 2xx range indicate success. muffet treats these as valid links:

| Code | Name | Meaning |
|------|------|---------|
| 200 | OK | Standard successful response |
| 201 | Created | Resource was created (rare for link checking) |
| 202 | Accepted | Request accepted for processing |
| 204 | No Content | Successful but no response body |
| 206 | Partial Content | Partial response (range requests) |

### Redirect Status Codes

Status codes in the 3xx range indicate redirection. muffet follows these according to the `--max-redirections` setting:

| Code | Name | Behavior |
|------|------|----------|
| 301 | Moved Permanently | Follow redirect |
| 302 | Found | Follow redirect |
| 303 | See Other | Follow redirect (method changed to GET) |
| 304 | Not Modified | Treated as cache hit, generally not encountered |
| 307 | Temporary Redirect | Follow redirect (preserve method) |
| 308 | Permanent Redirect | Follow redirect (preserve method) |

### Client Error Status Codes

Status codes in the 4xx range indicate client errors. muffet reports these as broken links:

| Code | Name | Typical Cause |
|------|------|---------------|
| 400 | Bad Request | Malformed URL |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Access denied (authentication succeeded but authorization failed) |
| 404 | Not Found | Page does not exist |
| 405 | Method Not Allowed | Server does not support the HTTP method used |
| 406 | Not Acceptable | Content negotiation failed |
| 407 | Proxy Authentication Required | Proxy requires authentication |
| 408 | Request Timeout | Server timed out |
| 409 | Conflict | Request conflicts with server state |
| 410 | Gone | Resource permanently removed (stronger than 404) |
| 411 | Length Required | Content-Length header required |
| 413 | Payload Too Large | Request body too large |
| 414 | URI Too Long | URL exceeds server's limit |
| 415 | Unsupported Media Type | Request format not supported |
| 416 | Range Not Satisfiable | Requested range not available |
| 417 | Expectation Failed | Expect header not satisfiable |
| 421 | Misdirected Request | Request directed to wrong server |
| 422 | Unprocessable Entity | Request body semantic errors |
| 423 | Locked | Resource is locked |
| 429 | Too Many Requests | Rate limited |
| 451 | Unavailable For Legal Reasons | Legally blocked |

### Server Error Status Codes

Status codes in the 5xx range indicate server errors:

| Code | Name | Typical Cause |
|------|------|---------------|
| 500 | Internal Server Error | Unhandled server exception |
| 501 | Not Implemented | Feature not supported |
| 502 | Bad Gateway | Upstream server error |
| 503 | Service Unavailable | Server temporarily down (maintenance, overload) |
| 504 | Gateway Timeout | Upstream server timeout |
| 505 | HTTP Version Not Supported | HTTP version not supported |
| 507 | Insufficient Storage | Server storage full |
| 508 | Loop Detected | Infinite loop in server processing |
| 510 | Not Extended | Further extensions required |
| 511 | Network Authentication Required | Network login required (captive portals) |

### CDN and Non-Standard Status Codes

Some CDN providers (notably Cloudflare) use non-standard status codes:

| Code | Provider | Meaning |
|------|----------|---------|
| 520 | Cloudflare | Unknown error (web server returned unexpected response) |
| 521 | Cloudflare | Web server is down |
| 522 | Cloudflare | Connection timed out |
| 523 | Cloudflare | Origin is unreachable |
| 524 | Cloudflare | A timeout occurred |
| 525 | Cloudflare | SSL handshake failed |
| 526 | Cloudflare | Invalid SSL certificate |
| 527 | Cloudflare | Railgun error |
| 530 | Cloudflare | Origin DNS error |

muffet reports these non-standard codes as-is, showing the numeric code in the error output.

---

## Network Error Categories

### Connection Establishment Errors

These errors occur before any HTTP communication takes place:

#### DNS Resolution Failures

```
dial tcp: lookup hostname: no such host
dial tcp: lookup hostname: Temporary failure in name resolution
dial tcp: lookup hostname: server misbehaving
```

DNS errors indicate that the hostname could not be resolved to an IP address. This can be temporary (DNS server overloaded) or permanent (domain does not exist).

#### TCP Connection Failures

```
dial tcp 1.2.3.4:443: connect: connection refused
dial tcp 1.2.3.4:443: connect: connection timed out
dial tcp 1.2.3.4:443: connect: network is unreachable
dial tcp 1.2.3.4:443: connect: no route to host
```

TCP connection errors indicate that the IP address was resolved but a TCP connection could not be established. The server may be down, firewalled, or on an unreachable network.

#### TLS Handshake Failures

```
tls: handshake failure
tls: protocol version not supported
tls: oversized record received
remote error: tls: bad certificate
```

TLS errors occur after the TCP connection is established but before HTTP communication begins.

### Request/Response Errors

These errors occur during HTTP communication:

#### Timeout Errors

```
context deadline exceeded
i/o timeout
net/http: request canceled (Client.Timeout exceeded while awaiting headers)
net/http: request canceled (Client.Timeout exceeded while reading body)
```

Timeout errors are among the most common errors in link checking. They indicate that the server did not respond within the configured timeout period.

#### Connection Reset Errors

```
read tcp 1.2.3.4:12345->5.6.7.8:443: read: connection reset by peer
write tcp 1.2.3.4:12345->5.6.7.8:443: write: broken pipe
```

These errors occur when the server abruptly closes the connection during communication. This can be caused by server crashes, firewall timeouts, or server-side rate limiting.

#### EOF Errors

```
EOF
unexpected EOF
```

An unexpected end-of-file indicates that the connection was closed before the response was fully received. This can indicate server issues or network problems.

### Redirect Errors

```
stopped after N redirects
```

This error indicates that the redirect chain exceeded the `--max-redirections` limit.

### Content Errors

#### Fragment Not Found

```
id "section-name" not found
```

The page loaded successfully, but no HTML element with the specified fragment ID was found.

### Categorizing Errors for Triage

When reviewing muffet's output, errors can be categorized by severity:

**Critical (fix immediately)**:
- 404 Not Found: Broken links visible to users
- 410 Gone: Content permanently removed
- DNS failures: Domain no longer exists
- Connection refused: Server is down

**Important (investigate)**:
- 500 Internal Server Error: Server-side bugs
- 502/503/504: Infrastructure issues
- TLS errors: Certificate problems
- Fragment not found: Navigation issues

**Low priority (monitor)**:
- 403 Forbidden: May be intentional access control
- 429 Too Many Requests: Rate limiting; reduce muffet's request rate
- Timeouts: May be temporary; retry before fixing
- Connection reset: May be transient

**Informational (often ignorable)**:
- 401 Unauthorized: Expected for protected pages
- 405 Method Not Allowed: Some servers block HEAD/GET from bots
- External link errors: Often caused by anti-bot measures

---

## Practical Examples

### Basic Website Check

```bash
muffet https://example.com
```

The simplest invocation. Crawls the entire site and reports broken links.

### Check a Staging Site with Self-Signed Certificate

```bash
muffet --skip-tls-verification https://staging.example.com
```

### Quick Single-Page Check

```bash
muffet --one-page-only https://example.com/important-page
```

### Gentle Check of a Production Site

```bash
muffet \
  --concurrency 5 \
  --max-connections-per-host 1 \
  --rate-limit 2 \
  --timeout 30 \
  https://production.example.com
```

### Check with Authentication

```bash
muffet \
  -H "Authorization: Bearer $(cat token.txt)" \
  -e "^https?://(?!docs\\.example\\.com)" \
  https://docs.example.com
```

### Generate JSON Report for CI

```bash
muffet --json --timeout 30 https://example.com > report.json
```

### Exclude Social Media and Known-Flaky Links

```bash
muffet \
  -e "twitter\\.com" \
  -e "x\\.com" \
  -e "linkedin\\.com" \
  -e "facebook\\.com" \
  -e "instagram\\.com" \
  -e "github\\.com/.*/(issues|pulls)" \
  -e "\\.pdf$" \
  https://example.com
```

### Check Documentation Site with Sitemap

```bash
muffet \
  --follow-sitemap-xml \
  --follow-robots-txt \
  --ignore-fragments \
  https://docs.example.com
```

### Verbose Check for Debugging

```bash
muffet -v --one-page-only https://example.com/problem-page 2>&1 | head -50
```

### Check Through a Corporate Proxy

```bash
muffet \
  --proxy http://proxy.corp.example.com:8080 \
  --timeout 60 \
  https://external-docs.example.com
```

### Maximum Throughput Local Check

```bash
muffet \
  --concurrency 200 \
  --max-connections 200 \
  --max-connections-per-host 50 \
  http://localhost:8080
```

### Check and Process Results with jq

```bash
# Count broken links per page
muffet --json https://example.com | jq '[.[] | {url, count: (.links | length)}]'

# List all 404 errors
muffet --json https://example.com | jq '[.[] | .links[] | select(.error == "404") | .url]'

# Find pages with the most broken links
muffet --json https://example.com | jq 'sort_by(.links | length) | reverse | .[0:5]'
```

---

## Troubleshooting

### Common Issues and Solutions

#### "Too many open files" Error

**Symptom**: muffet crashes with "too many open files" or "socket: too many open files"

**Cause**: The operating system's file descriptor limit is too low for muffet's concurrency level.

**Solution**:
1. Reduce concurrency: `--concurrency 20 --max-connections 20`
2. Increase the file descriptor limit: `ulimit -n 10000` (Unix/macOS)

#### Excessive Timeout Errors

**Symptom**: Many links reported as timeout errors

**Cause**: Timeout too short, server too slow, or rate limiting by the server

**Solution**:
1. Increase timeout: `-t 30`
2. Reduce concurrency: `--concurrency 10`
3. Add rate limiting: `--rate-limit 5`
4. Reduce per-host connections: `--max-connections-per-host 2`

#### 403 Errors on External Links

**Symptom**: External links return 403 Forbidden even though they work in a browser

**Cause**: External servers block requests without a recognizable User-Agent or from automated tools

**Solution**:
1. Set a browser-like User-Agent: `-H "User-Agent: Mozilla/5.0 (compatible; LinkChecker/1.0)"`
2. Exclude problematic domains: `-e "problematic-domain\\.com"`

#### 429 Too Many Requests

**Symptom**: Server returns 429 status codes

**Cause**: muffet is sending requests too fast for the server

**Solution**:
1. Add rate limiting: `--rate-limit 5`
2. Reduce per-host connections: `--max-connections-per-host 1`
3. Reduce concurrency: `--concurrency 10`

#### Memory Usage Too High

**Symptom**: muffet uses excessive memory on large sites

**Cause**: Buffering too many responses, or fetching very large files

**Solution**:
1. Reduce buffer size: `--buffer-size 32`
2. Limit response body size: `--max-response-body-size 1048576` (1MB)
3. Exclude large file downloads: `-e "\\.(zip|tar|gz|iso|dmg|exe)$"`

#### TLS Certificate Errors on Internal Sites

**Symptom**: muffet reports TLS certificate errors for internal/development sites

**Cause**: Self-signed certificates or corporate CA not in system trust store

**Solution**:
1. Skip TLS verification: `--skip-tls-verification` (development only)
2. Add the CA certificate to the system trust store
3. Set the `SSL_CERT_FILE` or `SSL_CERT_DIR` environment variables

#### Links Work in Browser but Fail in muffet

**Symptom**: Links that work in a browser are reported as broken by muffet

**Cause**: JavaScript-rendered content, authentication, anti-bot measures, or IP-based restrictions

**Solution**:
1. Add appropriate headers: `-H "Cookie: ..." -H "User-Agent: ..."`
2. Exclude JavaScript-dependent links: `-e "pattern"`
3. Use `--ignore-fragments` if fragments are JavaScript-rendered
4. Check if the site uses IP-based access control or geographic restrictions

#### muffet Hangs or Runs Forever

**Symptom**: muffet does not terminate

**Cause**: Very large site, or the site generates dynamic URLs that create an effectively infinite crawl space

**Solution**:
1. Use `--one-page-only` to limit scope
2. Exclude dynamic URL patterns: `-e "\\?.*page=" -e "/search\\?"`
3. Add a timeout at the shell level: `timeout 300 muffet https://example.com`
4. Exclude URL patterns that generate infinite variations

---

## Comparison with Other Link Checkers

### Key Differentiators

muffet stands out among link checkers in several ways:

1. **Speed**: Written in Go with goroutine-based concurrency, muffet is significantly faster than link checkers written in interpreted languages.

2. **Simplicity**: muffet is a single binary with no dependencies. No runtime environment, no package managers, no configuration files required.

3. **Resource efficiency**: Go's goroutines use much less memory than OS threads, allowing muffet to maintain thousands of concurrent checks without excessive resource usage.

4. **Reliable exit codes**: muffet's exit codes (0, 1, 2) make it easy to integrate into CI/CD pipelines without parsing output.

5. **JSON output**: Machine-readable output enables integration with monitoring and reporting tools.

6. **Fine-grained concurrency control**: Four independent concurrency parameters (concurrency, max-connections, max-connections-per-host, rate-limit) provide precise control over resource usage.

---

## Glossary

| Term | Definition |
|------|-----------|
| **BFS** | Breadth-First Search; the crawling algorithm used by muffet |
| **CDN** | Content Delivery Network; a distributed network that serves cached content |
| **Connection pooling** | Reusing TCP connections for multiple HTTP requests to the same host |
| **Crawl queue** | The list of URLs waiting to be fetched and checked |
| **Deduplication** | The process of ensuring each URL is checked only once |
| **DNS** | Domain Name System; translates hostnames to IP addresses |
| **Exit code** | A numeric value returned by a program indicating success or failure |
| **Fragment** | The portion of a URL after the `#` symbol, referencing a specific element on the page |
| **Goroutine** | A lightweight thread managed by Go's runtime |
| **IDN** | Internationalized Domain Name; a domain name containing non-ASCII characters |
| **Keep-alive** | Maintaining a TCP connection open for multiple HTTP requests |
| **Link rot** | The tendency for URLs to become broken over time as content is moved or deleted |
| **Punycode** | An encoding scheme for representing Unicode characters in domain names |
| **Rate limiting** | Controlling the frequency of requests to avoid overwhelming servers |
| **RE2** | The regular expression engine used by Go's regexp package |
| **robots.txt** | A file that tells web crawlers which pages not to access |
| **Sitemap** | An XML file listing the URLs on a website |
| **TLS** | Transport Layer Security; the protocol that provides HTTPS encryption |
| **Token bucket** | A rate limiting algorithm that allows bursts while maintaining an average rate |
| **URL frontier** | Another name for the crawl queue |
| **WAF** | Web Application Firewall; a security layer that can block automated requests |

---

## Appendix A: Regular Expression Quick Reference

Since muffet uses Go's RE2 regexp syntax for the `--exclude` flag, here is a quick reference of commonly used patterns:

### Character Classes

| Pattern | Matches |
|---------|---------|
| `.` | Any character except newline |
| `\d` | A digit (0-9) |
| `\D` | A non-digit |
| `\w` | A word character (letter, digit, underscore) |
| `\W` | A non-word character |
| `\s` | A whitespace character |
| `\S` | A non-whitespace character |
| `[abc]` | Any of a, b, or c |
| `[a-z]` | Any lowercase letter |
| `[^abc]` | Any character except a, b, or c |
| `[0-9a-fA-F]` | A hexadecimal digit |

### Quantifiers

| Pattern | Meaning |
|---------|---------|
| `*` | Zero or more |
| `+` | One or more |
| `?` | Zero or one |
| `{n}` | Exactly n times |
| `{n,}` | n or more times |
| `{n,m}` | Between n and m times |

### Anchors

| Pattern | Meaning |
|---------|---------|
| `^` | Start of string |
| `$` | End of string |

### Grouping and Alternation

| Pattern | Meaning |
|---------|---------|
| `(abc)` | Capturing group |
| `(?:abc)` | Non-capturing group |
| `a\|b` | a or b |

### Escaping Special Characters

The following characters have special meaning in regex and must be escaped with `\` to match literally: `. * + ? ^ $ { } [ ] ( ) | \`

In shell commands, you often need to double-escape: `\\.` becomes `\\\\.` in some shells, or use single quotes to avoid shell interpretation.

### URL-Specific Pattern Examples

```
# Match a domain
https?://(www\\.)?example\\.com

# Match a file extension
\\.(pdf|docx?|xlsx?)$

# Match a path segment
/api/v[0-9]+/

# Match query parameters
\\?.*key=value

# Match any URL with a port number
:[0-9]{2,5}/

# Match IP addresses
https?://[0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+

# Match URLs with specific path depth
https?://[^/]+/[^/]+/[^/]+/[^/]+  # At least 4 path segments
```

---

## Appendix B: HTTP Request Flow

The following describes the complete lifecycle of a single HTTP request in muffet:

1. **URL selection**: A URL is dequeued from the crawl frontier
2. **Exclusion check**: The URL is checked against all `--exclude` patterns. If it matches, it is silently skipped.
3. **robots.txt check** (if `--follow-robots-txt`): The URL is checked against the cached robots.txt rules for the URL's domain. If disallowed, it is silently skipped.
4. **Rate limit wait**: If `--rate-limit` is set, the goroutine waits for a token from the rate limiter.
5. **Connection acquisition**: The goroutine requests a connection from the connection pool. It blocks if `--max-connections` or `--max-connections-per-host` limits are reached.
6. **DNS resolution**: The hostname is resolved to an IP address (cached by the OS and Go runtime).
7. **TCP connection**: A TCP connection is established to the resolved IP address on the appropriate port (80 for HTTP, 443 for HTTPS).
8. **TLS handshake** (for HTTPS): The TLS handshake is performed, including certificate validation (unless `--skip-tls-verification` is set).
9. **HTTP request**: The HTTP request is sent, including any custom headers from `--header`.
10. **Response receipt**: The HTTP response status line and headers are received.
11. **Redirect handling**: If the response is a redirect (3xx), the process repeats from step 4 with the redirect target URL, up to `--max-redirections` times.
12. **Body reading**: The response body is read, up to `--max-response-body-size` bytes.
13. **HTML parsing** (for internal pages): If the response is HTML, it is parsed to extract links.
14. **Fragment checking** (if applicable): If the URL has a fragment and `--ignore-fragments` is not set, the parsed HTML is searched for a matching element ID.
15. **Link dispatch**: Extracted links are resolved to absolute URLs and dispatched: internal links to the frontier, external links to the checker queue.
16. **Connection return**: The TCP connection is returned to the pool for reuse (or closed if the server sent `Connection: close`).
17. **Result recording**: The check result (success or failure with error details) is recorded for output.

At any point during steps 5-12, a timeout may occur if the total elapsed time exceeds `--timeout` seconds. The timeout covers the entire request lifecycle for a single request, not the full redirect chain.

---

## Appendix C: Understanding muffet Output

### Reading Default Output

The default output groups broken links by source page:

```
https://example.com/
        404     https://example.com/old-page
        timeout https://cdn.example.com/missing-script.js
https://example.com/about
        403     https://private.example.com/internal
        x509: certificate has expired or is not yet valid https://expired.example.com
https://example.com/links
        lookup bad-domain.invalid: no such host  https://bad-domain.invalid/page
```

Each section begins with a source URL on its own line (no indentation). Below it, broken links are listed with a tab indentation, followed by the error description, then a tab, then the broken URL.

Reading this output:
- The page at `https://example.com/` contains a link to `/old-page` which returns 404, and a script reference to a CDN that times out.
- The page at `https://example.com/about` has a link to a private server that returns 403, and a link to a site with an expired certificate.
- The page at `https://example.com/links` references a domain that does not exist.

### Reading JSON Output

JSON output provides the same information in a structured format:

```json
[
  {
    "url": "https://example.com/",
    "links": [
      {"url": "https://example.com/old-page", "error": "404"},
      {"url": "https://cdn.example.com/missing-script.js", "error": "timeout"}
    ]
  },
  {
    "url": "https://example.com/about",
    "links": [
      {"url": "https://private.example.com/internal", "error": "403"},
      {"url": "https://expired.example.com", "error": "x509: certificate has expired or is not yet valid"}
    ]
  }
]
```

### Interpreting Error Messages

| Error in Output | Meaning | Action |
|-----------------|---------|--------|
| `404` | Page not found | Fix or remove the link |
| `403` | Access forbidden | May be intentional; check if link should be excluded |
| `500` | Server error | Investigate server-side issue |
| `timeout` | Request timed out | Increase timeout or check server health |
| `connection refused` | Server not accepting connections | Check if server is running |
| `no such host` | DNS resolution failed | Check domain spelling or if domain exists |
| `x509: ...` | TLS certificate issue | Fix certificate or use `--skip-tls-verification` |
| `too many redirections` | Redirect loop | Fix the redirect chain |
| `id "..." not found` | Fragment target missing | Fix the fragment or use `--ignore-fragments` |
