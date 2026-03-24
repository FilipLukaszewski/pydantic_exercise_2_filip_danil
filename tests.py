import json
import unittest
from datetime import date, timedelta
from io import StringIO
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile
import os
from pydantic import ValidationError

from main import save_data, load_data, add_ship, view_ships, remove_ship, search_ship
from modules import Spaceship, Captain, Cargo


# ---------------------------------------------------------------------------
# Base class — overridable default fixtures for all test classes
# ---------------------------------------------------------------------------

class BaseSpaceportTest(unittest.TestCase):
    """
    Provides ready-to-use default objects for every test class.
    Override any attribute in a subclass to customise fixtures locally.
    """

    # --- Captain defaults ---
    default_captain_name: str = "Jean-Luc Picard"
    default_license_number: str = "GAL-1701-JP"

    # --- Cargo defaults ---
    default_cargo_item: str = "Dilithium Crystals"
    default_cargo_weight: float = 200.0

    # --- Ship defaults ---
    default_ship_id: str = "NCC-1701"
    default_model_name: str = "Galaxy-Class"
    default_max_capacity_kg: float = 500.0
    default_arrival_date: date = date.today()

    def make_captain(self, name: str = None, license_number: str = None) -> Captain:
        return Captain(
            name=name or self.default_captain_name,
            license_number=license_number or self.default_license_number,
        )

    def make_cargo(self, item_name: str = None, weight_kg: float = None) -> Cargo:
        return Cargo(
            item_name=item_name or self.default_cargo_item,
            weight_kg=weight_kg if weight_kg is not None else self.default_cargo_weight,
        )

    def make_ship(
        self,
        ship_id: str = None,
        model_name: str = None,
        max_capacity_kg: float = None,
        captain: Captain = None,
        cargo_hold: list = None,
        arrival_date: date = None,
    ) -> Spaceship:
        return Spaceship(
            ship_id=ship_id or self.default_ship_id,
            model_name=model_name or self.default_model_name,
            max_capacity_kg=max_capacity_kg if max_capacity_kg is not None else self.default_max_capacity_kg,
            captain=captain or self.make_captain(),
            cargo_hold=cargo_hold if cargo_hold is not None else [self.make_cargo()],
            arrival_date=arrival_date or self.default_arrival_date,
        )


# ---------------------------------------------------------------------------
# save_data
# ---------------------------------------------------------------------------

