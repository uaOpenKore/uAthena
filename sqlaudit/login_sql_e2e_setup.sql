-- Audit DB only: accounts for login_sql_e2e.py (run before the login-server boots: it reads GM levels at start).
DELETE FROM login WHERE userid IN ('sqlinj1', 'sqlinj2', 'sqlinj2_hidden', 'qa''b', 'x''OR SLEEP(0.0005)OR''');
INSERT INTO login (userid, user_pass, sex, email, level) VALUES ('sqlinj1', 'injpw1', 'M', 'a@a.com', 1);
INSERT INTO login (userid, user_pass, sex, email, level) VALUES ('sqlinj2', 'injpw2', 'M', 'a@a.com', 99);
DELETE FROM `char` WHERE name IN ('SqlInj1', 'SqlInj2');
