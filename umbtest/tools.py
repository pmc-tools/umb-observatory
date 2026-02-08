import subprocess
import pathlib
import tomllib
import logging
import umbi
import umbi.io

logger = logging.getLogger(__name__)


#  LOGFILE Parsing
# Taken from and adapted from a project by Alex Bork and Tim Quatmann
def contains_any_of(log, msg):
    for m in msg:
        if m in log:
            return True
    return False


def try_parse(log, start, before, after, out_dict, out_key, out_type):
    pos1 = log.find(before, start)
    if pos1 >= 0:
        pos1 += len(before)
        pos2 = log.find(after, pos1)
        if pos2 >= 0:
            out_dict[out_key] = out_type(log[pos1:pos2])
            return pos2 + len(after)
    return start


def parse_logfile_storm(log, inv):
    unsupported_messages = [
        "ERROR (storm-cli.cpp:49): An exception caused Storm to terminate. The message of the exception is: NotSupportedException: Can not build interval model for the provided value type."
    ]  # add messages that indicate that the invocation is not supported
    inv.not_supported = contains_any_of(log, unsupported_messages)
    memout_messages = []  # add messages that indicate that the invocation is not supported
    memout_messages.append(
        "An unexpected exception occurred and caused Storm to terminate. The message of this exception is: std::bad_alloc"
    )
    memout_messages.append("Return code:\t-9")
    inv.memout = contains_any_of(log, memout_messages)
    known_error_messages = [
        "ERROR (SparseModelFromUmb.cpp:242): Only state observations are currently supported for POMDP models.",
        "ERROR (ValueEncoding.h:56): Some values are given as double intervals but a model with a non-interval type is requested.",
    ]  # add messages that indicate a "known" error, i.e., something that indicates that no warning should be printed
    inv.anticipated_error = contains_any_of(log, known_error_messages)
    if inv.not_supported or inv.anticipated_error:
        return
    if inv.exit_code not in [0, 1]:
        if not inv.timeout and not inv.memout:
            print("WARN: Unexpected return code(s): {}".format(inv["return-codes"]))

    errors = {}
    pos = 0
    i = 0
    while i <= 30:
        pos = try_parse(
            log,
            pos,
            "ERROR",
            "\n",
            errors,
            i,
            str,
        )
        if i not in errors:
            break
        i = i + 1
    inv.errors = tuple(errors.values())
    pos = 0
    inv.model_info = dict()

    pos = try_parse(
        log,
        pos,
        "Time for model construction: ",
        "s.",
        inv.model_info,
        "model-building-time",
        float,
    )

    pos = try_parse(log, pos, "States: \t", "\n", inv.model_info, "states", int)
    pos = try_parse(
        log, pos, "Transitions: \t", "\n", inv.model_info, "transitions", int
    )
    pos = try_parse(log, pos, "Choices: \t", "\n", inv.model_info, "choices", int)
    pos = try_parse(
        log, pos, "Observations: \t", "\n", inv.model_info, "observations", int
    )


class UmbTool:
    pass


def configure_umbtools():
    path = str(pathlib.Path(__file__).parent.parent / "tools.toml")
    with open(path, "rb") as config_file:
        paths = tomllib.load(config_file)
        PrismCLI.default_path = paths["tools"]["prism"]
        logger.warning(
            f"Prism is now configured with default location {PrismCLI.default_path}"
        )
        StormCLI.default_path = paths["tools"]["storm"]
        logger.warning(
            f"Storm is now configured with default location {StormCLI.default_path}"
        )
        ModestCLI.default_path = paths["tools"]["modest"]
        logger.warning(
            f"Modest is now configured with default location {ModestCLI.default_path}"
        )


def check_tools(*args):
    for tool in args:
        if not tool.check_process():
            raise RuntimeError(f"Tool '{tool.name}' failed")


class ReportedResults:
    def __init__(self):
        self.timeout = None
        self.memout = None
        self.not_supported = (
            False  # Error messages that say something is not supported.
        )
        self.anticipated_error = (
            False  # Can be used to declare an error message that "makes sense"
        )
        self.errors = tuple()
        self.exit_code = None
        self.model_info = None
        self.logfile = None

    def __str__(self):
        return f"ReportedResults[{self.logfile},{self.exit_code},{self.model_info},{self.timeout},{self.memout}]"

