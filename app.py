import io
import sys
import tarfile
import importlib.abc
import importlib.machinery

class InMemoryTarImporter(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def __init__(self, disguised_file_path):
        self.modules_code = {}
        self._load_and_extract(disguised_file_path)
        # Register into Python's module search path
        sys.meta_path.insert(0, self)

    def _load_and_extract(self, path):
        with open(path, "rb") as f:
            raw_data = f.read()
        
        # Bulletproof header bypass: locate the gzip magic bytes (\x1f\x8b) 
        # regardless of how large or complex the fake PNG header is.
        gzip_index = raw_data.find(b"\x1f\x8b")
        payload = raw_data[gzip_index:] if gzip_index != -1 else raw_data

        # Unpack the tar.gz entirely in RAM using BytesIO
        with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as tar:
            for member in tar.getmembers():
                if member.isfile() and member.name.endswith(".py"):
                    f_obj = tar.extractfile(member)
                    if f_obj:
                        # Clean module name mapping (strips directories and .py extension)
                        clean_name = member.name.split("/")[-1].replace(".py", "")
                        self.modules_code[clean_name] = f_obj.read().decode("utf-8")

    def find_spec(self, fullname, path, target=None):
        if fullname in self.modules_code:
            return importlib.machinery.ModuleSpec(fullname, self)
        return None

    def create_module(self, spec):
        return None  # Default module creation

    def exec_module(self, module):
        code_str = self.modules_code.get(module.__name__)
        if code_str:
            exec(code_str, module.__dict__)

dep_loader = InMemoryTarImporter("dependencies.png")

