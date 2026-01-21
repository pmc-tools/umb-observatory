import tempfile
from typing import List
from umbtest.tools import UmbTool, ReportedResults, PrismCLI
from pathlib import Path
from collections import deque


class UmbBenchmark:
    def __init__(self, location: Path, properties=None, is_prism_file=True):
        self.location = location
        self.properties = properties
        self.is_prism_file = is_prism_file

    def __str__(self):
        return str(self.__dict__)

    @property
    def id(self) -> Path:
        return Path("/".join(self.location.parts[-2:]))


_prism_files_path = Path(__file__).parent / "../resources/prism-files/"
prism_files = [UmbBenchmark(p) for p in _prism_files_path.glob("*.nm")]
few_files = prism_files[5:]

standard = [
    UmbBenchmark(
        Path(PrismCLI.default_path) / "prism-examples/simple/dice/dice.pm", None
    )
]


class Tester:
    def __init__(self, id=None):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._loader = None
        self._checker = None
        self._transformer = None
        self._id = id

    def _tmpumbfile(self):
        return tempfile.NamedTemporaryFile(dir=self._tmpdir.name, suffix=".umb")

    def _tmplogfile(self):
        return tempfile.NamedTemporaryFile(dir=self._tmpdir.name, suffix=".log")

    def set_chain(
        self, loader: UmbTool, checker: UmbTool, transformer: None | UmbTool = None
    ) -> None:
        self._loader = loader
        self._transformer = transformer
        self._checker = checker

    @property
    def id(self):
        if self._id is None:
            result = f"l={self._loader.name}"
            if self._transformer is not None:
                result += f"_t={self._transformer.name}"
            else:
                result += "_t=None"
            result += f"_c={self._checker.name}"
            return result
        else:
            return self._id

    def __str__(self):
        result = f"load with {self._loader.name}"
        if self._transformer is not None:
            result += f" transform with {self._transformer.name}"
        result += f" check with {self._checker.name}"
        return result

    def check_benchmark(self, benchmark):
        if benchmark.is_prism_file:
            return self.check_prism_file(benchmark.location, benchmark.properties)
        else:
            raise NotImplementedError("We currently only support prism files")

    def check_prism_file(
        self, prism_file: Path, properties: List[str]
    ) -> dict[str, ReportedResults]:
        result = dict()
        if self._loader is None or self._checker is None:
            raise RuntimeError("You must first set the tool chain, using set_chain()")
        tmpfile_in = self._tmpumbfile()
        tmpfile_in_path = Path(tmpfile_in.name)
        log_file_to_umb = self._tmplogfile()
        result["loader"] = self._loader.prism_file_to_umb(
            prism_file, tmpfile_in_path, log_file=Path(log_file_to_umb.name)
        )
        result["checker"] = None
        result["transformer"] = None
        if result["loader"].error_code != 0:
            with open(result["loader"].logfile, "r") as f:
                print(f.read())
            if result["loader"].not_supported:
                return result
            if not result["loader"].anticipated_error:
                raise RuntimeError(
                    f"Unexpected exception during loading by {self._loader.name}"
                )
            else:
                return result
        if not tmpfile_in_path.exists() or tmpfile_in_path.stat().st_size == 0:
            d = None
            with open(result["loader"].logfile, "r") as f:
                d = deque(f.readlines(), maxlen=3)
            with open(result["loader"].logfile, "r") as f:
                print(f.read())
            raise RuntimeError(
                f"{self._loader.name} did not yield a UMB file (but status=0). Last log lines are {" ".join([d[i].rstrip('\n') for i in range(len(d)) if d[i]])} "
            )
        if self._transformer:
            tmpfile_out = self._tmpumbfile()
            try:
                result["transformer"] = self._transformer.umb_to_umb(
                    tmpfile_in_path,
                    Path(tmpfile_out.name),
                    log_file=Path(self._tmplogfile().name),
                )
            except Exception as e:
                raise RuntimeError(f"{self._transformer.name} raised {type(e)}:{e}!")
        else:
            tmpfile_out = tmpfile_in
        result["checker"] = self._checker.check_umb(
            Path(tmpfile_out.name),
            log_file=Path(self._tmplogfile().name),
            properties=properties,
        )
        if result["checker"].error_code != 0:
            with open(result["checker"].logfile, "r") as f:
                print(f.read())
            if result["checker"].anticipated_error or result["checker"].not_supported:
                return result
            if result["checker"].errors is None:
                raise RuntimeError("Something unexpected went wrong.")

        return result
