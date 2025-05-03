create table public.planning_areas (
  id serial not null,
  subzone text not null,
  planning_area text not null,
  region text not null,
  min_latitude double precision not null,
  max_latitude double precision not null,
  min_longitude double precision not null,
  max_longitude double precision not null,
  created_at timestamp without time zone null default CURRENT_TIMESTAMP,
  updated_at timestamp without time zone null default CURRENT_TIMESTAMP,
  geometry_type text null,
  coordinates text null,
  constraint planning_areas_pkey primary key (id)
) TABLESPACE pg_default;