1. 1. `mise run format && mise run lint`, then fix issues
2. `mise run tests`, then fix issues
3. Review changes with `git status` and `git diff`, checking for commits vs the merge-base of origin/main, as well as unstaged cahnges, and staged changes
4. Stage and commit changes:

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
5. `git push -u origin HEAD`
6. Edit the existing open pull request using the `gh` command
7. Monitor CI with `uv run cimonitor watch --pr=<pr-number>`