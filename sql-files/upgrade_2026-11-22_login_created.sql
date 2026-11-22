-- [purge] When an account was registered (S. 2026-11-22): the inactive-account cleanup deletes an account that never
-- logged in (lastlogin = 0) only once it is older than the threshold. Existing accounts get NULL (registration
-- date unknown), every new account gets the time of its INSERT from the column default, whoever inserts it
-- (login-server _M/_F registration or the web site).
-- The index serves the cleanup's "lastlogin older than N days" query.
ALTER TABLE `login` ADD COLUMN `created` DATETIME NULL DEFAULT NULL;
ALTER TABLE `login` MODIFY COLUMN `created` DATETIME NULL DEFAULT CURRENT_TIMESTAMP, ADD KEY `lastlogin` (`lastlogin`);
