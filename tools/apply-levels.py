#!/usr/bin/env python3
"""
Fold the build half of the document into five reading depths, and rewrite the
install and backup/restore prose around the one-command installer and its two
companion scripts.

Run once, from the project root:  python3 tools/apply-levels.py
Kept in tools/ as the record of how the document took its reading depths.
The payload below is zip-era text; the document has moved on, and this
tool is never run again — it is a record, not a generator.

The model: every block in sections 02-17 carries a data-lvl of 2..5, or none.
None means it belongs to the Easy read - the lede, one new plain-language
paragraph per section, and the occasional friendly figure. Depth 2 is enough
to build it, 3 is how it works, and 4 is why it is built that way and every
deeper answer to "why?" - anything past the fourth answer also lives at 4.
Section 01 is untouched: the argument is for everyone, at every depth.

Every edit is anchored on a string or a parsed span that must be found; a
missing anchor stops the script before anything is written.
"""
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sections as S  # noqa: E402

INDEX = "site/app/index.html"
src = io.open(INDEX, encoding="utf-8").read()
orig_len = len(src)


def must(old, new, s, count=1):
    n = s.count(old)
    if n != count:
        sys.exit("anchor found %d times, expected %d:\n  %r" % (n, count, old[:120]))
    return s.replace(old, new, count)


# ===========================================================================
# The per-section plain-language paragraph — the Easy read's whole body
# ===========================================================================

EASY = {
    "s02": "<p>In short: the inverter measures, the Pi decides, the car obeys. "
           "The charger just delivers power and reports what it sees; the car is "
           "what actually adjusts how much it draws, one amp at a time, over "
           "Bluetooth. Everything runs inside the house &mdash; no cloud account "
           "is in the loop, and the internet can be down while the car charges.</p>",
    "s03": "<p>Three small purchases carry the whole control stack: a Raspberry "
           "Pi, a memory card for its system, and an ordinary USB disk for the "
           "measurement history. Everything else in this section is advice on "
           "where to put them.</p>",
    "s04": "<p>The inverter has two switches to flip in its own web page &mdash; "
           "one lets the Pi read the meters, the other exposes the voltages. "
           "Five minutes in a browser, done before the Pi even exists.</p>",
    "s05": "<p>The charger only needs to join the home Wi-Fi, from the Tesla "
           "app, standing next to it. After that it is never configured again "
           "&mdash; it just reports what it sees.</p>",
    "s06": "<p>The electrician&rsquo;s cabinet: where the grid, the house, the "
           "solar and the charger meet, with a protection relay that disconnects "
           "the house if the voltage climbs too far. Built by professionals; "
           "photographed here so you know what is what.</p>",
    "s07": "<p>Everything lives on one home network. Three devices get fixed "
           "addresses on the router, the Pi runs on a cable, and the two outdoor "
           "devices stay on 2.4&nbsp;GHz Wi-Fi.</p>",
    "s08": "<p>Put the operating system on the card with Raspberry Pi&rsquo;s "
           "own tool, plug in network and power, and log in once from the "
           "laptop. No screen, no keyboard, nothing typed on the Pi itself.</p>",
    "s09": "<p>One command builds the whole thing. The installer asks four "
           "questions, sets up every service, and checks its own work as it "
           "goes; if a USB disk is plugged in it puts the history there, asking "
           "before it touches anything. Ten minutes, most of it downloads.</p>",
    "s10": "<p>The one step no script can do: teaching the car to trust the Pi. "
           "You send a key from your phone, hold the key card against the "
           "console, and confirm on the car&rsquo;s screen. Then you back the "
           "key up &mdash; it is the one file that can never be recreated.</p>",
    "s11": "<p>evcc is told about the four devices in its own web page &mdash; "
           "the two meters, the charger and the car. Screenshots of every "
           "dialog, filled in, are below.</p>",
    "s12": "<p>Four numbers decide everything: start charging at one amp of "
           "spare sun, never draw more than sixteen, wait a minute before "
           "starting and ten before stopping. The result, measured: over "
           "98&nbsp;% of the roof&rsquo;s output used at home.</p>",
    "s13": "<p>Seventeen small files do the housekeeping &mdash; two loggers, "
           "the update machinery, and the two container recipes. The installer "
           "places all of them, and none contains a secret.</p>",
    "s14": "<p>One Grafana page shows the whole system: live power at the top, "
           "the day&rsquo;s history under it, and an update desk at the bottom. "
           "The installer imports it ready-made.</p>",
    "s15": "<p>Three checks decide whether to trust it: the numbers agree with "
           "the inverter, the grid meter&rsquo;s sign is right, and everything "
           "comes back on its own after a reboot.</p>",
    "s16": "<p>On a clear day it needs nothing from you: the car starts on its "
           "own mid-morning, follows the sun, and stops when the surplus is "
           "gone. The table is what that looks like; the commands are for when "
           "you are curious.</p>",
    "s17": "<p>The tables, and the safety net: what runs on boot, what "
           "<code>backup.py</code> saves and <code>restore.py</code> brings "
           "back, where every file lives, and the address worksheet to fill "
           "in.</p>",
}

