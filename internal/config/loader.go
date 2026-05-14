package config

import (
	"fmt"
	"log/slog"
	"os"
	"path/filepath"
	"strings"

	"github.com/BurntSushi/toml"
	"github.com/irskep/autowt/internal/model"
)

// Loader handles loading and merging configuration from multiple sources.
type Loader struct {
	AppDir           string
	GlobalConfigFile string
}

// NewLoader creates a Loader with the default OS-specific config directory.
func NewLoader() *Loader {
	dir := DefaultConfigDir()
	return &Loader{
		AppDir:           dir,
		GlobalConfigFile: filepath.Join(dir, "config.toml"),
	}
}

// Load reads configuration with cascading precedence:
// defaults -> global file -> project file -> env vars -> CLI overrides.
func (l *Loader) Load(projectDir string, cliOverrides map[string]any) (Config, error) {
	cfg := DefaultConfig()

	// Global config.
	if data, err := l.loadTOMLFile(l.GlobalConfigFile); err == nil {
		applyTOMLData(&cfg, data)
	} else if !os.IsNotExist(err) {
		slog.Warn("Failed to load global config", "path", l.GlobalConfigFile, "error", err)
	}

	// Project config.
	if projectDir != "" {
		for _, name := range []string{"autowt.toml", ".autowt.toml"} {
			path := filepath.Join(projectDir, name)
			if data, err := l.loadTOMLFile(path); err == nil {
				applyTOMLData(&cfg, data)
				break
			}
		}
	}

	// Environment variables.
	applyEnvVars(&cfg)

	// CLI overrides.
	if cliOverrides != nil {
		applyCLIOverrides(&cfg, cliOverrides)
	}

	return cfg, nil
}

// LoadGlobalOnly loads only the global config (no project, env, or CLI overrides).
func (l *Loader) LoadGlobalOnly() (Config, error) {
	cfg := DefaultConfig()
	if data, err := l.loadTOMLFile(l.GlobalConfigFile); err == nil {
		applyTOMLData(&cfg, data)
	} else if !os.IsNotExist(err) {
		return cfg, fmt.Errorf("loading global config: %w", err)
	}
	return cfg, nil
}

// LoadProjectHookConfig loads only the project hook definitions.
func (l *Loader) LoadProjectHookConfig(projectDir string) HookConfig {
	for _, name := range []string{"autowt.toml", ".autowt.toml"} {
		path := filepath.Join(projectDir, name)
		if data, err := l.loadTOMLFile(path); err == nil {
			return hookConfigFromTOML(data)
		}
	}
	return HookConfig{}
}

// LoadGlobalHookConfig loads only the global hook definitions.
func (l *Loader) LoadGlobalHookConfig() HookConfig {
	if data, err := l.loadTOMLFile(l.GlobalConfigFile); err == nil {
		return hookConfigFromTOML(data)
	}
	return HookConfig{}
}

// HasUserConfiguredCleanupMode checks if the user has set a cleanup mode.
func (l *Loader) HasUserConfiguredCleanupMode() bool {
	data, err := l.loadTOMLFile(l.GlobalConfigFile)
	if err != nil {
		return false
	}
	cleanup, ok := data["cleanup"].(map[string]any)
	if !ok {
		return false
	}
	_, ok = cleanup["default_mode"]
	return ok
}

// SaveCleanupMode updates only the cleanup.default_mode in the global config.
func (l *Loader) SaveCleanupMode(mode model.CleanupMode) error {
	if err := os.MkdirAll(l.AppDir, 0o755); err != nil {
		return err
	}

	existing := make(map[string]any)
	if _, err := toml.DecodeFile(l.GlobalConfigFile, &existing); err != nil && !os.IsNotExist(err) {
		return fmt.Errorf("cannot save cleanup mode: failed to parse existing config at %s: %w", l.GlobalConfigFile, err)
	}

	cleanup, ok := existing["cleanup"].(map[string]any)
	if !ok {
		cleanup = make(map[string]any)
		existing["cleanup"] = cleanup
	}
	cleanup["default_mode"] = string(mode)

	return l.writeTOML(l.GlobalConfigFile, existing)
}

// SaveConfig writes the full config to the global config file.
func (l *Loader) SaveConfig(cfg Config) error {
	if err := os.MkdirAll(l.AppDir, 0o755); err != nil {
		return err
	}

	// Validate existing file is parseable before overwriting.
	if _, err := os.Stat(l.GlobalConfigFile); err == nil {
		var check map[string]any
		if _, err := toml.DecodeFile(l.GlobalConfigFile, &check); err != nil {
			return fmt.Errorf("cannot save config: existing file at %s has invalid TOML: %w", l.GlobalConfigFile, err)
		}
	}

	data := configToTOML(cfg)
	return l.writeTOML(l.GlobalConfigFile, data)
}

func (l *Loader) loadTOMLFile(path string) (map[string]any, error) {
	data := make(map[string]any)
	_, err := toml.DecodeFile(path, &data)
	return data, err
}

