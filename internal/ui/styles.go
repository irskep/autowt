package ui

import (
	"github.com/charmbracelet/lipgloss"
	"github.com/irskep/autowt/internal/styles"
)

var (
	selectedStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("10")) // green
	cursorStyle   = lipgloss.NewStyle().Foreground(lipgloss.Color("14")) // cyan
	dimStyle      = styles.Dim
	statusStyle   = lipgloss.NewStyle().Foreground(lipgloss.Color("11")) // yellow
)
