#!/usr/bin/env python

import os
import unittest
from bazel_external_data.util import subshell

expected_files = {
    "master_files": [
        "basic.bin",
        "glob_1.bin",
        "glob_2.bin",
        "glob_3.bin",
    ],
    "extra_files": [
        "extra.bin",
    ],
}

data_dir = 'data'
mock_dir = 'mock'


class TestBasics(unittest.TestCase):
    def test_files(self):
        # Go through each file and ensure that we have the desired contents.
        files = subshell("find data -name '*.bin'")
        for file in files.split('\n'):
            contents = open(file).read()
            file_name = os.path.basename(file)

            mock_file = None
            mock_contents = None
            for mock_name, mock_file_names in expected_files.iteritems():
                if file_name in mock_file_names:
                    mock_file = os.path.join(mock_dir, mock_name, file_name)
                    mock_contents = open(mock_file).read()
                    break
            if mock_file is None:
                print("Skipping: {}".format(file))
            else:
                self.assertEquals(contents, mock_contents)


if __name__ == '__main__':
    unittest.main()
