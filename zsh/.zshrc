# Enable Powerlevel10k instant prompt. Should stay close to the top of ~/.zshrc.  Initialization code that may require console input (password prompts, [y/n]
# confirmations, etc.) must go above this block; everything else may go below.
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi

export SSH_AUTH_SOCK=/run/user/1000/gnupg/S.gpg-agent.ssh
export EDITOR='vim'
export TERM="screen-256color"

HISTFILE="$HOME/.zsh_history"
HISTSIZE=10000000
SAVEHIST=10000000
setopt BANG_HIST                 # Treat the '!' character specially during expansion.
setopt EXTENDED_HISTORY          # Write the history file in the ":start:elapsed;command" format.
setopt INC_APPEND_HISTORY        # Write to the history file immediately, not when the shell exits.
setopt SHARE_HISTORY             # Share history between all sessions.
setopt HIST_EXPIRE_DUPS_FIRST    # Expire duplicate entries first when trimming history.
setopt HIST_IGNORE_DUPS          # Don't record an entry that was just recorded again.
setopt HIST_IGNORE_ALL_DUPS      # Delete old recorded entry if new entry is a duplicate.
setopt HIST_FIND_NO_DUPS         # Do not display a line previously found.
setopt HIST_IGNORE_SPACE         # Don't record an entry starting with a space.
setopt HIST_SAVE_NO_DUPS         # Don't write duplicate entries in the history file.
setopt HIST_REDUCE_BLANKS        # Remove superfluous blanks before recording entry.
setopt HIST_VERIFY               # Don't execute immediately upon history expansion.
setopt HIST_BEEP                 # Beep when accessing nonexistent history.

ZSH_TMUX_AUTOSTART=true;
ZSH_TMUX_AUTOCONNECT=true;

if which antibody > /dev/null; then
	plugin_txt=${HOME}/.zsh_plugins.txt
	plugin_sh=${HOME}/.zsh_plugins.sh

	function antibody_reload() {
		antibody bundle < $plugin_txt > $plugin_sh
	}

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
		antibody_reload
	fi
	source $plugin_sh
else
	# Set up the prompt
	
	autoload -Uz promptinit
	promptinit
	prompt adam1
fi

autoload -U +X compinit && compinit
# compinit optimization for oh-my-zsh
# On slow systems, checking the cached .zcompdump file to see if it must be
# regenerated adds a noticable delay to zsh startup.  This little hack restricts
# it to once a day.  It should be pasted into your own completion file.
#
# The globbing is a little complicated here:
# - '#q' is an explicit glob qualifier that makes globbing work within zsh's [[ ]] construct.
# - 'N' makes the glob pattern evaluate to nothing when it doesn't match (rather than throw a globbing error)
# - '.' matches "regular files"
# - 'mh+24' matches files (or directories or whatever) that are older than 24 hours.
# setopt extendedglob
if [[ -n "${ZSH_COMPDUMP}"(#qN.mh+24) ]]; then
    compinit -i -d "${ZSH_COMPDUMP}"
    compdump
else
    compinit -C
fi
autoload -U +X bashcompinit && bashcompinit
autoload -Uz url-quote-magic

[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh
# Use emacs keybindings even if our EDITOR is set to vi
bindkey -e

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
# preview directory's content with exa when completing cd
# disable sort when completing `git checkout`
zstyle ':completion:*:git-checkout:*' sort false
# set descriptions format to enable group support
zstyle ':completion:*:descriptions' format '[%d]'
# set list-colors to enable filename colorizing
zstyle ':completion:*' list-colors ${(s.:.)LS_COLORS}
# preview directory's content with exa when completing cd
zstyle ':fzf-tab:complete:cd:*' fzf-preview 'exa -1 --color=always $realpath'
# switch group using `,` and `.`
zstyle ':fzf-tab:*' switch-group ',' '.'

export GPG_TTY="${TTY}"
# Keyring
# if [ -z "$SSH_AUTH_SOCK" ]; then
#   eval $(gnome-keyring-daemon --start --components=ssh,secrets,gpg)
#   export SSH_AUTH_SOCK
# fi

source /home/max/.gvm/scripts/gvm
export PATH=/usr/local/go/bin:$PATH
export PATH=/home/max/.local/bin:$PATH
export PATH=/home/max/.bin:$PATH
export PATH=/home/max/.local/share/coursier/bin:$PATH
export PATH="${KREW_ROOT:-$HOME/.krew}/bin:$PATH"
export PATH=/home/max/.kafka/kafka_2.13-3.3.1/bin:$PATH

export NVM_DIR="$([ -z "${XDG_CONFIG_HOME-}" ] && printf %s "${HOME}/.nvm" || printf %s "${XDG_CONFIG_HOME}/nvm")"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh" # This loads nvm

autoload -U add-zsh-hook
load-nvmrc() {
  local nvmrc_path="$(nvm_find_nvmrc)"

  if [ -n "$nvmrc_path" ]; then
    local nvmrc_node_version=$(nvm version "$(cat "${nvmrc_path}")")

    if [ "$nvmrc_node_version" = "N/A" ]; then
      nvm install
    elif [ "$nvmrc_node_version" != "$(nvm version)" ]; then
      nvm use
    fi
  elif [ -n "$(PWD=$OLDPWD nvm_find_nvmrc)" ] && [ "$(nvm version)" != "$(nvm version default)" ]; then
    echo "Reverting to nvm default version"
    nvm use default
  fi
}
add-zsh-hook chpwd load-nvmrc
load-nvmrc

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
alias sudo='nocorrect sudo '
alias watch='watch '

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


# Undo rm alias from ohmyzsh common-aliases
# alias rm="rm -I"

# kubectl aliases
alias kg='kubectl get'
alias kgj='kubectl get jobs'
alias kd='kubectl describe'
alias kw='kubectl wait'

# git aliases
alias gcr='current_branch'
alias gmt='git mergetool --no-promt'

# docker
# alias docker=podman

complete -o nospace -C /home/max/tfenv/versions/1.0.1/terraform terraform
