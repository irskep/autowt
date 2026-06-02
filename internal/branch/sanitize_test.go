package branch

import (
	"path/filepath"
	"testing"
)

func TestPathFragmentFlattensDirectories(t *testing.T) {
	tests := []struct {
		input string
		want  string
	}{
		{"feature/my-branch", "feature-my-branch"},
		{"simple", "simple"},
		{"with spaces", "with-spaces"},
		{"back\\slash", "back-slash"},
		{"special@#$chars", "specialchars"},
		{"leading..dots", "leading..dots"},
		{".leading-dot", "leading-dot"},
		{"trailing-dot.", "trailing-dot"},
		{"a/b/c", "a-b-c"},
		{"", "branch"},
		{"@#$", "branch"},
		{"under_score", "under_score"},
		{"dots.in.name", "dots.in.name"},
	}

	for _, tt := range tests {
		t.Run(tt.input, func(t *testing.T) {
			got := PathFragment(tt.input, true)
			if got != tt.want {
				t.Errorf("PathFragment(%q, true) = %q, want %q", tt.input, got, tt.want)
			}
		})
	}
}

func TestPathFragmentPreserveDirectories(t *testing.T) {
	tests := []struct {
		input string
		want  string
	}{
		{"feature/my-branch", filepath.Join("feature", "my-branch")},
		{"simple", "simple"},
		{"with spaces", "with-spaces"},
		{"back\\slash", filepath.Join("back", "slash")},
		{"special@#$chars", "specialchars"},
		{"a/b/c", filepath.Join("a", "b", "c")},
		{"a//b", filepath.Join("a", "b")},
		{"./feature/../thing", filepath.Join("feature", "thing")},
		{".../---/valid", "valid"},
		{"", "branch"},
		{"@#$", "branch"},
		{"under_score", "under_score"},
		{"dots.in.name", "dots.in.name"},
	}

	for _, tt := range tests {
		t.Run(tt.input, func(t *testing.T) {
			got := PathFragment(tt.input, false)
			if got != tt.want {
				t.Errorf("PathFragment(%q, false) = %q, want %q", tt.input, got, tt.want)
			}
		})
	}
}
