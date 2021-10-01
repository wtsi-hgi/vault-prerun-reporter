import unittest
from report import FileNode, Expiry, KeepStatus, fill_array_of_files


class TestFileStructure(unittest.TestCase):
    def test_add_child(self):
        expected = FileNode(Expiry.Directory, 0, None)
        expected.children = {
            "fileA": FileNode(Expiry.InDate, 17000, "userA"),
            "fileB": FileNode(Expiry.Expired, 24000, "userB"),
            "dirA": FileNode(Expiry.Directory, 4096, None)
        }
        expected.children["dirA"].children = {
            "fileA": FileNode(Expiry.InDate, 48000, "userA"),
            "fileB": FileNode(Expiry.Expired, 70000, "userB")
        }

        actual = FileNode(Expiry.Directory, 0, None)
        actual.add_child("fileA", Expiry.InDate, 17000, "userA")
        actual.add_child("fileB", Expiry.Expired, 24000, "userB")
        actual.add_child("dirA/fileA", Expiry.InDate, 48000, "userA")
        actual.add_child("dirA/fileB", Expiry.Expired, 70000, "userB")

        # adding this last to see if it'll cope
        actual.add_child("dirA", Expiry.Directory, 4096, None)

        self.assertEqual(hash(expected), hash(actual))

    def test_file_size(self):
        files = FileNode(Expiry.Directory, 0, None)
        files.children = {
            "fileA": FileNode(Expiry.InDate, 17000, ""),
            "fileB": FileNode(Expiry.Expired, 24000, ""),
            "dirA": FileNode(Expiry.Directory, 4096, "")
        }
        files.children["dirA"].children = {
            "fileA": FileNode(Expiry.InDate, 48000, ""),
            "fileB": FileNode(Expiry.Expired, 70000, "")
        }

        self.assertEqual(
            (files.size, files.children["dirA"].size), (163096, 122096))


class TestFiletypeCalculations(unittest.TestCase):
    def setUp(self) -> None:
        self.file_root = FileNode(Expiry.Directory, 0, None)
        self.file_root.children = {
            "dirA": FileNode(Expiry.Directory, 4096, None),
            "dirB": FileNode(Expiry.Directory, 4096, None),
            "fileA.py": FileNode(Expiry.Expired, 12000, "userA"),
            "fileB.py": FileNode(Expiry.InDate, 12000, "userA"),
            "fileC.py": FileNode(Expiry.Expired, 14000, "userA"),
            "fileA.vcf": FileNode(Expiry.Expired, 100000, "userA"),
            "fileB.vcf": FileNode(Expiry.InDate, 100000, "userA"),
            "fileC.vcf": FileNode(Expiry.Expired, 150000, "userA"),
            "fileX.py": FileNode(Expiry.Expired, 22000, "userB"),
            "fileY.py": FileNode(Expiry.InDate, 22000, "userB"),
            "fileZ.py": FileNode(Expiry.Expired, 24000, "userB"),
            "fileX.vcf": FileNode(Expiry.Expired, 200000, "userB"),
            "fileY.vcf": FileNode(Expiry.InDate, 200000, "userB"),
            "fileZ.vcf": FileNode(Expiry.Expired, 250000, "userB"),
            "fileA.other": FileNode(Expiry.Expired, 100000, "userA")
        }
        self.file_root.children["dirA"].children = {
            "fileAA.py": FileNode(Expiry.Expired, 12000, "userA"),
            "fileBB.py": FileNode(Expiry.InDate, 12000, "userA"),
            "fileCC.py": FileNode(Expiry.Expired, 14000, "userA"),
            "fileAA.vcf": FileNode(Expiry.Expired, 100000, "userA"),
            "fileBB.vcf": FileNode(Expiry.InDate, 100000, "userA"),
            "fileCC.vcf": FileNode(Expiry.Expired, 150000, "userA"),
            "fileXX.py": FileNode(Expiry.Expired, 22000, "userB"),
            "fileYY.py": FileNode(Expiry.InDate, 22000, "userB"),
            "fileZZ.py": FileNode(Expiry.Expired, 24000, "userB"),
            "fileXX.vcf": FileNode(Expiry.Expired, 200000, "userB"),
            "fileYY.vcf": FileNode(Expiry.InDate, 200000, "userB"),
            "fileZZ.vcf": FileNode(Expiry.Expired, 250000, "userB")
        }
        self.file_root.children["dirB"].children = {
            "fileAAA.py": FileNode(Expiry.Expired, 12000, "userA"),
            "fileBBB.py": FileNode(Expiry.InDate, 12000, "userA"),
            "fileCCC.py": FileNode(Expiry.Expired, 14000, "userA"),
            "fileAAA.vcf": FileNode(Expiry.Expired, 100000, "userA"),
            "fileBBB.vcf": FileNode(Expiry.InDate, 100000, "userA"),
            "fileCCC.vcf": FileNode(Expiry.Expired, 150000, "userA"),
            "fileXXX.py": FileNode(Expiry.Expired, 22000, "userB"),
            "fileYYY.py": FileNode(Expiry.InDate, 22000, "userB"),
            "fileZZZ.py": FileNode(Expiry.Expired, 24000, "userB"),
            "fileXXX.vcf": FileNode(Expiry.Expired, 200000, "userB"),
            "fileYYY.vcf": FileNode(Expiry.InDate, 200000, "userB"),
            "fileZZZ.vcf": FileNode(Expiry.Expired, 250000, "userB"),
            "fileA.other": FileNode(Expiry.Expired, 100000, "userA")
        }

        """
        Expectations:

        userA
                Num Files   Size
        .py     6           78000
        .vcf    6           750000
        Other   2           200000

        userB
                Num Files   Size
        .py     6           138000
        .vcf    6           1350000
        """

    def test_file_count(self):
        expected = {"userA": {".py": 6, ".vcf": 6, "Other": 2},
                    "userB": {".py": 6, ".vcf": 6}}
        actual = {user: {path: details.num_files for path, details in v.items()} for (
            user, v) in self.file_root.filetypes.items()}
        self.assertEqual(expected, actual)

    def test_file_size(self):
        expected = {"userA": {".py": 78000, ".vcf": 750000,
                              "Other": 200000}, "userB": {".py": 138000, ".vcf": 1350000}}
        actual = {user: {path: details.size for path, details in v.items()}
                  for (user, v) in self.file_root.filetypes.items()}
        self.assertEqual(expected, actual)


