PATH="/Library/Frameworks/Python.framework/Versions/3.4/bin:${PATH}"                                                    
export PATH

export HISTCONTROL=erasedups
export HISTSIZE=100000
shopt -s histappend

export LC_CTYPE=en_US.UTF-8
export CLICOLOR=1
export LSCOLORS=gxGxFxdxbxDxDxBxBxExEx

alias grep='grep --color=auto' 2>/dev/null

if [ -f "/usr/local/etc/bash_completion" ]; then
  source "/usr/local/etc/bash_completion"
  export PS1='[\h \[\033[0;36m\]\W\[\033[0m\]$(__git_ps1 " \[\033[1;32m\](%s)\[\033[0m\]")]\$ '
else
  export PS1='[\h \[\033[0;36m\]\W\[\033[0m\]]\$ '
fi
