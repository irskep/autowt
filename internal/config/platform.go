package config

import (
	"os"
	"path/filepath"
	"runtime"
)

// DefaultConfigDir returns the OS-specific configuration directory for autowt.
func DefaultConfigDir() string {
	switch runtime.GOOS {
	case "darwin":
		home, _ := os.UserHomeDir()
		return filepath.Join(home, "Library", "Application Support", "autowt")
	case "windows":
		home, _ := os.UserHomeDir()
		return filepath.Join(home, ".autowt")
	default: // linux and others
		if xdg := os.Getenv("XDG_CONFIG_HOME"); xdg != "" {
			return filepath.Join(xdg, "autowt")
		}
		home, _ := os.UserHomeDir()
		return filepath.Join(home, ".config", "autowt")
	}
}

// DefaultStateDir returns the OS-specific state directory for autowt.
func DefaultStateDir() string {
	switch runtime.GOOS {
	case "darwin":
		home, _ := os.UserHomeDir()
		return filepath.Join(home, "Library", "Application Support", "autowt")
	case "windows":
		home, _ := os.UserHomeDir()
		return filepath.Join(home, ".autowt")
	default:
		if xdg := os.Getenv("XDG_DATA_HOME"); xdg != "" {
			return filepath.Join(xdg, "autowt")
		}
		home, _ := os.UserHomeDir()
		return filepath.Join(home, ".local", "share", "autowt")
	}
}