class TestSaveData(BaseSpaceportTest):

    def test_creates_file_with_correct_content(self):
        """Saved file should be valid JSON containing the ship's data."""
        ship = self.make_ship()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
            tmp_path = Path(tmp.name)

        try:
            with patch("main.DATA_FILE", tmp_path):
                save_data([ship])

            with open(tmp_path) as f:
                data = json.load(f)

            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["ship_id"], self.default_ship_id)
            self.assertEqual(data[0]["captain"]["name"], self.default_captain_name)
        finally:
            os.unlink(tmp_path)

    def test_saves_multiple_ships(self):
        """All ships in the list should be written to the file."""
        ships = [
            self.make_ship(ship_id="NCC-1701"),
            self.make_ship(ship_id="NCC-1702"),
        ]
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
            tmp_path = Path(tmp.name)

        try:
            with patch("main.DATA_FILE", tmp_path):
                save_data(ships)

            with open(tmp_path) as f:
                data = json.load(f)

            self.assertEqual(len(data), 2)
            ids = [d["ship_id"] for d in data]
            self.assertIn("NCC-1701", ids)
            self.assertIn("NCC-1702", ids)
        finally:
            os.unlink(tmp_path)

    def test_overwrites_existing_file(self):
        """Saving a shorter list should overwrite, not append to, the file."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
            tmp_path = Path(tmp.name)

        try:
            ships_first = [self.make_ship(ship_id="NCC-1701"), self.make_ship(ship_id="NCC-1702")]
            ships_second = [self.make_ship(ship_id="NCC-9999")]

            with patch("main.DATA_FILE", tmp_path):
                save_data(ships_first)
                save_data(ships_second)

            with open(tmp_path) as f:
                data = json.load(f)

            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["ship_id"], "NCC-9999")
        finally:
            os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# load_data
# ---------------------------------------------------------------------------

class TestLoadData(BaseSpaceportTest):

    def test_returns_empty_list_when_file_missing(self):
        """A non-existent data file should produce an empty list, not an error."""
        with patch("main.DATA_FILE", Path("/nonexistent/path/file.json")):
            result = load_data()
        self.assertEqual(result, [])

    def test_loads_valid_data_correctly(self):
        """A well-formed JSON file should be deserialised into Spaceship objects."""
        ship = self.make_ship()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w") as tmp:
            json.dump([ship.model_dump(mode="json")], tmp)
            tmp_path = Path(tmp.name)

        try:
            with patch("main.DATA_FILE", tmp_path):
                result = load_data()

            self.assertEqual(len(result), 1)
            self.assertIsInstance(result[0], Spaceship)
            self.assertEqual(result[0].ship_id, self.default_ship_id)
        finally:
            os.unlink(tmp_path)

    def test_returns_empty_list_on_corrupted_json(self):
        """Corrupted JSON should trigger the warning path and return an empty list."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w") as tmp:
            tmp.write("{ this is not valid json ,,, }")
            tmp_path = Path(tmp.name)

        try:
            with patch("main.DATA_FILE", tmp_path):
                with patch("builtins.print") as mock_print:
                    result = load_data()

            self.assertEqual(result, [])
            printed = " ".join(str(c) for c in mock_print.call_args_list)
            self.assertIn("Corrupted", printed)
        finally:
            os.unlink(tmp_path)

    def test_returns_empty_list_on_validation_error(self):
        """JSON that fails Pydantic validation should return an empty list with a warning."""
        bad_data = [{"ship_id": "X", "completely": "wrong", "schema": True}]
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w") as tmp:
            json.dump(bad_data, tmp)
            tmp_path = Path(tmp.name)

        try:
            with patch("main.DATA_FILE", tmp_path):
                with patch("builtins.print") as mock_print:
                    result = load_data()

            self.assertEqual(result, [])
            printed = " ".join(str(c) for c in mock_print.call_args_list)
            self.assertIn("Invalid", printed)
        finally:
            os.unlink(tmp_path)

    def test_round_trip_save_and_load(self):
        """Data saved by save_data should be exactly reproduced by load_data."""
        original = self.make_ship()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
            tmp_path = Path(tmp.name)

        try:
            with patch("main.DATA_FILE", tmp_path):
                save_data([original])
                loaded = load_data()

            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0].ship_id, original.ship_id)
            self.assertEqual(loaded[0].captain.license_number, original.captain.license_number)
            self.assertEqual(loaded[0].cargo_hold[0].weight_kg, original.cargo_hold[0].weight_kg)
        finally:
            os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# add_ship
# ---------------------------------------------------------------------------

