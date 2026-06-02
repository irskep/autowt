## autowt hook

Run a specific lifecycle hook

### Synopsis

Run the configured global and project hooks for the given hook type.
Useful for integrating autowt's hook configuration with other worktree tools.

Available hooks:
  pre_create
  post_create
  post_create_async
  session_init
  pre_cleanup
  post_cleanup
  pre_switch
  post_switch

```
autowt hook <hook_name> [flags]
```

### Options

```
  -h, --help   help for hook
```

### Options inherited from parent commands

```
      --debug   Enable debug logging
  -y, --yes     Automatically confirm all prompts
```

### SEE ALSO

* [autowt](autowt.md)	 - Git worktree manager

