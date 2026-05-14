package ui

import (
	"fmt"
	"strings"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
	"github.com/irskep/autowt/internal/model"
)

// SwitchResult is what RunSwitchTUI returns.
type SwitchResult struct {
	Branch string
	IsNew  bool
}

// RunSwitchTUI presents worktrees and branches for the user to select.
// Returns the selected branch name and whether it's a new branch.
func RunSwitchTUI(worktrees []model.WorktreeInfo, allBranches []string) (*SwitchResult, error) {
	var items []switchItem

	// Existing worktrees first.
	for _, wt := range worktrees {
		items = append(items, switchItem{
			label:      wt.Branch,
			isWorktree: true,
			path:       wt.DisplayPath(),
		})
	}

	// Add branches that don't have worktrees yet.
	wtBranches := make(map[string]bool)
	for _, wt := range worktrees {
		wtBranches[wt.Branch] = true
	}
	for _, b := range allBranches {
		if !wtBranches[b] {
			items = append(items, switchItem{
				label: b,
				isNew: true,
			})
		}
	}

	m := switchModel{items: items}
	p := tea.NewProgram(m)
	final, err := p.Run()
	if err != nil {
		return nil, err
	}

	fm := final.(switchModel)
	if fm.cancelled || fm.cursor >= len(fm.items) {
		return nil, nil
	}

	selected := fm.items[fm.cursor]
	return &SwitchResult{
		Branch: selected.label,
		IsNew:  selected.isNew,
	}, nil
}

type switchItem struct {
	label      string
	isWorktree bool
	isNew      bool
	path       string
}

type switchModel struct {
	items     []switchItem
	cursor    int
	cancelled bool
}

func (m switchModel) Init() tea.Cmd {
	return nil
}

func (m switchModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
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
		}
	}
	return m, nil
}

func (m switchModel) View() string {
	var b strings.Builder

	b.WriteString("Select a worktree or branch:\n")
	b.WriteString(dimStyle.Render("  enter: select  q: cancel"))
	b.WriteString("\n\n")

	for i, item := range m.items {
		cursor := "  "
		if i == m.cursor {
			cursor = cursorStyle.Render("> ")
		}

		label := item.label
		if item.isWorktree {
			pathInfo := dimStyle.Render(item.path)
			label = fmt.Sprintf("%s  %s", label, pathInfo)
		} else if item.isNew {
			label += " " + lipgloss.NewStyle().Foreground(lipgloss.Color("12")).Render("(new worktree)")
		}

		b.WriteString(cursor + label + "\n")
	}

	return b.String()
}
