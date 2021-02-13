# random-uci

## Overview

An open source simple UCI engine that moves randomly.

## UCI Options

In addition to moving randomly there are UCI options that alter its behavior. They are:

### Deterministic

If set to **true** then the random move is a function of the board state, so the same move will always be made in the same situation.

### Filter

A subset of the moves may be chosen. If the filter fails to find a valid move then it reverts to randomly choosing from all possible moves. Valid values are:

* **none**
  * Apply no filter so that all moves are considered. This is the default.
* **first**
  * Play the first move after sorting the move alphabetically. This is "a2a3" for the first move.
* **last**
  * Play the last move after sorting the move alphabetically. This is "h2h4" for the first move.
* **mirror**
  * Mirror the opponent's move across the boundary between the fourth and fifth row. Move "e2e4" becomes "e7e5", for example.
* **rotate**
  * Rotate the opponent's move 180° around the vertical axis. Move "e2e4" becomes "d7d5", for example.
* **syzygy**
  * Use the specified syzygy tablespace to pick the best move when in the tablespace.

### Promotion

The action to take when a pawn is promoted. Valid values are:

* **random**
  * Promote to a random piece. This is the default.
* **knight**
  * Promote to a knight.
* **bishop**
  * Promote to a bishop.
* **rook**
  * Promote to a rook.
* **queen**
  * Promote to a queen.

### Seed

When **Deterministic** is set to **true** this allows an alternate set of random moves to be played. All strings are valid values. All values result in a complete different set of random moves.

### SyzygyPath

Path to a syzygy tablespace. "/mnt/data/chess/syzygy/3-4-5", for example.

## Installation

The following dependencies are required:

* Python 3
* python-chess

**python-chess** can be installed via **pip**:
```shell
pip install chess
```

Once the dependencies have been satisfied the [ZIP file](https://github.com/selliott512/random-uci/archive/v0.9.2.zip) can be expanded to a directory of your choice. For example, if you downloaded the ZIP file to **~/Downloads**, but you wish to install it to **/opt** then:
```shell
sudo unzip -d /opt ~/Downloads/random-uci-0.9.2.zip
```
Or use the GUI interface on your operating system to expand the ZIP file wherever you want.

If your chess GUI supports UCI then you only have to refer to the full path to **random-uci.py**, which in the above example is ***/opt/random-uci-0.9.2/bin/random-uci.py***. Some chess GUIs, such as Xboard and WinBoard, require Polyglot to translate from the Xboard protocol to UCI. In that case see the included **polyglot/random-uci.ini** for an example configuration file.

## License

GPL version 2.0 or later as per the included **LICENSE** file.
