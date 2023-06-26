"""Generate markdown files for the environments."""
import os
import shutil

import gymnasium as gym

from utils import get_all_registered_miniwob_envs, trim_docstring


LAYOUT = "env"

gym.logger.set_level(gym.logger.DISABLED)


# Copy MiniWoB-plusplus/miniwob/html to /docs/demos/
source_path = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "miniwob",
    "html",
)
# Sphinx copies everything inside the first demos/ directory to the root
# So to ensure that the final path is /demos/** we need another demos folder
destination_path = os.path.join(os.path.dirname(__file__), "..", "demos", "demos")
shutil.copytree(source_path, destination_path)


# Update Docs
filtered_envs = get_all_registered_miniwob_envs()
for i, env_spec in enumerate(filtered_envs):
    print("ID:", env_spec.id)
    try:
        env_spec = gym.spec(env_spec.id)

        split = env_spec.entry_point.split(":")
        mod = __import__(split[0], fromlist=[split[1]])
        env_class = getattr(mod, split[1])
        docstring = env_class.__doc__

        if not docstring:
            docstring = env_class.__class__.__doc__

        docstring = trim_docstring(docstring)

        env_type = "miniwob"
        env_name = env_spec.name
        title_env_name = env_name

        # path for saving the markdown file
        md_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "environments",
            env_name + ".md",
        )
        os.makedirs(os.path.dirname(md_path), exist_ok=True)

        front_matter = f"""---
autogenerated:
title: {title_env_name}
---
"""
        title = f"# {title_env_name}"
        if env_name.startswith("flight."):
            url = f'../../demos/{env_name.replace(".", "/")}/wrapper.html'
            info = f"""
<center>
    <a href="{url}" target="_blank"><button>Open demo in a separate tab.</button></a>
</center>
"""
        else:
            url = f"../../demos/miniwob/{env_name}.html"
            info = f"""
<center>
    <iframe src="{url}" width="325" height="210" scrolling="no" style="overflow:hidden;">
    </iframe><br>
    <a href="{url}" target="_blank"><button>Open demo in a separate tab.</button></a>
</center>
"""
        if docstring is None:
            docstring = "No information provided"
        all_text = f"""{front_matter}
{title}

{info}

{docstring}
"""
        file = open(md_path, "w", encoding="utf-8")
        file.write(all_text)
        file.close()
    except Exception as e:
        print(e)
