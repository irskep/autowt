package config

import (
	"fmt"
	"os"
	"path/filepath"
	"runtime"
)

// DefaultConfigDir returns the OS-specific configuration directory for autowt.
func DefaultConfigDir() (string, error) {
	return defaultConfigDir(runtime.GOOS, os.Getenv, os.UserHomeDir, fileExists)
}

// defaultConfigDir is the testable core of DefaultConfigDir. Its inputs (the
// target OS, environment lookup, home directory, and a file-existence probe)
// are injected so every platform branch can be exercised on any host.
func defaultConfigDir(goos string, getenv func(string) string, homeDir func() (string, error), fileExists func(string) bool) (string, error) {
	// XDG_CONFIG_HOME is an explicit opt-in honored on every platform; absent
	//   it, each OS falls back to its native default below.
	if xdg := getenv("XDG_CONFIG_HOME"); xdg != "" {
		return filepath.Join(xdg, "autowt"), nil
	}

	home, err := homeDir()
	if err != nil {
		return "", fmt.Errorf("determine home directory: %w", err)
	}

	switch goos {
	case "darwin":
		// Modern macOS config lives under ~/.config; a config in the legacy
		//   Application Support directory is still honored.
		modern := filepath.Join(home, ".config", "autowt")
		legacy := filepath.Join(home, "Library", "Application Support", "autowt")
		return preferModern(modern, legacy, fileExists), nil
	case "windows":
		// Modern Windows config lives under %LOCALAPPDATA%; a config in the
		//   legacy ~/.autowt directory is still honored.
		localAppData := getenv("LOCALAPPDATA")
		if localAppData == "" {
			localAppData = filepath.Join(home, "AppData", "Local")
		}
		modern := filepath.Join(localAppData, "autowt")
		legacy := filepath.Join(home, ".autowt")
		return preferModern(modern, legacy, fileExists), nil
	default: // linux and others
		return filepath.Join(home, ".config", "autowt"), nil
	}
}

// preferModern returns the modern config directory unless a config.toml exists
// only at the legacy location, in which case legacy is kept for backward
// compatibility.
func preferModern(modern, legacy string, fileExists func(string) bool) string {
	if !fileExists(filepath.Join(modern, "config.toml")) &&
		fileExists(filepath.Join(legacy, "config.toml")) {
		return legacy
	}
	return modern
}

// fileExists reports whether path refers to an existing file (not a directory).
func fileExists(path string) bool {
	fi, err := os.Stat(path)
	return err == nil && !fi.IsDir()
}

// DefaultStateDir returns the OS-specific state directory for autowt.
func DefaultStateDir() (string, error) {
	switch runtime.GOOS {
	case "darwin":
		home, err := os.UserHomeDir()
		if err != nil {
			return "", fmt.Errorf("determine home directory: %w", err)
		}
		return filepath.Join(home, "Library", "Application Support", "autowt"), nil
	case "windows":
		home, err := os.UserHomeDir()
		if err != nil {
			return "", fmt.Errorf("determine home directory: %w", err)
		}
		return filepath.Join(home, ".autowt"), nil
	default:
		if xdg := os.Getenv("XDG_DATA_HOME"); xdg != "" {
			return filepath.Join(xdg, "autowt"), nil
		}
		home, err := os.UserHomeDir()
		if err != nil {
			return "", fmt.Errorf("determine home directory: %w", err)
		}
		return filepath.Join(home, ".local", "share", "autowt"), nil
	}
}