# ===========================================================================
# The depth of every kept block, by section and block index
# ===========================================================================

LEVELS = {
    "s02": {2: 3, 3: 3, 4: 4, 5: 3, 6: 3, 7: 3, 8: 4, 9: 3},
    "s03": {2: 2, 3: 2, 4: 2, 5: 4, 6: 2, 7: 2},
    "s04": {1: 2, 2: 2, 3: 2, 4: 3, 5: 2, 6: 2, 7: 2, 8: 2, 9: 3, 10: 2, 11: 2},
    "s05": {1: 2, 2: 2, 3: 2, 4: 3, 5: 3, 6: 4, 7: 3},
    "s06": {2: 2, 3: 2, 4: 4, 5: 3},
    "s07": {1: 2, 2: 3, 3: 2, 4: 4, 5: 2, 6: 2, 7: 2},
    "s08": {1: 2, 2: 2, 3: 2, 4: 2, 5: 2, 6: 2, 7: 2, 8: 2, 9: 2, 10: 4,
            11: 3, 12: 3, 13: 2, 14: 2},
    "s09": {1: 2, 2: 2, 9: 2, 10: 2, 11: 2, 12: 3, 13: 2, 14: 2, 15: 2,
            16: 3, 17: 3, 18: 3, 19: 3, 20: 3, 21: 3, 22: 4, 23: 2, 24: 2,
            25: 2, 27: 3, 28: 4, 29: 2},
    "s10": {1: 2, 2: 2, 3: 2, 4: 2, 5: 3, 6: 3, 7: 3, 8: 3, 9: 4, 10: 3,
            11: 3, 12: 3, 13: 4, 14: 2, 15: 3, 16: 2, 17: 3},
    "s11": {1: 3, 2: 2, 3: 2, 4: 3, 5: 2, 6: 2, 7: 3, 8: 2, 9: 2, 10: 2,
            11: 3, 12: 2, 13: 2, 14: 2, 15: 2, 16: 2, 17: 2, 18: 2, 19: 2,
            20: 2, 21: 2, 22: 2, 23: 2, 24: 2, 25: 2},
    "s12": {1: 2, 2: 3, 3: 3, 4: 3, 5: 3, 6: 4, 7: 3, 8: 3, 9: 4, 10: 4,
            11: 4, 12: 3, 13: 3, 14: 4, 15: 4, 16: 3, 17: 3, 18: 4, 19: 2,
            20: 3, 21: 3, 22: 3},
    "s13": {1: 4, 2: 3, 3: 3, 4: 3, 5: 4, 6: 3, 7: 3, 8: 3, 9: 3, 10: 4,
            11: 3, 12: 3, 13: 4, 14: 3, 15: 3, 16: 3, 17: 4, 18: 4, 19: 3,
            20: 3, 21: 4, 22: 3, 23: 3, 24: 3, 25: 4, 26: 4, 27: 3, 28: 3,
            29: 4, 30: 4, 31: 4, 32: 3, 33: 3},
    "s14": {1: 2, 2: 3, 3: 2, 4: 2, 6: 3, 7: 2, 8: 2, 9: 3, 10: 3, 11: 4,
            12: 2, 13: 4, 14: 2, 15: 3, 16: 4, 17: 3, 18: 4},
    "s15": {1: 2, 2: 2, 3: 2, 4: 2, 5: 2, 6: 2, 7: 2, 8: 2, 9: 3, 10: 2,
            11: 2, 12: 3, 13: 2, 14: 2},
    "s16": {0: 2, 1: 2, 2: 3},
    "s17": {0: 2, 1: 2, 2: 2, 3: 3, 4: 3, 16: 2, 17: 2, 18: 2, 19: 2, 20: 2},
}

# Blocks these ranges cover are replaced wholesale by the HTML below, with
# their data-lvl carried inline; they must not also appear in LEVELS.
REPLACED = {"s09": [(3, 8), (26, 26), (30, 30)], "s17": [(5, 15)]}

# ===========================================================================
# New prose — section 09, the one-run install
# ===========================================================================

