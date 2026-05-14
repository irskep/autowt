package branch

import "testing"

func TestApplyPrefix(t *testing.T) {
	tests := []struct {
		name     string
		branch   string
		template string
		context  map[string]string
		want     string
	}{
		{
			name:     "simple prefix",
			branch:   "my-branch",
			template: "feature/",
			context:  nil,
			want:     "feature/my-branch",
		},
		{
			name:     "template variable",
			branch:   "my-branch",
			template: "{github_username}/",
			context:  map[string]string{"github_username": "alice"},
			want:     "alice/my-branch",
		},
		{
			name:     "no double prefix",
			branch:   "feature/my-branch",
			template: "feature/",
			context:  nil,
			want:     "feature/my-branch",
		},
		{
			name:     "missing template variable",
			branch:   "my-branch",
			template: "{github_username}/",
			context:  nil,
			want:     "my-branch",
		},
		{
			name:     "empty template",
			branch:   "my-branch",
			template: "",
			context:  nil,
			want:     "my-branch",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := ApplyPrefix(tt.branch, tt.template, tt.context)
			if got != tt.want {
				t.Errorf("ApplyPrefix(%q, %q, %v) = %q, want %q",
					tt.branch, tt.template, tt.context, got, tt.want)
			}
		})
	}
}
