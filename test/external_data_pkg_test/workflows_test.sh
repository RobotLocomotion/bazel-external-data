#!/bin/bash
set -e -u
set -x

eecho() { echo "$@" >&2; }
mkcd() { mkdir -p ${1} && cd ${1}; }
bazel() { $(which bazel) --bazelrc=/dev/null "$@"; }
# For testing, we should be able to both (a) test and (b) run the target.
bazel-test() { bazel test "$@"; bazel run "$@"; }
readlink_py() { python -c 'import os, sys; print(os.path.realpath(sys.argv[1]))' ${1}; }
should_fail() { eecho "Should have failed!"; exit 1; }

# Ensure this is only run with `TEST_TMPDIR` present (called from
# `workspace_test.sh`).
[[ -n "${TEST_TMPDIR}" ]]

cache_dir=${TEST_TMPDIR}/test_cache
upload_dir=${TEST_TMPDIR}/upload_extra

cd $(dirname $0)
pwd

# Create a new package.
mkcd data_new

# Create the expected contents.
cat > expected.txt <<EOF
Expected contents.
EOF
# Create the new file.
cp expected.txt new.bin
hash=$(sha512sum new.bin | cut -f1 -d' ')

# Write a test that consumes the file.
cat > test_basics.py <<EOF
with open('data_new/new.bin') as f:
    contents = f.read()
with open('data_new/expected.txt') as f:
    contents_expected = f.read()
assert contents == contents_expected
EOF

# Declare this file as a development file, and write our test.
cat > BUILD.bazel <<EOF
load("//tools:external_data.bzl", "external_data")

external_data(
    file = "new.bin",
    mode = "devel",
)

py_test(
    name = "test_basics",
    srcs = ["test_basics.py"],
    data = [
        ":expected.txt",
        ":new.bin"
    ],
)
EOF

# Ensure that we can build the file.
bazel build :new.bin

# Ensure that we can run the test with the file in development mode.
bazel-test :test_basics

# Ensure that our cache and upload directory is empty.
[[ ! -d ${cache_dir} ]]
[[ ! -d ${upload_dir} ]]

# Now upload the file.
../tools/external_data upload ./new.bin

# Ensure our upload directory has the file (and only this file).
[[ -d ${upload_dir} ]]
upload_file=$(find ${upload_dir} -type f)
# - We should have the hash name.
# - The contents should be the same as the original.
diff ${upload_file} ./new.bin > /dev/null
# We should NOT have created a cache at this point.
[[ ! -d ${cache_dir} ]]

# Ensure that we have created the hash file accurately.
[[ $(cat ./new.bin.sha512) == ${hash} ]]

# - Change the original, such that it'd fail the test, and ensure failure.
echo "User changed the file" > ./new.bin
bazel-test :test_basics && should_fail
[[ ! -d ${cache_dir} ]]

# Now switch to 'no_cache' mode.
sed -i 's#mode = "devel",#mode = "no_cache",#g' ./BUILD.bazel
cat BUILD.bazel
# Ensure that we can now run the binary with the external data setup.
bazel-test :test_basics
# No cache should have been used.
[[ ! -d ${cache_dir} ]]

# Switch to 'normal' mode.
sed -i 's/mode = "no_cache",/# Normal is implicit./g' ./BUILD.bazel
cat BUILD.bazel
# - Clean so that we re-trigger a download.
bazel clean
bazel-test :test_basics

# This should have encountered a cache-miss.
[[ -d ${cache_dir} ]]
# - This should be the *only* file in the cache.
cache_file=$(find ${cache_dir} -type f)
# Should have been indexed by the SHA.
[[ $(basename ${cache_file}) == ${hash} ]]
# Contents should be the same.
diff ${cache_file} ./expected.txt > /dev/null

# Now download the file via the command line.
# - This should fail since we already have the file.
../tools/external_data download ./new.bin.sha512 && should_fail
# - Try it with -f
../tools/external_data download -f ./new.bin.sha512
diff new.bin ./expected.txt > /dev/null
# - Try it without -f
rm new.bin
../tools/external_data download ./new.bin.sha512
diff new.bin ./expected.txt > /dev/null

# Ensure that we can just refer to the file, without the hash suffix.
rm new.bin
../tools/external_data download ./new.bin
diff new.bin ./expected.txt > /dev/null

