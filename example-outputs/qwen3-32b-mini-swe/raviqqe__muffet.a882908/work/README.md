# Muffet

![demo](img/demo.gif)

Muffet is a fast website link checker which scrapes and inspects all pages in a website recursively.

## Features

- Massive speed
- High compatibility with web browsers
- Different tag support (`a`, `img`, `link`, `script`, etc)
- Multiple output formats (text, JSON, and JUnit XML)

## Installation

### Go

If you have Go installed:

```sh
go install github.com/raviqqe/muffet/v2@latest
```

### Homebrew

On macOS and Linux:

```sh
brew install muffet
```

### Docker

```sh
docker pull raviqqe/muffet
```

## Usage

### Command line

Check a website:

```sh
muffet https://example.com
```

### Docker

```sh
docker run raviqqe/muffet https://example.com
```

### GitHub Action

[My Broken Link Checker](https://github.com/ruzickap/action-my-broken-link-checker) is a third-party GitHub Action that uses Muffet to test static websites.

## License

[MIT](LICENSE)
