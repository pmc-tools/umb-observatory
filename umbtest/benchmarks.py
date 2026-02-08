import tempfile
from typing import List
from umbtest.tools import UmbTool, ReportedResults, PrismCLI
from pathlib import Path
from collections import deque
import tomllib
import pathlib
import logging

logger = logging.getLogger(__name__)

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

standard = [
    UmbBenchmark(
        Path(PrismCLI.default_path) / "prism-examples/simple/dice/dice.pm", None
    )
]

class Tester:
    testdir = tempfile.TemporaryDirectory()
    delete_files_default = True

    def __init__(self, id=None, delete_files=None):
        self._tmpdir = __class__.testdir
        self._loader = None
        self._checker = None
        self._transformer = None
        self._id = id
        if delete_files is None:
            self._delete_files = __class__.delete_files_default
        else:
            self._delete_files = delete_files

    def _get_tmp_dir_name(self):
        if isinstance(self._tmpdir, str):
            return self._tmpdir
        return self._tmpdir.name

    def _tmpumbfile(self):
        return tempfile.NamedTemporaryFile(dir=self._get_tmp_dir_name(), suffix=".umb", delete=self._delete_files, delete_on_close=self._delete_files)

    def _tmplogfile(self):
        return tempfile.NamedTemporaryFile(dir=self._get_tmp_dir_name(), suffix=".log", delete=self._delete_files, delete_on_close=self._delete_files)

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
        if result["loader"].exit_code != 0:
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
                if result["transformer"].exit_code != 0:
                    return result
            except Exception as e:
                raise RuntimeError(f"{self._transformer.name} raised {type(e)}:{e}!")
        else:
            tmpfile_out = tmpfile_in
        result["checker"] = self._checker.check_umb(
            Path(tmpfile_out.name),
            log_file=Path(self._tmplogfile().name),
            properties=properties,
        )
        if result["checker"].exit_code != 0:
            with open(result["checker"].logfile, "r") as f:
                print(f.read())
            if result["checker"].anticipated_error or result["checker"].not_supported:
                return result
            if result["checker"].errors is None:
                raise RuntimeError("Something unexpected went wrong.")

        return result


def configure_tester():
    path = str(pathlib.Path(__file__).parent.parent / "tools.toml")
    with open(path, "rb") as config_file:
        paths = tomllib.load(config_file)
        if "byproducts" in paths:
            if "tmpfolder" in paths["byproducts"]:
                Tester.testdir = paths["byproducts"]["tmpfolder"]
                logger.warning(
                    f"Temporary files are now stored at {Tester.testdir}"
                )
            if "cleanup" in paths["byproducts"]:
                Tester.delete_files_default = paths["byproducts"]["cleanup"]
                logger.warning(
                    f"Temporary files cleanup is set to {Tester.delete_files_default}"
                )

configure_tester()
