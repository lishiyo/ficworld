import pytest
from pydantic import ValidationError

from modules.data_models import CharacterConfig, InitialGoals

# Tests for InitialGoals
def test_initial_goals_defaults():
    goals = InitialGoals()
    assert goals.long_term == []
    assert goals.short_term == []

def test_initial_goals_with_data():
    long_term_goals = ["Become a master sorcerer", "Restore the kingdom"]
    short_term_goals = ["Find the ancient staff", "Learn a new spell"]
    goals = InitialGoals(long_term=long_term_goals, short_term=short_term_goals)
    assert goals.long_term == long_term_goals
    assert goals.short_term == short_term_goals

# Tests for CharacterConfig
def test_character_config_required_fields():
    data = {
        "full_name": "Sir Gideon Ofnir",
        "persona": "A knowledgeable but stern knight.",
        "backstory": "Once a revered scholar, now a knight seeking lost lore."
    }
    config = CharacterConfig(**data)
    assert config.full_name == "Sir Gideon Ofnir"
    assert config.persona == data["persona"]
    assert config.backstory == data["backstory"]
    assert isinstance(config.initial_goals, InitialGoals)
    assert config.initial_goals.long_term == []
    assert config.activity_coefficient == 0.8 # Default
    assert config.starting_mood == {} # Default

def test_character_config_all_fields():
    data = {
        "full_name": "Lady Elara",
        "persona": "A graceful diplomat with a hidden agenda.",
        "backstory": "Exiled from her homeland, she seeks to reclaim her birthright.",
        "initial_goals": {
            "long_term": ["Reclaim the throne"],
            "short_term": ["Gather allies", "Secure funding"]
        },
        "activity_coefficient": 0.9,
        "starting_mood": {"determination": 0.8, "sadness": 0.3}
    }
    config = CharacterConfig(**data)
    assert config.full_name == "Lady Elara"
    assert config.persona == data["persona"]
    assert config.backstory == data["backstory"]
    assert config.initial_goals.long_term == ["Reclaim the throne"]
    assert config.initial_goals.short_term == ["Gather allies", "Secure funding"]
    assert config.activity_coefficient == 0.9
    assert config.starting_mood == {"determination": 0.8, "sadness": 0.3}

def test_character_config_missing_required_field():
    with pytest.raises(ValidationError) as excinfo:
        CharacterConfig(persona="Missing name and backstory", backstory="test")
    # Check that 'full_name' is in the error messages
    assert "full_name" in str(excinfo.value).lower()

    with pytest.raises(ValidationError):
        CharacterConfig(full_name="Missing persona", backstory="test")
    
    with pytest.raises(ValidationError):
        CharacterConfig(full_name="Missing backstory", persona="test")

def test_character_config_invalid_type():
    with pytest.raises(ValidationError) as excinfo:
        CharacterConfig(
            full_name="Test Name", 
            persona="Test Persona", 
            backstory="Test Backstory",
            activity_coefficient="not_a_float" # Invalid type
        )
    assert "activity_coefficient" in str(excinfo.value).lower()
    assert "float_parsing" in str(excinfo.value).lower() # Pydantic v2 error message detail

    with pytest.raises(ValidationError) as excinfo:
        CharacterConfig(
            full_name="Test Name", 
            persona="Test Persona", 
            backstory="Test Backstory",
            initial_goals={"long_term": "not_a_list"} # Invalid type for list field
        )
    assert "initial_goals.long_term" in str(excinfo.value).lower()
    assert "list_type" in str(excinfo.value).lower() 