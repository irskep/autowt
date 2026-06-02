// Package branch provides branch name manipulation utilities.
package branch

import (
	"path/filepath"
	"strings"
	"unicode"
)

// PathFragment converts a branch name into a safe filesystem path fragment
// according to the configured directory flattening behavior.
func PathFragment(branch string, flattenDirectories bool) string {
	if flattenDirectories {
		return sanitizeFlat(branch)
	}
	return sanitizeHierarchical(branch)
}

func sanitizeFlat(branch string) string {
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

func sanitizeHierarchical(branch string) string {
	branch = strings.ReplaceAll(branch, "\\", "/")

	var parts []string
	for _, rawPart := range strings.Split(branch, "/") {
		part := sanitizePathComponent(rawPart)
		if part != "" && part != "." && part != ".." {
			parts = append(parts, part)
		}
	}

	if len(parts) == 0 {
		return "branch"
	}
	return filepath.Join(parts...)
}

func sanitizePathComponent(component string) string {
	var b strings.Builder
	for _, r := range component {
		switch {
		case r == ' ':
			b.WriteRune('-')
		case unicode.IsLetter(r) || unicode.IsDigit(r) || r == '-' || r == '_' || r == '.':
			b.WriteRune(r)
		}
	}
	return strings.Trim(b.String(), ".-")
}
