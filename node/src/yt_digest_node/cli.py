"""Command line: `yt-digest-node transcript <video_id> [--langs fr,en] [--request-id ID]`."""

import argparse
import re
import sys
from collections.abc import Sequence

from yt_digest_node.extract import make_extractor
from yt_digest_node.log import emit
from yt_digest_node.pipeline import Config, package_version, run

_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


def _video_id(value: str) -> str:
    if not _VIDEO_ID.fullmatch(value):
        raise argparse.ArgumentTypeError(f"invalid video id: {value!r}")
    return value


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="yt-digest-node")
    commands = parser.add_subparsers(dest="command", required=True)
    transcript = commands.add_parser("transcript", help="print the transcript result of a video")
    transcript.add_argument("video_id", type=_video_id)
    transcript.add_argument("--langs", help="language order, e.g. fr,en")
    transcript.add_argument("--request-id")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)  # exits 2 on a bad argument
    try:
        config = Config.from_env(args.langs)
    except ValueError as error:
        parser.error(str(error))
    try:
        extractor = make_extractor()
    except ValueError as error:  # FAKE_YTDLP_DIR missing with the fake extractor
        parser.error(str(error))
    emit("service.started", request_id=args.request_id, attrs={"version": package_version()})
    result = run(args.video_id, config, extractor, args.request_id)
    sys.stdout.write(result.model_dump_json() + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
