if status is-interactive
    ### Commands to run in interactive sessions can go here
    
    ### Set path
    #fish_add_path ~/.rfswift/bin
    fish_add_path ~/bin
    fish_add_path ~/.local/bin
    #fish_add_path ~/go/bin
    #fish_add_path /usr/sbin
    #fish_add_path /usr/local/sbin

    ### Set colors for man pages
    #setaf = forground, setab = background
    #0=black 1=red 2=green 3=yellow 4=blue 5=purple 6=cyan 7=white
    set -x fish_greeting "Welcome to Fish!"
    set -x LESS_TERMCAP_mb $(tput bold; tput setaf 1)  # Start blink mode
    set -x LESS_TERMCAP_md $(tput bold; tput setaf 3)  # Start bold mode
    set -x LESS_TERMCAP_mr $(tput rev)                 # Start reverse mode
    set -x LESS_TERMCAP_mh $(tput dim)                 # Start dim mode
    set -x LESS_TERMCAP_so $(tput bold; tput setaf 1; tput setab 4)   # Start standout mode
    set -x LESS_TERMCAP_se $(tput rmso; tput sgr0)     # Stop standout mode
    set -x LESS_TERMCAP_us $(tput smul; tput bold; tput setaf 6)  # Start underline mode
    set -x LESS_TERMCAP_ue $(tput rmul; tput sgr0)     # Stop underline mode
    set -x LESS_TERMCAP_ZN $(tput ssubm)               # Start subscript mode
    set -x LESS_TERMCAP_ZV $(tput rsubm)               # Stop subscript mode
    set -x LESS_TERMCAP_ZO $(tput ssupm)               # Start superscript mode
    set -x LESS_TERMCAP_ZW $(tput rsupm)               # Stop subscript mode
    set -x LESS_TERMCAP_me $(tput sgr0)                # Stop all modes
    set -x GROFF_NO_SGR 1                                # Old drawing scheme

    ### Functions

    ### Set environmental variables
    set -x EDITOR /usr/bin/vim
    set -x SYSTEMD_EDITOR /usr/bin/vim
    set -x PAGER moor
    set -x QT_QPA_PLATFORM wayland

    ### Aliases
    #alias bat='bat -p --pager "less -RFSM --shift 4 --use-color --color Ny"'
    #alias dnf="dnf -C"
    alias c="clear"
    alias cm="clear && macchina -t ControlThings"
    #alias edit="gnome-text-editor"

    ### Abbreviations
    abbr -a kf   "kate ~/.config/fish/config.fish"
    ## systemctl
    abbr -a s    "systemctl"
    abbr -a sss  "sudo systemctl status"
    abbr -a sst  "sudo systemctl start"
    abbr -a ssp  "sudo systemctl stop"
    abbr -a ssr  "sudo systemctl restart"
    abbr -a ssd  "sudo systemctl disable"
    abbr -a ssn  "sudo systemctl enable"
    abbr -a sse  "sudo systemctl edit"
    abbr -a ssdr "sudo systemctl daemon-reload"
    ## journalctl
    abbr -a j    "journalctl"
    abbr -a jb   "journalctl -b"
    abbr -a jk   "journalctl -k"
    ## dnf
    #abbr -a ds   "dnf search"
    #abbr -a di   "dnf info"
    #abbr -a dl   "dnf list"
    #abbr -a dle  "dnf list extras"
    #abbr -a dli  "dnf list --installed"
    #abbr -a dliu "dnf repoquery --installed --userinstalled"
    #abbr -a sdi  "sudo dnf install"
    #abbr -a sdu  "sudo dnf update"
    #abbr -a sdr  "sudo dnf remove"
    #abbr -a sdc  "sudo dnf clean all"
    #abbr -a dhl  "dnf history list"
    #abbr -a dhi  "dnf history info"
    #abbr -a drq  "dnf repoquery -l"
    #abbr -a drl  "dnf repo list --all"
    #abbr -a dcd  "sudo dnf config-manager disable"
    #abbr -a sdp  "sudo dnf provides"
    ## flatpak
    abbr -a f    "flatpak"
    abbr -a fe   "flatpak enter"
    abbr -a fh   "flatpak history"
    abbr -a fi   "flatpak info"
    abbr -a fI   "flatpak install"
    abbr -a fl   "flatpak list --columns name,branch,version,size,description"
    abbr -a fla  "flatpak list --app --columns name,application,branch,version,size,runtime"
    abbr -a flr  "flatpak list --runtime --columns name,application,branch,version,size,description"
    abbr -a fr   "flatpak run"
    abbr -a fs   "flatpak search"
    abbr -a fu   "flatpak uninstall"
    abbr -a fuu  "flatpak uninstall --unused"
    ## podman
    abbr -a pil  "podman image list"
    abbr -a pir  "podman image rm"
    abbr -a pcl  "podman container list"
    abbr -a pcs  "podman container start"
    abbr -a pcS  "podman container stop"
    abbr -a pr   "podman run"
    ## other
    abbr -a pg   "ps -Al | grep"
    abbr -a tigard-spi  "flashrom -p ft2232_spi:type=2232H,port=B,divisor=4 -r dump.bin"
    abbr -a rqk  "sudo rpm -q gpg-pubkey --qf '%{NAME}-%{VERSION}-%{RELEASE}\t%{SUMMARY}\n'"
    abbr -a bs   "brew search"
    abbr -a bi   "brew info"
    abbr -a bI   "brew install"
    abbr -a bu   "brew upgrade"
    
    ### Commands
    mkdir -p /tmp/$USER && ln -Tfs /tmp/$USER /home/$USER/tmp
    eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
    
    ### Set terminal splash screen
    sleep 0.2
    macchina -t ControlThings

    ### Set prompt (config at ~/.config/starship.toml)
    starship init fish | source

end

