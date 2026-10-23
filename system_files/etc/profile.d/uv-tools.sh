# Personal commands override shared tools; never export shared UV_* settings.
case ":${PATH}:" in
    *:/var/lib/uv-tools/bin:*) ;;
    *) PATH="/var/lib/uv-tools/bin:${PATH}" ;;
esac
case "${PATH}" in
    "${HOME}/.local/bin":*) ;;
    *) PATH="${HOME}/.local/bin:${PATH}" ;;
esac
export PATH
