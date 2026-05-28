package main

import (
	"flag"
	"fmt"
	"os"
	"strings"
	"csv"
	"bufio"
	"unicode/utf8"
)

var (
	noHeaders = flag.Bool("H", false, "Input has no header row")
	lineNumbers = flag.Bool("n", false, "Add line numbers column")
	tsvMode = flag.Bool("t", false, "Use tab as delimiter")
	delimiter = flag.String("d", ",", "Field delimiter")
	style = flag.String("s", "sharp", "Border style")
	padding = flag.Int("p", 1, "Cell padding")
	indent = flag.Int("i", 0, "Global indent")
	sniffLimit = flag.Int("sniff", 1000, "Sniff limit for column widths")
	headerAlign = flag.String("header-align", "center", "Header alignment")
	bodyAlign = flag.String("body-align", "left", "Body alignment")
	disablePager = flag.Bool("P", false, "Disable pager")
	version = flag.Bool("V", false, "Print version")
	help = flag.Bool("h", false, "Print help")
)

func main() {
	flag.Parse()

	if *version {
		fmt.Println("csview 1.3.4")
		return
	}

	if *help {
		fmt.Println("A high performance csv viewer with cjk/emoji support.")
		fmt.Println("Usage: executable [OPTIONS] [FILE]")
		flag.PrintDefaults()
		return
	}

	var filePath string
	if flag.NArg() > 0 {
		filePath = flag.Arg(0)
	}

	var file *os.File
	var err error
	if filePath != "" {
		file, err = os.Open(filePath)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error opening file: %v\n", err)
			os.Exit(1)
		}
		defer file.Close()
	} else {
		file = os.Stdin
	}

	var delimiterChar rune
	if *tsvMode {
		delimiterChar =  
	} else if len(*delimiter) > 0 {
		delimiterChar = rune(*delimiter[0])
	} else {
		delimiterChar = ,
	}

	reader := csv.NewReader(bufio.NewReader(file))
	reader.Comma = delimiterChar
	rows, err := reader.ReadAll()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error reading CSV: %v\n", err)
		os.Exit(1)
	}

	if *lineNumbers {
		for i := range rows {
			rows[i] = append([]string{fmt.Sprintf("%d", i+1)}, rows[i]...)
		}
	}

	header := make([]string, 0)
	bodyRows := rows
	if !*noHeaders && len(rows) > 0 {
		header = rows[0]
		bodyRows = rows[1:]
	}

	maxWidths := calculateColumnWidths(bodyRows, *sniffLimit)
	table := renderTable(header, bodyRows, maxWidths, *headerAlign, *bodyAlign, *style, *padding, *indent)

	fmt.Print(table)
}

func calculateColumnWidths(rows [][]string, sniffLimit int) []int {
	if len(rows) == 0 {
		return []int{}
	}
	maxWidths := make([]int, len(rows[0]))

	maxRows := len(rows)
	if sniffLimit > 0 && sniffLimit < maxRows {
		maxRows = sniffLimit
	}

	for i := 0; i < maxRows; i++ {
		for j, cell := range rows[i] {
			width := utf8.RuneCountInString(cell)
			if width > maxWidths[j] {
				maxWidths[j] = width
			}
		}
	}
	return maxWidths
}

