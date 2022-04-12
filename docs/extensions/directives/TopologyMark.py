from __future__ import annotations

import yaml
from sphinx.directives.code import CodeBlock

from lib.multihost import KnownTopology
from lib.multihost.plugin.marks import TopologyMark


class TopologyMarkDirective(CodeBlock):
    """
    Convert :class:`TopologyMark` into yaml and wrap it in code-block directive.
    """

    def run(self):
        x = eval(self.arguments[0])

        if isinstance(x, KnownTopology):
            x = x.value

        if not isinstance(x, TopologyMark):
            raise ValueError(f'Invalid argument: {self.arguments[0]}')

        # Set language
        self.arguments[0] = 'yaml'

        # Set content
        self.content = yaml.dump(x.export(), sort_keys=False).splitlines()

        return super().run()


def setup(app):
    app.add_directive("topology-mark", TopologyMarkDirective)

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
