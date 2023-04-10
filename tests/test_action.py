"""Test action execution."""
from typing import Mapping, Tuple

import gymnasium
import numpy as np
import pytest

from miniwob.action import ActionSpaceConfig, ActionTypes
from miniwob.fields import field_lookup


class RepeatedTester:
    """Base class for repeated testing on a single task."""

    # Environment name; subclasses should set this field
    ENV_NAME = ""
    # Number of times to run the test
    N = 10
    # Maximum number of steps for each episode
    MAX_STEPS = 1
    # Fragile tasks need longer wait time and single instance
    FRAGILE = False
    # Supported actions in the action space
    SUPPORTED_ACTIONS = [
        ActionTypes.NONE,
        ActionTypes.CLICK_COORDS,
        ActionTypes.CLICK_ELEMENT,
        ActionTypes.TYPE_TEXT,
        ActionTypes.FOCUS_ELEMENT_AND_TYPE_TEXT,
    ]

    @pytest.fixture
    def env(self):
        """Yield an environment for the task."""
        action_space_config = ActionSpaceConfig(action_types=self.SUPPORTED_ACTIONS)
        if self.FRAGILE:
            env = gymnasium.make(
                self.ENV_NAME, action_space_config=action_space_config, wait_ms=300
            )
        else:
            env = gymnasium.make(self.ENV_NAME, action_space_config=action_space_config)
        yield env
        env.close()

    def test_run(self, env):
        """Run the test N times on the environment."""
        for i in range(self.N):
            print(f"Iteration {i + 1} / {self.N}")
            obs, info = env.reset()
            reward = -1
            for step in range(self.MAX_STEPS):
                action = self._get_action(env, obs, info, step)
                obs, reward, terminated, _, _ = env.step(action)
                assert reward >= 0
                if terminated:
                    break
            else:
                assert False, f"Number of steps exceeded {self.MAX_STEPS}"
            assert reward >= 0

    def _get_action(self, env, obs, info, step):
        """Return a MiniWoBAction that clicks the right thing."""
        raise NotImplementedError

    def create_click_element_action(self, env, element):
        """Create an action that clicks in the specified element."""
        action = env.action_space.sample()
        action["action_type"] = self.SUPPORTED_ACTIONS.index(ActionTypes.CLICK_ELEMENT)
        action["ref"] = element["ref"]
        return action

    def create_click_button_action(self, env, obs, button_text):
        """Create an action that clicks on the button with the specified text."""
        for element in obs["dom_elements"]:
            if element["tag"] == "button" and element["text"] == button_text:
                return self.create_click_element_action(env, element)
        assert False, f"{button_text} button not found"

    def create_click_coords_action(self, env, left, top):
        """Create an action that clicks on the specified coordinates."""
        action = env.action_space.sample()
        action["action_type"] = self.SUPPORTED_ACTIONS.index(ActionTypes.CLICK_COORDS)
        action["coords"] = np.array([left, top], dtype=np.float32)
        return action

    def create_click_element_center_action(self, env, element):
        """Create an action that clicks the element's center."""
        left, top = element["left"].item(), element["top"].item()
        width, height = element["width"].item(), element["height"].item()
        return self.create_click_coords_action(
            env, left + (width / 2), top + (height / 2)
        )

    def create_type_action(self, env, text):
        """Create an action that types text."""
        action = env.action_space.sample()
        action["action_type"] = self.SUPPORTED_ACTIONS.index(ActionTypes.TYPE_TEXT)
        action["text"] = text
        return action

    def create_focus_and_type_action(self, env, element, text):
        """Create an action that focuses on the element and types text."""
        action = env.action_space.sample()
        action["action_type"] = self.SUPPORTED_ACTIONS.index(
            ActionTypes.FOCUS_ELEMENT_AND_TYPE_TEXT
        )
        action["ref"] = element["ref"]
        action["text"] = text
        return action


################################################
# Test suites for tasks that involve a single click


class TestClickTest2(RepeatedTester):
    """Tests for task click-test-2."""

    ENV_NAME = "miniwob/click-test-2-v1"

    def _get_action(self, env, obs, info, step):
        for element in obs["dom_elements"]:
            if element["tag"] == "button" and element["text"] == "ONE":
                return self.create_click_element_action(env, element)
        # No button is found, which is weird
        assert False, 'Button "ONE" not found'


class TestClickButton(RepeatedTester):
    """Tests for task click-button."""

    ENV_NAME = "miniwob/click-button-v1"

    def _get_action(self, env, obs, info, step):
        target = field_lookup(obs["fields"], "target")
        for element in obs["dom_elements"]:
            if element["tag"] == "button" and element["text"] == target:
                return self.create_click_element_center_action(env, element)
        # No button is found, which is weird
        assert False, f'Button "{target}" not found'