class TestFileTreeToArrays(unittest.TestCase):
    def setUp(self) -> None:
        self.file_root = FileNode(Expiry.Directory, 0, None)
        self.file_root.children = {
            "dirA": FileNode(Expiry.Directory, 4096, None),
            "dirB": FileNode(Expiry.Directory, 4096, None),
            "dirC": FileNode(Expiry.Directory, 4096, None),
            "dirD": FileNode(Expiry.Directory, 4096, None),
            "fileA.py": FileNode(Expiry.Expired, 12000, ""),
            "fileB.py": FileNode(Expiry.InDate, 12000, ""),
            "fileC.py": FileNode(Expiry.Expired, 14000, ""),
            "fileA.vcf": FileNode(Expiry.Expired, 100000, ""),
            "fileB.vcf": FileNode(Expiry.InDate, 100000, ""),
            "fileC.vcf": FileNode(Expiry.Expired, 150000, "")
        }
        self.file_root.children["dirA"].children = {
            "fileAA.py": FileNode(Expiry.Expired, 12000, ""),
            "fileBB.py": FileNode(Expiry.InDate, 12000, ""),
            "fileCC.py": FileNode(Expiry.Expired, 14000, ""),
            "fileAA.vcf": FileNode(Expiry.Expired, 100000, ""),
            "fileBB.vcf": FileNode(Expiry.InDate, 100000, ""),
            "fileCC.vcf": FileNode(Expiry.Expired, 150000, "")
        }
        self.file_root.children["dirB"].children = {
            "fileAAA.py": FileNode(Expiry.Expired, 12000, ""),
            "fileBBB.py": FileNode(Expiry.InDate, 12000, ""),
            "fileCCC.py": FileNode(Expiry.Expired, 14000, ""),
            "fileAAA.vcf": FileNode(Expiry.Expired, 100000, ""),
            "fileBBB.vcf": FileNode(Expiry.InDate, 100000, ""),
            "fileCCC.vcf": FileNode(Expiry.Expired, 150000, "")
        }
        self.file_root.children["dirC"].children = {
            "fileA": FileNode(Expiry.Expired, 10000, ""),
            "fileB": FileNode(Expiry.Expired, 10000, "")
        }
        self.file_root.children["dirD"].children = {
            "fileA": FileNode(Expiry.InDate, 10000, ""),
            "fileB": FileNode(Expiry.InDate, 10000, "")
        }

    def test_files_to_array_delete(self):
        # converting to set to remove order requirement
        expected = set([
            ("/dirA/fileAA.py", 12000),
            ("/dirA/fileCC.py", 14000),
            ("/dirA/fileAA.vcf", 100000),
            ("/dirA/fileCC.vcf", 150000),
            ("/dirB/fileAAA.py", 12000),
            ("/dirB/fileCCC.py", 14000),
            ("/dirB/fileAAA.vcf", 100000),
            ("/dirB/fileCCC.vcf", 150000),
            ("/dirC", 24096),
            ("/fileA.py", 12000),
            ("/fileC.py", 14000),
            ("/fileA.vcf", 100000),
            ("/fileC.vcf", 150000)
        ])
        actual = set(fill_array_of_files(
            "", self.file_root, KeepStatus.Delete))
        self.assertEqual(expected, actual)

    def test_files_to_keep(self):
        expected = set([
            ("/dirA/fileBB.py", 12000),
            ("/dirA/fileBB.vcf", 100000),
            ("/dirB/fileBBB.py", 12000),
            ("/dirB/fileBBB.vcf", 100000),
            ("/dirD", 24096),
            ("/fileB.py", 12000),
            ("/fileB.vcf", 100000)
        ])
        actual = set(fill_array_of_files("", self.file_root, KeepStatus.Keep))
        self.assertEqual(expected, actual)
