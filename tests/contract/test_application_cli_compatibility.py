from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from vali.application.collection import (
    run_kalshi_command,
    run_trends_command,
)
from vali.application.commands import build_parser, main as application_main
from vali.application.reporting import run_report_command
from vali.application.research import (
    run_research_command,
    run_sample_data_command,
)
from vali.application.validation import run_validation_command
from vali.cli import _parser as legacy_parser
from vali.cli import main as legacy_main
from vali.sample import make_synthetic_dataset


def subcommands(parser):
    action = next(
        action
        for action in parser._actions
        if action.__class__.__name__ == "_SubParsersAction"
    )
    return action.choices


def option_strings(parser):
    return {
        option
        for action in parser._actions
        for option in action.option_strings
    }


def capture(function, arguments):
    output = StringIO()
    with redirect_stdout(output):
        function(arguments)
    return output.getvalue()


class ApplicationCliCompatibilityTests(unittest.TestCase):
    def test_old_and_new_application_imports_are_available(self):
        for function in (
            legacy_main,
            application_main,
            build_parser,
            run_research_command,
            run_sample_data_command,
            run_kalshi_command,
            run_trends_command,
            run_report_command,
            run_validation_command,
        ):
            self.assertTrue(callable(function))

    def test_command_names_help_and_arguments_are_unchanged(self):
        legacy = legacy_parser()
        extracted = build_parser()
        self.assertEqual(legacy.format_help(), extracted.format_help())

        legacy_commands = subcommands(legacy)
        commands = subcommands(extracted)
        expected_commands = {
            "validate",
            "signal",
            "backtest",
            "confirmation-panel",
            "report",
            "sample-data",
            "kalshi",
            "trends",
        }
        self.assertEqual(set(commands), expected_commands)
        self.assertEqual(set(legacy_commands), expected_commands)
        for command in expected_commands:
            self.assertEqual(
                legacy_commands[command].format_help(),
                commands[command].format_help(),
            )

        self.assertEqual(
            option_strings(commands["validate"]),
            {"-h", "--help", "--config"},
        )
        self.assertEqual(
            option_strings(commands["signal"]),
            {"-h", "--help", "--config", "--out"},
        )
        self.assertEqual(
            option_strings(commands["backtest"]),
            {"-h", "--help", "--config", "--out"},
        )
        self.assertEqual(
            option_strings(commands["confirmation-panel"]),
            {"-h", "--help", "--config", "--out", "--grid"},
        )
        self.assertEqual(
            option_strings(commands["report"]),
            {"-h", "--help", "--run-dir"},
        )

        kalshi_commands = subcommands(commands["kalshi"])
        trends_commands = subcommands(commands["trends"])
        self.assertEqual(
            set(kalshi_commands), {"discover", "backfill", "snapshot"}
        )
        self.assertEqual(
            set(trends_commands), {"plan", "backfill", "collect", "status"}
        )

    def test_legacy_and_application_parser_namespaces_are_identical(self):
        cases = [
            ["validate", "--config", "config.toml"],
            ["signal", "--config", "config.toml", "--out", "run"],
            ["backtest", "--config", "config.toml", "--out", "run"],
            [
                "confirmation-panel",
                "--config",
                "config.toml",
                "--out",
                "run",
                "--grid",
                "1/1,2/2",
            ],
            ["report", "--run-dir", "run"],
            ["sample-data", "--out", "data", "--seed", "7", "--events", "3"],
            ["kalshi", "discover", "--out", "kalshi"],
            [
                "kalshi",
                "backfill",
                "--out",
                "kalshi",
                "--min-events",
                "20",
                "--no-trades",
                "--candle-interval",
                "1440",
            ],
            ["kalshi", "snapshot", "--out", "kalshi", "--depth-band", "0.02"],
            ["trends", "plan", "--out", "trends", "--as-of", "2026-06-23", "--days", "30"],
            ["trends", "status", "--out", "trends"],
            [
                "trends",
                "backfill",
                "--out",
                "trends",
                "--fixture",
                "fixture.json",
                "--as-of",
                "2026-06-23",
            ],
            [
                "trends",
                "collect",
                "--out",
                "trends",
                "--fixture",
                "fixture.json",
                "--lookback-days",
                "5",
            ],
        ]
        for arguments in cases:
            with self.subTest(arguments=arguments):
                self.assertEqual(
                    vars(legacy_parser().parse_args(arguments)),
                    vars(build_parser().parse_args(arguments)),
                )

    def test_validate_and_signal_outputs_remain_compatible(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = make_synthetic_dataset(
                root / "data", seed=19, event_count=3
            )
            arguments = ["validate", "--config", str(config)]
            self.assertEqual(
                capture(legacy_main, arguments),
                capture(application_main, arguments),
            )

            legacy_output = capture(
                legacy_main,
                [
                    "signal",
                    "--config",
                    str(config),
                    "--out",
                    str(root / "legacy"),
                ],
            )
            application_output = capture(
                application_main,
                [
                    "signal",
                    "--config",
                    str(config),
                    "--out",
                    str(root / "application"),
                ],
            )
            legacy_payload = json.loads(legacy_output)
            application_payload = json.loads(application_output)
            self.assertEqual(
                legacy_payload["signal_rows"],
                application_payload["signal_rows"],
            )
            self.assertEqual(
                {path.name for path in (root / "legacy").iterdir()},
                {path.name for path in (root / "application").iterdir()},
            )

    def test_report_command_output_and_delegation_are_unchanged(self):
        arguments = ["report", "--run-dir", "run"]
        expected_report = Path("run").resolve() / "report.html"
        with patch(
            "vali.application.reporting.rebuild_report",
            return_value=expected_report,
        ) as rebuild:
            legacy_output = capture(legacy_main, arguments)
            application_output = capture(application_main, arguments)
        self.assertEqual(legacy_output, application_output)
        self.assertEqual(
            json.loads(application_output), {"report": str(expected_report)}
        )
        self.assertEqual(rebuild.call_count, 2)

    def test_python_module_entrypoint_remains_compatible(self):
        completed = subprocess.run(
            [sys.executable, "-m", "vali", "--help"],
            cwd=Path(__file__).parents[2],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stderr, "")
        self.assertIn("Offline VALI research pipeline", completed.stdout)
        self.assertIn("confirmation-panel", completed.stdout)

    def test_no_trading_credentials_or_p_flow_cli_surface_exists(self):
        parser = build_parser()
        text = parser.format_help().lower()
        for command in subcommands(parser).values():
            text += command.format_help().lower()
            try:
                nested = subcommands(command)
            except StopIteration:
                nested = {}
            for child in nested.values():
                text += child.format_help().lower()

        forbidden = (
            "api-key",
            "cancel-order",
            "credentials",
            "live-trading",
            "order-submit",
            "p_flow",
            "place-order",
            "private-input",
            "submit-order",
        )
        for value in forbidden:
            self.assertNotIn(value, text)


if __name__ == "__main__":
    unittest.main()
