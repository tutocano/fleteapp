-- Fix puntual: normaliza a minusculas los correos de usuario ya existentes.
--
-- Motivo: antes de este fix, el correo se guardaba tal cual lo escribia el
-- SUPER_ADMIN al crear el usuario (ej. "Juang@dist.com"), pero el login
-- comparaba el correo de forma exacta (sensible a mayusculas). Si el usuario
-- despues escribia su correo en minusculas para iniciar sesion, fallaba con
-- "Correo o contrasena incorrectos" aunque la contrasena fuera correcta.
--
-- El codigo ya se corrigio (UsuarioBase/LoginRequest normalizan a minusculas,
-- y el login ademas compara con func.lower() como respaldo). Este script solo
-- limpia los datos que ya existian en produccion antes del fix.
--
-- Es idempotente: correrlo varias veces no hace dano (LOWER de algo que ya
-- esta en minusculas no cambia nada).
--
-- Uso:
--   docker run -i --rm postgres:15-alpine psql "<External Database URL>/flete_db" < migrate_v4_fix_email_lower.sql

UPDATE usuario SET email = LOWER(email) WHERE email <> LOWER(email);
