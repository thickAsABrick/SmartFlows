# BSD 2-Clause License
#
# Copyright (c) 2021-2023, Hewlett Packard Enterprise
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


from pathlib import Path

import os
from re import A, L
import pytest
import shutil
import typing as t

from smartsim._core.config.config import Config
from smartsim.error import SSConfigError


def test_all_config_defaults():
    config = Config()
    assert Path(config.redisai).is_file()
    assert Path(config.database_exe).is_file()
    assert Path(config.database_cli).is_file()
    assert Path(config.database_conf).is_file()

    # these will be changed so we will just run them
    assert config.log_level
    assert config.jm_interval

    config.test_interface
    config.test_launcher
    config.test_account
    config.test_device


def get_redisai_env(rai_path: t.Optional[str], lib_path: t.Optional[str]) -> t.Dict[str, str]:
    """Convenience method to create a set of environment variables 
    that include RedisAI-specific variables
    :param rai_path: The path to the RedisAI library
    :type: str (optional)
    :param lib_path: The path to the SMARTSIM_DEP_INSTALL_PATH
    :type: str (optional)
    :return: A dictionary containing an updated set of environment variables
    """
    env = os.environ.copy()
    if rai_path is not None:
        env["RAI_PATH"] = rai_path
    else:
        env.pop("RAI_PATH", None)
    
    if lib_path is not None:
        env["SMARTSIM_DEP_INSTALL_PATH"] = lib_path
    else:
        env.pop("SMARTSIM_DEP_INSTALL_PATH", None)
    
    return env


def test_redisai_invalid_rai_path(fileutils, monkeypatch):
    """An invalid RAI_PATH and valid SMARTSIM_DEP_INSTALL_PATH should fail"""
    test_dir = fileutils.make_test_dir()
    rai_file_path = os.path.join(test_dir, "lib", "mock-redisai.so")
    _ = fileutils.make_test_file("redisai.so", "lib")

    env = get_redisai_env(rai_file_path, test_dir)
    monkeypatch.setattr(os, "environ", env)

    config = Config()

    # Fail when no file exists @ RAI_PATH
    with pytest.raises(SSConfigError) as ex:
        _ = config.redisai

    assert 'RedisAI dependency not found' in ex.value.args[0]


def test_redisai_valid_rai_path(fileutils, monkeypatch):
    """A valid RAI_PATH should override valid SMARTSIM_DEP_INSTALL_PATH and succeed"""
    test_dir = fileutils.make_test_dir()
    rai_file_path = fileutils.make_test_file("mock-redisai.so", "lib")
    _ = fileutils.make_test_file("redisai.so", "deps")

    env = get_redisai_env(rai_file_path, test_dir)
    monkeypatch.setattr(os, "environ", env)

    config = Config()
    assert config.redisai
    assert Path(config.redisai).is_file()
    assert config.redisai == rai_file_path


def test_redisai_invalid_lib_path(fileutils, monkeypatch):
    """Invalid RAI_PATH and invalid SMARTSIM_DEP_INSTALL_PATH should fail"""
    test_dir = fileutils.make_test_dir()
    rai_file_path = f"{test_dir}/railib/redisai.so"

    env = get_redisai_env(rai_file_path, test_dir)
    monkeypatch.setattr(os, "environ", env)
    
    config = Config()
    # Fail when no files exist @ either location
    with pytest.raises(SSConfigError) as ex:
        _ = config.redisai

    assert 'RedisAI dependency not found' in ex.value.args[0]


def test_redisai_valid_lib_path(fileutils, monkeypatch):
    """Valid RAI_PATH and invalid SMARTSIM_DEP_INSTALL_PATH should succeed"""
    test_dir = fileutils.make_test_dir()
    rai_file_path = fileutils.make_test_file("mock-redisai.so", "lib")

    env = get_redisai_env(rai_file_path, test_dir)
    monkeypatch.setattr(os, "environ", env)
    
    config = Config()
    assert config.redisai
    assert Path(config.redisai).is_file()
    assert config.redisai == rai_file_path


def test_redisai_valid_lib_path_null_rai(fileutils, monkeypatch):
    """Missing RAI_PATH and valid SMARTSIM_DEP_INSTALL_PATH should succeed"""
    test_dir = fileutils.make_test_dir()
    rai_file_path: t.Optional[str] = None
    lib_file_path = fileutils.make_test_file("redisai.so", "lib")

    env = get_redisai_env(rai_file_path, test_dir)
    monkeypatch.setattr(os, "environ", env)
    
    config = Config()
    assert config.redisai
    assert Path(config.redisai).is_file()
    assert config.redisai == lib_file_path


def test_redis_conf():
    config = Config()
    assert Path(config.database_conf).is_file()
    assert isinstance(config.database_conf, str)

    os.environ["REDIS_CONF"] = "not/a/path"
    config = Config()
    with pytest.raises(SSConfigError):
        config.database_conf
    os.environ.pop("REDIS_CONF")


def test_redis_exe():
    config = Config()
    assert Path(config.database_exe).is_file()
    assert isinstance(config.database_exe, str)

    os.environ["REDIS_PATH"] = "not/a/path"
    config = Config()
    with pytest.raises(SSConfigError):
        config.database_exe
    os.environ.pop("REDIS_PATH")


def test_redis_cli():
    config = Config()
    assert Path(config.redisai).is_file()
    assert isinstance(config.redisai, str)

    os.environ["REDIS_CLI_PATH"] = "not/a/path"
    config = Config()
    with pytest.raises(SSConfigError):
        config.database_cli
    os.environ.pop("REDIS_CLI_PATH")
