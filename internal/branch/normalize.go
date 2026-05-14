package branch

import (
	"regexp"
	"strings"
)

var (
	separatorRe    = regexp.MustCompile(`[\s_]+`)
	gitInvalidRe   = regexp.MustCompile(`[~^:?*\[\]\\@\x00-\x1f\x7f]+`)
	multiDotRe     = regexp.MustCompile(`\.\.+`)
	multiDashRe    = regexp.MustCompile(`-+`)
	multiSlashRe   = regexp.MustCompile(`/+`)
)

// NormalizeDynamic normalizes raw command output for use as a git ref.
// Unlike Sanitize (which is for filesystem paths and replaces / with -),
// this function preserves / for hierarchical branches like feature/fix-login.
func NormalizeDynamic(raw string) string {
	result := strings.ToLower(raw)

	// Replace common separators with dashes.
	result = separatorRe.ReplaceAllString(result, "-")

	// Remove git-invalid characters.
	result = gitInvalidRe.ReplaceAllString(result, "")

	// Collapse consecutive dots.
	result = multiDotRe.ReplaceAllString(result, ".")

	// Collapse consecutive dashes and slashes.
	result = multiDashRe.ReplaceAllString(result, "-")
	result = multiSlashRe.ReplaceAllString(result, "/")

	// Strip leading/trailing dashes, dots, slashes.
	result = strings.Trim(result, "-./")

	// Clean each slash-separated component.
	parts := strings.Split(result, "/")
	var cleaned []string
	for _, part := range parts {
		part = strings.TrimLeft(part, ".")
		if strings.HasSuffix(part, ".lock") {
			part = part[:len(part)-5]
		}
		part = strings.TrimLeft(part, "-")
		if part != "" {
			cleaned = append(cleaned, part)
		}
	}
	result = strings.Join(cleaned, "/")

	// Enforce maximum length.
	const maxLength = 255
	if len(result) > maxLength {
		result = result[:maxLength]
		result = strings.TrimRight(result, "-./")
	}

	return result
}
