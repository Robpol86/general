export HISTCONTROL=erasedups
export HISTSIZE=100000
shopt -s histappend

export LC_CTYPE=en_US.UTF-8
export CLICOLOR=1
export LSCOLORS=gxGxFxdxbxDxDxBxBxExEx

if [ -e "/opt/git/etc/bash_completion.d/git-completion.bash" ]; then
  if [ -e "/opt/git/etc/bash_completion.d/git-prompt.sh" ]; then
    # Both of these files are required.
    source "/opt/git/etc/bash_completion.d/git-completion.bash"
    source "/opt/git/etc/bash_completion.d/git-prompt.sh"
    export PS1='[\h \[\033[0;36m\]\W\[\033[0m\]$(__git_ps1 " \[\033[1;32m\](%s)\[\033[0m\]")]\$ '
  fi
else
  export PS1='[\h \[\033[0;36m\]\W\[\033[0m\]]\$ '
fi