S09_INSTALL = """<p data-lvl="2">WinSCP: a new session, SCP or SFTP, host <code>PI_IP</code>, the username and password from <a href="#s08">section 08</a> &mdash; then drag the zip into <code>/tmp</code>. Or, from PowerShell:</p>

<div class="cmd" data-lvl="2">
<div class="lbl"><span>Copy the release</span><span class="path">WinSCP, or any SCP client</span></div>
<pre>scp solar-surplus-vX.Y.zip USERNAME@PI_IP:/tmp/</pre>
</div>

<div class="cmd" data-lvl="2">
<div class="lbl"><span>Shell</span><span class="path">on the Raspberry Pi</span></div>
<pre>cd /tmp
unzip solar-surplus-vX.Y.zip
sudo python3 solar-surplus-vX.Y/install.py</pre>
</div>

<div class="note" data-lvl="2">
  <span class="h">The disk is the installer's business now</span>
  <p>There is no separate disk command and no disk flag. The <code>storage</code> step resolves the history disk inside the same run, in this order: a disk already carrying the <code>influxdb</code> label &mdash; a previous life of this system &mdash; is <b>adopted</b> exactly as it stands, with nothing written to it; a blank, unused USB disk is <b>offered</b>, and preparing it happens only after you type its device path in full; no disk at all ends the run &mdash; said out loud, with the recipe for adding one and re-running the step.</p>
</div>

<div class="note red" data-lvl="3">
  <span class="h">The one destructive moment, and its locks</span>
  <p>Preparing a blank disk erases it, so it is the one act in this build behind a typed confirmation: the installer lists only disks nothing is using, and still asks you to type the device path in full &mdash; a pipe cannot answer, and Enter declines. Read the listing before you type. The card this Pi runs from is <code>mmcblk0</code> and is never in the list, because everything mounted is excluded; the disk you mean is the one whose size you recognise, with no filesystem and nothing mounted.</p>
  <p data-lvl="4">Everything that could stop it runs before the first byte is written. It refuses a partition where a whole disk is meant, any disk with something mounted from it, a disk carrying swap, and a disk with an array or volume group on top &mdash; the first two of those rule out the card twice over, without depending on you reading a name correctly. What it leaves behind: one GPT partition, ext4, labelled <code>influxdb</code> with no reserved blocks, and an <code>/etc/fstab</code> line naming it by <b>UUID</b> with the options <code>defaults,noatime,nofail,x-systemd.device-timeout=30,x-systemd.before=docker.service</code>. The label is what a later reinstall adopts the disk by; the UUID is because an old drive on a different port comes back with a different name; <code>nofail</code> is because a Pi that stops at a maintenance shell over a sleepy disk is a Pi with no network and nothing charging.</p>
</div>

<p data-lvl="3">That is the whole of it. The script is standard-library Python &mdash; Raspberry Pi OS Lite already has <code>python3</code>, and an installer that needs <code>pip</code> before it can install anything is an installer that fails on the one machine where nothing is installed yet. <code>backup.py</code> and <code>restore.py</code> beside it hold to the same rule, for the same reason.</p>

<div class="cmd" data-lvl="3">
<div class="lbl"><span>Response</span><span class="path">the storage step meeting a blank disk, once</span></div>
<pre>&#9472;&#9472; The disk the history lives on &#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;

  No disk is mounted at /mnt/influxdb, but this Pi has an unused USB disk:
      NAME   SIZE TYPE FSTYPE LABEL MOUNTPOINTS
      sda  465.8G disk

  Preparing it ERASES it. Press Enter instead to stop without a disk.
  Type the device path to prepare it, or Enter to stop: /dev/sda

&#9472;&#9472; Prepare /dev/sda for InfluxDB &#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;
  /dev/sda &#8212; 500.1 GB Generic
    NAME   SIZE TYPE FSTYPE LABEL MOUNTPOINTS
    sda  465.8G disk

  warn    EVERYTHING ON /dev/sda WILL BE DESTROYED.
  Type the device path to confirm, or anything else to stop: /dev/sda
  ok      old signatures wiped
  ok      one GPT partition, /dev/sda1
  ok      ext4, label influxdb, no reserved blocks
  ok      UUID 63ea7203-5039-40c5-ba06-f36d695088d0
  ok      /etc/fstab written
          UUID=63ea7203-5039-40c5-ba06-f36d695088d0  /mnt/influxdb  ext4  <span class="c">\\</span>
          defaults,noatime,nofail,x-systemd.device-timeout=30,<span class="c">\\</span>
          x-systemd.before=docker.service  0  2
  ok      mounted at /mnt/influxdb (ext4)
  ok      491.1 GB usable</pre>
</div>

<p data-lvl="4">On a reinstall the same step never reaches that prompt: the disk carries the <code>influxdb</code> label from its first life, so the step adopts it &mdash; an <code>/etc/fstab</code> line by UUID, a mount, not one byte written &mdash; and the history is simply back. The three outcomes are ranked exactly so that the destructive one comes last, cannot touch a disk in use, and cannot happen at all without a human typing at a terminal.</p>

<p data-lvl="4">The manufacturer&rsquo;s 500&nbsp;GB is the kernel&rsquo;s 465.8&nbsp;GiB is 491.1&nbsp;GB usable once ext4 has taken its own overhead and given back the root reserve &mdash; three numbers for one disk, all of them correct, which is worth knowing before you go looking for the missing ten gigabytes. Write the UUID down or do not: it is in <code>/etc/fstab</code> from here on, and <code>blkid</code> will tell you again.</p>"""

S09_FLAGS = """<div class="tw" tabindex="0" data-lvl="3">
<table>
<caption>Flags &mdash; both of them</caption>
<thead><tr><th scope="col" style="width:30%">Flag</th><th scope="col">Effect</th></tr></thead>
<tbody>
<tr><td><code>--force</code></td><td>Replace files that exist and differ. Read what it refused first</td></tr>
<tr><td><code>--only STEP</code></td><td>Run only the named step. Repeatable &mdash; <code>--only files --only services</code> runs those two. For picking up after a failure, once you know which step failed</td></tr>
</tbody>
</table>
</div>"""

