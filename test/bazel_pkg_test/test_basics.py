#!/usr/bin/env python

import os
import unittest


class TestBasics(unittest.TestCase):
    def test_files(self):
        with open('data/basic.bin') as f:
            contents = f.read()
        contents_expected = "Content for 'basic.bin'\n"
        self.assertEquals(contents, contents_expected)


if __name__ == '__main__':
    unittest.main()
