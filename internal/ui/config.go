package ui

import (
	"fmt"
	"strings"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
	"github.com/irskep/autowt/internal/config"
	"github.com/irskep/autowt/internal/model"
)

// RunConfigTUI presents an interactive editor for global config settings.
// Returns the modified config if the user saved, or nil if cancelled.
func RunConfigTUI(cfg config.Config) (*config.Config, error) {
	fields := buildConfigFields(cfg)
	m := configModel{fields: fields, cfg: cfg}
	p := tea.NewProgram(m)
	final, err := p.Run()
	if err != nil {
		return nil, err
	}

	fm := final.(configModel)
	if fm.cancelled {
		return nil, nil
	}

	result := applyFieldsToConfig(fm.cfg, fm.fields)
	return &result, nil
}

type configField struct {
	label    string
	value    string
	options  []string // if non-nil, cycle through options
	optIndex int
}

type configModel struct {
	fields    []configField
	cursor    int
	cfg       config.Config
	cancelled bool
}

func buildConfigFields(cfg config.Config) []configField {
	terminalModes := []string{"tab", "window", "inplace", "echo", "vscode", "cursor"}
	cleanupModes := []string{"interactive", "merged", "remoteless", "all", "github"}

	termIdx := indexOf(terminalModes, string(cfg.Terminal.Mode))
	cleanIdx := indexOf(cleanupModes, string(cfg.Cleanup.DefaultMode))

	return []configField{
		{label: "Terminal mode", value: string(cfg.Terminal.Mode), options: terminalModes, optIndex: termIdx},
		{label: "Always new session", value: boolStr(cfg.Terminal.AlwaysNew), options: []string{"false", "true"}, optIndex: boolIdx(cfg.Terminal.AlwaysNew)},
		{label: "Directory pattern", value: cfg.Worktree.DirectoryPattern},
		{label: "Auto fetch", value: boolStr(cfg.Worktree.AutoFetch), options: []string{"false", "true"}, optIndex: boolIdx(cfg.Worktree.AutoFetch)},
		{label: "Branch prefix", value: cfg.Worktree.BranchPrefix},
		{label: "Default cleanup mode", value: string(cfg.Cleanup.DefaultMode), options: cleanupModes, optIndex: cleanIdx},
	}
}

func applyFieldsToConfig(cfg config.Config, fields []configField) config.Config {
	cfg.Terminal.Mode = model.TerminalMode(fields[0].value)
	cfg.Terminal.AlwaysNew = fields[1].value == "true"
	cfg.Worktree.DirectoryPattern = fields[2].value
	cfg.Worktree.AutoFetch = fields[3].value == "true"
	cfg.Worktree.BranchPrefix = fields[4].value
	cfg.Cleanup.DefaultMode = model.CleanupMode(fields[5].value)
	return cfg
}

func (m configModel) Init() tea.Cmd {
	return nil
}

func (m configModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
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
			if m.cursor < len(m.fields)-1 {
				m.cursor++
			}
		case "left", "h":
			f := &m.fields[m.cursor]
			if f.options != nil && f.optIndex > 0 {
				f.optIndex--
				f.value = f.options[f.optIndex]
			}
		case "right", "l", " ":
			f := &m.fields[m.cursor]
			if f.options != nil && f.optIndex < len(f.options)-1 {
				f.optIndex++
				f.value = f.options[f.optIndex]
			}
		}
	}
	return m, nil
}

func (m configModel) View() string {
	var b strings.Builder

	headerStyle := lipgloss.NewStyle().Bold(true)
	b.WriteString(headerStyle.Render("autowt configuration"))
	b.WriteString("\n")
	b.WriteString(dimStyle.Render("  ←/→: change value  enter: save  q: cancel"))
	b.WriteString("\n\n")

	labelWidth := 0
	for _, f := range m.fields {
		if len(f.label) > labelWidth {
			labelWidth = len(f.label)
		}
	}

	for i, f := range m.fields {
		cursor := "  "
		if i == m.cursor {
			cursor = cursorStyle.Render("> ")
		}

		label := fmt.Sprintf("%-*s", labelWidth, f.label)
		value := f.value
		if f.options != nil {
			value = renderOptions(f.options, f.optIndex, i == m.cursor)
		}

		b.WriteString(fmt.Sprintf("%s%s  %s\n", cursor, label, value))
	}

	return b.String()
}

func renderOptions(options []string, selected int, active bool) string {
	var parts []string
	for i, opt := range options {
		if i == selected {
			if active {
				parts = append(parts, selectedStyle.Render("["+opt+"]"))
			} else {
				parts = append(parts, "["+opt+"]")
			}
		} else {
			parts = append(parts, dimStyle.Render(opt))
		}
	}
	return strings.Join(parts, " ")
}

func indexOf(slice []string, val string) int {
	for i, s := range slice {
		if s == val {
			return i
		}
	}
	return 0
}

func boolStr(b bool) string {
	if b {
		return "true"
	}
	return "false"
}

func boolIdx(b bool) int {
	if b {
		return 1
	}
	return 0
}
