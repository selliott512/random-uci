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
import chess.syzygy
import hashlib
import os
import random
import struct
import time
import sys

# Options
opt_debug         = False
opt_deterministic = False
opt_filter        = None
opt_promotion     = None
opt_seed          = None
opt_syzygypath    = None

# Globals from "chess"
board             = chess.Board()
tablespace        = None

# Globals having to with search
max_depth         = 1
max_score         = 1000000
fen_to_raw_score  = {} # Transposition table
min_ordering      = 1000

# Functions

# Standard alpha beta search. The value of score "score" relative to the root
# node. Best nodes matching the best score may optionally be return by passing
# true for "best_nodes".
def alpha_beta(board, depth, alpha, beta, maximize, get_best):
    # for the top level call make sure we're in the tablespace before doing
    # anything else.
    if depth == max_depth:
        wdl = tablespace.get_wdl(board)
        if wdl is None:
            return None, []

    # Extreme values to start max / min with.
    score = -max_score if maximize else max_score

    # The terminal node case.
    leaf_node = board.is_stalemate() or board.is_checkmate()
    if depth == 0 or leaf_node:
        # How far we've searched so far from root. This is needed to
        # prefer faster wins over slower ones.
        searched_depth = max_depth - depth
        fen = board.fen()
        raw_score = fen_to_raw_score.get(fen)
        if raw_score is None:
            wdl = tablespace.get_wdl(board)
            if wdl is not None:
                dtz = 0 if leaf_node else tablespace.get_dtz(board)
                if dtz is not None:
                    # 1000 was chosen so that wdl will always take precedence over
                    # dtz, but also so that the score produced is always much lower
                    # than max_score.
                    raw_score = 1000 * wdl - dtz
                    fen_to_raw_score[fen] = raw_score
        # A good score could not be found, so we haven't reached the tablespace.
        if raw_score is None:
            return None, []
        # Positive values are good for the root player.
        return (raw_score if maximize else -raw_score) - searched_depth, []

    if get_best:
        move_scores = []
    moves = [move for move in board.legal_moves]
    # Move the best moves to the start of the list. This seems to be harmful in
    # some cases, so it's effectively disabled by setting min_ordering to a
    # high value.
    if depth > min_ordering:
        estimated_score, best_moves = alpha_beta(board, depth - 1, alpha, beta, maximize, True)
        if estimated_score is not None:
            best_moves_set = set(best_moves)
            best_count = 0
            # Make sure the best moves are first.
            for index, move in enumerate(moves):
                if (index > best_count) and (move.uci() in best_moves):
                    temp_move = moves[best_count]
                    moves[best_count] = move
                    moves[index] = temp_move
                    best_count += 1
    for move in moves:
        board.push(move)
        child_score, best_moves = alpha_beta(board, depth - 1, alpha, beta, not maximize, False)
        board.pop()
        if child_score is None:
            # This seems odd since we should be in the tablespace. Maybe a warning?
            continue
        # Normally for alpha-beta pruning a score equal to one of the limits
        # (score equal to alpha or beta) causes the searched_depth to break. However
        # since the best moves (get_best) may be needed by a parent call of
        # this method we need to know whether each node matches the best score,
        # and should be included in the list of moves ultimately returned, or
        # not.
        if maximize:
            score = max(score, child_score)
            alpha = max(score, alpha)
            if alpha > beta:
                break # beta cutoff
        else:
            score = min(score, child_score)
            beta  = min(score, beta)
            if beta < alpha:
                break # alpha cutoff
        if get_best:
            move_scores.append((move, child_score))
    if get_best:
        moves = []
        for move_score in move_scores:
            mv, sc = move_score
            if sc == score:
                moves.append(mv.uci())
        return score, moves
    else:
        return score, []

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
            elif opt_filter == "syzygy":
                # If we were able to pen the table space then attempt an alpha
                # beta search to find the best move.
                if tablespace is not None:
                    before = time.time()
                    alpha_beta_ret = alpha_beta(board, max_depth, -max_score, max_score, True, True)
                    score, filtered_moves = alpha_beta_ret
                    if opt_debug:
                        print("info string syzygy score=" + str(score) + " pid=" + str(os.getpid()))
                        print("info string syzygy search took " + str(int(
                            1000*(time.time() - before))) + " millis for " +
                            board.fen())
            else:
                # Assume the filter is a piece. Only moves that move the
                # specified piece will remain.
                piece = opt_filter[0]
                filtered_moves = [move for move in moves \
                    if board.piece_at(ord(move[0]) - 97 + \
                                 8 * (ord(move[1]) - 49)).symbol() == piece]

            orig_moves_len = len(moves)
            if filtered_move:
                # Just one move that is certainly valid.
                moves = [filtered_move]
            if filtered_moves and (len(filtered_moves) > 0):
                # One or move filtered moves.
                moves = filtered_moves
            elif proposed_move and (proposed_move in moves):
                # A proposed move that was found to be be valid.
                moves = [proposed_move]
            if opt_debug and len(moves) < orig_moves_len:
                print("info string filtered moves=" + str(moves))

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
            print("setoption has syntax \"setoption name <name> value <value>\"")
            continue
        opt_name = args[1].lower()
        # For paths only retain the exact case of the value.
        if "path" in opt_name:
            opt_value = args[3]
        else:
            opt_value = args[3].lower()
        opt_value = None if (opt_value == "none") or (len(opt_value) == 0) else opt_value
        if opt_name == "debug":
            # Start with t or T for True, False otherwise.
            opt_debug = (len(opt_value) >= 1) and (opt_value[0] == "t")
        elif opt_name == "deterministic":
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
        elif opt_name == "syzygypath":
            if os.path.isdir(opt_value):
                if os.path.isfile(opt_value + "/KRvK.rtbw"):
                    tablespace = chess.syzygy.open_tablebase(opt_value)
                else:
                    print("SyzygyPath path \"" + opt_value + "\" does not contain KRvK.rtbw. Ignoring.")
            else:
                print("SyzygyPath path \"" + opt_value + "\" is not a directory. Ignoring.")
        else:
            print("Unknown option: " + line)
    elif command == "stop":
        # No thinking to stop
        pass
    elif command == "uci":
        print("id name random-uci 0.9.2")
        print("id author Steven Elliott")
        print()
        print("option name Debug type check default false")
        print("option name Deterministic type check default false")
        # Make sure to add any new filter types here as well.
        print("option name Filter type combo default none var none var first var last var mirror var rotate var syzygy")
        print("option name Promotion type combo default random var random var knight var bishop var rook var queen")
        print("option name Seed type string default none")
        print("option name SyzygyPath type string default none")
        print("uciok")
    elif command == "ucinewgame":
        # Reset to the initial board.
        board.reset()
        # TODO: Come up with more transposition strategy where the oldest
        # entries are removed. For now hopefully games aren't too long.
        fen_to_raw_score.clear()
    else:
        print("Unknown command: " + line)

    # If this is omitted commands may linger in the output buffer.
    sys.stdout.flush()