class PrismCLI(UmbTool):
    default_path = "/opt/prism"
    name = "PrismCLI"

    def __init__(self, location=None, extra_args=[], custom_identifier=None):
        """
        Create an instance of a prism cli tool.

        :param location: The location of the prism installation. If none, PrismCLI.default_path is used.
        """
        if location is None:
            self.prism_dir_path = __class__.default_path
        else:
            self.prism_dir_path = location
        self._extra_args = extra_args
        self._custom_identifier = custom_identifier

    @property
    def identifier(self):
        return self._custom_identifier if self._custom_identifier is not None else self.name + "(" + ",".join(
            self._extra_args
        ) + ")"

    def get_prism_path(self):
        path = pathlib.Path(self.prism_dir_path) / "prism/bin/prism"
        if not path.exists():
            raise RuntimeError(f"Prism executable not found at {path}")
        return path

    def get_prism_log_extract_script(self):
        path = pathlib.Path(self.prism_dir_path) / "prism/etc/scripts/prism-log-extract"
        if not path.exists():
            raise RuntimeError(f"Prism log script not found at {path}")
        return path

    def _make_invocation(self, args):
        return [self.get_prism_path().as_posix()] + args

    def _call_prism(self, log_file: pathlib.Path, args: list[str]):
        args += ["-test"] + self._extra_args
        reported_args = args
        if log_file is not None:
            args = ["-mainlog", log_file.as_posix()] + args
        print(" ".join(self._make_invocation(reported_args)))
        invocation = self._make_invocation(args)

        subprocess_result = subprocess.run(
            invocation,
            capture_output=True,
            text=True,
        )
        reported_result = ReportedResults()
        reported_result.timeout = None
        reported_result.memout = None
        reported_result.exit_code = subprocess_result.returncode
        reported_result.logfile = log_file
        print(log_file)
        if log_file is not None:
            with open(log_file, "r") as log:
                parse_logfile_prism(log.read(), reported_result)
            log_subprocess_result = subprocess.run(
                [
                    self.get_prism_log_extract_script().as_posix(),
                    "--fields=import_model_file,states,transitions",
                    reported_result.logfile,
                ],
                capture_output=True,
                text=True,
            )
            if log_subprocess_result.stderr != "":
                logger.warning(
                    "Issues parsing logfile:  " + log_subprocess_result.stderr
                )
            if log_subprocess_result.returncode != 0:
                logger.warning("Issues parsing logfile yielded error code")
            data = log_subprocess_result.stdout.split("\n")[1].split(",")
            try:
                reported_result.model_info = {
                    "states": int(data[1]),
                    "transitions": int(data[2]),
                }
            except ValueError:
                logger.warning(f"Issues parsing the model info data {data}")
                reported_result.model_info = {}

        return reported_result

    def prism_file_to_umb(
        self,
        prism_file: pathlib.Path,
        output_file: pathlib.Path,
        log_file: pathlib.Path,
    ):
        return self._call_prism(
            log_file,
            [prism_file.as_posix(), "-exportmodel", output_file.as_posix(), "-ex"],
        )

    def check_umb(self, umb_file: pathlib.Path, log_file: pathlib.Path, properties=[]):
        return self._call_prism(log_file, ["-importmodel", umb_file.as_posix()])

    def umb_to_umb(
        self,
        input_file: pathlib.Path,
        output_file: pathlib.Path,
        log_file: pathlib.Path,
    ):
        return self._call_prism(
            log_file,
            [
                "-importmodel",
                input_file.as_posix(),
                "-exportmodel",
                output_file.as_posix(),
            ],
        )

    def check_process(self):
        result = self._call_prism(None, ["-version"])
        return result.exit_code == 0


def parse_logfile_prism(log, inv):
    unsupported_messages = [
        "smg",
        "Error: Explicit engine: Intervals not supported for EXACT.",
        "Error: Unsupported model type TSG in UMB file.",
    ]  # add messages that indicate that the invocation is not supported
    inv.not_supported = contains_any_of(log, unsupported_messages)


class ModestCLI(UmbTool):
    name = "ModestCLI"
    default_path = "/opt/modest"
    empty_properties_file = (pathlib.Path(__file__).parent.parent) / "resources" / "empty.properties.txt"

    def __init__(self, location=None, extra_args=[], custom_identifier=None):
        if location is None:
            self._modest_path = __class__.default_path
        else:
            self._modest_path = location
        self._extra_args = extra_args
        self._custom_identifier = custom_identifier



    @property
    def identifier(self):
        return self._custom_identifier if self._custom_identifier is not None else self.name + "(" + ",".join(
            self._extra_args
        ) + ")"

    def get_modest_path(self):
        path = pathlib.Path(self._modest_path)
        if not path.exists():
            raise RuntimeError(f"Modest executable not found at {path}")
        return path

    def _call_mcsta(self, log_file, args):
        invocation = [self.get_modest_path().as_posix(), "mcsta", "-Y"] + args + self._extra_args
        # if log_file is not None:
        #     invocation = invocation +["-O", log_file.as_posix()]
        # else:
        #     print("WTF")
        print(" ".join(invocation))
        result = subprocess.run(
            invocation,
            capture_output=True,
            text=True,
        )
        reported_result = ReportedResults()
        reported_result.exit_code = result.returncode
        reported_result.timeout = False
        reported_result.memout = False
        reported_result.logfile = log_file
        if log_file is not None:
            with open(log_file, "r") as log:
                print(log.read())
                for line in result.stdout.split("\n"):
                    print(line)
                    if "error:" in line:
                        reported_result.exit_code = 1
                    if "UMB: error: Only deadlock-free MA, MDP, CTMC, DTMC, and LTS models are supported." in line:
                        reported_result.not_supported = True
        return reported_result

    def check_umb(self, umb_file: pathlib.Path, log_file: pathlib.Path, properties=[]):
        args = [umb_file.as_posix(), __class__.empty_properties_file.as_posix(), "-I", "UMB", "--exhaustive", "-D"]
        if properties is not None and len(properties) > 0:
            raise NotImplementedError("The use of properties is not implemented yet.")
        return self._call_mcsta(log_file, args)

    def umb_to_umb(
        self,
        input_file: pathlib.Path,
        output_file: pathlib.Path,
        log_file: pathlib.Path
    ):
        assert log_file is not None
        print(log_file)
        # Note that output_file must end with .umb for this to work.
        return self._call_mcsta(
            log_file=log_file,
            args=[
                input_file.as_posix(),
                __class__.empty_properties_file.as_posix(),
                "-I", "UMB",
                "--umb",
                output_file.as_posix(),
                "-D",
                "--exhaustive"
            ],
        )

    def check_process(self):
        result = self._call_mcsta(None, ["--version"])
        return result.exit_code == 0


