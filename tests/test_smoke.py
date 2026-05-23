# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from typer.testing import CliRunner

from programbench.cli.main import app

runner = CliRunner()


def test_eval_help() -> None:
    result = runner.invoke(app, ["eval", "--help"])
    assert result.exit_code == 0
    assert "sources" in result.output.lower()
