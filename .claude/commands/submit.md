# Submit changes

1. `mise run format && mise run lint`, then fix issues
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
6. Create a PR:

   ```bash
   gh pr create --title "[PR Title]" --body "$(cat <<'EOF'
   <message>
   
   🤖 Generated with [Claude Code](https://claude.ai/code)
   EOF
   )"
   ```

   Avoid unnecessary lists in the PR description. PR descriptions do not have a minimum length, just do what's appropriate. Adding fluff and over-emphasizing minor points makes you seem less intelligent.
7. Monitor CI with `uv run cimonitor watch --pr=<pr-number>`
