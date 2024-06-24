#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Hermes : Change Data Capture (CDC) tool from any source(s) to any target
# Copyright (C) 2023, 2024 INSA Strasbourg
#
# This file is part of Hermes.
#
# Hermes is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Hermes is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hermes. If not, see <https://www.gnu.org/licenses/>.


from ast import parse, literal_eval
from itertools import chain, islice
from jinja2 import meta, Environment
from jinja2.environment import Template
from jinja2.nativetypes import NativeCodeGenerator
from jinja2.nodes import Output, TemplateData
from types import GeneratorType
from typing import Any, Iterable, Optional


class HermesNotAJinjaExpression(Exception):
    """Raised when a Jinja statement is found in template"""


class HermesDataModelAttrsmappingError(Exception):
    """Raised when an attrsmapping in datamodel is invalid"""


class HermesTooManyJinjaVarsError(Exception):
    """Raised when an attrsmapping in datamodel is invalid"""


class HermesUnknownVarsInJinjaTemplateError(Exception):
    """Raised when an unknown var is found in a Jinja template"""


def hermes_native_concat(values: Iterable[Any]) -> Optional[Any]:
    """Copy of jinja2.nativetypes.native_concat that will return the raw string
    if the resulting value would have been a complex number
    """
    head = list(islice(values, 2))

    if not head:
        return None

    if len(head) == 1:
        raw = head[0]
        if not isinstance(raw, str):
            return raw
    else:
        if isinstance(values, GeneratorType):
            values = chain(head, values)
        raw = "".join([str(v) for v in values])

    try:
        res = literal_eval(
            # In Python 3.10+ ast.literal_eval removes leading spaces/tabs
            # from the given string. For backwards compatibility we need to
            # parse the string ourselves without removing leading spaces/tabs.
            parse(raw, mode="eval")
        )
    except (ValueError, SyntaxError, MemoryError):
        return raw

    if isinstance(res, complex):
        # Return the raw string instead of the evaluated value
        return raw
    else:
        return res


class HermesNativeEnvironment(Environment):
    """An environment that renders templates to native Python types, excepted
    the complex numbers that are ignored."""

    code_generator_class = NativeCodeGenerator
    concat = staticmethod(hermes_native_concat)  # type: ignore


