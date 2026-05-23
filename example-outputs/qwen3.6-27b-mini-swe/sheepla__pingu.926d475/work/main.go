package main

import (
	"context"
	"encoding/binary"
	"fmt"
	"math"
	"math/rand"
	"net"
	"os"
	"os/signal"
	"strconv"
	"strings"
	"sync"
	"syscall"
	"time"
)

const version = "pingu: v-rev9c2e3df"

// 20 ASCII art frames of the penguin, each exactly 58 characters
var penguinFrames = []string{
	" ...        .     ...   ..    ..     .........            ",
	" ...     ....          ..  ..      ... .....  .. ..       ",
	" ...    .......      ...         ... . ..... #######      ",
	".....  ........ .###############.....  ... ##########.  . ",
	" .... ........#####################.  ... ###########     ",
	"      ....... ######################.... ############     ",
	".    .  .... ########################... ###########      ",
	"   ..   ....#########################.. .###########      ",
	"    .       #########################.   .##########      ",
	"   ....     .########################.      ########      ",
	"  .....      .  ####################.        #######.     ",
	"......     .. . ################## . .      .#######      ",
	"......       #####################  .      .#######       ",
	"......   .###########################  ..  #######        ",
	"...    . ########################################.        ",
	"       ####################################### .          ",
	"      ##################################    .             ",
	"     ###################################  ........        ",
	"  .#####################################    .........     ",
	" .#######################################       .... . .  ",
}

func init() {
	for i := range penguinFrames {
		for len(penguinFrames[i]) < 57 {
			penguinFrames[i] += " "
		}
		penguinFrames[i] = penguinFrames[i][:57]
	}
}

type pingResult struct {
	addr  string
	ttl   int
	rtt   time.Duration
	seq   int
	bytes int
}

func main() {
	if len(os.Args) < 2 {
		fmt.Fprintln(os.Stderr, "[ ERROR ] must requires an argument")
		os.Exit(1)
	}

	count := 20
	host := ""

	i := 1
	for i < len(os.Args) {
		switch os.Args[i] {
		case "-h", "--help":
			printHelp()
			os.Exit(0)
		case "-V", "--version":
			fmt.Println(version)
			os.Exit(0)
		case "-P", "--privilege":
			i++
		case "-c":
			i++
			if i >= len(os.Args) {
				fmt.Fprintln(os.Stderr, "[ ERROR ] count value required")
				os.Exit(1)
			}
			n, err := strconv.Atoi(os.Args[i])
			if err != nil {
				fmt.Fprintln(os.Stderr, "[ ERROR ] invalid count value")
				os.Exit(1)
			}
			count = n
			i++
		default:
			if strings.HasPrefix(os.Args[i], "-c=") {
				val := os.Args[i][3:]
				n, err := strconv.Atoi(val)
				if err != nil {
					fmt.Fprintln(os.Stderr, "[ ERROR ] invalid count value")
					os.Exit(1)
				}
				count = n
				i++
			} else {
				if host == "" {
					host = os.Args[i]
				}
				i++
			}
		}
	}

	if host == "" {
		fmt.Fprintln(os.Stderr, "[ ERROR ] must requires an argument")
		os.Exit(1)
	}

	runPing(host, count)
}

func printHelp() {
	fmt.Println("Usage:")
	fmt.Println("  pingu [OPTIONS] HOST")
	fmt.Println()
	fmt.Println("`ping` command but with pingu")
	fmt.Println()
	fmt.Println("Application Options:")
	fmt.Println("  -c, --count=     Stop after <count> replies (default: 20)")
	fmt.Println("  -P, --privilege  Enable privileged mode")
	fmt.Println("  -V, --version    Show version")
	fmt.Println()
	fmt.Println("Help Options:")
	fmt.Println("  -h, --help       Show this help message")
	fmt.Println()
}

func buildICMPPacket(myID uint16, seq int, dataLen int) []byte {
	data := make([]byte, 8+dataLen)
	data[0] = 8 // Echo request
	data[1] = 0
	binary.BigEndian.PutUint16(data[4:6], myID)
	binary.BigEndian.PutUint16(data[6:8], uint16(seq))
	binary.BigEndian.PutUint64(data[8:16], uint64(time.Now().UnixNano()))
	for j := 16; j < len(data); j++ {
		data[j] = uint8(myID*2 + uint16(seq))
	}

	// Checksum
	var sum uint32
	for j := 0; j < len(data)-1; j += 2 {
		sum += uint32(data[j])<<8 | uint32(data[j+1])
	}
	if len(data)%2 == 1 {
		sum += uint32(data[len(data)-1]) << 8
	}
	for sum > 0xFFFF {
		sum = (sum >> 16) + (sum & 0xFFFF)
	}
	binary.BigEndian.PutUint16(data[2:4], uint16(^sum))
	return data
}