S09_MEASURED = """<div class="note green" data-lvl="3">
  <span class="h">Measured, on a bare card &mdash; twice</span>
  <p>Fresh 64-bit Lite image, release unzipped, the installer run once, on a Raspberry&nbsp;Pi&nbsp;4&nbsp;B. Everything happened in one session with no failures and nothing typed twice: Docker installed from scratch, evcc <b>0.313.3</b> from its own repository, both container stacks pulled and started, the bucket token minted and proved with a real write, and the dashboard imported through Grafana&rsquo;s <code>v2beta1</code> API rather than the fallback. The closing list held only what it should &mdash; a fresh login for the <code>docker</code> group, and the car.</p>
  <p>And measured again on 15&nbsp;August&nbsp;2026, as a reinstall: the same fresh card and one run, then the pairing key restored from its archive &mdash; the sequence <code>restore.py</code> now automates, run by hand and confirmed step by step &mdash; and the car answered the very first request. No ceremony, no key card, no driver&rsquo;s seat. That reinstall is what this release&rsquo;s backup and restore scripts are built from.</p>
</div>"""

# ===========================================================================
# New prose — section 17, backup and restore around the two scripts
# ===========================================================================

S17_BACKUP = """<div class="note blue" data-lvl="2">
  <span class="h">What to back up</span>
  <p><code>backup.py</code>, in the release beside the installer, writes one archive per component into your home directory: the pairing key, evcc&rsquo;s device database, the history together with the secrets that match it, and the board. Copy the archives somewhere that is not the Pi and not the card, and that is the whole discipline.</p>
  <p data-lvl="4">Five things are inside those four archives, and the fifth is the one most restores are missing. <code>/var/lib/evcc/evcc.db</code> holds the evcc configuration. <code>/mnt/influxdb/</code> on the USB disk holds the history and the CLI profile beside it, and the <code>grafana-data</code> volume on the card holds the board. <code>~/TeslaBleHttpProxy/key/</code> holds the pairing, and is the one item here that cannot be regenerated from anything at all. And <code>/etc/solar-surplus/</code> with the three files under <code>/etc/default/</code> holds the answers and the secrets &mdash; which is why they ride inside the history&rsquo;s archive rather than travelling alone. A restore that brings back the data but not its tokens produces a Pi whose voltage logger writes to an InfluxDB that has never heard of it, and whose Update buttons are refused: the secrets and the data arrive together or neither is any use.</p>
  <p data-lvl="4">The history living on its own disk changes what a backup is for. A dead card no longer takes the history with it &mdash; the disk survives, and the installer adopts it back by its label. What the archives still cover is the disk itself dying, a filesystem that will not mount, and the ordinary mistake. Two devices that fail independently is the whole benefit; treating the second one as a backup of the first is how people lose both.</p>
</div>

<div class="cmd" data-lvl="2">
<div class="lbl"><span>Backup</span><span class="path">ssh, or the terminal in WinSCP</span></div>
<pre>sudo python3 solar-surplus-vX.Y/backup.py</pre>
</div>

<p data-lvl="3">It stops evcc, the loggers and both container stacks before reading a byte &mdash; evcc&rsquo;s database and InfluxDB&rsquo;s bolt file are live stores, and a copy taken mid-write is a copy of a torn file &mdash; writes the four archives, starts everything again, and ends by counting the <code>.pem</code> files in the key archive out loud, because that archive is the one whose loss cannot be repaired. Expect the history archive in the tens of megabytes and growing; the key archive is a few kilobytes. Then, in WinSCP: the remote pane opens in your home directory, so the archives are already in front of you &mdash; drag them out, and keep them somewhere you have written down.</p>

<p data-lvl="4">The archives exist because nothing here can be pulled directly with WinSCP: Grafana&rsquo;s volume lives under <code>/var/lib/docker/volumes/</code>, the state files are root-owned, and <code>/mnt/influxdb</code> belongs to the disk rather than to your home directory &mdash; an SFTP session logged in as you can see none of them. So the Pi packs what root can read into archives that you can.</p>

<h3 data-lvl="2">Restore</h3>
<p data-lvl="2">The order of a rebuild: fresh card (<a href="#s08">section 08</a>), the installer (<a href="#s09">section 09</a>), one reboot for the docker group, the archives copied back to <code>/tmp</code>, then one command. It restores whichever of the four archives it finds, in the right order, with the right pauses, and says what it skipped and why.</p>

<div class="cmd" data-lvl="2">
<div class="lbl"><span>Restore, after a fresh install</span><span class="path">the archives in /tmp</span></div>
<pre>sudo python3 solar-surplus-vX.Y/restore.py
sudo reboot</pre>
</div>

<p data-lvl="3">What one command hides: it refuses to run before the installer has; it takes every service and both container stacks down so the volumes are closed; it puts the secrets back before anything starts, unpacks each archive to the root it was written from, returns ownership of the key and the history to your login, starts everything, waits for InfluxDB, Grafana and the BLE proxy to answer, and &mdash; if the key came back &mdash; prints the one request that proves the pairing survived. The reboot at the end is not politeness: every unit is still holding what it read at boot, and the restore has just replaced that on disk.</p>

<div class="note" data-lvl="3">
  <span class="h">A surviving disk needs no restoring &mdash; and both scripts know</span>
  <p>When the card died and the disk did not, the disk is carrying the history the card lost, and the installer&rsquo;s <code>storage</code> step adopts it by its <code>influxdb</code> label &mdash; mounted, recorded in <code>/etc/fstab</code> by UUID, untouched. <code>restore.py</code> then skips the history inside the influxdb archive on its own, saying so: the disk&rsquo;s copy is newer than any archive&rsquo;s. Only if the disk itself is what died do you want the archive&rsquo;s copy, and you say that out loud &mdash; <code>sudo python3 solar-surplus-vX.Y/restore.py influxdb</code>. Even then nothing is erased: what was there is set aside beside the data until you delete it yourself.</p>
  <p data-lvl="4">One consequence of adoption is worth knowing before it happens to you. An adopted disk holds a database built with the <em>old</em> secrets, and a fresh installer generates <em>new</em> ones &mdash; so the run stops at the <code>token</code> step with a 401, correctly, saying the admin token does not match the running instance. That stop is the sign to run <code>restore.py</code>: it puts the old secrets back, and the next <code>install.py</code> run reads them from <code>/etc/solar-surplus/install.conf</code>, generates nothing, and finishes the steps the stop skipped. Two runs with one restore between them, and every token matches the database it is pointed at.</p>
</div>

<div class="note green" data-lvl="4">
  <span class="h">Measured, on cards rebuilt from nothing</span>
  <p>Measured on an early build, when the history was still a Docker volume on the card: fresh Raspberry&nbsp;Pi&nbsp;OS write, release unzipped, installer run, archive restored, reboot &mdash; under thirty minutes end to end, and the board came back whole: the same history in the same panels, the same session totals, evcc still holding every device it was configured with, and the update desk reading Current on all five components. Nothing was reconfigured and nothing was typed in twice.</p>
  <p>Measured again on 15&nbsp;August&nbsp;2026, on this release&rsquo;s ancestor: fresh card, installer, reboot, and the pairing key alone put back by hand &mdash; the exact sequence <code>restore.py</code> now runs &mdash; and the car&rsquo;s body controller answered the first request. The pairing survived the reinstall with no ceremony, which was the whole claim.</p>
</div>

<div class="note" data-lvl="3">
  <span class="h">The key alone is a complete restore of the pairing</span>
  <p>Everything else in the archives is convenience &mdash; answers you could retype, dashboards you could rebuild, history you could live without. <code>TeslaBleHttpProxy/key/</code> is different in kind: the car holds the public half, and only the key-card ceremony in <a href="#s10">section 10</a> can enroll a new one. Restoring that directory <em>is</em> the pairing. On a machine where only the key matters, copy the key archive alone to <code>/tmp</code> and run <code>restore.py</code> &mdash; it restores what it finds. The proof, with the real VIN: <code>curl -s "http://127.0.0.1:8080/api/1/vehicles/YOUR_VIN/body_controller_state"</code> &mdash; a JSON answer means the key that came back is the one the car knows; &ldquo;your public key has not been paired&rdquo; means it is not, and section 10&rsquo;s ceremony is the road back.</p>
  <p data-lvl="4">The installer&rsquo;s <code>ble</code> step recognises a pre-existing <code>key/</code> and says so, which means the order also works the other way around: put the key back <em>before</em> running the installer and the run itself reports the pairing as already done.</p>
</div>

<div class="cmd" data-lvl="4">
<div class="lbl"><span>What the scripts do, spelled out</span><span class="path">the same backup and restore, by hand</span></div>
<pre><span class="c"># backup.py, by hand &#8212; one archive per component, everything stopped first</span>
sudo systemctl stop evcc grid-voltage-logger.service
docker compose -f ~/monitoring/docker-compose.yml stop
docker compose -f ~/TeslaBleHttpProxy/docker-compose.yml stop
sudo tar -czf ~/key-backup-$(date +%F).tar.gz      -C "$HOME" TeslaBleHttpProxy/key
sudo tar -czf ~/evcc-db-backup-$(date +%F).tar.gz  -C /      var/lib/evcc/evcc.db
sudo tar -czf ~/influxdb-backup-$(date +%F).tar.gz -C /mnt   influxdb <span class="c">\\</span>
     -C /  etc/solar-surplus etc/default/grid-voltage-logger <span class="c">\\</span>
           etc/default/update-agent etc/default/update-runner
sudo tar -czf ~/grafana-backup-$(date +%F).tar.gz  -C /      var/lib/docker/volumes/monitoring_grafana-data
docker compose -f ~/TeslaBleHttpProxy/docker-compose.yml start
docker compose -f ~/monitoring/docker-compose.yml start
sudo systemctl start evcc grid-voltage-logger.service

<span class="c"># restore.py, by hand &#8212; after install.py and its reboot, archives in /tmp</span>
cd /tmp
sudo systemctl stop evcc grid-voltage-logger.service update-agent.service
docker compose -f ~/monitoring/docker-compose.yml down
docker compose -f ~/TeslaBleHttpProxy/docker-compose.yml down
sudo tar -xzf influxdb-backup-*.tar.gz -C /    etc
sudo tar -xzf influxdb-backup-*.tar.gz -C /mnt influxdb   <span class="c"># only if the disk died</span>
sudo tar -xzf evcc-db-backup-*.tar.gz  -C /    var/lib/evcc/evcc.db
sudo tar -xzf grafana-backup-*.tar.gz  -C /    var
sudo tar -xzf key-backup-*.tar.gz      -C "$HOME" TeslaBleHttpProxy/key
sudo chown -R "$USER:$USER" ~/TeslaBleHttpProxy/key /mnt/influxdb/data /mnt/influxdb/config
docker compose -f ~/monitoring/docker-compose.yml up -d
docker compose -f ~/TeslaBleHttpProxy/docker-compose.yml up -d
sudo systemctl start evcc grid-voltage-logger.service update-agent.service
sudo reboot</pre>
</div>

<p data-lvl="4">Why each line is where it is: the stacks go <em>down</em> rather than <em>stop</em> on a restore because <code>down</code> releases the volumes the archives are about to replace; the secrets under <code>/etc</code> unpack before anything starts because every service reads them at start; the archives are named from <code>/tmp</code> by explicit path because <code>~</code> on a fresh card is a different home than the one they were written from; the <code>chown</code> exists because <code>tar</code> ran as root; and the reboot is what turns &ldquo;the files are back&rdquo; into &ldquo;the system read them&rdquo;.</p>"""

