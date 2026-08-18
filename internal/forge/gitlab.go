package forge

import (
	"encoding/json"
	"log/slog"
	"strings"

	"github.com/irskep/autowt/internal/model"
)

// gitLab talks to GitLab through the glab CLI.
type gitLab struct{}

func (gitLab) Name() string                   { return "GitLab" }
func (gitLab) CLIName() string                { return "glab" }
func (gitLab) InstallURL() string             { return "https://gitlab.com/gitlab-org/cli" }
func (gitLab) RequestNoun() string            { return "merge request" }
func (gitLab) CleanupMode() model.CleanupMode { return model.CleanupModeGitLab }
func (gitLab) UsernameVar() string            { return "gitlab_username" }
func (g gitLab) Available() bool              { return cliAvailable(g.CLIName()) }

// Username returns the authenticated GitLab username, or an empty string.
func (g gitLab) Username() string {
	out, err := cliOutput("", g.CLIName(), "api", "user")
	if err != nil {
		return ""
	}

	var user struct {
		Username string `json:"username"`
	}
	if err := json.Unmarshal(out, &user); err != nil {
		slog.Debug("Failed to parse glab api user output", "error", err)
		return ""
	}
	return strings.TrimSpace(user.Username)
}

// RequestStatus returns the state of the merge requests opened from a branch.
func (g gitLab) RequestStatus(repoPath, branch string) string {
	out, err := cliOutput(repoPath, g.CLIName(),
		"mr", "list",
		"--source-branch", branch,
		"--all",
		"--output", "json",
	)
	if err != nil {
		return ""
	}

	states, err := parseGitLabStates(out)
	if err != nil {
		slog.Debug("Failed to parse glab mr list output", "branch", branch, "error", err)
		return ""
	}
	return statusFromStates(states)
}

// matchesRemote recognizes gitlab.com, self-hosted instances that keep gitlab
// in their hostname, and whatever host glab is pointed at.
func (gitLab) matchesRemote(remoteURL string) bool {
	return hostContains(remoteURL, "gitlab") || hostMatchesEnv(remoteURL, "GITLAB_HOST")
}

// parseGitLabStates pulls the states out of `glab mr list --output json`
// output.
func parseGitLabStates(out []byte) ([]string, error) {
	var mrs []struct {
		State        string `json:"state"`
		IID          int    `json:"iid"`
		SourceBranch string `json:"source_branch"`
	}
	if err := json.Unmarshal(out, &mrs); err != nil {
		return nil, err
	}

	states := make([]string, 0, len(mrs))
	for _, mr := range mrs {
		states = append(states, mr.State)
	}
	return states, nil
}
