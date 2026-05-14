// Package prompt provides simple Y/n terminal confirmation prompts.
package prompt

import (
	"bufio"
	"fmt"
	"os"
	"strings"
)

// ConfirmDefaultYes asks the user a yes/no question, defaulting to yes.
// Returns true if the user confirms (or presses enter).
func ConfirmDefaultYes(question string) bool {
	fmt.Fprintf(os.Stderr, "%s (Y/n) ", question)
	return readConfirmation(true)
}

// ConfirmDefaultNo asks the user a yes/no question, defaulting to no.
// Returns true if the user explicitly enters yes.
func ConfirmDefaultNo(question string) bool {
	fmt.Fprintf(os.Stderr, "%s (y/N) ", question)
	return readConfirmation(false)
}

func readConfirmation(defaultValue bool) bool {
	scanner := bufio.NewScanner(os.Stdin)
	if !scanner.Scan() {
		return defaultValue
	}
	input := strings.TrimSpace(strings.ToLower(scanner.Text()))
	switch input {
	case "":
		return defaultValue
	case "y", "yes":
		return true
	case "n", "no":
		return false
	default:
		return defaultValue
	}
}
