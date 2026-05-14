// Package ui provides bubbletea-based interactive TUI programs.
package ui

import (
	"fmt"
	"strings"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
	"github.com/irskep/autowt/internal/model"
)

var (
	selectedStyle   = lipgloss.NewStyle().Foreground(lipgloss.Color("10")) // green
	cursorStyle     = lipgloss.NewStyle().Foreground(lipgloss.Color("14")) // cyan
	dimStyle        = lipgloss.NewStyle().Foreground(lipgloss.Color("8"))  // gray
	statusStyle     = lipgloss.NewStyle().Foreground(lipgloss.Color("11")) // yellow
)

// RunCleanupTUI presents an interactive list of worktrees for the user
// to select for cleanup. Returns the selected statuses.
func RunCleanupTUI(statuses []model.BranchStatus) ([]model.BranchStatus, error) {
	items := make([]cleanupItem, len(statuses))
	for i, bs := range statuses {
		items[i] = cleanupItem{status: bs}
	}

	m := cleanupModel{items: items}
	p := tea.NewProgram(m)
	final, err := p.Run()
	if err != nil {
		return nil, err
	}

	fm := final.(cleanupModel)
	if fm.cancelled {
		return nil, nil
	}

	var selected []model.BranchStatus
	for _, item := range fm.items {
		if item.checked {
			selected = append(selected, item.status)
		}
	}
	return selected, nil
}

type cleanupItem struct {
	status  model.BranchStatus
	checked bool
}

type cleanupModel struct {
	items     []cleanupItem
	cursor    int
	cancelled bool
}

func (m cleanupModel) Init() tea.Cmd {
	return nil
}

func (m cleanupModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		switch msg.String() {
		case "q", "esc", "ctrl+c":
			m.cancelled = true
			return m, tea.Quit
		case "enter":
			return m, tea.Quit
		case "up", "k":
			if m.cursor > 0 {
				m.cursor--
			}
		case "down", "j":
			if m.cursor < len(m.items)-1 {
				m.cursor++
			}
		case " ", "x":
			m.items[m.cursor].checked = !m.items[m.cursor].checked
		case "a":
			allChecked := true
			for _, item := range m.items {
				if !item.checked {
					allChecked = false
					break
				}
			}
			for i := range m.items {
				m.items[i].checked = !allChecked
			}
		}
	}
	return m, nil
}

func (m cleanupModel) View() string {
	var b strings.Builder

	b.WriteString("Select worktrees to remove:\n")
	b.WriteString(dimStyle.Render("  space: toggle  a: all  enter: confirm  q: cancel"))
	b.WriteString("\n\n")

	for i, item := range m.items {
		cursor := "  "
		if i == m.cursor {
			cursor = cursorStyle.Render("> ")
		}

		check := "[ ]"
		if item.checked {
			check = selectedStyle.Render("[x]")
		}

		info := buildStatusInfo(item.status)
		line := fmt.Sprintf("%s%s %s", cursor, check, item.status.Branch)
		if info != "" {
			line += " " + statusStyle.Render(info)
		}

		b.WriteString(line)
		b.WriteString("\n")
	}

	selected := 0
	for _, item := range m.items {
		if item.checked {
			selected++
		}
	}
	b.WriteString(fmt.Sprintf("\n%d selected\n", selected))

	return b.String()
}

func buildStatusInfo(bs model.BranchStatus) string {
	var parts []string
	if !bs.HasRemote {
		parts = append(parts, "no remote")
	}
	if bs.IsMerged {
		parts = append(parts, "merged")
	}
	if bs.IsIdentical {
		parts = append(parts, "identical to main")
	}
	if bs.HasUncommittedChanges {
		parts = append(parts, "uncommitted changes")
	}
	if len(parts) == 0 {
		return ""
	}
	return "(" + strings.Join(parts, ", ") + ")"
}
