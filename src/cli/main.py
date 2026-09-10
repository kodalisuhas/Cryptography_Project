"""CLI entry point: argument parsing, command dispatch, and error mapping.

Exit codes
----------
0 - success (including "Cancelled" from KeyboardInterrupt)
1 - user-input / runtime failure (ValueError, TypeError, KeyError, etc.)
2 - usage / argument failure (argparse-built-in)

No new dependencies. No crypto logic.
"""

import matplotlib
matplotlib.use("Agg")

import sys
import traceback

from src.cli.argument_parser import create_parser, validate_persistence_args
from src.cli import commands
from src.cli import menu

EXIT_SUCCESS = 0
EXIT_RUNTIME = 1  # user-input or runtime failure
EXIT_USAGE = 2    # CLI usage / argument failure


def _dispatch(args) -> None:
    """Route to the appropriate command handler."""
    if args.command == "menu":
        menu.run_menu(args)
        return

    handlers = {
        "encrypt": commands.run_encrypt,
        "decrypt": commands.run_decrypt,
        "benchmark": commands.run_benchmark,
        "security": commands.run_security,
    }
    handler = handlers[args.command]
    handler(args)


def main(argv=None) -> int:
    """Parse arguments, dispatch to the selected command, and map exceptions.

    Parameters
    ----------
    argv : list[str] | None
        Arguments to parse. ``None`` reads ``sys.argv[1:]`` (the default
        behaviour of ``argparse``).
    """
    parser = create_parser()
    args = parser.parse_args(argv)
    validate_persistence_args(parser, args)

    try:
        _dispatch(args)
    except KeyboardInterrupt:
        print("Cancelled")
        return EXIT_SUCCESS
    except FileExistsError as exc:
        print(f"Error: {exc}")
        return EXIT_RUNTIME
    except OSError as exc:
        print(f"Error: {exc}")
        return EXIT_RUNTIME
    except (ValueError, TypeError, KeyError) as exc:
        print(f"Error: {exc}")
        return EXIT_RUNTIME
    except Exception as exc:  # unexpected — never swallowed
        if getattr(args, "verbose", False):
            traceback.print_exc()
        else:
            print(f"Unexpected error: {exc}")
        return EXIT_RUNTIME

    return EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())