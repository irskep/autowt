package main

import (
	"log/slog"
	"os"

	"github.com/irskep/autowt/internal/cli"
)

func main() {
	slog.SetDefault(slog.New(slog.NewTextHandler(os.Stderr, &slog.HandlerOptions{Level: slog.LevelWarn})))

	if err := cli.Execute(); err != nil {
		os.Exit(1)
	}
}
