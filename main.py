import json
from pathlib import Path
from datetime import date
from modules import Spaceship, Captain, Cargo
from pydantic import ValidationError

DATA_FILE = Path("spaceport_inventory.json")


def save_data(ships: list[Spaceship]):
    with open(DATA_FILE, "w") as f:
        json.dump([s.model_dump(mode="json") for s in ships], f, indent=4)


def load_data() -> list[Spaceship]:
    if not DATA_FILE.exists():
        return []

    with open(DATA_FILE, "r") as f:
        try:
            data = json.load(f)
            return [Spaceship(**item) for item in data]
        except json.JSONDecodeError:
            print("⚠️ Warning: Corrupted JSON file. Starting fresh.")
            return []
        except ValidationError as e:
            print("⚠️ Warning: Invalid data in file:", e)
            return []


def add_ship(ships: list[Spaceship]):
    try:
        print("\n[ SHIP DETAILS ]")
        s_id = input("Ship ID (e.g. NCC-1702): ")
        model = input("Ship Model: ")
        cap_max = float(input("Max Capacity (kg): "))

        print("\n[ CAPTAIN DETAILS ]")
        cap_name = input("Captain Name: ")
        cap_lic = input("License (GAL-XXXX-YY): ")
        captain = Captain(name=cap_name, license_number=cap_lic)

        print("\n[ CARGO DETAILS ]")
        cargo_items = []

        while True:
            cargo_name = input("Item Name (or press Enter to finish): ")
            if not cargo_name:
                break

            cargo_weight = float(input("Weight (kg): "))
            cargo_items.append(Cargo(item_name=cargo_name, weight_kg=cargo_weight))

        if not cargo_items:
            print("At least one cargo item is required.")
            return

        new_ship = Spaceship(
            ship_id=s_id,
            model_name=model,
            max_capacity_kg=cap_max,
            captain=captain,
            cargo_hold=cargo_items,
            arrival_date=date.today()
        )

        ships.append(new_ship)
        save_data(ships)
        print("\nShip successfully logged!")

    except ValidationError as e:
        print(f"\nVALIDATION ERROR:\n{e}")
    except ValueError:
        print("\nINPUT ERROR: Invalid numeric value.")


def view_ships(ships: list[Spaceship]):
    if not ships:
        print("\nNo ships docked.")
        return

    print(f"\n{'ID':<15} | {'CAPTAIN':<15} | {'CARGO'}")
    print("-" * 50)

    for s in ships:
        total_w = sum(c.weight_kg for c in s.cargo_hold)
        print(f"{s.ship_id:<15} | {s.captain.name:<15} | {total_w} kg")


def remove_ship(ships: list[Spaceship]):
    ship_id = input("Enter Ship ID to remove: ")

    for s in ships:
        if s.ship_id == ship_id:
            ships.remove(s)
            save_data(ships)
            print("Ship removed.")
            return

    print("Ship not found.")


def search_ship(ships: list[Spaceship]):
    query = input("Search by Ship ID or Captain Name: ").lower()

    results = [
        s for s in ships
        if query in s.ship_id.lower() or query in s.captain.name.lower()
    ]

    if not results:
        print("No matching ships found.")
        return

    print("\n🔍 Search Results:")
    for s in results:
        total_w = sum(c.weight_kg for c in s.cargo_hold)
        print(f"{s.ship_id} | {s.captain.name} | {total_w} kg")


def main():
    ships = load_data()

    while True:
        print("\n--- INTERGALACTIC SPACEPORT TERMINAL ---")
        print("1. Log New Arrival")
        print("2. View Docked Ships")
        print("3. Search Ship")
        print("4. Remove Ship")
        print("5. Exit")

        choice = input("Select command: ")

        if choice == "1":
            add_ship(ships)

        elif choice == "2":
            view_ships(ships)

        elif choice == "3":
            search_ship(ships)

        elif choice == "4":
            remove_ship(ships)

        elif choice == "5":
            print("Shutting down terminal.")
            break

        else:
            print("Invalid option.")


if __name__ == "__main__":
    main()