class TestFocusText(RepeatedTester):
    """Tests for task focus-text."""

    ENV_NAME = "miniwob/focus-text-v1"

    def _get_action(self, env, obs, info, step):
        for element in obs["dom_elements"]:
            if element["tag"] == "input_text":
                return self.create_click_element_center_action(env, element)
        # No input is found, which is weird
        assert False, "Input box not found"


class TestIdentifyShape(RepeatedTester):
    """Tests for task identify-shape."""

    ENV_NAME = "miniwob/identify-shape-v1"

    def _get_action(self, env, obs, info, step):
        shape = self._identify_shape(obs)
        for element in obs["dom_elements"]:
            if element["tag"] == "button" and element["text"] == shape:
                return self.create_click_element_action(env, element)
        # No button is found, which is weird
        assert False, f'Button "{shape}" not found'

    def _identify_shape(self, obs):
        for element in obs["dom_elements"]:
            if element["tag"] == "svg":
                child = [
                    x for x in obs["dom_elements"] if x["parent"] == element["ref"]
                ][0]
                if child["tag"] == "circle":
                    return "Circle"
                elif child["tag"] == "text":
                    if child["text"].isdigit():
                        return "Number"
                    else:
                        return "Letter"
                elif child["tag"] == "rect":
                    return "Rectangle"
                elif child["tag"] == "polygon":
                    return "Triangle"


class TestClickDialog2(RepeatedTester):
    """Tests for task click-dialog-2."""

    ENV_NAME = "miniwob/click-dialog-2-v1"

    def _get_action(self, env, obs, info, step):
        target = field_lookup(obs["fields"], "target")
        if target == "x":
            target = ""
        for element in obs["dom_elements"]:
            if element["tag"] == "button" and element["text"] == target:
                return self.create_click_element_action(env, element)
        # No button is found, which is weird
        assert False, f'Button "{target}" not found'


################################################################################
# Test suites for more advanced tasks


class TestEnterText(RepeatedTester):
    """Tests for task enter-text."""

    ENV_NAME = "miniwob/enter-text-v1"
    MAX_STEPS = 3

    def _get_action(self, env, obs, info, step):
        if step == 0:
            # Click on the textbox
            for element in obs["dom_elements"]:
                if element["tag"] == "input_text":
                    assert not element["flags"][0].item()
                    return self.create_click_element_action(env, element)
            assert False, "Input text not found"
        elif step == 1:
            # Assert that the input is focused
            for element in obs["dom_elements"]:
                if element["tag"] == "input_text":
                    assert element["flags"][0].item()
                    break
            else:
                assert False, "Input text not found"
            # Type the text
            target = field_lookup(obs["fields"], "target")
            if len(target) > 2:
                # Hmm... Let's try the LEFT arrow key
                target = target[:-2] + target[-1] + "\ue012" + target[-2]
            return self.create_type_action(env, target)
        elif step == 2:
            # Click submit
            return self.create_click_button_action(env, obs, "Submit")


class TestEnterTextFocusAndType(RepeatedTester):
    """Tests for task enter-text, using FocusAndType actions."""

    ENV_NAME = "miniwob/enter-text-v1"
    MAX_STEPS = 2

    def _get_action(self, env, obs, info, step):
        if step == 0:
            # Type into the textbox
            target = field_lookup(obs["fields"], "target")
            for element in obs["dom_elements"]:
                if element["tag"] == "input_text":
                    return self.create_focus_and_type_action(env, element, target)
            assert False, "Input text not found"
        elif step == 1:
            # Click submit
            return self.create_click_button_action(env, obs, "Submit")


class TestClickCheckboxes(RepeatedTester):
    """Tests for task click-checkboxes."""

    ENV_NAME = "miniwob/click-checkboxes-v1"
    MAX_STEPS = 7

    def _get_action(self, env, obs, info, step):
        if not obs:
            return
        # print obs.dom.visualize()
        things_to_click = [value for (key, value) in obs["fields"] if key != "button"]
        for element in obs["dom_elements"]:
            if element["tag"] == "label":
                checkbox, text = (
                    x for x in obs["dom_elements"] if x["parent"] == element["ref"]
                )
                if checkbox["value"]:
                    things_to_click.remove(text["text"])
                    continue
                elif text["text"] in things_to_click:
                    # Click on <label>:
                    return self.create_click_element_action(env, element)
        # Click the submit button
        assert not things_to_click
        return self.create_click_button_action(env, obs, "Submit")


class TestChooseDateEasy(RepeatedTester):
    """Tests for task choose-date-easy."""

    ENV_NAME = "miniwob/choose-date-easy-v1"
    MAX_STEPS = 3
    FRAGILE = True

    def _get_action(self, env, obs, info, step):
        if step == 0:
            for element in obs["dom_elements"]:
                if element["tag"] == "input_text":
                    return self.create_click_element_action(env, element)
            assert False, "Input text not found"
        elif step == 1:
            target = field_lookup(obs["fields"], "day")
            for element in obs["dom_elements"]:
                if element["tag"] == "a" and element["text"] == target:
                    return self.create_click_element_action(env, element)
            assert False, f"Day {target} not found"
        elif step == 2:
            return self.create_click_button_action(env, obs, "Submit")


