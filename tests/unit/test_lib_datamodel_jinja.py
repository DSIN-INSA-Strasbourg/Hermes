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

import unittest

from lib.datamodel.jinja import (
    HermesNativeEnvironment,
    Jinja,
    HermesDataModelAttrsmappingError,
    HermesNotAJinjaExpression,
    HermesTooManyJinjaVarsError,
)


class TestJinjaClass(unittest.TestCase):
    types = {
        "str": {"tpl": "{{ 'azerty' }}", "restype": str},
        "int": {"tpl": "{{ 1234 }}", "restype": int},
        "float": {"tpl": "{{ 1234.5678 }}", "restype": float},
        "complex": {
            "tpl": "{{ '1595014243J' }}",
            "restype": str,  # MUST be an str, not a complex
        },
        "list": {"tpl": "{{ [1, 2] }}", "restype": list},
        "tuple": {"tpl": "{{ (1, 2) }}", "restype": tuple},
        "dict": {"tpl": "{{ {'a':1, 2:'b'} }}", "restype": dict},
    }

    def test_jinja_type_conversion(self):
        env = HermesNativeEnvironment()
        compiled = Jinja.compileIfJinjaTemplate(
            var=self.types,
            flatvars_set=None,
            jinjaenv=env,
            errorcontext="Error context",
            allowOnlyOneTemplate=False,
            allowOnlyOneVar=False,
        )
        for k, v in compiled.items():
            result = v["tpl"].render()
            self.assertEqual(
                v["restype"],
                type(result),
                msg=f"{k=} failed: {result=} {type(result)=} instead of {str(v['restype'])}",
            )

    def test_flatvars_set_filling(self):
        env = HermesNativeEnvironment()
        flatvars = set()
        vars = {
            "1": "{{ VAR1 }}",
            "2": "{{ VAR2 | lower }}",
            "3+4": "{{ VAR3 ~ '+' ~ VAR4 }}",
        }
        compiled = Jinja.compileIfJinjaTemplate(
            var=vars,
            flatvars_set=flatvars,
            jinjaenv=env,
            errorcontext="Error context",
            allowOnlyOneTemplate=False,
            allowOnlyOneVar=False,
        )
        self.assertSetEqual(flatvars, set(["VAR1", "VAR2", "VAR3", "VAR4"]))

    def test_allowOnlyOneVar(self):
        env = HermesNativeEnvironment()
        flatvars = set()
        vars = {
            "1": "{{ VAR1 }}",
            "2": "{{ VAR2 | lower }}",
            "3+4": "{{ VAR3 ~ '+' ~ VAR4 }}",
        }
        self.assertRaisesRegex(
            HermesTooManyJinjaVarsError,
            r"2 variables found in Jinja template '''{{ VAR3 ~ '\+' ~ VAR4 }}'''. Only one Jinja var is allowed to ensure data consistency",
            Jinja.compileIfJinjaTemplate,
            var=vars,
            flatvars_set=flatvars,
            jinjaenv=env,
            errorcontext="Error context",
            allowOnlyOneTemplate=False,
            allowOnlyOneVar=True,
        )

    def test_renderQueryVars(self):
        env = HermesNativeEnvironment()

        vars = {
            "1": "{{ VAR1 }}",
            "2": "{{ VAR2 | lower }}",
            "3+4": "{{ VAR3 ~ '+' ~ VAR4 }}",
            "[5, 6]": "{{ [VAR5, VAR6] }}",
            "[7, 8]": ["{{ VAR7 }}", "{{ VAR8 }}"],
            "None": None,
        }

        compiled = Jinja.compileIfJinjaTemplate(
            var=vars,
            flatvars_set=None,
            jinjaenv=env,
            errorcontext="Error context",
            allowOnlyOneTemplate=False,
            allowOnlyOneVar=False,
        )
        context = {
            "VAR1": "VaLuE_1",
            "VAR2": "VaLuE_2",
            "VAR3": "VaLuE_3",
            "VAR4": "VaLuE_4",
            "VAR5": "VaLuE_5",
            "VAR6": "VaLuE_6",
            "VAR7": "VaLuE_7",
            "VAR8": "VaLuE_8",
        }

        result = {
            "1": "VaLuE_1",
            "2": "value_2",
            "3+4": "VaLuE_3+VaLuE_4",
            "[5, 6]": ["VaLuE_5", "VaLuE_6"],
            "[7, 8]": ["VaLuE_7", "VaLuE_8"],
            "None": None,
        }

        rendered = Jinja.renderQueryVars(compiled, context)
        self.assertDictEqual(rendered, result)

    def test_renderStatement(self):
        env = HermesNativeEnvironment()

        vars = {
            "statement": "{% for c in VAR1 %}{{ c }}{% endfor %}",
        }

        self.assertRaisesRegex(
            HermesNotAJinjaExpression,
            "Error context: Only Jinja expressions '{{ ... }}' are allowed. Another type of Jinja data was found in '''{% for c in VAR1 %}{{ c }}{% endfor %}'''",
            Jinja.compileIfJinjaTemplate,
            var=vars,
            flatvars_set=None,
            jinjaenv=env,
            errorcontext="Error context",
            allowOnlyOneTemplate=False,
            allowOnlyOneVar=False,
        )

    def test_emptyValues_error(self):
        env = HermesNativeEnvironment()

        vars = {
            "empty": "",
        }

        self.assertRaisesRegex(
            HermesDataModelAttrsmappingError,
            "Error context: Empty value was found",
            Jinja.compileIfJinjaTemplate,
            var=vars,
            flatvars_set=None,
            jinjaenv=env,
            errorcontext="Error context",
            allowOnlyOneTemplate=False,
            allowOnlyOneVar=False,
        )

        vars = {
            "empty": "{# comment #}",
        }

        self.assertRaisesRegex(
            HermesDataModelAttrsmappingError,
            "Error context: Empty value was found",
            Jinja.compileIfJinjaTemplate,
            var=vars,
            flatvars_set=None,
            jinjaenv=env,
            errorcontext="Error context",
            allowOnlyOneTemplate=False,
            allowOnlyOneVar=False,
        )

    def test_multipleTemplates_error(self):
        env = HermesNativeEnvironment()
        vars = {
            "expressions": "{{ VAR1 | upper }} Hello {{ VAR2 }}",
        }

        self.assertRaisesRegex(
            HermesDataModelAttrsmappingError,
            "Error context: A mix between jinja templates and raw data was found in '''{{ VAR1 | upper }} Hello {{ VAR2 }}''', with this configuration it's impossible to determine source attribute name",
            Jinja.compileIfJinjaTemplate,
            var=vars,
            flatvars_set=None,
            jinjaenv=env,
            errorcontext="Error context",
            allowOnlyOneTemplate=True,
            allowOnlyOneVar=False,
        )

    def test_multipleTemplates_success(self):
        env = HermesNativeEnvironment()
        vars = {
            "expressions": "{{ VAR1 | upper }} Hello {{ VAR2 }}",
        }

        compiled = Jinja.compileIfJinjaTemplate(
            var=vars,
            flatvars_set=None,
            jinjaenv=env,
            errorcontext="Error context",
            allowOnlyOneTemplate=False,
            allowOnlyOneVar=False,
        )

        context = {
            "VAR1": "VaLuE_1",
            "VAR2": "VaLuE_2",
        }

        result = {
            "expressions": "VALUE_1 Hello VaLuE_2",
        }

        rendered = Jinja.renderQueryVars(compiled, context)
        self.assertDictEqual(rendered, result)

    def test_multipleVars_error(self):
        env = HermesNativeEnvironment()
        vars = {
            "expression": "{{ (VAR1 | upper) ~ ' ' ~ VAR2 }}",
        }

        self.assertRaisesRegex(
            HermesTooManyJinjaVarsError,
            r"Error context: 2 variables found in Jinja template '''{{ \(VAR1 \| upper\) ~ ' ' ~ VAR2 }}'''. Only one Jinja var is allowed to ensure data consistency",
            Jinja.compileIfJinjaTemplate,
            var=vars,
            flatvars_set=None,
            jinjaenv=env,
            errorcontext="Error context",
            allowOnlyOneTemplate=False,
            allowOnlyOneVar=True,
        )

    def test_multipleVars_success(self):
        env = HermesNativeEnvironment()
        vars = {
            "expression": "{{ (VAR1 | upper) ~ '+' ~ VAR2 }}",
        }

        compiled = Jinja.compileIfJinjaTemplate(
            var=vars,
            flatvars_set=None,
            jinjaenv=env,
            errorcontext="Error context",
            allowOnlyOneTemplate=False,
            allowOnlyOneVar=False,
        )

        context = {
            "VAR1": "VaLuE_1",
            "VAR2": "VaLuE_2",
        }

        result = {
            "expression": "VALUE_1+VaLuE_2",
        }

        rendered = Jinja.renderQueryVars(compiled, context)
        self.assertDictEqual(rendered, result)
