#!/bin/bash
#
# Restart ALL THREE game servers. `systemctl restart uAthena.target` does NOT reliably
# propagate the restart to the PartOf member services -- a .target has no process of its
# own, so "restarting" it is largely a no-op and the login/char servers kept running for
# days while only the map churned (S.). Restart the services directly; systemd honours the
# After= ordering (login -> char -> map).
systemctl restart uAlogin.service uAchar.service uAmap.service
