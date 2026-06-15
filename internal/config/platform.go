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
	// XDG_CONFIG_HOME is an explicit opt-in used on every platform.
	// When unset, each OS uses its default below.
	if xdg := getenv("XDG_CONFIG_HOME"); xdg != "" {
		return filepath.Join(xdg, "autowt"), nil
	}

	home, err := homeDir()
	if err != nil {
		return "", fmt.Errorf("determine home directory: %w", err)
	}

	switch goos {
	case "darwin":
		// Use ~/.config unless an existing config file is present at the
		// previous Application Support location.
		primary := filepath.Join(home, ".config", "autowt")
		fallback := filepath.Join(home, "Library", "Application Support", "autowt")
		return selectConfigDir(primary, fallback, fileExists), nil
	case "windows":
		// Use %LOCALAPPDATA% unless an existing config file is present at
		// the previous ~/.autowt location.
		localAppData := getenv("LOCALAPPDATA")
		if localAppData == "" {
			localAppData = filepath.Join(home, "AppData", "Local")
		}
		primary := filepath.Join(localAppData, "autowt")
		fallback := filepath.Join(home, ".autowt")
		return selectConfigDir(primary, fallback, fileExists), nil
	default: // linux and others
		return filepath.Join(home, ".config", "autowt"), nil
	}
}

// selectConfigDir returns the primary config directory unless a config.toml
// exists only at the fallback location.
func selectConfigDir(primary, fallback string, fileExists func(string) bool) string {
	if !fileExists(filepath.Join(primary, "config.toml")) &&
		fileExists(filepath.Join(fallback, "config.toml")) {
		return fallback
	}
	return primary
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
