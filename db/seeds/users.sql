-- Seed users
INSERT INTO users (user_id, username, hashed_password, role) VALUES 
('00000000-0000-0000-0000-000000000001', 'analyst', '$2b$12$Nq9T.Yw94K.gM/.c8W4uOOGi2V5O75iYQ0/k/j28.J3vN7Ww7WbW2', 'ANALYST'),
('00000000-0000-0000-0000-000000000002', 'admin', '$2b$12$Nq9T.Yw94K.gM/.c8W4uOOGi2V5O75iYQ0/k/j28.J3vN7Ww7WbW2', 'ADMIN');
-- Note: Replace password hashes with proper bcrypt hashes for analyst123 and admin123
