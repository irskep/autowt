// Package console provides styled terminal output for autowt, matching
// the Python version's Rich-based theme.
package console

import (
	"fmt"
	"os"

	"github.com/charmbracelet/lipgloss"
)

var (
	commandStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("245")) // gray
	sectionStyle = lipgloss.NewStyle().Bold(true)
	successStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("10")) // green
	warningStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("11")) // yellow
	errorStyle   = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("9")) // bold red
	infoStyle    = lipgloss.NewStyle().Foreground(lipgloss.Color("6"))  // dim cyan
	outputStyle  = lipgloss.NewStyle().Foreground(lipgloss.Color("245")) // gray
)

// Suppressed controls whether styled output is suppressed (echo mode).
// When true, all Print* functions are no-ops.
var Suppressed bool

// Command prints a shell command string in gray.
func Command(cmd string) {
	if Suppressed {
		return
	}
	fmt.Fprintln(os.Stderr, commandStyle.Render("> "+cmd))
}

// Section prints a section header in bold.
func Section(text string) {
	if Suppressed {
		return
	}
	fmt.Fprintln(os.Stderr, sectionStyle.Render(text))
}

// Success prints a success message in green.
func Success(text string) {
	if Suppressed {
		return
	}
	fmt.Fprintln(os.Stderr, successStyle.Render(text))
}

// Warning prints a warning message in yellow.
func Warning(text string) {
	if Suppressed {
		return
	}
	fmt.Fprintln(os.Stderr, warningStyle.Render(text))
}

// Error prints an error message in bold red.
func Error(text string) {
	if Suppressed {
		return
	}
	fmt.Fprintln(os.Stderr, errorStyle.Render(text))
}

// Info prints an informational message in dim cyan.
func Info(text string) {
	if Suppressed {
		return
	}
	fmt.Fprintln(os.Stderr, infoStyle.Render(text))
}

// Output prints raw command output in gray.
func Output(text string) {
	if Suppressed {
		return
	}
	fmt.Fprintln(os.Stderr, outputStyle.Render(text))
}

// Plain prints text without styling to stderr.
func Plain(text string) {
	if Suppressed {
		return
	}
	fmt.Fprintln(os.Stderr, text)
}

// Infof prints a formatted info message.
func Infof(format string, args ...any) {
	Info(fmt.Sprintf(format, args...))
}

// Successf prints a formatted success message.
func Successf(format string, args ...any) {
	Success(fmt.Sprintf(format, args...))
}

// Errorf prints a formatted error message.
func Errorf(format string, args ...any) {
	Error(fmt.Sprintf(format, args...))
}

// Warningf prints a formatted warning message.
func Warningf(format string, args ...any) {
	Warning(fmt.Sprintf(format, args...))
}