func (l *Loader) writeTOML(path string, data map[string]any) error {
	f, err := os.Create(path)
	if err != nil {
		return err
	}
	defer f.Close()
	return toml.NewEncoder(f).Encode(data)
}

// applyTOMLData merges parsed TOML data onto an existing config.
func applyTOMLData(cfg *Config, data map[string]any) {
	if terminal, ok := data["terminal"]; ok {
		switch v := terminal.(type) {
		case string:
			cfg.Terminal.Mode = model.TerminalMode(v)
		case map[string]any:
			if mode, ok := v["mode"].(string); ok {
				cfg.Terminal.Mode = model.TerminalMode(mode)
			}
			if alwaysNew, ok := v["always_new"].(bool); ok {
				cfg.Terminal.AlwaysNew = alwaysNew
			}
			if program, ok := v["program"].(string); ok {
				cfg.Terminal.Program = program
			}
		}
	}

	if worktree, ok := data["worktree"].(map[string]any); ok {
		if dp, ok := worktree["directory_pattern"].(string); ok {
			cfg.Worktree.DirectoryPattern = dp
		}
		if af, ok := worktree["auto_fetch"].(bool); ok {
			cfg.Worktree.AutoFetch = af
		}
		if bp, ok := worktree["branch_prefix"].(string); ok {
			cfg.Worktree.BranchPrefix = bp
		}
	}

	if cleanup, ok := data["cleanup"].(map[string]any); ok {
		if dm, ok := cleanup["default_mode"].(string); ok {
			cfg.Cleanup.DefaultMode = model.CleanupMode(dm)
		}
	}

	if scripts, ok := data["scripts"].(map[string]any); ok {
		applyScriptsData(&cfg.Scripts, scripts)
	}

	if confirmations, ok := data["confirmations"].(map[string]any); ok {
		if cm, ok := confirmations["cleanup_multiple"].(bool); ok {
			cfg.Confirmations.CleanupMultiple = cm
		}
		if fo, ok := confirmations["force_operations"].(bool); ok {
			cfg.Confirmations.ForceOperations = fo
		}
	}
}

func applyScriptsData(scripts *ScriptsConfig, data map[string]any) {
	// Handle init -> session_init backward compatibility.
	if si, ok := data["session_init"].(string); ok {
		scripts.SessionInit = si
	} else if init, ok := data["init"].(string); ok {
		slog.Warn("The 'init' script key is deprecated; rename to 'session_init'")
		scripts.SessionInit = init
	}

	if v, ok := data["pre_create"].(string); ok {
		scripts.PreCreate = v
	}
	if v, ok := data["post_create"].(string); ok {
		scripts.PostCreate = v
	}
	if v, ok := data["post_create_async"].(string); ok {
		scripts.PostCreateAsync = v
	}
	if v, ok := data["pre_cleanup"].(string); ok {
		scripts.PreCleanup = v
	}
	if v, ok := data["post_cleanup"].(string); ok {
		scripts.PostCleanup = v
	}
	if v, ok := data["pre_switch"].(string); ok {
		scripts.PreSwitch = v
	}
	if v, ok := data["post_switch"].(string); ok {
		scripts.PostSwitch = v
	}

	if custom, ok := data["custom"].(map[string]any); ok {
		for name, val := range custom {
			cs := model.CustomScript{InheritHooks: true}
			switch v := val.(type) {
			case string:
				cs.SessionInit = v
			case map[string]any:
				if d, ok := v["description"].(string); ok {
					cs.Description = d
				}
				if bn, ok := v["branch_name"].(string); ok {
					cs.BranchName = bn
				}
				if ih, ok := v["inherit_hooks"].(bool); ok {
					cs.InheritHooks = ih
				}
				if s, ok := v["session_init"].(string); ok {
					cs.SessionInit = s
				}
				if s, ok := v["pre_create"].(string); ok {
					cs.PreCreate = s
				}
				if s, ok := v["post_create"].(string); ok {
					cs.PostCreate = s
				}
				if s, ok := v["post_create_async"].(string); ok {
					cs.PostCreateAsync = s
				}
				if s, ok := v["pre_cleanup"].(string); ok {
					cs.PreCleanup = s
				}
				if s, ok := v["post_cleanup"].(string); ok {
					cs.PostCleanup = s
				}
				if s, ok := v["pre_switch"].(string); ok {
					cs.PreSwitch = s
				}
				if s, ok := v["post_switch"].(string); ok {
					cs.PostSwitch = s
				}
			}
			scripts.Custom[name] = cs
		}
	}
}

