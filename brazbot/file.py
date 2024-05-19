class File:
    def __init__(self, file_path):
        self.file_path = file_path

    def to_dict(self):
        return {
            "file": open(self.file_path, 'rb')
        }
