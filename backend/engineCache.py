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

import redis
import json
import logging
import os
from typing import Dict, List, Optional, Tuple, Any

class EngineCache:
    """
    Redis-based cache for engine analysis results.
    Cache key format: {fen}_{lines}
    Cache value format: {depth: analysis_data}
    """
    
    def __init__(self, host=None, port=None, db=0):
        """Initialize Redis connection."""
        # Use environment variables if available, otherwise defaults
        if host is None:
            host = os.getenv('REDIS_HOST', 'redis_cache')
        if port is None:
            port = int(os.getenv('REDIS_PORT', 6379))
            
        try:
            self.redis_client = redis.Redis(
                host=host, 
                port=port, 
                db=db, 
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            logging.info(f"Connected to Redis at {host}:{port}")
        except redis.ConnectionError as e:
            logging.warning(f"Could not connect to Redis: {e}")
            self.redis_client = None
        except Exception as e:
            logging.warning(f"Redis connection error: {e}")
            self.redis_client = None
    
    def _create_cache_key(self, fen: str, lines: int) -> str:
        """Create cache key from FEN and lines."""
        return f"{fen}_{lines}"
    
    def get_cached_analysis(self, fen: str, depth: int, lines: int) -> Optional[Tuple[List[Dict], Any]]:
        """
        Get cached analysis if available and depth is sufficient.
        
        Args:
            fen: Chess position in FEN notation
            depth: Requested analysis depth
            lines: Number of analysis lines requested
            
        Returns:
            Tuple of (bestmoves, ponder) if cache hit with sufficient depth, None otherwise
        """
        if not self.redis_client:
            return None
            
        try:
            cache_key = self._create_cache_key(fen, lines)
            cached_data = self.redis_client.get(cache_key)
            
            if not cached_data:
                logging.debug(f"Cache miss for key: {cache_key}")
                return None
                
            # Parse cached data
            depth_analysis = json.loads(cached_data)
            
            # Find the highest depth that is >= requested depth
            available_depths = [int(d) for d in depth_analysis.keys()]
            suitable_depths = [d for d in available_depths if d >= depth]
            
            if not suitable_depths:
                logging.debug(f"No suitable depth found in cache. Requested: {depth}, Available: {available_depths}")
                return None
                
            # Use the lowest suitable depth (most efficient)
            best_depth = min(suitable_depths)
            analysis = depth_analysis[str(best_depth)]
            
            logging.info(f"Cache hit for {cache_key} at depth {best_depth} (requested: {depth})")
            return analysis['bestmoves'], analysis['ponder']
            
        except (json.JSONDecodeError, KeyError, redis.RedisError) as e:
            logging.warning(f"Error retrieving from cache: {e}")
            return None
    
    def store_analysis(self, fen: str, depth: int, lines: int, bestmoves: List[Dict], ponder: Any):
        """
        Store analysis result in cache.
        
        Args:
            fen: Chess position in FEN notation
            depth: Analysis depth used
            lines: Number of analysis lines
            bestmoves: Analysis results from engine
            ponder: Ponder move from engine
        """
        if not self.redis_client:
            return
            
        try:
            cache_key = self._create_cache_key(fen, lines)
            
            # Get existing cached data or create new
            existing_data = self.redis_client.get(cache_key)
            if existing_data:
                depth_analysis = json.loads(existing_data)
            else:
                depth_analysis = {}
            
            # Store/update analysis for this depth
            depth_analysis[str(depth)] = {
                'bestmoves': bestmoves,
                'ponder': ponder
            }
            
            # Store back to Redis with expiration (1 week)
            self.redis_client.set(
                cache_key,
                json.dumps(depth_analysis)
            )
            
            logging.info(f"Stored analysis in cache: {cache_key} at depth {depth}")
            
        except (json.JSONDecodeError, redis.RedisError) as e:
            logging.warning(f"Error storing to cache: {e}")
    
    def clear_cache(self):
        """Clear all cached analysis."""
        if not self.redis_client:
            return
            
        try:
            self.redis_client.flushdb()
            logging.info("Cache cleared")
        except redis.RedisError as e:
            logging.warning(f"Error clearing cache: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if not self.redis_client:
            return {"error": "Redis not connected"}
            
        try:
            info = self.redis_client.info()
            return {
                "connected": True,
                "used_memory": info.get('used_memory_human', 'N/A'),
                "keyspace_hits": info.get('keyspace_hits', 0),
                "keyspace_misses": info.get('keyspace_misses', 0),
                "total_keys": self.redis_client.dbsize()
            }
        except redis.RedisError as e:
            logging.warning(f"Error getting cache stats: {e}")
            return {"error": str(e)}


# Global cache instance
_cache_instance = None

def get_cache() -> EngineCache:
    """Get or create global cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = EngineCache()
    return _cache_instance
