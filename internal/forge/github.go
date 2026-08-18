package forge

import (
	"encoding/json"
	"log/slog"
	"strings"

	"github.com/irskep/autowt/internal/model"
)

// gitHub talks to GitHub through the gh CLI.
type gitHub struct{}

func (gitHub) Name() string                   { return "GitHub" }
func (gitHub) CLIName() string                { return "gh" }
func (gitHub) InstallURL() string             { return "https://cli.github.com/" }
func (gitHub) RequestNoun() string            { return "pull request" }
func (gitHub) CleanupMode() model.CleanupMode { return model.CleanupModeGitHub }
func (gitHub) UsernameVar() string            { return "github_username" }
func (g gitHub) Available() bool              { return cliAvailable(g.CLIName()) }

// Username returns the authenticated GitHub username, or an empty string.
func (g gitHub) Username() string {
	out, err := cliOutput("", g.CLIName(), "api", "user", "--jq", ".login")
	if err != nil {
		return ""
	}
	return strings.TrimSpace(string(out))
}

// RequestStatus returns the state of the pull requests opened from a branch.
func (g gitHub) RequestStatus(repoPath, branch string) string {
	out, err := cliOutput(repoPath, g.CLIName(),
		"pr", "list",
		"--head", branch,
		"--state", "all",
		"--json", "state,number,headRefName",
	)
	if err != nil {
		return ""
	}

	states, err := parseGitHubStates(out)
	if err != nil {
		slog.Debug("Failed to parse gh pr list output", "branch", branch, "error", err)
		return ""
	}
	return statusFromStates(states)
}

// matchesRemote recognizes github.com plus whatever host gh is pointed at.
func (gitHub) matchesRemote(remoteURL string) bool {
	return hostContains(remoteURL, "github.com") || hostMatchesEnv(remoteURL, "GH_HOST")
}

// parseGitHubStates pulls the states out of `gh pr list --json` output.
func parseGitHubStates(out []byte) ([]string, error) {
	var prs []struct {
		State       string `json:"state"`
		Number      int    `json:"number"`
		HeadRefName string `json:"headRefName"`
	}
	if err := json.Unmarshal(out, &prs); err != nil {
		return nil, err
	}

	states := make([]string, 0, len(prs))
	for _, pr := range prs {
		states = append(states, pr.State)
	}
	return states, nil
}
