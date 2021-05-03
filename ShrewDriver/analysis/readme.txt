Contains the analysis code that turns sensor readings into interpretable data (sets of trials, performances, etc.)

Also, stores analysis results in "db" files, which are like very lightweight databases.

The db files are a python format, called a "shelf". See documentation for the python "shelve" library.

Shelves store key-value pairs, and you can load in just part of a file.
Unlike a proper database, there's no locking or joining or anything cool like that.
But they're built into python (yay no dependencies) and they get the job done well enough.

The db files get read in order to make the pretty graphs over in ui_graphs.


