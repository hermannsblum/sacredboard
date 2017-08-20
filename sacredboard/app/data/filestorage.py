"""Implements backend storage interface for sacred's file store."""

import datetime
import os
import json
import hashlib

from sacredboard.app.data.datastorage import Cursor, DataStorage

CONFIG_JSON = "config.json"
RUN_JSON = "run.json"
INFO_JSON = "info.json"

def _path_to_config(path):
    return os.path.join(path, CONFIG_JSON)


def _path_to_info(path):
    return os.path.join(path, INFO_JSON)


def _path_to_run(path):
    return os.path.join(path, RUN_JSON)


def _read_json(path_to_json):
    with open(path_to_json) as f:
        return json.load(f)


def _create_run(run_id, runjson, configjson, infojson):
    runjson["_id"] = run_id
    runjson["config"] = configjson
    runjson["info"] = infojson

    # TODO probably want a smarter way of detecting
    # which values have type "time."
    for k in ["start_time", "stop_time", "heartbeat"]:
        runjson[k] = datetime.datetime.strptime(runjson[k],
                                                '%Y-%m-%dT%H:%M:%S.%f')
    return runjson


class FileStoreCursor(Cursor):
    """Implements the cursor for file stores."""

    def __init__(self, count, iterable):
        """Initialize FileStoreCursor with a given iterable."""
        self.iterable = iterable
        self._count = count

    def count(self):
        """
        Return the number of runs in this query.

        :return: int
        """
        return self._count

    def __iter__(self):
        """Iterate over runs."""
        return iter(self.iterable)


class FileStorage(DataStorage):

    """Object to interface with one of sacred's file stores."""


    def __init__(self, path_to_dir):
        """Initialize file storage run accessor."""
        super().__init__()
        self.path_to_dir = os.path.expanduser(path_to_dir)
        self.hash_to_runpath = None

    def get_run(self, run_id):
        """
        Return the run associated with a particular `run_id`.

        :param run_id:
        :return: dict
        :raises FileNotFoundError
        """
        if self.hash_to_runpath is None:
            _scan_for_runs()

        if run_id in self.hash_to_runpath:
            run_path = self.hash_to_runpath[run_id]
            run, config, info = _get_run_data(self, run_path)
            return _create_run(run_id, run, config, info)
        else:
            return None

    def _get_run_data(self,run_path):
        config = _read_json(_path_to_config(run_path))
        run = _read_json(_path_to_run(run_path))
        info = _read_json(_path_to_info(run_path))
        return run, config, info

    def _scan_for_runs(self):
        self.hash_to_runpath = {}
        # Scan trough directories recursively
        all_dirs = [dir[0] for dir in os.walk(self.path_to_dir)]

        for run_dir in all_dirs:
            run_id = hashlib.sha1(run_dir.encode("UTF-8")).hexdigest()[:7]
            try:
                self._get_run_data(run_dir)
                self.hash_to_runpath[run_id] = run_dir
            except FileNotFoundError:
                # An incomplete experiment is a corrupt experiment.
                # Skip it for now.
                # TODO
                pass
            except Exception:
                # Skip all exeptions
                pass

        self.hash_to_runpath[]

    def get_runs(self, sort_by=None, sort_direction=None,
                 start=0, limit=None, query={"type": "and", "filters": []}):
        """
        Return all runs in the file store.

        If a run is corrupt, e.g. missing files, it is skipped.

        :param sort_by: NotImplemented
        :param sort_direction:  NotImplemented
        :param start: NotImplemented
        :param limit: NotImplemented
        :param query: NotImplemented
        :return: FileStoreCursor
        """

        self._scan_for_runs()

        def run_iterator():
            for run_id in self.hash_to_runpath.keys():
                try:
                    yield self.get_run(run_id)
                except FileNotFoundError:
                    # An incomplete experiment is a corrupt experiment.
                    # Skip it for now.
                    # TODO
                    pass
                except NotADirectoryError:
                    # Is thrown on Macs if a .DS_STORE folder is found
                    # Skip it
                    pass

        count = len(self.hash_to_runpath.keys())
        return FileStoreCursor(count, run_iterator())
