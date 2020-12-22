#!/usr/bin/env python3

# An open source simple UCI engine that plays randomly.
#
# UCI chess engines require a GUI interface to play.
#
# There is optional filtering in addition to pure random play.
#
# The python-chess Python chess library is required. It can be installed by "pip":
#   "pip install chess"

import chess
import hashlib
import random
import struct
import sys

# Options
opt_deterministic = False
opt_filter        = None
opt_promotion     = None
opt_seed          = None

# Global board state
board = chess.Board()

# Keep reading lines/commands from standard input until told to quit.
for line in sys.stdin:
    line = line.strip()
    tokens = line.split()
    if len(tokens) == 0:
        continue
    command = tokens[0]
    args = tokens[1:]

    # Commands in alphabetical order.
    if command == "go":
        # A deterministic sorted order of move stings in "e2e4" form.
        moves = [m.uci() for m in board.legal_moves]
        moves.sort()

        # If a piece was specified (length 5) only allow promotions to that.
        if opt_promotion:
            moves = [m for m in moves if (len(m) == 4) or (m[4] == opt_promotion)]

        # Each filter sets one of the following three variables.
        filtered_move  = None # A single move that is definitely in "moves".
        filtered_moves = None # A subset of moves that are definitely in "moves".
        proposed_move  = None # A single move that may be in "moves".

        # If there is no filter then "moves" will be selected from as is.
        if opt_filter:
            try:
                # "lm" is the last move.
                lm = board.peek().uci()
            except IndexError:
                # This is probably the first move.
                lm = None

            # Each filter listed in alphabetical order. To try a new filter
            # idea add it here. For example, if it is called "my-filter":
            #    elif opt_filter == "my-filter":
            #        # Update one of filtered_move, filtered_moves or
            #        # proposed_move here (see above).
            if opt_filter == "first":
                # The first move alphabetically ("a2a3", for example).
                filtered_move = moves[0]
            elif opt_filter == "mirror":
                # Mirror the opponent's last move.
                if lm:
                    proposed_move = lm[0] + chr(105 - ord(lm[1])) + \
                                    lm[2] + chr(105 - ord(lm[3])) + lm[4:]
            elif opt_filter == "last":
                filtered_move = moves[len(moves) - 1]
            elif opt_filter == "rotate":
                # Rotate the opponent's last move around the vertical axis.
                if lm:
                    proposed_move = chr(201 - ord(lm[0])) + chr(105 - ord(lm[1])) + \
                                    chr(201 - ord(lm[2])) + chr(105 - ord(lm[3])) + lm[4:]
            else:
                # Assume the filter is a piece. Only moves that move the
                # specified piece will remain.
                piece = opt_filter[0]
                filtered_moves = [move for move in moves \
                    if board.piece_at(ord(move[0]) - 97 + \
                                 8 * (ord(move[1]) - 49)).symbol() == piece]

            if filtered_move:
                # Just one move that is certainly valid.
                moves = [filtered_move]
            if filtered_moves and (len(filtered_moves) > 0):
                # One or move filtered moves.
                moves = filtered_moves
            elif proposed_move and (proposed_move in moves):
                # A proposed move that was found to be be valid.
                moves = [proposed_move]

        if len(moves) == 1:
            # If there is only one move then it's easy to pick.
            move = moves[0]
        else:
            # If deterministic then choose based on the board state, random otherwise.
            if opt_deterministic:
                # Get the SHA-1 of the FEN (with a possible seed appended), take
                # the first 4 bytes, convert to an unsigned integer, and mod
                # that into the list of moves. random.seed() may have been
                # sufficient, but this guarantees that the move is only a function
                # of the board state.
                if opt_seed:
                    board_str = board.fen() + " " + opt_seed
                else:
                    board_str = board.fen()
                hash_bytes = hashlib.sha1(bytes(board_str, "UTF-8")).digest()
                hash_num, = struct.unpack("I", hash_bytes[0:4])
                move_index = hash_num % len(moves)
            else:
                # Random. Different with each run. The order of moves does not
                # matter in this case.
                move_index = random.randrange(len(moves))
            move = moves[move_index]
        board.push_uci(move)
        # The move output. Note that the possible requested ponder information
        # is never included, since there is no pondering information, but the
        # GUI does not seem to mind.
        print("bestmove " + move)
    elif command == "isready":
        print("readyok")
    elif command == "position":
        try:
            moves_index = args.index("moves")
        except ValueError:
            # No moves. Pretend "moves" is past the end, with no moves following.
            moves_index = len(args)
        pos_type = args[0]
        if pos_type == "startpos":
            # Initial board.
            fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        elif pos_type == "fen":
            # Join the remaining arguments to produce the original FEN string.
            fen = " ".join(args[1:moves_index])
        else:
            print("Unknown position type \"" + pos_type + "\" for line \"" + line +"\"")
            continue
        board.set_fen(fen)
        # moves_index + 1 may be past the end of the array which means no moves.
        for move in args[moves_index + 1:]:
            board.push_uci(move)
    elif command == "print":
        # A non-standard UCI command that is quite helpful.
        print(board)
    elif command == "quit":
        # The only way this top level loop should exit.
        sys.exit(0)
    elif command == "setoption":
        if len(args) < 4:
            print("setoption has syntax \"setoption name <name> value <value\"")
            continue
        opt_name = args[1].lower()
        opt_value = args[3].lower()
        opt_value = None if (opt_value == "none") or (len(opt_value) == 0) else opt_value
        if opt_name == "deterministic":
            # Start with t or T for True, False otherwise.
            opt_deterministic = (len(opt_value) >= 1) and (opt_value[0] == "t")
        elif opt_name == "filter":
            opt_filter = opt_value
        elif opt_name == "promotion":
            # For pieces just take the first character (except for "knight").
            # This could have better validation.
            opt_promotion = None if (opt_value == None) or \
                                    (opt_value == "random") else \
                                    ("n" if opt_value == "knight" else opt_value[0])
        elif opt_name == "seed":
            opt_seed = None if opt_value == None else opt_value
        else:
            print("Unknown option: " + line)
    elif command == "stop":
        # No thinking to stop
        pass
    elif command == "uci":
        print("id name random-uci 0.9.0")
        print("id author Steven Elliott")
        print()
        print("option name Deterministic type check default false")
        # Make sure to add any new filter types here as well.
        print("option name Filter type combo default none var none var first var last var mirror var rotate")
        print("option name Promotion type combo default random var random var knight var bishop var rook var queen")
        print("option name Seed type string default none")
        print("uciok")
    elif command == "ucinewgame":
        # Reset to the initial board.
        board.reset()
    else:
        print("Unknown command: " + line)

    # If this is omitted commands may linger in the output buffer.
    sys.stdout.flush()
