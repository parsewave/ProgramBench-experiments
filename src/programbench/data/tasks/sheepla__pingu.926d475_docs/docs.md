# pingu -- Ping with Penguin

## Overview

pingu is a command-line network diagnostic tool that reimplements the classic `ping` utility with colorized output and penguin-themed ASCII art. Written in Go, pingu does not wrap the system's `ping` command as a subprocess. Instead, it directly constructs and sends ICMP Echo Request packets using the `pro-bing` library (from the Prometheus community), receives Echo Reply packets, and renders results in real time with a decorative penguin displayed alongside each response line. The tool targets Linux, macOS, and Windows, and supports both privileged (raw socket) and unprivileged (UDP) ICMP modes.

pingu is a single-file Go application (the entire implementation lives in `main.go`) that compiles to one self-contained binary with no runtime dependencies on the system `ping` command. It uses the `go-flags` library for argument parsing, the `fatih/color` library for terminal color output, and the `pro-bing` library for the actual ICMP implementation.

The tool's distinguishing characteristic is its visual presentation: each received ICMP reply is printed alongside one line of a multi-line penguin ASCII art figure, and every field in the output (sequence number, byte count, IP address, TTL, round-trip time) is rendered in a different terminal color. Upon completion, summary statistics are displayed with a decorated header.

---

## Arguments

### HOST (Positional, Required)

The single required positional argument is the target hostname or IP address. pingu resolves the hostname to an IP address before beginning the ping sequence. Both IPv4 and IPv6 addresses are supported.

Valid examples:

- `example.com` -- a DNS hostname
- `8.8.8.8` -- an IPv4 address
- `2001:4860:4860::8888` -- an IPv6 address
- `localhost` -- the loopback hostname

When a hostname is provided, pingu resolves it to an IP address using the Go standard library's DNS resolver. The resolved address is displayed in the initial output line. If DNS resolution fails, pingu reports the error and exits.

---

## Options

### `-c, --count <NUM>`

Specifies the number of ICMP Echo Request packets to send. After sending this many packets and receiving their replies (or timing them out), pingu stops and prints summary statistics.

- **Type**: Integer
- **Default**: 20
- **Example**: `pingu -c 10 example.com`

When the count is reached, the pinger stops and the `OnFinish` callback fires to display the summary statistics. If the user interrupts with Ctrl-C before the count is reached, the pinger also stops and displays statistics for however many packets were sent and received up to that point.

The count value must be a positive integer. Providing a non-integer or negative value results in an argument parsing error.

### `-P, --privilege`

Enables privileged mode, which uses raw ICMP sockets instead of UDP-based ICMP. On most Unix-like systems, raw sockets require root privileges or the `CAP_NET_RAW` capability.

- **Type**: Boolean flag
- **Default**: false (unprivileged UDP mode)
- **Example**: `pingu -P example.com`

On Windows, privileged mode is always enabled regardless of this flag, because Windows requires raw sockets for ICMP operations.

The distinction between privileged and unprivileged modes is significant:

- **Unprivileged mode** (default on Linux and macOS): Uses UDP sockets to send ICMP-like packets. This works without root access on most modern Linux kernels (where `net.ipv4.ping_group_range` is configured appropriately). However, some systems may not support this mode, in which case the `-P` flag or appropriate system capabilities must be used.

- **Privileged mode** (`-P`): Uses raw ICMP sockets directly. This requires either running as root or having the `CAP_NET_RAW` capability set on the binary. This mode is more reliable across different system configurations.

For WSL (Windows Subsystem for Linux) users, the following capability must be set:

```
sudo setcap cap_net_raw=+ep /path/to/pingu
```

Then run with the `-P` flag:

```
pingu -P example.com
```

---

## Architecture and Internal Design

### Single-File Structure

The entire pingu application is implemented in a single Go source file (`main.go`). This file contains:

1. The penguin ASCII art data (a global string slice)
2. Application metadata variables (name, usage, description, version, revision)
3. Exit code constants
4. The options struct (for CLI argument definitions)
5. The `main()` function (entry point)
6. The `run()` function (core orchestration logic)
7. The `initPinger()` function (pinger configuration)
8. The `pingerOnrecv()` callback (per-packet display)
9. The `pingerOnFinish()` callback (summary statistics display)
10. The `renderASCIIArt()` function (art rendering)
11. The `colorize()` helper function (character-to-color substitution)

### Dependency Graph

pingu depends on three external Go libraries:

- **`github.com/fatih/color` v1.13.0**: Provides cross-platform terminal color output. Used extensively to colorize every field in the ping output. The library handles Windows console API differences transparently.

- **`github.com/jessevdk/go-flags` v1.5.0**: Provides command-line argument parsing with struct tag-based option definitions. Supports short and long option names, default values, and automatic help generation.

- **`github.com/prometheus-community/pro-bing` v0.1.0**: Provides the ICMP ping implementation. This is a community-maintained fork of `go-ping` that handles raw socket creation, ICMP packet construction, timing, and statistics aggregation.

Indirect dependencies include:

- `github.com/google/uuid` -- used by pro-bing for packet identification
- `github.com/mattn/go-colorable` -- used by fatih/color for Windows color support
- `github.com/mattn/go-isatty` -- used by fatih/color for TTY detection
- `golang.org/x/net` -- used by pro-bing for ICMP protocol support
- `golang.org/x/sync` -- used by pro-bing for concurrency primitives
- `golang.org/x/sys` -- used by pro-bing and others for system call access

---

## Program Flow

### Entry Point and Error Handling

The `main()` function serves as a thin entry point that delegates to `run()`. The separation exists to allow `run()` to return both an exit code and an error, which `main()` then handles:

```
main()
  |
  +--> run(os.Args[1:])
         |
         +--> parse arguments
         +--> handle --version
         +--> validate positional args
         +--> initPinger(host, opts)
         |      |
         |      +--> create Pinger
         |      +--> set up signal handler
         |      +--> register OnRecv callback
         |      +--> register OnFinish callback
         |      +--> configure privilege mode
         |      +--> return Pinger
         |
         +--> pinger.Run()  [blocks until complete]
         |
         +--> return exit code
```

If an error occurs, `main()` prints it to stderr using the `color.Error` writer. The error message is formatted with a red, bold `ERROR` label:

```
[ ERROR ] <error message>
```

The program then exits with the appropriate exit code.

### Argument Parsing Phase

pingu uses the `go-flags` library for argument parsing. Options are defined as struct tags on the `options` struct:

```go
type options struct {
    Count     int  `short:"c" long:"count" default:"20" description:"Stop after <count> replies"`
    Privilege bool `short:"P" long:"privilege" description:"Enable privileged mode"`
    Version   bool `short:"V" long:"version" description:"Show version"`
}
```

The parser is configured with `flags.Default` behavior, which includes:

- Automatic help flag (`-h`, `--help`)
- Printing errors to stderr
- Error formatting

After parsing, `go-flags` returns the remaining positional arguments (those not consumed by flags). pingu validates that exactly one positional argument (the host) was provided.

If the parser wrote help text (i.e., the user passed `-h`), pingu exits with code 0 and no error. This is detected via `flags.WroteHelp(err)`.

### Pinger Initialization Phase

The `initPinger()` function creates and configures a `probing.Pinger` instance:

1. **Pinger creation**: `probing.NewPinger(host)` resolves the hostname to an IP address and creates the ICMP pinger. If resolution fails, an error is returned.

2. **Count configuration**: The `Count` field is set from the CLI option (default 20).

3. **Signal handling**: A goroutine is spawned that listens for `os.Interrupt` (SIGINT / Ctrl-C). When received, it calls `pinger.Stop()` to gracefully terminate the ping sequence. This ensures the `OnFinish` callback is still called with accumulated statistics.

4. **Header output**: Before any pings are sent, a header line is printed in bold white:
   ```
   PING <hostname> (<ip address>) type `Ctrl-C` to abort
   ```

5. **Callback registration**: The `OnRecv` and `OnFinish` callbacks are assigned to the pinger.

6. **Privilege configuration**: If the `-P` flag is set, or if the runtime OS is Windows, the pinger is set to privileged mode via `pinger.SetPrivileged(true)`.

### Ping Execution Phase

`pinger.Run()` is a blocking call that:

1. Opens the appropriate socket (raw ICMP or UDP)
2. Sends ICMP Echo Request packets at the default interval (1 second)
3. Listens for Echo Reply packets
4. Calls `OnRecv` for each received reply
5. After `Count` packets are sent and replied to (or after `Stop()` is called), calls `OnFinish` with the accumulated statistics
6. Returns any error that occurred during the process

The execution phase is entirely managed by the `pro-bing` library. pingu itself does not perform any packet construction, socket management, or timing -- it delegates all of this to the library.

---

## ICMP Implementation Details

### How pro-bing Works

Unlike tools that wrap the system `ping` command, pingu performs ICMP operations natively through the pro-bing library. The library:

1. **Resolves the target**: Performs DNS resolution to obtain the target IP address.

