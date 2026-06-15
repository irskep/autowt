package config

import (
	"errors"
	"os"
	"path/filepath"
	"testing"
)

func TestDefaultConfigDirResolution(t *testing.T) {
	const home = "/home/u"
	homeDir := func() (string, error) { return home, nil }
	noFiles := func(string) bool { return false }
	fileAt := func(want string) func(string) bool {
		return func(p string) bool { return p == want }
	}
	env := func(m map[string]string) func(string) string {
		return func(k string) string { return m[k] }
	}

	xdgDefault := filepath.Join(home, ".config", "autowt")
	appSupport := filepath.Join(home, "Library", "Application Support", "autowt")

	tests := []struct {
		name   string
		goos   string
		getenv func(string) string
		exists func(string) bool
		want   string
	}{
		{
			name:   "darwin honors XDG_CONFIG_HOME when set",
			goos:   "darwin",
			getenv: env(map[string]string{"XDG_CONFIG_HOME": "/custom/xdg"}),
			exists: noFiles,
			want:   filepath.Join("/custom/xdg", "autowt"),
		},
		{
			name:   "darwin XDG_CONFIG_HOME is used even when a previous config exists",
			goos:   "darwin",
			getenv: env(map[string]string{"XDG_CONFIG_HOME": "/custom/xdg"}),
			exists: fileAt(filepath.Join(appSupport, "config.toml")),
			want:   filepath.Join("/custom/xdg", "autowt"),
		},
		{
			name:   "darwin uses ~/.config when a config already exists there",
			goos:   "darwin",
			getenv: env(nil),
			exists: fileAt(filepath.Join(xdgDefault, "config.toml")),
			want:   xdgDefault,
		},
		{
			name:   "darwin uses previous Application Support location when only it has a config",
			goos:   "darwin",
			getenv: env(nil),
			exists: fileAt(filepath.Join(appSupport, "config.toml")),
			want:   appSupport,
		},
		{
			name:   "darwin defaults to ~/.config when neither location has a config",
			goos:   "darwin",
			getenv: env(nil),
			exists: noFiles,
			want:   xdgDefault,
		},
		{
			name:   "darwin uses ~/.config when both locations have configs",
			goos:   "darwin",
			getenv: env(nil),
			exists: func(p string) bool {
				return p == filepath.Join(xdgDefault, "config.toml") ||
					p == filepath.Join(appSupport, "config.toml")
			},
			want: xdgDefault,
		},
		{
			name:   "linux honors XDG_CONFIG_HOME when set",
			goos:   "linux",
			getenv: env(map[string]string{"XDG_CONFIG_HOME": "/custom/xdg"}),
			exists: noFiles,
			want:   filepath.Join("/custom/xdg", "autowt"),
		},
		{
			name:   "linux defaults to ~/.config when XDG unset (no filesystem probe)",
			goos:   "linux",
			getenv: env(nil),
			exists: fileAt(filepath.Join(appSupport, "config.toml")),
			want:   xdgDefault,
		},
		{
			name:   "windows honors XDG_CONFIG_HOME when set",
			goos:   "windows",
			getenv: env(map[string]string{"XDG_CONFIG_HOME": "/custom/xdg"}),
			exists: noFiles,
			want:   filepath.Join("/custom/xdg", "autowt"),
		},
		{
			name:   "windows uses %LOCALAPPDATA% when a config already exists there",
			goos:   "windows",
			getenv: env(map[string]string{"LOCALAPPDATA": "/localappdata"}),
			exists: fileAt(filepath.Join("/localappdata", "autowt", "config.toml")),
			want:   filepath.Join("/localappdata", "autowt"),
		},
		{
			name:   "windows uses previous ~/.autowt location when only it has a config",
			goos:   "windows",
			getenv: env(map[string]string{"LOCALAPPDATA": "/localappdata"}),
			exists: fileAt(filepath.Join(home, ".autowt", "config.toml")),
			want:   filepath.Join(home, ".autowt"),
		},
		{
			name:   "windows defaults to %LOCALAPPDATA% when neither location has a config",
			goos:   "windows",
			getenv: env(map[string]string{"LOCALAPPDATA": "/localappdata"}),
			exists: noFiles,
			want:   filepath.Join("/localappdata", "autowt"),
		},
		{
			name:   "windows uses %LOCALAPPDATA% when both locations have configs",
			goos:   "windows",
			getenv: env(map[string]string{"LOCALAPPDATA": "/localappdata"}),
			exists: func(p string) bool {
				return p == filepath.Join("/localappdata", "autowt", "config.toml") ||
					p == filepath.Join(home, ".autowt", "config.toml")
			},
			want: filepath.Join("/localappdata", "autowt"),
		},
		{
			name:   "windows falls back to ~/AppData/Local when LOCALAPPDATA unset",
			goos:   "windows",
			getenv: env(nil),
			exists: noFiles,
			want:   filepath.Join(home, "AppData", "Local", "autowt"),
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := defaultConfigDir(tt.goos, tt.getenv, homeDir, tt.exists)
			if err != nil {
				t.Fatalf("defaultConfigDir() error: %v", err)
			}
			if got != tt.want {
				t.Errorf("defaultConfigDir(%q) = %q, want %q", tt.goos, got, tt.want)
			}
		})
	}
}

func TestDefaultConfigDirPropagatesHomeError(t *testing.T) {
	boom := errors.New("no home")
	_, err := defaultConfigDir(
		"darwin",
		func(string) string { return "" },
		func() (string, error) { return "", boom },
		func(string) bool { return false },
	)
	if !errors.Is(err, boom) {
		t.Fatalf("expected wrapped home directory error, got %v", err)
	}
}

func TestDefaultConfigDirReturnsAutowtPath(t *testing.T) {
	got, err := DefaultConfigDir()
	if err != nil {
		t.Fatalf("DefaultConfigDir() error: %v", err)
	}
	if filepath.Base(got) != "autowt" {
		t.Errorf("DefaultConfigDir() = %q, want a path ending in 'autowt'", got)
	}
}

func TestFileExists(t *testing.T) {
	dir := t.TempDir()

	file := filepath.Join(dir, "config.toml")
	if err := os.WriteFile(file, []byte("x"), 0o644); err != nil {
		t.Fatal(err)
	}
	if !fileExists(file) {
		t.Errorf("fileExists(%q) = false, want true for a regular file", file)
	}

	// A directory named config.toml must not be mistaken for a config file.
	dirNamedConfig := filepath.Join(dir, "sub", "config.toml")
	if err := os.MkdirAll(dirNamedConfig, 0o755); err != nil {
		t.Fatal(err)
	}
	if fileExists(dirNamedConfig) {
		t.Errorf("fileExists(%q) = true, want false for a directory", dirNamedConfig)
	}

	if fileExists(filepath.Join(dir, "absent.toml")) {
		t.Error("fileExists() = true for a nonexistent path, want false")
	}
}