class TestUseAutocomplete(RepeatedTester):
    """Tests for task use-autocomplete."""

    ENV_NAME = "miniwob/use-autocomplete-v1"
    MAX_STEPS = 3
    FRAGILE = True

    def _check(self, element, fields):
        t = element["text"]
        if t is None:
            return False
        start = field_lookup(fields, "start")
        end = field_lookup(fields, "end")
        return t.startswith(start) and t.endswith(end)

    def _get_action(self, env, obs, info, step):
        if step == 0:
            for element in obs["dom_elements"]:
                if element["tag"] == "input_text":
                    return self.create_focus_and_type_action(
                        env, element, field_lookup(obs["fields"], "start")
                    )
            assert False, "Input text not found"
        elif step == 1:
            # print obs.dom.visualize()
            for element in obs["dom_elements"]:
                if element["tag"] == "div" and self._check(element, obs["fields"]):
                    return self.create_click_element_action(env, element)
            assert False, "Correct entry not found"
        elif step == 2:
            return self.create_click_button_action(env, obs, "Submit")


class TestUseAutocompleteNoDelay(RepeatedTester):
    """Tests for task use-autocomplete-nodelay."""

    ENV_NAME = "miniwob/use-autocomplete-nodelay-v1"
    MAX_STEPS = 3
    FRAGILE = "instance"

    def _check(self, element, fields):
        t = element["text"]
        if t is None:
            return False
        start = field_lookup(fields, "start")
        end = field_lookup(fields, "end")
        return t.startswith(start) and t.endswith(end)

    def _get_action(self, env, obs, info, step):
        if step == 0:
            for element in obs["dom_elements"]:
                if element["tag"] == "input_text":
                    return self.create_focus_and_type_action(
                        env, element, field_lookup(obs["fields"], "start")
                    )
            assert False, "Input text not found"
        elif step == 1:
            # print obs.dom.visualize()
            for element in obs["dom_elements"]:
                if element["tag"] == "div" and self._check(element, obs["fields"]):
                    return self.create_click_element_action(env, element)
            assert False, "Correct entry not found"
        elif step == 2:
            return self.create_click_button_action(env, obs, "Submit")


class TestClickColor(RepeatedTester):
    """Tests for task click-color."""

    ENV_NAME = "miniwob/click-color-v1"
    COLORS: Mapping[Tuple[int, int, int], str] = {
        (0, 0, 0): "black",
        (255, 0, 0): "red",
        (0, 255, 0): "lime",
        (0, 0, 255): "blue",
        (255, 255, 0): "yellow",
        (255, 0, 255): "magenta",
        (0, 255, 255): "cyan",
        (255, 255, 255): "white",
        (128, 128, 128): "grey",
        (128, 128, 0): "olive",
        (128, 0, 128): "purple",
        (255, 165, 0): "orange",
        (255, 192, 203): "pink",
    }

    def _get_action(self, env, obs, info, step):
        for element in obs["dom_elements"]:
            if "color" in element["classes"]:
                r, g, b, a = element["bg_color"].tolist()
                name = self.COLORS[int(r * 255), int(g * 255), int(b * 255)]
                if name == field_lookup(obs["fields"], "target"):
                    return self.create_click_element_action(env, element)
        assert False, "Correct entry not found"


class TestEnterTime(RepeatedTester):
    """Tests for task enter-time."""

    ENV_NAME = "miniwob/enter-time-v1"
    MAX_STEPS = 2

    def _get_action(self, env, obs, info, step):
        if step == 0:
            target = field_lookup(obs["fields"], "target")
            if target.startswith("1:"):
                target = "0" + target  # Typing '14' will change the number to 2
            for element in obs["dom_elements"]:
                if element["tag"] == "input_time":
                    return self.create_focus_and_type_action(env, element, target)
            assert False, "Input text not found"
        elif step == 1:
            return self.create_click_button_action(env, obs, "Submit")


class TestClickPie(RepeatedTester):
    """Tests for task click-pie-nodelay."""

    ENV_NAME = "miniwob/click-pie-nodelay-v1"
    MAX_STEPS = 2

    def _get_action(self, env, obs, info, step):
        if step == 0:
            path = None
            for element in obs["dom_elements"]:
                if element["tag"] == "path":
                    path = element
                elif element["text"] == "+":
                    assert path is not None
                    return self.create_click_element_action(env, path)
            assert False, "Select not found"
        elif step == 1:
            path = None
            for element in obs["dom_elements"]:
                if element["tag"] == "path":
                    path = element
                elif element["text"] == field_lookup(obs["fields"], "target"):
                    assert path is not None
                    return self.create_click_element_action(env, path)
            assert False, "Correct entry not found"
