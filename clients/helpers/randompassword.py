#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Hermes : Change Data Capture (CDC) tool from any source(s) to any target
# Copyright (C) 2024 INSA Strasbourg
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

import random


class RandomPassword:
    """Helper to generate a random password"""

    def __init__(
        self,
        length: int = 32,
        withUpperLetters: bool = True,
        minimumNumberOfUpperLetters: int = 1,
        withLowerLetters: bool = True,
        minimumNumberOfLowerLetters: int = 1,
        withNumbers: bool = True,
        minimumNumberOfNumbers: int = 1,
        withSpecialChars: bool = True,
        minimumNumberOfSpecialChars: int = 1,
        lettersDict: str = "abcdefghijklmnopqrstuvwxyz",
        specialCharsDict: str = "!@#$%^&*",
        avoidAmbigousChars: bool = False,
        ambigousCharsdict: str = "lIO01",
    ):
        if (
            minimumNumberOfUpperLetters < 0
            or minimumNumberOfLowerLetters < 0
            or minimumNumberOfNumbers < 0
            or minimumNumberOfSpecialChars < 0
        ):
            raise AssertionError(
                "Invalid minimum value specified : the value can't be negative !"
                f" {minimumNumberOfUpperLetters=} {minimumNumberOfLowerLetters=}"
                f" {minimumNumberOfNumbers=} {minimumNumberOfSpecialChars=}"
            )

        self._withUpperLetters: bool = withUpperLetters
        self._withLowerLetters: bool = withLowerLetters
        self._withNumbers: bool = withNumbers
        self._withSpecialChars: bool = withSpecialChars
        self._minUpper: int = 0
        self._minLower: int = 0
        self._minNumbers: int = 0
        self._minSpecials: int = 0
        self._upperLetters: str = ""
        self._lowerLetters: str = ""
        self._numbers: str = ""
        self._specials: str = ""
        self._ambigous: str = ""

        if avoidAmbigousChars:
            self._ambigous = ambigousCharsdict

        if withUpperLetters:
            self._minUpper = minimumNumberOfUpperLetters
            self._upperLetters = RandomPassword._removeCharsFromString(
                lettersDict.upper(), self._ambigous
            )
            if self._upperLetters == "":
                raise AssertionError(
                    "Unable to enforce specified constraints:"
                    " the resulting upperLettersDict is empty"
                )

        if withLowerLetters:
            self._minLower = minimumNumberOfLowerLetters
            self._lowerLetters = RandomPassword._removeCharsFromString(
                lettersDict.lower(), self._ambigous
            )
            if self._lowerLetters == "":
                raise AssertionError(
                    "Unable to enforce specified constraints:"
                    " the resulting lowerLettersDict is empty"
                )

        if withNumbers:
            self._minNumbers = minimumNumberOfNumbers
            self._numbers = RandomPassword._removeCharsFromString(
                "0123456789", self._ambigous
            )
            if self._numbers == "":
                raise AssertionError(
                    "Unable to enforce specified constraints:"
                    " the resulting numbersDict is empty"
                )

        if withSpecialChars:
            self._minSpecials = minimumNumberOfSpecialChars
            self._specials = RandomPassword._removeCharsFromString(
                specialCharsDict, self._ambigous
            )
            if self._specials == "":
                raise AssertionError(
                    "Unable to enforce specified constraints:"
                    " the resulting specialCharsDict is empty"
                )

        self._remaining: int = (
            length
            - self._minUpper
            - self._minLower
            - self._minNumbers
            - self._minSpecials
        )
        if self._remaining < 0:
            raise AssertionError(
                f"Unable to enforce specified constraints: the specified {length=} is"
                " lower than the sum of all minimumNumberOf*"
            )

        self._allChars: str = (
            self._upperLetters + self._lowerLetters + self._numbers + self._specials
        )
        if self._allChars == "":
            raise AssertionError(
                "Unable to enforce specified constraints:"
                " the resulting allCharsDict is empty"
            )

    def generate(self) -> str:
        result: str = ""
        if self._withUpperLetters:
            result += RandomPassword._randomChoice(self._minUpper, self._upperLetters)

        if self._withLowerLetters:
            result += RandomPassword._randomChoice(self._minLower, self._lowerLetters)

        if self._withNumbers:
            result += RandomPassword._randomChoice(self._minNumbers, self._numbers)

        if self._withSpecialChars:
            result += RandomPassword._randomChoice(self._minSpecials, self._specials)

        result += RandomPassword._randomChoice(self._remaining, self._allChars)
        # Shuffle and return the result
        return "".join(random.sample(result, len(result)))

    @staticmethod
    def generateOne(
        length: int = 32,
        withUpperLetters: bool = True,
        minimumNumberOfUpperLetters: int = 1,
        withLowerLetters: bool = True,
        minimumNumberOfLowerLetters: int = 1,
        withNumbers: bool = True,
        minimumNumberOfNumbers: int = 1,
        withSpecialChars: bool = True,
        minimumNumberOfSpecialChars: int = 1,
        lettersDict: str = "abcdefghijklmnopqrstuvwxyz",
        specialCharsDict: str = "!@#$%^&*",
        avoidAmbigousChars: bool = False,
        ambigousCharsdict: str = "lIO01",
    ) -> str:
        pwg = RandomPassword(
            length,
            withUpperLetters,
            minimumNumberOfUpperLetters,
            withLowerLetters,
            minimumNumberOfLowerLetters,
            withNumbers,
            minimumNumberOfNumbers,
            withSpecialChars,
            minimumNumberOfSpecialChars,
            lettersDict,
            specialCharsDict,
            avoidAmbigousChars,
            ambigousCharsdict,
        )
        return pwg.generate()

    @staticmethod
    def _removeCharsFromString(string: str, charsToRemove: str) -> str:
        return "".join(sorted(set(string) - set(charsToRemove)))

    @staticmethod
    def _randomChoice(quantity: int, fromstr: str):
        return "".join(random.choices(fromstr, k=quantity))
