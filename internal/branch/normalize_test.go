package branch

import "testing"

func TestNormalizeDynamic(t *testing.T) {
	tests := []struct {
		input string
		want  string
	}{
		{"My Feature Branch", "my-feature-branch"},
		{"feature/Fix Login", "feature/fix-login"},
		{"UPPER_CASE", "upper-case"},
		{"has~tilde^caret:colon", "hastildecaretcolon"},
		{"double..dots", "double.dots"},
		{"multi---dash", "multi-dash"},
		{"multi///slash", "multi/slash"},
		{"/leading/slash/", "leading/slash"},
		{".leading.dot/component", "leading.dot/component"},
		{"component/.hidden", "component/hidden"},
		{"ends-with.lock", "ends-with"},
		{"part/.lock", "part/lock"},
		{"a/b/c", "a/b/c"},
		{"simple", "simple"},
		{"", ""},
	}

	for _, tt := range tests {
		t.Run(tt.input, func(t *testing.T) {
			got := NormalizeDynamic(tt.input)
			if got != tt.want {
				t.Errorf("NormalizeDynamic(%q) = %q, want %q", tt.input, got, tt.want)
			}
		})
	}
}