# ===========================================================================
# 1. Wholesale replacements and easy paragraphs, by parsed span
# ===========================================================================

REPLACEMENT_HTML = {("s09", 3, 8): S09_INSTALL,
                    ("s09", 26, 26): S09_FLAGS,
                    ("s09", 30, 30): S09_MEASURED,
                    ("s17", 5, 15): S17_BACKUP}

cols, secs = S.parse(src)
by_id = {s["id"]: s for s in secs}
if len(secs) != 17:
    sys.exit("expected 17 sections, found %d" % len(secs))

edits = []  # (start, end, replacement)

for sid, ranges in REPLACED.items():
    sec = by_id[sid]
    for a, b in ranges:
        start = sec["blocks"][a]["span"][0]
        end = sec["blocks"][b]["span"][1]
        edits.append((start, end, REPLACEMENT_HTML[(sid, a, b)]))

tagged = 0
for sid, levels in LEVELS.items():
    sec = by_id[sid]
    for i, lvl in levels.items():
        blk = sec["blocks"][i]
        a = blk["span"][0]
        tag = blk["tag"]
        if not src.startswith("<" + tag, a):
            sys.exit("%s block %d does not start with <%s>" % (sid, i, tag))
        p = a + 1 + len(tag)
        edits.append((p, p, ' data-lvl="%d"' % lvl))
        tagged += 1

