from __future__ import annotations

import inspect

from ..host import BaseHost


class MultihostUtility(object):
    """
    Base class for utility functions that operate on remote hosts, such as
    writing a file or managing SSSD.

    Instances of :class:`MultihostUtility` can be used in any role class which
    is a subclass of :class:`lib.multihost.roles.BaseRole`. In this case,
    :func:`setup` and :func:`teardown` methods are called automatically when the
    object is created and destroyed to ensure proper setup and clean up on the
    remote host.
    """

    def __init__(self, host: BaseHost) -> None:
        """
        :param host: Remote host instance.
        :type host: BaseHost
        """
        self.host = host

    def setup(self) -> None:
        """
        Setup object.
        """
        pass

    def teardown(self) -> None:
        """
        Teardown object.
        """
        pass

    @staticmethod
    def GetUtilityAttributes(o: object) -> dict[str, MultihostUtility]:
        """
        Get all attributes of the ``o`` that are instance of
        :class:`MultihostUtility`.

        :param o: Any object.
        :type o: object
        :return: Dictionary {attribute name: value}
        :rtype: dict[str, MultihostUtility]
        """
        return dict(inspect.getmembers(o, lambda attr: isinstance(attr, MultihostUtility)))

    @classmethod
    def SetupUtilityAttributes(cls, o: object) -> None:
        """
        Setup all :class:`MultihostUtility` objects attributes of the given
        object.

        :param o: Any object.
        :type o: object
        """
        for util in cls.GetUtilityAttributes(o).values():
            util.setup()

    @classmethod
    def TeardownUtilityAttributes(cls, o: object) -> None:
        """
        Teardown all :class:`MultihostUtility` objects attributes of the given
        object.

        :param o: Any object.
        :type o: object
        """
        errors = []
        for util in cls.GetUtilityAttributes(o).values():
            try:
                util.teardown()
            except Exception as e:
                errors.append(e)

        if errors:
            raise Exception(errors)
