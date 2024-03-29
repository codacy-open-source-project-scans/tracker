#
# Copyright (C) 2010, Nokia <jean-luc.lamadon@nokia.com>
# Copyright (C) 2019, Sam Thursfield <sam@afuera.me.uk>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.
#

from pathlib import Path
from tempfile import TemporaryDirectory
import atexit
import logging
import os
import shutil
import subprocess

log = logging.getLogger(__name__)


class TemporaryDConfProfile():
    """
    A DConf profile that is isolated from the rest of the system.

    See https://help.gnome.org/admin/system-admin-guide/stable/dconf-profiles.html.en
    """

    def __init__(self):
        self._tmpdir = TemporaryDirectory()
        atexit.register(self.cleanup)

        self._profile = Path(self._tmpdir.name).joinpath('trackertest')
        self._profile.write_text('user-db:trackertest')

    def get_path(self) -> str:
        return str(self._profile)

    def cleanup(self):
        self._tmpdir.cleanup()


class DConfClient(object):
    """
    Allow changing Tracker configuration in DConf.

    Tests should be run with a separate DConf profile so that these changes do
    not affect the user's configuration. The 'trackertest' profile exists for
    this reason, and the constructor will fail if this isn't the profile in
    use, to avoid any risk of modifying or removing your real configuration.

    We use the `gsettings` binary rather than using the Gio.Settings API.
    This is to avoid the need to set DCONF_PROFILE in our own process
    environment.
    """

    def __init__(self, extra_env, session_bus_address, host_dbus=False):
        self.env = os.environ
        self.env.update(extra_env)
        self.env['DBUS_SESSION_BUS_ADDRESS'] = session_bus_address
        if not host_dbus:
            self._check_using_correct_dconf_profile()

    def _check_using_correct_dconf_profile(self):
        profile = self.env.get("DCONF_PROFILE")
        if not profile:
            raise Exception(
                "DCONF_PROFILE is not set in the environment. This class must "
                "be created inside a TrackerDBussandbox to avoid risk of "
                "interfering with real settings.")
        if not os.path.exists(profile):
            raise Exception("Unable to find DConf profile '%s'." % profile)

        assert os.path.basename(profile) == "trackertest"

    def write(self, schema, key, value):
        """
        Write a settings value.
        """
        subprocess.run(['gsettings', 'set', schema, key, value.print_(False)],
                       env=self.env,
                       stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
