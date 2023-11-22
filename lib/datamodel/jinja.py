#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Hermes : Change Data Capture (CDC) tool from any source(s) to any target
# Copyright (C) 2023 INSA Strasbourg
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


from jinja2 import meta
from jinja2.environment import Template
from jinja2.nativetypes import NativeEnvironment
from jinja2.nodes import TemplateData
from typing import Any

import logging

logger = logging.getLogger("hermes")


class HermesDataModelAttrsmappingError(Exception):
    """Raised when an attrsmapping in datamodel is invalid"""


class HermesTooManyJinjaVarsError(Exception):
    """Raised when an attrsmapping in datamodel is invalid"""


class HermesUnknownVarsInJinjaTemplateError(Exception):
    """Raised when an unknown var is found in a Jinja template"""


class Jinja:
    """Helper class to compile Jinja expressions, and render query vars"""

    @classmethod
    def _compileIfJinjaTemplate(
        cls,
        tpl: str,
        jinjaenv: NativeEnvironment,
        errorcontext: str,
        allowOnlyOneTemplate: bool,
        allowOnlyOneVar: bool,
    ) -> tuple[Template | str, list[str]]:
        """Parse specified string to determine if it contains some Jinja or not.
        Return a tuple (jinjaCompiledTemplate, varlist)

        If tpl contains some Jinja :
            - jinjaCompiledTemplate will be a Template instance, to call with
                .render(contextdict)
            - varlist will be a list of var names required to render templates
        else :
            - jinjaCompiledTemplate will be tpl
            - varlist will be a list containing only tpl

        errorcontext: is a string that will prefix error messages
        allowOnlyOneTemplate: if True, if tpl contains something else than a
            non-jinja string OR a single template, an HermesDataModelAttrsmappingError
            will be raised
        allowOnlyOneVar: if True, if tpl contains more than one variable, an
            HermesTooManyJinjaVarsError will be raised
        """
        env = NativeEnvironment()
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
                    f"{errorcontext}: Multiple jinja templates found in '''{tpl}''', only one is allowed"
                )
        else:
            if (
                len(ast.body[0].nodes) == 1
                and type(ast.body[0].nodes[0]) == TemplateData
            ):
                # tpl is not a Jinja template, return it as is
                return (tpl, [tpl])

            for item in ast.body[0].nodes:
                if allowOnlyOneTemplate and type(item) == TemplateData:
                    raise HermesDataModelAttrsmappingError(
                        f"{errorcontext}: A mix between jinja templates and raw data was found in '''{tpl}''', with this configuration it's impossible to determine source attribute name"
                    )

        # tpl is a Jinja template, return each var name it contains
        if allowOnlyOneVar and len(vars) > 1:
            raise HermesTooManyJinjaVarsError(
                f"{len(vars)} variables found in Jinja template '''{tpl}'''. Only one Jinja var is allowed to ensure data consistency"
            )

        return (jinjaenv.from_string(tpl), vars)

    @classmethod
    def compileIfJinjaTemplate(
        cls,
        var: Any,
        flatvars_set: set[str] | None,
        jinjaenv: NativeEnvironment,
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
        if type(var) == str:
            template, varlist = cls._compileIfJinjaTemplate(
                var, jinjaenv, errorcontext, allowOnlyOneTemplate, allowOnlyOneVar
            )
            if type(flatvars_set) == set:
                flatvars_set.update(set(varlist) - excludeFlatVars)
            return template
        elif type(var) == dict:
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
        elif type(var) == list:
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
        """Render Jinja queryvars templates with specified context dict, and returns rendered dict"""
        if isinstance(queryvars, Template):
            return queryvars.render(context)
        elif type(queryvars) == dict:
            return {k: cls.renderQueryVars(v, context) for k, v in queryvars.items()}
        elif type(queryvars) == list:
            return [cls.renderQueryVars(v, context) for v in queryvars]
        else:
            return queryvars