2. **Opens a socket**: Either a raw ICMP socket (privileged) or a UDP socket (unprivileged).

3. **Sends Echo Requests**: Constructs ICMP Echo Request packets with incrementing sequence numbers and unique identifiers (based on UUID).

4. **Receives Echo Replies**: Listens on the socket for incoming ICMP Echo Reply packets that match the identifier.

5. **Calculates RTT**: Measures the round-trip time by comparing the send timestamp (embedded in the packet payload) with the receive timestamp.

6. **Tracks statistics**: Maintains running statistics including packet counts, loss rate, and min/avg/max/stddev of round-trip times.

### ICMP Packet Structure

Each ICMP Echo Request sent by pingu contains:

- **Type**: 8 (Echo Request for IPv4) or 128 (Echo Request for IPv6)
- **Code**: 0
- **Checksum**: Calculated over the ICMP header and payload
- **Identifier**: Derived from a UUID, used to match replies to this specific pinger instance
- **Sequence Number**: Starts at 0, increments by 1 for each packet
- **Payload**: Contains the send timestamp for RTT calculation, padded to the requested size

The corresponding Echo Reply contains:

- **Type**: 0 (Echo Reply for IPv4) or 129 (Echo Reply for IPv6)
- **Code**: 0
- **Checksum**: Recalculated
- **Identifier**: Copied from the request
- **Sequence Number**: Copied from the request
- **Payload**: Copied from the request (including the original timestamp)

### Privileged vs. Unprivileged Mode

**Privileged mode** (raw sockets):
- Requires root or `CAP_NET_RAW`
- Creates a raw ICMP socket using `syscall.Socket(AF_INET, SOCK_RAW, IPPROTO_ICMP)`
- Has full control over the ICMP packet
- Works on all platforms

**Unprivileged mode** (UDP sockets):
- Does not require root
- Uses a UDP socket that the kernel translates to ICMP
- Relies on the kernel's `net.ipv4.ping_group_range` sysctl setting
- The kernel assigns the ICMP identifier, so the library cannot control it
- May not work on all systems or kernel versions

On Linux, unprivileged ICMP is controlled by:
```
sysctl net.ipv4.ping_group_range
```

If the current user's GID falls within the configured range, unprivileged pings are allowed. Otherwise, the user must either adjust the sysctl setting, run as root, or use privileged mode (`-P`).

On Windows, only privileged mode is available, so pingu automatically enables it regardless of the `-P` flag.

On macOS, the behavior depends on the system configuration. By default, unprivileged ICMP is available for non-root users, but certain network configurations or firewall rules may restrict it.

### Socket Lifecycle

1. **Creation**: When `pinger.Run()` is called, the appropriate socket type is created based on the privilege mode setting.

2. **Binding**: The socket is bound to the local address (typically `0.0.0.0` for IPv4 or `::` for IPv6).

3. **Sending**: ICMP Echo Requests are sent at regular intervals (default 1 second). Each packet is marshaled using the `golang.org/x/net/icmp` package.

4. **Receiving**: A separate goroutine continuously reads from the socket, unmarshals received ICMP packets, and matches them against outstanding requests by identifier and sequence number.

5. **Cleanup**: When the pinger stops (either by reaching the count or by receiving a stop signal), the socket is closed and all goroutines are terminated.

---

## ASCII Art Rendering

### The Penguin

The penguin ASCII art is defined as a global slice of 20 strings. Each string represents one line of the penguin figure, approximately 57 characters wide. The art uses letter characters as color placeholders:

