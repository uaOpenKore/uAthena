#!/usr/bin/env python3
"""authguard_e2e.py <run dir>: the account lock against password guessing from many addresses (S. 2026-11-21).
The stand keeps ipban/dynamic_pass_failure_ban/account_fail_ban off for the other tests; this test turns
account_fail_ban on (and for check 7 the IP ban), restarts, and puts the import file back. 127.0.0.x are all
the loopback, so each is "another address".
 1 9 wrong passwords from 9 addresses: each refused as incorrect (account_fail_ban_limit 10)
 2 the 10th from a 10th address locks: the right password from a stranger's address is refused (code 6, "until")
 3 the owner's last login address (login.last_ip) still gets in; that login clears the lock
 4 the attack log has the lock (10 wrong passwords from 10 addresses, 5 min) and the refusal
 5 an unknown account name gets code 1 ("incorrect password"), like a wrong password
 6 the account's real password is not in the login-server's output, the tried one is
 7 with the IP ban on: 7 tries of unknown names from one address ban that address
"""
import os, socket, struct, subprocess, sys, time
SP = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/c1/e2e")
import rostub  # noqa: E402
run = sys.argv[1]
MYSQL = ["mysql", "--no-defaults", "-h127.0.0.1", "-P13306", "-uroot", "ragnarok", "-N", "-B", "-e"]
def sql(q): return subprocess.run(MYSQL + [q], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True).stdout.strip()
ok = True
def check(n, c, d=""):
    global ok
    print("%s  %s%s" % ("ok  " if c else "FAIL", n, ("  [%s]" % d) if d and not c else ""), flush=True); ok = ok and c
IMPORT = os.path.join(run, "conf", "import", "login_conf.txt")
MARK = "// [authguard_e2e]"
def conf(lines):
    # a value line cannot carry a comment (it would be part of the value): the block is fenced by comment lines
    text = open(IMPORT).read().split(MARK + " begin\n")[0]
    if lines:
        text += MARK + " begin\n" + "".join(l + "\n" for l in lines)
    open(IMPORT, "w").write(text)
def srv(a): subprocess.run([os.path.join(SP, "srv.sh"), a, run], stdout=subprocess.DEVNULL)
def restart():
    srv("stop"); srv("start"); time.sleep(4)
def login_from(src, user, pw):
    s = socket.create_connection(("127.0.0.1", rostub.LOGIN_PORT), timeout=10, source_address=(src, 0))
    try:
        s.sendall(struct.pack("<HI", 0x64, 20) + rostub._fixed(user, 24) + rostub._fixed(pw, 24) + b"\0")
        dl = time.time() + 10
        cmd = struct.unpack("<H", rostub._recv_exact(s, 2, dl))[0]
        if cmd == 0x69:
            return "ok"
        if cmd == 0x6A:
            rest = rostub._recv_exact(s, 21, dl)
            return "refused code=%d %s" % (rest[0], rest[1:].split(b"\0")[0].decode("latin-1"))
        return "unexpected 0x%04x" % cmd
    finally:
        s.close()
def attack():
    try: return open(os.path.join(run, "log", "attack-login.log"), errors="replace").read()
    except FileNotFoundError: return ""
def loginout(): return open(os.path.join(run, "login.out"), errors="replace").read()

USER, PW = "agvictim", "agright77"
try:
    conf(["account_fail_ban: yes", "hide_unknown_account: yes"])
    restart()
    if sql("SELECT COUNT(*) FROM login WHERE userid='%s'" % USER) == "0":
        login_from("127.0.0.1", USER + "_M", PW); time.sleep(1)
    sql("UPDATE login SET user_pass='%s', last_ip='127.0.0.50', state=0, ban_until=0 WHERE userid='%s'" % (PW, USER))
    sql("DELETE FROM ipbanlist")
    log0 = len(loginout()); att0 = len(attack())
    r = [login_from("127.0.0.%d" % (11 + i), USER, "guess%d" % i) for i in range(9)]
    check("1 9 wrong passwords from 9 addresses: each refused as incorrect", all(x.startswith("refused code=1") for x in r), r)
    r5 = login_from("127.0.0.20", USER, "guess9")
    stranger = login_from("127.0.0.21", USER, PW)
    check("2 the 10th from a 10th address locks: the right password from a stranger is refused 'until <time>'",
          r5.startswith("refused code=1") and stranger.startswith("refused code=6 ") and len(stranger) > len("refused code=6 ") + 5,
          "5th=%r stranger=%r" % (r5, stranger))
    owner = login_from("127.0.0.50", USER, PW)
    after = login_from("127.0.0.21", USER, PW)
    check("3 the owner's last login address gets in, and that clears the lock", owner == "ok" and after == "ok",
          "owner=%r after=%r" % (owner, after))
    a = attack()[att0:]
    check("4 the attack log: the lock (10 from 10 addresses, 5 min) and the refusal",
          "acc='agvictim' bruteforce: 10 wrong password(s) from 10 address(es) in 10 min, the account is locked 5 min" in a
          and "acc='agvictim' bruteforce_refused: the account is locked until" in a, a[-600:])
    unk = login_from("127.0.0.30", "nosuchname9q", "whatever1")
    check("5 an unknown name gets code 1 like a wrong password", unk.startswith("refused code=1"), unk)
    out = loginout()[log0:]
    check("6 the real password is not logged, the tried one is", PW not in out and "received pass: guess0" in out,
          [l for l in out.splitlines() if "Invalid password" in l][:2])
    # 7 the IP ban counts unknown names now
    conf(["account_fail_ban: yes", "ipban: yes", "dynamic_pass_failure_ban: yes"])
    restart(); sql("DELETE FROM ipbanlist"); sql("DELETE FROM loginlog WHERE ip=%d" % (127 << 24 | 40))
    for i in range(7):
        login_from("127.0.0.40", "nosuchname%d" % i, "x%d" % i)
    time.sleep(1)
    bans = sql("SELECT list FROM ipbanlist").splitlines()
    check("7 IP ban on: 7 unknown names from one address ban it", bans == ["127.0.0.40"], bans)
finally:
    conf([]); sql("DELETE FROM ipbanlist"); srv("stop")
print("ALL PASSED" if ok else "FAILED")
sys.exit(0 if ok else 1)
