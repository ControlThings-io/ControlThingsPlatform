# Session-only PATH changes; do not alter universal fish_user_paths.
set -l uv_tools_path
for entry in $PATH
    if not contains -- $entry $HOME/.local/bin /var/lib/uv-tools/bin
        set -a uv_tools_path $entry
    end
end
set -gx PATH $HOME/.local/bin /var/lib/uv-tools/bin $uv_tools_path
