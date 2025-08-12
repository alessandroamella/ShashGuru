#This file is part of ShashGuru, a chess analyzer that takes a FEN, asks a UCI chess engine to analyse it and then outputs a natural language analysis made by an LLM.
#Copyright (C) 2025  Alessandro Libralesso
#
#This program is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <https://www.gnu.org/licenses/>.


import subprocess
import os
import chess
import logging
import threading
import queue
import time
import atexit
from engineCache import get_cache

logging.basicConfig(level=logging.INFO)
engine_name_NNUE = 'shashchess'
engine_name_HUMAN = 'alexander'
engine_path_NNUE = f".\\executables\\{engine_name_NNUE}.exe" if os.name == 'nt' else f"./executables/{engine_name_NNUE}"
engine_path_HUMAN = f".\\executables\\{engine_name_HUMAN}.exe" if os.name == 'nt' else f"./executables/{engine_name_HUMAN}"

class EnginePool:
    """
    Manages a pool of pre-initialized UCI chess engines for better performance.
    """
    def __init__(self, engine_path, pool_size=16):
        self.engine_path = engine_path
        self.pool_size = pool_size
        self.available_engines = queue.Queue()
        self.lock = threading.Lock()
        self.shutdown = False
        self._initialize_pool()
        
    def _initialize_pool(self):
        """Initialize all engines in the pool."""
        logging.info(f"Initializing engine pool with {self.pool_size} engines for {self.engine_path}")
        for i in range(self.pool_size):
            try:
                engine = self._create_engine()
                if engine:
                    self.available_engines.put(engine)
                    logging.info(f"Engine {i+1}/{self.pool_size} initialized successfully")
            except Exception as e:
                logging.error(f"Failed to initialize engine {i+1}: {e}")
                
    def _create_engine(self):
        """Create and initialize a single engine."""
        try:
            logging.info(f"Creating new engine instance from {self.engine_path}")
            engine = subprocess.Popen([self.engine_path],
                                     stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE,
                                     universal_newlines=True)
            
            # Initialize UCI protocol
            engine.stdin.write('uci\n')
            engine.stdin.flush()


            # Send isready and wait for readyok
            engine.stdin.write('isready\n')
            engine.stdin.flush()

            return engine
            
        except Exception as e:
            logging.error(f"Failed to create engine: {e}")
            return None
            
    def get_engine(self, timeout=30):
        """Get an available engine from the pool."""
        if self.shutdown:
            return None
            
        try:
            engine = self.available_engines.get(timeout=timeout)
            # Test if engine is still alive
            if engine.poll() is not None:
                # Engine died, create a new one
                logging.warning("Engine died, creating replacement")
                new_engine = self._create_engine()
                return new_engine if new_engine else None
            return engine
        except queue.Empty:
            logging.warning("No engines available in pool, creating temporary engine")
            return self._create_engine()
            
    def return_engine(self, engine):
        """Return an engine to the pool."""
        if self.shutdown or engine.poll() is not None:
            # Don't return dead engines or during shutdown
            self._cleanup_engine(engine)
            return
            
        try:
            # Reset engine state
            engine.stdin.write('ucinewgame\n')
            engine.stdin.flush()
            engine.stdin.write('isready\n')
            engine.stdin.flush()
            
            # Wait for readyok with timeout
            start_time = time.time()
            while time.time() - start_time < 5:
                output = engine.stdout.readline().strip()
                if output == 'readyok':
                    self.available_engines.put(engine)
                    return
                    
            # Timeout - engine is unresponsive
            logging.warning("Engine unresponsive, discarding")
            self._cleanup_engine(engine)
            
        except Exception as e:
            logging.error(f"Error returning engine to pool: {e}")
            self._cleanup_engine(engine)
            
    def _cleanup_engine(self, engine):
        """Safely cleanup an engine."""
        try:
            if engine.poll() is None:
                engine.stdin.write('quit\n')
                engine.stdin.flush()
                engine.wait(timeout=5)
        except Exception:
            try:
                engine.terminate()
                engine.wait(timeout=5)
            except Exception:
                engine.kill()
                
    def shutdown_pool(self):
        """Shutdown all engines in the pool."""
        self.shutdown = True
        logging.info("Shutting down engine pool")
        
        engines_to_cleanup = []
        while not self.available_engines.empty():
            try:
                engine = self.available_engines.get_nowait()
                engines_to_cleanup.append(engine)
            except queue.Empty:
                break
                
        for engine in engines_to_cleanup:
            self._cleanup_engine(engine)