class TestAddShip(BaseSpaceportTest):

    def _run_add_ship(self, ships: list, inputs: list) -> list:
        """Helper: run add_ship with a mocked input sequence and a temp data file."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
            tmp_path = Path(tmp.name)

        try:
            with patch("main.DATA_FILE", tmp_path):
                with patch("builtins.input", side_effect=inputs):
                    with patch("builtins.print"):
                        add_ship(ships)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

        return ships

    def _valid_inputs(
        self,
        ship_id="NCC-9000",
        model="Voyager-Class",
        capacity="1000",
        arrival=None,
        cap_name="Kathryn Janeway",
        cap_lic="GAL-9000-KJ",
        cargo_name="Rations",
        cargo_weight="50",
    ):
        """Returns a standard valid input sequence for add_ship."""
        return [
            ship_id, model, capacity, arrival or str(date.today()),
            cap_name, cap_lic,
            cargo_name, cargo_weight,
            "",                         # empty item name → finish cargo loop
        ]

    def test_valid_ship_is_appended(self):
        """A fully valid input sequence should add exactly one ship to the list."""
        ships = []
        self._run_add_ship(ships, self._valid_inputs())
        self.assertEqual(len(ships), 1)
        self.assertEqual(ships[0].ship_id, "NCC-9000")

    def test_duplicate_id_is_rejected(self):
        """Supplying an ID that is already docked should leave the list unchanged."""
        existing = self.make_ship(ship_id="NCC-1701")
        ships = [existing]

        with patch("builtins.input", return_value="NCC-1701"):
            with patch("builtins.print") as mock_print:
                add_ship(ships)

        self.assertEqual(len(ships), 1)
        printed = " ".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("already docked", printed)

    def test_empty_cargo_is_rejected(self):
        """Submitting no cargo items should print an error and not add the ship."""
        ships = []
        inputs = [
            "NCC-8888", "Nebula-Class", "500", str(date.today()),
            "Beverly Crusher", "GAL-8888-BC",
            "",  # immediately finish cargo loop — no items added
        ]

        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
            tmp_path = Path(tmp.name)

        try:
            with patch("main.DATA_FILE", tmp_path):
                with patch("builtins.input", side_effect=inputs):
                    with patch("builtins.print") as mock_print:
                        add_ship(ships)

            self.assertEqual(len(ships), 0)
            printed = " ".join(str(c) for c in mock_print.call_args_list)
            self.assertIn("required", printed)
        finally:
            os.unlink(tmp_path)

    def test_invalid_capacity_raises_value_error(self):
        """Non-numeric capacity input should print an input error without crashing."""
        ships = []
        inputs = ["NCC-7777", "Nova-Class", "NOT_A_NUMBER"]

        with patch("builtins.input", side_effect=inputs):
            with patch("builtins.print") as mock_print:
                add_ship(ships)

        self.assertEqual(len(ships), 0)
        printed = " ".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("INPUT ERROR", printed)

    def test_multiple_cargo_items_are_accepted(self):
        """All entered cargo items should be stored on the new ship."""
        ships = []
        inputs = [
            "NCC-6000", "Defiant-Class", "2000", str(date.today()),
            "Worf", "GAL-6000-WS",
            "Torpedoes", "300",
            "Food", "100",
            "",
        ]
        self._run_add_ship(ships, inputs)
        self.assertEqual(len(ships[0].cargo_hold), 2)

    def test_invalid_license_triggers_validation_error(self):
        """A malformed license number should print a validation error and not add the ship."""
        ships = []
        inputs = [
            "NCC-5000", "Miranda-Class", "500", str(date.today()),
            "Data", "INVALID-LICENSE",
            "Cargo", "10",
            "",
        ]

        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
            tmp_path = Path(tmp.name)

        try:
            with patch("main.DATA_FILE", tmp_path):
                with patch("builtins.input", side_effect=inputs):
                    with patch("builtins.print") as mock_print:
                        add_ship(ships)

            self.assertEqual(len(ships), 0)
            printed = " ".join(str(c) for c in mock_print.call_args_list)
            self.assertIn("VALIDATION ERROR", printed)
        finally:
            os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# view_ships
# ---------------------------------------------------------------------------

class TestViewShips(BaseSpaceportTest):

    def test_empty_list_prints_no_ships_message(self):
        """An empty dock should print the 'No ships docked' message."""
        with patch("builtins.print") as mock_print:
            view_ships([])
        printed = " ".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("No ships docked", printed)

    def test_ship_id_and_captain_appear_in_output(self):
        """Ship ID and captain name should both be visible in the printed table."""
        ship = self.make_ship()
        with patch("builtins.print") as mock_print:
            view_ships([ship])
        printed = " ".join(str(c) for c in mock_print.call_args_list)
        self.assertIn(self.default_ship_id, printed)
        self.assertIn(self.default_captain_name, printed)

    def test_total_cargo_weight_is_correct(self):
        """The displayed cargo weight should equal the sum of all cargo item weights."""
        cargo = [self.make_cargo(weight_kg=150.0), self.make_cargo(weight_kg=50.0)]
        ship = self.make_ship(cargo_hold=cargo, max_capacity_kg=1000.0)
        with patch("builtins.print") as mock_print:
            view_ships([ship])
        printed = " ".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("200.0", printed)

    def test_multiple_ships_all_appear(self):
        """Every ship in the list should have its ID printed."""
        ships = [
            self.make_ship(ship_id="NCC-0001"),
            self.make_ship(ship_id="NCC-0002"),
        ]
        with patch("builtins.print") as mock_print:
            view_ships(ships)
        printed = " ".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("NCC-0001", printed)
        self.assertIn("NCC-0002", printed)


# ---------------------------------------------------------------------------
# remove_ship
# ---------------------------------------------------------------------------

class TestRemoveShip(BaseSpaceportTest):

    def test_removes_existing_ship(self):
        """Providing a valid ship ID should remove that ship from the list."""
        ship = self.make_ship(ship_id="NCC-1701")
        ships = [ship]

        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
            tmp_path = Path(tmp.name)

        try:
            with patch("main.DATA_FILE", tmp_path):
                with patch("builtins.input", return_value="NCC-1701"):
                    with patch("builtins.print"):
                        remove_ship(ships)
            self.assertEqual(len(ships), 0)
        finally:
            os.unlink(tmp_path)

    def test_prints_not_found_for_unknown_id(self):
        """An ID that doesn't match any ship should print 'Ship not found'."""
        ship = self.make_ship(ship_id="NCC-1701")
        ships = [ship]

        with patch("builtins.input", return_value="NCC-9999"):
            with patch("builtins.print") as mock_print:
                remove_ship(ships)

        self.assertEqual(len(ships), 1)
        printed = " ".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("not found", printed)

    def test_removal_is_case_insensitive(self):
        """Ship ID matching should ignore case differences."""
        ship = self.make_ship(ship_id="NCC-1701")
        ships = [ship]

        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
            tmp_path = Path(tmp.name)

        try:
            with patch("main.DATA_FILE", tmp_path):
                with patch("builtins.input", return_value="ncc-1701"):
                    with patch("builtins.print"):
                        remove_ship(ships)
            self.assertEqual(len(ships), 0)
        finally:
            os.unlink(tmp_path)

    def test_only_matching_ship_is_removed(self):
        """Removing one ship by ID should leave all other ships intact."""
        ships = [
            self.make_ship(ship_id="NCC-1701"),
            self.make_ship(ship_id="NCC-1702"),
        ]

        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
            tmp_path = Path(tmp.name)

        try:
            with patch("main.DATA_FILE", tmp_path):
                with patch("builtins.input", return_value="NCC-1701"):
                    with patch("builtins.print"):
                        remove_ship(ships)
            self.assertEqual(len(ships), 1)
            self.assertEqual(ships[0].ship_id, "NCC-1702")
        finally:
            os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# search_ship