for sid, para in EASY.items():
    sec = by_id[sid]
    first = sec["blocks"][0]
    if first["tag"] == "p" and "lede" in first["cls"]:
        at = first["span"][1]
        edits.append((at, at, "\n" + para))
    else:
        at = first["span"][0]
        edits.append((at, at, para + "\n\n"))

# Bottom-up, so earlier offsets stay valid. No two edits may overlap.
edits.sort(key=lambda e: (e[0], e[1]), reverse=True)
last_start = len(src) + 1
for start, end, replacement in edits:
    if end > last_start:
        sys.exit("overlapping edits at %d" % start)
    last_start = start
    src = src[:start] + replacement + src[end:]

print("spliced: %d replacements, %d depth tags, %d easy paragraphs"
      % (len(REPLACEMENT_HTML), tagged, len(EASY)))

# ===========================================================================
# 2. Small anchored edits inside kept blocks
# ===========================================================================

# The lede: no separate disk step to promise any more.
src = must(
    "One script, and everything it needs from the network is already switched "
    "on. Copy the release to the Pi, prepare the disk the history will live "
    "on, answer four questions, and everything between a bare Raspberry Pi OS "
    "and a working dashboard is done for you.",
    "One script, one run &mdash; the disk included. Everything it needs from "
    "the network is already switched on: copy the release to the Pi, answer "
    "four questions, and everything between a bare Raspberry Pi OS and a "
    "working dashboard is done for you.",
    src)

# The step count was written as thirteen beside a table of fourteen.
src = must("Nothing in the thirteen steps <em>needs</em>",
           "Nothing in the fourteen steps <em>needs</em>", src)

# The questions table: the storage step no longer merely insists.
src = must(
    "and what the <code>storage</code> step insists on finding a filesystem at",
    "and where the <code>storage</code> step mounts, adopts or prepares the disk",
    src)