func runPing(host string, count int) {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
	go func() {
		<-sigCh
		cancel()
	}()

	// Resolve host
	ips, err := net.DefaultResolver.LookupIPAddr(ctx, host)
	if err != nil {
		fmt.Fprintf(os.Stderr, "[ ERROR ] an error occurred while initializing pinger: failed to init pinger lookup %s: %v\n", host, err)
		return
	}
	if len(ips) == 0 {
		fmt.Fprintf(os.Stderr, "[ ERROR ] an error occurred while initializing pinger: failed to resolve %s\n", host)
		return
	}

	// Prefer IPv4
	targetIP := ips[0].IP
	for _, ip := range ips {
		if ip.IP.To4() != nil {
			targetIP = ip.IP
			break
		}
	}

	// Open ICMP socket
	conn, err := net.ListenPacket("ip4:icmp", "0.0.0.0")
	if err != nil {
		fmt.Fprintf(os.Stderr, "[ ERROR ] an error occurred while initializing pinger: %v\n", err)
		return
	}
	defer conn.Close()

	dstAddr := net.IPAddr{IP: targetIP}
	rand.Seed(time.Now().UnixNano())
	myID := uint16(rand.Intn(65536))

	// Track sent packets: seq -> send time
	sentLock := &sync.Mutex{}
	sent := make(map[int]time.Time)

	// Channel for matching responses
	resultCh := make(chan *pingResult, 1)

	// Receiver goroutine - reads from socket and sends matching results
	go func() {
		buf := make([]byte, 1500)
		for {
			select {
			case <-ctx.Done():
				return
			default:
			}
			conn.SetReadDeadline(time.Now().Add(5 * time.Second))
			n, addr, err := conn.ReadFrom(buf)
			if err != nil {
				continue
			}
			if n < 8 {
				continue
			}
			if buf[0] != 0 { // Echo reply
				continue
			}
			respID := binary.BigEndian.Uint16(buf[4:6])
			respSeq := int(binary.BigEndian.Uint16(buf[6:8]))
			if respID != myID {
				continue
			}
			sentLock.Lock()
			startTime, ok := sent[respSeq]
			delete(sent, respSeq)
			sentLock.Unlock()
			if !ok {
				continue
			}
			rtt := time.Since(startTime)
			resultCh <- &pingResult{
				addr:  addr.String(),
				ttl:   64,
				rtt:   rtt,
				seq:   respSeq,
				bytes: 32,
			}
		}
	}()

	fmt.Printf("PING %s (%s) type `Ctrl-C` to abort\n", host, targetIP.String())

	// Send one packet at a time, wait for reply
	var results []*pingResult
	frameIdx := 0
	received := 0

	for seq := 0; seq < count; seq++ {
		select {
		case <-ctx.Done():
			printStats(host, seq, received, results)
			return
		default:
		}

		// Send packet
		data := buildICMPPacket(myID, seq, 56)
		sendTime := time.Now()
		conn.WriteTo(data, &dstAddr)
		sentLock.Lock()
		sent[seq] = sendTime
		sentLock.Unlock()

		// Wait for reply to this sequence number
		select {
		case r := <-resultCh:
			if r.seq != seq {
				// Wrong sequence - put it back by storing in results  
				// Actually, with one-at-a-time sending, this shouldn't happen
				// unless we get out of order. Put it in results anyway.
				results = append(results, r)
				received++
				continue
			}
			results = append(results, r)
			received++
			frame := penguinFrames[frameIdx%len(penguinFrames)]
			frameIdx++
			fmt.Printf("%s seq=%d 32bytes from %s: ttl=%d time=%sµs\n",
				frame, r.seq, r.addr, r.ttl, formatTime(r.rtt))
		case <-time.After(6 * time.Second):
			// Timeout for this packet - still print it
			frame := penguinFrames[frameIdx%len(penguinFrames)]
			frameIdx++
			fmt.Printf("%s seq=%d 32bytes from %s: ttl=%d time=timeout\n",
				frame, seq, targetIP.String(), 64)
			continue
		}
	}

	printStats(host, count, received, results)
}

func printStats(host string, sent, received int, results []*pingResult) {
	fmt.Printf("\n───────── %s ping statistics ─────────\n", host)
	lossPct := float64(0)
	if sent > 0 {
		lossPct = float64(sent-received) / float64(sent) * 100
	}
	fmt.Printf("PACKET STATISTICS: %d transmitted => %d received (%.0f%% loss)\n",
		sent, received, lossPct)

	if len(results) > 0 {
		minRtt := results[0].rtt
		maxRtt := results[0].rtt
		totalNanos := int64(0)
		for _, r := range results {
			totalNanos += int64(r.rtt)
			if r.rtt < minRtt {
				minRtt = r.rtt
			}
			if r.rtt > maxRtt {
				maxRtt = r.rtt
			}
		}
		avgRtt := time.Duration(totalNanos / int64(len(results)))

		var sumSqDiff float64
		for _, r := range results {
			diff := float64(r.rtt - avgRtt)
			sumSqDiff += diff * diff
		}
		stddev := time.Duration(math.Sqrt(sumSqDiff / float64(len(results))))

		if stddev == 0 {
			fmt.Printf("ROUND TRIP: min=%sµs avg=%sµs max=%sµs stddev=0s\n",
				formatTime(minRtt), formatTime(avgRtt), formatTime(maxRtt))
		} else {
			fmt.Printf("ROUND TRIP: min=%sµs avg=%sµs max=%sµs stddev=%sµs\n",
				formatTime(minRtt), formatTime(avgRtt), formatTime(maxRtt), formatTime(stddev))
		}
	}
}

func formatTime(d time.Duration) string {
	nanos := int64(d)
	if nanos%1000 == 0 {
		return strconv.FormatInt(nanos/1000, 10)
	}
	micros := float64(nanos) / 1e6
	return strconv.FormatFloat(micros, 'f', 3, 64)
}
