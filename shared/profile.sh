# ========== Set Home Directory ===============
export HOME=/Users/$USER 

# ======== Setting proxy and docker defaults ==========
export DOCKER_DEFAULT_PLATFORM=linux/amd64

# ========== Alias prompt commands =================
alias refresh='source ~/.bash_profile'
alias tree="find . -print | sed -e 's;[^/]*/;|____;g;s;____|; |;g'"

# =========== Python Commands ====================
alias pip="pip3"
alias python="python3"

# ============ AWS_CONFIG ==================
export AWS_DEFAULT_REGION="us-east-1"
export AWS_PROFILE="default"

# ========== AWS Base login and profiles ===========
alias aws-who="aws sts get-caller-identity"
alias aws-ecr-vulcan="aws ecr get-login-password --region us-east-1 | docker login --username AWS --password stdin 752531709667.dkr.ecr.us-east-1.amazonaws.com/vulcan"
alias aws-ecr-heimdall="aws ecr get-login-password --region us-east-1 | docker login --username AWS --password stdin 752531709667.dkr.ecr.us-east-1.amazonaws.com/heimdall"
alias aws-ecr-nginx="aws ecr get-login-password --region us-east-1 | docker login --username AWS --password stdin 752531709667.dkr.ecr.us-east-1.amazonaws.com/custom-nginx"

# === Setting Prompt Details ======
parse_git_branch() {
    git branch 2> /dev/null | sed -e '/^[^*]/d' -e 's/* \(.*\)/ (\1)/'
}

export PS1="\[\e[32m\]\u@\h \[\e[35m\]\W\[\033[33m\]\$\[\033[00m\] \[\033[34m\]\$(parse_git_branch)\[\033[00m\] $ "