class StormCLI(UmbTool):
    name = "StormCLI"
    default_path = "/opt/storm"

    def __init__(self, location=None, extra_args=[], custom_identifier=None):
        if location is None:
            self._storm_path = __class__.default_path
        else:
            self._storm_path = location
        self._extra_args = extra_args
        self._custom_identifier = custom_identifier

    @property
    def identifier(self):
        return self._custom_identifier if self._custom_identifier is not None else self.name + "(" + ",".join(
            self._extra_args
        ) + ")"

    def get_storm_path(self):
        path = pathlib.Path(self._storm_path)
        if not path.exists():
            raise RuntimeError(f"Storm executable not found at {path}")
        return path

    def _call_storm(self, log_file, args):
        invocation = [self.get_storm_path().as_posix()] + args + self._extra_args
        logger.info("Storm invocation: " + " ".join(invocation))
        result = subprocess.run(
            invocation,
            capture_output=True,
            text=True,
        )
        reported_result = ReportedResults()
        reported_result.exit_code = result.returncode
        reported_result.timeout = False
        reported_result.memout = False
        reported_result.logfile = log_file
        if log_file is not None:
            parse_logfile_storm(result.stdout, reported_result)
            with open(log_file, "w+") as log:
                log.write(result.stdout)
        return reported_result

    def prism_file_to_umb(
        self,
        prism_file: pathlib.Path,
        output_file: pathlib.Path,
        log_file: pathlib.Path,
    ):
        # Note that output_file must end with .umb for this to work.
        return self._call_storm(
            log_file,
            [
                "--prism",
                prism_file.as_posix(),
                "--exportbuild",
                output_file.as_posix(),
                "--buildfull",
                "-pc",
            ],
        )

    def check_umb(self, umb_file: pathlib.Path, log_file=pathlib.Path, properties=[]):
        args = ["--explicit-umb", umb_file.as_posix()]
        if properties is not None and len(properties) > 0:
            args += ["--prop", ";".join(properties)]
        return self._call_storm(log_file, args)

    def umb_to_umb(
        self,
        input_file: pathlib.Path,
        output_file: pathlib.Path,
        log_file: pathlib.Path
    ):
        # Note that output_file must end with .umb for this to work.
        return self._call_storm(
            log_file,
            [
                "--explicit-umb",
                input_file.as_posix(),
                "--exportbuild",
                output_file.as_posix(),
            ],
        )

    def check_process(self):
        result = self._call_storm(None, ["--version"])
        return result.exit_code == 0


class UmbPython(UmbTool):
    name = "umbilib"

    def __init__(self, mode="umb"):
        """
        :param mode: Either ats or umb
        """
        self._mode = mode

    def check_process(self):
        return True

    def umb_to_umb(
        self,
        input_file: pathlib.Path,
        output_file: pathlib.Path,
        log_file: pathlib.Path
    ):
        if self._mode == "ats":
            ats = umbi.io.read_ats(input_file)
            umbi.io.write_ats(ats, output_file)
            reported_results = ReportedResults()
            reported_results.model_info = {
                "states": ats.num_states,
                "transitions": ats.num_branches,
            }
            return reported_results
        elif self._mode == "umb":
            umb = umbi.io.read_umb(input_file)
            umbi.io.write_umb(umb, output_file)
            reported_results = ReportedResults()
            reported_results.model_info = {
                "states": umb.index.transition_system.num_states,
                "transitions": umb.index.transition_system.num_branches,
            }
            return reported_results
        else:
            raise RuntimeError("Unknown mode")
