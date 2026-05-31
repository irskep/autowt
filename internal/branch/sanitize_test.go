package branch

import (
	"path/filepath"
	"testing"

	"github.com/irskep/autowt/internal/model"
)

func TestPathFragmentFlat(t *testing.T) {
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
			got, err := PathFragment(tt.input, model.BranchPathModeFlat)
			if err != nil {
				t.Fatalf("PathFragment(%q, flat) error: %v", tt.input, err)
			}
			if got != tt.want {
				t.Errorf("PathFragment(%q, flat) = %q, want %q", tt.input, got, tt.want)
			}
		})
	}
}

func TestPathFragmentHierarchical(t *testing.T) {
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
			got, err := PathFragment(tt.input, model.BranchPathModeHierarchical)
			if err != nil {
				t.Fatalf("PathFragment(%q, hierarchical) error: %v", tt.input, err)
			}
			if got != tt.want {
				t.Errorf("PathFragment(%q, hierarchical) = %q, want %q", tt.input, got, tt.want)
			}
		})
	}
}

func TestPathFragmentUnknownModeErrors(t *testing.T) {
	_, err := PathFragment("feature/my-branch", model.BranchPathMode("unknown"))
	if err == nil {
		t.Fatal("PathFragment() error = nil, want invalid mode error")
	}
}