# ---------------------------------------------------------------------------

class TestSearchShip(BaseSpaceportTest):

    def test_finds_ship_by_exact_id(self):
        """Searching for an exact ship ID should return that ship."""
        ship = self.make_ship(ship_id="NCC-1701")
        ships = [ship]

        with patch("builtins.input", return_value="NCC-1701"):
            with patch("builtins.print") as mock_print:
                search_ship(ships)

        printed = " ".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("NCC-1701", printed)

    def test_finds_ship_by_captain_name(self):
        """Searching for a captain's name should surface the matching ship."""
        captain = self.make_captain(name="James Kirk")
        ship = self.make_ship(captain=captain)
        ships = [ship]

        with patch("builtins.input", return_value="James Kirk"):
            with patch("builtins.print") as mock_print:
                search_ship(ships)

        printed = " ".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("James Kirk", printed)

    def test_partial_match_returns_results(self):
        """A partial query should match ships whose ID or captain name contains it."""
        ship = self.make_ship(ship_id="NCC-1701")
        ships = [ship]

        with patch("builtins.input", return_value="1701"):
            with patch("builtins.print") as mock_print:
                search_ship(ships)

        printed = " ".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("NCC-1701", printed)

    def test_no_match_prints_not_found(self):
        """A query with no matches should print the 'No matching ships' message."""
        ship = self.make_ship(ship_id="NCC-1701")
        ships = [ship]

        with patch("builtins.input", return_value="ZZZZ"):
            with patch("builtins.print") as mock_print:
                search_ship(ships)

        printed = " ".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("No matching ships found", printed)

    def test_search_is_case_insensitive(self):
        """Search should match regardless of the capitalisation of the query."""
        captain = self.make_captain(name="Spock")
        ship = self.make_ship(captain=captain)
        ships = [ship]

        with patch("builtins.input", return_value="SPOCK"):
            with patch("builtins.print") as mock_print:
                search_ship(ships)

        printed = " ".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("Spock", printed)

    def test_returns_multiple_matches(self):
        """A broad query should return all ships that match, not just the first."""
        ships = [
            self.make_ship(ship_id="NCC-1701"),
            self.make_ship(ship_id="NCC-1702"),
            self.make_ship(ship_id="NX-01"),
        ]

        with patch("builtins.input", return_value="NCC"):
            with patch("builtins.print") as mock_print:
                search_ship(ships)

        printed = " ".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("NCC-1701", printed)
        self.assertIn("NCC-1702", printed)
        self.assertNotIn("NX-01", printed)

