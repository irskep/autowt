# Terminal Integration

## Terminal Session Management

### Session Tracking Architecture
- **Session ID registration**: New terminals automatically register with autowt
- **Session persistence**: Mapping stored in `sessionids.toml`
- **Intelligent switching**: Finds existing sessions before creating new ones
- **Fallback discovery**: Directory-based session detection for supported terminals

### Terminal Mode Options
- **Tab mode (`--terminal=tab`)**: Switch to existing session or create new tab
- **Window mode (`--terminal=window`)**: Switch to existing session or create new window
- **Inplace mode (`--terminal=inplace`)**: Output shell commands for current terminal

### Smart Session Switching
- **Existing session detection**: Checks for active terminal in target worktree
- **User choice prompts**: Ask whether to switch to existing or create new
- **Auto-confirmation**: `--yes` flag switches to existing without prompting
- **Session state validation**: Verifies session still exists before switching

## Platform-Specific Integration

### macOS Terminal Support
#### iTerm2 (Fully Tested)
- **AppleScript integration**: Native session creation and switching
- **Session UUID tracking**: Precise session identification
- **Tab management**: Create tabs within existing windows
- **Window management**: Create new windows as needed
- **Session validation**: Check if sessions still exist

#### Terminal.app (Fully Tested)
- **AppleScript integration**: Native macOS terminal support
- **Working directory identification**: Uses directory as session identifier
- **TTY discovery**: Maps working directories to terminal sessions
- **Tab and window support**: Full integration with Terminal.app features

### Cross-Platform Terminal Support
#### tmux (Universal)
- **Native session management**: `autowt-{branch}` session naming
- **Session persistence**: Survives terminal application restarts
- **Cross-platform compatibility**: Works on macOS, Linux, Windows
- **Robust switching**: Reliable session detection and switching

#### Modern Terminal Applications
- **Alacritty**: Basic process spawning, limited session tracking
- **Kitty**: Directory-based session discovery
- **WezTerm**: Experimental support for session management
- **Hyper**: Basic process spawning without session tracking

### Linux Terminal Support (Experimental)
- **GNOME Terminal**: Desktop environment integration
- **Konsole**: KDE desktop terminal support
- **XFCE Terminal**: XFCE desktop environment
- **Tilix**: Advanced terminal emulator support
- **Terminator**: Multi-pane terminal support

### Windows Terminal Support (Experimental)
- **Windows Terminal**: Basic tab and window creation
- **Session tracking**: Limited session identification
- **Process spawning**: Fallback to basic directory switching

## Terminal Behavior Configuration

### Default Mode Configuration
- **Global preferences**: Set via `autowt config` TUI
- **Per-command override**: `--terminal=mode` flag
- **Project-specific defaults**: Configure in `autowt.toml`
- **Environment variables**: Override through environment

### Session Creation Preferences
- **Always create new**: Never switch to existing sessions
- **Smart switching**: Prompt for existing vs new (default)
- **Always switch**: Never create new if existing session found
- **Terminal-specific behavior**: Different modes for different terminals

### Init Script Integration
- **Post-directory change**: Scripts run after changing to worktree
- **Terminal-specific execution**: Scripts run in appropriate terminal context
- **Environment inheritance**: Inherit environment from parent terminal
- **Error handling**: Script failures don't prevent terminal switching

## Session Lifecycle Management

### Session Registration
- **Automatic registration**: New terminals register on startup
- **Session ID generation**: Unique identifiers for each session
- **State persistence**: Session mappings saved across autowt runs
- **Cross-terminal consistency**: Same session ID format across platforms

### Session Discovery
1. **Check registered sessions**: Look up stored session IDs
2. **Validate session existence**: Verify sessions are still active
3. **Fallback to directory detection**: Find sessions by working directory
4. **Process-based discovery**: Use process information for session matching

### Session Cleanup and Maintenance
- **Stale session removal**: Clean up sessions for removed terminals
- **Process validation**: Check if terminal processes still exist
- **Directory-based cleanup**: Remove sessions for deleted worktrees
- **Manual session management**: Tools for session debugging and repair

## Cleanup Impact on Terminal Sessions

### Pre-Cleanup Session Analysis
- **Active session detection**: Identify terminals running in target worktrees
- **Process discovery**: Find all processes with open files in directories
- **User notification**: Show which terminals will be affected
- **Impact assessment**: Preview of terminal sessions that will be closed

### Process Termination During Cleanup
1. **Graceful termination**: Send SIGINT to all processes in worktree
2. **Wait period**: Allow 10 seconds for graceful shutdown
3. **Force termination**: Send SIGKILL to remaining processes
4. **Terminal closure**: Terminal sessions automatically close
5. **Session cleanup**: Remove session mappings from state

### Session State Management
- **Session mapping updates**: Remove entries for cleaned worktrees
- **State consistency**: Ensure session state matches actual terminals
- **Orphaned session cleanup**: Remove mappings for non-existent sessions
- **Recovery procedures**: Handle partial cleanup failures

### Post-Cleanup Session Recovery
- **Session validation**: Check remaining sessions for consistency
- **State file updates**: Update session mappings after cleanup
- **Terminal re-registration**: Allow terminals to re-register if needed
- **Manual recovery**: Tools for fixing session state issues

## Advanced Terminal Features

### Environment Management
- **Variable inheritance**: Pass environment variables to new terminals
- **Path management**: Ensure correct PATH in new sessions
- **Shell configuration**: Respect user shell preferences and configs
- **Working directory**: Set correct initial directory in terminals

### Terminal Window Management
- **Window positioning**: Place new windows in convenient locations
- **Tab organization**: Group related worktrees in same windows
- **Focus management**: Control which terminal receives focus
- **Multi-monitor support**: Distribute terminals across displays

### Integration with Development Tools
- **IDE integration**: Work alongside terminal-based IDEs
- **Multiplexer compatibility**: Support for screen, tmux, etc.
- **Shell integration**: Work with zsh, bash, fish configurations
- **Development server management**: Handle long-running processes

## Troubleshooting Terminal Issues

### Common Session Problems
- **Session not found**: Recovery from missing session mappings
- **Terminal not responding**: Handle unresponsive terminal applications
- **Permission issues**: AppleScript and terminal access permissions
- **Platform detection**: Fallback when terminal detection fails

### Debug and Diagnostic Tools
- **Session listing**: Show all registered sessions
- **Process discovery**: Debug process detection mechanisms
- **Terminal detection**: Verify platform and terminal identification
- **State validation**: Check consistency of session state

### Manual Session Management
- **Session cleanup**: Remove stale or invalid sessions
- **Force registration**: Manually register current terminal
- **Reset session state**: Clear all session mappings
- **Diagnostic output**: Detailed logging for troubleshooting

## Best Practices for Terminal Usage

### Workflow Optimization
- **Consistent terminal choice**: Stick to one terminal application
- **Session hygiene**: Regular cleanup of stale sessions
- **Window organization**: Logical grouping of worktree terminals
- **Keyboard shortcuts**: Learn terminal-specific switching shortcuts

### Performance Considerations
- **Session limits**: Be aware of terminal session resource usage
- **Process cleanup**: Ensure proper cleanup of background processes
- **State file maintenance**: Regular validation of session state
- **Terminal restart handling**: Graceful handling of terminal restarts

### Multi-User Environments
- **User-specific sessions**: Isolate sessions between users
- **Shared worktree access**: Handle multiple users in same worktrees
- **Permission management**: Proper file and process permissions
- **Collaboration patterns**: Best practices for shared development