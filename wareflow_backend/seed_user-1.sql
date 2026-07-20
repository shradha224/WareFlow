-- Removes any previous demo/admin users and creates three fresh ones,
-- one per role. All three share the password: 12345678

DELETE FROM users WHERE user_id IN ('admin1', 'wareflow_admin', 'supervisor1', 'inspector1', 'worker1');

INSERT INTO users (user_id, password, user_role, email_verified) VALUES
  ('supervisor1', '$2b$12$qhiaadKfuDiejHCLAyh/ke/9V0JecmhX5HbdmBAEYnRsqqmcRUZca', 'Supervisor', 1),
  ('inspector1',  '$2b$12$qhiaadKfuDiejHCLAyh/ke/9V0JecmhX5HbdmBAEYnRsqqmcRUZca', 'Inventory Inspector', 1),
  ('worker1',     '$2b$12$qhiaadKfuDiejHCLAyh/ke/9V0JecmhX5HbdmBAEYnRsqqmcRUZca', 'Worker', 1);
