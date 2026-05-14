package branch

import "testing"

func TestInterpolateArgs(t *testing.T) {
	tests := []struct {
		template string
		args     []string
		want     string
	}{
		{"gh issue view $1 --json title", []string{"123"}, "gh issue view 123 --json title"},
		{"deploy $1 $2", []string{"staging", "v2"}, "deploy staging v2"},
		{"no args here", nil, "no args here"},
		{"$1 and $1 again", []string{"x"}, "x and x again"},
		{"$1 $2 $3", []string{"a"}, "a $2 $3"},
	}

	for _, tt := range tests {
		t.Run(tt.template, func(t *testing.T) {
			got := InterpolateArgs(tt.template, tt.args)
			if got != tt.want {
				t.Errorf("InterpolateArgs(%q, %v) = %q, want %q", tt.template, tt.args, got, tt.want)
			}
		})
	}
}