func renderTable(header []string, body [][]string, maxWidths []int, headerAlign, bodyAlign string, style string, padding, indent int) string {
	styleChars := getStyleChars(style)
	horizontal := styleChars["horizontal"]
	vertical := styleChars["vertical"]
	topLeft := styleChars["topLeft"]
	topRight := styleChars["topRight"]
	bottomLeft := styleChars["bottomLeft"]
	bottomRight := styleChars["bottomRight"]
	headerSeparator := styleChars["headerSeparator"]

	if len(maxWidths) == 0 {
		return ""
	}

	colWidths := make([]int, len(maxWidths))
	for i, w := range maxWidths {
		colWidths[i] = w + 2*padding
	}

	var output strings.Builder
	output.WriteString(strings.Repeat(" ", indent))
	output.WriteString(topLeft)
	for i, cw := range colWidths {
		output.WriteString(strings.Repeat(horizontal, cw))
		if i != len(colWidths)-1 {
			output.WriteString("┬")
		}
	}
	output.WriteString(topRight)
	output.WriteString("\n")

	// Render header if not noHeaders and header is non-empty
	if !*noHeaders && len(header) > 0 {
		output.WriteString(strings.Repeat(" ", indent))
		output.WriteString(vertical)
		for i, h := range header {
			output.WriteString(formatCell(h, maxWidths[i], headerAlign, padding))
			output.WriteString(vertical)
		}
		output.WriteString("\n")

		// Header separator
		output.WriteString(strings.Repeat(" ", indent))
		output.WriteString("├")
		for i, cw := range colWidths {
			output.WriteString(strings.Repeat(headerSeparator, cw))
			if i != len(colWidths)-1 {
				output.WriteString("┼")
			}
		}
		output.WriteString("┤")
		output.WriteString("\n")
	}

	// Render body rows
	for _, row := range body {
		output.WriteString(strings.Repeat(" ", indent))
		output.WriteString(vertical)
		for i, cell := range row {
			output.WriteString(formatCell(cell, maxWidths[i], bodyAlign, padding))
			output.WriteString(vertical)
		}
		output.WriteString("\n")
	}

	// Bottom border
	output.WriteString(strings.Repeat(" ", indent))
	output.WriteString(bottomLeft)
	for i, cw := range colWidths {
		output.WriteString(strings.Repeat(horizontal, cw))
		if i != len(colWidths)-1 {
			output.WriteString("┴")
		}
	}
	output.WriteString(bottomRight)
	output.WriteString("\n")

	return output.String()
}

func getStyleChars(style string) map[string]string {
	switch style {
	case "none":
		return map[string]string{
			"horizontal":  " ",
			"vertical":    " ",
			"topLeft":     " ",
			"topRight":    " ",
			"bottomLeft":  " ",
			"bottomRight": " ",
			"headerSeparator": " ",
		}
	case "ascii":
		return map[string]string{
			"horizontal":  "-",
			"vertical":    "|",
			"topLeft":     "+",
			"topRight":    "+",
			"bottomLeft":  "+",
			"bottomRight": "+",
			"headerSeparator": "-",
		}
	case "ascii2":
		return map[string]string{
			"horizontal":  "-",
			"vertical":    "|",
			"topLeft":     "+",
			"topRight":    "+",
			"bottomLeft":  "-",
			"bottomRight": "+",
			"headerSeparator": "=",
		}
	case "sharp":
		return map[string]string{
			"horizontal":  "─",
			"vertical":    "│",
			"topLeft":     "┌",
			"topRight":    "┐",
			"bottomLeft":  "└",
			"bottomRight": "┘",
			"headerSeparator": "─",
		}
	case "rounded":
		return map[string]string{
			"horizontal":  "─",
			"vertical":    "│",
			"topLeft":     "┌",
			"topRight":    "┐",
			"bottomLeft":  "└",
			"bottomRight": "┘",
			"headerSeparator": "─",
		}
	case "reinforced":
		return map[string]string{
			"horizontal":  "═",
			"vertical":    "║",
			"topLeft":     "╔",
			"topRight":    "╗",
			"bottomLeft":  "╚",
			"bottomRight": "╝",
			"headerSeparator": "╤",
		}
	case "markdown":
		return map[string]string{
			"horizontal":  "-",
			"vertical":    "|",
			"topLeft":     "|",
			"topRight":    "",
			"bottomLeft":  "",
			"bottomRight": "",
			"headerSeparator": "-",
		}
	case "grid":
		return map[string]string{
			"horizontal":  "─",
			"vertical":    "│",
			"topLeft":     "├",
			"topRight":    "┤",
			"bottomLeft":  "└",
			"bottomRight": "┘",
			"headerSeparator": "─",
		}
	default:
		return getStyleChars("sharp")
	}
}

func formatCell(text string, width int, align string, padding int) string {
	textWidth := utf8.RuneCountInString(text)
	if textWidth > width {
		text = text[:width] // Truncate for demonstration
	}

	switch align {
	case "left":
		return strings.Repeat(" ", padding) + text + strings.Repeat(" ", padding+width-textWidth-padding)
	case "right":
		return strings.Repeat(" ", padding+width-textWidth) + text + strings.Repeat(" ", padding)
	case "center":
		leftPad := padding + (width-textWidth)/2
		return strings.Repeat(" ", leftPad) + text + strings.Repeat(" ", 2*padding+width-textWidth-leftPad)
	default:
		return strings.Repeat(" ", padding) + text + strings.Repeat(" ", padding+width-textWidth-padding)
	}
}

