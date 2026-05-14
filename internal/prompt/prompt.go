// Package prompt provides simple Y/n terminal confirmation prompts.
package prompt

import (
	"bufio"
	"fmt"
	"os"
	"strings"
)

// ConfirmYes asks a yes/no question defaulting to yes.
// If autoConfirm is true, returns true without prompting.
func ConfirmYes(question string, autoConfirm bool) bool {
	if autoConfirm {
		return true
	}
	fmt.Fprintf(os.Stderr, "%s (Y/n) ", question)
	return readConfirmation(true)
}

// ConfirmNo asks a yes/no question defaulting to no.
// If autoConfirm is true, returns false without prompting.
func ConfirmNo(question string, autoConfirm bool) bool {
	if autoConfirm {
		return false
	}
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
