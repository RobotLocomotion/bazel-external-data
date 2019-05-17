#!/usr/bin/env python

import os
import subprocess
import unittest


def subshell(cmd):
    return subprocess.check_output(cmd, shell=True).decode("utf8").strip()


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

archive_files = [
    "archive/a.bin",
    "archive/b.bin",
    "archive/subdir/c.bin",
]

data_dir = 'data'
mock_dir = 'mock'


class TestBasics(unittest.TestCase):
    def test_files(self):
        # Go through each file and ensure that we have the desired contents.
        files = subshell("find data -name '*.bin' | sort")
        for file in files.split('\n'):
            with open(file) as f:
                contents = f.read()
            file_name = os.path.basename(file)

            mock_contents = None
            for mock_name, mock_file_names in expected_files.items():
                if file_name in mock_file_names:
                    mock_file = os.path.join(mock_dir, mock_name, file_name)
                    with open(mock_file) as f:
                        mock_contents = f.read()
                    break
            if mock_contents is None:
                for archive_file in archive_files:
                    if "data/" + archive_file == file:
                        mock_contents = "Contents of '{}'".format(file_name)
                        break
                else:
                    print("Skipping: {}".format(file))
            else:
                self.assertEqual(contents, mock_contents)

    def test_executable(self):
        output = subshell("data/executable")
        self.assertEqual(output, "Hello")


if __name__ == '__main__':
    unittest.main()
