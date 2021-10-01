import unittest
from report import FileNode, Expiry, KeepStatus, fill_array_of_files


class TestFileStructure(unittest.TestCase):
    def test_add_child(self):
        expected = FileNode(Expiry.Directory, 0)
        expected.children = {
            "fileA": FileNode(Expiry.InDate, 17000),
            "fileB": FileNode(Expiry.Expired, 24000),
            "dirA": FileNode(Expiry.Directory, 4096)
        }
        expected.children["dirA"].children = {
            "fileA": FileNode(Expiry.InDate, 48000),
            "fileB": FileNode(Expiry.Expired, 70000)
        }

        actual = FileNode(Expiry.Directory, 0)
        actual.add_child("fileA", Expiry.InDate, 17000)
        actual.add_child("fileB", Expiry.Expired, 24000)
        actual.add_child("dirA/fileA", Expiry.InDate, 48000)
        actual.add_child("dirA/fileB", Expiry.Expired, 70000)

        # adding this last to see if it'll cope
        actual.add_child("dirA", Expiry.Directory, 4096)

        self.assertEqual(hash(expected), hash(actual))

    def test_file_size(self):
        files = FileNode(Expiry.Directory, 0)
        files.children = {
            "fileA": FileNode(Expiry.InDate, 17000),
            "fileB": FileNode(Expiry.Expired, 24000),
            "dirA": FileNode(Expiry.Directory, 4096)
        }
        files.children["dirA"].children = {
            "fileA": FileNode(Expiry.InDate, 48000),
            "fileB": FileNode(Expiry.Expired, 70000)
        }

        self.assertEqual(
            (files.size, files.children["dirA"].size), (163096, 122096))


class TestFiletypeCalculations(unittest.TestCase):
    def setUp(self) -> None:
        self.file_root = FileNode(Expiry.Directory, 0)
        self.file_root.children = {
            "dirA": FileNode(Expiry.Directory, 4096),
            "dirB": FileNode(Expiry.Directory, 4096),
            "fileA.py": FileNode(Expiry.Expired, 12000),
            "fileB.py": FileNode(Expiry.InDate, 12000),
            "fileC.py": FileNode(Expiry.Expired, 14000),
            "fileA.vcf": FileNode(Expiry.Expired, 100000),
            "fileB.vcf": FileNode(Expiry.InDate, 100000),
            "fileC.vcf": FileNode(Expiry.Expired, 150000)
        }
        self.file_root.children["dirA"].children = {
            "fileAA.py": FileNode(Expiry.Expired, 12000),
            "fileBB.py": FileNode(Expiry.InDate, 12000),
            "fileCC.py": FileNode(Expiry.Expired, 14000),
            "fileAA.vcf": FileNode(Expiry.Expired, 100000),
            "fileBB.vcf": FileNode(Expiry.InDate, 100000),
            "fileCC.vcf": FileNode(Expiry.Expired, 150000)
        }
        self.file_root.children["dirB"].children = {
            "fileAAA.py": FileNode(Expiry.Expired, 12000),
            "fileBBB.py": FileNode(Expiry.InDate, 12000),
            "fileCCC.py": FileNode(Expiry.Expired, 14000),
            "fileAAA.vcf": FileNode(Expiry.Expired, 100000),
            "fileBBB.vcf": FileNode(Expiry.InDate, 100000),
            "fileCCC.vcf": FileNode(Expiry.Expired, 150000)
        }

        """
        Expectations:
                Num Files   Size
        .py     6           78000
        .vcf    6           750000
        """

    def test_file_count(self):
        expected = {".py": 6, ".vcf": 6}
        actual = {k: v[0] for (k, v) in dict(self.file_root.filetypes).items()}
        self.assertEqual(expected, actual)

    def test_file_size(self):
        expected = {".py": 78000, ".vcf": 750000}
        actual = {k: v[1] for (k, v) in dict(self.file_root.filetypes).items()}
        self.assertEqual(expected, actual)


class TestFileTreeToArrays(unittest.TestCase):
    def setUp(self) -> None:
        self.file_root = FileNode(Expiry.Directory, 0)
        self.file_root.children = {
            "dirA": FileNode(Expiry.Directory, 4096),
            "dirB": FileNode(Expiry.Directory, 4096),
            "dirC": FileNode(Expiry.Directory, 4096),
            "dirD": FileNode(Expiry.Directory, 4096),
            "fileA.py": FileNode(Expiry.Expired, 12000),
            "fileB.py": FileNode(Expiry.InDate, 12000),
            "fileC.py": FileNode(Expiry.Expired, 14000),
            "fileA.vcf": FileNode(Expiry.Expired, 100000),
            "fileB.vcf": FileNode(Expiry.InDate, 100000),
            "fileC.vcf": FileNode(Expiry.Expired, 150000)
        }
        self.file_root.children["dirA"].children = {
            "fileAA.py": FileNode(Expiry.Expired, 12000),
            "fileBB.py": FileNode(Expiry.InDate, 12000),
            "fileCC.py": FileNode(Expiry.Expired, 14000),
            "fileAA.vcf": FileNode(Expiry.Expired, 100000),
            "fileBB.vcf": FileNode(Expiry.InDate, 100000),
            "fileCC.vcf": FileNode(Expiry.Expired, 150000)
        }
        self.file_root.children["dirB"].children = {
            "fileAAA.py": FileNode(Expiry.Expired, 12000),
            "fileBBB.py": FileNode(Expiry.InDate, 12000),
            "fileCCC.py": FileNode(Expiry.Expired, 14000),
            "fileAAA.vcf": FileNode(Expiry.Expired, 100000),
            "fileBBB.vcf": FileNode(Expiry.InDate, 100000),
            "fileCCC.vcf": FileNode(Expiry.Expired, 150000)
        }
        self.file_root.children["dirC"].children = {
            "fileA": FileNode(Expiry.Expired, 10000),
            "fileB": FileNode(Expiry.Expired, 10000)
        }
        self.file_root.children["dirD"].children = {
            "fileA": FileNode(Expiry.InDate, 10000),
            "fileB": FileNode(Expiry.InDate, 10000)
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
