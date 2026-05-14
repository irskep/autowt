package main

import (
	"os"

	"github.com/irskep/autowt/internal/cli"
)

func main() {
	if err := cli.Execute(); err != nil {
		os.Exit(1)
	}
}