# Now we wish to actively modify the file.
cat > expected.txt <<EOF
New contents!
EOF
# - Must be different.
diff new.bin expected.txt > /dev/null && should_fail
# - Now update local workspace version.
cp expected.txt new.bin
# Change to development mode.
sed -i 's/# Normal is implicit./mode = "devel",/g' ./BUILD.bazel
cat ./BUILD.bazel
# The test should pass.
bazel-test :test_basics

# Now upload the newest version (both original file and hash file should work).
../tools/external_data upload ./new.bin
../tools/external_data upload ./new.bin.sha512

# There should be two files uploaded.
[[ $(find ${upload_dir} -type f | wc -l) -eq 2 ]]

# Test default upload behavior vs. --ignore_overlay
# Specifically, use a file in `master` that is not currently in `extra`.
../tools/external_data download ../data/basic.bin -o ./basic_copy.bin
# - Try uploading. This should not actually upload the file.
../tools/external_data upload ./basic_copy.bin
[[ $(find ${upload_dir} -type f | wc -l) -eq 2 ]]
# - Try uploading wth `--ignore_overlay`. This should upload the file to `extra`.
../tools/external_data upload --ignore_overlay ./basic_copy.bin
[[ $(find ${upload_dir} -type f | wc -l) -eq 3 ]]

# Switch back to normal mode.
sed -i 's/mode = "devel",/# Normal is implicit./g' ./BUILD.bazel
cat ./BUILD.bazel

# Now remove the file. It should still pass the test.
rm new.bin
bazel-test :test_basics

# Download and check the file, but as a symlink now.
../tools/external_data download --symlink ./new.bin.sha512
[[ -L new.bin ]]
diff new.bin expected.txt > /dev/null

# Make sure symlink is read-only.
echo 'Try to overwrite' > ./new.bin && should_fail

# Corrupt the cache.
cache_file=$(readlink ./new.bin)
chmod +w ${cache_file}
echo "Corrupted" > ${cache_file}
# TODO(eric.cousineau): This is using the user's cache -- why?
diff new.bin expected.txt > /dev/null && should_fail
# - Bazel should have recognized the write on the internally built file.
# It will re-trigger a download.
bazel-test :test_basics
# Ensure our symlink is now correct.
diff new.bin expected.txt > /dev/null

# Remove the cache.
rm -rf ${cache_dir}
# - Bazel should have a bad symlink, and should recognize this and re-trigger a download.
bazel-test :test_basics
# - The cache directory should have been re-created.
[[ -d ${cache_dir} ]]

# Ensure that we have all the files we want.
rm new.bin
find . -name '*.sha512' | xargs ../tools/external_data check
# `check` should not have written a new file.
[[ ! -f new.bin ]]


# Test in `data/`
cd ../data/

# Remove any *.bin files that may have been from the original folder.
find . -name '*.bin' | xargs rm -f

# Ensure that we can download all files here (without `check`).
find . -name 'bad.bin.sha512' -prune -o \( -name '*.sha512' -print \) | xargs ../tools/external_data download -f

../tools/external_data check ./subdir/extra.bin.sha512
# Ensure that 'bad.bin' is invalid with `check` and `download`.
../tools/external_data check ./bad.bin.sha512 && should_fail
../tools/external_data download ./bad.bin.sha512 && should_fail

# Now run the external data tests in Bazel, and ensure that everything passes, since
# all files defined in Bazel are covered by the remote structures.
bazel test --test_tag_filters=external_data_check_test ...
bazel build :data

# Now add the file from our original setup.
# - Delete the uploads so that is now an invalid file.
rm -rf ${upload_dir}
# - Add it to the glob setup to ensure that it gets pulled into Bazel.
[[ ! -f new.bin.sha512 ]]
[[ ! -f new.bin ]]
cp ../data_new/new.bin.sha512 glob_4.bin.sha512
# - Ensure that we can download the cached version of it.
../tools/external_data download glob_4.bin.sha512
diff glob_4.bin ../data_new/expected.txt > /dev/null
# - Now check via command-line that it fails.
../tools/external_data check ./glob_4.bin.sha512 && should_fail
# - With caching, it should be able to build.
bazel build :data
# - Now ensure that the this test is (a) defined and (b) will fail.
bazel build :glob_4.bin__check_test
bazel test :glob_4.bin__check_test && should_fail
# - Ensure that testing across all download tests also fail.
bazel test --test_tag_filters=external_data_check_test ... && should_fail

echo "[ Done ]"
