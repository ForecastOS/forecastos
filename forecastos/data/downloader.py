from contextlib import contextmanager
from pathlib import Path
from typing import Generator
import requests

TIMEOUT_SEC = 30
CHUNK_BYTES = 1 << 20


class FileDownloader:
    """Download URLs into `data_dir`, reusing any file already there.

    Args:
        data_dir: directory downloads land in; created if it does not exist.
        cleanup: whether `fetch` deletes the file once the caller is done with
            it. A capture can be tens of GB, so re-fetching is expensive - pass
            False unless the file is genuinely disposable.
        headers: sent with every request. Some hosts - SEC among them - reject
            an unidentified client outright, so the caller supplies whatever
            that host expects.
    """

    def __init__(self, data_dir: str, cleanup: bool, headers: dict = None):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cleanup = cleanup
        self.headers = headers

    def download(self, url: str, filename: str) -> Path:
        """Return the local path for `url`, downloading it only if missing.

        Bytes land in a sibling `.part` file that is renamed only once the transfer
        completes, so an interrupted run never leaves a truncated file behind for the
        next run to mistake for a finished download.
        """
        out_path = self.data_dir / filename

        if out_path.exists():
            print(f"already downloaded: {out_path}")
            return out_path

        part = out_path.with_name(out_path.name + ".part")
        print(f"downloading: {url}\nsaving to:   {out_path}")

        try:
            self._stream(url, part)
            part.replace(out_path)
        except BaseException:
            # Also catches KeyboardInterrupt: the `exists()` check above would
            # read a half-written file as a finished download.
            part.unlink(missing_ok=True)
            raise

        print(f"\nsaved {out_path} ({_fmt(out_path.stat().st_size)})")
        return out_path

    def _stream(self, url: str, path: Path) -> None:
        """Write the response body to `path` a chunk at a time."""
        with requests.get(
            url, stream=True, timeout=TIMEOUT_SEC, headers=self.headers
        ) as response:
            response.raise_for_status()
            total = int(response.headers.get("content-length", 0))
            done = 0

            with open(path, "wb") as f:
                for chunk in response.iter_content(chunk_size=CHUNK_BYTES):
                    f.write(chunk)
                    done += len(chunk)

                    # A capture can run to tens of GB, so show progress when the
                    # server told us how much to expect.
                    if total:
                        print(f"\r  {_fmt(done)} / {_fmt(total)}"
                              f" ({done / total:4.0%})", end="")

    @contextmanager
    def fetch(self, url: str, filename: str) -> Generator[Path, None, None]:
        """Yield the local path for `url`, deleting it afterwards if `self.cleanup`.

        Only a file this call downloaded is deleted. One that was already on disk
        is the caller's, not ours to remove, whatever `cleanup` says.
        """
        ours = not (self.data_dir / filename).exists()
        path = self.download(url, filename)
        try:
            yield path
        finally:
            if self.cleanup and ours:
                print(f"removing {path}")
                path.unlink(missing_ok=True)


def _fmt(n: float) -> str:
    """Bytes in the largest unit that keeps the number under 1024."""
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"