# ---------------------------------------------------------------------------
# Captain
# ---------------------------------------------------------------------------

class TestCaptainLicenseValidator(BaseSpaceportTest):

    def test_valid_license_is_accepted(self):
        captain = self.make_captain()
        self.assertEqual(captain.license_number, self.default_license_number)

    def test_wrong_prefix_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.make_captain(license_number="XYZ-1234-AB")

    def test_lowercase_suffix_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.make_captain(license_number="GAL-1234-ab")

    def test_too_few_digits_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.make_captain(license_number="GAL-123-AB")

    def test_extra_characters_are_rejected(self):
        with self.assertRaises(ValidationError):
            self.make_captain(license_number="GAL-1234-ABC")


# ---------------------------------------------------------------------------
# Cargo
# ---------------------------------------------------------------------------

class TestCargoWeightConstraint(BaseSpaceportTest):

    def test_positive_weight_is_accepted(self):
        cargo = self.make_cargo(weight_kg=0.1)
        self.assertEqual(cargo.weight_kg, 0.1)

    def test_zero_weight_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.make_cargo(weight_kg=0)

    def test_negative_weight_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.make_cargo(weight_kg=-10)


# ---------------------------------------------------------------------------
# Spaceship
# ---------------------------------------------------------------------------

class TestSpaceshipArrivalValidator(BaseSpaceportTest):

    def test_today_is_accepted(self):
        ship = self.make_ship(arrival_date=date.today())
        self.assertEqual(ship.arrival_date, date.today())

    def test_future_date_is_accepted(self):
        ship = self.make_ship(arrival_date=date.today() + timedelta(days=7))
        self.assertGreater(ship.arrival_date, date.today())

    def test_past_date_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.make_ship(arrival_date=date.today() - timedelta(days=1))


class TestSpaceshipCapacityValidator(BaseSpaceportTest):

    def test_cargo_within_capacity_is_accepted(self):
        cargo = [self.make_cargo(weight_kg=100)]
        ship = self.make_ship(cargo_hold=cargo, max_capacity_kg=200)
        self.assertEqual(ship.max_capacity_kg, 200)

    def test_cargo_at_exact_capacity_is_accepted(self):
        cargo = [self.make_cargo(weight_kg=500)]
        ship = self.make_ship(cargo_hold=cargo, max_capacity_kg=500)
        self.assertIsNotNone(ship)

    def test_cargo_exceeding_capacity_is_rejected(self):
        cargo = [self.make_cargo(weight_kg=600)]
        with self.assertRaises(ValidationError):
            self.make_ship(cargo_hold=cargo, max_capacity_kg=500)

    def test_zero_max_capacity_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.make_ship(max_capacity_kg=0)

    def test_empty_cargo_hold_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.make_ship(cargo_hold=[])


if __name__ == "__main__":
    unittest.main()