# Global engine pools
_nnue_pool = None
_human_pool = None
_pool_lock = threading.Lock()

def _initialize_nnue_pool():
    """Initialize NNUE engine pool at startup."""
    global _nnue_pool
    
    logging.info("Initializing NNUE engine pool at startup...")
    try:
        _nnue_pool = EnginePool(engine_path_NNUE, pool_size=16)
        logging.info("NNUE engine pool initialized successfully at startup")
    except Exception as e:
        logging.error(f"Failed to initialize NNUE engine pool at startup: {e}")
        _nnue_pool = None

def _get_engine_pool(engine_path):
    """Get or create engine pool for the given path."""
    global _nnue_pool, _human_pool
    
    with _pool_lock:
        if engine_path == engine_path_NNUE:
            if _nnue_pool is None:
                logging.warning("NNUE pool not initialized at startup, creating now...")
                _nnue_pool = EnginePool(engine_path, pool_size=16)
            return _nnue_pool
        elif engine_path == engine_path_HUMAN:
            if _human_pool is None:
                logging.info("Lazy initializing HUMAN engine pool...")
                _human_pool = EnginePool(engine_path, pool_size=16)
            return _human_pool
        else:
            # For other engine paths, create a temporary pool
            return EnginePool(engine_path, pool_size=4)

def _cleanup_pools():
    """Cleanup function called on exit."""
    global _nnue_pool, _human_pool
    if _nnue_pool:
        _nnue_pool.shutdown_pool()
    if _human_pool:
        _human_pool.shutdown_pool()

# Register cleanup function
atexit.register(_cleanup_pools)

# Initialize NNUE engine pool at startup (HUMAN pool is lazy-loaded)
_initialize_nnue_pool()

def get_pool_stats():
    """Get statistics about the engine pools."""
    stats = {}
    if _nnue_pool:
        stats['NNUE'] = {
            'initialized': True,
            'pool_size': _nnue_pool.pool_size,
            'available': _nnue_pool.available_engines.qsize(),
            'busy': _nnue_pool.pool_size - _nnue_pool.available_engines.qsize()
        }
    else:
        stats['NNUE'] = {'initialized': False, 'reason': 'Failed to initialize at startup'}
        
    if _human_pool:
        stats['HUMAN'] = {
            'initialized': True,
            'pool_size': _human_pool.pool_size,
            'available': _human_pool.available_engines.qsize(),
            'busy': _human_pool.pool_size - _human_pool.available_engines.qsize()
        }
    else:
        stats['HUMAN'] = {'initialized': False, 'reason': 'Lazy initialization - not yet needed'}
    return stats