class Jinja:
    """Helper class to compile Jinja expressions, and render query vars"""

    @classmethod
    def _compileIfJinjaTemplate(
        cls,
        tpl: str,
        jinjaenv: HermesNativeEnvironment,
        errorcontext: str,
        allowOnlyOneTemplate: bool,
        allowOnlyOneVar: bool,
    ) -> tuple[Template | str, list[str]]:
        """Parse specified string to determine if it contains some Jinja or not.
        Return a tuple (jinjaCompiledTemplate, varlist)

        If tpl contains some Jinja:
            - jinjaCompiledTemplate will be a Template instance, to call with
                .render(contextdict)
            - varlist will be a list of var names required to render templates
        else:
            - jinjaCompiledTemplate will be tpl
            - varlist will be a list containing only tpl

        errorcontext: is a string that will prefix error messages
        allowOnlyOneTemplate: if True, if tpl contains something else than a
            non-jinja string OR a single template, an HermesDataModelAttrsmappingError
            will be raised
        allowOnlyOneVar: if True, if tpl contains more than one variable, an
            HermesTooManyJinjaVarsError will be raised
        """
        env = HermesNativeEnvironment()
        env.filters.update(jinjaenv.filters)
        ast = env.parse(tpl)
        vars = meta.find_undeclared_variables(ast)

        if len(ast.body) == 0:
            raise HermesDataModelAttrsmappingError(
                f"{errorcontext}: Empty value was found"
            )

        elif len(ast.body) > 1:
            if allowOnlyOneTemplate:
                raise HermesDataModelAttrsmappingError(
                    f"{errorcontext}: Multiple jinja templates found in '''{tpl}''',"
                    " only one is allowed"
                )
        else:
            if not isinstance(ast.body[0], Output):
                raise HermesNotAJinjaExpression(
                    f"{errorcontext}: Only Jinja expressions '{{{{ ... }}}}' are"
                    f" allowed. Another type of Jinja data was found in '''{tpl}'''"
                )

            if len(ast.body[0].nodes) == 1 and isinstance(
                ast.body[0].nodes[0], TemplateData
            ):
                # tpl is not a Jinja template, return it as is
                return (tpl, [tpl])

            for item in ast.body[0].nodes:
                if allowOnlyOneTemplate and isinstance(item, TemplateData):
                    raise HermesDataModelAttrsmappingError(
                        f"{errorcontext}: A mix between jinja templates and raw data"
                        f" was found in '''{tpl}''', with this configuration it's"
                        " impossible to determine source attribute name"
                    )

        # tpl is a Jinja template, return each var name it contains
        if allowOnlyOneVar and len(vars) > 1:
            raise HermesTooManyJinjaVarsError(
                f"{errorcontext}: {len(vars)} variables found in Jinja template"
                f" '''{tpl}'''. Only one Jinja var is allowed to ensure data"
                " consistency"
            )

        return (jinjaenv.from_string(tpl), vars)

    @classmethod
    def compileIfJinjaTemplate(
        cls,
        var: Any,
        flatvars_set: set[str] | None,
        jinjaenv: HermesNativeEnvironment,
        errorcontext: str,
        allowOnlyOneTemplate: bool,
        allowOnlyOneVar: bool,
        excludeFlatVars: set[str] = set(),
    ) -> Any:
        """Recursive copy of specified var to replace all jinja templates strings by
        their compiled template instance.

        If flatvars_set is specified, every vars met (raw string, or Jinja vars) will be
        added to it, excepted those specified in excludeFlatVars

        Returns the same var as specified, where all strings containing jinja templates
        have been replaced by a compiled version of the template
        (jinja2.environment.Template instance).

        errorcontext: is a string that will prefix error messages
        allowOnlyOneTemplate: if True, if tpl contains something else than a
            non-jinja string OR a single template, an HermesDataModelAttrsmappingError
            will be raised
        allowOnlyOneVar: if True, if tpl contains more than one variable, an
            HermesTooManyJinjaVarsError will be raised
        """
        if type(var) is str:
            template, varlist = cls._compileIfJinjaTemplate(
                var, jinjaenv, errorcontext, allowOnlyOneTemplate, allowOnlyOneVar
            )
            if type(flatvars_set) is set:
                flatvars_set.update(set(varlist) - excludeFlatVars)
            return template
        elif type(var) is dict:
            res = {}
            for k, v in var.items():
                res[k] = cls.compileIfJinjaTemplate(
                    v,
                    flatvars_set,
                    jinjaenv,
                    errorcontext,
                    allowOnlyOneTemplate,
                    allowOnlyOneVar,
                    excludeFlatVars,
                )
            return res
        elif type(var) is list:
            return [
                cls.compileIfJinjaTemplate(
                    v,
                    flatvars_set,
                    jinjaenv,
                    errorcontext,
                    allowOnlyOneTemplate,
                    allowOnlyOneVar,
                    excludeFlatVars,
                )
                for v in var
            ]
        else:
            return var

    @classmethod
    def renderQueryVars(cls, queryvars: Any, context: dict[str, Any]) -> Any:
        """Render Jinja queryvars templates with specified context dict, and returns
        rendered dict"""
        if isinstance(queryvars, Template):
            return queryvars.render(context)
        elif type(queryvars) is dict:
            return {k: cls.renderQueryVars(v, context) for k, v in queryvars.items()}
        elif type(queryvars) is list:
            return [cls.renderQueryVars(v, context) for v in queryvars]
        else:
            return queryvars
