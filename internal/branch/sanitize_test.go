package branch

import "testing"

func TestSanitize(t *testing.T) {
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
			got := Sanitize(tt.input)
			if got != tt.want {
				t.Errorf("Sanitize(%q) = %q, want %q", tt.input, got, tt.want)
			}
		})
	}
}
