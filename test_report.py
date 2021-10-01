import unittest
from report import FileNode, Expiry


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
