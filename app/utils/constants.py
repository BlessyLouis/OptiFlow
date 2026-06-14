# Order lifecycle stages — order matters for progression tracking
ORDER_STATUSES = [
    "Prescription Verified",
    "Lens Processing",
    "QC",
    "QC Failed",
    "Reorder Generated",
    "Packing",
    "Shipped",
    "Delivered",
    "Cancelled",
]

ACTIVE_STATUSES = [
    "Prescription Verified",
    "Lens Processing",
    "QC",
    "QC Failed",
    "Reorder Generated",
    "Packing",
    "Shipped",
]

LENS_TYPES = [
    "Single Vision",
    "Bifocal",
    "Progressive",
    "Blue Cut",
    "Photochromic",
    "Reading",
]

COATINGS = [
    "Anti-Reflective",
    "UV Protection",
    "Scratch Resistant",
    "Blue Light Block",
    "Hydrophobic",
    "None",
]

LENS_INDEXES = ["1.50", "1.56", "1.60", "1.67", "1.74"]

STORE_LOCATIONS = [
    "Mumbai - Bandra",
    "Mumbai - Andheri",
    "Delhi - Connaught Place",
    "Delhi - Saket",
    "Bangalore - Koramangala",
    "Bangalore - Indiranagar",
    "Chennai - Anna Nagar",
    "Hyderabad - Banjara Hills",
    "Pune - Kothrud",
    "Kolkata - Park Street",
]

DELAY_REASONS = [
    "Lens out of stock",
    "QC failure — power mismatch",
    "QC failure — coating defect",
    "Supplier delay",
    "High-index lens unavailable",
    "Frame procurement pending",
    "Lab processing backlog",
    None,
]

# Risk thresholds for SLA breach probability (0–100)
RISK_LEVELS = {
    "LOW": (0, 40),
    "MEDIUM": (41, 70),
    "HIGH": (71, 100),
}

# SLA hours by lens type — realistic ops benchmarks
SLA_BY_LENS_TYPE = {
    "Single Vision": 48,
    "Bifocal": 72,
    "Progressive": 96,
    "Blue Cut": 60,
    "Photochromic": 72,
    "Reading": 48,
}

LOW_STOCK_THRESHOLD = 20
CRITICAL_STOCK_THRESHOLD = 5
