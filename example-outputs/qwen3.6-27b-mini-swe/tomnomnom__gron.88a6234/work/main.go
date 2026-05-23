package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"sort"
	"strings"
)

type Stmt struct {
	Path  []interface{}
	Value interface{}
}

func isIdent(key string) bool {
	if key == "" {
		return false
	}
	for i, r := range key {
		switch {
		case i == 0 && (r >= 'a' && r <= 'z' || r >= 'A' && r <= 'Z'):
			continue
		case i == 0 && r == '_':
			continue
		case i > 0 && (r >= 'a' && r <= 'z' || r >= 'A' && r <= 'Z' || r >= '0' && r <= '9' || r == '_'):
			continue
		default:
			return false
		}
	}
	return true
}

func keyAccess(k interface{}) string {
	switch v := k.(type) {
	case string:
		if isIdent(v) {
			return "." + v
		}
		return fmt.Sprintf(`["%s"]`, v)
	case int:
		return fmt.Sprintf("[%d]", v)
	default:
		return fmt.Sprintf(`[%v]`, v)
	}
}

func buildPath(path []interface{}) string {
	p := "json"
	for _, part := range path {
		p += keyAccess(part)
	}
	return p
}

func stringifyValue(v interface{}) string {
	switch val := v.(type) {
	case string:
		b, _ := json.Marshal(val)
		return string(b)
	case float64:
		if val == float64(int64(val)) {
			return fmt.Sprintf("%d", int64(val))
		}
		return fmt.Sprintf("%g", val)
	case bool:
		if val {
			return "true"
		}
		return "false"
	case nil:
		return "null"
	case containerMarker:
		return string(val)
	default:
		b, _ := json.Marshal(v)
		return string(b)
	}
}

type containerMarker string

const emptyObj = containerMarker("{}")
const emptyArr = containerMarker("[]")

func makePathSlice(path []interface{}) []interface{} {
	cp := make([]interface{}, len(path))
	copy(cp, path)
	return cp
}

func appendPath(path []interface{}, elem interface{}) []interface{} {
	cp := make([]interface{}, len(path)+1)
	copy(cp, path)
	cp[len(path)] = elem
	return cp
}

func sortKeys(keys []string) {
	sort.Slice(keys, func(i, j int) bool {
		ai, aj := isIdent(keys[i]), isIdent(keys[j])
		if ai && !aj {
			return true
		}
		if !ai && aj {
			return false
		}
		if ai && aj {
			li := strings.ToLower(keys[i])
			lj := strings.ToLower(keys[j])
			if li != lj {
				return li < lj
			}
			return keys[i] < keys[j]
		}
		return keys[i] < keys[j]
	})
}

func flatten(data interface{}, path []interface{}, stmts *[]Stmt) {
	switch val := data.(type) {
	case map[string]interface{}:
		*stmts = append(*stmts, Stmt{Path: makePathSlice(path), Value: emptyObj})
		var keys []string
		for k := range val {
			keys = append(keys, k)
		}
		sortKeys(keys)
		for _, k := range keys {
			newPath := appendPath(path, k)
			flatten(val[k], newPath, stmts)
		}
	case []interface{}:
		*stmts = append(*stmts, Stmt{Path: makePathSlice(path), Value: emptyArr})
		for i, item := range val {
			newPath := appendPath(path, i)
			flatten(item, newPath, stmts)
		}
	default:
		*stmts = append(*stmts, Stmt{Path: makePathSlice(path), Value: val})
	}
}

func jsonToGronLines(data interface{}) []string {
	var stmts []Stmt
	flatten(data, nil, &stmts)
	lines := make([]string, len(stmts))
	for i, s := range stmts {
		p := buildPath(s.Path)
		v := stringifyValue(s.Value)
		lines[i] = fmt.Sprintf("%s = %s;", p, v)
	}
	return lines
}

type parsedStmt struct {
	Path  []interface{}
	Value interface{}
}

func unescapeStr(s string) string {
	var result string
	if err := json.Unmarshal([]byte(s), &result); err == nil {
		return result
	}
	return s
}

