# FIXME: This works but not in github workflows?
#
# from time import sleep
# from pathlib import Path
# from dooit.api.manager import Manager
# from dooit.api.project import Project
# from tests.test_core.core_base import CoreTestBase
# import tempfile
#
#
# class TestSync(CoreTestBase):
#     def test_sync(self):
#         # create a temporary folder
#         temp_folder = tempfile.TemporaryDirectory()
#         temp_db = Path(temp_folder.name) / "dooit1.db"
#         TEMP_CONN = f"sqlite:////{temp_db}"
#
#         manager1 = Manager()
#         manager2 = Manager()
#
#         manager1.connect(TEMP_CONN)
#         manager2.connect(TEMP_CONN)
#
#         p = Project(description="test")
#         manager1.save(p)
#
#         self.assertFalse(manager1.has_changed())
#         sleep(1)  # ensuring the times dont match
#
#         self.assertTrue(manager2.has_changed())
#         temp_folder.cleanup()