def call_engine(fen, depth, engine_path=engine_path_NNUE, lines=3):
    """
    Call chess engine for analysis with Redis caching and engine pooling.
    
    Args:
        fen: Chess position in FEN notation
        depth: Analysis depth
        engine_path: Path to chess engine executable
        lines: Number of analysis lines (MultiPV)
        
    Returns:
        Tuple of (bestmoves, ponder)
    """
    # Try to get from cache first
    cache = get_cache()
    cached_result = cache.get_cached_analysis(fen, depth, lines)
    if cached_result:
        return cached_result
    
    # Cache miss - compute analysis
    logging.info(f"Computing engine analysis for FEN: {fen}, depth: {depth}, lines: {lines}")
    
    # Get engine from pool
    pool = _get_engine_pool(engine_path)
    engine = pool.get_engine()
    
    if engine is None:
        logging.error("Failed to get engine from pool")
        return [], None
    
    try:
        # Set position and options
        engine.stdin.write(f'position fen {fen}\n')
        engine.stdin.flush()
        engine.stdin.write(f'setoption name MultiPV value {lines}\n')
        engine.stdin.flush()
        engine.stdin.write(f'go depth {depth}\n')
        engine.stdin.flush()

        bestmoves = []
        ponder = None
        logging.info("ENGINE OUTPUT:\n")
        while True:
            output = engine.stdout.readline().strip()
            logging.info(f"{output}")
            if output.startswith(f"info depth {depth}") and "multipv" in output:
                parts = output.split()
                try:
                    mv_idx = parts.index("multipv") + 1
                    pv_idx = parts.index("pv") + 1
                    
                    # Extract the full principal variation (all moves in the line)
                    pv_moves = []
                    for i in range(pv_idx, len(parts)):
                        # Stop at the next engine info keyword or end of line
                        if parts[i] in ['depth', 'seldepth', 'time', 'nodes', 'score', 'multipv', 'wdl']:
                            break
                        pv_moves.append(parts[i])
                    
                    first_move = pv_moves[0] if pv_moves else None

                    # Get score
                    score = None
                    mate = None
                    if "score" in parts:
                        score_idx = parts.index("score")
                        if parts[score_idx + 1] == "cp":
                            score = int(parts[score_idx + 2])
                        elif parts[score_idx + 1] == "mate":
                            mate = int(parts[score_idx + 2])

                    # MODIFIED: Extract WDL if available
                    winprob = None
                    w = None
                    d = None
                    l = None
                    if "wdl" in parts:
                        wdl_idx = parts.index("wdl") + 1
                        w = int(parts[wdl_idx])
                        d = int(parts[wdl_idx + 1])
                        l = int(parts[wdl_idx + 2])
                        winprob = (w +(d/2))/10

                    bestmoves.insert(int(parts[mv_idx]) - 1, {
                        'move': first_move,
                        'pv_moves': pv_moves,  # Full principal variation
                        'score': score,
                        'mate': mate,
                        'w': w,
                        'd': d,
                        'l': l,
                        'winprob': winprob,
                    })
                    
                except Exception as e:
                    print("Parse error:", e)
                    continue

            elif output.startswith("bestmove"):
                parts = output.split()
                if len(parts) >= 4:
                    ponder = parts[3]
                break

        logging.info("BESTMOVES: %s", bestmoves)
        
        # Store result in cache
        cache.store_analysis(fen, depth, lines, bestmoves, ponder)
        
        return bestmoves, ponder
        
    except Exception as e:
        logging.error(f"Error during engine analysis: {e}")
        return [], None
        
    finally:
        # Return engine to pool
        pool.return_engine(engine)


def apply_move_to_fen(fen, move_uci):
    """
    Uses python-chess to apply a UCI move string to a FEN.
    Handles promotions, castling, en passant, clock updates.
    """
    board = chess.Board(fen)
    move = chess.Move.from_uci(move_uci)

    if move not in board.legal_moves:
        raise ValueError(f"Illegal move '{move_uci}' for given FEN")

    board.push(move)
    return board.fen()
# Evaluate specific move from a FEN
def eval_move(fen, move, depth, engine_path):
    try:
        new_fen = apply_move_to_fen(fen, move)
        evals, _ = call_engine(new_fen, depth, engine_path, lines=1)
        return evals[0] if evals else None
    except Exception as e:
        print(f"Error evaluating move {move}: {e}")
        return None

# Master function
def engines(fen, depth):
    bestmovesNNUE, ponderNNUE = call_engine(fen, depth, engine_path_NNUE, lines=3)
    bestmovesHUMAN, ponderHUMAN = call_engine(fen, depth, engine_path_HUMAN, lines=3)

    human_move = bestmovesHUMAN[0]['move']
    nnue_eval_of_human = eval_move(fen, human_move, depth, engine_path_NNUE)

    nnue_move = bestmovesNNUE[0]['move']
    human_eval_of_nnue = eval_move(fen, nnue_move, depth, engine_path_HUMAN)

    nnue_eval_of_human_ponder = eval_move(fen, ponderHUMAN, depth, engine_path_NNUE) if ponderHUMAN else None
    human_eval_of_nnue_ponder = eval_move(fen, ponderNNUE, depth, engine_path_HUMAN) if ponderNNUE else None

    return {
        'NNUE': {
            'top_moves': bestmovesNNUE,
            'eval_human_move': nnue_eval_of_human,
            'eval_human_ponder': nnue_eval_of_human_ponder
        },
        'HUMAN': {
            'top_moves': bestmovesHUMAN,
            'eval_nnue_move': human_eval_of_nnue,
            'eval_nnue_ponder': human_eval_of_nnue_ponder
        }
    }