package config

import (
	"errors"
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
			name:   "darwin XDG_CONFIG_HOME wins even when a legacy config exists",
			goos:   "darwin",
			getenv: env(map[string]string{"XDG_CONFIG_HOME": "/custom/xdg"}),
			exists: fileAt(filepath.Join(appSupport, "config.toml")),
			want:   filepath.Join("/custom/xdg", "autowt"),
		},
		{
			name:   "darwin prefers ~/.config when a config already lives there",
			goos:   "darwin",
			getenv: env(nil),
			exists: fileAt(filepath.Join(xdgDefault, "config.toml")),
			want:   xdgDefault,
		},
		{
			name:   "darwin keeps an existing legacy Application Support install",
			goos:   "darwin",
			getenv: env(nil),
			exists: fileAt(filepath.Join(appSupport, "config.toml")),
			want:   appSupport,
		},
		{
			name:   "darwin fresh install defaults to ~/.config",
			goos:   "darwin",
			getenv: env(nil),
			exists: noFiles,
			want:   xdgDefault,
		},
		{
			name:   "darwin prefers ~/.config over legacy when both exist",
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
			name:   "windows prefers %LOCALAPPDATA% when a config already lives there",
			goos:   "windows",
			getenv: env(map[string]string{"LOCALAPPDATA": "/localappdata"}),
			exists: fileAt(filepath.Join("/localappdata", "autowt", "config.toml")),
			want:   filepath.Join("/localappdata", "autowt"),
		},
		{
			name:   "windows keeps an existing legacy ~/.autowt install",
			goos:   "windows",
			getenv: env(map[string]string{"LOCALAPPDATA": "/localappdata"}),
			exists: fileAt(filepath.Join(home, ".autowt", "config.toml")),
			want:   filepath.Join(home, ".autowt"),
		},
		{
			name:   "windows fresh install defaults to %LOCALAPPDATA%",
			goos:   "windows",
			getenv: env(map[string]string{"LOCALAPPDATA": "/localappdata"}),
			exists: noFiles,
			want:   filepath.Join("/localappdata", "autowt"),
		},
		{
			name:   "windows prefers %LOCALAPPDATA% over legacy when both exist",
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
