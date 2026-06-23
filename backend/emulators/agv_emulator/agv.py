class AGV:
    def __init__(self, agv_id: str, start_row: int, start_col: int):
        self.agv_id = agv_id
        self.row = start_row
        self.col = start_col
        self.status = "IDLE"
        self.route: list[dict] = []

    def dispatch(self, route: list[dict]):
        self.route = route
        self.status = "MOVING"

    def step(self) -> bool:
        """Move one cell along the route. Returns True when route is complete."""
        if not self.route:
            self.status = "IDLE"
            return True
        next_cell = self.route.pop(0)
        self.row = next_cell["row"]
        self.col = next_cell["col"]
        if not self.route:
            self.status = "IDLE"
            return True
        return False

    def to_dict(self) -> dict:
        return {
            "agv_id":          self.agv_id,
            "row":             self.row,
            "col":             self.col,
            "status":          self.status,
            "route_remaining": len(self.route),
        }
