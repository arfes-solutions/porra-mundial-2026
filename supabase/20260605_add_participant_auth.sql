alter table public.participants
add column if not exists email text unique;

alter table public.participants
add column if not exists password_hash text;
