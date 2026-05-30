// Package entrypoint contains shared binary startup code.
package entrypoint

import (
	"log/slog"
	"os"

	"github.com/irskep/autowt/internal/cli"
)

// Main configures process-wide defaults and runs the CLI.
func Main() {
	// Default to warn level; --debug upgrades to debug in PersistentPreRun.
	slog.SetDefault(slog.New(slog.NewTextHandler(os.Stderr, &slog.HandlerOptions{Level: slog.LevelWarn})))

	if err := cli.Execute(); err != nil {
		os.Exit(1)
	}
}