# The steps table: the storage row describes the three ranked outcomes.
src = must(
    "<tr><td><code>storage</code></td><td>The one step that can stop the run "
    "over hardware. It insists that <code>/mnt/influxdb</code> is a filesystem "
    "of its own &mdash; mounted, not the card, and not one of the filesystems "
    "a database cannot live on &mdash; then creates <code>data/</code> and "
    "<code>config/</code> on it and reports the free space. It also says so if "
    "<code>/etc/fstab</code> does not mention the mount, because a mount that "
    "only exists until the next reboot is a trap rather than a disk</td></tr>",
    "<tr><td><code>storage</code></td><td>Resolves the history disk in one "
    "run: adopts a disk labelled <code>influxdb</code> untouched, offers to "
    "prepare a blank one behind a typed confirmation, or falls back to the "
    "card out loud. Then it checks what it has &mdash; a real filesystem, not "
    "the card, not one a database cannot live on, recorded in "
    "<code>/etc/fstab</code> so it comes back &mdash; creates "
    "<code>data/</code> and <code>config/</code> and reports the free "
    "space</td></tr>",
    src)

# Section 10's pass block: name the script, and point at the right section.
src = must(
    "Back up <code>~/TeslaBleHttpProxy/key/</code> now — it is the one thing "
    "in this build that cannot be regenerated from the release, and "
    "<a href=\"#s16\">section 16</a> is where restoring it makes a future "
    "reinstall skip this whole section.",
    "Back up <code>~/TeslaBleHttpProxy/key/</code> now &mdash; "
    "<code>backup.py</code> writes it as an archive of its own, it is the one "
    "thing in this build that cannot be regenerated from the release, and "
    "<a href=\"#s17\">section 17</a> is where restoring it makes a future "
    "reinstall skip this whole section.",
    src)

# Section 17's file table: the two new scripts, and the corrected counts.
src = must(
    "These twenty-four items rebuild the system on a fresh card. The eighteen "
    "marked <span class=\"tag\">custom</span>",
    "These twenty-six items rebuild the system on a fresh card. The twenty "
    "marked <span class=\"tag\">custom</span>",
    src)

INSTALL_ROW = ('<tr><td><span class="tag">custom</span> <a href="files/'
               'install.py">install.py</a></td><td>—</td><td>The installer. '
               'Runs from <code>/tmp</code> and is not left on the Pi</td></tr>')
NEW_ROWS = (
    '\n<tr><td><span class="tag">custom</span> <a href="files/backup.py">'
    'backup.py</a></td><td>—</td><td>One archive per component &mdash; the '
    'key, <code>evcc.db</code>, the history with its secrets, the board '
    '&mdash; written to your home directory. Runs from <code>/tmp</code> and '
    'is not left on the Pi</td></tr>'
    '\n<tr><td><span class="tag">custom</span> <a href="files/restore.py">'
    'restore.py</a></td><td>—</td><td>Puts any subset of those archives back '
    'onto a fresh install, in the proved order, and prints the pairing '
    'proof</td></tr>')
src = must(INSTALL_ROW, INSTALL_ROW + NEW_ROWS, src)

src = must(
    "The whole evcc configuration, written by the browser. Not installed, not "
    "touched, not backed up by this release",
    "The whole evcc configuration, written by the browser. Not installed and "
    "not touched by the installer; <code>backup.py</code> archives it",
    src)

# The footer names what ships.
src = must(
    "Released as <code>install.py</code> and the seventeen files in "
    "<code>files/</code>.",
    "Released as <code>install.py</code>, <code>backup.py</code>, "
    "<code>restore.py</code> and the seventeen files in <code>files/</code>.",
    src)

# ===========================================================================
# 3. The depth bar, its CSS, its script, and the body attribute
# ===========================================================================

DEPTH_CSS = """
/* ---- reading depth ------------------------------------------------------
   Four depths, cumulative, from a plain-language summary to every why
   answered. Blocks below section 01 carry data-lvl 2..4 or nothing; nothing
   means the Easy read. Hiding is one body attribute, so switching depth is
   a single write; print ignores the whole mechanism and shows everything,
   and so does a browser with no script (the <noscript> block below the
   body tag). Section 01 carries no depth marks at all - the argument is
   for everyone. */
body[data-depth="1"] :is([data-lvl="2"],[data-lvl="3"],[data-lvl="4"],[data-lvl="4"]),
body[data-depth="2"] :is([data-lvl="3"],[data-lvl="4"],[data-lvl="4"]),
body[data-depth="3"] :is([data-lvl="4"],[data-lvl="4"]),
body[data-depth="4"] [data-lvl="4"]{display:none}
.depth{
  position:sticky; top:0; z-index:40; background:var(--bg);
  border-bottom:1px solid var(--rule); max-width:790px;
  padding:12px 56px 13px;
}
.depth .dlbl{font:600 10.5px/1 var(--sans); letter-spacing:.16em; text-transform:uppercase; color:var(--faint); display:block; margin-bottom:9px}
.depth .dbtns{display:flex; gap:6px; flex-wrap:wrap}
.depth button{
  font:600 12.5px/1 var(--sans); letter-spacing:.02em; color:var(--muted);
  background:var(--panel); border:1px solid var(--rule); border-radius:20px;
  padding:7px 13px; cursor:pointer;
}
.depth button:hover{color:var(--ink); border-color:var(--accent-line)}
.depth button.on{color:#fff; background:var(--accent); border-color:var(--accent)}
.depth button:focus-visible{outline:2px solid var(--accent); outline-offset:2px}
.depth .dhint{display:block; margin-top:9px; font-size:12.8px; color:var(--muted)}
@media (max-width:1000px){ .depth{padding-left:26px; padding-right:26px} }
@media (max-width:560px){ .depth{padding-left:18px; padding-right:18px} .depth button{padding:6px 10px; font-size:12px} }
@media print{
  .depth{display:none}
  body[data-depth] [data-lvl]{display:revert !important}
}
"""

