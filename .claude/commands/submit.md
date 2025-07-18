# Submit Changes

Follow these steps to format, lint, commit, push, create a PR, and monitor CI:

1. **Format and lint code:**
   ```bash
   mise run format
   mise run lint
   ```

2. **Check git status and review changes:**
   ```bash
   git status
   git diff
   ```

3. **Stage and commit changes:**
   ```bash
   git add .
   git commit -m "$(cat <<'EOF'
   [Your commit message here]
   
   🤖 Generated with [Claude Code](https://claude.ai/code)
   
   Co-Authored-By: Claude <noreply@anthropic.com>
   EOF
   )"
   ```

4. **Push to remote:**
   ```bash
   git push -u origin [branch-name]
   ```

5. **Create pull request:**
   ```bash
   gh pr create --title "[PR Title]" --body "$(cat <<'EOF'
   ## Summary
   - [Summary point 1]
   - [Summary point 2]
   
   ## Test plan
   - [x] [Test item 1]
   - [x] [Test item 2]
   
   🤖 Generated with [Claude Code](https://claude.ai/code)
   EOF
   )"
   ```

6. **Monitor CI:**
   ```bash
   uv run cimonitor watch --pr [PR-NUMBER]
   ```

Replace `[branch-name]`, `[PR Title]`, `[PR-NUMBER]`, and customize the commit message and PR body as needed.
