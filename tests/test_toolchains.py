import pytest
import umbtest.tools
from umbtest.benchmarks import UmbBenchmark, Tester
from umbtest.tools import check_tools

"""
We initialize the tools we use in the tests. 
This can also be used to override the standard paths loaded by the configure tools call.
"""
umbtest.tools.configure_umbtools()
storm_cli = umbtest.tools.StormCLI(custom_identifier="Storm")
storm_cli_exact = umbtest.tools.StormCLI(extra_args = ["--exact"], custom_identifier="Storm (exact)")
prism_cli = umbtest.tools.PrismCLI(custom_identifier="Prism")
prism_cli_exact = umbtest.tools.PrismCLI(extra_args = ["-exact"], custom_identifier="Prism (exact)")
modest_cli = umbtest.tools.ModestCLI(custom_identifier="Modest")
umbi_py_umb = umbtest.tools.UmbPython("umb")
umbi_py_ats = umbtest.tools.UmbPython("ats")
check_tools(prism_cli, storm_cli, modest_cli)


def _toolname(val: umbtest.tools.UmbTool) -> str:
    """
    Helper function to provide better test names.
    :param val:
    :return:
    """
    return str(val.identifier)

def _toolpair(val: tuple[umbtest.tools.UmbTool, umbtest.tools.UmbTool]) -> str:
    return str(val[0].identifier)+"->"+str(val[1].identifier)

def _testername(val: Tester) -> str:
    """
    Helper function to provide better test names.
    :param val:
    :return:
    """
    return str(val.id)

def _benchmarkname(val: UmbBenchmark) -> str:
    """
    Helper function to provide better test names.s
    :param val:
    :return:
    """
    return str(val.id)


def load_and_read(tester, benchmark):
    """
    Tests a tool chain.

    :param tester:
    :param benchmark:
    :return:
    """
    print(f"Testing {tester} on {benchmark}...")
    results = tester.check_benchmark(benchmark)
    if results["loader"].anticipated_error:
        pytest.skip("Loader failed with an anticipated error")
    if results["loader"].not_supported:
        pytest.skip("Checker does not support these files.")
    assert results["loader"].exit_code == 0, "Loader should not crash."
    assert results["transformer"].exit_code == 0, "Transformer should not crash"
    if results["checker"].anticipated_error:
        pytest.xfail("Checker failed with an anticipated error.")
    if results["checker"].not_supported:
        pytest.skip("Checker does not support these files.")
    assert results["checker"].exit_code == 0, "Checker should not crash."
    # assert (
    #     results["loader"].model_info["states"]
    #     == results["checker"].model_info["states"]
    # )
    # assert (
    #     results["loader"].model_info["transitions"]
    #     == results["checker"].model_info["transitions"]
    # )

tools = [storm_cli, prism_cli, prism_cli_exact, storm_cli_exact]
@pytest.mark.parametrize("tool", tools, ids=_toolname, scope="class")
class TestTool:
    @pytest.mark.parametrize(
        "benchmark", umbtest.benchmarks.prism_files, ids=_benchmarkname
    )
    def test_write_read(self, tool, benchmark):
        tester = Tester()
        tester.set_chain(loader=tool, checker=tool)
        load_and_read(tester, benchmark)

    @pytest.mark.parametrize(
        "benchmark", umbtest.benchmarks.prism_files, ids=_benchmarkname
    )
    def test_write_umbi_read(self, tool, benchmark):
        tester = Tester()
        tester.set_chain(loader=tool, transformer=umbi_py_umb, checker=tool)
        load_and_read(tester, benchmark)

    @pytest.mark.parametrize(
        "benchmark", umbtest.benchmarks.prism_files, ids=_benchmarkname
    )
    @pytest.mark.skipif(True, reason="Not implemented yet.")
    def test_write_umbi_ats_read(self, tool, benchmark):
        tester = Tester()
        tester.set_chain(loader=tool, transformer=umbi_py_ats, checker=tool)
        load_and_read(tester, benchmark)

    @pytest.mark.parametrize(
        "benchmark", umbtest.benchmarks.prism_files, ids=_benchmarkname
    )
    def test_write_modest_read(self, tool, benchmark):
        tester = Tester()
        tester.set_chain(loader=tool, transformer=modest_cli, checker=tool)
        load_and_read(tester, benchmark)

toolpairs = [(prism_cli, modest_cli)]
@pytest.mark.parametrize("toolpair", toolpairs, ids=_toolpair, scope="class")
class TestAlignment:
    @pytest.mark.parametrize(
        "benchmark", umbtest.benchmarks.prism_files, ids=_benchmarkname
    )
    def test_write_read(self, toolpair, benchmark):
        tester = Tester()
        tester.set_chain(loader=toolpair[0], checker=toolpair[1])
        load_and_read(tester, benchmark)