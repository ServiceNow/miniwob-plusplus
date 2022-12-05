"""MiniWoB observation space."""
import numpy as np
from gymnasium import spaces

UTTERANCE_MAX_LENGTH = 256
ATTRIBUTE_MAX_LENGTH = 64
TEXT_MAX_LENGTH = 256
ASCII_CHARSET = frozenset(chr(x) for x in range(32, 128))
MIN_REF = -1000000
MAX_REF = 1000000


def get_observation_space(screen_width, screen_height):
    """Return the space of observations."""
    utterance_space = spaces.Text(
        max_length=UTTERANCE_MAX_LENGTH,
        charset=ASCII_CHARSET,
    )
    element_space = spaces.Dict(
        {
            # Non-zero integer ID:
            # `ref` for normal elements start from 1, while `ref` for text
            # pseudo-elements counts down from -1.
            "ref": spaces.Discrete(MAX_REF - MIN_REF, start=MIN_REF),
            # `ref` ID of the parent (0 = no parent, for root element).
            "parent": spaces.Discrete(MAX_REF),
            # Position (left, top)
            "pos": spaces.Box(
                np.array([float("-inf"), float("-inf")]),
                np.array([float("inf"), float("inf")]),
            ),
            # Size (width, height)
            "size": spaces.Box(
                np.array([0.0, 0.0]), np.array([float("inf"), float("inf")])
            ),
            # Tag:
            # For normal elements, this is the uppercased tag name (e.g., "DIV").
            # For <input> elements, the input type is appended (e.g., "INPUT_text").
            # Each non-empty text node becomes a pseudo-elements with tag "t".
            "tag": spaces.Text(max_length=ATTRIBUTE_MAX_LENGTH, charset=ASCII_CHARSET),
            # Text content of leaf nodes.
            "text": spaces.Text(
                min_length=0, max_length=TEXT_MAX_LENGTH, charset=ASCII_CHARSET
            ),
            # Value of <input> elements.
            "value": spaces.Text(
                min_length=0, max_length=TEXT_MAX_LENGTH, charset=ASCII_CHARSET
            ),
            # HTML id attribute
            "id": spaces.Text(
                min_length=0, max_length=ATTRIBUTE_MAX_LENGTH, charset=ASCII_CHARSET
            ),
            # HTML class attribute (multiple classes are separated by spaces)
            "classes": spaces.Text(
                min_length=0, max_length=ATTRIBUTE_MAX_LENGTH, charset=ASCII_CHARSET
            ),
            # Colors (RGBA)
            "bg_color": spaces.Box(
                np.array([0.0] * 4, dtype=np.float32),
                np.array([255.0] * 4, dtype=np.float32),
            ),
            "fg_color": spaces.Box(
                np.array([0.0] * 4, dtype=np.float32),
                np.array([255.0] * 4, dtype=np.float32),
            ),
            # Flags:
            # focused: whether the element is being focused on
            # tampered: whether the element has been tampered (clicked, focused, typed, etc.)
            # targeted: whether the element is an event target (for recorded demonstrations)
            # is_leaf: whether the element is a leaf
            "flags": spaces.MultiBinary(n=4),
        }
    )
    screenshot_space = spaces.Box(
        # Each position stores the RGB values. Note the swapped axes (height first).
        np.zeros((screen_height, screen_width, 3), dtype=np.uint8),
        np.ones((screen_height, screen_width, 3), dtype=np.uint8) * 255.0,
        dtype=np.uint8,
    )
    observation_space = spaces.Dict(
        {
            "utterance": utterance_space,
            "dom_elements": spaces.Sequence(element_space),
            "screenshot": screenshot_space,
        }
    )
    return observation_space


def serialize_dom_element(element):
    """Serialize the given DOMElement to fit the element space."""
    serialized = {
        "ref": element.ref,
        "parent": element.parent.ref if element.parent else 0,
        "pos": np.array([element.left, element.top], dtype=np.float32),
        "size": np.array([element.width, element.height], dtype=np.float32),
        "tag": element.tag[:ATTRIBUTE_MAX_LENGTH],
        "text": (element.text or "")[:TEXT_MAX_LENGTH],
        "value": str(element.value or "")[:TEXT_MAX_LENGTH],
        "id": element.id,
        "classes": element.classes,
        "bg_color": np.array(element.bg_color, dtype=np.float32),
        "fg_color": np.array(element.fg_color, dtype=np.float32),
        "flags": np.array(
            [
                element.focused,
                element.tampered,
                element.targeted,
                element.is_leaf,
            ],
            dtype=np.int8,
        ),
    }
    return serialized


def create_empty_screenshot(screen_width, screen_height):
    """Returns an all-black screenshot."""
    return np.zeros((screen_height, screen_width, 3), dtype=np.uint8)


def create_empty_observation(screen_width, screen_height):
    """Returns an empty observation for a terminated session."""
    observation = {
        "utterance": "",
        "dom_elements": [],
        "screenshot": create_empty_screenshot(screen_width, screen_height),
    }
    return observation


def create_observation(utterance, root_dom, screenshot):
    """Returns an observation that fits in the observation space.

    Args:
        utterance: Instruction text extracted from the task.
        root_dom: DOMElement object for the root element.
        screenshot: Screenshot as an RGB array.
    Returns:
        the observation object
    """
    dom_elements = root_dom.subtree_elements
    serialized_elements = [serialize_dom_element(element) for element in dom_elements]
    observation = {
        "utterance": utterance[:UTTERANCE_MAX_LENGTH],
        "dom_elements": serialized_elements,
        "screenshot": screenshot,
    }
    return observation