func parseValue(v string) interface{} {
	v = strings.TrimSpace(v)
	switch v {
	case "null":
		return nil
	case "true":
		return true
	case "false":
		return false
	case "{}":
		return emptyObj
	case "[]":
		return emptyArr
	}
	if len(v) >= 2 && v[0] == '"' && v[len(v)-1] == '"' {
		return unescapeStr(v)
	}
	return v
}

func parsePath(pathStr string) []interface{} {
	if pathStr == "json" {
		return nil
	}
	path := []interface{}{}
	rest := pathStr[4:]
	for len(rest) > 0 {
		if rest[0] == '.' {
			rest = rest[1:]
			end := 0
			for end < len(rest) && rest[end] != '[' && rest[end] != '.' {
				end++
			}
			path = append(path, rest[:end])
			rest = rest[end:]
		} else if rest[0] == '[' {
			rest = rest[1:]
			end := strings.Index(rest, "]")
			if end == -1 {
				break
			}
			slice := rest[:end]
			rest = rest[end+1:]
			if len(slice) >= 2 && slice[0] == '"' && slice[len(slice)-1] == '"' {
				path = append(path, unescapeStr(slice))
			} else {
				var n int
				fmt.Sscanf(slice, "%d", &n)
				path = append(path, n)
			}
		} else {
			break
		}
	}
	return path
}

func parseGrondLine(line string) (*parsedStmt, error) {
	trimmed := strings.TrimSpace(line)
	if trimmed == "" {
		return nil, fmt.Errorf("empty line")
	}
	idx := strings.Index(trimmed, " = ")
	if idx == -1 {
		return nil, fmt.Errorf("invalid format")
	}
	pathStr := trimmed[:idx]
	valStr := trimmed[idx+3:]
	if strings.HasSuffix(valStr, ";") {
		valStr = valStr[:len(valStr)-1]
	}
	path := parsePath(pathStr)
	value := parseValue(valStr)
	return &parsedStmt{Path: path, Value: value}, nil
}

func parseJSONStreamLine(line string) (*parsedStmt, error) {
	trimmed := strings.TrimSpace(line)
	if len(trimmed) == 0 || trimmed[0] != '[' {
		return nil, fmt.Errorf("not json stream format")
	}
	var parts []json.RawMessage
	if err := json.Unmarshal([]byte(trimmed), &parts); err != nil {
		return nil, err
	}
	if len(parts) != 2 {
		return nil, fmt.Errorf("invalid JSON stream format: need 2 elements")
	}

	// Parse path
	var pathElements []interface{}
	if err := json.Unmarshal(parts[0], &pathElements); err != nil {
		return nil, err
	}
	// Convert numeric types
	for i, p := range pathElements {
		switch v := p.(type) {
		case json.Number:
			var n int
			fmt.Sscanf(v.String(), "%d", &n)
			pathElements[i] = n
		case float64:
			pathElements[i] = int(v)
		}
	}

	// Parse value
	var val interface{}
	// Pre-check: is it a JSON object or array?
	valStr := string(parts[1])
	switch {
	case len(valStr) > 0 && valStr[0] == '{':
		return &parsedStmt{Path: pathElements, Value: emptyObj}, nil
	case len(valStr) > 0 && valStr[0] == '[':
		return &parsedStmt{Path: pathElements, Value: emptyArr}, nil
	}
	if err := json.Unmarshal(parts[1], &val); err != nil {
		return nil, err
	}
	return &parsedStmt{Path: pathElements, Value: val}, nil
}

func readStatements(r io.Reader, useJSONStream bool) ([]*parsedStmt, error) {
	var stmts []*parsedStmt
	scanner := bufio.NewScanner(r)
	scanner.Buffer(make([]byte, 0, 1024*1024), 1024*1024)
	for scanner.Scan() {
		line := scanner.Text()
		var ps *parsedStmt
		var err error
		if useJSONStream {
			ps, err = parseJSONStreamLine(line)
		} else {
			ps, err = parseGrondLine(line)
		}
		if err != nil {
			continue
		}
		stmts = append(stmts, ps)
	}
	return stmts, nil
}

