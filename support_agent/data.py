"""In-memory mock backend. Stands in for the CRM / order system that
an MCP server will expose in Module 4."""

CUSTOMERS = {
    "C001": {"customer_id": "C001", "name": "Ana Lopez", "email": "ana@example.com", "tier": "gold"},
    "C002": {"customer_id": "C002", "name": "Ben Okafor", "email": "ben@example.com", "tier": "standard"},
}

ORDERS = {
    "O1001": {"order_id": "O1001", "customer_id": "C001", "item": "Wireless headphones",
              "total": 129.99, "status": "delivered", "days_since_delivery": 5},
    "O1002": {"order_id": "O1002", "customer_id": "C001", "item": "4K monitor",
              "total": 749.00, "status": "delivered", "days_since_delivery": 12},
    "O1003": {"order_id": "O1003", "customer_id": "C002", "item": "USB-C cable",
              "total": 14.50, "status": "shipped", "days_since_delivery": None},
}

REFUNDS: list[dict] = []   # refunds issued during this process
ESCALATIONS: list[dict] = []  # tickets handed to humans
