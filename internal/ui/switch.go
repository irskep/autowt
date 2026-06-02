package ui

import (
	"fmt"
	"strings"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/irskep/autowt/internal/model"
)

// SwitchResult is what RunSwitchTUI returns.
type SwitchResult struct {
	Branch string
}

// RunSwitchTUI presents existing worktrees for the user to select.
func RunSwitchTUI(worktrees []model.WorktreeInfo) (*SwitchResult, error) {
	m := switchModel{items: switchItemsForWorktrees(worktrees)}
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
	}, nil
}

func switchItemsForWorktrees(worktrees []model.WorktreeInfo) []switchItem {
	items := make([]switchItem, 0, len(worktrees))
	for _, wt := range worktrees {
		items = append(items, switchItem{
			label:      wt.Branch,
			isWorktree: true,
			path:       wt.DisplayPath(),
		})
	}
	return items
}

type switchItem struct {
	label      string
	isWorktree bool
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

	b.WriteString("Select a worktree:\n")
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
		}

		b.WriteString(cursor + label + "\n")
	}

	return b.String()
}
