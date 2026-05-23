package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"os"
	"strings"
	"time"
)

type ModuleInfo struct {
	Path     string      `json:"Path"`
	Version  string      `json:"Version"`
	Time     string      `json:"Time"`
	Indirect bool        `json:"Indirect"`
	Main     bool        `json:"Main"`
	Update   *ModuleInfo `json:"Update"`
}

type RowData struct {
	module          string
	version         string
	newVersion      string
	direct          string
	validTimestamps string
}

func iMax(a, b int) int {
	if a > b {
		return a
	}
	return b
}

func padCenterCell(s string, width int) string {
	if len(s) >= width {
		return s
	}
	totalPad := width - len(s)
	left := totalPad / 2
	right := totalPad - left
	return strings.Repeat(" ", left) + s + strings.Repeat(" ", right)
}

func padLeftCell(s string, width int) string {
	if len(s) >= width {
		return s
	}
	return " " + s + strings.Repeat(" ", width-1-len(s))
}

func main() {
	ci := flag.Bool("ci", false, "Non-zero exit code when at least one outdated dependency was found")
	direct := flag.Bool("direct", false, "List only direct modules")
	style := flag.String("style", "default", "Output style, pass 'markdown' for a Markdown table")
	update := flag.Bool("update", false, "List only modules with updates")
	flag.Parse()

	decoder := json.NewDecoder(os.Stdin)
	var modules []ModuleInfo

	for {
		var m ModuleInfo
		if err := decoder.Decode(&m); err == io.EOF {
			break
		} else if err != nil {
			fmt.Fprintf(os.Stderr, "%s %s\n", time.Now().Format("2006/01/02 15:04:05"), err.Error())
			os.Exit(0)
		}

		if m.Main {
			continue
		}

		modules = append(modules, m)
	}

	if len(modules) == 0 {
		return
	}

	// Filter
	var filtered []ModuleInfo
	for _, m := range modules {
		if *direct && m.Indirect {
			continue
		}
		if *update && m.Update == nil {
			continue
		}
		filtered = append(filtered, m)
	}

	if len(filtered) == 0 {
		return
	}

	headers := []string{"MODULE", "VERSION", "NEW VERSION", "DIRECT", "VALID TIMESTAMPS"}

	// Compute column widths
	numCols := len(headers)
	minWidths := make([]int, numCols)
	for i, h := range headers {
		minWidths[i] = len(h) + 2 // Always at least header + 2 padding
	}

	hasOutdated := false

	var rows []RowData
	for _, m := range filtered {
		newVersion := ""
		validTimestamps := true

		if m.Update != nil {
			newVersion = m.Update.Version
			currentTime, err1 := time.Parse(time.RFC3339, m.Time)
			updatedTime, err2 := time.Parse(time.RFC3339, m.Update.Time)
			if err1 == nil && err2 == nil {
				if updatedTime.Before(currentTime) {
					validTimestamps = false
				}
			} else {
				validTimestamps = false
			}
			hasOutdated = true
		}

		directStr := "false"
		if !m.Indirect {
			directStr = "true"
		}
		validStr := "false"
		if validTimestamps {
			validStr = "true"
		}

		rows = append(rows, RowData{
			module:          m.Path,
			version:         m.Version,
			newVersion:      newVersion,
			direct:          directStr,
			validTimestamps: validStr,
		})

		values := []string{m.Path, m.Version, newVersion, directStr, validStr}
		for i, v := range values {
			minWidths[i] = iMax(minWidths[i], len(v)+2)
		}
	}

	if *style == "markdown" {
		printMarkdown(rows, headers, minWidths)
	} else {
		printDefault(rows, headers, minWidths)
	}

	if *ci && hasOutdated {
		os.Exit(1)
	}
}

func printDefault(rows []RowData, headers []string, minWidths []int) {
	n := len(headers)

	// Border line
	border := ""
	for i := 0; i < n; i++ {
		border += "+" + strings.Repeat("-", minWidths[i])
	}
	border += "+"
	fmt.Println(border)

	// Header row (centered)
	line := ""
	for i, h := range headers {
		line += "|" + padCenterCell(h, minWidths[i])
	}
	line += "|"
	fmt.Println(line)

	fmt.Println(border)

	// Data rows (left aligned)
	for _, row := range rows {
		values := []string{row.module, row.version, row.newVersion, row.direct, row.validTimestamps}
		line := ""
		for i, v := range values {
			line += "|" + padLeftCell(v, minWidths[i])
		}
		line += "|"
		fmt.Println(line)
	}

	fmt.Println(border)
}

func printMarkdown(rows []RowData, headers []string, minWidths []int) {
	n := len(headers)

	// Header row (centered)
	line := ""
	for i, h := range headers {
		line += "|" + padCenterCell(h, minWidths[i])
	}
	line += "|"
	fmt.Println(line)

	// Separator line
	sep := ""
	for i := 0; i < n; i++ {
		sep += "|" + strings.Repeat("-", minWidths[i])
	}
	sep += "|"
	fmt.Println(sep)

	// Data rows (left aligned)
	for _, row := range rows {
		values := []string{row.module, row.version, row.newVersion, row.direct, row.validTimestamps}
		line := ""
		for i, v := range values {
			line += "|" + padLeftCell(v, minWidths[i])
		}
		line += "|"
		fmt.Println(line)
	}
}
