# Enable Powerlevel10k instant prompt. Should stay close to the top of ~/.zshrc.  Initialization code that may require console input (password prompts, [y/n]
# confirmations, etc.) must go above this block; everything else may go below.
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi

if which antibody > /dev/null; then
	plugin_txt=${HOME}/.zsh_plugins.txt
	plugin_sh=${HOME}/.zsh_plugins.sh
	reload=false
	if [[ ! -f ${plugin_sh} ]]; then
		reload=true
	else
		txt_time=$(stat --format='%Y' "$(realpath "$plugin_txt")")
		sh_time=$(stat --format='%Y' "$(realpath "$plugin_sh")")
		if (( txt_time > sh_time )); then
			reload=true
		fi
	fi
	if $reload; then
		antibody bundle < $plugin_txt > $plugin_sh
	fi
	source $plugin_sh
else
	# Set up the prompt
	
	autoload -Uz promptinit
	promptinit
	prompt adam1
fi

setopt histignorealldups sharehistory

# Use emacs keybindings even if our EDITOR is set to vi
bindkey -e

# Keep 1000 lines of history within the shell and save it to ~/.zsh_history:
HISTSIZE=1000
SAVEHIST=1000
HISTFILE=~/.zsh_history

zstyle ':completion:*' auto-description 'specify: %d'
zstyle ':completion:*' completer _expand _complete _correct _approximate
zstyle ':completion:*' format 'Completing %d'
zstyle ':completion:*' group-name ''
zstyle ':completion:*' menu select=2
eval "$(dircolors -b)"
zstyle ':completion:*:default' list-colors ${(s.:.)LS_COLORS}
zstyle ':completion:*' list-prompt %SAt %p: Hit TAB for more, or the character to insert%s
zstyle ':completion:*' matcher-list '' 'm:{a-z}={A-Z}' 'm:{a-zA-Z}={A-Za-z}' 'r:|[._-]=* r:|=* l:|=*'
zstyle ':completion:*' menu select=long
zstyle ':completion:*' select-prompt %SScrolling active: current selection at %p%s
zstyle ':completion:*' use-compctl false
zstyle ':completion:*' verbose true

zstyle ':completion:*:*:kill:*:processes' list-colors '=(#b) #([0-9]#)*=0=01;31'
zstyle ':completion:*:kill:*' command 'ps -u $USER -o pid,%cpu,tty,cputime,cmd'
# set list-colors to enable filename colorizing
zstyle ':completion:*' list-colors ${(s.:.)LS_COLORS}
zstyle ":fzf-tab:*" default-color  $'\6'
zstyle ':fzf-tab:complete:cd:*' fzf-preview 'ls -1 --color=always $realpath'
zstyle ':fzf-tab:*' fzf-command 'ftb-tmux-popup'

export GPG_TTY="${TTY}"
# Keyring
# if [ -z "$SSH_AUTH_SOCK" ]; then
#   eval $(gnome-keyring-daemon --start --components=ssh,secrets,gpg)
#   export SSH_AUTH_SOCK
# fi
export SSH_AUTH_SOCK=/run/user/1000/gnupg/S.gpg-agent.ssh

source /home/max/.gvm/scripts/gvm
export PATH=$PATH:/usr/local/go/bin
export PATH=$PATH:/home/max/.local/bin

export NVM_DIR="$([ -z "${XDG_CONFIG_HOME-}" ] && printf %s "${HOME}/.nvm" || printf %s "${XDG_CONFIG_HOME}/nvm")"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh" # This loads nvm

# To customize prompt, run `p10k configure` or edit ~/.p10k.zsh.
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh

export DEBFULLNAME="Max Mizikar"
export DEBEMAIL="maxmzkr@gmail.com"

# Uses the command-not-found package zsh support
# as seen in https://www.porcheron.info/command-not-found-for-zsh/
# this is installed in Ubuntu

if [ -x /usr/lib/command-not-found -o -x /usr/share/command-not-found/command-not-found ]; then
    function command_not_found_handler {
        # check because c-n-f could've been removed in the meantime
        if [ -x /usr/lib/command-not-found ]; then
            /usr/lib/command-not-found -- "$1"
            return $?
        elif [ -x /usr/share/command-not-found/command-not-found ]; then
            /usr/share/command-not-found/command-not-found -- "$1"
            return $?
        else
            printf "zsh: command not found: %s\n" "$1" >&2
            return 127
        fi
        return 0
    }
fi

export FZF_DEFAULT_COMMAND='rg --hidden --files'
[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh

# enable color support of ls and also add handy aliases
if [ -x /usr/bin/dircolors ]; then
    test -r ~/.dircolors && eval "$(dircolors -b ~/.dircolors)" || eval "$(dircolors -b)"
    alias ls='ls --color=auto'
    #alias dir='dir --color=auto'
    #alias vdir='vdir --color=auto'

    alias grep='grep --color=auto'
    alias fgrep='fgrep --color=auto'
    alias egrep='egrep --color=auto'
fi
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'

alias ipdb='ipdb3 '
alias sudo='sudo '

notif () {
    $@ && paplay /usr/share/sounds/gnome/default/alerts/bark.ogg
}

# function to set the title of the current tab
function set-title() {
  printf '\e]2;'"${1}"'\a'
}

# function to start tmux and set title
function new-ses() {
  tmux new -s $1
  set-title $1
}

# allow for ctrl+arrow movement
bindkey "^[[1;5C" forward-word
bindkey "^[[1;5D" backward-word

ENVSDIR="${HOME}"'/.venvs'

function venv() {
    source "${ENVSDIR}"'/'"${1}"'/bin/activate'
}

function makevenv() {
    "${1}" -m venv "${ENVSDIR}"'/'"${2}"
}

function vf() {
    ls -d "${ENVSDIR}"'/'*'/' | fzf | while read file; do source $file/bin/activate; done
}

function sf() {
    sudo echo || exit 1
    state_lookup=$(sudo salt-call --local state.show_highstate --output yaml | yq e '.local as $top | .local | keys | .[] | {.: $top[.].__sls__}' -)
    all_sls=$(echo "${state_lookup}" | yq e '.[]' - | sort | uniq | paste -sd "," -)
    echo "${state_lookup}" | yq e 'keys | .[]' - | fzf | while read state;
    do
        print -s 'sudo salt-call --local --log-level debug state.sls_id '"${state}"' '"${all_sls}";
        sudo salt-call --local --log-level debug state.sls_id "${state}" "${all_sls}";
    done
}

# if systemctl --user status docker.service > /dev/null; then
# 	export DOCKER_HOST=unix://$XDG_RUNTIME_DIR/docker.sock
# fi


# kubectl aliases
alias kg='kubectl get'
alias kd='kubectl describe'
alias kw='kubectl wait'

# git aliases
alias gcr='current_branch'

# docker
alias docker=podman

autoload -U +X bashcompinit && bashcompinit
complete -o nospace -C /home/max/tfenv/versions/1.0.1/terraform terraform