func isContainerMarker(v interface{}) bool {
	rm, ok := v.(containerMarker)
	return ok && (rm == emptyObj || rm == emptyArr)
}

func shiftPath(path []interface{}) []interface{} {
	if len(path) <= 1 {
		return nil
	}
	result := make([]interface{}, len(path)-1)
	copy(result, path[1:])
	return result
}

func ungronToJSON(stmts []*parsedStmt) (interface{}, error) {
	if len(stmts) == 0 {
		return nil, nil
	}

	rootIsArr := false
	for _, s := range stmts {
		if len(s.Path) == 0 {
			if rm, ok := s.Value.(containerMarker); ok && rm == emptyArr {
				rootIsArr = true
			}
			break
		}
	}

	if rootIsArr {
		return buildFromArray(stmts)
	}
	return buildFromObject(stmts)
}

func isPathArray(path []interface{}) bool {
	if len(path) > 0 {
		_, ok := path[0].(int)
		return ok
	}
	return false
}

func buildFromObject(stmts []*parsedStmt) (interface{}, error) {
	root := make(map[string]interface{})

	type groupInfo struct {
		stmts   []*parsedStmt
		isArray bool
	}
	grouped := make(map[string]*groupInfo)
	var groupKeys []string

	for _, s := range stmts {
		if len(s.Path) == 0 {
			continue
		}
		if k, ok := s.Path[0].(string); ok {
			if _, exists := grouped[k]; !exists {
				isArr := false
				if len(s.Path) > 1 {
					_, isArr = s.Path[1].(int)
				}
				grouped[k] = &groupInfo{isArray: isArr, stmts: nil}
				groupKeys = append(groupKeys, k)
			}
			grouped[k].stmts = append(grouped[k].stmts, s)
		}
	}

	sortKeys(groupKeys)

	for _, key := range groupKeys {
		gi := grouped[key]
		leafVal := interface{}(nil)
		hasLeaf := false
		restStmts := make([]*parsedStmt, 0)

		for _, s := range gi.stmts {
			if len(s.Path) == 1 {
				leafVal = s.Value
				hasLeaf = true
				continue
			}
			restStmts = append(restStmts, &parsedStmt{Path: shiftPath(s.Path), Value: s.Value})
		}

		if len(restStmts) > 0 {
			var sub interface{}
			var err error
			if isPathArray(restStmts[0].Path) {
				sub, err = buildFromArray(restStmts)
			} else {
				sub, err = buildFromObject(restStmts)
			}
			if err != nil {
				return nil, err
			}
			root[key] = sub
			if hasLeaf && !isContainerMarker(leafVal) {
				root[key] = leafVal
			}
		} else if hasLeaf {
			root[key] = leafVal
		}
	}

	return root, nil
}

func buildFromArray(stmts []*parsedStmt) (interface{}, error) {
	maxIdx := -1
	for _, s := range stmts {
		if len(s.Path) == 0 {
			continue
		}
		if idx, ok := s.Path[0].(int); ok && idx > maxIdx {
			maxIdx = idx
		}
	}
	if maxIdx < 0 {
		return make([]interface{}, 0), nil
	}
	result := make([]interface{}, maxIdx+1)

	type groupInfo struct {
		stmts []*parsedStmt
	}
	grouped := make(map[int]*groupInfo)
	for i := 0; i <= maxIdx; i++ {
		grouped[i] = &groupInfo{stmts: nil}
	}

	for _, s := range stmts {
		if len(s.Path) == 0 {
			continue
		}
		if idx, ok := s.Path[0].(int); ok {
			grouped[idx].stmts = append(grouped[idx].stmts, s)
		}
	}

	for idx := 0; idx <= maxIdx; idx++ {
		gi := grouped[idx]
		leafVal := interface{}(nil)
		hasLeaf := false
		restStmts := make([]*parsedStmt, 0)

		for _, s := range gi.stmts {
			if len(s.Path) == 1 {
				leafVal = s.Value
				hasLeaf = true
				continue
			}
			restStmts = append(restStmts, &parsedStmt{Path: shiftPath(s.Path), Value: s.Value})
		}

		if len(restStmts) > 0 {
			var sub interface{}
			var err error
			if isPathArray(restStmts[0].Path) {
				sub, err = buildFromArray(restStmts)
			} else {
				sub, err = buildFromObject(restStmts)
			}
			if err != nil {
				return nil, err
			}
			result[idx] = sub
			if hasLeaf && !isContainerMarker(leafVal) {
				result[idx] = leafVal
			}
		} else if hasLeaf {
			result[idx] = leafVal
		}
	}
	return result, nil
}

