import hashlib
import os


class HashType(object):
    def __init__(self, name):
        self.name = name

    def compute(self, filepath):
        """Computes the hashsum for a given `filepath`. """
        if not os.path.exists(filepath):
            raise RuntimeError("File does not exist: {}".format(filepath))
        assert os.path.isabs(filepath)
        value = self.do_compute(filepath)
        return self.create(value, filepath)

    def do_compute(self, filepath):
        """Implementation to compute a hashsum that is comparable via __eq__.
        """
        raise NotImplemented

    def create(self, value, filepath=None):
        """Creates hashsum given `value` and an optional `filepath`. """
        return Hash(self, value, filepath=filepath)

    def create_empty(self):
        """Creates empty hashsum. """
        return Hash(self, None)

    def __str__(self):
        return "hash[{}]".format(self.name)


class Hash(object):
    """Stores hash value, type, and possibly the filepath the hash was
    generated from. """
    def __init__(self, hash_type, value, filepath=None):
        self.hash_type = hash_type
        self.filepath = filepath
        self._value = value

    def compute(self, filepath):
        """Computes hash for a filepath, using the same type as this hash. """
        return self.hash_type.compute(filepath)

    def compare(self, other_hash, do_throw=True):
        """Compares against another hash. """
        if (other_hash.hash_type == self.hash_type and
                self._value == other_hash._value):
            return True
        else:
            if do_throw:
                raise RuntimeError(
                    "Hash mismatch: {} != {}".format(
                        self.full_str(), other_hash.full_str()))
            else:
                return False

    def compare_file(self, filepath, do_throw=True):
        """Compares against a file, using the same algorithm. """
        return self.compare(self.compute(filepath), do_throw=do_throw)

    def is_empty(self):
        return self._value is None

    def get_value(self):
        return self._value

    def get_algo(self):
        return self.hash_type.name

    def __repr__(self):
        return str(self)

    def __str__(self):
        return "{}:{}".format(self.hash_type.name, self._value)

    def __eq__(self, rhs):
        return self.compare(rhs, do_throw=False)

    def __hash__(self):
        # Do not permit empty hashes to be used in a dict.
        assert not self.is_empty()
        params = (self.hash_type, self._value)
        return hash(params)

    def __ne__(self, rhs):
        return not self.__eq__(rhs)

    def full_str(self):
        out = str(self)
        if self.filepath:
            out += " (file: {})".format(self.filepath)
        return out


class Sha512(HashType):
    def __init__(self):
        HashType.__init__(self, 'sha512')

    def do_compute(self, filepath):
        # From girder/plugins/hashsum_download/server/__init__.py
        chunk_len = 65536
        digest = hashlib.sha512()
        with open(filepath, 'rb') as f:
            while True:
                chunk = f.read(chunk_len)
                if not chunk:
                    break
                digest.update(chunk)
        return digest.hexdigest()


sha512 = Sha512()

if __name__ == "__main__":
    tmp_file = '/tmp/test_hash_file'
    with open(tmp_file, 'w') as f:
        f.write('Example contents\n')
    cur = sha512.compute(tmp_file)

    value_expected = '7f3f25018046549d08c6c9c97808e344aee60071164789a2077a5e34f4a219e45b4f30bc671dc71d2f05d05cec9235a523ebba436254a2b0b3b794f0afd9a7c3'
    hash_expected = sha512.create(value_expected)
    str_expected = 'sha512:{}'.format(value_expected)

    assert hash_expected.compare(cur)
    assert hash_expected == cur

    str_actual = str(cur)
    assert str_actual == str_expected

    try:
        cur_bad = sha512.create('blech')
        cur.compare(cur_bad)
        assert False
    except RuntimeError as e:
        print(e)
    assert cur != cur_bad

    value_1 = sha512.create('7f3f25018046549d08c6c9c97808e344aee60071164789a2077a5e34f4a219e45b4f30bc671dc71d2f05d05cec9235a523ebba436254a2b0b3b794f0afd9a7c3')
    value_2 = sha512.create('6f3f25018046549d08c6c9c97808e344aee60071164789a2077a5e34f4a219e45b4f30bc671dc71d2f05d05cec9235a523ebba436254a2b0b3b794f0afd9a7c3')
    value_2_copy = sha512.create('6f3f25018046549d08c6c9c97808e344aee60071164789a2077a5e34f4a219e45b4f30bc671dc71d2f05d05cec9235a523ebba436254a2b0b3b794f0afd9a7c3')
    value_3 = sha512.create('5f3f25018046549d08c6c9c97808e344aee60071164789a2077a5e34f4a219e45b4f30bc671dc71d2f05d05cec9235a523ebba436254a2b0b3b794f0afd9a7c3')
    d = {value_1: 1, value_2: 2}
    assert value_1 in d
    assert value_2 in d
    assert value_2_copy in d
    assert value_3 not in d
    assert d[value_1] == 1
    assert d[value_2] == 2

    print("[ Done ]")
