import libcst as cst
from libcst.codemod import Codemod, CodemodContext, ContextAwareTransformer
from libcst.metadata import ParentNodeProvider, ScopeProvider, PositionProvider

from libcst import matchers
from codemodder.codemods.base_codemod import ReviewGuidance
from codemodder.codemods.api import BaseCodemod
from codemodder.codemods.utils_mixin import NameResolutionMixin
from codemodder.codemods.base_visitor import UtilsMixin
from codemodder.codemods.base_visitor import BaseTransformer
from codemodder.change import Change
from codemodder.file_context import FileContext
from typing import Union


class SecureFlaskSessionConfig(BaseCodemod, Codemod):
    # METADATA_DEPENDENCIES = BaseCodemod.METADATA_DEPENDENCIES + (
    #     ParentNodeProvider,
    #     ScopeProvider,
    # )
    NAME = "secure-flask-session-configuration"
    SUMMARY = "UTODO"
    REVIEW_GUIDANCE = ReviewGuidance.MERGE_AFTER_REVIEW
    DESCRIPTION = "TODO"
    REFERENCES = [
        {
            "url": "todo",
            "description": "",
        }
    ]

    METADATA_DEPENDENCIES = (PositionProvider,)

    def transform_module_impl(self, tree: cst.Module) -> cst.Module:
        flask_codemod = FixFlaskConfig(self.context, self.file_context)
        result_tree = flask_codemod.transform_module(tree)

        if not flask_codemod.flask_app_name:
            return tree

        if flask_codemod.configs_to_write:
            return self.insert_secure_configs(
                tree,
                result_tree,
                flask_codemod.flask_app_name,
                flask_codemod.configs_to_write,
            )
        return result_tree

    def insert_secure_configs(
        self,
        original_node: cst.Module,
        updated_node: cst.Module,
        app_name: str,
        configs: dict,
    ) -> cst.Module:
        if not configs:
            return updated_node

        config_string = ", ".join(
            f"{key}='{value[0]}'" if isinstance(value[0], str) else f"{key}={value[0]}"
            for key, value in configs.items()
            if value and value[0] is not None
        )
        if not config_string:
            return updated_node

        self.report_change_endof_module(original_node)
        final_line = cst.parse_statement(f"{app_name}.config.update({config_string})")
        new_body = updated_node.body + (final_line,)
        return updated_node.with_changes(body=new_body)

    def report_change_endof_module(self, original_node: cst.Module) -> None:
        # line_number is the end of the module where we will insert the new line.
        pos_to_match = self.node_position(original_node)
        line_number = pos_to_match.end.line
        self.file_context.codemod_changes.append(
            Change(line_number, self.CHANGE_DESCRIPTION)
        )


class FixFlaskConfig(BaseTransformer, NameResolutionMixin):
    """
    Visitor to find calls to flask.Flask and related `.config` accesses.
    """

    METADATA_DEPENDENCIES = (PositionProvider, ParentNodeProvider)
    SECURE_SESSION_CONFIGS = dict(
        # None value indicates unassigned, using default is safe
        # values in order of precedence
        SESSION_COOKIE_HTTPONLY=[None, True],
        SESSION_COOKIE_SECURE=[True],
        SESSION_COOKIE_SAMESITE=["Lax", "Strict"],
    )

    def __init__(self, codemod_context: CodemodContext, file_context: FileContext):
        super().__init__(codemod_context, [])
        self.flask_app_name = ""
        self.configs_to_write = self.SECURE_SESSION_CONFIGS.copy()
        self.file_context = file_context

    def _store_flask_app(self, original_node) -> None:
        flask_app_parent = self.get_metadata(ParentNodeProvider, original_node)
        match flask_app_parent:
            case cst.AnnAssign() | cst.Assign():
                flask_app_attr = flask_app_parent.targets[0].target
                self.flask_app_name = flask_app_attr.value

    def _remove_config(self, key):
        try:
            del self.configs_to_write[key]
        except KeyError:
            pass

    def _get_secure_config_val(self, key):
        val = self.SECURE_SESSION_CONFIGS[key][0] or self.SECURE_SESSION_CONFIGS[key][1]
        return cst.parse_expression(f'"{val}"' if isinstance(val, str) else f"{val}")

    @property
    def flask_app_is_assigned(self):
        return bool(self.flask_app_name)

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call):
        true_name = self.find_base_name(original_node.func)
        if true_name == "flask.Flask":
            self._store_flask_app(original_node)

        if self.flask_app_is_assigned and self._is_config_update_call(original_node):
            return self.call_node_with_secure_configs(original_node, updated_node)
        return updated_node

    def call_node_with_secure_configs(
        self, original_node: cst.Call, updated_node: cst.Call
    ) -> cst.Call:
        new_args = []
        for arg in updated_node.args:
            if (key := arg.keyword.value) in self.SECURE_SESSION_CONFIGS:
                self._remove_config(key)
                if true_value(arg.value) not in self.SECURE_SESSION_CONFIGS[key]:
                    safe_value = self._get_secure_config_val(key)
                    arg = arg.with_changes(value=safe_value)
            new_args.append(arg)

        if updated_node.args != new_args:
            self.report_change(original_node)
        return updated_node.with_changes(args=new_args)

    def leave_Assign(self, original_node: cst.Assign, updated_node: cst.Assign):
        if self.flask_app_is_assigned and self._is_config_subscript(original_node):
            return self.assign_node_with_secure_config(original_node, updated_node)
        return updated_node

    def assign_node_with_secure_config(
        self, original_node: cst.Assign, updated_node: cst.Assign
    ) -> cst.Assign:
        key = true_value(updated_node.targets[0].target.slice[0].slice.value)
        if key in self.SECURE_SESSION_CONFIGS:
            self._remove_config(key)
            if true_value(updated_node.value) not in self.SECURE_SESSION_CONFIGS[key]:
                safe_value = self._get_secure_config_val(key)
                self.report_change(original_node)
                return updated_node.with_changes(value=safe_value)
        return updated_node

    def _is_config_update_call(self, original_node: cst.Call):
        config = cst.Name(value="config")
        app_name = cst.Name(value=self.flask_app_name)
        app_config_node = cst.Attribute(value=app_name, attr=config)
        update = cst.Name(value="update")
        return matchers.matches(
            original_node.func, matchers.Attribute(value=app_config_node, attr=update)
        )

    def _is_config_subscript(self, original_node: cst.Assign):
        config = cst.Name(value="config")
        app_name = cst.Name(value=self.flask_app_name)
        app_config_node = cst.Attribute(value=app_name, attr=config)
        return matchers.matches(
            original_node.targets[0].target, matchers.Subscript(value=app_config_node)
        )

    def report_change(self, original_node):
        # TODO: GET POS TO WORK

        # line_number = self.lineno_for_node(original_node)
        line_number = self.lineno_for_node(original_node)
        self.file_context.codemod_changes.append(
            Change(line_number, SecureFlaskSessionConfig.CHANGE_DESCRIPTION)
        )


def true_value(node: cst.Name | cst.SimpleString) -> str | int | bool:
    # todo: move to a more general util
    from codemodder.project_analysis.file_parsers.utils import clean_simplestring

    # convert 'True' to True, etc
    # '123'  to 123
    # leave strs as they are
    # Try to convert the string to a boolean, integer, or float
    match node:
        case cst.SimpleString():
            return clean_simplestring(node)
        case cst.Name():
            val = node.value
            if val.lower() == "true":
                return True
            elif val.lower() == "false":
                return False
            return val
    return ""
