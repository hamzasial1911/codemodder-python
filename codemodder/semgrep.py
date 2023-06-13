import json
import subprocess
import itertools
from tempfile import NamedTemporaryFile
from typing import List
from pathlib import Path


def run(project_root: Path, yaml_files: List[Path]):
    """
    Runs Semgrep and outputs the result in a Sarif TemporaryFile.
    """
    # TODO Look into running semgrep from its module later
    with NamedTemporaryFile(prefix="semgrep", suffix=".sarif") as temp_sarif_file:
        command = [
            "semgrep",
            "scan",
            "--no-error",
            "--dataflow-traces",
            "--sarif",
            "-o",
            temp_sarif_file.name,
        ]
        command.extend(
            itertools.chain.from_iterable(
                map(lambda f: ["--config", str(f)], yaml_files)
            )
        )
        command.append(str(project_root))
        print(f"Executing semgrep with: {command}")
        subprocess.run(" ".join(command), shell=True, check=True)
        results = results_by_rule_id(temp_sarif_file)
        return results


def find_all_yaml_files(codemods) -> list[Path]:
    """
    Finds all yaml files associated with the given codemods.
    """
    # TODO for now, just pass everything until we figure out semgrep codemods
    return list((Path("codemodder") / "codemods" / "semgrep").iterdir())


def results_by_rule_id(sarif_file):
    """
    Extract all the results of a sarif file and organize them by id.
    """
    # TODO ruleId could be indirectly pointed by the rule field
    # TODO test with webgoat sarif
    with open(sarif_file.name, "r", encoding="utf-8") as f:
        data = json.load(f)
    results = [result for sarif_run in data["runs"] for result in sarif_run["results"]]
    return {r["ruleId"]: r for r in results}


def get_results():
    """
    Extract the results of a semgrep run.
    """
    with open("sarif.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    return data["runs"][0]["results"]
