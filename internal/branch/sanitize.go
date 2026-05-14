// Package branch provides branch name manipulation utilities.
package branch

import (
	"strings"
	"unicode"
)

// Sanitize converts a branch name into a safe filesystem directory name.
// Slashes become hyphens, special characters are removed.
func Sanitize(branch string) string {
	var b strings.Builder
	for _, r := range branch {
		switch {
		case r == '/' || r == ' ' || r == '\\':
			b.WriteRune('-')
		case unicode.IsLetter(r) || unicode.IsDigit(r) || r == '-' || r == '_' || r == '.':
			b.WriteRune(r)
		}
	}

	result := b.String()
	result = strings.Trim(result, ".-")

	if result == "" {
		return "branch"
	}
	return result
}
