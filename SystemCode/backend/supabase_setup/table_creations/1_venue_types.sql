create table public.venue_types (
  id serial not null,
  type_name text not null,
  created_at timestamp without time zone null default CURRENT_TIMESTAMP,
  updated_at timestamp without time zone null default CURRENT_TIMESTAMP,
  constraint venue_types_pkey primary key (id),
  constraint venue_types_type_name_key unique (type_name)
) TABLESPACE pg_default;