type jsonStreamEntry struct {
	Path  []interface{}
	Value interface{}
}

func flattenToStream(data interface{}, path []interface{}) []jsonStreamEntry {
	var entries []jsonStreamEntry
	switch val := data.(type) {
	case map[string]interface{}:
		entries = append(entries, jsonStreamEntry{Path: makePathSlice(path), Value: map[string]interface{}{}})
		var keys []string
		for k := range val {
			keys = append(keys, k)
		}
		sortKeys(keys)
		for _, k := range keys {
			newPath := appendPath(path, k)
			entries = append(entries, flattenToStream(val[k], newPath)...)
		}
	case []interface{}:
		entries = append(entries, jsonStreamEntry{Path: makePathSlice(path), Value: []interface{}{}})
		for i, item := range val {
			newPath := appendPath(path, i)
			entries = append(entries, flattenToStream(item, newPath)...)
		}
	default:
		entries = append(entries, jsonStreamEntry{Path: makePathSlice(path), Value: val})
	}
	return entries
}

func formatJSON(v interface{}) ([]byte, error) {
	return json.MarshalIndent(cleanValues(v), "", "  ")
}

func cleanValues(v interface{}) interface{} {
	switch val := v.(type) {
	case map[string]interface{}:
		for k, v2 := range val {
			val[k] = cleanValues(v2)
		}
	case []interface{}:
		for i, v2 := range val {
			val[i] = cleanValues(v2)
		}
	case containerMarker:
		if val == emptyObj {
			return map[string]interface{}{}
		}
		if val == emptyArr {
			return []interface{}{}
		}
	}
	return v
}

func readInput(filename string) ([]byte, error) {
	if filename == "-" || filename == "" {
		return io.ReadAll(os.Stdin)
	}
	if strings.HasPrefix(filename, "http://") || strings.HasPrefix(filename, "https://") {
		return nil, fmt.Errorf("URL fetching not supported")
	}
	f, err := os.Open(filename)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	return io.ReadAll(f)
}

