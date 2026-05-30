// Package styles defines shared terminal presentation styles.
package styles

import "github.com/charmbracelet/lipgloss"

// Dim is the shared low-emphasis text style.
var Dim = lipgloss.NewStyle().Foreground(lipgloss.Color("245"))