- `B` -- Represents black regions (the penguin's body outline and dark features)
- `W` -- Represents white regions (the penguin's belly and face highlights)
- `R` -- Represents red regions (the penguin's beak and feet)
- `Y` -- Represents yellow regions (decorative accents)
- `.` -- Represents background dots (rendered as-is, no colorization)
- ` ` -- Represents empty space

The raw art data (before colorization) looks like this:

```
 ...        .     ...   ..    ..     .........
 ...     ....          ..  ..      ... .....  .. ..
 ...    .......      ...         ... . ..... BBBBBBB
.....  ........ .BBBBBBBBBBBBBBB.....  ... BBBBBBBBBB.  .
 .... ........BBBBBBBBBBBBBBBBBBBBB.  ... BBBBBBBBBBB
      ....... BBWWWWBBBBBBBBBBBBBBBB.... BBBBBBBBBBBB
.    .  .... BBWWBBWWBBBBBBBBBBWWWWBB... BBBBBBBBBBB
   ..   ....BBBBWWWWBBRRRRRRBBWWBBWWB.. .BBBBBBBBBBB
    .       BBBBBBBBRRRRRRRRRRBWWWWBB.   .BBBBBBBBBB
   ....     .BBBBBBBBRRRRRRRRBBBBBBBB.      BBBBBBBB
  .....      .  BBBBBBBBBBBBBBBBBBBB.        BBBBBBB.
......     .. . BBBBBBBBBBBBBBBBBB . .      .BBBBBBB
......       BBBBBBBBBBBBBBBBBBBBB  .      .BBBBBBB
......   .BBBBBBBBBBBBBBBBBBYYWWBBBBB  ..  BBBBBBB
...    . BBBBBBBBBBBBBBBBYWWWWWWWWWBBBBBBBBBBBBBB.
       BBBBBBBBBBBBBBBBYWWWWWWWWWWWWWBBBBBBBBB .
      BBBBBBBBBBBBBBBYWWWWWWWWWWWWWWWWBB    .
     BBBBBBBBBBBBBBBYWWWWWWWWWWWWWWWWWWW  ........
  .BBBBBBBBBBBBBBBBYWWWWWWWWWWWWWWWWWWWW    .........
 .BBBBBBBBBBBBBBBBYWWWWWWWWWWWWWWWWWWWWWW       .... . .
```

The figure depicts a penguin in profile, facing right. The body is outlined in black (`B`), with a white (`W`) belly area and red (`R`) beak/feet region. Yellow (`Y`) accents appear near the belly/feet transition area. The dots (`.`) form a scattered snow or background pattern around the penguin.

### The Rendering Pipeline

The `renderASCIIArt()` function is called for every received packet. It takes the packet's sequence number as input and uses it to select which line of the penguin to display:

1. **Line selection**: The sequence number (`idx`) is used as an index into the `pingu` slice. If the index exceeds the slice length (i.e., more than 20 packets have been received), the modulo operator wraps it around: `idx %= len(pingu)`. This means the penguin art cycles every 20 packets.

2. **Colorization**: The selected line is processed through four `colorize()` calls in sequence, one for each color placeholder character:
   - `R` is replaced with `#` in hi-red bold
   - `Y` is replaced with `#` in hi-yellow bold
   - `B` is replaced with `#` in hi-black bold (which typically appears as dark gray on most terminals)
   - `W` is replaced with `#` in hi-white bold

3. **Return**: The colorized string is returned and prepended to the ping reply output line.

### The colorize() Function

The `colorize()` function performs a simple string replacement:

```go
func colorize(text string, target rune, color *color.Color) string {
    return strings.ReplaceAll(
        text,
        string(target),
        color.Sprint("#"),
    )
}
```

Every occurrence of the `target` character in the text is replaced with the `#` character wrapped in the specified ANSI color escape sequence. The `#` character is used because it renders as a solid block-like character in most monospaced terminal fonts, giving the penguin a filled-in appearance.

### Color Mapping Details

The four color channels map to ANSI escape sequences as follows:

| Placeholder | Color Constant               | ANSI Code | Typical Appearance      |
|-------------|------------------------------|-----------|-------------------------|
| `B`         | `FgHiBlack` + `Bold`         | `\e[90;1m`| Dark gray / bright black|
| `W`         | `FgHiWhite` + `Bold`         | `\e[97;1m`| Bright white            |
| `R`         | `FgHiRed` + `Bold`           | `\e[91;1m`| Bright red              |
| `Y`         | `FgHiYellow` + `Bold`        | `\e[93;1m`| Bright yellow           |

The "Hi" (high-intensity) variants are used rather than the standard color variants to ensure the art stands out on both dark and light terminal backgrounds.

### Cycling Behavior

Because the penguin art consists of 20 lines and the sequence number increments by 1 with each packet, the visual effect is:

- **Packets 0-19**: Each packet reveals a new line of the penguin, building up the image line by line from top to bottom as packets come in.
- **Packets 20-39**: The penguin art cycles back to the top and repeats.
- **Packets 40+**: The cycle continues indefinitely.

With the default count of 20 packets, the user sees exactly one complete rendering of the penguin across all 20 output lines. If `-c` is set to a value less than 20, only a partial penguin is displayed. If set to more than 20, the penguin repeats.

### Art Dimensions and Terminal Considerations

The penguin art lines are approximately 57 characters wide. Combined with the ping output data that follows on the same line (sequence number, bytes, IP address, TTL, round-trip time), a single output line can be approximately 100-130 characters wide. This means:

- On standard 80-column terminals, the output will wrap. The art and data will span two physical lines per logical line.
- On wider terminals (120+ columns), the output typically fits on a single physical line, producing the intended visual layout.
- The art does not dynamically adapt to terminal width; it is a fixed-width rendering.

---

## Output Format

### Header Line

Before any ping packets are sent, pingu prints a header line:

```
PING <hostname> (<ip_address>) type `Ctrl-C` to abort
```

This line is printed in bold white (`FgHiWhite` + `Bold`). It shows the original hostname provided by the user and the resolved IP address in parentheses. The message "type \`Ctrl-C\` to abort" informs the user how to stop the ping sequence early.

Examples:

```
PING example.com (93.184.216.34) type `Ctrl-C` to abort
PING 8.8.8.8 (8.8.8.8) type `Ctrl-C` to abort
PING localhost (127.0.0.1) type `Ctrl-C` to abort
```

### Per-Packet Output Lines

Each received ICMP Echo Reply triggers the `pingerOnrecv` callback, which prints a line with the following format:

```
<ascii_art_line> seq=<N> <bytes>bytes from <ip>: ttl=<ttl> time=<rtt>
```

Each field is colorized differently:

| Field      | Color                          | Format     | Description                              |
|------------|--------------------------------|------------|------------------------------------------|
| ASCII art  | Multi-color (see art section)  | Variable   | One line of the penguin figure           |
| `seq=`     | Hi-yellow bold                 | Integer    | ICMP sequence number (starts at 0)       |
| bytes      | Hi-blue bold                   | Integer    | Number of bytes in the reply packet      |
| `from`     | White bold                     | IP address | Source IP address of the reply           |
| `ttl=`     | Hi-cyan bold                   | Integer    | Time-to-live value from the reply        |
| `time=`    | Hi-magenta bold                | Duration   | Round-trip time (e.g., `1.234ms`)        |

A concrete example of one output line (without ANSI color codes) might look like:

```
 ...        .     ...   ..    ..     .........            seq=0 64bytes from 93.184.216.34: ttl=56 time=11.234ms
```

The format string used internally is:

```
%s seq=%s %sbytes from %s: ttl=%s time=%s\n
```

Note that there is no space between the byte count and the word "bytes" -- the format uses `%sbytes` where `%s` is the colorized byte count number.

### Statistics Output

When the ping sequence completes (either by reaching the count or by Ctrl-C interruption), the `pingerOnFinish` callback prints a summary. The output has three sections:

#### Statistics Header

```
───────── <hostname> ping statistics ─────────
```

This line is printed in bold white. The horizontal line characters are Unicode box-drawing characters (U+2500 "BOX DRAWINGS LIGHT HORIZONTAL"), not dashes or hyphens.

#### Packet Statistics Line

```
PACKET STATISTICS: <sent> transmitted => <received> received (<loss>% loss)
```

| Field               | Color              | Description                     |
|---------------------|--------------------|---------------------------------|
| `PACKET STATISTICS` | Hi-white bold      | Label                           |
| transmitted count   | Hi-blue bold       | Number of packets sent          |
| received count      | Hi-green bold      | Number of packets received      |
| loss percentage     | Hi-red bold        | Percentage of packets lost      |

The loss percentage includes a `%` sign and is formatted by Go's default `%v` formatting of a float64 value.

#### Round Trip Statistics Line

```
ROUND TRIP: min=<min> avg=<avg> max=<max> stddev=<stddev>
```

| Field          | Color              | Description                        |
|----------------|--------------------|------------------------------------|
| `ROUND TRIP`   | Hi-white bold      | Label                              |
| min            | Hi-blue bold       | Minimum round-trip time            |
| avg            | Hi-cyan bold       | Average round-trip time            |
| max            | Hi-green bold      | Maximum round-trip time            |
| stddev         | Magenta bold       | Standard deviation of RTT          |

Note that `stddev` uses `FgMagenta` (not `FgHiMagenta`) -- this is a subtle difference from the other fields which all use "Hi" variants.

RTT values are formatted using Go's `time.Duration` string representation, which automatically selects appropriate units. For typical LAN round trips, values appear as microseconds (e.g., `1.234ms`). For very fast loopback pings, values may appear as nanoseconds.

### Complete Output Example

A complete session pinging localhost with `-c 3` might produce (colors omitted):

```
PING localhost (127.0.0.1) type `Ctrl-C` to abort
 ...        .     ...   ..    ..     .........            seq=0 64bytes from 127.0.0.1: ttl=64 time=45.208us
 ...     ....          ..  ..      ... .....  .. ..       seq=1 64bytes from 127.0.0.1: ttl=64 time=38.125us
 ...    .......      ...         ... . ..... #######      seq=2 64bytes from 127.0.0.1: ttl=64 time=51.042us

───────── localhost ping statistics ─────────
PACKET STATISTICS: 3 transmitted => 3 received (0% loss)
ROUND TRIP: min=38.125us avg=44.791us max=51.042us stddev=5.271us
```

---

## Exit Codes

pingu uses three exit codes defined as an `exitCode` type (an integer alias):

| Exit Code | Constant          | Meaning                                                                  |
|-----------|-------------------|--------------------------------------------------------------------------|
| 0         | `exitCodeOK`      | Successful execution. All pings completed without error.                 |
| 1         | `exitCodeErrArgs` | Argument error. Invalid flags, missing host, or too many arguments.      |
| 2         | `exitCodeErrPing` | Ping error. An error occurred during the ICMP ping execution.            |

### Exit Code Details

**Exit code 0** is returned when:
- The help flag (`-h`) is used (help text is displayed and the program exits cleanly)
- The version flag (`-V`) is used
- All requested pings complete successfully
- Note: even if some packets are lost, the exit code is 0 as long as `pinger.Run()` completes without returning a Go error. This differs from the standard `ping` command which returns 1 if any packets are lost.

**Exit code 1** is returned when:
- No positional arguments are provided ("must requires an argument")
- More than one positional argument is provided ("too many arguments")
- The `go-flags` parser encounters an invalid flag or invalid flag value

**Exit code 2** is returned when:
- `pinger.Run()` returns an error (e.g., permission denied when opening a raw socket, network unreachable, etc.)

Note that there is a subtle implementation detail: if `probing.NewPinger()` fails (e.g., DNS resolution failure), the function returns `exitCodeOK` (0) paired with an error. This means the error is still printed to stderr, but the exit code is 0 rather than 2. This appears to be unintentional behavior in the source code.

---

## Error Handling

### Argument Errors

pingu reports argument errors in a consistent format:

```
[ ERROR ] parse error: <details>
```

Specific argument error conditions:

- **No host provided**: "must requires an argument" (note: the original source contains this grammatical quirk)
- **Too many hosts**: "too many arguments"
- **Invalid flag**: Handled by `go-flags`, which prints its own error message (e.g., "unknown flag \`x\`")
- **Invalid flag value**: Handled by `go-flags` (e.g., "expected int" for a non-integer count value)

### Pinger Initialization Errors

If the pinger cannot be created (typically DNS resolution failure):

```
[ ERROR ] an error occurred while initializing pinger: failed to init pinger <details>
```

### Ping Execution Errors

If the ping operation fails during execution:

```
[ ERROR ] an error occurred when running ping: <details>
```

Common causes:
- **Permission denied**: Raw socket creation failed because the user lacks privileges. The error message from the operating system (typically "operation not permitted") is included.
- **Network unreachable**: The network interface is down or the route to the host does not exist.
- **Socket error**: The operating system refused to create the requested socket type.

### Error Display Format

All errors are printed to `color.Error` (which maps to stderr on most platforms). The format is:

```
[ ERROR ] <message>
```

Where `ERROR` is rendered in red bold text. The square brackets and the error message itself are in the default terminal color.

---

## Signal Handling

### SIGINT (Ctrl-C) Handling

pingu registers a signal handler for `os.Interrupt` (which corresponds to SIGINT on Unix systems). The handler runs in a dedicated goroutine:

```go
c := make(chan os.Signal, 1)
signal.Notify(c, os.Interrupt)
go func() {
    <-c
    pinger.Stop()
}()
```

When the user presses Ctrl-C:

1. The operating system delivers SIGINT to the pingu process.
2. Go's signal notification mechanism sends the signal to channel `c`.
3. The goroutine receives the signal and calls `pinger.Stop()`.
4. `pinger.Stop()` signals the pinger to finish its current operation.
5. The `OnFinish` callback is invoked with the accumulated statistics.
6. `pinger.Run()` returns.
7. The `run()` function returns `exitCodeOK`.
8. The program exits normally with code 0.

This graceful handling ensures that even when interrupted, the user sees summary statistics for all packets sent and received up to that point.

### Signal Channel Buffer

The signal channel has a buffer size of 1 (`make(chan os.Signal, 1)`). This prevents the signal from being lost if the goroutine is not immediately ready to receive. Without this buffer, a signal sent while the goroutine is not blocked on the receive operation would be dropped.

### Multiple Signals

The current implementation only handles a single SIGINT. If the user presses Ctrl-C a second time while the pinger is stopping, the default Go signal handling takes over, which terminates the process immediately. This provides an escape hatch if the graceful shutdown hangs for any reason.

### No SIGTERM Handling

pingu does not explicitly handle SIGTERM. If the process receives SIGTERM (e.g., from `kill <pid>`), Go's default behavior applies: the process terminates immediately without printing statistics.

---

## Platform Compatibility

### Linux

Linux is the primary target platform. Both privileged and unprivileged modes are supported.

**Unprivileged mode** (default):
- Requires the kernel to be configured with an appropriate `net.ipv4.ping_group_range`:
  ```
  sysctl -w net.ipv4.ping_group_range="0 2147483647"
  ```
- Uses DGRAM sockets which the kernel translates to ICMP
- No root or capabilities required if the sysctl is set

**Privileged mode** (`-P`):
- Requires either root access or the `CAP_NET_RAW` capability:
  ```
  sudo setcap cap_net_raw=+ep /path/to/pingu
  ```
- Uses raw sockets for full ICMP control
- More portable across different Linux distributions

### macOS

macOS supports pingu in both modes, though the behavior differs slightly from Linux:

- **Unprivileged mode**: Works by default on macOS for most users, as macOS allows non-root users to open ICMP sockets without special configuration.
- **Privileged mode**: Requires running as root (`sudo pingu -P ...`).
- ICMP behavior on macOS may differ slightly in timing granularity and TTL handling compared to Linux.

### Windows

Windows has the most restricted ICMP support:

- **Privileged mode is always enabled**: Regardless of the `-P` flag, `pinger.SetPrivileged(true)` is called when `runtime.GOOS == "windows"`.
- Windows does not support unprivileged ICMP sockets, hence the automatic override.
- The `fatih/color` library handles Windows console color output via `go-colorable`, which translates ANSI escape sequences to Windows Console API calls.
- Windows Terminal and PowerShell support ANSI escape sequences natively, but older cmd.exe requires the `go-colorable` translation.

### WSL (Windows Subsystem for Linux)

WSL requires special handling:

1. Set the `CAP_NET_RAW` capability on the pingu binary:
   ```
   sudo setcap cap_net_raw=+ep /path/to/pingu
   ```
2. Run with the `-P` flag:
   ```
   pingu -P example.com
   ```

This is necessary because WSL's network stack has specific restrictions on raw socket access.

### Cross-Platform Considerations

| Feature              | Linux              | macOS              | Windows            |
|----------------------|--------------------|--------------------|--------------------|
| Unprivileged mode    | Needs sysctl config| Works by default   | Not supported      |
| Privileged mode      | Needs root/cap     | Needs root         | Always enabled     |
| Color output         | ANSI escapes       | ANSI escapes       | Console API / ANSI |
| IPv6 support         | Full               | Full               | Full               |
| Signal handling      | SIGINT             | SIGINT             | Ctrl-C event       |

---

## Color Output System

### The fatih/color Library

pingu uses `github.com/fatih/color` for all terminal color output. This library provides:

- **Cross-platform support**: Works on Linux, macOS, and Windows (including older Windows versions that don't support ANSI escape sequences natively).
- **TTY detection**: Automatically disables color output when stdout is not a terminal (e.g., when piped to a file or another command).
- **Environment variable respect**: Honors the `NO_COLOR` environment variable and `TERM=dumb` to disable colors.
- **Thread safety**: Color output is safe to use from multiple goroutines.

### Color Constants Used

pingu uses the following `color.Attribute` constants:

| Constant        | ANSI Code | Appearance          | Used For                              |
|-----------------|-----------|---------------------|---------------------------------------|
| `FgHiWhite`     | 97        | Bright white        | Header, labels, IP addresses          |
| `FgHiYellow`    | 93        | Bright yellow       | Sequence numbers, penguin Y regions   |
| `FgHiBlue`      | 94        | Bright blue         | Byte counts, transmitted count, min RTT|
| `FgHiCyan`      | 96        | Bright cyan         | TTL values, avg RTT                   |
| `FgHiMagenta`   | 95        | Bright magenta      | Round-trip time                       |
| `FgHiRed`       | 91        | Bright red          | ERROR label, loss %, penguin R regions|
| `FgHiGreen`     | 92        | Bright green        | Received count, max RTT               |
| `FgHiBlack`     | 90        | Dark gray           | Penguin B (body) regions              |
| `FgMagenta`     | 35        | Standard magenta    | Stddev RTT                            |
| `FgWhite`       | 37        | Standard white      | IP address in ping replies            |
| `FgRed`         | 31        | Standard red        | ERROR label text                      |
| `Bold`          | 1         | Bold text           | Applied to almost all colored text    |

### Color Output Streams

pingu uses two different output streams from the `fatih/color` library:

- **`color.Output`**: Used for normal output (ping replies, statistics). This is a `colorable.Writer` that wraps `os.Stdout` and handles ANSI-to-Console-API translation on Windows.
- **`color.Error`**: Used for error messages. This wraps `os.Stderr` with the same colorable treatment.

The distinction is important because it allows users to redirect stdout (e.g., to a file) while still seeing error messages on the terminal, and vice versa.

### ANSI Escape Sequence Format

For terminals that support ANSI escape sequences (Linux, macOS, modern Windows Terminal), the color output is encoded as:

```
\e[<code>m<text>\e[0m
```

Where `\e` is the escape character (0x1B), `<code>` is the color/style code, and `\e[0m` resets all formatting. For combined attributes (e.g., bold + hi-yellow), the format is:

```
\e[93;1m<text>\e[0m
```

Where `93` is the hi-yellow foreground code and `1` is the bold code.

### Color Disable Conditions

Colors are automatically disabled when:

- `os.Stdout` is not a terminal (detected via `isatty`)
- The `NO_COLOR` environment variable is set (any value)
- `TERM` is set to `dumb`
- The `color.NoColor` global variable is set to `true` programmatically

When colors are disabled, all `color.Sprint`, `color.Printf`, etc. functions return/print the text without ANSI escape sequences.

---

## Building from Source

### Prerequisites

- Go 1.18 or later (the project was developed with Go 1.18.3)
- Git (for version/revision injection)

### Using the Makefile

The project includes a Makefile with several targets:

```
make build      # Build the binary
make fmt        # Format the code
make lint       # Run static analysis
make test       # Run tests with coverage
make coverage   # Generate HTML coverage report
make clean      # Remove build artifacts
```

#### Build Target

```
make build
```

This compiles the binary to `bin/pingu` with version and revision information injected via linker flags:

```
go build -ldflags "-w -s -X main.appVersion=$(VERSION) -X main.appRevision=$(REVISION)" -o bin/pingu
```

The linker flags:
- `-w`: Omit DWARF debugging information (reduces binary size)
- `-s`: Omit the symbol table (further reduces binary size)
- `-X "main.appVersion=$(VERSION)"`: Set the `appVersion` variable to the latest git tag (without the `v` prefix)
- `-X "main.appRevision=$(REVISION)"`: Set the `appRevision` variable to the short hash of the current HEAD commit

The version is extracted from git tags using:
```
git describe --tags --abbrev=0 | tr -d "v"
```

The revision is extracted using:
```
git rev-parse --short HEAD
```

### Using go install

```
go install github.com/sheepla/pingu@latest
```

This installs pingu to `$GOPATH/bin` (or `$GOBIN` if set). Note that when installed this way, the version and revision will show as `???` since no linker flags are set.

### Using go build Directly

```
go build -o pingu
```

This builds the binary in the current directory. As with `go install`, version and revision will be `???` without explicit linker flags.

---

## Version Information

### Version Format

When the `-V` flag is used, pingu prints:

```
pingu: v<VERSION>-rev<REVISION>
```

For example:
```
pingu: v0.10.0-rev926d475
```

### Build-Time Injection

The version and revision are stored in package-level variables:

```go
var (
    appVersion  = "???"
    appRevision = "???"
)
```

These default to `"???"` and are overridden at build time by the linker via `-X` flags. This approach means:

- Release builds (via Makefile or goreleaser) have proper version information
- Development builds (`go build` without flags) show `???`
- The `go-flags` library does not handle version display; it is done manually in the `run()` function before argument validation

### Release Process

The project uses GoReleaser (configured in `.goreleaser.yaml`) for creating release binaries. GoReleaser handles:

- Cross-compilation for multiple OS/architecture combinations
- Binary naming and packaging
- GitHub release creation
- Changelog generation

---

## Continuous vs. Counted Mode

### Counted Mode (Default)

By default, pingu sends 20 ICMP Echo Request packets (the default value of the `-c` flag). After all 20 packets have been sent and their replies received (or timed out), the pinger stops and prints statistics.

This differs from the standard `ping` command, which by default pings continuously until interrupted. pingu's default of 20 was chosen to provide a reasonable amount of data while still terminating automatically.

The count can be customized:

```
pingu -c 5 example.com     # Send 5 packets
pingu -c 100 example.com   # Send 100 packets
pingu -c 1 example.com     # Send 1 packet (quick connectivity check)
```

### Early Termination

In both modes, the user can press Ctrl-C to stop pinging early. When this happens:

1. The signal handler calls `pinger.Stop()`
2. The pinger finishes processing any in-flight packets
3. The `OnFinish` callback fires with statistics for all packets sent/received so far
4. The program exits with code 0

This means you can start a 100-count ping and interrupt it at any time to see partial statistics:

```
pingu -c 100 example.com
# ... after seeing enough replies, press Ctrl-C
# Statistics are shown for however many packets were processed
```

---

## Timing and Intervals

### Default Ping Interval

The default interval between ICMP Echo Requests is determined by the `pro-bing` library's default setting, which is 1 second. This matches the behavior of the standard `ping` command on most systems.

pingu does not expose a CLI flag to change the interval in the current version. The interval is fixed at the library default.

### Round-Trip Time Measurement

RTT is measured by the `pro-bing` library using timestamps embedded in the ICMP packet payload:

1. When sending an Echo Request, the current time is recorded and embedded in the packet payload.
2. When the Echo Reply is received, the embedded timestamp is extracted and compared to the current time.
3. The difference is the RTT, stored as a Go `time.Duration` value.

This approach measures the true network round-trip time, including:
- Network propagation delay (both directions)
- Target host processing time
- Any queuing delays at routers and switches

The RTT does not include:
- Time spent constructing the ICMP packet
- Time spent parsing the reply

### Statistics Calculation

The `pro-bing` library maintains running statistics:

- **MinRtt**: The smallest RTT observed across all received replies
- **MaxRtt**: The largest RTT observed
- **AvgRtt**: The arithmetic mean of all RTTs
- **StdDevRtt**: The population standard deviation of all RTTs

These are calculated incrementally as packets arrive, so the final statistics are available immediately when the pinger stops, without needing a separate computation pass.

---

## Packet Size

pingu does not expose a CLI flag for packet size in the current version. The default ICMP payload size is determined by the `pro-bing` library, which uses a payload large enough to embed a timestamp and other metadata.

The total ICMP packet size includes:
- 8 bytes for the ICMP header (type, code, checksum, identifier, sequence number)
- Variable bytes for the payload (timestamp + padding)

The number of bytes reported in each reply line (`Nbytes`) is the total number of bytes received, which includes both the ICMP header and payload.

---

## TTL (Time to Live)

### What TTL Means

TTL (Time to Live) is a field in the IP header that limits the number of network hops a packet can traverse:

- Each router that forwards the packet decrements the TTL by 1
- If TTL reaches 0, the router drops the packet and sends an ICMP Time Exceeded message back to the sender
- This prevents packets from circulating indefinitely in routing loops

### TTL in pingu Output

pingu displays the TTL value from each received Echo Reply. This value represents the TTL set by the target host, decremented by each intermediate router. The displayed TTL can be used to estimate the number of hops to the target:

```
Estimated hops = Initial TTL - Received TTL
```

Common initial TTL values:
- **64**: Linux, macOS, FreeBSD
- **128**: Windows
- **255**: Cisco routers, some Unix variants

For example, if pinging a Linux host and the received TTL is 56, the estimated hop count is `64 - 56 = 8` hops.

### TTL Configuration

pingu does not expose a CLI flag to set the outgoing TTL in the current version. The TTL is set by the operating system's default value (typically 64 on Linux and macOS).

---

## DNS Resolution

### Hostname Resolution

When a hostname is provided as the target, pingu resolves it to an IP address during the `probing.NewPinger(host)` call. The resolution uses Go's standard library DNS resolver, which:

1. Checks `/etc/hosts` (or equivalent) for static mappings
2. Queries the configured DNS servers (from `/etc/resolv.conf` or system configuration)
3. Returns the first resolved address

The resolved address is used for all subsequent ICMP operations. If the hostname resolves to multiple addresses, only the first one is used.

### Resolution Failure

If DNS resolution fails, `probing.NewPinger()` returns an error, and pingu prints:

```
[ ERROR ] an error occurred while initializing pinger: failed to init pinger <dns error>
```

Common DNS resolution errors:
- "no such host" -- the hostname does not exist in DNS
- "i/o timeout" -- the DNS server did not respond
- "server misbehaving" -- the DNS server returned an invalid response

### Display of Resolved Address

The header line shows both the original hostname and the resolved IP address:

```
PING example.com (93.184.216.34) type `Ctrl-C` to abort
```

In the per-packet output, only the IP address is shown (not the hostname):

```
... seq=0 64bytes from 93.184.216.34: ttl=56 time=11.234ms
```

This matches the behavior of the standard `ping` command.

---

## IPv4 and IPv6

### Automatic Protocol Selection

pingu uses whichever protocol the DNS resolver returns for the given hostname. If a hostname resolves to an IPv4 address, IPv4 ICMP (type 8/0) is used. If it resolves to an IPv6 address, IPv6 ICMPv6 (type 128/129) is used.

### Explicit Protocol Selection

The current version of pingu does not have `-4` or `-6` flags. The protocol is determined solely by the DNS resolution result or the address format:

- Providing an IPv4 address (e.g., `8.8.8.8`) forces IPv4
- Providing an IPv6 address (e.g., `2001:4860:4860::8888`) forces IPv6
- Providing a hostname leaves the choice to the DNS resolver

### IPv6 Considerations

When pinging IPv6 addresses:
- The ICMP type changes from 8/0 to 128/129
- The raw socket uses `AF_INET6` instead of `AF_INET`
- Some systems require different privileges for IPv6 raw sockets
- The output format remains the same, but the IP address field shows the full IPv6 address

---

## Real-Time Output Streaming

### Callback-Based Architecture

pingu uses a callback-based architecture for real-time output. Rather than collecting all results and printing them at the end, the `pro-bing` library invokes registered callbacks as events occur:

- **`OnRecv`**: Called immediately when an ICMP Echo Reply is received. This triggers the per-packet output line with the penguin ASCII art.
- **`OnFinish`**: Called when the pinger stops (either by reaching the count or by being stopped manually). This triggers the statistics summary.

This design ensures that each ping reply appears on the terminal as soon as it arrives, providing real-time feedback to the user.

### Concurrency Model

The `pro-bing` library uses multiple goroutines internally:

1. **Sender goroutine**: Sends ICMP Echo Request packets at regular intervals (every 1 second by default). This goroutine sleeps between sends.

2. **Receiver goroutine**: Continuously reads from the ICMP socket, waiting for incoming packets. When a valid Echo Reply is received, it invokes the `OnRecv` callback.

3. **Signal handler goroutine**: Waits for SIGINT and calls `pinger.Stop()` when received.

The `OnRecv` callback is called from the receiver goroutine. Since the callback performs I/O (writing to stdout), and Go's `fmt.Fprintf` is goroutine-safe (it acquires a lock on the writer), the output is serialized even though it originates from a concurrent goroutine.

### Buffering Behavior

Terminal output buffering affects how quickly pingu's output appears:

- When stdout is a terminal (the common case), Go's `fmt.Fprintf` to `color.Output` is line-buffered by default. Each reply line is flushed immediately because it ends with `\n`.
- When stdout is piped to another process, the output may be fully buffered by the OS, causing delays. The `go-colorable` library does not add additional buffering beyond what the OS provides.

### Output Ordering

Because pingu uses a single receiver goroutine that calls `OnRecv` sequentially for each received packet, output lines appear in the order packets are received. In normal operation, this matches the sequence number order. However, if packets arrive out of order (which is possible on congested networks), the output lines will also appear out of order.

Duplicate replies (e.g., from certain network configurations) are not handled specially by pingu's callbacks -- only `OnRecv` is registered, not `OnDuplicateRecv`. If the `pro-bing` library detects a duplicate, it is silently ignored.

---

## Detailed ASCII Art Analysis

### Character-by-Character Breakdown

The penguin figure is composed of distinct anatomical regions, each mapped to a color:

**Head (lines 2-6)**:
The penguin's head appears in the upper portion of the art. The outer silhouette is rendered in `B` (black/dark gray), with `W` (white) regions for the face and eye areas. The shape suggests a round head with a slight beak protrusion.

**Eyes (lines 5-7)**:
The `WW` and `WWBB` patterns in lines 5-7 create a suggestion of eyes. The `WW` regions represent the white sclera, with `BB` between them forming the dark pupils or eye outlines.

**Beak (lines 7-9)**:
The `R` (red) characters in lines 7-9 form the penguin's beak. The pattern `RRRRRRR` creates a triangular beak shape pointing to the right. The beak is the most prominent red feature in the figure.

**Body (lines 3-19)**:
The main body outline is composed entirely of `B` characters, forming a rounded body shape that is wider at the middle and tapers at the top (head) and bottom (feet). The body is the largest region in the art.

**Belly (lines 13-19)**:
The lower portion of the body contains `W` (white) characters representing the penguin's characteristic white belly. The `YWW` patterns in lines 13-14 indicate the transition zone between the body and belly, with `Y` (yellow) accents.

**Feet (lines 14-19)**:
The `Y` and `W` characters at the bottom form the penguin's feet/flippers. The `YWWWWWWWWWWWW` patterns suggest webbed feet extending to the right.

**Snow/Background (all lines)**:
The `.` (dot) characters scattered throughout the art represent falling snow or a winter background. They are denser in some areas than others, creating a sense of depth and atmosphere.

### Art Dimensions

- **Width**: Approximately 57 characters per line (including trailing spaces)
- **Height**: 20 lines
- **Total characters**: Approximately 1,140 characters (before colorization)
- **After colorization**: Significantly longer due to ANSI escape sequences (each colored `#` character is wrapped in approximately 10-12 bytes of escape sequence overhead)

### Rendering Performance

Each line of the art undergoes four `strings.ReplaceAll` operations (one per color). For a 57-character line with approximately 15-20 color placeholder characters, this involves:

1. Scanning the entire string for `R` characters and replacing each
2. Scanning the result for `Y` characters and replacing each
3. Scanning the result for `B` characters and replacing each
4. Scanning the result for `W` characters and replacing each

Each replacement creates a new string (Go strings are immutable). For a typical line with 30 placeholder characters across all four colors, this means 4 string scans and approximately 30 string allocations per line. At 1 line per second (one per ping reply), this overhead is negligible.

### Ordering of Colorization

The order of the four `colorize()` calls matters because the replacement character `#` is the same for all four colors. However, since each color targets a different placeholder character (`R`, `Y`, `B`, `W`), and these characters do not conflict with the `#` output character (which is wrapped in ANSI escape sequences), the order does not affect the visual result. Each placeholder character is uniquely consumed in exactly one pass.

The only scenario where order could matter is if the `#` character appeared in the original art, which it does not. All characters in the art are limited to: `B`, `W`, `R`, `Y`, `.`, and space.

---

## Comparison with Standard Ping

### Feature Comparison

| Feature                  | Standard `ping`            | `pingu`                       |
|--------------------------|----------------------------|-------------------------------|
| ICMP implementation      | Built into the binary      | Via pro-bing Go library       |
| Packet count flag        | `-c N`                     | `-c N` (default 20)          |
| Default count            | Unlimited (until Ctrl-C)   | 20                            |
| Interval flag            | `-i N`                     | Not exposed                   |
| Timeout flag             | `-W N`                     | Not exposed                   |
| Packet size flag         | `-s N`                     | Not exposed                   |
| TTL flag                 | `-t N` (Linux) / `-m N` (macOS) | Not exposed             |
| IPv4 force               | `-4`                       | Not exposed                   |
| IPv6 force               | `-6`                       | Not exposed                   |
| Color output             | None                       | Full color with per-field colors |
| ASCII art                | None                       | Penguin art per line          |
| Privileged mode          | Required on most systems   | Optional (`-P`)               |
| Output format            | Standard text              | Colorized with art prefix     |
| Exit code on packet loss | 1                          | 0                             |

### Output Format Comparison

**Standard ping output**:
```
PING example.com (93.184.216.34) 56(84) bytes of data.
64 bytes from 93.184.216.34: icmp_seq=1 ttl=56 time=11.2 ms
64 bytes from 93.184.216.34: icmp_seq=2 ttl=56 time=11.1 ms
64 bytes from 93.184.216.34: icmp_seq=3 ttl=56 time=11.3 ms

--- example.com ping statistics ---
3 packets transmitted, 3 received, 0% packet loss, time 2003ms
rtt min/avg/max/mdev = 11.100/11.200/11.300/0.081 ms
```

**pingu output** (colors and art omitted):
```
PING example.com (93.184.216.34) type `Ctrl-C` to abort
<art> seq=0 64bytes from 93.184.216.34: ttl=56 time=11.2ms
<art> seq=1 64bytes from 93.184.216.34: ttl=56 time=11.1ms
<art> seq=2 64bytes from 93.184.216.34: ttl=56 time=11.3ms

───────── example.com ping statistics ─────────
PACKET STATISTICS: 3 transmitted => 3 received (0% loss)
ROUND TRIP: min=11.1ms avg=11.2ms max=11.3ms stddev=81.65us
```

Key differences:
- pingu uses 0-based sequence numbers (standard ping uses 1-based)
- pingu does not show the total data size in the header (no "56(84) bytes of data")
- pingu uses `=>` instead of commas to separate transmitted and received counts
- pingu uses `stddev` instead of `mdev`
- pingu uses Unicode box-drawing characters in the statistics header
- pingu does not show the total time elapsed

---

## Packet Loss Handling

### No Explicit Loss Display Per-Packet

pingu does not display an explicit message when a packet is lost (i.e., when no reply is received within the timeout period). The `OnRecv` callback is only invoked when a reply is received. If a packet times out, nothing is printed for that sequence number.

This differs from the standard `ping` command, which displays timeout messages:
```
Request timeout for icmp_seq 5
```

With pingu, a timeout is only visible as:
1. A gap in the sequence number progression (e.g., seq=3 followed by seq=5, indicating seq=4 was lost)
2. The packet loss percentage in the final statistics

### Loss Statistics

Packet loss is calculated by the `pro-bing` library as:

```
PacketLoss = ((PacketsSent - PacketsRecv) / PacketsSent) * 100
```

The loss percentage is displayed in the final statistics with the `%` sign and formatted in hi-red bold:

```
PACKET STATISTICS: 10 transmitted => 8 received (20% loss)
```

---

## Memory and Resource Usage

### Memory Footprint

pingu's memory usage is minimal:

- The binary itself is small (a few MB after stripping debug symbols with `-w -s`)
- The penguin ASCII art is a constant 20-element string slice (~1.2 KB)
- Each in-flight ICMP packet consumes a small amount of memory for tracking (managed by pro-bing)
- Color formatting creates temporary string allocations that are quickly garbage collected

### File Descriptors

pingu uses the following file descriptors:

- stdin (fd 0): Not used
- stdout (fd 1): Used for normal output (via `color.Output`)
- stderr (fd 2): Used for error output (via `color.Error`)
- ICMP socket: One raw or UDP socket for sending and receiving ICMP packets

### Goroutine Count

During operation, pingu runs approximately 4-5 goroutines:

1. The main goroutine (blocked on `pinger.Run()`)
2. The ICMP sender goroutine
3. The ICMP receiver goroutine
4. The signal handler goroutine
5. Any internal goroutines used by `pro-bing` for timing

---

## Potential Failure Modes

### Permission Denied

The most common failure mode. Occurs when:

- Running in unprivileged mode on a system that doesn't support unprivileged ICMP
- Running in privileged mode without root or `CAP_NET_RAW`
- Running in WSL without the proper capability set

**Symptoms**: `pinger.Run()` returns an error immediately, before any packets are sent.

**Resolution**: Use the `-P` flag with appropriate privileges, or configure unprivileged ICMP:

```bash
# Option 1: Run as root
sudo pingu example.com

# Option 2: Set capability (persists across runs)
sudo setcap cap_net_raw=+ep /path/to/pingu
pingu -P example.com

# Option 3: Configure unprivileged ICMP (Linux only, persists until reboot)
sudo sysctl -w net.ipv4.ping_group_range="0 2147483647"
pingu example.com
```

### DNS Resolution Failure

Occurs when the target hostname cannot be resolved to an IP address.

**Symptoms**: pingu exits with an error message containing "failed to init pinger" and the DNS error.

**Resolution**: Verify the hostname is correct, check DNS configuration, or use an IP address directly.

### Network Unreachable

Occurs when there is no route to the target host.

**Symptoms**: `pinger.Run()` may return an error, or packets may be sent but no replies received (100% loss).

**Resolution**: Check network connectivity, routing tables, and firewall rules.

### Firewall Blocking

ICMP traffic is sometimes blocked by firewalls at the source, destination, or intermediate network devices.

**Symptoms**: Packets are sent but no replies are received. The output shows sequence numbers but with gaps or complete silence.

**Resolution**: Check firewall rules on the local machine, target machine, and any intermediate firewalls.

### Invalid Count Value

Occurs when a non-integer value is passed to `-c`.

**Symptoms**: The `go-flags` parser reports an error: "expected int".

**Resolution**: Provide a valid positive integer.

---

## Environment Variables

pingu itself does not define or read any custom environment variables. However, the following standard environment variables affect its behavior through the underlying libraries:

### NO_COLOR

When set (to any value), the `fatih/color` library disables all color output. pingu's output will be plain text without ANSI escape sequences.

```
NO_COLOR=1 pingu example.com
```

### TERM

If set to `dumb`, the `fatih/color` library disables color output, similar to `NO_COLOR`.

```
TERM=dumb pingu example.com
```

### PATH

The Go runtime uses `PATH` for external command lookups, but pingu does not invoke any external commands, so this only affects Go's internal DNS resolution (which may use `nslookup` or similar on some platforms).

### HOME, USER

Standard environment variables that may affect Go's DNS resolution behavior (e.g., reading `~/.resolv.conf` on some systems).

---

## Piping and Redirection

### Piping stdout

When stdout is piped to another program, colors are automatically disabled by the `fatih/color` library (due to TTY detection). The ASCII art characters and structure are preserved but without color codes:

```
pingu -c 3 example.com | cat
```

Output will contain `#` characters (the replacement character used in the penguin art) but without ANSI escape sequences.

### Redirecting to a File

Similarly, redirecting to a file produces uncolorized output:

```
pingu -c 3 example.com > output.txt
```

### Stderr vs. Stdout

Error messages go to stderr, so they can be separated from normal output:

```
pingu -c 3 example.com > output.txt 2> errors.txt
```

### Force Color

There is no built-in flag to force color output when stdout is not a terminal. However, the `fatih/color` library can be configured via the `color.NoColor` global variable, which is not exposed by pingu's CLI.

---

## Comparison with Other Ping Wrappers

### pingu vs. gping

`gping` is another ping visualization tool that provides a graphical TUI (text-based user interface) with a live-updating graph of ping latency over time. In contrast, pingu provides a simpler line-by-line output with ASCII art and colors. gping is more suited for long-running monitoring, while pingu is designed for quick, visually appealing connectivity checks.

### pingu vs. prettyping

`prettyping` is a wrapper around the system `ping` command that provides colorized output with a compact, graphical representation of packet loss. It processes the output of the standard `ping` command, while pingu implements ICMP natively via the pro-bing library.

### pingu vs. Standard ping

Standard `ping` is universally available, requires no installation, and produces plain text output optimized for machine parsing. pingu adds visual appeal at the cost of portability and parseability. The colored output and ASCII art make pingu more engaging for interactive use but less suitable for scripting.

---

## Sequence Number Behavior

### Zero-Based Indexing

pingu uses 0-based sequence numbers, following the pro-bing library's convention. The first packet has `seq=0`, the second `seq=1`, and so on. This differs from the standard `ping` command which uses 1-based sequence numbers (`icmp_seq=1` for the first packet).

### Modular Art Selection

The sequence number is used directly as the index for selecting the ASCII art line. The modulo operation (`idx %= len(pingu)`, where `len(pingu)` is 20) ensures the index stays within bounds. This creates a cyclic pattern:

| Seq Range | Art Lines Displayed |
|-----------|---------------------|
| 0-19      | Lines 0-19 (full penguin) |
| 20-39     | Lines 0-19 (repeat) |
| 40-59     | Lines 0-19 (repeat) |
| ...       | ...                 |

### Gap Behavior

If a packet is lost (no reply received), the art line for that sequence number is skipped. For example, if packets 5 and 6 are lost:

```
<line 4> seq=4 ...
<line 7> seq=7 ...
```

Lines 5 and 6 of the penguin art are never shown. This means packet loss causes visual gaps in the penguin rendering.

---

## go-flags Parser Configuration

### Parser Options

pingu creates the go-flags parser with `flags.Default`, which is a combination of:

- `flags.HelpFlag`: Adds `-h, --help` flag
- `flags.PrintErrors`: Prints errors to stderr
- `flags.PassDoubleDash`: Passes `--` through as a positional argument

### Parser Metadata

The parser is configured with the following metadata:

- **Name**: `pingu`
- **Usage**: `[OPTIONS] HOST`
- **ShortDescription**: `` `ping` command but with pingu ``
- **LongDescription**: `` `ping` command but with pingu ``

Both the short and long descriptions are identical, which means the help output shows the same description in both the brief and extended help sections.

---

## Goreleaser Configuration

The project includes a `.goreleaser.yaml` file for automated release builds. GoReleaser handles:

- Cross-compilation for multiple platforms (linux/amd64, linux/arm64, darwin/amd64, darwin/arm64, windows/amd64, etc.)
- Creating compressed archives (tar.gz for Unix, zip for Windows)
- Generating checksums
- Creating GitHub releases with changelogs
- Injecting version information via ldflags

The goreleaser configuration ensures that released binaries have proper version and revision information (unlike manual `go build` which defaults to `???`).

---

## Internal Data Structures

### options struct

```go
type options struct {
    Count     int  `short:"c" long:"count" default:"20" description:"Stop after <count> replies"`
    Privilege bool `short:"P" long:"privilege" description:"Enable privileged mode"`
    Version   bool `short:"V" long:"version" description:"Show version"`
}
```

Fields:
- `Count` (int): The number of ICMP packets to send. Tagged with `default:"20"` so go-flags automatically sets this if the user doesn't specify `-c`.
- `Privilege` (bool): Whether to use raw sockets. False by default (bool zero value).
- `Version` (bool): Whether to display version info and exit. False by default.

### exitCode type

```go
type exitCode int

const (
    exitCodeOK exitCode = iota    // 0
    exitCodeErrArgs               // 1
    exitCodeErrPing               // 2
)
```

An integer alias type with three named constants using `iota` for auto-incrementing values.

### probing.Packet struct (from pro-bing)

The `OnRecv` callback receives a `*probing.Packet` with the following fields used by pingu:

- `Seq` (int): The ICMP sequence number
- `Nbytes` (int): Number of bytes in the reply
- `IPAddr` (*net.IPAddr): The source IP address of the reply
- `TTL` (int): The TTL value from the IP header
- `Rtt` (time.Duration): The round-trip time

### probing.Statistics struct (from pro-bing)

The `OnFinish` callback receives a `*probing.Statistics` with the following fields used by pingu:

- `Addr` (string): The target address (hostname or IP)
- `PacketsSent` (int): Total number of Echo Requests sent
- `PacketsRecv` (int): Total number of Echo Replies received
- `PacketLoss` (float64): Percentage of packets lost (0.0 to 100.0)
- `MinRtt` (time.Duration): Minimum round-trip time
- `AvgRtt` (time.Duration): Average round-trip time
- `MaxRtt` (time.Duration): Maximum round-trip time
- `StdDevRtt` (time.Duration): Standard deviation of round-trip times

---

## Terminal Compatibility

### Minimum Terminal Requirements

pingu requires a terminal that supports:

- Standard output (stdout) for printing
- At least ~130 columns for non-wrapping display (57 for art + ~73 for ping data)
- ANSI escape sequence support for colors (or Windows Console API support)

### Terminal Emulators

pingu has been observed to work correctly with:

- **Linux**: gnome-terminal, konsole, xterm, alacritty, kitty, tmux, screen
- **macOS**: Terminal.app, iTerm2, alacritty, kitty
- **Windows**: Windows Terminal, PowerShell, cmd.exe (with go-colorable translation)

### Color Scheme Considerations

Because pingu uses both "Hi" (high-intensity) and standard color variants, the visual appearance depends heavily on the terminal's color scheme:

- **Dark backgrounds**: All colors are typically visible. HiBlack (dark gray) for the penguin body may appear very dark and subtle.
- **Light backgrounds**: HiBlack may blend into the background. HiWhite may be hard to see against white backgrounds. The penguin art may appear partially invisible.
- **Solarized themes**: May map colors differently, causing unexpected color combinations.
- **256-color and truecolor terminals**: pingu only uses the 16 standard ANSI colors (8 normal + 8 high-intensity), so it works identically in 16-color, 256-color, and truecolor terminals.

### Unicode Support

The statistics header uses Unicode box-drawing characters (`─`, U+2500). Terminals that do not support Unicode will display these as replacement characters or garbled output. Modern terminals universally support UTF-8, but legacy terminals (particularly on older systems or serial consoles) may have issues.

The penguin ASCII art itself uses only ASCII characters (letters, dots, spaces), so it displays correctly on any terminal regardless of Unicode support.

---

## Networking Fundamentals

### ICMP Protocol Overview

ICMP (Internet Control Message Protocol) is a network-layer protocol used by network devices to communicate diagnostic information. It is defined in RFC 792 (for IPv4) and RFC 4443 (for IPv6).

The ping utility uses two specific ICMP message types:

- **Echo Request** (Type 8 for IPv4, Type 128 for IPv6): Sent by the pinger to the target host, asking for a reply.
- **Echo Reply** (Type 0 for IPv4, Type 129 for IPv6): Sent by the target host back to the pinger, confirming receipt of the request.

Each Echo Request/Reply pair contains:
- **Identifier**: Used to match replies to the correct pinger process (especially when multiple ping instances are running)
- **Sequence Number**: Used to match replies to specific requests and detect packet loss
- **Payload**: Arbitrary data (typically used for timestamps and padding)

### How Ping Works at the Network Level

1. The pinger constructs an ICMP Echo Request packet with a unique identifier, incrementing sequence number, and timestamp payload.
2. The packet is encapsulated in an IP datagram and sent to the target host.
3. Each router along the path decrements the TTL. If TTL reaches 0, the router sends an ICMP Time Exceeded message back.
4. The target host receives the Echo Request, constructs an Echo Reply with the same identifier, sequence number, and payload, and sends it back.
5. The pinger receives the Echo Reply, extracts the timestamp from the payload, and calculates the round-trip time.

### Common ICMP Error Messages

Beyond Echo Request/Reply, ICMP can deliver several error types that pingu may encounter:

- **Destination Unreachable** (Type 3): The target host or network cannot be reached. Subtypes include network unreachable, host unreachable, port unreachable, and fragmentation needed.
- **Time Exceeded** (Type 11): The TTL reached 0, or fragment reassembly timed out.
- **Redirect** (Type 5): The router suggests a better route for the target.

The `pro-bing` library handles these messages internally and may report them as errors or lost packets, depending on the specific error type.

### Raw Sockets vs. UDP Sockets for ICMP

Operating systems provide two mechanisms for user-space programs to send ICMP packets:

**Raw sockets** (`SOCK_RAW` with `IPPROTO_ICMP`):
- Provide direct access to the ICMP protocol
- The application constructs the entire ICMP packet (header + payload)
- The application controls the ICMP identifier
- Require elevated privileges (root or `CAP_NET_RAW`)
- Most reliable and portable method

**UDP sockets** (datagram ICMP):
- Available on Linux kernels 3.0+ with appropriate `ping_group_range` configuration
- The kernel transparently translates UDP datagrams to ICMP Echo Requests
- The kernel assigns the ICMP identifier (the application cannot control it)
- Do not require elevated privileges
- May not work on all systems or configurations

pingu supports both mechanisms via the `-P` flag, allowing it to work in the widest range of system configurations.

---

## Performance Characteristics

### CPU Usage

pingu's CPU usage is minimal during normal operation:

- Between pings (1 second intervals), the process is largely idle, blocked on socket I/O
- When a reply arrives, CPU is briefly used for packet parsing, string formatting, color rendering, and output
- The string operations for ASCII art colorization are fast (microsecond scale for a 57-character string)
- Color output adds minimal overhead through ANSI escape sequence insertion

### Network Usage

pingu sends one ICMP packet per second (default interval) and expects one reply per packet. The total bandwidth is negligible:

- Each ICMP packet is typically 64 bytes (8 header + 56 data)
- At 1 packet per second, this is 64 bytes/second in each direction
- Total bandwidth: approximately 128 bytes/second (0.001 Mbit/s)

### Startup Time

pingu's startup time includes:

1. Binary loading and Go runtime initialization: ~5-10ms
2. Argument parsing: <1ms
3. DNS resolution: 1-100ms (varies by DNS server latency and caching)
4. Socket creation: <1ms
5. First packet send: <1ms

Total typical startup time: 10-120ms, dominated by DNS resolution.

---

## Troubleshooting Guide

### "operation not permitted" Error

**Problem**: `pinger.Run()` returns a permission error.

**Cause**: The system does not allow the current user to create raw or UDP ICMP sockets.

**Solutions** (in order of preference):

1. Configure unprivileged ICMP (Linux only):
   ```
   sudo sysctl -w net.ipv4.ping_group_range="0 2147483647"
   ```

2. Set the `CAP_NET_RAW` capability:
   ```
   sudo setcap cap_net_raw=+ep /path/to/pingu
   pingu -P example.com
   ```

3. Run as root:
   ```
   sudo pingu -P example.com
   ```

### No Output After Header

**Problem**: The header line prints but no ping replies appear.

**Possible causes**:
- The target host is not responding (firewall, host down, network issue)
- ICMP is being filtered by a local or remote firewall
- DNS resolved to an unreachable address

**Diagnosis**:
- Try pinging the same host with the standard `ping` command to compare
- Try pinging a known-reachable host (e.g., `127.0.0.1` or `localhost`)
- Check firewall rules with `iptables -L` (Linux) or `pfctl -sr` (macOS)

### Garbled or Missing Art

**Problem**: The penguin art appears garbled or partially invisible.

**Possible causes**:
- Terminal does not support ANSI colors
- Terminal color scheme makes certain colors invisible (e.g., HiBlack on black background)
- Terminal width is too narrow, causing line wrapping that breaks the art alignment

**Solutions**:
- Try a different terminal emulator
- Adjust the terminal's color scheme
- Increase the terminal width to at least 130 columns

### Version Shows "???"

**Problem**: `pingu -V` shows `pingu: v???-rev???`.

**Cause**: The binary was built without linker flags to inject version information.

**Solution**: Build using the Makefile:
```
make build
./bin/pingu -V
```

Or manually specify linker flags:
```
go build -ldflags '-X "main.appVersion=1.0.0" -X "main.appRevision=abc1234"' -o pingu
```

---

## Security Considerations

### Privilege Escalation

Setting the `CAP_NET_RAW` capability on the pingu binary allows any user to send ICMP packets. This is generally safe but should be considered in environments where ICMP is restricted for security reasons.

### Network Scanning

pingu can be used for basic network reconnaissance (identifying live hosts). While this is a legitimate use case, administrators should be aware that allowing ICMP can reveal network topology information.

### Input Validation

pingu relies on the `go-flags` parser and the `pro-bing` library for input validation. The hostname is passed directly to the DNS resolver, and the count value is parsed as an integer by `go-flags`. No additional input sanitization is performed, but since pingu does not invoke shell commands or perform file operations based on user input, the attack surface is minimal.

### No Subprocess Invocation

Unlike ping wrappers that shell out to the system `ping` command, pingu does not invoke any external processes. This eliminates the risk of command injection through crafted hostnames.

---

## Limitations and Known Issues

### Fixed Default Count

The default count of 20 differs from standard `ping`'s infinite-by-default behavior. Users accustomed to standard `ping` may be surprised that pingu stops after 20 packets. There is no way to specify "unlimited" via the CLI -- the user must set a very large count or rely on Ctrl-C.

### No Interval Control

The current version does not expose a flag for the ping interval. Users cannot speed up or slow down the ping rate.

### No Timeout Control

There is no `-W` or `--timeout` flag. The receive timeout is determined by the `pro-bing` library defaults.

### No Packet Size Control

There is no `-s` or `--size` flag. The packet size is fixed at the library default.

### No TTL Control

There is no `-t` or `--ttl` flag. The outgoing TTL is set by the OS default.

### No IPv4/IPv6 Force Flags

There are no `-4` or `-6` flags. Protocol selection is automatic based on DNS resolution or the address format provided.

### No Per-Packet Loss Indication

When a packet is lost, pingu does not print a timeout message. The loss is only visible in the final statistics or by noticing gaps in sequence numbers.

### Exit Code on Initialization Error

If `probing.NewPinger()` fails, the exit code is 0 (not 2), even though an error is printed. This may confuse scripts that rely on exit codes to detect failures.

### No Adaptive Art for Terminal Width

The penguin art is a fixed width and does not adapt to narrow terminals. On terminals narrower than ~130 columns, the output wraps, breaking the visual alignment.

### Sequence Number Display

pingu uses 0-based sequence numbers while standard `ping` uses 1-based. This may confuse users comparing output between the two tools.

---

## Source Code Reference

### File Structure

The entire application is in a single file:

```
main.go    # ~200 lines, all application logic
go.mod     # Go module definition
go.sum     # Dependency checksums
Makefile   # Build automation
```

### Key Functions

| Function           | Lines | Purpose                                          |
|--------------------|-------|--------------------------------------------------|
| `main()`           | ~10   | Entry point, delegates to run(), handles errors   |
| `run()`            | ~30   | Argument parsing, validation, orchestration       |
| `initPinger()`     | ~25   | Pinger creation, signal handling, callback setup  |
| `pingerOnrecv()`   | ~10   | Per-packet output with art and colors             |
| `pingerOnFinish()` | ~15   | Statistics summary output                         |
| `renderASCIIArt()` | ~10   | Art line selection and colorization               |
| `colorize()`       | ~5    | Character-to-colored-hash replacement             |

### Global Variables

| Variable         | Type       | Purpose                                    |
|------------------|------------|--------------------------------------------|
| `pingu`          | `[]string` | The 20-line penguin ASCII art              |
| `appName`        | `string`   | Application name ("pingu")                 |
| `appUsage`       | `string`   | Usage string ("[OPTIONS] HOST")            |
| `appDescription` | `string`   | Description ("`ping` command but with pingu") |
| `appVersion`     | `string`   | Version (set via ldflags, default "???")   |
| `appRevision`    | `string`   | Git revision (set via ldflags, default "???") |

---

## Summary

pingu is a compact, visually engaging alternative to the standard `ping` command. Its key characteristics are:

- **Native ICMP**: Uses the pro-bing library for direct ICMP operations, not a subprocess wrapper
- **Visual appeal**: Penguin ASCII art and per-field color coding make the output distinctive and fun
- **Simplicity**: The entire application is ~200 lines of Go in a single file
- **Cross-platform**: Works on Linux, macOS, and Windows with automatic platform adaptation
- **Minimal dependencies**: Only three external libraries (color, flags, pro-bing)
- **Safe defaults**: Unprivileged mode by default, 20-packet count, graceful Ctrl-C handling

The tool trades some features of the standard `ping` command (interval control, packet size, TTL configuration, explicit timeout) for visual presentation and ease of use. It is best suited for interactive use where the user wants a quick, visually appealing connectivity check rather than detailed network diagnostics.