func main() {
	args := os.Args[1:]
	ungron := false
	values := false
	stream := false
	jsonStream := false
	filename := ""

	for i := 0; i < len(args); i++ {
		switch args[i] {
		case "-u", "--ungron":
			ungron = true
		case "-v", "--values":
			values = true
		case "-s", "--stream":
			stream = true
		case "-j", "--json":
			jsonStream = true
		case "--no-sort":
		case "--version":
			fmt.Println("gron version dev")
			return
		case "-c", "--colorize", "-m", "--monochrome":
		case "-k", "--insecure":
		case "-x", "--proxy":
			if i+1 < len(args) {
				i++
			}
		case "--noproxy":
			if i+1 < len(args) {
				i++
			}
		case "-h", "--help":
			printHelp()
			return
		default:
			if !strings.HasPrefix(args[i], "-") {
				filename = args[i]
			} else {
				if i+1 < len(args) && !strings.HasPrefix(args[i+1], "-") {
					i++
				}
			}
		}
	}

	var input []byte
	var err error
	if filename != "" {
		input, err = readInput(filename)
		if err != nil {
			fmt.Fprintf(os.Stderr, "%v\n", err)
			os.Exit(1)
		}
	} else {
		input, err = readInput("-")
		if err != nil {
			fmt.Fprintf(os.Stderr, "%v\n", err)
			os.Exit(2)
		}
	}

	if ungron {
		stmts, _ := readStatements(strings.NewReader(string(input)), jsonStream)
		result, err := ungronToJSON(stmts)
		if err != nil {
			fmt.Fprintf(os.Stderr, "%v\n", err)
			os.Exit(6)
		}
		out, err := formatJSON(result)
		if err != nil {
			fmt.Fprintf(os.Stderr, "%v\n", err)
			os.Exit(6)
		}
		fmt.Println(string(out))
		return
	}

	if values {
		stmts, _ := readStatements(strings.NewReader(string(input)), jsonStream)
		for _, s := range stmts {
			printParsedValue(s.Value)
		}
		return
	}

	if stream {
		lines := strings.Split(string(input), "\n")
		var objects []interface{}
		for _, line := range lines {
			line = strings.TrimSpace(line)
			if line == "" {
				continue
			}
			var data interface{}
			if err := json.Unmarshal([]byte(line), &data); err != nil {
				fmt.Fprintf(os.Stderr, "%v\n", err)
				os.Exit(3)
			}
			objects = append(objects, data)
		}

		if len(objects) == 0 {
			fmt.Println("json = [];")
			return
		}

		if len(objects) > 1 {
			var stmts []Stmt
			flatten(objects, nil, &stmts)
			for _, s := range stmts {
				p := buildPath(s.Path)
				v := stringifyValue(s.Value)
				fmt.Printf("%s = %s;\n", p, v)
			}
		} else {
			rlines := jsonToGronLines(objects[0])
			for _, line := range rlines {
				fmt.Println(line)
			}
		}
		return
	}

	var data interface{}
	if err := json.Unmarshal(input, &data); err != nil {
		fmt.Fprintf(os.Stderr, "%v\n", err)
		os.Exit(3)
	}

	if jsonStream {
		entries := flattenToStream(data, nil)
		for _, e := range entries {
			pathPart := make([]interface{}, len(e.Path))
			for j, p := range e.Path {
				pathPart[j] = p
			}
			record := []interface{}{pathPart, e.Value}
			out, _ := json.Marshal(record)
			fmt.Println(string(out))
		}
		return
	}

	glines := jsonToGronLines(data)
	for _, line := range glines {
		fmt.Println(line)
	}
}

func printParsedValue(v interface{}) {
	var valStr string
	switch val := v.(type) {
	case string:
		valStr = val
	case float64:
		if val == float64(int64(val)) {
			valStr = fmt.Sprintf("%d", int64(val))
		} else {
			valStr = fmt.Sprintf("%g", val)
		}
	case bool:
		valStr = fmt.Sprintf("%t", val)
	case nil:
		valStr = "null"
	case containerMarker:
		valStr = string(val)
	default:
		b, _ := json.Marshal(v)
		valStr = string(b)
	}
	fmt.Println(valStr)
}

func printHelp() {
	fmt.Println(`Transform JSON (from a file, URL, or stdin) into discrete assignments to make it greppable

Usage:
  gron [OPTIONS] [FILE|URL|-]

Options:
  -u, --ungron     Reverse the operation (turn assignments back into JSON)
  -v, --values     Print just the values of provided assignments
  -c, --colorize   Colorize output (default on tty)
  -m, --monochrome Monochrome (don't colorize output)
  -s, --stream     Treat each line of input as a separate json object
  -k, --insecure   Disable certificate validation
  -x, --proxy      Set proxy configuration
      --noproxy    Comma-separated list of hosts for which not to use a proxy, if one is specified.
  -j, --json       Represent gron data as JSON stream
      --no-sort    Don't sort output (faster)
      --version    Print version information

Exit Codes:
  0\tOK
  1\tFailed to open file
  2\tFailed to read input
  3\tFailed to form statements
  4\tFailed to fetch URL
  5\tFailed to parse statements
  6\tFailed to encode JSON

Examples:
  gron /tmp/apiresponse.json
  gron http://jsonplaceholder.typicode.com/users/1 
  curl -s http://jsonplaceholder.typicode.com/users/1 | gron
  gron http://jsonplaceholder.typicode.com/users/1 | grep company | gron --ungron`)
}
