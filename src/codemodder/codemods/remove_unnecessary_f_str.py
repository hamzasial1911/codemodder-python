import libcst as cst
from libcst.codemod import (
    CodemodContext,
)
from libcst.codemod.commands.unnecessary_format_string import UnnecessaryFormatString
import libcst.matchers as m
from codemodder.codemods.base_codemod import ReviewGuidance
from codemodder.codemods.api import BaseCodemod
from codemodder.file_context import FileContext


class RemoveUnnecessaryFStr(BaseCodemod, UnnecessaryFormatString):
    NAME = "remove-unnecessary-f-str"
    REVIEW_GUIDANCE = ReviewGuidance.MERGE_WITHOUT_REVIEW
    DESCRIPTION = UnnecessaryFormatString.DESCRIPTION

    def __init__(self, codemod_context: CodemodContext, file_context: FileContext):
        UnnecessaryFormatString.__init__(self, codemod_context)
        BaseCodemod.__init__(self, file_context)

    @m.leave(m.FormattedString(parts=(m.FormattedStringText(),)))
    def _check_formatted_string(
        self,
        _original_node: cst.FormattedString,
        updated_node: cst.FormattedString,
    ):
        transformed_node = super()._check_formatted_string(_original_node, updated_node)
        if not _original_node.deep_equals(transformed_node):
            self.report_change(_original_node)
        return transformed_node