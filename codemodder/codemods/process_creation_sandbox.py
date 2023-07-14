import libcst as cst
from libcst import Arg, Name
from libcst.codemod import CodemodContext
from codemodder.file_context import FileContext
from codemodder.semgrep import rule_ids_from_yaml_files

from libcst.codemod.visitors import AddImportsVisitor
from codemodder.codemods.change import Change
from codemodder.codemods.base_codemod import BaseCodemod
from codemodder.codemods.base_visitor import BaseVisitor

replacement_import = "safe_command"


class ProcessSandbox(BaseCodemod, BaseVisitor):
    NAME = "process-sandbox"
    DESCRIPTION = (
        "Replaces subprocess.{func} with more secure safe_command library functions."
    )
    CHANGE_DESCRIPTION = "Switch use of subprocess for security.safe_command"
    AUTHOR = "dani.alcala@pixee.ai"
    YAML_FILES = [
        "sandbox_process_creation.yaml",
    ]

    RULE_IDS = rule_ids_from_yaml_files(YAML_FILES)

    def __init__(self, codemod_context: CodemodContext, file_context: FileContext):
        BaseCodemod.__init__(self, file_context)
        BaseVisitor.__init__(
            self,
            codemod_context,
            self._results,
            file_context.line_exclude,
            file_context.line_include,
        )

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:
        pos_to_match = self.get_metadata(self.METADATA_DEPENDENCIES[0], original_node)
        if self.filter_by_result(
            pos_to_match
        ) and self.filter_by_path_includes_or_excludes(pos_to_match):
            line_number = pos_to_match.start.line
            self.CHANGES_IN_FILE.append(
                Change(str(line_number), self.CHANGE_DESCRIPTION).to_json()
            )
            AddImportsVisitor.add_needed_import(
                self.context, "security", "safe_command"
            )
            return updated_node.with_changes(
                func=updated_node.func.with_changes(value=Name(replacement_import)),
                args=[Arg(updated_node.func), *updated_node.args],
            )
        return updated_node