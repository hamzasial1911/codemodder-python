import libcst as cst
from typing import Union
from codemodder.codemods.api import BaseCodemod, ReviewGuidance
from codemodder.codemods.utils_mixin import NameResolutionMixin, AncestorPatternsMixin


class FixEmptySequenceComparison(
    BaseCodemod, NameResolutionMixin, AncestorPatternsMixin
):
    NAME = "fix-empty-sequence-comparison"
    SUMMARY = "TODO"
    REVIEW_GUIDANCE = ReviewGuidance.MERGE_WITHOUT_REVIEW
    DESCRIPTION = "TODO"
    REFERENCES: list = []

    def leave_If(
        self, original_node: cst.If, updated_node: cst.If
    ) -> cst.BaseStatement:
        if not self.filter_by_path_includes_or_excludes(
            self.node_position(original_node)
        ):
            return original_node

        match original_node.test:
            case cst.Comparison(
                left=left, comparisons=[cst.ComparisonTarget() as target]
            ):
                if isinstance(target.operator, cst.Equal | cst.NotEqual):
                    right = target.comparator
                    # right is empty: x == []
                    # left is empty: [] == x
                    if (
                        empty_left := self._is_empty_sequence(left)
                    ) or self._is_empty_sequence(right):
                        self.report_change(original_node)
                        if isinstance(target.operator, cst.NotEqual):
                            return updated_node.with_changes(
                                test=right if empty_left else left,
                            )
                        return updated_node.with_changes(
                            test=cst.UnaryOperation(
                                operator=cst.Not(),
                                expression=right if empty_left else left,
                            )
                        )
        return original_node

    def _is_empty_sequence(self, node: cst.BaseExpression):
        match node:
            case cst.List(elements=[]) | cst.Dict(elements=[]) | cst.Tuple(elements=[]):
                return True
        return False

    # def leave_Assert(self, original_node: cst.Assert, updated_node: cst.Assert) -> cst.BaseSmallStatement:
    #     #filter
    #     return self._simplify_empty_check(updated_node)

    # def _simplify_empty_check(self, node): # add type

    # if isinstance(node.test, cst.BooleanOperation) and isinstance(node.test.operator, cst.And):
    #     new_left = self._simplify_comparison(node.test.left)
    #     new_right = self._simplify_comparison(node.test.right)
    #     return node.with_changes(test=cst.BooleanOperation(left=new_left, operator=cst.And(), right=new_right))

    # return self._simplify_comparison(node)