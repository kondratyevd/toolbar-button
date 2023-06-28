"""
Export a Conda environment with --from-history, but also append
Pip-installed dependencies, as well as locally installed pip packages.

The code is based on https://gist.github.com/gwerbin/dab3cf5f8db07611c6e0aeec177916d8

MIT License:
    
    Copyright (c) 2021 @gwerbin

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.
"""
import re
import subprocess
import sys

import yaml


def export_env(history_only=False, include_builds=False):
    """ Capture `conda env export` output """
    cmd = ['conda', 'env', 'export']
    if history_only:
        cmd.append('--from-history')
        if include_builds:
            raise ValueError('Cannot include build versions with "from history" mode')
    if not include_builds:
        cmd.append('--no-builds')
    cp = subprocess.run(cmd, stdout=subprocess.PIPE)
    try:
        cp.check_returncode()
    except:
        raise
    else:
        return yaml.safe_load(cp.stdout)


def export_pip_local():
    """ Export only packages installed locally with pip """
    cmd = ["pip", "freeze", "--user"]
    cp = subprocess.run(cmd, stdout=subprocess.PIPE)
    try:
        cp.check_returncode()
    except:
        raise
    else:
        return cp.stdout.decode().splitlines()


def _is_history_dep(d, history_deps):
    if not isinstance(d, str):
        return False
    d_prefix = re.sub(r'=.*', '', d)
    return d_prefix in history_deps


def _get_pip_deps(full_deps):
    for dep in full_deps:
        if isinstance(dep, dict) and 'pip' in dep:
            return dep


def override_with_local(target, local_pkgs, eq="=="):
    overlapping = []
    for idep, dep in enumerate(target):
        pkg_name = dep.split("=")[0]
        pkg_version = dep.split("=")[-1]
        if pkg_name in local_pkgs.keys():
            overlapping.append(pkg_name)
            local_pkg_ver = local_pkgs[pkg_name]
            if pkg_version != local_pkg_ver:
                target[idep] = f"{pkg_name}{eq}{local_pkg_ver}"
    return overlapping


def _combine_env_data(env_data_full, env_data_hist, pip_local=None):
    deps_full = env_data_full['dependencies']
    deps_hist = env_data_hist['dependencies']
    deps = [dep for dep in deps_full if _is_history_dep(dep, deps_hist)]

    python_specified = any([d.split("=")[0]=="python" for d in deps])
    if not python_specified:
        py_version = sys.version.split(" ")[0]
        deps.append(f"python={py_version}")

    pip_deps = _get_pip_deps(deps_full)

    if pip_local:
        local_pkgs = {p.split("=")[0]:p.split("=")[-1] for p in pip_local}
        overlapping_with_conda = []
        overlapping_with_pip = []

        if deps:
            overlapping_with_conda = override_with_local(deps, local_pkgs, "=")
        if pip_deps:
            overlapping_with_pip = override_with_local(pip_deps["pip"], local_pkgs, "==")

        extra_pkgs = {
            k:v for k,v in local_pkgs.items()\
            if (k not in overlapping_with_pip) and (k not in overlapping_with_conda)
        }
        if extra_pkgs and (not pip_deps):
            pip_deps = {"pip": []}
        for pkg, ver in extra_pkgs.items():
            pip_deps["pip"].append(f"{pkg}=={ver}")

    env_data = {}
    env_data['channels'] = env_data_full['channels']
    env_data['dependencies'] = deps
    if pip_deps:
        env_data['dependencies'].append(pip_deps)

    return env_data


def main():
    env_data_full = export_env()
    env_data_hist = export_env(history_only=True)
    pip_local = export_pip_local()
    env_data = _combine_env_data(env_data_full, env_data_hist, pip_local=pip_local)

    yaml.dump(env_data, sys.stdout)


if __name__ == '__main__':
    main()