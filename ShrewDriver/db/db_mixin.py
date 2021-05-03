from __future__ import division
import sys
sys.path.append("..")


import os
import shelve

class DbMixin(object):
    """
    Mixin that provides a few common functions to db classes.
    """

    def get(self, animalName):
        """
        You can think of each database as being split across several files named after the corresponding animal.
        So, there's only one History database, but it has several db files ("Bernadette_history.db",
        Chico_history.db, etc.)

        Generally you only want to access one animal at a time, so you call get(animalName)
        to pull in the db file you want.

        Each animal's db file is a dict; keys are session strings, e.g. "2016-06-06_0001".
        """

        if animalName not in self._db:
            dbfile = self.get_path(animalName)
            if not os.path.isfile(dbfile):
                print "Creating db file: " + dbfile
                if not os.path.isdir(os.path.dirname(dbfile)):
                    os.makedirs(os.path.dirname(dbfile))
            with self._lock:
                self._db[animalName] = shelve.open(dbfile, writeback=True, protocol=2)
        return self._db[animalName]


    def sync(self, animalName):
        with self._lock:
            if animalName.capitalize() in self._db:
                self._db[animalName.capitalize()].sync()

    def make(self, analyses):
        """Go through all the provided analysis objects and make / update DB entries."""
        for a in analyses:  # type: sd1_analysis.Analysis
            self.add_entry(a)


    def get_datestr(self, analysis):
        return str(analysis.date.year).zfill(4) + "-" \
            + str(analysis.date.month).zfill(2) + "-" \
            + str(analysis.date.day).zfill(2) + "_" \
            + str(analysis.session).zfill(4)