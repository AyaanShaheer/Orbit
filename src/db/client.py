import time
import logging
from typing import Dict, Any, List, Optional, Tuple
from falkordb import FalkorDB
from src.config import settings

logger = logging.getLogger("orbit.db")

class FalkorDBClient:
    """
    Authoritative FalkorDB client for ORBIT.
    Handles graph connection, Cypher execution, parameter passing, and query profiling.
    """
    def __init__(self, host: str = None, port: int = None, graph_name: str = None):
        self.host = host or settings.falkordb_host
        self.port = port or settings.falkordb_port
        self.graph_name = graph_name or settings.graph_name
        self._client: Optional[FalkorDB] = None
        self._graph = None
        self._is_connected = False
        self._last_error = None
        self.connect()

    def connect(self) -> bool:
        """Attempt to establish connection to FalkorDB."""
        try:
            self._client = FalkorDB(host=self.host, port=self.port)
            self._graph = self._client.select_graph(self.graph_name)
            # Ping to verify
            self._graph.query("RETURN 1 AS ping")
            self._is_connected = True
            self._last_error = None
            logger.info(f"Connected to FalkorDB at {self.host}:{self.port}, graph: {self.graph_name}")
            return True
        except Exception as e:
            self._is_connected = False
            self._last_error = str(e)
            logger.warning(f"FalkorDB connection failed ({self.host}:{self.port}): {e}")
            return False

    @property
    def is_connected(self) -> bool:
        if not self._is_connected:
            # Try reconnecting
            return self.connect()
        return True

    def query(self, cypher: str, params: Optional[Dict[str, Any]] = None) -> Tuple[List[Dict[str, Any]], float]:
        """
        Execute a Cypher query on the authoritative FalkorDB graph.
        Returns a tuple: (list of result row dictionaries, elapsed_time_ms)
        """
        if not self.is_connected:
            raise ConnectionError(f"Cannot execute Cypher query: FalkorDB is not connected. Last error: {self._last_error}")

        start_time = time.perf_counter()
        try:
            res = self._graph.query(cypher, params or {})
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            rows: List[Dict[str, Any]] = []
            if hasattr(res, 'result_set') and res.result_set:
                header = res.header if hasattr(res, 'header') else [f"col_{i}" for i in range(len(res.result_set[0]))]
                # In falkordb-py, header is typically list of [type, name] or strings
                column_names = []
                for h in header:
                    if isinstance(h, (list, tuple)) and len(h) >= 2:
                        column_names.append(str(h[1]))
                    else:
                        column_names.append(str(h))

                for raw_row in res.result_set:
                    row_dict = {}
                    for col_idx, val in enumerate(raw_row):
                        col_name = column_names[col_idx] if col_idx < len(column_names) else f"col_{col_idx}"
                        # If node or relation object, convert to dict
                        if hasattr(val, 'properties'):
                            row_dict[col_name] = val.properties
                            if hasattr(val, 'labels'):
                                row_dict[col_name]["_labels"] = val.labels
                            if hasattr(val, 'id'):
                                row_dict[col_name]["_id"] = val.id
                        else:
                            row_dict[col_name] = val
                    rows.append(row_dict)

            return rows, elapsed_ms
        except Exception as e:
            logger.error(f"Cypher query error: {e} | Query: {cypher} | Params: {params}")
            raise e

    def execute_write(self, cypher: str, params: Optional[Dict[str, Any]] = None) -> float:
        """Execute a write query (CREATE, MERGE, SET, DELETE) and return elapsed ms."""
        _, elapsed_ms = self.query(cypher, params)
        return elapsed_ms

    def drop_graph(self):
        """Reset or drop the entire graph for fresh scenario seeding."""
        if self.is_connected:
            try:
                self._graph.delete()
                self._graph = self._client.select_graph(self.graph_name)
                logger.info(f"Graph '{self.graph_name}' dropped and recreated.")
            except Exception as e:
                logger.warning(f"Could not drop graph: {e}")

# Global singleton client
db_client = FalkorDBClient()