func hookConfigFromTOML(data map[string]any) HookConfig {
	hc := HookConfig{}
	scripts, ok := data["scripts"].(map[string]any)
	if !ok {
		return hc
	}
	if v, ok := scripts["pre_create"].(string); ok {
		hc.PreCreate = v
	}
	if v, ok := scripts["post_create"].(string); ok {
		hc.PostCreate = v
	}
	if v, ok := scripts["post_create_async"].(string); ok {
		hc.PostCreateAsync = v
	}
	if v, ok := scripts["session_init"].(string); ok {
		hc.SessionInit = v
	} else if v, ok := scripts["init"].(string); ok {
		hc.SessionInit = v
	}
	if v, ok := scripts["pre_cleanup"].(string); ok {
		hc.PreCleanup = v
	}
	if v, ok := scripts["post_cleanup"].(string); ok {
		hc.PostCleanup = v
	}
	if v, ok := scripts["pre_switch"].(string); ok {
		hc.PreSwitch = v
	}
	if v, ok := scripts["post_switch"].(string); ok {
		hc.PostSwitch = v
	}
	return hc
}

// applyEnvVars reads AUTOWT_* environment variables and applies them.
func applyEnvVars(cfg *Config) {
	envMap := map[string]func(string){
		"AUTOWT_TERMINAL_MODE":                    func(v string) { cfg.Terminal.Mode = model.TerminalMode(v) },
		"AUTOWT_TERMINAL_ALWAYS_NEW":              func(v string) { cfg.Terminal.AlwaysNew = parseBool(v) },
		"AUTOWT_TERMINAL_PROGRAM":                 func(v string) { cfg.Terminal.Program = v },
		"AUTOWT_WORKTREE_DIRECTORY_PATTERN":       func(v string) { cfg.Worktree.DirectoryPattern = v },
		"AUTOWT_WORKTREE_AUTO_FETCH":              func(v string) { cfg.Worktree.AutoFetch = parseBool(v) },
		"AUTOWT_WORKTREE_BRANCH_PREFIX":           func(v string) { cfg.Worktree.BranchPrefix = v },
		"AUTOWT_CLEANUP_DEFAULT_MODE":             func(v string) { cfg.Cleanup.DefaultMode = model.CleanupMode(v) },
		"AUTOWT_SCRIPTS_SESSION_INIT":             func(v string) { cfg.Scripts.SessionInit = v },
		"AUTOWT_SCRIPTS_PRE_CREATE":               func(v string) { cfg.Scripts.PreCreate = v },
		"AUTOWT_SCRIPTS_POST_CREATE":              func(v string) { cfg.Scripts.PostCreate = v },
		"AUTOWT_SCRIPTS_POST_CREATE_ASYNC":        func(v string) { cfg.Scripts.PostCreateAsync = v },
		"AUTOWT_SCRIPTS_PRE_CLEANUP":              func(v string) { cfg.Scripts.PreCleanup = v },
		"AUTOWT_SCRIPTS_POST_CLEANUP":             func(v string) { cfg.Scripts.PostCleanup = v },
		"AUTOWT_SCRIPTS_PRE_SWITCH":               func(v string) { cfg.Scripts.PreSwitch = v },
		"AUTOWT_SCRIPTS_POST_SWITCH":              func(v string) { cfg.Scripts.PostSwitch = v },
		"AUTOWT_CONFIRMATIONS_CLEANUP_MULTIPLE":   func(v string) { cfg.Confirmations.CleanupMultiple = parseBool(v) },
		"AUTOWT_CONFIRMATIONS_FORCE_OPERATIONS":   func(v string) { cfg.Confirmations.ForceOperations = parseBool(v) },
	}

	for key, apply := range envMap {
		if val := os.Getenv(key); val != "" {
			apply(val)
		}
	}
}

func parseBool(s string) bool {
	switch strings.ToLower(s) {
	case "true", "yes", "1", "on":
		return true
	default:
		return false
	}
}

func applyCLIOverrides(cfg *Config, overrides map[string]any) {
	if v, ok := overrides["terminal_mode"].(string); ok && v != "" {
		cfg.Terminal.Mode = model.TerminalMode(v)
	}
	if v, ok := overrides["cleanup_mode"].(string); ok && v != "" {
		cfg.Cleanup.DefaultMode = model.CleanupMode(v)
	}
	if v, ok := overrides["after_init"].(string); ok && v != "" {
		cfg.Scripts.SessionInit = v
	}
}

func configToTOML(cfg Config) map[string]any {
	data := map[string]any{
		"terminal": map[string]any{
			"mode":       string(cfg.Terminal.Mode),
			"always_new": cfg.Terminal.AlwaysNew,
		},
		"worktree": map[string]any{
			"directory_pattern": cfg.Worktree.DirectoryPattern,
			"auto_fetch":       cfg.Worktree.AutoFetch,
		},
		"cleanup": map[string]any{
			"default_mode": string(cfg.Cleanup.DefaultMode),
		},
	}

	if cfg.Terminal.Program != "" {
		data["terminal"].(map[string]any)["program"] = cfg.Terminal.Program
	}
	if cfg.Worktree.BranchPrefix != "" {
		data["worktree"].(map[string]any)["branch_prefix"] = cfg.Worktree.BranchPrefix
	}

	return data
}
