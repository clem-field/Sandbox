gcm() {
    # Usage: gcm "my awesome feature"   (or just gcm and it will open $EDITOR)

    local branch dir ticket summary message

    # 1. Get current branch name
    branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null) \
        || { [[ $? -ne 0 ]] && echo "Not in a git repo" >&2 && return 1; }

    # 2. Extract ticket number from branch like feature/XXX-1234_desc or hotfix/1234-fix
    if [[ "$branch" =~ ([A-Z]+-[0-9]+) ]]; then
        ticket="${BASH_REMATCH[1]}"            # e.g. XXX-1234
    elif [[ "$branch" =~ ([0-9]+) ]]; then
        ticket="$BASH_REMATCH[1]"              # fallback if branch is just 1234-fix
    else
        echo "Could not detect ticket number in branch '$branch'" >&2
        return 1
    fi

    # 3. Get current directory name (basename of pwd)
    dir=$(basename "$(pwd)")

    # 4. The actual commit summary you passed (or open editor if none)
    if [[ -n "$*" ]]; then
        summary="$*"
    else
        # No argument → let user type a longer message in $EDITOR
        git commit --edit
        return $?
    fi

    # 5. Build the final commit message
    message="${ticket} - ${dir} - ${summary}"

    # 6. Do the commit (you can change -am to -m if you don't want to include staged changes automatically)
    git commit -am "$message"

    # Optional: print what we just committed
    echo "Committed: $message"
}