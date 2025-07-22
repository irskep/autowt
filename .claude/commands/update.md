1. `mise run format && mise run lint`, then fix issues
2. `mise run tests`, then fix issues
3. Update CHANGELOG.md with a brief description of changes made if and only if they are user-facing.
4. Review changes with `git status` and `git diff`, checking for commits vs origin/{branch}, as well as unstaged cahnges, and staged changes
5. Stage and commit changes:

   ```bash
   git add . # or an appropriate set of files
   git commit -m "$(cat <<'EOF'
   [Your commit message here]
   
   🤖 Generated with [Claude Code](https://claude.ai/code)
   
   Co-Authored-By: Claude <noreply@anthropic.com>
   EOF
   )"
   ```

   Avoid unnecessary lists in your commit message. Avoid adding filler to lists to make them longer.
6. `git push -u origin HEAD`
7. Edit the existing open pull request using the `gh` command
8. Monitor CI with `uv run cimonitor watch --pr=<pr-number>`
