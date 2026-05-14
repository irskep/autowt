package branch

import (
	"fmt"
	"os"
	"strings"
)

// ApplyPrefix applies a prefix template to a branch name. Template variables
// like {repo_name} and {github_username} are expanded from context.
// Environment variables ($HOME, etc.) are also expanded.
// Returns the branch unchanged if the prefix is empty, a template variable
// is missing, or the branch already has the prefix.
func ApplyPrefix(branch, prefixTemplate string, context map[string]string) string {
	if prefixTemplate == "" {
		return branch
	}

	// Replace template variables.
	prefix := prefixTemplate
	for key, val := range context {
		prefix = strings.ReplaceAll(prefix, fmt.Sprintf("{%s}", key), val)
	}

	// Check for unreplaced template variables.
	if strings.Contains(prefix, "{") && strings.Contains(prefix, "}") {
		return branch
	}

	// Expand environment variables.
	prefix = os.ExpandEnv(prefix)

	// Avoid double-prefixing.
	if strings.HasPrefix(branch, prefix) {
		return branch
	}

	return prefix + branch
}
