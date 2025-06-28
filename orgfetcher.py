from time import sleep
from typing import Any
from orgmunge import Org, Heading

class Fetcher:
    """Fetches data from an external source"""
    data = None
    data_ready = False
    def __init__(self, **kwargs):
        for arg, val in kwargs.items():
            setattr(self, arg, val)
    def fetch(self):
        "Override this"
        self.data_ready = True

class Transformer:
    """Transforms fetched data into orgmunge Heading objects"""
    data = None
    data_ready = False
    todos = Org.get_todos()
    def __init__(self, fetcher: Fetcher, poll_interval: float = 5.0, **kwargs):
        self.poll_interval = poll_interval
        for arg, val in kwargs.items():
            setattr(self, arg, val)
        self.fetcher = fetcher
    def get_data(self):
        "Override this"
        self.fetcher.fetch()
        while (not self.fetcher.data_ready):
            sleep(self.poll_interval)
        self.data = self.fetcher.data
        self.transformed_data = None
    def transform(self, item: Any) -> Heading:
        "Override this. Take a data item and return a heading"
        pass

class Updater:
    """Updates the given file using the data from the transfomer"""
    update_done = False
    def __init__(self, transformer: Transformer, org_file_path: str, **kwargs):
        self.transformer = transformer
        self.fetcher = transformer.fetcher
        self.poll_interval = transformer.poll_interval
        self.org_file_path = org_file_path
        self.todos = self.transformer.todos
        for arg, val in kwargs.items():
            setattr(self, arg, val)
    def _get_data(self):
        self.fetcher.fetch()
        self.transformer.get_data()
        while(not self.transformer.data_ready):
            sleep(self.poll_interval)
    def update_headings(self):
        "Override this"
        if hasattr(self, 'todos'):
            self.org_file = Org(self.org_file_path, todos=self.todos)
        else:
            self.org_file = Org(self.org_file_path)
    def update(self):
        self._get_data()
        self.update_headings()
        self.org_file.write(self.org_file_path)
