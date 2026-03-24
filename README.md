# 🚀 Intergalactic Spaceport Terminal

A command-line inventory management system for tracking spaceships, their captains, and cargo at a spaceport. Built with Python and Pydantic for robust data validation.

---

## Features

- **Log new arrivals** — Register incoming ships with captain and cargo details
- **View docked ships** — Display a summary of all ships currently in port
- **Search ships** — Find ships by ID or captain name
- **Remove ships** — Deregister a ship from the terminal
- **Persistent storage** — All data is saved to a local JSON file between sessions

---

## Project Structure

```
.
├── main.py                   # CLI entry point and all menu actions
├── modules.py                # Pydantic data models (Spaceship, Captain, Cargo)
├── requirements.txt          # Project dependencies
└── spaceport_inventory.json  # Auto-generated data file (created on first run)
```

---

## Requirements

- Python 3.10+
- [Pydantic](https://docs.pydantic.dev/) (with email extras)

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Usage

```bash
python main.py
```

You will be presented with the main menu:

```
--- INTERGALACTIC SPACEPORT TERMINAL ---
1. Log New Arrival
2. View Docked Ships
3. Search Ship
4. Remove Ship
5. Exit
```

### 1. Log New Arrival

Registers a new ship by collecting the following information interactively:

**Ship Details**
| Field | Description | Example |
|---|---|---|
| Ship ID | Unique identifier for the vessel | `NCC-1702` |
| Ship Model | Model name of the ship | `Falcon-X` |
| Max Capacity | Maximum cargo weight in kg | `5000` |
| Arrival Date | Date of arrival (must not be in the past) | `2026-04-01` |

**Captain Details**
| Field | Description | Format |
|---|---|---|
| Name | Captain's full name | Any string |
| License Number | Galactic pilot license | `GAL-XXXX-YY` (e.g. `GAL-4821-AB`) |

**Cargo Details**

Add one or more cargo items. Each item requires a name and weight (kg). Press Enter with an empty item name to finish. At least one cargo item is required.

### 2. View Docked Ships

Displays a table of all currently docked ships with their ID, captain name, and total cargo weight.

```
ID              | CAPTAIN         | CARGO
--------------------------------------------------
NCC-1702        | James Kirk      | 1200.0 kg
```

### 3. Search Ship

Search for ships by partial Ship ID or Captain Name (case-insensitive).

### 4. Remove Ship

Remove a ship from the terminal by its Ship ID (case-insensitive match).

### 5. Exit

Shuts down the terminal.

---

## Data Models

### `Captain`
| Field | Type | Validation |
|---|---|---|
| `name` | `str` | Required |
| `license_number` | `str` | Must match pattern `GAL-XXXX-YY` (4 digits, 2 uppercase letters) |

### `Cargo`
| Field | Type | Validation |
|---|---|---|
| `item_name` | `str` | Required |
| `weight_kg` | `float` | Must be greater than 0 |

### `Spaceship`
| Field | Type | Validation |
|---|---|---|
| `ship_id` | `str` | Must be unique across all docked ships |
| `model_name` | `str` | Required |
| `max_capacity_kg` | `float` | Must be greater than 0 |
| `captain` | `Captain` | See Captain model |
| `cargo_hold` | `List[Cargo]` | At least one item required |
| `arrival_date` | `date` | Must not be in the past |

**Cross-field validation:** The total weight of all cargo items must not exceed the ship's `max_capacity_kg`.

---

## Data Persistence

All ship records are saved to `spaceport_inventory.json` in the working directory. The file is updated automatically after every add or remove operation. On startup, the application loads existing records from this file. Corrupted or invalid data in the file is handled gracefully, starting with an empty registry if needed.

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| Duplicate Ship ID | Rejected with a message; no data is modified |
| Invalid license format | Pydantic `ValidationError` is caught and displayed |
| Arrival date in the past | Pydantic `ValidationError` is caught and displayed |
| Cargo overload | Pydantic `ValidationError` is caught and displayed |
| Non-numeric weight/capacity input | `ValueError` is caught and displayed |
| Corrupted JSON file | Warning is shown; terminal starts with an empty registry |