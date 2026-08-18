package forge

import (
	"testing"

	"github.com/irskep/autowt/internal/model"
)

func TestForCleanupMode(t *testing.T) {
	tests := []struct {
		mode model.CleanupMode
		want string
	}{
		{model.CleanupModeGitHub, "GitHub"},
		{model.CleanupModeGitLab, "GitLab"},
	}
	for _, tt := range tests {
		provider, ok := ForCleanupMode(tt.mode)
		if !ok {
			t.Fatalf("ForCleanupMode(%q) found no provider", tt.mode)
		}
		if provider.Name() != tt.want {
			t.Errorf("ForCleanupMode(%q).Name() = %q, want %q", tt.mode, provider.Name(), tt.want)
		}
	}

	for _, mode := range []model.CleanupMode{
		model.CleanupModeAll,
		model.CleanupModeMerged,
		model.CleanupModeRemoteless,
		model.CleanupModeInteractive,
	} {
		if _, ok := ForCleanupMode(mode); ok {
			t.Errorf("ForCleanupMode(%q) unexpectedly found a provider", mode)
		}
	}
}

func TestStatusFromStatesPrefersFinishedStates(t *testing.T) {
	tests := []struct {
		name   string
		states []string
		want   string
	}{
		{"no requests", nil, ""},
		{"github open", []string{"OPEN"}, "open"},
		{"gitlab open", []string{"opened"}, "open"},
		{"gitlab locked counts as open", []string{"locked"}, "open"},
		{"closed beats open", []string{"opened", "closed"}, "closed"},
		{"merged beats everything", []string{"closed", "opened", "merged"}, "merged"},
		{"unknown state ignored", []string{"something-else"}, ""},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := statusFromStates(tt.states); got != tt.want {
				t.Errorf("statusFromStates(%v) = %q, want %q", tt.states, got, tt.want)
			}
		})
	}
}

func TestMatchesRemote(t *testing.T) {
	tests := []struct {
		remote string
		want   string // provider name, or "" for no match
	}{
		{"git@github.com:irskep/autowt.git", "GitHub"},
		{"https://github.com/irskep/autowt.git", "GitHub"},
		{"git@gitlab.com:group/repo.git", "GitLab"},
		{"https://gitlab.example.com/group/repo.git", "GitLab"},
		{"git@gitlab.atticus.com:atticus/atticus.git", "GitLab"},
		{"ssh://git@gitlab.example.com:2222/group/repo.git", "GitLab"},
		{"git@bitbucket.org:team/repo.git", ""},
		{"/srv/git/bare-repo.git", ""},
		// The host decides, not the repository name.
		{"git@gitlab.com:group/github.com-mirror.git", "GitLab"},
		{"https://github.com/irskep/gitlab-tools.git", "GitHub"},
	}
	for _, tt := range tests {
		var matched string
		for _, provider := range Providers() {
			if provider.matchesRemote(tt.remote) {
				matched = provider.Name()
				break
			}
		}
		if matched != tt.want {
			t.Errorf("remote %q matched %q, want %q", tt.remote, matched, tt.want)
		}
	}
}

func TestRemoteHost(t *testing.T) {
	tests := map[string]string{
		"git@gitlab.atticus.com:atticus/atticus.git":       "gitlab.atticus.com",
		"https://GitLab.example.com/group/repo.git":        "gitlab.example.com",
		"ssh://git@gitlab.example.com:2222/group/repo.git": "gitlab.example.com",
		"https://user:token@gitlab.example.com/group/repo": "gitlab.example.com",
		"/srv/git/bare-repo.git":                           "",
	}
	for remote, want := range tests {
		if got := remoteHost(remote); got != want {
			t.Errorf("remoteHost(%q) = %q, want %q", remote, got, want)
		}
	}
}

func TestMatchesRemoteHonorsHostEnvVars(t *testing.T) {
	t.Setenv("GH_HOST", "git.example.com")
	if !(gitHub{}).matchesRemote("git@git.example.com:team/repo.git") {
		t.Error("GH_HOST host should match as GitHub")
	}

	t.Setenv("GITLAB_HOST", "https://code.example.com")
	if !(gitLab{}).matchesRemote("https://code.example.com/group/repo.git") {
		t.Error("GITLAB_HOST host should match as GitLab")
	}
	if (gitLab{}).matchesRemote("git@other.example.com:group/repo.git") {
		t.Error("an unrelated host should not match GITLAB_HOST")
	}
}

