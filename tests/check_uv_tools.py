"""Exercise shared uv policy with isolated files and mocked package/privilege calls.

Run with python3; no host accounts, packages or update settings are modified.
Live dependency/GUI/hardware checks and a booted image remain separate validation.
"""

from contextlib import ExitStack
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from io import StringIO
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
loader = SourceFileLoader('uv_tools', str(ROOT / 'system_files/usr/libexec/uv-tools'))
spec = spec_from_loader(loader.name, loader)
module = module_from_spec(spec)
loader.exec_module(module)
manifest_path = ROOT / 'system_files/usr/share/controlthings/uv-tools.json'

with tempfile.TemporaryDirectory(prefix='uv-tools-check-') as temporary:
    work = Path(temporary)
    manifest = work / 'manifest.json'
    manifest.write_bytes(manifest_path.read_bytes())
    with patch.object(module, 'MANIFEST', manifest):
        selection = module.read_manifest()
        names = [tool['package'] for tool in selection['tools']]
        assert names == ['ctmodbus', 'ctserial', 'greatfet', 'rfcat', 'urh']
        assert selection['python'] == '3.13'
        for bad in [dict(selection, python='../../python'), dict(selection, schema=2),
                    dict(selection, tools=selection['tools'] * 2),
                    dict(selection, tools=[{'package': '--help', 'commands': ['foo']}]),
                    dict(selection, tools=[{'package': 'foo', 'commands': ['../../bin']}]),
                    dict(selection, tools=[{'package': 'foo', 'commands': ['a', 'a']}])]:
            manifest.write_text(json.dumps(bad))
            try:
                module.read_manifest()
            except ValueError:
                pass
            else:
                raise AssertionError(f'Invalid manifest accepted: {bad}')
        manifest.write_bytes(manifest_path.read_bytes())

    # A caller's Python path, package index and selected tool store cannot cross
    # the authorized shared boundary, including during package builds.
    account = SimpleNamespace(pw_uid=395, pw_gid=395)
    with (patch.object(module, 'account', return_value=account), patch.object(
            module.subprocess, 'run', return_value=SimpleNamespace(stdout='ok')) as command,
            patch.dict(os.environ, {'UV_INDEX_URL': 'https://untrusted.invalid',
                                    'UV_TOOL_DIR': '/attacker', 'PYTHONPATH': '/attacker'})):
        assert module.uv('tool', 'list', capture=True) == 'ok'
        args, kwargs = command.call_args
        assert args[0][:3] == ['/usr/bin/uv', '--config-file', str(module.CONFIG)]
        assert kwargs['user'] == kwargs['group'] == 395
        assert kwargs['extra_groups'] == [] and kwargs['umask'] == 0o022
        assert kwargs['env']['UV_TOOL_DIR'] == '/var/lib/uv-tools/tools'
        assert 'UV_INDEX_URL' not in kwargs['env'] and 'PYTHONPATH' not in kwargs['env']

    with patch.object(module, 'uv', return_value='ctmodbus v0.6.0\n- ctmodbus\nrfcat v2.0.1\n- rfcat\n'):
        assert module.installed() == {'ctmodbus': '0.6.0', 'rfcat': '2.0.1'}
    with patch.object(module, 'uv', return_value='unexpected output'):
        try:
            module.installed()
        except RuntimeError:
            pass
        else:
            raise AssertionError('Unexpected inventory format accepted')

    # Existing tools retain their versions; a rerun installs only missing ones.
    with ExitStack() as stack:
        stack.enter_context(patch.object(module, 'BASE', work))
        stack.enter_context(patch.object(module, 'MANIFEST', manifest))
        stack.enter_context(patch.object(module, 'setup'))
        validate = stack.enter_context(patch.object(module, 'validate_tools'))
        inventory = stack.enter_context(patch.object(module, 'installed', return_value={'ctmodbus': '0.5'}))
        run = stack.enter_context(patch.object(module, 'uv', return_value=''))
        (work / 'tools').mkdir()
        module.manage('install')
        assert [call.args[-1] for call in run.call_args_list] == names[1:]
        assert all(call.args[:5] == ('tool', 'install', '--managed-python', '--python', '3.13')
                   for call in run.call_args_list)
        run.reset_mock()
        inventory.return_value = dict.fromkeys(names, '1.0')
        module.manage('install')
        run.assert_not_called()
        module.manage('update')
        assert [call.args for call in run.call_args_list] == [('python', 'upgrade'), ('tool', 'upgrade', '--all')]
        run.reset_mock()
        inventory.return_value = {}
        module.manage('update')
        run.assert_not_called()
        run.side_effect = subprocess.CalledProcessError(7, 'uv')
        try:
            module.manage('install')
        except subprocess.CalledProcessError:
            pass
        else:
            raise AssertionError('Failed installation hidden')
        assert run.call_count == 1
        # Metadata is produced separately, only after successful disk install.

    # No payload on an existing OS installation: updates must never seed tools.
    with patch.object(module, 'BASE', work / 'absent'), patch.object(module, 'MANIFEST', manifest), \
            patch.object(module, 'setup') as setup, patch.object(module, 'uv') as command:
        module.manage('update')
        setup.assert_not_called()
        command.assert_not_called()

    # Required exported commands cannot silently disappear behind a success.
    with patch.object(module, 'BASE', work), patch.object(module, 'uv'):
        try:
            module.validate_tools(selection, {'ctmodbus': '0.6.0'})
        except RuntimeError:
            pass
        else:
            raise AssertionError('Missing command accepted')

    # Shared-directory symlinks and writable-by-others stores are refused.
    target = work / 'target'
    target.mkdir()
    symlink = work / 'symlink'
    symlink.symlink_to(target)
    for path in (symlink, target):
        if path == target:
            target.chmod(0o777)
        try:
            module.directory(path, os.getuid(), 0o755)
        except RuntimeError:
            pass
        else:
            raise AssertionError('Unsafe directory accepted')

    # No per-user updates run as root. A shared failure still allows personal
    # attempts, but the combined result remains a failure.
    with patch.object(module.os, 'geteuid', return_value=0), patch.object(module.subprocess, 'run') as command:
        try:
            module.user_update()
        except RuntimeError:
            pass
        else:
            raise AssertionError('Personal tools updated as root')
        command.assert_not_called()
    with patch.object(module.os, 'geteuid', return_value=1000), patch.object(module.subprocess, 'run',
            side_effect=[SimpleNamespace(returncode=c) for c in (1, 0, 0)]) as command:
        try:
            module.user_update()
        except RuntimeError:
            pass
        else:
            raise AssertionError('Shared failure hidden')
        assert command.call_count == 3
        assert command.call_args_list[0].args[0] == ['/usr/bin/sudo', '-n', module.HELPER, 'update']

    # Supported shells include user directories even before first installation.
    env = dict(os.environ, HOME=str(work / 'new-home'), PATH='/usr/bin:/usr/sbin')
    bash_profile = ROOT / 'system_files/etc/profile.d/uv-tools.sh'
    fish_profile = ROOT / 'system_files/usr/share/fish/vendor_conf.d/uv-tools.fish'
    for shell, code in [('bash', f'. {bash_profile}; . {bash_profile}; echo "$PATH"'),
                        ('fish', f'source {fish_profile}; source {fish_profile}; string join : $PATH')]:
        output = subprocess.check_output([shell, '-c', code], env=env, text=True).strip()
        assert output.split(':')[:2] == [env['HOME'] + '/.local/bin', '/var/lib/uv-tools/bin'], output

    # Exercise Just's real import/override/alias resolution and the upstream
    # failure boundary, replacing only the commands that would update the host.
    upstream = work / 'update.just'
    upstream.write_text('alias upgrade := update\nupdate:\n'
                        '    #!/bin/bash\n    echo upstream >> "$CT_UPDATE_LOG"\n'
                        '    exit "${CT_UPDATE_STATUS:-0}"\n')
    libexec = work / 'libexec'
    libexec.mkdir()
    helper = libexec / 'uv-tools'
    helper.write_text('#!/bin/bash\nset -eu\n[[ "$1" == user-update ]]\n'
                      'echo uv >> "$CT_UPDATE_LOG"\n')
    helper.chmod(0o755)
    entry = work / 'entry.just'
    entry.write_text('set allow-duplicate-recipes := true\n'
                     'import "/usr/share/ublue-os/just/update.just"\n'
                     f'import "{ROOT}/system_files/usr/share/ublue-os/just/60-custom.just"\n'
                     + (ROOT / 'system_files/usr/share/ublue-os/just/uv-update.just').read_text())
    log = work / 'updates.log'
    wrapped = ['bwrap', '--ro-bind', '/', '/', '--bind', str(work), str(work),
               '--ro-bind', str(upstream), '/usr/share/ublue-os/just/update.just',
               '--ro-bind', str(libexec), '/usr/libexec',
               '/usr/bin/just', '--justfile', str(entry)]
    for recipe, status, expected in [('update', '0', ['upstream', 'uv']),
                                      ('upgrade', '0', ['upstream', 'uv']),
                                      ('update', '7', ['upstream'])]:
        log.write_text('')
        result = subprocess.run(wrapped + [recipe], text=True, capture_output=True,
                                env=dict(os.environ, XDG_RUNTIME_DIR=str(work), TMPDIR=str(work),
                                         CT_UPDATE_LOG=str(log), CT_UPDATE_STATUS=status))
        assert (result.returncode == 0) == (status == '0'), result.stderr
        assert log.read_text().splitlines() == expected, (recipe, log.read_text(), result.stderr)

for unit in ('uupd.service', 'uupd-manual.service'):
    dropin = ROOT / f'system_files/usr/lib/systemd/system/{unit}.d/60-uv-tools.conf'
    assert 'ExecStartPost=/usr/libexec/uv-tools update' in dropin.read_text()
assert not list((ROOT / 'system_files/usr/lib/systemd/system').glob('*uv*.timer'))
policy = (ROOT / 'system_files/etc/sudoers.d/uv-tools').read_text()
assert '%wheel ALL=(root) NOPASSWD:' in policy and '*' not in policy
assert 'is-enabled' not in (ROOT / 'system_files/usr/libexec/uv-tools').read_text()
print('PASS uv selection, additive installs, update scopes, privilege isolation, failures and shell precedence')