src = must(
    "  figure.chart svg text.v{font-size:27px} figure.chart svg text.c{font-size:23px}\n}\n</style>",
    "  figure.chart svg text.v{font-size:27px} figure.chart svg text.c{font-size:23px}\n}\n"
    + DEPTH_CSS + "</style>",
    src)

DEPTH_BAR = """<div class="depth" id="depth">
  <span class="dlbl">Reading depth</span>
  <div class="dbtns" role="group" aria-label="Reading depth">
    <button type="button" data-d="1" class="on" aria-pressed="true">Easy</button>
    <button type="button" data-d="2" aria-pressed="false">Normal</button>
    <button type="button" data-d="3" aria-pressed="false">Hard</button>
    <button type="button" data-d="4" aria-pressed="false">Legendary</button>
  </div>
  <span class="dhint" id="dhint">The short version &mdash; what each part is, and what you get.</span>
</div>

"""

src = must('<div class="col">\n\n<h2 id="s01">',
           DEPTH_BAR + '<div class="col">\n\n<h2 id="s01">', src)

src = must("<body>",
           '<body data-depth="1">\n'
           '<noscript><style>body[data-depth] [data-lvl]{display:revert}'
           '#depth{display:none}</style></noscript>',
           src)

DEPTH_JS = """(function(){
  // ------------------------------------------------------------ reading depth
  // Four cumulative depths; the default is the condensed read, and each
  // button reveals one more stratum of answers to "why?". Anything past the
  // fourth answer lives at the fourth. The document is complete at every
  // depth - print ignores the mechanism entirely and shows it all.
  var body = document.body;
  var bar = document.getElementById('depth');
  if(!bar){ return; }
  var hint = document.getElementById('dhint');
  var HINTS = {
    1: 'The short version \\u2014 what each part is, and what you get.',
    2: 'Enough to build it: the steps, the commands, the settings.',
    3: 'How it actually works \\u2014 mechanics, checks and edge cases.',
    4: 'The design decisions, and why each one went the way it did.',
    5: 'Every why answered, all the way down \\u2014 incidents, physics, war stories.'
  };
  var btns = Array.prototype.slice.call(bar.querySelectorAll('button[data-d]'));
  function set(d){
    body.setAttribute('data-depth', String(d));
    btns.forEach(function(b){
      var on = b.getAttribute('data-d') === String(d);
      b.classList.toggle('on', on);
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
    if(hint){ hint.textContent = HINTS[d] || ''; }
    // The contents highlight tracks heading positions, and every one of
    // them just moved; nudge the scroll handler rather than duplicating it.
    requestAnimationFrame(function(){ window.dispatchEvent(new Event('scroll')); });
  }
  btns.forEach(function(b){
    b.addEventListener('click', function(){
      set(parseInt(b.getAttribute('data-d'), 10) || 1);
    });
  });
})();
"""

src = must("  sync();\n})();\n</script>",
           "  sync();\n})();\n" + DEPTH_JS + "</script>", src)

# ===========================================================================
# 4. Prove the result still parses the way every tool expects
# ===========================================================================

cols2, secs2 = S.parse(src)
if len(secs2) != 17:
    sys.exit("after the edits: expected 17 sections, found %d" % len(secs2))
n_tags = len(re.findall(r' data-lvl="[2-5]"', src))
if n_tags < tagged:
    sys.exit("after the edits: %d depth tags survive of %d applied" % (n_tags, tagged))
heads = len(re.findall(r'<h2 id="s\d\d">', src))
if heads != 17:
    sys.exit("after the edits: %d numbered headings" % heads)
s01 = [s for s in secs2 if s["id"] == "s01"][0]
span01 = src[s01["span"][0]:s01["span"][1]]
if "data-lvl" in span01:
    sys.exit("section 01 must remain untouched, but carries a depth mark")

io.open(INDEX, "w", encoding="utf-8").write(src)
print("index.html: %d -> %d bytes, %d depth tags, 17 sections intact"
      % (orig_len, len(src), n_tags))