func TestParseGitHubStates(t *testing.T) {
	out := []byte(`[{"state":"MERGED","number":7,"headRefName":"feature"},{"state":"OPEN","number":9,"headRefName":"feature"}]`)
	states, err := parseGitHubStates(out)
	if err != nil {
		t.Fatalf("parseGitHubStates() error: %v", err)
	}
	if len(states) != 2 || states[0] != "MERGED" || states[1] != "OPEN" {
		t.Fatalf("parseGitHubStates() = %v", states)
	}
	if got := statusFromStates(states); got != "merged" {
		t.Errorf("status = %q, want merged", got)
	}
}

func TestParseGitLabStates(t *testing.T) {
	out := []byte(`[{"id":1,"iid":222,"state":"merged","source_branch":"feature"}]`)
	states, err := parseGitLabStates(out)
	if err != nil {
		t.Fatalf("parseGitLabStates() error: %v", err)
	}
	if len(states) != 1 || states[0] != "merged" {
		t.Fatalf("parseGitLabStates() = %v", states)
	}

	empty, err := parseGitLabStates([]byte(`[]`))
	if err != nil {
		t.Fatalf("parseGitLabStates([]) error: %v", err)
	}
	if got := statusFromStates(empty); got != "" {
		t.Errorf("status for no merge requests = %q, want empty", got)
	}
}

func TestAnalyzeBranchesForCleanupMarksFinishedRequests(t *testing.T) {
	provider := fakeProvider{states: map[string]string{
		"merged-branch": "merged",
		"closed-branch": "closed",
		"open-branch":   "open",
	}}
	worktrees := []model.WorktreeInfo{
		{Branch: "merged-branch", Path: "/wt/merged"},
		{Branch: "closed-branch", Path: "/wt/closed"},
		{Branch: "open-branch", Path: "/wt/open"},
		{Branch: "no-request", Path: "/wt/none"},
	}

	statuses, err := AnalyzeBranchesForCleanup(provider, "/repo", worktrees, func(path string) bool {
		return path == "/wt/merged"
	})
	if err != nil {
		t.Fatalf("AnalyzeBranchesForCleanup() error: %v", err)
	}
	if len(statuses) != len(worktrees) {
		t.Fatalf("got %d statuses, want %d", len(statuses), len(worktrees))
	}

	wantMerged := map[string]bool{
		"merged-branch": true,
		"closed-branch": true,
		"open-branch":   false,
		"no-request":    false,
	}
	for _, bs := range statuses {
		if bs.IsMerged != wantMerged[bs.Branch] {
			t.Errorf("%s IsMerged = %v, want %v", bs.Branch, bs.IsMerged, wantMerged[bs.Branch])
		}
	}
	if !statuses[0].HasUncommittedChanges {
		t.Error("uncommitted changes should be reported for /wt/merged")
	}
}

func TestAnalyzeBranchesForCleanupRequiresCLI(t *testing.T) {
	provider := fakeProvider{unavailable: true}
	_, err := AnalyzeBranchesForCleanup(provider, "/repo", nil, func(string) bool { return false })
	if err == nil {
		t.Fatal("expected an error when the forge CLI is missing")
	}
}

// fakeProvider serves canned request states without shelling out.
type fakeProvider struct {
	states      map[string]string
	unavailable bool
}

func (fakeProvider) Name() string                   { return "Fake" }
func (fakeProvider) CLIName() string                { return "fake" }
func (fakeProvider) InstallURL() string             { return "https://example.com/" }
func (fakeProvider) RequestNoun() string            { return "change request" }
func (fakeProvider) CleanupMode() model.CleanupMode { return model.CleanupMode("fake") }
func (fakeProvider) UsernameVar() string            { return "fake_username" }
func (f fakeProvider) Available() bool              { return !f.unavailable }
func (fakeProvider) Username() string               { return "" }
func (fakeProvider) matchesRemote(string) bool      { return false }

func (f fakeProvider) RequestStatus(repoPath, branch string) string {
	return f.states[branch]
}
